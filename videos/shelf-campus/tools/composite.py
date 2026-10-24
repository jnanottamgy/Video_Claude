"""Composite the SHELF CAMPUS founders reel.

Per output frame (tools/edl.py says what plays, tools/direction.py what happens):
  talking heads: source frame -> grade (look) -> wall re-lit behind the person (police lights / navy /
    clean day) -> camera (push, punch, shake; centred on the sunglasses) -> "behind" graphics under the
    person matte -> rim light on the navy wall -> front graphics -> censor bar, glints, flashes,
    shockwaves, chroma, glitch, zoom blur -> bloom, vignette, grain -> captions LAST
  the two-founders poster: graphics background -> both founders cut out (graded, rim-lit, drifting)
    -> its text layer
  full-frame graphics (logo reveal, demo, end card): the slot's own frames + a little grain
Encodes H.264 BT.709 limited range.

  python3 tools/composite.py --stills 0.1,11.8,25.7     # QA frames -> renders/verify/
  python3 tools/composite.py --range 0-10                # one part (renders/parts/)
  python3 tools/composite.py --jobs 3                    # the whole reel, in parallel parts -> renders/video.mp4
"""
import argparse
import os
import subprocess
import sys
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import captions as CAP  # noqa: E402
import direction as DR  # noqa: E402
import edl  # noqa: E402
import fxlib as fx  # noqa: E402
import split_people as SP  # noqa: E402

W, H, FPS = edl.W, edl.H, edl.FPS
os.chdir(edl.ROOT)
DECODE_VF = "scale=in_color_matrix=bt709:in_range=tv:out_range=full"
NSRC = 2165

# overlay windows: (slot, window start s, layer[, opts]); opts: until=t (cut it off at t)
OVERLAYS = [
    ("storage_behind", 0.000, "behind"),
    ("storm_behind", edl.SEGMENTS[1]["out0"], "behind"),
    ("evidence_behind", DR.o0("A3a"), "behind", dict(until=DR.o0("A5"))),
    ("hook_title", 0.000, "front"),
    ("stamps", DR.o0("A5"), "front", dict(until=DR.o0("B1"))),
    ("name_j_behind", DR.o0("B1"), "behind", dict(until=DR.o0("B2"), screen=True)),   # screen-locked: the punch-ins move
    ("name_k_behind", DR.o0("B2"), "behind", dict(until=DR.o0("B3"), screen=True)),   # the founder, never push the name off-frame
    ("lowers", DR.o0("B1"), "front", dict(until=DR.o0("B3"))),
    ("poster_bg", DR.o0("B3"), "full", dict(until=DR.o0("B4"))),
    ("poster_text", DR.o0("B3"), "front", dict(until=DR.o0("B4"))),
    ("minds_behind", DR.o0("B4"), "behind", dict(until=DR.o0("B5"))),
    ("built_behind", DR.o0("B5"), "behind", dict(until=edl.R)),
    ("logo_reveal", edl.R, "full", dict(until=DR.o0("C2"))),
    ("memory_behind", DR.o0("C2"), "behind", dict(until=DR.o0("C3"))),
    ("whatsapp_behind", DR.o0("C3"), "behind", dict(until=DR.o0("D"))),
    ("demo", DR.o0("D"), "full", dict(until=DR.o0("E1"))),
    ("payoff", DR.o0("E1"), "front", dict(until=DR.o0("F1"))),
    ("cta", DR.o0("F1"), "front", dict(until=DR.o0("F3"))),
    ("end_card", DR.o0("F3"), "full"),
]


def overlay_index():
    idx = []
    for slot, t0, layer, *rest in OVERLAYS:
        d = f"slots/{slot}/renders/png"
        if not os.path.isdir(d):
            continue
        opts = rest[0] if rest else {}
        n = len([f for f in os.listdir(d) if f.endswith(".png")])
        f0 = int(round(t0 * FPS))
        end = f0 + n
        if "until" in opts:
            end = min(end, int(round(opts["until"] * FPS)))
        idx.append((d, f0, n, layer + ("_screen" if opts.get("screen") else ""), end))
    return idx


