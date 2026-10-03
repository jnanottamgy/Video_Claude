"""Composite the S.H.E.L.F reel recut.

Per output frame (edl.py says which source frames, direction.py says what happens):
  source frame(s)  -> old burned-in captions inpainted -> grade (PROBLEM / S.H.E.L.F mood)
  -> camera (push, punch, shake) -> whip smear at marked cuts -> sunglasses glint
  -> freeze treatment + "behind" words, then the person matte re-laid on top (words sit behind him)
  -> front overlays (HUD, notifications, tiles, name cards) -> looks (red alarm, chroma, glitch,
     flash, light leak, VHS, fade) -> vignette + grain -> captions LAST
and encodes H.264 BT.709 (limited range, the safe delivery default).

  python3 tools/composite.py                     # full render -> renders/SHELF_reel_video.mp4
  python3 tools/composite.py --stills 13.3,45.2  # QA frames -> renders/verify/
  python3 tools/composite.py --range 40.0-48.0   # partial render (preview mp4)
"""
import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import direction as D  # noqa: E402
import edl  # noqa: E402
import fxlib as fx  # noqa: E402

W, H, FPS = 1080, 1920, edl.FPS
SRC = "renders/source.mp4"
DECODE_VF = "scale=in_color_matrix=bt709:in_range=full:out_range=full"
FOUNDERS_AT = edl.BY_ID["P6a"]["o"] / FPS

# overlay windows: (png dir, window start in output s, layer)
OVERLAYS = [
    ("slots/notifs/storm_hook/renders/png", 0.000, "front"),
    ("slots/hud/hud/renders/png", 14.300, "front"),
    ("slots/notifs/cards/renders/png", 30.000, "front"),
    ("slots/notifs/storm/renders/png", 44.600, "front"),
    ("slots/titles/shelf_behind/renders/png", 54.100, "behind"),
    ("slots/titles/jnanottam_behind/renders/png", 60.600, "behind"),
    ("slots/titles/namecard_j/renders/png", 63.400, "front"),
    ("slots/titles/kartik_behind/renders/png", 66.100, "behind"),
    ("slots/titles/namecard_k/renders/png", 68.633, "front"),
    ("slots/tiles/problem/renders/png", 70.100, "front"),
    ("slots/titles/simple_behind/renders/png", 85.450, "behind"),
    ("slots/titles/shelf2_behind/renders/png", 87.950, "behind"),
    ("slots/tiles/oneplace/renders/png", 89.000, "front"),
]
NO_CAPTION_SEGS = {"P1a", "P1b", "P1c", "P1d", "P9b", "END"}


def overlay_index():
    idx = []
    for d, t0, layer in OVERLAYS:
        if not os.path.isdir(d):
            print(f"  (missing overlay {d})")
            continue
        n = len([f for f in os.listdir(d) if f.endswith(".png")])
        idx.append((d, int(round(t0 * FPS)), n, layer))
    cap = []
    if os.path.exists("renders/captions/manifest.json"):
        for m in json.load(open("renders/captions/manifest.json")):
            d = f"{m['dir']}/renders/png"
            if os.path.isdir(d):
                cap.append((d, m["start_frame"], len(os.listdir(d)), "caption"))
    return idx, cap


def layer_frames(index, n, layer):
    out = []
    for d, f0, cnt, lay in index:
        if lay == layer and f0 <= n < f0 + cnt:
            im = fx.load_rgba(f"{d}/frame_{n - f0 + 1:06d}.png")
            if im is not None:
                out.append(im)
    return out


class Source:
    """Sequential decoder with restarts on seeks, plus a small frame cache."""

    def __init__(self):
        self.p, self.pos, self.cache = None, -1, OrderedDict()

    def _open(self, f):
        if self.p:
            self.p.kill()
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{(f + 0.5) / FPS:.4f}", "-i", SRC, "-vf", DECODE_VF,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
        self.pos = f

    def get(self, f):
        f = int(min(max(f, 0), 3594))
        if f in self.cache:
            return self.cache[f]
        if self.p is None or f < self.pos or f > self.pos + 45:
            self._open(f)
        while self.pos <= f:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                raise RuntimeError(f"decode ended before frame {f}")
            fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.cache[self.pos] = fr
            self.pos += 1
            while len(self.cache) > 12:
                self.cache.popitem(last=False)
        return self.cache[f]


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def shot_at(t):
    for s in D.SHOTS:
        if s[0] <= t < s[1]:
            return s
    return D.SHOTS[-1]


