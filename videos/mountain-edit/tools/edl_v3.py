"""REEL 3 ("TORE UP"): the 37.8 s edit to renders/audio/reel3.wav (Don Toliver, "Tore Up", TikTok edit audio).

  EDL=edl_v3 python3 tools/render.py ...      (the picture goes to renders/picture_v3/)

The story: the road up (a jeep on a red trail, mist, the walk to the edge), him, the summit as a photo that
still moves; the jeep accelerates into the drop and comes out as a rally car rushing the lens; velocity edits
(full speed, a sudden drop into slow motion with graphics locking on, full speed out) on every snare; the 808
glide rewinds the tape; a freeze frame tears the title in two; the frame rips open onto the summit; photos
flash like a camera; an 808 roll stutters through the best frames; the last silhouette with the title behind
him.

The audio (142.55 BPM, 0.4209 s beats; phrases of 8 beats, 3.367 s):
  0.106 / 3.473 / 6.841 / 10.208   intro phrases (sustained bass, no drums); gaps before each
  12.75-13.1  the breath          13.19-13.48  an 808 roll in          13.584  DROP
  14.408 16.093 17.768 19.467 21.139 22.821 24.464 26.184   snares (every 4 beats)
  26.2-27.35  808 glide-up (peak 27.035)    27.5-28.25  the dip     28.299  second section
  32.93-33.87 an 808 roll (eighths)         35.035  last phrase     37.54 / 37.66  last 808s
"""
import math

import cv2
import numpy as np

import fx2
import gfx
import look
from edl_v2 import car_gfx, ease, freeze_post, headlights, hold, outline, sun_at, sunflare, velo, word
from fx2 import speedmap
from media import FPS, H, W, frame_of, path

DURATION = 37.80
OUT = "renders/picture_v3"
BEAT = 0.4209
RED, WHITE = gfx.RED, gfx.WHITE

AUDIO = dict(P1=0.106, B5=1.790, P2=3.473, B13=5.157, P3=6.841, B21=8.524, P4=10.208, B29=11.891, PU=13.192,
             DROP=13.584, S1=14.408, S2=16.093, X2=16.509, S3=17.768, S4=19.467, N4=19.888, S5=21.139, N5a=21.573,
             N5b=22.0, S6=22.821, X6=23.568, S7=24.464, S8=26.184, GL=27.035, DROPB=28.299, Q1=29.990, Q2=30.827,
             PB2=31.664, ROLL=32.928, R2=34.461, PB3=35.035, L1=37.539, L2=37.664)


def snap(t):
    return frame_of(t) / FPS


A = {k: snap(v) for k, v in AUDIO.items()}          # the same moments on the frame that contains them
END = snap(37.72)

SHOTS, SPECS = [], {}


def shot(sid, t0, t1, **kw):
    s = dict(id=sid, t0=t0, t1=t1, F0=frame_of(t0), F1=frame_of(t1), **kw)
    s.setdefault("layout", "full")
    s.setdefault("fx", [])
    SHOTS.append(s)
    SPECS[sid] = s
    return s


def sub(sid, parent, **kw):
    s = dict(id=sid, t0=parent["t0"], t1=parent["t1"], F0=parent["F0"], F1=parent["F1"], **kw)
    s.setdefault("fx", [])
    SPECS[sid] = s
    return sid


# =========================================================================================== overlays

def leak(t0, t1, strength=0.4, seed=1):
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1):
            return img
        a = strength * min(1.0, (t - t0) / 0.3) * min(1.0, (t1 - t) / 0.3)
        return gfx.light_leak(img, t, a, seed)
    return fx