def layer_frames(index, n, layer):
    out = []
    for d, f0, cnt, lay, end in index:
        if lay == layer and f0 <= n < end:
            im = fx.load_rgba(f"{d}/frame_{min(n - f0 + 1, cnt):06d}.png")
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
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, f - 0.01) / FPS:.6f}", "-i", edl.SRC, "-vf", DECODE_VF,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
        self.pos = f

    def get(self, f):
        f = int(min(max(f, 0), NSRC - 1))
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


def matte(f):
    for k in (f, f + 1, f - 1, f + 2, f - 2):
        p = f"renders/mattes/f_{k:05d}.png"
        if os.path.exists(p):
            return cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32)[..., None] / 255
    return np.zeros((H, W, 1), np.float32)


_glasses = {}


def glasses(f, rgb8):
    """Centre of the yellow sunglasses in source frame f (the founders' eyes)."""
    if f in _glasses:
        return _glasses[f]
    hsv = cv2.cvtColor(rgb8[600:1250], cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] >= 20) & (hsv[..., 0] <= 34) & (hsv[..., 1] > 110) & (hsv[..., 2] > 110)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    p, best = None, 0
    for k in range(1, n):                       # the frames are a wide, thin ring: books and lamps are not
        w, h, a = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT], stats[k, cv2.CC_STAT_AREA]
        if a > 300 and w > 2.2 * h and w > 140 and a > best:
            p, best = (float(cent[k][0]), float(cent[k][1]) + 600), a
    _glasses[f] = p or (780.0, 980.0)
    return _glasses[f]


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def env(t, t0, decay):
    return float(np.exp(-(t - t0) / decay)) if t >= t0 else 0.0


def camera_at(t, seg, focus):
    """Affine matrix for the scene camera at output time t (centred on `focus`)."""
    cx, cy = focus
    s0, s1 = DR.SHOTS.get(seg["id"], (1.0, 1.0))
    u = (t - seg["out0"]) / max(seg["out1"] - seg["out0"], 1e-6)
    s = s0 + (s1 - s0) * ease_io(u)
    if seg["id"] == "A1":                           # frame 1 slams in, then the slow push takes over
        st, sv = DR.OPEN_SETTLE
        k = ease_out(t / st)
        s = s0 + (sv - s0) * k if t < st else sv + (s1 - sv) * ease_io((t - st) / (seg["out1"] - st))
    M = np.vstack([fx.camera_matrix(s, cx, cy), [0, 0, 1]])
    for tp, amt, att, hold, rel in DR.PUNCH:
        inside = seg["out0"] - 1e-6 <= tp < seg["out1"]
        held = seg["kind"] == "freeze" and seg["out0"] - 2.0 <= tp < seg["out0"]      # a punch held into a freeze
        if not (inside or held) or t < tp:
            continue
        uu = t - tp
        if att > 0 and uu < att:
            k = ease_out(uu / att)
        elif uu < att + hold or rel == 0:
            k = 1.0
        elif uu < att + hold + rel:
            k = 1 - ease_io((uu - att - hold) / rel)
        else:
            continue
        M = np.vstack([fx.camera_matrix(1 + amt * k, cx, cy), [0, 0, 1]]) @ M
    dx = dy = rot = 0.0
    for i, (ts, amp, decay, freq) in enumerate(DR.SHAKE):
        if ts <= t < ts + 5 * decay:
            a, b, r = fx.shake_offset(t, ts, amp, decay, freq, seed=i)
            dx, dy, rot = dx + a, dy + b, rot + r
    if dx or dy or rot:
        M = np.vstack([fx.camera_matrix(1.0, W / 2, H / 2, dx, dy, rot), [0, 0, 1]]) @ M
    return M[:2]


def look_at(t):
    for t0, t1, g, wall in DR.LOOKS:
        if t0 - 1e-6 <= t < t1:
            return g, wall
    return "day", None


