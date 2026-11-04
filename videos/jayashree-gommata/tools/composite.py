"""The picture: every frame of the reel, 1080x1920 at 30 fps.

Per frame:
  - the shot's source frame, graded (tools/grade.py, v2): per-shot levels, contrast, colour, denoise and local
    contrast;
  - pushed in and cropped into the 4:3 window, inside the ticker-free area, enlarged and sharpened;
  - a gentle graduated filter on the blown skies and the window's own vignette (v2: no bloom or god rays in
    the window, they read as haze);
  - the canvas: deep temple maroon, the shot itself blurred into a soft glow, a slowly turning gold mandala and
    a warm halo behind the window;
  - the gold border with a travelling glint;
  - golden dust, falling petals (a burst on the shouted "Jai!"), the titles, a vignette and grain.

  python3 tools/composite.py --part i/N      ->  renders/parts/part_i.mp4
  python3 tools/composite.py --join N        ->  renders/picture/picture.mp4
  python3 tools/composite.py --stills T ...  ->  renders/verify/still_T.jpg (+ a contact sheet)
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402
import fx  # noqa: E402
import grade as GR  # noqa: E402
import layout as LY  # noqa: E402
import look  # noqa: E402
import media  # noqa: E402
import titles as T  # noqa: E402

W, H = edl.W, edl.H
MAROON_TOP = np.array([0.20, 0.045, 0.040], np.float32)
MAROON_MID = np.array([0.27, 0.065, 0.045], np.float32)
MAROON_BOT = np.array([0.12, 0.025, 0.020], np.float32)
GOLD = np.array([1.0, 0.80, 0.46], np.float32)
GLINT_PERIOD = 6.0
CUTS = [s_["t0"] for s_ in edl.SHOTS[1:]]


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


class Renderer:
    def __init__(self):
        self.readers = {}
        self.titles = T.Titles(edl.LYRICS)
        self.dust = fx.Dust(seed=7, n=110, n_bokeh=10)
        self.petals = fx.Petals(seed=21, burst_t=edl.JAI)
        self.mand = fx.mandala()
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        grad = np.where(yy < 0.5, MAROON_TOP + (MAROON_MID - MAROON_TOP) * (yy / 0.5),
                        MAROON_MID + (MAROON_BOT - MAROON_MID) * ((yy - 0.5) / 0.5))
        self.base = np.ascontiguousarray(np.broadcast_to(grad, (H, W, 3)), np.float32)
        gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((gx - W / 2) / 620) ** 2 + ((gy - LY.WIN_CY) / 560) ** 2)
        self.halo = (np.exp(-d ** 2 * 1.6) * 0.22)[..., None] * np.array([1.0, 0.62, 0.30], np.float32)
        wy = np.linspace(0, 1, LY.WIN_H, dtype=np.float32)[:, None, None]
        self.grad = np.clip(1 - wy / 0.55, 0, 1) ** 1.6              # the window's graduated filter, top 55%
        wx = np.linspace(-1, 1, LY.WIN_W, dtype=np.float32)[None, :, None]
        wyy = np.linspace(-1, 1, LY.WIN_H, dtype=np.float32)[:, None, None]
        self.wvig = 1 - 0.20 * np.clip(np.sqrt(wx ** 2 * 0.9 + wyy ** 2) - 0.45, 0, 1) ** 1.4   # the window's own vignette
        self.params = {}

    def reader(self, sh):
        k = sh["name"]
        if k not in self.readers:
            self.readers[k] = media.Reader(sh["src"], sh["src"] + (sh["t1"] - sh["t0"]) + 0.15)
        return self.readers[k]

    def shot_params(self, sh):
        """The shot's levels and gamma (tools/grade.py), measured once from three of its frames."""
        k = sh["name"]
        if k not in self.params:
            r = self.reader(sh)
            box = media.crop_box(r.w, r.h, sh["cx"], sh["cy"], sh["cw"], LY.ASPECT)
            x0, y0, x1, y1 = [int(round(v)) for v in box]
            d = sh["t1"] - sh["t0"]
            self.params[k] = GR.measure([r.at(sh["src"] + d * q)[y0:y1, x0:x1] for q in (0.1, 0.5, 0.9)])
        return self.params[k]

    def graded(self, src, sh):
        """The source frame graded (v2): levels, curve, colour, then denoise and local contrast (uint8)."""
        return GR.clarity_src((GR.tone(src, self.shot_params(sh)) * 255 + 0.5).astype(np.uint8))

    def window_img(self, g, sh, t):
        r = self.reader(sh)
        u = (t - sh["t0"]) / max(1e-6, sh["t1"] - sh["t0"])
        z0, z1 = sh["zoom"]
        z = z0 + (z1 - z0) * ease(u)
        box = media.crop_box(r.w, r.h, sh["cx"], sh["cy"], sh["cw"] / z, LY.ASPECT)
        win = GR.sharpen_out(media.warp(g, box, LY.WIN_W, LY.WIN_H).astype(np.float32) / 255)
        # the blown sky and white cloth: a gentle graduated filter toward the top, and the window's vignette
        L = win.max(2, keepdims=True)
        hi = np.clip((L - 0.72) / 0.28, 0, 1)
        win = win * (1 - 0.20 * self.grad * hi) + np.array([0.50, 0.40, 0.30], np.float32) * 0.20 * self.grad * hi
        win = win * self.wvig
        return np.clip(win, 0, 1), box

    def background(self, g, box, t):
        blur = LY.background(g, box, darken=1.0)
        bg = self.base + blur * 0.30
        bg = 1 - (1 - bg) * (1 - self.halo)
        ang = 0.6 * t
        D = self.mand.shape[0]
        m = cv2.getRotationMatrix2D((D / 2, D / 2), ang, 1.0)
        m[0, 2] += W / 2 - D / 2
        m[1, 2] += LY.WIN_CY - D / 2
        a = cv2.warpAffine(self.mand, m, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)[..., None] * 0.22
        return np.clip(bg * (1 - a) + GOLD * a, 0, 1)

    def frame(self, t, n):
        sh = edl.shot_at(t)
        src = self.reader(sh).at(sh["src"] + (t - sh["t0"]))
        g = self.graded(src, sh)
        win, box = self.window_img(g, sh, t)
        # the "Jai!": a zoom burst in the window
        if edl.JAI <= t < edl.JAI + 0.35:
            win = _zoom_blur(win, 0.10 * (1 - (t - edl.JAI) / 0.35))
        if edl.JAI <= t < 29.40:                                  # the window dims behind the big ಜೈ
            win = win * (1 - 0.42 * ease((t - edl.JAI) / 0.2) * (1 - ease((t - 29.1) / 0.3)))
        bg = self.background(g, box, t)
        cut = max([0.0] + [math.exp(-(t - c) / 0.22) for c in CUTS if 0 <= t - c < 0.9])
        fr = LY.compose(bg, win, glint=(t / GLINT_PERIOD) % 1.0, pulse=cut)
        fr = fx.screen(fr, self.dust.layer(t, 0.45, bokeh_amount=0.6) * 0.55)
        dens = float(np.interp(t, [p[0] for p in edl.PETALS], [p[1] for p in edl.PETALS]))
        self.petals.draw(fr, t, min(dens, 1.0))
        # flash on the "Jai!"
        if edl.JAI <= t < edl.JAI + 0.6:
            f = math.exp(-(t - edl.JAI) / 0.11) * 0.5
            fr = fr + (1 - fr) * f * np.array([1.0, 0.93, 0.80], np.float32)
            lk = fx.leak(t - edl.JAI, 11, 0.55 * (1 - (t - edl.JAI) / 0.6))
            if lk is not None:
                fr = fx.screen(fr, lk)
        # the titles
        fr = self.titles.artist(fr, t, -0.55, edl.DURATION, hi=edl.S[2])
        for ly in edl.LYRICS:
            if ly["t0"] <= t < ly["t1"]:
                fr = self.titles.lyric(fr, t, ly)
        for c in edl.CARDS:
            if c["t0"] <= t < c["t1"]:
                if c["kind"] == "event":
                    fr = self.titles.event(fr, t, c["t0"], c["t1"])
                elif c["kind"] == "jai":
                    fr = self.titles.jai_card(fr, t, c["t0"], c["t1"], LY.WIN_CY)
                elif c["kind"] == "end":
                    fr = self.titles.end(fr, t, c["t0"], c["t1"])
        fr = look.vignette(fr, 0.32, tint=(0.05, 0.01, 0.005))
        fr = look.grain(fr, 1000 + n, 0.022)
        return (np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)


