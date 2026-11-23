"""The client's footage: probing, frame-accurate decoding of a range, and reframing to the 16:9 output.

Coordinates are *display* pixels of the source (after the iPhone rotation flag; ffmpeg applies it). A view is
(cx, cy, cw): the centre and width of a 16:9 window in those pixels, plus an optional roll in degrees.
"""
import functools
import glob
import json
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "renders/src/footage")
W, H, FPS = 1920, 1080, 30
ASPECT = W / H
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def frame_of(t):
    """The output frame a time falls in (a cut placed at an audio onset lands on the frame containing it)."""
    return int(np.floor(t * FPS + 1e-6))


@functools.lru_cache(None)
def info(clip):
    """clip: '0418' -> path, display size, fps, duration, HDR flag. Photos (jpg/png) get fps 0."""
    path = sorted(glob.glob(os.path.join(SRC, f"IMG_{clip}.*")))[0]
    if path.lower().endswith((".jpg", ".png")):
        im = cv2.imread(path)
        return dict(path=path, w=im.shape[1], h=im.shape[0], fps=0.0, dur=0.0, hdr=False, photo=True)
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,avg_frame_rate,color_transfer:stream_side_data=rotation:format=duration",
                                   "-of", "json", path], capture_output=True, text=True, check=True).stdout)
    s = d["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = s["width"], s["height"]
    if abs(rot) == 90:
        w, h = h, w
    a, b = s["avg_frame_rate"].split("/")
    return dict(path=path, w=w, h=h, fps=float(a) / float(b), dur=float(d["format"]["duration"]),
                hdr=s.get("color_transfer") == "arib-std-b67", photo=False)


def decode(clip, t0, t1, band=None, scale=1.0):
    """Every source frame in [t0, t1): (frames uint8 RGB [n,h,w,3], source time of each).
    band = (x, y, w, h) crops in display pixels first; scale resizes after the crop (lanczos)."""
    i = info(clip)
    t0 = max(0.0, t0)
    t1 = min(i["dur"], t1)
    vf = []
    if i["hdr"]:
        vf.append(TONEMAP)
    bw, bh = i["w"], i["h"]
    if band:
        x, y, bw, bh = [int(round(v)) for v in band]
        x, y = max(0, x), max(0, y)
        bw, bh = min(bw, i["w"] - x), min(bh, i["h"] - y)
        bw, bh = bw - bw % 2, bh - bh % 2
        vf.append(f"crop={bw}:{bh}:{x}:{y}")
    ow, oh = bw, bh
    if abs(scale - 1.0) > 1e-3:
        ow, oh = int(round(bw * scale / 2)) * 2, int(round(bh * scale / 2)) * 2
        vf.append(f"scale={ow}:{oh}:flags=lanczos")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", i["path"], "-t", f"{t1 - t0:.4f}"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (ow * oh * 3)
    frames = np.frombuffer(raw[:n * ow * oh * 3], np.uint8).reshape(n, oh, ow, 3)
    times = t0 + np.arange(n) / i["fps"]
    return frames, times


def photo(clip, rotate=0):
    """A photo as float RGB 0..1, EXIF orientation applied, optionally rotated by 90/180/270 (clockwise)."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(info(clip)["path"])).convert("RGB")
    if rotate:
        im = im.rotate(-rotate, expand=True)
    return np.asarray(im).astype(np.float32) / 255


class Shot:
    """Source frames for one shot, decoded once, and the 16:9 view of any of them.

    times: the source times the shot will ask for (to size the decode).
    views: [(cx, cy, cw)] the windows it will ask for (to size the band and the decode scale).
    """

    def __init__(self, clip, times, views, margin=1.25, max_scale=1.0):
        self.clip = clip
        i = info(clip)
        self.info = i
        cw_min = min(v[2] for v in views)
        # the band: the union of every window (with a margin for shakes, punches and rolls), in display px
        xs0, xs1, ys0, ys1 = [], [], [], []
        for cx, cy, cw in views:
            ch = cw / ASPECT
            xs0.append(cx - cw * margin / 2); xs1.append(cx + cw * margin / 2)
            ys0.append(cy - ch * margin / 2); ys1.append(cy + ch * margin / 2)
        x0, x1 = max(0, min(xs0)), min(i["w"], max(xs1))
        y0, y1 = max(0, min(ys0)), min(i["h"], max(ys1))
        # decode scale: the tightest window should map to at least the output width, never upscaled at decode
        self.scale = min(max_scale, max(W / cw_min, 0.25))
        self.band = (x0, y0, x1 - x0, y1 - y0)
        t0, t1 = min(times) - 0.05, max(times) + 0.1
        self.frames, self.times = decode(clip, t0, t1, self.band, self.scale)
        self.x0, self.y0 = int(round(x0)) // 1, int(round(y0)) // 1

    def src(self, s, blend=False):
        """The decoded source frame at source time s (nearest, or blended between neighbours) as float32 0..1."""
        k = (s - self.times[0]) * self.info["fps"]
        k = min(max(k, 0), len(self.frames) - 1)
        i0 = int(np.floor(k))
        f = k - i0
        a = self.frames[i0].astype(np.float32)
        if blend and f > 0.02 and i0 + 1 < len(self.frames):
            a = a * (1 - f) + self.frames[i0 + 1].astype(np.float32) * f
        return a / 255

    def view(self, s, cx, cy, cw, roll=0.0, blend=False, out=(W, H), dx=0.0, dy=0.0, img=None):
        """Render the 16:9 window (centre cx, cy, width cw in display px, roll degrees) of the frame at source
        time s to the output size. dx, dy shift the result in output pixels (shake)."""
        img = self.src(s, blend) if img is None else img
        ow, oh = out
        sc = self.scale
        # display px -> decoded px
        ccx, ccy, ccw = (cx - self.x0) * sc, (cy - self.y0) * sc, cw * sc
        k = ow / ccw                                     # decoded px -> output px
        a = np.deg2rad(roll)
        ca, sa = np.cos(a) * k, np.sin(a) * k
        m = np.float32([[ca, -sa, ow / 2 + dx - (ca * ccx - sa * ccy)],
                        [sa, ca, oh / 2 + dy - (sa * ccx + ca * ccy)]])
        interp = cv2.INTER_CUBIC if k > 1.05 else cv2.INTER_LINEAR
        out_img = cv2.warpAffine(img, m, (ow, oh), flags=interp, borderMode=cv2.BORDER_REFLECT101)
        if k > 1.2:                                      # upscaled footage: restore some edge contrast
            blur = cv2.GaussianBlur(out_img, (0, 0), 1.2 * k / 1.8)
            out_img = out_img + (out_img - blur) * min(0.6, 0.35 * k)
        return np.clip(out_img, 0, 1)


def ramp(keys):
    """A time map from keyframes [(out_t, src_t), ...]: monotone cubic between them (speed ramps that ease)."""
    from scipy.interpolate import PchipInterpolator
    ks = np.array(keys, float)
    f = PchipInterpolator(ks[:, 0], ks[:, 1], extrapolate=True)
    return lambda t: float(f(t))


def linear(out0, src0, speed):
    return lambda t: src0 + (t - out0) * speed


def path(keys):
    """A view path from keyframes [(out_t, cx, cy, cw[, roll]), ...], eased (smoothstep) between keys."""
    ks = [tuple(k) + (0.0,) * (5 - len(k)) for k in keys]

    def f(t):
        if t <= ks[0][0]:
            return ks[0][1:]
        for a, b in zip(ks, ks[1:]):
            if t <= b[0]:
                u = (t - a[0]) / max(1e-6, b[0] - a[0])
                u = u * u * (3 - 2 * u)
                return tuple(a[i] + (b[i] - a[i]) * u for i in range(1, 5))
        return ks[-1][1:]
    return f
