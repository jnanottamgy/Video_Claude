"""REEL 2 ("REDLINE"): the 10.7 s edit to renders/audio/reel2.wav. Velocity edits on the rally cars (full speed with
real motion blur, a sudden drop into smooth slow motion while graphics lock onto the car, full speed out), and every
transition carries the motion of the shot it leaves.

  EDL=edl_v2 python3 tools/render.py ...      (see render.py; the picture goes to renders/picture_v2/)

The audio (85.9 BPM, 0.69875 s beats, drop on the 808 at 4.275):
  0.00-4.27  melodic intro, no drums; pitch rise 3.58-3.9; a near-silent gap 4.0-4.27
  4.275      DROP (808)          4.974 snare        6.248 808 + snare 6.35      7.07 808 retrigger
  7.768      snare, then the 808 drops out: a break with a whistle line to 8.8
  9.051      808 back (the climax)   9.16 snare   808 glides 9.5 / 9.9   10.563 last snare   10.71 end
"""
import functools
import math
import os

import cv2
import numpy as np

import fx2
import gfx
import look
from fx2 import speedmap
from media import FPS, H, W, frame_of, path

DURATION = 10.70
OUT = "renders/picture_v2"
BEAT = 0.69875
# the music's hits (exact, for the sound design) and the same moments snapped to the start of the frame that
# contains them (for the picture: a cut, a flash or a shake lands on that frame, never one late)
AUDIO = dict(DROP=4.275, SN1=4.974, B3=5.672, HIT2=6.248, RT=7.070, SN2=7.768, B7=8.467, HIT3=9.051, E1=9.515,
             E2=9.864, E3=10.214, SN3=10.563)


def snap(t):
    return frame_of(t) / FPS


DROP, SN1, B3, HIT2, RT, SN2, B7, HIT3, E1, E2, E3, SN3 = [snap(AUDIO[k]) for k in (
    "DROP", "SN1", "B3", "HIT2", "RT", "SN2", "B7", "HIT3", "E1", "E2", "E3", "SN3")]
C1, C2, C3 = snap(1.479), snap(2.178), snap(2.877)          # the intro cuts, on the beat
END = 10.667                       # black on the last frame
RED, WHITE = gfx.RED, gfx.WHITE

SHOTS, SPECS = [], {}


def shot(sid, t0, t1, **kw):
    s = dict(id=sid, t0=t0, t1=t1, F0=frame_of(t0), F1=frame_of(t1), **kw)
    s.setdefault("layout", "full")
    s.setdefault("fx", [])
    SHOTS.append(s)
    SPECS[sid] = s
    return s


def word(t, text, pos, size=300, color=WHITE, font=gfx.F_BIG, behind=False, until=None, **kw):
    if "from_" in kw:
        kw["from"] = kw.pop("from_")
    d = dict(t=t, text=text, pos=pos, size=size, color=color, font=font, behind=behind, **kw)
    if until is not None:
        d["until"] = until
    return d


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# =========================================================================================== overlays

def slow_onset(spec):
    """When a velocity edit drops into slow motion (the first key at <= 0.5x after a fast one)."""
    s = spec.get("src")
    segs = getattr(s, "segs", None)
    if not segs:
        return None
    for (ta, va), (tb, vb) in zip(segs, segs[1:]):
        if va > 1.0 and vb <= 0.5:
            return tb
    return None


def velo(direction=-1, lines=True, pulse=True, warp=False, wc=(W / 2, H / 2)):
    """Speed lines while the shot runs fast (streaming against the car's travel), a cold 'time drops' pulse the
    instant it falls into slow motion, and radial warp streaks for head-on shots."""
    def fx(img, spec, t, f, m, R):
        sp = fx2.speed_of(spec, t, None)
        a = float(np.clip((sp - 1.3) / 1.0, 0, 1))
        if lines and a > 0:
            img = fx2.speed_lines(img, t, -direction, 0.75 * a, seed=spec["F0"])
        if warp and a > 0:
            img = fx2.warp_lines(img, t, 0.7 * a, wc[0], wc[1], seed=spec["F0"])
        ts = slow_onset(spec)
        if pulse and ts is not None and ts <= t < ts + 0.3:
            img = fx2.time_slow(img, (t - ts) / 0.3)
        return img
    return fx


