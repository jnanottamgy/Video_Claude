"""TaxWise Singapore reel: the compositor (picture only; tools/deliver.sh adds the sound).

Per output frame:
  on camera (edl.PICTURE: shots A, B, E, F):
    the source frame (limited-range BT.709 -> full RGB) and its person matte (renders/mattes)
    -> his edges decontaminated against the shot's clean plate (tools/plates.py): no halo of white wall
    -> the room re-lit as a dim midnight-navy set with a royal-blue pool of light behind his head; the
       desk graded as dark warm wood
    -> the wall graphics (slots/*_behind, designed in source coordinates) on the wall, occluded by him and
       by the desk; a gold aura glowing off him
    -> him on top: a warm, clean skin grade and a gold rim light (flaring on the "aura" pull-outs)
    -> the camera: zooms about his face (the pull-outs, the pushes), punch-ins, shake
  full scenes (slots/singapore_slam, team_services, globe, end_card): their frames as rendered
  then: hits and transitions (flash, zoom blur, chromatic kick, glitch, light leaks, the end-card
  dissolve), vignette, grain, and the captions (tools/captions.py) on the on-camera sections.

  python3 tools/composite.py --stills 0.5,7.0      # QA frames -> renders/verify/
  python3 tools/composite.py --part 0/4            # one of N parallel parts -> renders/picture/part_0.mp4
  python3 tools/composite.py --join 4              # concatenate the parts -> renders/picture/picture.mp4
"""
import argparse
import glob
import os
import subprocess
import sys
from collections import OrderedDict

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import captions as CAP  # noqa: E402
import edl  # noqa: E402
import fx  # noqa: E402

cv2.setNumThreads(1)
W, H, FPS = edl.W, edl.H, edl.FPS
ROOT = edl.ROOT
DECODE_VF = "scale=in_color_matrix=bt709:in_range=tv:out_range=full"
PIC = os.path.join(ROOT, "renders/picture")

# his face centre per shot (source px), measured from the mattes: the camera zooms about it
SHOT_FACE = {"A": (882, 1016), "B": (938, 1049), "E": (912, 1024), "F": (895, 1062)}
# at desk level (y > 1100) he never reaches left of this x; the person segmenter glues the phone, its stand
# and the picture frame to him there (shot A especially), so the matte is cut off softly to their left
DESK_LEFT = {"A": 585, "B": 615, "E": 605, "F": 590}

SLOTS = [("hook_behind", 0.00, "behind"), ("name_behind", 6.10, "behind"), ("singapore_slam", 12.50, "full"),
         ("team_services", 14.22, "full"), ("globe", 25.47, "full"), ("values_behind", 35.57, "behind"),
         ("finale_behind", 42.37, "behind"), ("end_card", 48.25, "full")]
FULL = [(12.50, 14.22, "singapore_slam"), (14.22, 25.47, "team_services"), (25.47, 35.57, "globe"),
        (48.25, edl.DURATION, "end_card")]

# ---------------- direction (output seconds) ----------------
CAMERA = [  # (t0, t1, scale from, scale to, ease)
    (0.00, 3.10, 1.42, 1.12, "out3"),      # the hook: a slow pull-out from a close-up
    (3.10, 6.10, 1.12, 1.18, "io"),
    (6.10, 7.40, 1.45, 1.00, "expo"),      # the aura pull-out reveals his name
    (7.40, 8.50, 1.00, 1.00, "io"),
    (8.50, 12.50, 1.00, 1.22, "in2"),      # the build: a push-in toward the drop
    (35.57, 36.80, 1.35, 1.05, "expo"),    # back to him through the gold pulse: aura pull-out
    (36.80, 42.37, 1.05, 1.12, "io"),
    (42.37, 48.25, 1.05, 1.30, "push"),    # the last line: a push that accelerates into the bloom
]
PUNCH = [(38.24, 0.05), (39.20, 0.05), (41.52, 0.06)]                   # the values land: +5%, 0.3 s back
SHAKE = [(12.50, 10.0, 0.14, 17.0), (16.34, 4.0, 0.10, 19.0), (29.92, 2.5, 0.10, 19.0)]       # the end card stays still
FLASH = [(6.10, fx.WARM_WHITE, 0.45, 0.10), (12.50, fx.WARM_WHITE, 0.85, 0.17), (14.22, fx.WARM_WHITE, 0.22, 0.08),
         (16.34, fx.GOLD_HI, 0.16, 0.10), (35.57, fx.GOLD_HI, 0.78, 0.24), (42.37, fx.WARM_WHITE, 0.15, 0.06)]