def camera_at(t):
    """Affine matrix for the scene camera at output time t."""
    t0, t1, (s0, s1), (cx, cy) = shot_at(t)
    s = s0 + (s1 - s0) * ease_io((t - t0) / max(t1 - t0, 1e-6))
    M = np.vstack([fx.camera_matrix(s, cx, cy), [0, 0, 1]])
    for tp, amt, (px, py), att, hold, rel in D.PUNCH:
        if not (t0 <= tp < t1) or t < tp:
            continue
        u = t - tp
        if u < att:
            k = ease_out(u / att)
        elif u < att + hold or rel == 0:
            k = 1.0
        elif u < att + hold + rel:
            k = 1 - ease_io((u - att - hold) / rel)
        else:
            continue
        M = np.vstack([fx.camera_matrix(1 + amt * k, px, py), [0, 0, 1]]) @ M
    dx = dy = rot = 0.0
    for i, (ts, amp, decay, freq) in enumerate(D.SHAKE):
        if t0 <= ts < t1 and ts <= t < ts + 5 * decay:
            a, b, r = fx.shake_offset(t, ts, amp, decay, freq, seed=i)
            dx, dy, rot = dx + a, dy + b, rot + r
    if dx or dy or rot:
        M = np.vstack([fx.camera_matrix(1.0, W / 2, H / 2, dx, dy, rot), [0, 0, 1]]) @ M
    return M[:2]


def warp(img, M, border=cv2.BORDER_REFLECT101, interp=cv2.INTER_CUBIC):
    if np.allclose(M, [[1, 0, 0], [0, 1, 0]]):
        return img
    return cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=border)


def env(t, t0, decay):
    return np.exp(-(t - t0) / decay) if t >= t0 else 0.0