def car_gfx(title, rows, t_in, t_out, anchor=(0.3, 0.16), side=None, label=None, kf=None, box_until=None):
    """The slow-motion graphics: brackets lock onto the car (its matte, tracked), a leader line draws itself to a
    label, the data rows type in. kf(t) -> box is the fallback where the matte is missing."""
    def fx(img, spec, t, f, m, R):
        if not (t_in <= t < t_out):
            return img
        box = R.track_box(spec, f)
        if box is None and kf is not None:
            box = kf(t)
        if box is None:
            return img
        h = gfx.Hud()
        fx2.lock_box(h, box, t, t_in, f=f, out_t=t_out if box_until is None else box_until, label=label)
        x0, y0, x1, y1 = box
        ax, ay = x0 + (x1 - x0) * anchor[0], y0 + (y1 - y0) * anchor[1]
        sd = side if side is not None else (1 if (x0 + x1) / 2 < W * 0.55 else -1)
        fx2.callout(h, (ax, ay), t, t_in + 0.07, title, rows, side=sd, f=f, out_t=t_out)
        return gfx.over(img, h.overlay())
    return fx


def lens_tint(t0, t1):
    """Coming out of his lens: the green mirror tint and the lens rim open out and fade."""
    def fx(img, spec, t, f, m, R):
        u = (t - t0) / (t1 - t0)
        if not (0 <= u < 1):
            return img
        e = (1 - u) ** 1.6
        tint = np.array([0.62, 0.92, 0.42], np.float32)
        g = img * (1 - 0.7 * e) + img * tint * 1.25 * 0.7 * e
        xx, yy = fx2._grid()
        d = np.sqrt(((xx - W / 2) / 1.0) ** 2 + ((yy - H / 2) / 0.92) ** 2)
        r = 520 + 1500 * u ** 1.2
        rim = np.clip((d - r) / 140, 0, 1)
        return g * (1 - 0.92 * rim * e)[..., None]
    return fx


def glint(t0, dur, xy_src, size=1.0):
    """A star glint on a point of the clip (display coords via the view) - the lens catching the sun."""
    def fx(img, spec, t, f, m, R):
        e = look.env_hit(t, t0, 0.12, dur, 1.4)
        if e <= 0:
            return img
        x, y = xy_src(t)
        ox, oy = R.to_out(spec, t, x, y)
        return gfx.add_star(img, ox, oy, size * (0.5 + 0.6 * e), 1.1 * e, angle=20 * t)
    return fx