CHROMA = [(6.10, 5, 0.10), (12.50, 10, 0.12), (14.22, 6, 0.08), (16.34, 3, 0.08), (35.57, 5, 0.12), (42.37, 6, 0.07)]
ZBLUR = [(6.10, 0.7), (12.50, 0.85), (14.22, 0.7), (35.57, 0.6)]
GLITCH = [(42.33, 42.40, 0.55)]                                             # the cut to his last line: two frames
LEAK = [(0.00, 2.60, 0.24, 0.60), (6.10, 8.00, 0.30, 0.55), (35.57, 37.50, 0.26, 0.62), (45.60, 48.25, 0.30, 0.50)]   # right side: clear of the wall titles
AURA = [(6.10, 1.0, 1.5), (35.57, 1.0, 1.5), (43.07, 0.45, 0.9)]           # rim + halo flares: (t, amount, decay s)
RIM_BASE, HALO_BASE = 0.35, 0.06
POOL = 0.14                                                                 # the royal-blue backlight (a touch)
DISSOLVE = (48.15, 48.32)                                                   # the bloom into the end card


def ease(name, u):
    u = min(max(u, 0.0), 1.0)
    if name == "expo":
        return (1 - 2 ** (-10 * u)) / (1 - 2 ** -10)
    if name == "out3":
        return 1 - (1 - u) ** 3
    if name == "in2":
        return u * u
    if name == "push":
        return 0.62 * u + 0.38 * u ** 6
    return u * u * (3 - 2 * u)


def decay(t, t0, d):
    return float(np.exp(-(t - t0) / d)) if t >= t0 else 0.0


def picture_at(t):
    for t0, t1, off, shot in edl.PICTURE:
        if t0 <= t < t1:
            return off, shot
    return None, None


def scale_at(t):
    s = 1.0
    for t0, t1, s0, s1, e in CAMERA:
        if t0 <= t < t1:
            s = s0 + (s1 - s0) * ease(e, (t - t0) / (t1 - t0))
            break
    for tp, amt in PUNCH:
        u = t - tp
        if 0 <= u < 0.06:
            s *= 1 + amt * ease("out3", u / 0.06)
        elif 0.06 <= u < 0.36:
            s *= 1 + amt * (1 - ease("io", (u - 0.06) / 0.30))
    return s


def shake_at(t):
    dx = dy = rot = 0.0
    for i, (ts, amp, dec, freq) in enumerate(SHAKE):
        if ts <= t < ts + 5 * dec:
            a, b, r = fx.shake_offset(t, ts, amp, dec, freq, seed=i)
            dx, dy, rot = dx + a, dy + b, rot + r
    return dx, dy, rot


class Source:
    """Sequential decoder with restarts on seeks, plus a small frame cache."""

    def __init__(self):
        self.p, self.pos, self.cache = None, -1, OrderedDict()

    def _open(self, f):
        if self.p:
            self.p.kill()
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, f - 0.01) / FPS:.6f}", "-i", edl.SRC,
                                   "-vf", DECODE_VF, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=W * H * 3 * 4)
        self.pos = f

    def get(self, f):
        f = int(min(max(f, 0), 1679))
        if f in self.cache:
            return self.cache[f]
        if self.p is None or f < self.pos or f > self.pos + 45:
            self._open(f)
        while self.pos <= f:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                raise RuntimeError(f"decode ended before frame {f}")
            self.cache[self.pos] = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.pos += 1
            while len(self.cache) > 8:
                self.cache.popitem(last=False)
        return self.cache[f]