class Comp:
    def __init__(self):
        self.src = Source()
        self.overlays = overlay_index()
        self._people = None

    def people(self):
        """The poster's two cut-outs, graded once (night look) and rim-lit."""
        if self._people is None:
            out = {}
            for who in ("K", "J"):
                n, s, dx, dy = SP.LAYOUT[who]
                rgb = self.src.get(n).astype(np.float32) / 255
                rgb = fx.grade(rgb, "night")
                m = matte(n)[..., 0]
                m = cv2.GaussianBlur(cv2.erode(m, np.ones((3, 3), np.uint8)), (0, 0), 1.2)   # choke the wall-coloured fringe
                rgb = fx.rim(rgb, m[..., None], (0.55, 0.75, 1.0), 0.5)
                out[who] = SP.cutout(who, rgb, m)
            self._people = out
        return self._people

    def poster(self, n, t, seg):
        bgs = layer_frames(self.overlays, n, "full")
        img = bgs[0][..., :3] if bgs else np.zeros((H, W, 3), np.float32) + np.array([0.02, 0.04, 0.09], np.float32)
        u = (t - seg["out0"]) / (seg["out1"] - seg["out0"])
        for who, (dxp, sc) in (("K", (14, 1.035)), ("J", (-14, 1.045))):
            lay = self.people()[who]
            M = fx.camera_matrix(1 + (sc - 1) * ease_io(u), W / 2, H, dxp * ease_io(u), 0)
            lay = cv2.warpAffine(lay, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            img = fx.over(img, lay)
        for layer in layer_frames(self.overlays, n, "front"):
            img = fx.over(img, layer)
        return img

    def footage(self, n, t, seg):
        f = int(round((seg["src"] + (t - seg["out0"])) * FPS)) if seg["kind"] == "talk" else int(round(seg["src"] * FPS))
        rgb8 = self.src.get(f)
        g, wall = look_at(t)
        img = fx.grade(rgb8.astype(np.float32) / 255, g)
        m = matte(f)
        if wall == "police":
            img = fx.wall_police(img, m, t)
        elif wall == "night":
            gx, gy = glasses(f, rgb8)
            img = fx.wall_night(img, m, (gx, gy - 80))
        elif wall == "day":
            img = fx.wall_day(img, m)
        if seg["kind"] == "freeze" and seg["id"] == "A5":           # the case-file freeze: cold, contrasty
            img = fx.desat(img, 0.72)
            img = np.clip((img - 0.5) * 1.18 + 0.5 + np.array([-0.01, 0.0, 0.02], np.float32), 0, 1)
        if seg["kind"] == "freeze" and seg["id"] == "E4f":
            img = fx.desat(img, 0.35)
        focus = glasses(f, rgb8)
        M = camera_at(t, seg, focus)
        img = fx.warp(img, M)
        mw = fx.warp(m, M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)
        if mw.ndim == 2:
            mw = mw[..., None]
        behind = layer_frames(self.overlays, n, "behind")
        locked = layer_frames(self.overlays, n, "behind_screen")
        if behind or locked:
            bg = img
            for layer in behind:      # on the wall: moves with the camera; premultiplied so edges stay clean
                a = fx.warp(layer[..., 3], M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)[..., None]
                pm = fx.warp(layer[..., :3] * layer[..., 3:4], M, cv2.BORDER_CONSTANT, cv2.INTER_LINEAR)
                bg = pm + bg * (1 - a)
            for layer in locked:      # behind the person but fixed to the screen (the giant names)
                bg = fx.over(bg, layer)
            img = img * mw + bg * (1 - mw)
        if wall == "night":
            img = fx.rim(img, mw, (0.55, 0.75, 1.0), 0.45)
        p = M @ np.array([focus[0], focus[1], 1.0])
        return img, (float(p[0]), float(p[1]))

    def frame(self, n):
        t = n / FPS
        seg = edl.at(t)
        eyes = (W / 2, H / 2)
        if seg["kind"] == "gfx":
            fulls = layer_frames(self.overlays, n, "full")
            img = fulls[-1][..., :3] if fulls else np.zeros((H, W, 3), np.float32)
            img = fx.grain(img, n, 0.008)
        elif seg["kind"] == "split":
            img = self.poster(n, t, seg)
        else:
            img, eyes = self.footage(n, t, seg)
            for layer in layer_frames(self.overlays, n, "front"):
                img = fx.over(img, layer)
            if DR.CENSOR[0] <= t < DR.CENSOR[1]:
                img = fx.censor(img, n, eyes[0] + DR.MOUTH_FROM_GLASSES[0], eyes[1] + DR.MOUTH_FROM_GLASSES[1])
            for tg, size, dur in DR.GLINT:
                if tg <= t < tg + dur:
                    u = (t - tg) / dur
                    img = fx.glint(img, eyes[0] + 70, eyes[1] - 18, size * (0.7 + 0.6 * u), np.sin(np.pi * u) ** 1.5)
            for ts in DR.SHOCK:
                if ts <= t < ts + 0.55:
                    img = fx.shockwave(img, t - ts, eyes[0], eyes[1])
        cpx = sum(px * env(t, tc, d) for tc, px, d in DR.CHROMA)
        img = fx.chroma(img, cpx)
        for t0, t1, k in DR.GLITCH:
            if t0 <= t < t1:
                img = fx.chroma(fx.glitch(img, n, k), 9 * k)
        for t0, t1 in DR.FLICKER:
            if t0 <= t < t1:
                img = img * (0.35 if (n % 3 == 1) else 0.85)
        zk = max([amp * env(t, tz, 0.07) for tz, amp in DR.ZBLUR if tz <= t < tz + 0.25], default=0.0)
        if zk > 0.02:
            img = fx.zoom_blur(img, zk, eyes[0], eyes[1])
        for tf, rgb, a, d in DR.FLASH:
            img = fx.flash(img, rgb, a * env(t, tf, d))
        if seg["kind"] != "gfx":
            img = fx.bloom(img, 0.80, 20, 0.12)
            img = fx.vignette(img, 0.16)
            img = fx.grain(img, n, 0.016)
        if seg["id"] not in DR.NO_CAPTIONS:
            c = CAP.frame(t, n)
            if c is not None:
                band, y0 = c
                img[y0:y0 + band.shape[0]] = fx.over(img[y0:y0 + band.shape[0]], band)
        return np.clip(img, 0, 1)


def encoder(path, crf=14):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-",
         "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
         "-profile:v", "high", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         path], stdin=subprocess.PIPE)