def sunflare(strength=0.7, color=(1.0, 0.85, 0.6), thr=0.8):
    """An anamorphic streak and glow on the brightest blob in frame (the sun)."""
    def fx(img, spec, t, f, m, R):
        L = look.luma(img)
        small = cv2.GaussianBlur(cv2.resize(L, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 2)
        y, x = np.unravel_index(np.argmax(small), small.shape)
        if small[y, x] < thr:
            return img
        return fx2.flares(img, [(x * 8 + 4, y * 8 + 4)], strength, color, streak=520)
    return fx


def sun_at(xy, strength=0.7, color=(1.0, 0.85, 0.6)):
    """An anamorphic streak and glow on the sun at a fixed point of the clip (display px), through the view."""
    def fx(img, spec, t, f, m, R):
        ox, oy = R.to_out(spec, t, xy[0], xy[1])
        return fx2.flares(img, [(ox, oy)], strength, color, streak=520)
    return fx


def headlights(strength=0.9, region=(0.25, 0.15, 0.75, 0.85)):
    """Flares on the two brightest points in the middle of frame: the headlights."""
    def fx(img, spec, t, f, m, R):
        L = look.luma(img)
        s = cv2.GaussianBlur(cv2.resize(L, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 1.2)
        x0, y0, x1, y1 = [int(v) for v in (region[0] * W / 8, region[1] * H / 8, region[2] * W / 8, region[3] * H / 8)]
        sub = s[y0:y1, x0:x1]
        dil = cv2.dilate(sub, np.ones((5, 5), np.uint8))
        ys, xs = np.nonzero((sub >= dil) & (sub > 0.62))
        if len(xs) == 0:
            return img
        order = np.argsort(-sub[ys, xs])[:2]
        pts = [((xs[i] + x0) * 8 + 4, (ys[i] + y0) * 8 + 4) for i in order]
        sp = fx2.speed_of(spec, t, None)
        return fx2.flares(img, pts, strength * (0.7 + 0.3 * min(1, sp / 2)), (0.7, 0.85, 1.0), streak=420)
    return fx


def hold(t0, t1, amount=0.5):
    """The breath before the drop: the world drains of colour and the edges close in, then snaps back."""
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1 + 0.05):
            return img
        u = ease((t - t0) / (t1 - t0)) if t < t1 else 1 - (t - t1) / 0.05
        L = look.luma(img)[..., None]
        g = img * (1 - amount * u) + L * np.array([0.9, 0.95, 1.05], np.float32) * amount * u
        return look.vignette(g, 0.55 * u)
    return fx


def freeze_post(t0):
    """On the freeze frame: everything but the car drains to a cold monochrome (the car keeps its colour)."""
    def fx(g, spec, t, f, m, R):
        if t < t0 or m is None:
            return g
        e = ease((t - t0) / 0.12)
        L = look.luma(g)[..., None]
        bg = np.clip(look.scurve(L, 1.4) * np.array([0.86, 0.93, 1.02], np.float32) * 0.62, 0, 1)
        mm = m[..., None]
        out = g * mm + (g * (1 - e) + bg * e) * (1 - mm)
        return out
    return fx


def outline(t0, color=(1.0, 1.0, 1.0), width=5):
    """A crisp outline around the car's matte with a soft red bloom behind it (the freeze-frame sticker look)."""
    def fx(img, spec, t, f, m, R):
        if t < t0 or m is None:
            return img
        e = ease((t - t0) / 0.1)
        b = (m > 0.5).astype(np.uint8)
        dil = cv2.dilate(b, np.ones((width * 2 + 1, width * 2 + 1), np.uint8))
        ring = cv2.GaussianBlur((dil - b).astype(np.float32), (0, 0), 1.0)
        bloom = np.clip(cv2.GaussianBlur(dil.astype(np.float32), (0, 0), 22) - b, 0, 1)
        out = 1 - (1 - img) * (1 - (bloom * 0.55 * e)[..., None] * np.array(RED, np.float32))
        out = out * (1 - ring[..., None] * e) + ring[..., None] * e * np.array(color, np.float32)
        return out
    return fx


def kinetic(text, t0, t1, y, direction=-1, size=150, color=WHITE, font=gfx.F_BIG, alpha=0.9):
    """A word that rides the motion: it streaks in along the travel direction, decelerates through the middle,
    and streaks out (with motion blur stretched along the travel)."""
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1):
            return img
        u = (t - t0) / (t1 - t0)
        # position: fast in, slow middle, fast out (a velocity ramp of its own)
        p = 0.5 + 0.5 * math.copysign(abs(2 * u - 1) ** 2.6, 2 * u - 1)
        x = W * (1.25 - 1.5 * p) if direction < 0 else W * (-0.25 + 1.5 * p)
        v = abs(2 * u - 1) ** 1.6
        spr = gfx.text(text, font, size, color, 0.03)
        ov = gfx.blank()
        gfx.place(ov, spr, x, y, 1.0, alpha)
        k = int(1 + 70 * v)
        if k > 2:
            ov = cv2.blur(ov, (k, 1))
        return gfx.over(img, ov)
    return fx


# =========================================================================================== the shots

# ---------------- INTRO (letterboxed 2.39:1, cool, slow) ----------------
def lens_xy(s):
    """The near lens of his shades in 0434 (display px) at source time s."""
    ks = ((0.2, 1750, 1200), (0.6, 1880, 1145), (1.0, 2090, 1090), (1.3, 2140, 1050))
    return (float(np.interp(s, [k[0] for k in ks], [k[1] for k in ks])),
            float(np.interp(s, [k[0] for k in ks], [k[2] for k in ks])))


def v01_src(t):
    return 0.10 + 0.5 * t


def v01_view(t):
    lx, ly = lens_xy(v01_src(t))
    a, b = 1.02, C1
    c0 = (1920 + (lx - 1920) * 0.3, 1080 + (ly - 1080) * 0.3)
    if t < a:
        u = ease(t / a)
        return (1920 + (c0[0] - 1920) * u, 1080 + (c0[1] - 1080) * u, 3840 - 700 * u)
    u = min(1.0, (t - a) / (b - a))
    e = u ** 1.8
    k = min(1.0, e * 1.7)
    return (c0[0] + (lx - c0[0]) * k, c0[1] + (ly - c0[1]) * k, 3140 * (330 / 3140) ** e)