class Comp:
    def __init__(self):
        self.src = Source()
        self.slots = {}
        for name, t0, layer in SLOTS:
            files = sorted(glob.glob(os.path.join(ROOT, "slots", name, "renders/png/*.png")))
            if files:
                self.slots[name] = (t0, layer, files)
            else:
                print(f"  (slot {name}: no frames yet)")
        self.plates = {}
        for s in SHOT_FACE:
            pl = cv2.imread(os.path.join(ROOT, f"renders/plates/plate_{s}.png"))
            dk = cv2.imread(os.path.join(ROOT, f"renders/plates/desk_{s}.png"), cv2.IMREAD_GRAYSCALE)
            fxs, fys = SHOT_FACE[s]
            pool = fx.pool(fxs - 30, fys - 170, 600, fx.ROYAL, POOL)
            d = dk.astype(np.float32) / 255
            rows = np.nonzero(d.max(1) > 0)[0]
            d0 = int(rows[0]) if len(rows) else H                          # first row with any desk
            full = np.nonzero(d.min(1) < 1)[0]
            d1 = int(full[-1]) + 1 if len(full) else H                     # first row that is all desk
            self.plates[s] = (cv2.cvtColor(pl, cv2.COLOR_BGR2RGB).astype(np.float32) / 255, d[..., None], pool,
                              min(d0, d1), d1)
        xx = np.arange(W, dtype=np.float32)[None, :]
        yy = np.arange(H, dtype=np.float32)[:, None]
        self.keep = {s: np.maximum(fx.smoothstep(x0 - 12, x0 + 12, xx), 1 - fx.smoothstep(1080, 1110, yy))
                     for s, x0 in DESK_LEFT.items()}
        self.matte_ids = sorted(int(os.path.basename(p)[2:7]) for p in glob.glob(os.path.join(ROOT, "renders/mattes/f_*.png")))
        self.caps = CAP.Captions()

    # ---- layers ----
    def slot_frame(self, name, t):
        if name not in self.slots:
            return None
        t0, layer, files = self.slots[name]
        k = int(round((t - t0) * FPS))
        if k < 0 or k > len(files):
            return None
        return fx.load_rgba(files[min(k, len(files) - 1)])

    def behind_layers(self, t):
        out = []
        for name, t0, layer in SLOTS:
            if layer == "behind" and name in self.slots:
                n = len(self.slots[name][2])
                if t0 - 1e-6 <= t < t0 + n / FPS + 1e-6:
                    im = self.slot_frame(name, t)
                    if im is not None:
                        out.append(im)
        return out

    def matte(self, f):
        if f not in self.matte_ids:
            i = int(np.argmin(np.abs(np.array(self.matte_ids) - f)))
            f = self.matte_ids[i]
        m = cv2.imread(os.path.join(ROOT, f"renders/mattes/f_{f:05d}.png"), cv2.IMREAD_GRAYSCALE)
        return m.astype(np.float32) / 255

    # ---- the on-camera picture, built in source coordinates, then the camera ----
    def aroll(self, t, off, shot):
        f = int(round((t + off) * FPS))
        img = self.src.get(f).astype(np.float32) / 255
        m = self.matte(f) * self.keep[shot]
        plate, desk, pool, d0, d1 = self.plates[shot]
        aura = sum(a * decay(t, t0, d) for t0, a, d in AURA)

        # his region, padded: all the per-person work happens inside it
        x0, y0, w, h = cv2.boundingRect((m > 0.003).astype(np.uint8))
        pad = 72
        R = (slice(max(0, y0 - pad), min(H, y0 + h + pad)), slice(max(0, x0 - pad), min(W, x0 + w + pad)))

        # the room: behind his edges, the wall pushed in from this frame; then his matte tightened against it
        room = img.copy()
        room[R] = fx.local_background(img[R], m[R], plate[R])
        mR = fx.refine_alpha(img[R], m[R], room[R])
        m = np.zeros_like(m)
        m[R] = mR

        # the room re-lit navy above the desk line, the desk graded as wood below it, a feathered band between
        bg = np.empty_like(img)
        bg[:d0] = fx.relight(room[:d0], pool[:d0])
        bg[d1:] = fx.grade_desk(room[d1:])
        if d1 > d0:
            dk = desk[d0:d1]
            bg[d0:d1] = fx.relight(room[d0:d1], pool[d0:d1]) * (1 - dk) + fx.grade_desk(room[d0:d1]) * dk
        for layer in self.behind_layers(t):
            bx, by, bw, bh = cv2.boundingRect((layer[..., 3] > 0.002).astype(np.uint8))
            if bw == 0:
                continue
            S = (slice(by, by + bh), slice(bx, bx + bw))
            a = layer[S][..., 3:4] * (1 - desk[S])
            bg[S] = layer[S][..., :3] * a + bg[S] * (1 - a)
        hl = fx.halo(m, HALO_BASE + 0.30 * aura)
        if hl is not None:
            bg += hl * (1 - desk)

        # him
        PR = fx.grade_person(fx.decontaminate(img[R], mR, room[R]))
        mm = mR[..., None]
        out = bg
        out[R] = PR * mm + bg[R] * (1 - mm)
        out[R] = fx.backlight(out[R], fx.rim_band(mR), RIM_BASE + 1.1 * aura)

        # camera: zoom about his face, then shake
        cx, cy = SHOT_FACE[shot]
        s = scale_at(t)
        M = np.vstack([fx.camera_matrix(s, cx, cy), [0, 0, 1]])
        dx, dy, rot = shake_at(t)
        if dx or dy or rot:
            M = np.vstack([fx.camera_matrix(1.0 + 2 * abs(dx) / W, W / 2, H / 2, dx, dy, rot), [0, 0, 1]]) @ M
        return fx.warp(np.clip(out, 0, 1), M[:2]), (cx, cy)

    def full(self, t, name):
        im = self.slot_frame(name, t)
        if im is None:
            return np.full((H, W, 3), fx.NAVY_DEEP, np.float32)
        img = im[..., :3] * im[..., 3:4] + fx.NAVY_DEEP * (1 - im[..., 3:4])
        dx, dy, rot = shake_at(t)
        if dx or dy or rot:
            img = fx.warp(img, fx.camera_matrix(1.0 + 2 * (abs(dx) + abs(dy)) / W, W / 2, H / 2, dx, dy, rot))
        return img

    def base(self, t):
        """(image, focus point, on camera?) for output time t."""
        for t0, t1, name in FULL:
            if t0 - 1e-6 <= t < t1:
                if name == "end_card" or True:
                    return self.full(t, name), (W / 2, H / 2), False
        off, shot = picture_at(t)
        if off is None:
            return np.full((H, W, 3), fx.NAVY_DEEP, np.float32), (W / 2, H / 2), False
        img, focus = self.aroll(t, off, shot)
        return img, focus, True

    def frame(self, n):
        t = n / FPS
        img, focus, on_cam = self.base(t)
        # the bloom on the wall dissolves into the end card
        if DISSOLVE[0] <= t < DISSOLVE[1]:
            u = ease("io", (t - DISSOLVE[0]) / (DISSOLVE[1] - DISSOLVE[0]))
            off, shot = picture_at(min(t, edl.PICTURE[4][1] - 1e-3)) if t < 48.25 else (edl.PICTURE[4][2], "F")
            fin, _ = self.aroll(t, off, shot)
            end = self.full(max(t, 48.25), "end_card")
            img = fin * (1 - u) + end * u
        img = fx.grade_scene(img)

        # hits and transitions
        zk = max([a * decay(t, tz, 0.09) for tz, a in ZBLUR if tz <= t < tz + 0.3], default=0.0)
        if zk > 0.02:
            img = fx.zoom_blur(img, zk, *focus)
        for t0, t1, k in GLITCH:
            if t0 <= t < t1:
                img = fx.glitch(img, n, k)
                img = fx.chroma(img, 10 * k)
        cpx = sum(px * decay(t, tc, d) for tc, px, d in CHROMA)
        img = fx.chroma(img, cpx)
        for t0, t1, k, side in LEAK:
            if t0 <= t < t1:
                u = (t - t0) / (t1 - t0)
                img = fx.light_leak(img, t, k * np.sin(np.pi * min(1.0, u * 1.6)) ** 1.2, True, side)
        for tf, rgb, a, d in FLASH:
            img = fx.flash(img, rgb, a * decay(t, tf, d))

        img = fx.vignette(img, 0.22 if on_cam else 0.12)
        img = fx.grain(img, n, 0.016 if on_cam else 0.010)
        if on_cam:
            img = CAP.over_premul(img, self.caps.render(t))
        return np.clip(img, 0, 1)


