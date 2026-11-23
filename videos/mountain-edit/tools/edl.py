"""The edit: every shot, its timing, framing, speed, words and effects, locked to the audio (PLAN.md).

Times are output seconds (= seconds into the edit audio). A shot's `src` is (source in-point, speed) or a function
of output time; its `view` is (cx, cy, cw[, roll]) in the clip's display pixels, or a function of time.
"""
import math

import numpy as np

import gfx
import look
from media import FPS, H, W, frame_of, path, ramp

DURATION = 50.5
D1, D2, BEAT = 15.187, 29.879, 0.45913
END = 50.371                       # picture to black on the frame after the last word


def T(k):
    """The beat grid after the intro (k = 0 is drop 1, k = 32 drop 2)."""
    return D1 + BEAT * k


SHOTS, SPECS = [], {}


def shot(sid, t0, t1, **kw):
    s = dict(id=sid, t0=t0, t1=t1, F0=frame_of(t0), F1=frame_of(t1), **kw)
    s.setdefault("layout", "full")
    s.setdefault("fx", [])
    SHOTS.append(s)
    SPECS[sid] = s
    return s


def sub(sid, parent, **kw):
    """A panel / tile / layer spec: its own source and view, framed by a parent shot."""
    s = dict(id=sid, t0=parent["t0"], t1=parent["t1"], F0=parent["F0"], F1=parent["F1"], **kw)
    s.setdefault("fx", [])
    SPECS[sid] = s
    return sid


def word(t, text, pos, size=300, color=gfx.WHITE, font=gfx.F_BIG, behind=False, until=None, **kw):
    if "from_" in kw:
        kw["from"] = kw.pop("from_")
    d = dict(t=t, text=text, pos=pos, size=size, color=color, font=font, behind=behind, **kw)
    if until is not None:
        d["until"] = until
    return d


RED, WHITE = gfx.RED, gfx.WHITE
PULSE = [T(k) for k in range(0, 29)] + [T(k) for k in range(33, 66)]       # beats in drop 1 and drop 2
SERIF, MONO, MONOB = gfx.F_SERIF, gfx.F_MONO, gfx.F_MONOB

# =========================================================================================== overlays

def hud_subject(label="SUBJECT 01", top_frac=1.05, data=None, prog=None, vf=True, lock_t=None, pts=0):
    """Scanner HUD on the matte's subject: brackets on the head, readouts, an optional sequencing bar."""
    def fx(img, spec, t, f, m, R):
        h = gfx.Hud()
        if vf:
            gfx.viewfinder(h, f, 3600 * 4 + 1800)
        if m is not None:
            box = R.matte_box(m, top_frac)
            if box is not None:
                lock = 1.0 if lock_t is None else float(np.clip((t - lock_t) / 0.25, 0, 1))
                x0, y0, x1, y1 = box
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                d = data(t, f, cx, cy) if data else [f"X {cx:06.1f}", f"Y {cy:06.1f}", f"CONF 0.{97 - (f % 5)}"]
                gfx.target_box(h, box, t, label, d, lock=lock, f=f)
                if pts:
                    # a fixed constellation in the subject's own box: it moves and scales with him (tracked)
                    full = R.matte_box(m, None)
                    if full is not None:
                        X0, Y0, X1, Y1 = full
                        rng = np.random.default_rng(spec["F0"])
                        uv = rng.random((pts * 3, 2))
                        P = np.stack([X0 + uv[:, 0] * (X1 - X0), Y0 + uv[:, 1] * (Y1 - Y0)], 1)
                        keep = [p for p in P if m[min(H - 1, int(p[1])), min(W - 1, int(p[0]))] > 0.6][:pts]
                        if keep:
                            gfx.points(h, np.array(keep))
        if prog:
            t0, t1, p0, p1, lab = prog
            u = float(np.clip((t - t0) / (t1 - t0), 0, 1))
            gfx.progress(h, W - 640, H - 200, 420, p0 + (p1 - p0) * u, lab)
        return gfx.over(img, h.overlay())
    return fx