shot("V01", 0.0, C1, clip="0434", src=v01_src, view=v01_view, look="intro", max_scale=0.75, margin=1.05,
     pre=[("exposure", 0.97)], fx=[("zoomblur", 1.22, C1, 0.55, 1)],
     overlays=[glint(0.28, 0.55, lambda t: lens_xy(v01_src(t)), 1.2)])

# out of the lens: 0438, the POV over the valley; the zoom keeps going forward (expanding from 0.5)
shot("V02", C1, C2, clip="0438", src=(2.30, 0.5), view=(1920, 1080, 3840), look="intro", max_scale=0.6,
     fx=[("zoomo", C1, 1.95, 0.5, 1.0, 2.4), ("zoomblur", C1, 1.72, 0.5, -1)],
     overlays=[lens_tint(C1, 1.86)])

# the pull-back on him, sped up a little: the reveal accelerates toward the drop
shot("V03", C2, C3, clip="0418", src=(1.30, 1.5), view=path([(C2, 1080, 2480, 2160), (C3, 1080, 2520, 2160)]),
     look="intro", shutter=0.9, max_scale=0.6, pre=[("sky", 0.3, 0.5)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=1, axis="y", blur=0.2))

# the silhouette (mirrored so his strike travels left, the way every car will): wind up, the breath, the strike
FIST = (1740, 1050)                 # the extended fist in 0430 at 2.50 s (display px, before the mirror)
V04_VIEW = path([(C3, 1460, 900, 2900), (3.576, 1500, 960, 2500), (4.0, 1580, 1080, 1520), (4.2, 1600, 1105, 1300),
                 (4.2667, 1630, 1090, 1150)])
shot("V04", C3, DROP, clip="0430", flip=True, look="summit", interp="flow", shutter=0.9, margin=1.08,
     src=speedmap((4.2667, 2.50), [(C3, 0.45), (3.95, 0.45), (4.0, 0.12), (4.185, 0.12), (4.20, 3.6), (4.30, 3.6)]),
     view=V04_VIEW, pre=[("sky", 0.28, 0.55)],
     fx=[("zoomo", C3, 3.12, 1.22, 1.0, 2.0), ("zoomblur", 4.19, 4.2667, 0.2, 1)],
     overlays=[sun_at((420, 330), 0.7), hold(4.0, 4.2, 0.55)])


def fist_out(t):
    """The fist in output px at the drop (the view's mapping, mirrored)."""
    cx, cy, cw, _ = V04_VIEW(4.2667)
    k = W / cw
    return W - (W / 2 + (FIST[0] - cx) * k), H / 2 + (FIST[1] - cy) * k


# ---------------- DROP: the rally, full frame, velocity edits ----------------
# 0396: the strike punches a hole through to the car; fast approach -> sudden slow broadside -> fast exit, left
shot("V05", DROP, SN1, clip="0396", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(4.40, 4.84),
     tag="TARGET 01 // POLO",
     src=speedmap((4.44, 4.52), [(4.20, 2.6), (4.40, 2.6), (4.44, 0.22), (4.80, 0.22), (4.85, 2.8), (5.10, 2.8)]),
     view=(540, 1170, 1080),
     fx=[("shake", DROP, 30, 0.45, 1), ("rumble", DROP, 4.42, 6), ("zoom", 4.44, 4.80, 1.0, 1.07),
         ("rumble", 4.84, 5.1, 7)],
     overlays=[velo(-1), car_gfx("TARGET 01", ["VW POLO // RALLY", lambda t, f: "SPD " + fx2.counter(t, 4.45, 4.75, 141, 126) + " KM/H",
                                               "LOCK  0.98"], 4.45, 4.83)],
     tx=dict(kind="shock", d=0.0, e=0.17, at=lambda t: fist_out(t), rmax=2400))

# 0465: the orange Gypsy bursts in from the right: fast, then the "53" door in slow motion, then gone
def v06_box(t):
    """The yellow "53" sticker on the frozen Gypsy's door, in output px (the car fills the frame, so no matte;
    the box follows the freeze's slow push-in about the frame centre)."""
    z = 1 + 0.08 * ease((t - 5.17) / 0.33)
    x0, y0, x1, y1 = 722, 728, 940, 904
    return (W / 2 + (x0 - W / 2) * z, H / 2 + (y0 - H / 2) * z, W / 2 + (x1 - W / 2) * z, H / 2 + (y1 - H / 2) * z)