def _zoom_blur(x, amount, n=8):
    if amount <= 0.003:
        return x
    h, w = x.shape[:2]
    acc = np.zeros_like(x)
    for j in range(n):
        s = 1 + amount * j / (n - 1)
        m = np.float32([[s, 0, w / 2 * (1 - s)], [0, s, h / 2 * (1 - s)]])
        acc += cv2.warpAffine(x, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def encode(path, w=W, h=H):
    return subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                             "-framerate", str(edl.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14",
                             "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                             "-color_trc", "bt709", path], stdin=subprocess.PIPE)


def main():
    a = sys.argv[1:]
    if a[0] == "--stills":
        R = Renderer()
        os.makedirs(os.path.join(edl.ROOT, "renders/verify"), exist_ok=True)
        ims = []
        for s in a[1:]:
            t = float(s)
            im = R.frame(t, int(t * edl.FPS))
            p = os.path.join(edl.ROOT, f"renders/verify/still_{t:06.2f}.jpg")
            cv2.imwrite(p, cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
            ims.append(cv2.resize(im, (360, 640), interpolation=cv2.INTER_AREA))
            print(p)
        cols = min(6, len(ims))
        while len(ims) % cols:
            ims.append(np.zeros_like(ims[0]))
        sheet = np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)])
        cv2.imwrite(os.path.join(edl.ROOT, "renders/verify/stills_sheet.jpg"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
        return
    if a[0] == "--part":
        i, n = map(int, a[1].split("/"))
        frames = range(edl.TOTAL)
        lo, hi = edl.TOTAL * i // n, edl.TOTAL * (i + 1) // n
        os.makedirs(os.path.join(edl.ROOT, "renders/parts"), exist_ok=True)
        R = Renderer()
        enc = encode(os.path.join(edl.ROOT, f"renders/parts/part_{i}.mp4"))
        for k in frames[lo:hi]:
            enc.stdin.write(R.frame(k / edl.FPS, k).tobytes())
        enc.stdin.close()
        enc.wait()
        print(f"part {i}: frames {lo}-{hi - 1}")
        return
    if a[0] == "--join":
        n = int(a[1])
        lst = os.path.join(edl.ROOT, "renders/parts/parts.txt")
        open(lst, "w").write("".join(f"file 'part_{i}.mp4'\n" for i in range(n)))
        os.makedirs(os.path.join(edl.ROOT, "renders/picture"), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        os.path.join(edl.ROOT, "renders/picture/picture.mp4")], check=True)
        print("joined")


if __name__ == "__main__":
    main()