def hud_target(label, top_frac=None, data=None, color=gfx.HUDC):
    """A target lock on whatever the matte holds (a car), with a speed-style readout from its motion."""
    state = {}

    def fx(img, spec, t, f, m, R):
        if m is None or any(x[0] == "whip" and x[1] - 0.02 <= t < x[2] + 0.02 for x in spec.get("fx", [])):
            return img
        box = R.matte_box(m, top_frac)
        if box is None:
            return img
        h = gfx.Hud()
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        prev = state.get(f - 1)
        state[f] = (cx, cy)
        v = 0.0 if prev is None else math.hypot(cx - prev[0], cy - prev[1])
        lock = float(np.clip((t - spec["t0"]) / 0.2, 0, 1))
        d = data(t, f, cx, cy, v) if data else [f"TRK {spec['id']}", f"V {v:05.1f} PX/F", f"X {cx:04.0f} Y {cy:04.0f}"]
        gfx.target_box(h, box, t, label, d, lock=lock, f=f)
        h.line((0, cy), (x0 - 20, cy), color, 0.35, 1)
        h.line((x1 + 20, cy), (W, cy), color, 0.35, 1)
        return gfx.over(img, h.overlay())
    return fx


def helix_fx(t0, t1, x, y, height, radius, grow=0.6, alpha=0.9, spin=1.6, color=WHITE, accent=RED):
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1):
            return img
        ov = gfx.blank()
        p = float(np.clip((t - t0) / grow, 0, 1))
        a = alpha * min(1.0, (t1 - t) / 0.12)
        gfx.helix(ov, x, y, height, radius, spin * t, p, alpha=a, color=color, accent=accent)
        return gfx.over(img, ov)
    return fx


def rain_fx(t0, t1, peak=0.85, ramp=0.5):
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1):
            return img
        a = peak * min(1.0, (t - t0) / ramp) * min(1.0, (t1 - t) / 0.1)
        ov = gfx.blank()
        gfx.code_rain(ov, t, a, size=32, density=1.15)
        g = img * np.array([0.75, 1.0, 0.8], np.float32)              # green the world a little
        return gfx.over(img * (1 - 0.5 * a) + g * 0.5 * a, ov)
    return fx