shot("V06", SN1, B3, clip="0465", look="rally", shutter=0.9,
     tag="CAR 53 // GYPSY", max_scale=0.75,
     src=speedmap((5.17, 6.345), [(4.80, 2.4), (5.14, 2.4), (5.17, 0.0), (5.50, 0.0), (5.53, 2.6), (5.80, 2.6)]),
     view=(1080, 2480, 2160),
     fx=[("rumble", SN1, 5.15, 6), ("zoom", 5.17, 5.50, 1.0, 1.08), ("shake", 5.1667, 16, 0.25, 9), ("rumble", 5.52, 5.80, 7)],
     overlays=[velo(-1), car_gfx("CAR 53", ["MARUTI GYPSY 4X4", lambda t, f: "SPD " + fx2.counter(t, 5.21, 5.42, 112, 98) + " KM/H",
                                            "G-LAT 1.1"], 5.20, 5.50, anchor=(0.5, 0.0), side=1, kf=v06_box)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=-1, blur=0.24))

# 0395: the white Polo drifts through; fast, slow on the drift, fast out
shot("V07", B3, HIT2, clip="0395", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(5.82, 6.16),
     tag="TARGET 02 // POLO",
     src=speedmap((5.85, 6.52), [(5.50, 2.4), (5.82, 2.4), (5.86, 0.25), (6.13, 0.25), (6.16, 2.6), (6.40, 2.6)]),
     view=(540, 1250, 1080),
     fx=[("rumble", B3, 5.84, 6), ("zoom", 5.86, 6.13, 1.0, 1.06), ("rumble", 6.15, 6.40, 7)],
     overlays=[velo(-1), car_gfx("TARGET 02", ["VW POLO // RALLY", lambda t, f: "DRIFT " + fx2.counter(t, 5.87, 6.05, 12, 24) + " DEG",
                                               "TRACTION 0.62"], 5.87, 6.15)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=-1, blur=0.24))

# 0397: the 808 hit freezes time on car 14 rushing at the lens, the HUD locks on, then it tears past to the left
V08_VIEW = path([(6.248, 1950, 1060, 2700), (6.80, 2000, 1080, 2450), (7.07, 2000, 1100, 3300)])
shot("V08", HIT2, RT, clip="0397", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(6.25, 6.84),
     tag="CAR 14 // POLO", max_scale=0.8,
     src=speedmap((6.28, 4.12), [(6.10, 1.0), (6.248, 1.0), (6.27, 0.2), (6.80, 0.2), (6.84, 3.2), (7.20, 3.2)]),
     view=V08_VIEW,
     fx=[("shake", HIT2, 34, 0.45, 2), ("zoom", 6.27, 6.80, 1.0, 1.12), ("rumble", 6.83, 7.2, 9)],
     overlays=[velo(-1, warp=True),
               car_gfx("CAR 14", ["VW POLO // R", lambda t, f: "SPD " + fx2.counter(t, 6.30, 6.62, 158, 132) + " KM/H",
                                  lambda t, f: "G " + fx2.counter(t, 6.30, 6.62, 4, 13, "{:02d}")[:1] + "." +
                                  fx2.counter(t, 6.30, 6.62, 4, 13, "{:02d}")[1:],
                                  "TYRE MRF // GRAVEL"], 6.29, 6.82, anchor=(0.62, 0.14))])

# 0465 again: the Gypsy disappears into its own dust; the camera whips after the car leaving left
shot("V09", RT, SN2, clip="0465", look="rally", shutter=0.9, max_scale=0.6, tag="CAR 53 // GYPSY",
     src=speedmap((7.07, 6.52), [(6.95, 2.8), (7.45, 2.2), (7.768, 1.1), (8.0, 0.6)]),
     view=path([(7.0, 1080, 2420, 2160), (7.768, 1080, 2250, 2160)]),
     fx=[("rumble", RT, 7.4, 6)],
     overlays=[velo(-1, pulse=False)],
     tx=dict(kind="push", d=0.067, e=0.1, dir=-1, blur=0.3))

# ---------------- BREAK (letterbox back, monsoon green, slow) ----------------
# the dust becomes cloud: 7910, tilting down out of the clouds onto him doing push-ups on the ledge
shot("V10", SN2, B7, clip="7910", look="summit", interp="flow", max_scale=0.6,
     src=(9.20, 0.5), view=path([(7.55, 1080, 1500, 2160), (8.15, 1080, 2560, 2160), (8.467, 1080, 2650, 2160)]),
     tx=dict(kind="luma", d=0.2, e=0.2, soft=0.14, bloom=0.55))