class Comp:
    def __init__(self):
        self.src = Source()
        self.overlays, self.captions = overlay_index()
        self.prev_mask = None
        self.inpainted = {}

    # -- footage --
    def clean(self, f, seg_id, temporal=True):
        """Source frame f as uint8 RGB with the old captions inpainted (cached for freezes).
        `temporal`: OR in the previous frame's caption mask (consecutive frames only)."""
        if f in self.inpainted:
            return self.inpainted[f]
        fr = self.src.get(f)
        if seg_id not in NO_CAPTION_SEGS:
            fr, self.prev_mask = fx.remove_captions(fr, self.prev_mask if temporal else None)
        else:
            self.prev_mask = None
        if len(self.inpainted) > 6:
            self.inpainted.pop(next(iter(self.inpainted)))
        self.inpainted[f] = fr
        return fr

    def footage(self, n):
        seg, pos, span = edl.src_frame(n)
        if seg["kind"] == "rewind":
            k = n - seg["o"]
            e = ease_io(k / (seg["n"] - 1))
            f = int(round(seg["a"] + (seg["b"] - seg["a"]) * e))
            return seg, f, self.clean(f, "H2", temporal=False).astype(np.float32) / 255
        if span and span > 1.0:                       # speed-up: blend the source frames it covers
            a, b = pos, pos + span
            acc, wsum = 0, 0
            for f in range(int(np.floor(a)), int(np.ceil(b))):
                w = min(b, f + 1) - max(a, f)
                if w > 0:
                    acc = acc + self.clean(f, seg["id"]).astype(np.float32) * w
                    wsum += w
            return seg, int(pos), acc / wsum / 255
        f = int(round(pos))
        return seg, f, self.clean(f, seg["id"]).astype(np.float32) / 255

    # -- one frame --
    def frame(self, n):
        t = n / FPS
        seg, f, img = self.footage(n)
        mood = 0.0 if t < FOUNDERS_AT else 1.0
        img = fx.grade(img, mood)
        M = camera_at(t)
        img = warp(img, M)

        # whip smear across marked cuts (2 frames either side)
        for tw, dxn in D.WHIP:
            k = 1 - abs(t - tw) * FPS / 2.5
            if k > 0:
                L = int(70 * k) | 1
                kern = np.zeros((1, L), np.float32)
                kern[0, :] = 1.0 / L
                img = cv2.filter2D(img, -1, kern, borderType=cv2.BORDER_REFLECT101)
                img = np.roll(img, int(dxn * 30 * k * (1 if t < tw else -1)), axis=1)

        for tg, gx, gy, size, dur in D.GLINT:
            if tg <= t < tg + dur:
                u = (t - tg) / dur
                k = np.sin(np.pi * u) ** 1.5
                p = M @ np.array([gx, gy, 1.0])
                img = fx.glint(img, p[0], p[1], size * (0.7 + 0.6 * u), k)

        # freeze treatment and behind-words, with the person matte laid back on top
        frz = next(((a, b, mf) for a, b, mf in D.FREEZE if a <= t < b), None)
        behind = layer_frames(self.overlays, n, "behind")
        if frz or behind:
            mf = frz[2] if frz else f
            mpath = f"renders/mattes/f_{mf:05d}.png"
            matte = cv2.imread(mpath, cv2.IMREAD_GRAYSCALE) if os.path.exists(mpath) else None
            m = warp(matte.astype(np.float32) / 255, M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)[..., None] if matte is not None else None
            bg = img
            if frz:
                u = (t - frz[0]) / 0.18
                k = min(1.0, max(0.0, u))
                l = bg.mean(axis=2, keepdims=True)
                bg = bg * (1 - k) + (l * 0.85 + bg * 0.15) * 0.42 * k
            for layer in behind:      # lives in the scene: moves with the camera (premultiplied, so edges stay clean)
                a = warp(layer[..., 3], M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)[..., None]
                pm = warp(layer[..., :3] * layer[..., 3:4], M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)
                bg = pm + bg * (1 - a)
            if m is not None:
                img = img * m + bg * (1 - m)
                if frz:
                    edge = np.clip(m[..., 0] - cv2.erode(m[..., 0], np.ones((5, 5), np.uint8)), 0, 1)
                    rim = cv2.GaussianBlur(edge, (0, 0), 3)[..., None] * np.array([0.75, 0.88, 1.0], np.float32)
                    img = fx.screen(img, np.clip(rim * 1.6, 0, 1))
            else:
                img = bg

        for layer in layer_frames(self.overlays, n, "front"):
            img = fx.over(img, layer)
        if seg["kind"] == "rewind":            # the cold open's notification storm rewinds with the tape
            hook = next((o for o in self.overlays if o[0].startswith("slots/notifs/storm_hook")), None)
            if hook:
                k = (n - seg["o"]) / (seg["n"] - 1)
                idx = int(round((hook[2] - 1) * (1 - ease_io(k)))) + 1
                layer = fx.load_rgba(f"{hook[0]}/frame_{idx:06d}.png")
                if layer is not None:
                    img = fx.over(img, layer)

        # looks
        for t0, t1, k in D.RED:
            if t0 <= t < t1:
                pulse = 0.55 + 0.45 * np.sin(2 * np.pi * 1.25 * (t - t0)) ** 2
                img = fx.red_alarm(img, k * pulse * 6)
        cpx = sum(px * env(t, tc, d) for tc, px, d in D.CHROMA)
        img = fx.chroma(img, cpx)
        for t0, t1, k in D.GLITCH:
            if t0 <= t < t1:
                img = fx.glitch(img, n, k)
                img = fx.chroma(img, 10 * k)
        for t0, t1, k, warm in D.LEAK:
            if t0 <= t < t1:
                u = (t - t0) / (t1 - t0)
                img = fx.light_leak(img, t, k * np.sin(np.pi * u), warm)
        for t0, t1 in D.VHS:
            if t0 <= t < t1:
                img = fx.vhs(img, n)
                img = self.osd(img, n)
        for tf, rgb, a, d in D.FLASH:
            img = fx.flash(img, rgb, a * env(t, tf, d))
        for t0, t1 in D.FADE:
            if t >= t0:
                img = img * (1 - min(1.0, (t - t0) / (t1 - t0)))

        img = fx.vignette(img, 0.18)
        img = fx.grain(img, n, 0.020)
        for layer in layer_frames(self.captions, n, "caption"):
            img = fx.over(img, layer)
        return img

    def osd(self, img, n):
        """VHS on-screen display during the rewind: blinking '<< REW' top-left."""
        if (n // 4) % 2 == 0:
            o = (img * 255).astype(np.uint8)
            cv2.putText(o, "<< REW", (70, 300), cv2.FONT_HERSHEY_DUPLEX, 2.4, (235, 235, 235), 5, cv2.LINE_AA)
            img = o.astype(np.float32) / 255
        return img


def encoder(path):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-",
         "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
         "-profile:v", "high", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-movflags", "+faststart", path], stdin=subprocess.PIPE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills")
    ap.add_argument("--range")
    ap.add_argument("--out", default="renders/SHELF_reel_video.mp4")
    a = ap.parse_args()
    c = Comp()
    if a.stills:
        os.makedirs("renders/verify", exist_ok=True)
        for s in a.stills.split(","):
            n = int(round(float(s) * FPS))
            im = c.frame(n)
            cv2.imwrite(f"renders/verify/still_{float(s):07.2f}.jpg", cv2.cvtColor((im * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            print("still", s)
        return
    n0, n1 = 0, edl.TOTAL
    out = a.out
    if a.range:
        r0, r1 = (float(x) for x in a.range.split("-"))
        n0, n1 = int(round(r0 * FPS)), int(round(r1 * FPS))
        out = a.out.replace(".mp4", f"_{r0:.1f}-{r1:.1f}.mp4")
    enc = encoder(out)
    for n in range(n0, n1):
        enc.stdin.write((c.frame(n) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0:
            print(f"  frame {n}/{n1} ({n / FPS:.1f}s)", flush=True)
    enc.stdin.close()
    enc.wait()
    print("->", out)


if __name__ == "__main__":
    main()