def stars_fx(times, n=7, size=(0.35, 0.9), seed=4):
    """Diamond glints on the brightest points of the frame, bursting at each time in `times`."""
    def fx(img, spec, t, f, m, R):
        L = look.luma(img)
        small = cv2_resize(L, (W // 8, H // 8))
        # local maxima of brightness
        import cv2
        dil = cv2.dilate(small, np.ones((9, 9), np.uint8))
        ys, xs = np.nonzero((small >= dil) & (small > 0.72))
        if len(xs) == 0:
            return img
        order = np.argsort(-small[ys, xs])[:n]
        rng = np.random.default_rng(seed)
        out = img
        for k, i in enumerate(order):
            e = max(look.env_hit(t, tt + 0.03 * k, 0.04, 0.5, 1.6) for tt in times)
            tw = 0.55 + 0.45 * math.sin(t * 9 + k * 1.7)
            sc = size[0] + (size[1] - size[0]) * rng.random()
            out = gfx.add_star(out, xs[i] * 8 + 4, ys[i] * 8 + 4, sc * (0.6 + 0.8 * e), 0.35 * tw + 0.9 * e,
                               angle=12 * math.sin(t + k))
        return out
    return fx


def sunflare_fx(strength=0.8, color=(0.55, 0.8, 1.0)):
    """An anamorphic streak and glow on the brightest blob in frame (the sun), found per frame."""
    import cv2

    def fx(img, spec, t, f, m, R):
        L = look.luma(img)
        small = cv2.GaussianBlur(cv2.resize(L, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 2)
        y, x = np.unravel_index(np.argmax(small), small.shape)
        if small[y, x] < 0.82:
            return img
        cx, cy = x * 8 + 4, y * 8 + 4
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        dx, dy = (xx - cx / 4), (yy - cy / 4)
        streak = np.exp(-(dy / 1.6) ** 2) * np.exp(-np.abs(dx) / 140.0)
        glow = np.exp(-(dx ** 2 + dy ** 2) / (2 * 26.0 ** 2)) * 0.6
        ring = np.exp(-((np.sqrt((xx - (W / 8 - dx * 0.0) * 0 - (W / 4 - cx / 4)) ** 2 + (yy - (H / 4 - cy / 4)) ** 2) - 18) / 4) ** 2) * 0.15
        fl = cv2.resize((streak + glow + ring).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        add = fl[..., None] * np.array(color, np.float32) * strength
        return 1 - (1 - img) * (1 - np.clip(add, 0, 1))
    return fx


def cv2_resize(x, size):
    import cv2
    return cv2.resize(x, size, interpolation=cv2.INTER_AREA)


def leak_fx(t0, t1, strength=0.45, seed=1):
    def fx(img, spec, t, f, m, R):
        if not (t0 <= t < t1):
            return img
        a = strength * min(1.0, (t - t0) / 0.3) * min(1.0, (t1 - t) / 0.3)
        return gfx.light_leak(img, t, a, seed)
    return fx


def mono_line(t0, text, x, y, size=22, until=None, typing=True, color=gfx.HUDC):
    """A HUD line that types itself on."""
    def fx(img, spec, t, f, m, R):
        if t < t0 or (until and t >= until):
            return img
        n = len(text) if not typing else int((t - t0) * 40)
        s = text[:max(0, n)]
        if not s:
            return img
        h = gfx.Hud()
        cur = "_" if (f // 8) % 2 == 0 and n < len(text) + 8 else ""
        h.text(s + cur, x, y, size, color, 0.95, MONO)
        return gfx.over(img, h.overlay())
    return fx


# =========================================================================================== custom layouts

def draw_cold_open(spec, t, f, R):
    """Black; a helix draws itself; the HUD types the job; two-frame subliminal flashes of him."""
    if f in (9, 10):                                   # his photo, inverted, for two frames
        s = SPECS["F1"]
        return look.invert(look.grade(R.photo_frame(s, s["t0"], f), "intro"), 1.0, (1.0, 0.8, 0.8))
    if f in (18, 19):                                  # the shades, for two frames
        s = SPECS["B2"]
        return look.grade(R.base_full("B2", s, s["t0"] + 0.05, f), "intro") * 0.85
    img = np.zeros((H, W, 3), np.float32)
    ov = gfx.blank()
    p = float(np.clip(t / 0.85, 0, 1))
    gfx.helix(ov, W / 2, H / 2, 600, 96, 1.2 + 2.2 * t, p, alpha=0.95, th=4)
    img = gfx.over(img, ov)
    h = gfx.Hud()
    s = "SEQUENCING SUBJECT 01"[:int(t * 34)]
    h.text(s, W / 2, H / 2 + 270, 22, gfx.HUDC, 0.9, MONO, anchor="ma")
    return gfx.over(img, h.overlay())


def card_word(text, color, bgcol=(0, 0, 0), size=420, font=gfx.F_BIG):
    def draw(spec, t, f, R):
        img = np.zeros((H, W, 3), np.float32) + np.array(bgcol, np.float32)
        ov = gfx.blank()
        sc, a = gfx.slam(t, spec["t0"], 0.08, 1.25) or (1, 1)
        gfx.place(ov, gfx.text(text, font, size, color, 0.02), W / 2, H / 2, sc, a, 2 * max(0, sc - 1) * 6)
        return gfx.over(img, ov)
    return draw


def draw_title(spec, t, f, R):
    """The end card: his white silhouette (the last matte of the edge shot), the helix and DNA."""
    import cv2
    import os
    img = np.zeros((H, W, 3), np.float32) + np.array([0.02, 0.02, 0.025], np.float32)
    mp = os.path.join(R.CACHE, "matte", "F3", f"{SPECS['F3']['F1'] - 1:05d}.png")
    if os.path.exists(mp):
        m = cv2.imread(mp, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        u = (t - spec["t0"]) / (spec["t1"] - spec["t0"])
        k = 1.0 + 0.06 * u
        M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
        m = cv2.warpAffine(m, M, (W, H))
        img = img * (1 - m[..., None]) + m[..., None] * 0.96
        edge = np.clip(cv2.GaussianBlur(m, (0, 0), 16) - m, 0, 1) * 1.8
        img = 1 - (1 - img) * (1 - edge[..., None] * np.array([1.0, 0.25, 0.2], np.float32))
    ov = gfx.blank()
    gfx.helix(ov, 330, H / 2, 560, 80, 2.0 * t, float(np.clip((t - spec["t0"]) / 0.3, 0, 1)), alpha=0.9)
    sc, a = gfx.slam(t, spec["t0"] + 0.02, 0.1, 1.3) or (1, 1)
    gfx.place(ov, gfx.text("DNA.", gfx.F_BIG, 360, RED, 0.02), W - 420, H / 2, sc, a)
    return gfx.over(img, ov)


def draw_stutter(spec, t, f, R):
    """Two-frame flashes of the hero shots before drop 2."""
    k = (f - spec["F0"]) // 2
    keys = spec["frames"]
    key = keys[min(k, len(keys) - 1)]
    s = SPECS[key]
    if s.get("layout") == "photo":
        img = R.photo_frame(s, s["t0"] + 0.3, f)
    else:
        img = R.base_full(key, s, s["t0"] + 0.1, f)
    g = look.grade(img, "intro")
    if k % 2 == 1:
        g = look.invert(g, 1.0, (1.0, 0.85, 0.85))
    return g


# =========================================================================================== the shots
# ---- A. cold open
shot("A1", 0.0, 0.951, layout="custom", draw=draw_cold_open, look=None)

# ---- B. intro: 2.39:1, slow motion, cool
shot("B1", 0.951, 1.84, clip="0418", src=(0.02, 0.5), view=(1080, 2250, 2160), look="intro", matte="isnet",
     pre=[("sky", 0.45, 0.55)], fx=[("punch", 0.951, 0.05, 0.6), ("handheld", 3)],
     words=[word(0.951, "LOYALTY", (960, 455), 410, WHITE, behind=True, tracking=0.03, dur=0.09)],
     overlays=[hud_subject("SUBJECT 01", 1.0, lock_t=1.15, prog=(0.951, 4.41, 0.0, 0.42, "SEQUENCING DNA"))])

shot("B2", 1.84, 2.65, clip="0434", src=(0.02, 0.5), view=(1920, 1080, 3840), look="intro", matte="isnet",
     pre=[("sky", 0.4, 0.6)], fx=[("punch", 1.84, 0.06, 0.4), ("handheld", 3)],
     words=[word(1.84, "ROYALTY", (1250, 300), 330, RED, behind=True, tracking=0.03, dur=0.09)],
     overlays=[hud_subject("SUBJECT 01", 0.95, lock_t=1.9, vf=True, prog=(0.951, 4.41, 0.0, 0.42, "SEQUENCING DNA"))])

shot("B3", 2.65, 4.412, clip="0434", src=(1.40, 0.72), view=path([(2.65, 1920, 1080, 3840), (4.41, 1950, 1120, 3500)]),
     look="intro", matte="isnet", pre=[("sky", 0.4, 0.6)], fx=[("handheld", 3), ("punch", 3.28, 0.07, 0.5)],
     words=[word(3.28, "DNA.", (1490, 520), 380, RED, behind=True, tracking=0.02, dur=0.1)],
     overlays=[hud_subject("SUBJECT 01", 1.0, lock_t=2.7, pts=26, prog=(0.951, 4.41, 0.0, 0.42, "SEQUENCING DNA")),
               helix_fx(3.1, 4.412, 1790, 540, 600, 62, grow=0.5)])

# ---- the broadcast (CRT) section under the news sample
shot("B4", 4.412, 5.70, clip="0430", src=(1.62, 1.0), view=(1600, 900, 2300), look="intro", fx=[("handheld", 4)])
shot("B5", 5.70, 6.90, clip="7910", src=(9.55, 1.0), view=(1080, 2520, 2160), look="intro", fx=[("handheld", 3)])
shot("B6", 6.90, 8.200, clip="0439", src=(3.35, 1.5), view=path([(6.9, 1080, 1900, 2160), (8.2, 1080, 2050, 2160)]),
     look="intro")

# ---- colour returns: the crew
shot("B7", 8.200, 9.68, clip="0462", src=(0.45, 0.6), view=(540, 1350, 1080), look="crew", fx=[("punch", 8.2, 0.08, 0.5)])
shot("B8", 9.68, 10.149, clip="0437", src=(0.05, 1.6), view=(1920, 1000, 3400), look="crew")
shot("B9", 10.149, 11.58, layout="photo", clip="0402", view=(1150, 1980, 2252), look="crew",
     bg_zoom=(1.0, 1.035), fg_zoom=(1.0, 1.1), pan=(-0.01, 0.0), fx=[("punch", 10.149, 0.05, 0.4)],
     overlays=[lambda img, s, t, f, m, R: gfx.add_star(img, 1165, 440, 0.9 * look.env_hit(t, 10.149, 0, 0.5, 1.5) + 0.05,
                                                     1.2 * look.env_hit(t, 10.149, 0, 0.6, 1.4))])
shot("B10", 11.58, 11.97, layout="black", look=None)
shot("B11", 11.97, 12.88, clip="0441", src=(9.2, 1.0), view=(540, 1100, 1080), look="intro", fx=[("zoom", 11.97, 12.88, 1.0, 1.06)],
     words=[word(12.40, "HERITAGE", (960, 520), 240, WHITE, tracking=0.14, dur=0.14, from_=1.1, alpha=0.95)])
shot("B12", 12.88, 13.76, clip="0438", src=(5.2, 1.0), view=(1920, 1080, 3840), look="intro",
     fx=[("handheld", 3), ("zoomblur", 13.60, 13.76, 0.45, 1)])

# ---- the build: money and power
shot("B13", 13.76, 13.93, layout="custom", draw=card_word("MONEY", WHITE), look=None)
shot("B14", 13.93, 14.08, clip="0397", src=(3.75, 1.0), view=(1920, 1080, 3400), look="rally")
shot("B15", 14.08, 14.26, layout="custom", draw=card_word("POWER", RED), look=None)
shot("B16", 14.26, 14.45, clip="0465", src=(6.10, 1.0), view=(1080, 2650, 2160), look="rally", fx=[("punch", 14.26, 0.1, 0.2)])
shot("B17", 14.45, 14.60, clip="0461", src=(10.12, 1.0), view=(540, 1150, 1080), look="rally")
shot("B18", 14.60, 14.72, clip="0395", src=(6.48, 1.0), view=(540, 1200, 1080), look="rally")
shot("B19", 14.72, 14.84, clip="0467", src=(6.72, 1.0), view=(960, 560, 1920), look="rally")
shot("B20", 14.84, 14.94, clip="0396", src=(4.58, 1.0), view=(540, 1250, 1080), look="rally")
shot("B21", 14.94, 15.04, clip="0418", src=(1.0, 1.0), view=(1080, 2300, 2160), look="intro", fx=[("punch", 14.94, 0.2, 0.15)])
shot("B22", 15.04, D1, layout="black", look=None)

# ---- C. drop 1: the rally, full frame, warm dust
shot("C1", D1, 16.20, clip="0397", src=(3.70, 0.85), view=(1920, 1080, 3600), look="rally", matte="isnet",
     fx=[("punch", D1, 0.16, 0.45), ("shake", D1, 26, 0.55, 1), ("whip", 16.10, 16.20, -1, 0.9, "out")],
     words=[word(D1, "DNA.", (960, 500), 560, RED, behind=True, tracking=0.02, dur=0.08, from_=1.5)],
     overlays=[hud_target("TARGET 14", None)])
shot("C2", 16.20, 16.96, clip="0395", src=ramp([(16.20, 6.10), (16.40, 6.42), (16.80, 6.58), (16.96, 6.70)]), blend=True,
     view=(540, 1200, 1080), look="rally", matte="isnet", overlays=[hud_target("TARGET 22", None)],
     fx=[("whip", 16.20, 16.30, -1, 0.9, "in"), ("shake", 16.20, 16, 0.4, 2), ("whip", 16.86, 16.96, 1, 0.9, "out")])
shot("C3", 16.96, 17.76, clip="0465", src=(6.0, 1.0), matte="isnet", overlays=[hud_target("TARGET 53", None)], view=path([(16.96, 1080, 1900, 2160), (17.4, 1080, 2500, 2160), (17.76, 1080, 2700, 2160)]), look="rally",
     fx=[("whip", 16.96, 17.06, 1, 0.9, "in"), ("punch", 17.30, 0.08, 0.3)])
shot("C4", 17.76, 18.80, clip="0396", src=(5.0, 0.5), view=(540, 1380, 1080), look="rally", fx=[("handheld", 6)],
     words=[word(17.76, "CAN'T", (960, 330), 230, WHITE, tracking=0.03),
            word(18.00, "tell me", (960, 520), 150, WHITE, font=SERIF),
            word(18.32, "NOTHIN'", (960, 730), 280, RED, tracking=0.02)])
shot("C5", 18.80, 19.52, clip="0467", src=(6.05, 1.0), view=(960, 540, 1920), look="rally", fx=[("zoom", 18.8, 19.52, 1.0, 1.28)],
     words=[word(18.80, "I'd rather", (960, 250), 130, WHITE, font=SERIF),
            word(19.28, "DIE.", (960, 640), 420, RED, tracking=0.02)])
shot("C6", 19.52, 20.64, clip="0461", src=ramp([(19.52, 9.85), (19.75, 10.12), (20.30, 10.30), (20.64, 10.45)]), blend=True, view=(540, 1150, 1080), look="rally", matte="isnet",
     fx=[("shake", 19.52, 14, 0.4, 3), ("whip", 20.54, 20.64, -1, 0.9, "out")], overlays=[hud_target("TARGET 07", None)])

C7 = shot("C7", 20.64, 22.56, layout="panels", look="rally", panels=[])
for i, (clip, s0, sp, cx, cy, cw, appear) in enumerate([("0395", 6.10, 0.5, 540, 1250, 900, 20.64),
                                                         ("0461", 9.80, 0.5, 540, 1150, 900, 20.88),
                                                         ("0465", 5.55, 1.0, 1080, 2150, 1800, 21.36)]):
    x0 = i * 640 + (4 if i else 0)
    x1 = (i + 1) * 640 - (4 if i < 2 else 0)
    C7["panels"].append(sub(f"C7p{i}", C7, clip=clip, src=(lambda t, s0=s0, sp=sp, a=appear: s0 + max(0.0, t - a + 0.2) * sp),
                            view=(cx, cy, cw), aspect=(x1 - x0) / H, rect=(x0, 0, x1, H), appear=appear, style="slide_up",
                            look="rally"))
C7["words"] = [word(21.36, "not for", (960, 360), 150, WHITE, font=SERIF),
               word(21.52, "IMITATION", (960, 600), 300, RED, tracking=0.03)]

shot("C8", 22.56, 23.90, clip="0396", src=(4.30, 0.5), view=(540, 1250, 1080), look="rally",
     fx=[("whip", 22.56, 22.66, 1, 0.8, "in"), ("shake", 22.56, 20, 0.5, 4)],
     words=[word(23.44, "ABOMINATION", (960, 560), 270, RED, tracking=0.03, dur=0.06)])
shot("C9", 23.90, 24.32, clip="0397", src=(5.10, 1.0), view=(1920, 1080, 3700), look="rally")
shot("C10", 24.32, 25.92, clip="0465", src=(7.25, 0.5), view=(1080, 2200, 2160), look="rally", blend=True,
     fx=[("zoom", 24.32, 25.92, 1.0, 1.12)],
     words=[word(25.52, "THE MATRIX", (960, 540), 200, (0.55, 1.0, 0.65), font=MONOB, tracking=0.1, dur=0.06)],
     overlays=[rain_fx(24.32, 25.92, 1.0, 0.45)])
shot("C11", 25.92, 26.38, clip="0393", src=(0.50, 1.0), view=(1920, 1080, 3840), look="rally", fx=[("punch", 25.92, 0.08, 0.3)])
shot("C12", 26.38, 26.84, clip="0467", src=(7.55, 1.0), view=(960, 560, 1920), look="rally", fx=[("punch", 26.38, 0.08, 0.3)])
shot("C13", 26.84, 27.07, clip="0395", src=(6.85, 1.0), view=(540, 1250, 1080), look="rally")
shot("C14", 27.07, 27.30, clip="0461", src=(11.40, 1.0), view=(540, 1300, 1080), look="rally")
shot("C15", 27.30, 27.52, clip="0465", src=(6.15, 1.0), view=(1080, 2150, 2160), look="rally")

C16 = shot("C16", 27.52, 28.482, layout="panels", look="rally", panels=[])
tiles = [("0397", 4.3, 1920, 1080, 3840), ("0395", 6.5, 540, 1200, 1080), ("0465", 6.2, 1080, 2150, 2160),
         ("0461", 10.2, 540, 1150, 1080), ("0418", 2.0, 1080, 2300, 2160), ("0396", 4.6, 540, 1250, 1080),
         ("0467", 7.7, 960, 560, 1920), ("0434", 5.0, 1920, 1080, 3840), ("0393", 1.5, 1920, 1080, 3840)]
order = [4, 0, 8, 2, 6, 1, 7, 3, 5]                 # the centre first, then around
for n, k in enumerate(order):
    clip, s0, cx, cy, cw = tiles[k]
    r, c = divmod(k, 3)
    x0, y0 = c * 640 + 4, r * 360 + 4
    appear = 27.52 + n * BEAT / 4
    C16["panels"].append(sub(f"C16t{k}", C16, clip=clip, src=(lambda t, s0=s0, a=appear: s0 + max(0.0, t - a)),
                             view=(cx, cy, cw), rect=(x0, y0, x0 + 632, y0 + 352), appear=appear, style="pop", anim=0.08,
                             look="rally" if k not in (4, 7) else "summit", max_scale=0.4))
C16["overlays"] = [mono_line(27.52, "FOOTAGE // STACKING 09 CLIPS", 60, H - 70, 22)]

# ---- D. the break: bass cut, letterbox, slow motion, glowing outline
shot("D1", 28.482, 29.60, clip="0430", src=(2.25, 0.5), view=(1600, 900, 2100), look="intro", matte="human",
     fx=[("glow", 28.482, 29.60, (1.0, 0.95, 0.9), 1.0), ("zoom", 28.482, 29.6, 1.0, 1.08)],
     overlays=[sunflare_fx(0.7), hud_subject("SUBJECT 01", 0.5, vf=True, prog=(28.482, 29.6, 0.87, 0.99, "SEQUENCING DNA"))])
shot("D2", 29.60, D2, layout="custom", draw=draw_stutter, look=None, frames=["B1", "B2", "F1", "B3"])

# ---- E. drop 2: the summit and the monsoon
shot("E1", D2, 31.28, clip="0434", src=ramp([(D2, 3.40), (30.10, 3.75), (31.28, 4.55)]), view=(1920, 1080, 3840), look="summit", matte="human",
     fx=[("cutout", D2, D2 + 2 / 30), ("punch", D2, 0.15, 0.5), ("shake", D2, 22, 0.5, 5)],
     overlays=[leak_fx(D2, 31.28, 0.4, 2)])
E2 = shot("E2", 31.28, 32.16, layout="panels", look="summit", panels=[])
E2["panels"] += [sub("E2a", E2, clip="0462", src=(lambda t: 2.0 + (t - 31.28) * 0.6), view=(540, 1300, 1000), aspect=956 / H,
                     rect=(0, 0, 956, H), appear=31.28, style="slide_down", look="summit"),
                 sub("E2b", E2, clip="9948", src=(lambda t: 0.4 + (t - 31.28)), view=(1080, 2200, 2000), aspect=956 / H,
                     rect=(964, 0, W, H), appear=31.52, style="slide_up", look="summit")]
shot("E3", 32.16, 33.04, clip="0472", src=(13.0, 1.0), view=path([(32.16, 540, 800, 1080, 0), (33.04, 540, 800, 1000, 6)]),
     look="summit", overlays=[stars_fx([32.16, 32.56])])
shot("E4", 33.04, 33.92, clip="0441", src=(1.50, 1.0), view=(540, 1150, 1080), look="summit",
     fx=[("whip", 33.04, 33.14, 1, 0.8, "in")])
shot("E5", 33.92, 35.84, layout="card", clip="9685", src=(9.0, 1.0), view=(540, 1000, 1080), look="summit",
     card=(1060, 600), grow=(34.88, 35.12), radius=44)
shot("E6", 35.84, 36.72, clip="0446", src=(4.6, 1.0), view=(540, 1400, 1080), look="summit", fx=[("punch", 35.84, 0.08, 0.3)])
shot("E7", 36.72, 38.64, clip="7910", src=(13.6, 1.0), view=(1080, 2350, 2160), look="summit",
     fx=[("punch", 36.72, 0.07, 0.35), ("punch", T(49), 0.05, 0.3), ("handheld", 3)])
shot("E8", 38.64, 39.84, clip="0418", src=(2.0, 1.0), view=(1080, 2300, 2160), look="summit", matte="human",
     overlays=[hud_subject("SUBJECT 01", 0.9, lock_t=38.7, data=lambda t, f, cx, cy: ["STATUS  LOCKED", f"X {cx:06.1f}", f"Y {cy:06.1f}"])])
shot("E9", 39.84, 40.48, clip="0461", src=(11.30, 1.0), view=(540, 1350, 1080), look="summit")
shot("E10", 40.48, 40.96, layout="photo", clip="0402", view=(1450, 2050, 1700), look="crew",
     bg_zoom=(1.0, 1.03), fg_zoom=(1.0, 1.08))
shot("E11", 40.96, T(58), clip="0437", src=(1.60, 1.0), view=(1900, 1000, 3300), look="crew")
shot("E12", T(58), T(60), clip="0439", src=(4.6, 1.0), view=(1080, 2350, 2160), look="summit", overlays=[sunflare_fx(0.8)], fx=[("whip", T(58), T(58) + 0.1, -1, 0.8, "in")])
shot("E13", T(60), T(62), clip="0430", src=(4.0, 0.5), view=(1600, 900, 2300), look="summit", fx=[("punch", T(60), 0.08, 0.35)],
     overlays=[sunflare_fx(0.8)])
shot("E14", T(62), T(64), clip="9948", src=(1.8, 1.0), view=(1080, 2150, 2160), look="summit", fx=[("whip", T(62), T(62) + 0.1, 1, 0.8, "in")])
shot("E15", T(64), T(66), layout="photo", clip="4838", rotate=90, view=(1046, 520, 2092), look="summit",
     bg_zoom=(1.0, 1.05), fg_zoom=(1.0, 1.12), pan=(0.02, 0.0))

# ---- F. the slide, the outro
shot("F1", T(66), 46.83, layout="photo", clip="0413", view=(1134, 2650, 2268), look="intro",
     bg_zoom=(1.0, 1.42), fg_zoom=(1.0, 1.04), fx=[("punch", T(66), 0.06, 0.4)],
     overlays=[hud_subject("SUBJECT 01", None, vf=True, prog=(T(66), 46.5, 0.99, 1.0, "DNA MATCH"))])
shot("F2", 46.83, 48.80, clip="0434", src=(6.60, 0.5), view=(2050, 1250, 3000), look="intro", matte="human",
     pre=[("sky", 0.35, 0.6)], fx=[("zoom", 46.83, 48.8, 1.0, 1.08)],
     overlays=[hud_subject("SUBJECT 01", 0.5, lock_t=47.0)])
shot("F3", 48.80, 49.68, clip="0434", src=(11.60, 0.5), view=(2350, 1250, 2300), look="intro", matte="isnet",
     pre=[("sky", 0.35, 0.6)], fx=[("zoom", 48.8, 49.68, 1.0, 1.06)],
     words=[word(48.80, "I don't", (960, 380), 140, WHITE, font=SERIF),
            word(49.04, "COMPROMISE", (960, 600), 330, WHITE, behind=True, tracking=0.04)])
shot("F4", 49.68, END, layout="custom", draw=draw_title, look=None)

SHOTS.sort(key=lambda s: s["F0"])
for a, b in zip(SHOTS, SHOTS[1:]):
    assert a["F1"] == b["F0"], (a["id"], a["F1"], b["id"], b["F0"])

# =========================================================================================== global finishing

def _bars(t):
    def blend(a, b, u):
        u = float(np.clip(u, 0, 1))
        u = u * u * (3 - 2 * u)
        ra, rb = W / a, W / b                     # picture heights
        return W / (ra + (rb - ra) * u)
    if t < D1:
        return 2.39
    if t < D1 + 0.12:
        return blend(2.39, 16 / 9, (t - D1) / 0.12)
    if t < 28.482:
        return 16 / 9
    if t < D2:
        return blend(16 / 9, 2.39, (t - 28.482) / 0.25)
    if t < D2 + 0.12:
        return blend(2.39, 16 / 9, (t - D2) / 0.12)
    if t < 46.83:
        return 16 / 9
    return blend(16 / 9, 2.39, (t - 46.83) / 0.4)


GLOBAL = dict(
    flashes=[(0.30, 0.08, 0.6), (0.60, 0.08, 0.5), (0.951, 0.4, 0.95), (1.84, 0.2, 0.45), (3.28, 0.3, 0.55, (1.0, 0.75, 0.7)), (4.412, 0.25, 0.9),
             (8.200, 0.45, 1.0), (10.149, 0.35, 1.0), (11.97, 0.25, 0.5), (13.93, 0.1, 0.5), (14.26, 0.18, 0.9), (D1, 0.5, 1.0), (16.20, 0.3, 0.85),
             (18.32, 0.15, 0.4), (19.28, 0.22, 0.6, (1.0, 0.55, 0.5)), (22.56, 0.15, 0.7), (23.44, 0.15, 0.6),
             (25.52, 0.22, 0.6, (0.6, 1.0, 0.7)), (25.92, 0.1, 0.4), (26.38, 0.1, 0.4), (28.482, 0.35, 0.6),
             (D2, 0.55, 1.0), (32.16, 0.25, 0.5, (1.0, 0.92, 0.8)), (33.04, 0.12, 0.35), (34.88, 0.2, 0.5), (35.84, 0.15, 0.4),
             (36.72, 0.2, 0.5), (38.64, 0.15, 0.4), (39.84, 0.07, 1.0), (40.00, 0.07, 1.0), (40.16, 0.07, 1.0),
             (40.32, 0.07, 1.0), (40.48, 0.2, 0.9), (40.96, 0.2, 0.8), (T(58), 0.15, 0.4), (T(60), 0.15, 0.45),
             (T(62), 0.15, 0.4), (T(64), 0.15, 0.45), (T(66), 0.4, 1.0), (46.83, 0.3, 0.5), (49.04, 0.2, 0.5),
             (49.68, 0.35, 0.85), (50.24, 0.13, 1.0)],
    inverts=[(22.56, 22.76, (1.0, 0.88, 0.88)), (14.94, 15.04)],
    glitches=[(4.40, 4.47, 1.0), (8.17, 8.22, 0.8), (22.56, 22.66, 1.0), (23.40, 23.50, 1.0), (25.48, 25.62, 1.2),
              (29.80, D2, 0.8)],
    hits=[(0.951, 0.6), (4.412, 0.8), (8.2, 0.6), (D1, 1.0, 0.4), (16.2, 0.7), (19.28, 0.5), (22.56, 0.9), (23.44, 0.7),
          (25.52, 0.9), (28.482, 0.6), (D2, 1.0, 0.4), (T(66), 0.8, 0.4), (49.68, 0.6)],
    crt=[(4.412, 8.200)],
    halation=lambda t: 0.16 if t < D1 else (0.1 if t < 28.482 else 0.2),
    vignette=lambda t: 0.5 if 4.412 <= t < 8.2 else 0.32,
    grain=lambda t: 0.02 if (t < D1 or t > 46.83) else 0.016,
    bars=_bars,
    fade=lambda t: 0.0 if t >= END else 1.0,
)