def render_range(args):
    n0, n1, out = args
    c = Comp()
    enc = encoder(out)
    for n in range(n0, n1):
        enc.stdin.write((c.frame(n) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
        if (n - n0) % 60 == 0:
            print(f"  [{n0}-{n1}] frame {n} ({n / FPS:.1f}s)", flush=True)
    enc.stdin.close()
    enc.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills")
    ap.add_argument("--range")
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--out", default="renders/video.mp4")
    a = ap.parse_args()
    if a.stills:
        c = Comp()
        os.makedirs("renders/verify", exist_ok=True)
        for s in a.stills.split(","):
            n = int(round(float(s) * FPS))
            im = c.frame(n)
            p = f"renders/verify/still_{float(s):06.2f}.jpg"
            cv2.imwrite(p, cv2.cvtColor((im * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print(p)
        return
    os.makedirs("renders/parts", exist_ok=True)
    if a.range:
        r0, r1 = (float(x) for x in a.range.split("-"))
        n0, n1 = int(round(r0 * FPS)), min(edl.TOTAL, int(round(r1 * FPS)))
        print(render_range((n0, n1, f"renders/parts/p_{n0:05d}-{n1:05d}.mp4")))
        return
    jobs = max(1, a.jobs)
    cuts = np.linspace(0, edl.TOTAL, jobs + 1).astype(int)
    parts = [(int(cuts[i]), int(cuts[i + 1]), f"renders/parts/p_{cuts[i]:05d}-{cuts[i + 1]:05d}.mp4") for i in range(jobs)]
    with ProcessPoolExecutor(jobs) as ex:
        outs = list(ex.map(render_range, parts))
    with open("renders/parts/list.txt", "w") as f:
        for o in outs:
            f.write(f"file '{os.path.basename(o)}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "renders/parts/list.txt", "-c", "copy",
                    "-movflags", "+faststart", a.out], check=True)
    print("->", a.out)


if __name__ == "__main__":
    main()