def mono(t0, text, x, y, size=24, until=None, anchor="la"):
    """A HUD line that types itself on."""
    def fx(img, spec, t, f, m, R):
        if t < t0 or (until and t >= until):
            return img
        n = int((t - t0) * 38)
        s = text[:max(0, n)]
        if not s:
            return img
        h = gfx.Hud()
        cur = "_" if (f // 8) % 2 == 0 and n < len(text) + 10 else ""
        h.text(s + cur, x, y, size, (1, 1, 1), 0.95, gfx.F_MONOB, anchor=anchor)
        return gfx.over(img, h.overlay())
    return fx


def panel_labels(labels):
    """Labels slamming onto the triptych panels as each one lands: (appear, x, text)."""
    def fx(img, spec, t, f, m, R):
        h = gfx.Hud()
        h.shadow = 0
        for (ta, x, text) in labels:
            if t < ta:
                continue
            u = min(1.0, (t - ta) / 0.12)
            w = int((len(text) * 30 * 0.62 + 28) * (1 - (1 - u) ** 3))
            h.rect(x, 64, x + w, 64 + 44, RED, 0.95, fill=True)
            if u > 0.6:
                h.text(text, x + 14, 64 + 22, 30, (1, 1, 1), 1.0, gfx.F_MONOB, anchor="lm")
        return gfx.over(img, h.overlay())
    return fx


# =========================================================================================== custom layouts

REWIND = ["T15", "T14", "T13", "T12", "T11", "T10", "T09"]


def draw_rewind(spec, t, f, R):
    """The 808 glides up and the tape rewinds through the drop: every car shot runs backwards at speed, one
    after another (their graphics retracting), through VHS tracking noise, with REW and a running timecode."""
    n = len(REWIND)
    u = (t - spec["t0"]) / (spec["t1"] - spec["t0"])
    k = min(n - 1, int(u * n))
    v = u * n - k
    s = SPECS[REWIND[k]]
    ts = s["t1"] - 1e-3 - v * (s["t1"] - s["t0"] - 2e-3)
    img = R.shot_image(s, ts, int(ts * FPS))
    img = fx2.vhs(img, f, t, 1.0)
    h = gfx.Hud()
    h.text("<< REW", 80, 70, 40, (1, 1, 1), 0.95, gfx.F_MONOB)
    h.text(f"00:{int(ts):02d}:{int((ts % 1) * 30):02d}", W - 80, 70, 34, (1, 1, 1), 0.95, gfx.F_MONOB, anchor="ra")
    return gfx.over(img, h.overlay())


STUTTER = [(32.928, "T09", 14.6), (33.139, "T05", 7.6), (33.349, "T11", 18.5), (33.56, "T06", 9.4),
           (33.765, "T15", 25.3), (33.867, "T12", 20.2), (34.0, "T22", 34.9)]


def draw_stutter(spec, t, f, R):
    """The 808 roll: one hero frame per note, each landing with a flash, every other one inverted."""
    k = max(i for i, (ta, _, _) in enumerate(STUTTER) if ta <= t + 1e-6) if t >= STUTTER[0][0] else 0
    ta, sid, ts = STUTTER[k]
    img = R.shot_image(SPECS[sid], ts, int(ts * FPS))
    e = look.env_hit(t, ta, 0.0, 0.09, 2)
    if k % 2 == 1 and k < len(STUTTER) - 1:
        img = look.invert(img, 1.0, (1.0, 0.86, 0.86))
    img = look.rgb_split(img, 10 * e)
    return look.flash(img, 0.8 * e)


# =========================================================================================== the shots

# ---------------- INTRO: the road up (2.39:1, cool, slow) ----------------
shot("T01", 0.0, A["B5"], clip="9685", src=(4.30, 0.5), view=(540, 1010, 1080), look="intro", max_scale=1.0,
     fx=[("zoom", 0.0, A["B5"] + 0.3, 1.0, 1.07), ("handheld", 2)], overlays=[leak(0.2, A["B5"], 0.2, 3)])

shot("T02", A["B5"], A["P2"], clip="2902", src=(2.0, 0.5), view=(1080, 1960, 2160), look="intro",
     max_scale=0.6, fx=[("zoom", A["B5"], A["P2"], 1.0, 1.08), ("handheld", 2)], overlays=[sunflare(0.7, (1.0, 0.88, 0.7), 0.8)],
     tx=dict(kind="luma", d=0.23, e=0.23, soft=0.16, bloom=0.4))

T03_VIEW = path([(A["P2"], 540, 1250, 1080), (4.3, 540, 1100, 1080), (A["B13"], 540, 900, 1080)])
shot("T03", A["P2"], A["B13"], clip="0441", src=(4.15, 1.0), view=T03_VIEW, look="intro", shutter=0.5,
     fx=[("zoomi", 4.92, A["B13"], 1.0, 1.7, 2.2), ("zoomblur", 4.95, A["B13"], 0.35, 1)],
     tx=dict(kind="tear", d=0.0, e=0.36, seed=11, x0=0.5, slope=0.1, spread=0.8))

shot("T04", A["B13"], A["P3"], clip="0434", src=(3.45, 0.9), look="intro", max_scale=0.6, pre=[("sky", 0.3, 0.55)],
     view=path([(A["B13"], 1920, 1080, 3840), (A["P3"], 1960, 1140, 3300)]),
     fx=[("zoomo", A["B13"], 5.5, 0.62, 1.0, 2.2), ("zoomblur", A["B13"], 5.42, 0.45, -1)],
     overlays=[sunflare(0.55, (1.0, 0.88, 0.7), 0.82)])

# him: the pull-back, a lock that names him
shot("T05", A["P3"], A["B21"], clip="0418", src=(0.40, 0.5), look="intro", max_scale=0.6, matte="human",
     matte_t=(7.05, 8.52), view=path([(A["P3"], 1080, 2470, 2160), (A["B21"], 1080, 2520, 2160)]),
     pre=[("sky", 0.3, 0.5)], fx=[("handheld", 2)],
     overlays=[car_gfx("MAIN CHARACTER", ["STATUS  UNBOTHERED", "AURA    100%", "LOCATION  ABOVE THE CLOUDS"],
                       7.15, A["B21"], anchor=(0.34, 0.1), side=-1)],
     tx=dict(kind="light", d=0.1, e=0.13, peak=0.9))

# the same summit, as a photograph that still moves (2.5D): the moment frozen into a memory
shot("T06", A["B21"], A["P4"], layout="photo", clip="0413", view=(1134, 2650, 2268), look="intro",
     bg_zoom=(1.0, 1.32), fg_zoom=(1.0, 1.05), fx=[("punch", A["B21"], 0.05, 0.4)],
     overlays=[leak(A["B21"], A["P4"], 0.3, 5)],
     tx=dict(kind="flash", d=0.067, e=0.2))

# the crane up from the rock to the sun
shot("T07", A["P4"], A["B29"], clip="0439", src=(2.40, 1.0), look="intro", max_scale=0.6, shutter=0.5,
     view=path([(A["P4"], 1080, 2000, 2160), (A["B29"], 1080, 1450, 2160)]), overlays=[sunflare(0.7, (1.0, 0.86, 0.66), 0.8)],
     tx=dict(kind="tear", d=0.0, e=0.36, seed=23, x0=0.46, slope=-0.1, spread=0.8))

# the build: back on the road, the jeep winds up, the breath, then it floors it down the trail into the drop
T08_VIEW = path([(A["B29"], 540, 1010, 1080), (13.15, 540, 1010, 1080), (A["DROP"], 400, 1060, 470)])
shot("T08", A["B29"], A["DROP"], clip="9685", look="intro", shutter=0.9, max_scale=1.0,
     src=speedmap((A["B29"], 6.30), [(11.80, 0.7), (12.70, 0.9), (12.76, 0.1), (13.10, 0.1), (13.20, 2.5), (A["DROP"], 7.0),
                                      (13.8, 7.0)]),
     view=T08_VIEW, fx=[("zoomblur", 13.3, A["DROP"], 0.5, 1), ("rumble", 13.2, A["DROP"], 5)],
     overlays=[hold(12.76, 13.14, 0.6), velo(-1, lines=False, pulse=False, warp=True)],
     tx=dict(kind="light", d=0.13, e=0.17, peak=0.92))

# ---------------- DROP: the rally (full frame, warm), a velocity edit on every snare ----------------
T09_VIEW = path([(A["DROP"], 1950, 1050, 2900), (15.55, 2000, 1080, 2400), (A["S2"], 2000, 1100, 3300)])
shot("T09", A["DROP"], A["S2"], clip="0397", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(13.98, 15.6),
     tag="CAR 14 // POLO", max_scale=0.6,
     src=speedmap((14.0, 4.06), [(13.4, 2.2), (13.95, 2.2), (14.0, 0.15), (15.55, 0.15), (15.62, 3.2), (16.4, 3.2)]),
     view=T09_VIEW,
     fx=[("zoomo", A["DROP"], 13.85, 0.6, 1.0, 2.2), ("zoomblur", A["DROP"], 13.8, 0.5, -1), ("shake", A["DROP"], 34, 0.5, 1),
         ("shake", A["S1"], 22, 0.3, 2), ("zoom", 14.0, 15.55, 1.0, 1.15), ("rumble", 15.6, 16.4, 9)],
     overlays=[velo(-1, warp=True),
               car_gfx("CAR 14", ["VW POLO // RALLY", lambda t, f: "SPD " + fx2.counter(t, 14.05, 14.6, 158, 132) + " KM/H",
                                  lambda t, f: "G " + fx2.counter(t, 14.05, 14.6, 4, 13, "{:02d}")[:1] + "." +
                                  fx2.counter(t, 14.05, 14.6, 4, 13, "{:02d}")[1:], "TYRE MRF // GRAVEL"],
                       14.05, 15.55, anchor=(0.62, 0.14))])

shot("T10", A["S2"], A["S3"], clip="0396", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(16.48, 17.42),
     tag="TARGET 01 // POLO",
     src=speedmap((16.509, 4.50), [(15.9, 1.8), (16.47, 1.8), (16.52, 0.2), (17.38, 0.2), (17.45, 2.8), (18.0, 2.8)]),
     view=(540, 1170, 1080),
     fx=[("rumble", A["S2"], 16.5, 6), ("zoom", 16.52, 17.38, 1.0, 1.08), ("shake", A["X2"], 16, 0.25, 3), ("rumble", 17.44, 18.0, 7)],
     overlays=[velo(-1), car_gfx("TARGET 01", ["VW POLO // RALLY", lambda t, f: "SPD " + fx2.counter(t, 16.55, 17.0, 141, 126) + " KM/H",
                                               "LOCK  0.98"], 16.55, 17.40)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=-1, blur=0.24))


def t11_box(t):
    """The yellow "53" sticker on the frozen Gypsy's door (output px), following the freeze's push-in."""
    z = 1 + 0.08 * ease((t - 18.17) / 0.78)
    x0, y0, x1, y1 = 722, 728, 940, 904
    return (W / 2 + (x0 - W / 2) * z, H / 2 + (y0 - H / 2) * z, W / 2 + (x1 - W / 2) * z, H / 2 + (y1 - H / 2) * z)


shot("T11", A["S3"], A["S4"], clip="0465", look="rally", shutter=0.9, tag="CAR 53 // GYPSY", max_scale=0.6,
     src=speedmap((18.17, 6.345), [(17.6, 2.4), (18.13, 2.4), (18.17, 0.0), (18.95, 0.0), (18.99, 2.6), (19.7, 2.6)]),
     view=(1080, 2480, 2160),
     fx=[("rumble", A["S3"], 18.15, 6), ("zoom", 18.17, 18.95, 1.0, 1.08), ("shake", 18.17, 18, 0.25, 9), ("rumble", 18.98, 19.7, 7)],
     overlays=[velo(-1), car_gfx("CAR 53", ["MARUTI GYPSY 4X4", lambda t, f: "SPD " + fx2.counter(t, 18.2, 18.6, 112, 98) + " KM/H",
                                            "G-LAT 1.1"], 18.2, 18.95, anchor=(0.5, 0.0), side=1, kf=t11_box)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=-1, blur=0.24))

shot("T12", A["S4"], A["S5"], clip="0395", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(19.86, 20.76),
     tag="TARGET 02 // POLO",
     src=speedmap((19.888, 6.52), [(19.3, 2.4), (19.84, 2.4), (19.89, 0.22), (20.70, 0.22), (20.76, 2.6), (21.3, 2.6)]),
     view=(540, 1250, 1080),
     fx=[("rumble", A["S4"], 19.86, 6), ("zoom", 19.89, 20.70, 1.0, 1.07), ("shake", A["N4"], 14, 0.25, 4), ("rumble", 20.75, 21.3, 7)],
     overlays=[velo(-1), car_gfx("TARGET 02", ["VW POLO // RALLY", lambda t, f: "DRIFT " + fx2.counter(t, 19.9, 20.3, 12, 24) + " DEG",
                                               "TRACTION 0.62"], 19.92, 20.74)],
     tx=dict(kind="push", d=0.1, e=0.1, dir=-1, blur=0.24))

# the triptych: three cars land in three panels on three 808 notes
T13 = shot("T13", A["S5"], A["S6"], layout="panels", look="rally", panels=[], bg=(0.02, 0.02, 0.02))
for i, (clip, src, view, appear) in enumerate([
        ("0461", speedmap((A["S5"], 9.95), [(21.0, 0.6), (22.9, 0.6)]), (420, 1050, 620), A["S5"]),
        ("0395", speedmap((A["N5a"], 6.47), [(21.4, 0.3), (22.9, 0.3)]), (560, 1230, 640), A["N5a"]),
        ("0397", speedmap((A["N5b"], 4.47), [(21.9, 0.35), (22.9, 0.35)]), (2700, 1080, 1180), A["N5b"])]):
    x0 = i * 640 + (4 if i else 0)
    x1 = (i + 1) * 640 - (4 if i < 2 else 0)
    T13["panels"].append(sub(f"T13p{i}", T13, clip=clip, src=src, view=view, aspect=(x1 - x0) / H, rect=(x0, 0, x1, H),
                             appear=appear, style="slide_down" if i == 1 else "slide_up", look="rally", shutter=0.6,
                             max_scale=0.6))
T13["overlays"] = [panel_labels([(A["S5"] + 0.03, 34, "CAR 65"), (A["N5a"] + 0.03, 674, "TARGET 02"),
                                 (A["N5b"] + 0.03, 1314, "CAR 14")])]

# headlights rushing the lens, a breath of slow motion in the glare, the real camera whip out
shot("T14", A["S6"], A["S7"], clip="0467", look="rally", shutter=0.9, interp="flow", tag="GYPSY // 4X4",
     src=speedmap((A["S6"], 5.50), [(22.6, 1.5), (23.5, 1.5), (23.55, 0.25), (24.10, 0.25), (24.16, 2.2), (24.7, 2.2)]),
     view=path([(A["S6"], 960, 520, 1300), (23.55, 980, 560, 900), (A["S7"], 1000, 580, 1250)]),
     fx=[("shake", A["S6"], 24, 0.35, 3), ("shake", A["X6"], 14, 0.25, 4), ("zoom", 23.55, 24.1, 1.0, 1.08)],
     overlays=[headlights(1.0), velo(-1, lines=False, warp=True)],
     tx=dict(kind="flash", d=0.033, e=0.17))

# the teal Polo drifts the other way: fast, slow on the drift, fast out
shot("T15", A["S7"], A["S8"], clip="0461", look="rally", interp="flow", shutter=0.9, matte="isnet", matte_t=(24.93, 25.86),
     tag="CAR 65 // POLO",
     src=speedmap((24.95, 10.24), [(24.3, 1.3), (24.90, 1.3), (24.95, 0.22), (25.80, 0.22), (25.86, 2.6), (26.4, 2.6)]),
     view=(540, 1060, 1080),
     fx=[("zoom", 24.95, 25.80, 1.0, 1.07), ("shake", 25.56, 14, 0.25, 5), ("rumble", 25.85, 26.4, 8)],
     overlays=[velo(1), car_gfx("CAR 65", ["VW POLO // RALLY", lambda t, f: "DRIFT " + fx2.counter(t, 25.0, 25.5, 20, 41) + " DEG",
                                           "SPD 087 KM/H"], 25.0, 25.82, anchor=(0.86, 0.3), side=1)],
     tx=dict(kind="light", d=0.13, e=0.17))

# the 808 glides up: the tape rewinds through the drop
shot("T16", A["S8"], A["GL"], layout="custom", draw=draw_rewind, look=None)

# the freeze: car 14 stopped dead, the world drained, the title torn in two behind it
T17_SEP = lambda t: 6 + 26 * ease((t - A["GL"]) / 1.1)
shot("T17", A["GL"], A["DROPB"], clip="0397", look="rally", matte="isnet", tag="CAR 14 // POLO", max_scale=0.8,
     src=speedmap((A["GL"], 4.16), [(26.9, 0.0), (28.5, 0.0)]), view=(2560, 1100, 2400),
     fx=[("zoom", A["GL"], A["DROPB"], 1.0, 1.08), ("shake", A["GL"], 26, 0.35, 6)],
     post=[freeze_post(A["GL"])],
     words=[word(A["GL"], "TORE", (1440, 380), 300, WHITE, behind=True, tracking=0.03, dur=0.08, from_=1.5, torn=T17_SEP, seed=5),
            word(A["GL"] + 0.07, "UP.", (1500, 690), 300, RED, behind=True, tracking=0.03, dur=0.08, from_=1.5, torn=T17_SEP, seed=9)],
     overlays=[outline(A["GL"]), mono(A["GL"] + 0.15, "CAR 14 // STATUS: TORE UP", 1080, 930, 26)])

# ---------------- SECOND SECTION: the summit, the photos, the roll, the last silhouette ----------------
shot("T18", A["DROPB"], A["Q1"], clip="0434", src=(12.0, 0.6), look="summit", max_scale=0.6, pre=[("sky", 0.3, 0.55)],
     view=path([(A["DROPB"], 1920, 1080, 3840), (A["Q1"], 1880, 1020, 3300)]), overlays=[sunflare(0.8, (1.0, 0.86, 0.62), 0.78)],
     tx=dict(kind="tear", d=0.0, e=0.4, seed=31, x0=0.5, slope=0.14, spread=0.85))

shot("T19", A["Q1"], A["Q2"], layout="photo", clip="0402", view=(1150, 1980, 2252), look="crew",
     bg_zoom=(1.0, 1.06), fg_zoom=(1.0, 1.14), pan=(-0.01, 0.0), tx=dict(kind="flash", d=0.067, e=0.2))
shot("T19b", A["Q2"], A["PB2"], layout="photo", clip="4838", rotate=90, view=(1046, 520, 2092), look="summit",
     bg_zoom=(1.0, 1.06), fg_zoom=(1.0, 1.15), pan=(0.02, 0.0), tx=dict(kind="flash", d=0.067, e=0.2))

shot("T20", A["PB2"], A["ROLL"], clip="7910", src=(9.20, 0.5), interp="flow", look="summit", max_scale=0.6,
     view=path([(A["PB2"] - 0.3, 1080, 1900, 2160), (32.4, 1080, 2560, 2160), (A["ROLL"], 1080, 2650, 2160)]),
     tx=dict(kind="tear", d=0.0, e=0.36, seed=41, x0=0.48, slope=-0.12, spread=0.8))

shot("T21", A["ROLL"], A["R2"], layout="custom", draw=draw_stutter, look=None)

T22_SEP = lambda t: 4 + 18 * ease((t - A["PB3"]) / 2.2)
shot("T22", A["R2"], DURATION, clip="0430", src=(2.50, 0.5), interp="flow", look="summit", matte="human",
     matte_t=(34.9, 37.8), max_scale=0.8, pre=[("sky", 0.28, 0.55)],
     view=path([(A["R2"], 1450, 950, 2400), (37.8, 1520, 990, 1800)]),
     fx=[("shake", A["R2"], 20, 0.3, 7), ("shake", A["L1"], 22, 0.3, 8)],
     words=[word(A["PB3"], "TORE UP.", (760, 600), 300, WHITE, behind=True, tracking=0.04, dur=0.1, from_=1.4,
                 torn=T22_SEP, seed=13)],
     overlays=[sun_at((420, 330), 0.75)],
     tx=dict(kind="flash", d=0.033, e=0.2))

SHOTS.sort(key=lambda s: s["F0"])
for a, b in zip(SHOTS, SHOTS[1:]):
    assert a["F1"] == b["F0"], (a["id"], a["F1"], b["id"], b["F0"])
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
    if t < 12.76:
        return 2.39
    if t < A["DROP"]:
        return blend(2.39, 2.9, (t - 12.76) / 0.3)
    if t < A["GL"]:
        return 16 / 9
    if t < A["GL"] + 0.2:
        return blend(16 / 9, 2.39, (t - A["GL"]) / 0.2)
    return 2.39


PUSHES = [(A["S2"] - 0.1, -1, 0.5), (A["S3"] - 0.1, -1, 0.66), (A["S4"] - 0.1, -1, 0.4)]


def hud(img, t, f, spec, R):
    """Chevrons racing with the pushes; the telemetry strip through the drop (revs, speed, gear and playback rate
    follow the picture's own time map)."""
    for (tp, d, y) in PUSHES:
        if tp <= t < tp + 0.3:
            h = gfx.Hud()
            h.shadow = 0
            fx2.chevrons(h, t, tp, d, y=H * y, alpha=0.9)
            img = gfx.over(img, h.overlay())
    if spec is None or spec.get("src") is None or not (A["DROP"] + 0.1 <= t < A["S8"]):
        return img
    a = min(1.0, (t - A["DROP"] - 0.1) / 0.15) * min(1.0, (A["S8"] - t) / 0.1)
    sp = fx2.speed_of(spec, t, None)
    slow = sp < 0.6
    jit = math.sin(f * 2.3) * 0.5 + math.sin(f * 5.1) * 0.5
    rpm = float(np.clip(0.38 + 0.22 * sp + 0.03 * jit, 0.12, 1.0)) if not slow else 0.3 + 0.05 * sp
    kmh = int(np.clip(36 + 44 * sp + 2 * jit, 0, 199)) if not slow else int(118 + 14 * sp)
    gear = 5 if sp > 2 else (4 if sp > 1 else 3)
    rate = f"{sp:.2f}X" if sp > 0.001 else "FREEZE"
    h = gfx.Hud()
    fx2.tach(h, t, rpm, kmh, gear, spec.get("tag", ""), slow=slow, alpha=a, f=f, rate=rate)
    return gfx.over(img, h.overlay())


GLOBAL = dict(
    flashes=[(A["P2"], 0.1, 0.3), (A["P3"], 0.1, 0.25), (A["P4"], 0.1, 0.3), (A["DROP"], 0.25, 0.95), (A["S1"], 0.1, 0.45),
             (A["S2"], 0.08, 0.3), (A["X2"], 0.1, 0.4), (A["S3"], 0.08, 0.3), (18.1667, 0.12, 0.5), (A["S4"], 0.08, 0.3),
             (A["N4"], 0.1, 0.4), (A["S5"], 0.1, 0.5), (A["N5a"], 0.1, 0.45), (A["N5b"], 0.1, 0.45), (A["X6"], 0.1, 0.4),
             (24.9333, 0.1, 0.45), (A["S8"], 0.12, 0.5), (A["GL"], 0.18, 0.9), (A["DROPB"], 0.15, 0.5), (A["PB2"], 0.1, 0.35),
             (A["R2"], 0.15, 0.6), (A["PB3"], 0.2, 0.7), (A["L1"], 0.1, 0.6), (A["L2"], 0.12, 0.9, (1.0, 0.25, 0.2))],
    inverts=[(A["L2"] + 0.034, A["L2"] + 0.067, (1.0, 0.85, 0.85))],
    glitches=[(A["S8"], A["S8"] + 0.067, 1.0), (A["GL"] - 0.034, A["GL"], 0.8), (A["L1"], A["L1"] + 0.067, 0.8),
              (A["L2"], END, 1.2)],
    hits=[(A["DROP"], 1.0, 0.4), (A["S1"], 0.6), (A["S2"], 0.4), (A["X2"], 0.5), (A["S3"], 0.4), (A["S4"], 0.4),
          (A["S5"], 0.5), (A["N5a"], 0.4), (A["N5b"], 0.4), (A["S6"], 0.6), (A["S7"], 0.5), (A["GL"], 0.9, 0.35),
          (A["DROPB"], 0.6), (A["R2"], 0.7), (A["PB3"], 0.8, 0.35), (A["L1"], 0.8), (A["L2"], 1.0)],
    shocks=[(A["DROP"], 0.45, (960, 540), 46), (A["S1"], 0.4, (960, 520), 30), (A["GL"], 0.45, (700, 560), 44),
            (A["PB3"], 0.45, (960, 470), 34)],
    crt=[],
    halation=lambda t: 0.18 if t < A["DROP"] else (0.12 if t < A["GL"] else 0.2),
    vignette=lambda t: 0.38 if t < A["DROP"] else (0.3 if t < A["GL"] else 0.36),
    grain=lambda t: 0.022 if t < A["DROP"] or t >= A["GL"] else 0.016,
    bars=_bars,
    fade=lambda t: 0.0 if t >= END else (0.0 if t < 0.1 else min(1.0, (t - 0.1) / 0.25)),
    hud=hud,
)