def encoder(path):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS),
         "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
         "-preset", "slow", "-crf", "15", "-profile:v", "high", "-color_range", "tv", "-colorspace", "bt709",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", path], stdin=subprocess.PIPE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills")
    ap.add_argument("--part")
    ap.add_argument("--join", type=int)
    ap.add_argument("--range")
    a = ap.parse_args()
    os.makedirs(PIC, exist_ok=True)
    if a.join:
        lst = os.path.join(PIC, "parts.txt")
        with open(lst, "w") as fh:
            for i in range(a.join):
                fh.write(f"file 'part_{i}.mp4'\n")
        out = os.path.join(PIC, "picture.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        "-movflags", "+faststart", out], check=True)
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
        print("->", out, n, "frames")
        return
    c = Comp()
    if a.stills:
        vd = os.path.join(ROOT, "renders/verify")
        os.makedirs(vd, exist_ok=True)
        for s in a.stills.split(","):
            n = int(round(float(s) * FPS))
            im = c.frame(n)
            p = os.path.join(vd, f"still_{float(s):06.2f}.jpg")
            cv2.imwrite(p, cv2.cvtColor((im * 255 + 0.5).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 93])
            print("still", p)
        return
    n0, n1 = 0, edl.TOTAL
    out = os.path.join(PIC, "picture.mp4")
    if a.part:
        i, k = (int(x) for x in a.part.split("/"))
        n0, n1 = edl.TOTAL * i // k, edl.TOTAL * (i + 1) // k
        out = os.path.join(PIC, f"part_{i}.mp4")
    if a.range:
        r0, r1 = (float(x) for x in a.range.split("-"))
        n0, n1 = int(round(r0 * FPS)), int(round(r1 * FPS))
        out = os.path.join(PIC, f"range_{r0:.1f}-{r1:.1f}.mp4")
    enc = encoder(out)
    for n in range(n0, n1):
        enc.stdin.write((c.frame(n) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
        if (n - n0) % 60 == 0:
            print(f"  frame {n} ({n / FPS:.1f}s)", flush=True)
    enc.stdin.close()
    enc.wait()
    print("->", out, n1 - n0, "frames")


if __name__ == "__main__":
    main()