# the summit, the sun breaking through; the 808 creeps back in and the camera is pulled toward the sun
V11_VIEW = path([(8.467, 1920, 1080, 3840), (8.80, 1750, 1040, 3400), (9.051, 900, 720, 1500)])
shot("V11", B7, HIT3, clip="0434", look="summit", shutter=0.9, max_scale=0.6, pre=[("sky", 0.3, 0.55)],
     src=speedmap((8.467, 12.10), [(8.40, 0.7), (8.80, 0.7), (9.051, 2.4), (9.2, 2.4)]), view=V11_VIEW,
     fx=[("zoomblur", 8.86, 9.051, 0.35, 1)],
     overlays=[sunflare(0.85, (1.0, 0.85, 0.62), 0.75)],
     tx=dict(kind="push", d=0.067, e=0.1, dir=-1, axis="y", blur=0.2))

# ---------------- FINAL ----------------
# the sun becomes headlights: the green Gypsy rushing at the lens, the world streaking past
shot("V12", HIT3, E1, clip="0467", look="rally", shutter=0.9, tag="CAR 08 // GYPSY",
     src=speedmap((9.051, 5.55), [(8.9, 2.4), (9.515, 2.6), (9.6, 2.6)]),
     view=path([(8.9, 960, 520, 1300), (9.515, 1000, 585, 620)]),
     fx=[("shake", HIT3, 26, 0.4, 3), ("shake", snap(9.166), 18, 0.25, 4), ("zoomblur", 9.38, E1, 0.45, 1)],
     overlays=[headlights(1.0), velo(-1, lines=False, pulse=False, warp=True)],
     tx=dict(kind="light", d=0.134, e=0.167))

# through: the side of a car fills the frame, sweeping left
shot("V13", E1, E2, clip="0396", look="rally", shutter=0.9, tag="TARGET 01 // POLO",
     src=speedmap((9.515, 4.60), [(9.40, 0.8), (9.9, 0.8)]), view=(540, 1200, 1080),
     fx=[("zoomo", E1, 9.70, 0.72, 1.0, 2.0), ("zoomblur", E1, 9.66, 0.5, -1), ("rumble", E1, E2, 8)],
     overlays=[velo(-1, pulse=False)])

# the teal Polo drifts the other way, slows, and freezes: outline, the world drained, REDLINE behind it
shot("V14", E2, DURATION, clip="0461", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(9.98, 10.70),
     tag="CAR 65 // POLO",
     src=speedmap((10.214, 10.44), [(9.70, 2.4), (10.0, 2.4), (10.04, 0.18), (10.18, 0.18), (10.214, 0.0), (10.8, 0.0)]),
     view=(540, 1060, 1080),
     fx=[("rumble", E2, 10.02, 7), ("zoom", 10.214, 10.70, 1.0, 1.09), ("shake", E3, 26, 0.35, 7), ("shake", SN3, 30, 0.3, 8)],
     post=[freeze_post(E3)],
     words=[word(E3, "REDLINE", (1478, 772), 218, RED, behind=True, tracking=0.03, dur=0.09, from_=1.6)],
     overlays=[velo(1), outline(E3), car_gfx("CAR 65", ["VW POLO // RALLY", lambda t, f: "DRIFT " + fx2.counter(t, 10.05, 10.3, 20, 41) + " DEG",
                                                       "STATUS  FROZEN"], 10.05, 10.70, anchor=(0.86, 0.3), side=1, box_until=E3 + 0.05)],
     tx=dict(kind="wipe", d=0.1, e=0.1, dir=-1, soft=110, blur=0.14))

SHOTS.sort(key=lambda s: s["F0"])
for a, b in zip(SHOTS, SHOTS[1:]):
    assert a["F1"] == b["F0"], (a["id"], a["F1"], b["id"], b["F0"])
# transitions borrow frames across the cut: decode them too
for i, s in enumerate(SHOTS):
    tx = s.get("tx")
    if tx and i:
        s["_pre"] = int(round(tx.get("d", 0) * FPS)) + 1
        SHOTS[i - 1]["_post"] = int(round(tx.get("e", 0) * FPS)) + 1

# =========================================================================================== global finishing

def _bars(t):
    def blend(a, b, u):
        u = ease(u)
        ra, rb = W / a, W / b
        return W / (ra + (rb - ra) * u)
    if t < 4.0:
        return 2.39
    if t < DROP - 0.01:
        return blend(2.39, 2.9, (t - 4.0) / 0.2)            # the breath: the frame closes in
    if t < SN2:
        return 16 / 9
    if t < SN2 + 0.25:
        return blend(16 / 9, 2.39, (t - SN2) / 0.25)
    if t < HIT3:
        return 2.39
    return 16 / 9


def _rally(t):
    return (DROP <= t < SN2 - 0.05) or (HIT3 + 0.12 <= t < END)


PUSHES = [(SN1 - 0.1, -1, 0.46), (B3 - 0.1, -1, 0.70), (RT - 0.067, -1, 0.40), (E2 - 0.1, -1, 0.55)]


def hud(img, t, f, spec, R):
    """Graphic motion on the pushes (chevrons racing with the cars), and the telemetry strip on the rally
    sections: revs, speed and gear follow the picture's playback speed."""
    for (tp, d, y) in PUSHES:
        if tp <= t < tp + 0.3:
            h = gfx.Hud()
            h.shadow = 0
            fx2.chevrons(h, t, tp, d, y=H * y, alpha=0.9)
            img = gfx.over(img, h.overlay())
    if spec is None or not _rally(t) or spec.get("src") is None:
        return img
    a = min(1.0, (t - DROP) / 0.12) if t < SN2 else min(1.0, (t - HIT3 - 0.12) / 0.12)
    a *= min(1.0, (SN2 - 0.05 - t) / 0.08) if t < SN2 else 1.0
    sp = fx2.speed_of(spec, t, None)
    slow = sp < 0.6
    jit = (math.sin(f * 2.3) * 0.5 + math.sin(f * 5.1) * 0.5)
    rpm = float(np.clip(0.38 + 0.22 * sp + 0.03 * jit, 0.12, 1.0)) if not slow else 0.3 + 0.05 * sp
    kmh = int(np.clip(36 + 44 * sp + 2 * jit, 0, 199)) if not slow else int(118 + 14 * sp)
    gear = 5 if sp > 2 else (4 if sp > 1 else 3)
    rate = f"{sp:.2f}X" if sp > 0.001 else "FREEZE"
    h = gfx.Hud()
    fx2.tach(h, t, rpm, kmh, gear, spec.get("tag", ""), slow=slow, alpha=a, f=f, rate=rate)
    return gfx.over(img, h.overlay())


GLOBAL = dict(
    flashes=[(snap(1.479), 0.14, 0.35, (0.8, 1.0, 0.7)), (DROP, 0.2, 0.9), (SN1, 0.08, 0.3), (B3, 0.08, 0.25),
             (5.1667, 0.12, 0.45), (HIT2, 0.2, 0.85), (RT, 0.1, 0.4), (SN2, 0.2, 0.3), (E1, 0.1, 0.5), (E2, 0.08, 0.35),
             (E3, 0.14, 0.8), (SN3, 0.16, 0.7, (1.0, 0.25, 0.2))],
    inverts=[(SN3 + 0.067, SN3 + 0.1, (1.0, 0.85, 0.85))],
    glitches=[(SN3, SN3 + 0.067, 1.0), (DROP - 0.034, DROP, 0.6)],
    hits=[(DROP, 1.0, 0.4), (SN1, 0.4), (B3, 0.4), (HIT2, 1.0, 0.4), (RT, 0.6), (HIT3, 0.8, 0.4), (9.166, 0.5),
          (E1, 0.5), (E2, 0.6), (E3, 0.9, 0.35), (SN3, 1.0, 0.3)],
    shocks=[(HIT2, 0.5, (960, 520), 48), (E3, 0.45, (620, 500), 44), (SN3, 0.3, (960, 540), 30)],
    crt=[],
    halation=lambda t: 0.18 if t < DROP else (0.12 if t < SN2 else (0.2 if t < HIT3 else 0.12)),
    vignette=lambda t: 0.38 if t < DROP else (0.3 if t < SN2 else (0.4 if t < HIT3 else 0.32)),
    grain=lambda t: 0.022 if t < DROP or SN2 <= t < HIT3 else 0.016,
    bars=_bars,
    fade=lambda t: 0.0 if t >= END else min(1.0, t / 0.2),
    hud=hud,
)
