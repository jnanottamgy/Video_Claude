"""The titles: ivory-to-gold serif type, letter by letter, with a soft shadow, a warm glow and a dark scrim.

Fonts (renders/fonts): Cinzel (the big Roman caps), Marcellus (small caps lines), Cormorant Garamond
italic (the spoken lines), Noto Serif Kannada (the event's name, shaped by raqm).
Safe zone: Instagram covers the top ~200 px and the bottom ~400 px, and the right edge has the buttons,
so the type lives between y 260 and y 1480, x 70 and x 960.
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "renders/fonts")
W, H = 1080, 1920
CINZEL = "cinzel-latin-700-normal.ttf"
MARCELLUS = "marcellus-latin-400-normal.ttf"
ITALIC = "cormorant-garamond-latin-500-italic.ttf"
KANNADA = "noto-serif-kannada-kannada-700-normal.ttf"
KANNADA_M = "noto-serif-kannada-kannada-500-normal.ttf"

GOLD_STOPS = [(0.0, (1.0, 0.97, 0.88)), (0.45, (1.0, 0.86, 0.56)), (1.0, (0.88, 0.63, 0.30))]
IVORY_STOPS = [(0.0, (1.0, 0.98, 0.93)), (1.0, (0.98, 0.90, 0.74))]

_fonts = {}


def font(name, size):
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(os.path.join(FONTS, name), size,
                                                  layout_engine=ImageFont.Layout.RAQM)
    return _fonts[(name, size)]


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def ease_in_out(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


class Line:
    """One line of type, as per-letter masks (Latin) or one shaped mask (Kannada)."""

    def __init__(self, text, face, size, tracking=0.0, per_char=True, stops=GOLD_STOPS):
        f = font(face, size)
        asc, desc = f.getmetrics()
        self.size, self.h, self.asc = size, asc + desc, asc
        self.stops = stops
        pad = size // 3
        self.pad = pad
        self.parts = []                                   # (x of glyph origin, mask)
        if per_char:
            for k, ch in enumerate(text):
                if ch == " ":
                    continue
                xk = f.getlength(text[:k]) + k * tracking
                im = Image.new("L", (int(f.getlength(ch)) + 2 * pad, self.h + 2 * pad), 0)
                ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255)
                self.parts.append((xk, np.asarray(im, np.float32) / 255))
            self.w = f.getlength(text) + max(0, len(text) - 1) * tracking
        else:
            wl = int(f.getlength(text)) + 2 * pad
            im = Image.new("L", (wl, self.h + 2 * pad), 0)
            ImageDraw.Draw(im).text((pad, pad), text, font=f, fill=255)
            self.parts.append((0.0, np.asarray(im, np.float32) / 255))
            self.w = f.getlength(text)
        self.n = len(self.parts)

    def colour(self, hpx):
        """Vertical gradient (hpx, 1, 3) over the glyph box."""
        u = np.linspace(-self.pad / self.h, 1 + self.pad / self.h, hpx)
        out = np.zeros((hpx, 3), np.float32)
        for c in range(3):
            out[:, c] = np.interp(u, [s[0] for s in self.stops], [s[1][c] for s in self.stops])
        return out[:, None, :]


class Canvas:
    """Accumulates text masks (with their colours) in a frame-sized region, then composites them."""

    def __init__(self):
        self.mask = np.zeros((H, W), np.float32)
        self.col = np.zeros((H, W, 3), np.float32)
        self.box = [W, H, 0, 0]

    def put(self, m, rgb, x, y, alpha):
        """Blit mask m (h, w) with colour rgb (h, 1, 3) or (h, w, 3) at integer-ish (x, y), max-combined."""
        if alpha <= 0.002:
            return
        h, w = m.shape
        # sub-pixel placement keeps slow drifts smooth
        fx, fy = x - math.floor(x), y - math.floor(y)
        if fx > 0.01 or fy > 0.01:
            mt = np.float32([[1, 0, fx], [0, 1, fy]])
            m = cv2.warpAffine(m, mt, (w + 1, h + 1), flags=cv2.INTER_LINEAR)
            rgb = np.broadcast_to(rgb, (h, w, 3)) if rgb.shape[1] == 1 else rgb
            rgb = cv2.warpAffine(np.ascontiguousarray(rgb), mt, (w + 1, h + 1), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
            h, w = m.shape
        x, y = int(math.floor(x)), int(math.floor(y))
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        ms = m[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
        cs = np.broadcast_to(rgb, (h, w, 3))[y0 - y:y1 - y, x0 - x:x1 - x]
        reg = self.mask[y0:y1, x0:x1]
        take = ms > reg
        self.col[y0:y1, x0:x1][take] = cs[take]
        np.maximum(reg, ms, out=reg)
        b = self.box
        self.box = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]

    def line(self, ln, x, y, alphas, dys=None, spread=1.0, centre=None):
        """Draw a Line with its glyph origin row at y; x = left edge. alphas/dys per part; spread scales
        the letter positions about `centre` (tracking animation)."""
        cx = centre if centre is not None else x + ln.w / 2
        for k, (xk, m) in enumerate(ln.parts):
            a = alphas[k] if hasattr(alphas, "__len__") else alphas
            dy = (dys[k] if hasattr(dys, "__len__") else dys) if dys is not None else 0.0
            gx = cx + (x + xk - cx) * spread - ln.pad
            self.put(m, ln.colour(m.shape[0]), gx, y - ln.pad + dy, a)

    def wipe(self, ln, x, y, progress, alpha=1.0, ramp=120):
        """Draw a shaped line revealed left to right."""
        xk, m = ln.parts[0]
        w = m.shape[1]
        pos = progress * (w + ramp) - ramp
        ramp_mask = np.clip((pos + ramp - np.arange(w, dtype=np.float32)) / ramp, 0, 1)[None, :]
        self.put(m * ramp_mask, ln.colour(m.shape[0]), x - ln.pad, y - ln.pad, alpha)

    def apply(self, frame, glow=0.45, shadow=0.55, glow_sigma=14):
        if self.box[2] <= self.box[0]:
            return frame
        m = 70
        x0, y0 = max(0, self.box[0] - m), max(0, self.box[1] - m)
        x1, y1 = min(W, self.box[2] + m), min(H, self.box[3] + m)
        M = self.mask[y0:y1, x0:x1]
        C = self.col[y0:y1, x0:x1]
        F = frame[y0:y1, x0:x1]
        S = cv2.GaussianBlur(M, (0, 0), 6)
        S = np.roll(S, 4, axis=0)
        F *= (1 - shadow * np.clip(S * 1.2, 0, 1))[..., None]
        F[:] = F * (1 - M[..., None]) + C * M[..., None]
        G = cv2.GaussianBlur(M, (0, 0), glow_sigma)[..., None] * np.array([1.0, 0.72, 0.36], np.float32)
        F[:] = 1 - (1 - F) * (1 - np.clip(G * glow, 0, 1))
        return frame


def scrim(frame, cx, cy, rx, ry, strength, tint=(0.06, 0.03, 0.015)):
    """A soft warm-dark ellipse behind type, so ivory reads on the cream walls."""
    if strength <= 0:
        return frame
    x0, x1 = int(max(0, cx - rx * 1.6)), int(min(W, cx + rx * 1.6))
    y0, y1 = int(max(0, cy - ry * 1.6)), int(min(H, cy + ry * 1.6))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    a = (np.clip(1 - d, 0, 1) ** 1.4 * strength)[..., None]
    reg = frame[y0:y1, x0:x1]
    reg[:] = reg * (1 - a) + np.array(tint, np.float32) * a
    return frame


def ornament(cv, cx, y, half, alpha, diamond=9):
    """A hairline with a small diamond in the middle and dots at the ends, drawn into the canvas."""
    if alpha <= 0 or half < 2:
        return
    s = 4                                                     # supersample
    hw, hh = int(half + diamond + 8), diamond + 6
    im = np.zeros((hh * 2 * s, hw * 2 * s), np.uint8)
    c = (hw * s, hh * s)
    cv2.line(im, (c[0] - int(half * s), c[1]), (c[0] - diamond * s - 6 * s, c[1]), 255, int(1.6 * s), cv2.LINE_AA)
    cv2.line(im, (c[0] + diamond * s + 6 * s, c[1]), (c[0] + int(half * s), c[1]), 255, int(1.6 * s), cv2.LINE_AA)
    pts = np.array([[c[0], c[1] - diamond * s], [c[0] + diamond * s, c[1]], [c[0], c[1] + diamond * s],
                    [c[0] - diamond * s, c[1]]], np.int32)
    cv2.fillConvexPoly(im, pts, 255, cv2.LINE_AA)
    for sx in (-1, 1):
        cv2.circle(im, (c[0] + sx * int((half + 6) * s), c[1]), int(2.2 * s), 255, -1, cv2.LINE_AA)
    m = cv2.resize(im, (hw * 2, hh * 2), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    col = np.broadcast_to(np.array([1.0, 0.84, 0.5], np.float32), (m.shape[0], 1, 3))
    cv.put(m, col, cx - hw, y - hh, alpha)


def stagger(t, t0, n, step, dur):
    """Per-letter progress 0..1 for letters starting at t0 + k * step."""
    return [ease_out((t - t0 - k * step) / dur) for k in range(n)]


# ---------------------------------------------------------------- the titles
class Titles:
    def __init__(self):
        self.hook_a = Line("THIS IS NOT", MARCELLUS, 50, tracking=14, stops=IVORY_STOPS)
        self.hook_b = Line("A CONCERT.", CINZEL, 124, tracking=6)
        self.name_lt = Line("JAYASHREE D JAIN", CINZEL, 62, tracking=7)
        self.role_lt = Line("CLASSICAL VOCALIST", MARCELLUS, 30, tracking=9, stops=IVORY_STOPS)
        self.prayer = Line("it’s a prayer.", ITALIC, 132, tracking=1, stops=IVORY_STOPS)
        self.kn1 = Line("ಸಿದ್ಧ ನವಗ್ರಹ "
                        "ತೀರ್ಥಂಕರ", KANNADA_M, 62, per_char=False,
                        stops=IVORY_STOPS)
        self.kn2 = Line("ಮಹಾ ಆರಾಧನ", KANNADA, 96, per_char=False)
        self.en = Line("Siddha Navagraha Tirthankara Maha Aradhana", ITALIC, 43, tracking=0.5, stops=IVORY_STOPS)
        self.end_name = Line("JAYASHREE D JAIN", CINZEL, 80, tracking=8)
        self.end_role = Line("CLASSICAL VOCALIST", MARCELLUS, 34, tracking=11, stops=IVORY_STOPS)
        self.end_cta = Line("follow for more", ITALIC, 50, tracking=0.5, stops=IVORY_STOPS)

    def hook(self, fr, t, t0, t1):
        u_out = ease_in_out((t - (t1 - 0.22)) / 0.22)
        a_all = 1 - u_out
        scrim(fr, 540, 400, 620, 330, 0.62 * a_all * ease_out((t - t0) / 0.25))
        cv = Canvas()
        la = self.hook_a
        pa = stagger(t, t0 + 0.02, la.n, 0.022, 0.30)
        cv.line(la, 540 - la.w / 2, 300, [p * a_all for p in pa], [14 * (1 - p) - 10 * u_out for p in pa])
        lb = self.hook_b
        pb = stagger(t, t0 + 0.16, lb.n, 0.035, 0.36)
        spread = 1.0 + 0.035 * ease_in_out((t - t0) / (t1 - t0))
        cv.line(lb, 540 - lb.w / 2, 372, [p * a_all for p in pb], [26 * (1 - p) - 14 * u_out for p in pb],
                spread=spread, centre=540)
        return cv.apply(fr, glow=0.55)

    def lower_third(self, fr, t, t0, t1):
        a_all = 1 - ease_in_out((t - (t1 - 0.3)) / 0.3)
        x, y = 78, 880
        scrim(fr, 360, 957, 470, 150, 0.55 * a_all * ease_out((t - t0) / 0.3))
        cv = Canvas()
        pn = stagger(t, t0 + 0.12, self.name_lt.n, 0.028, 0.32)
        cv.line(self.name_lt, x, y, [p * a_all for p in pn], [12 * (1 - p) for p in pn])
        lw = ease_out((t - t0) / 0.5) * 230
        # a hairline that draws itself out from the left
        m = np.zeros((10, 600), np.float32)
        cv2.line(m, (4, 5), (4 + int(lw), 5), 1.0, 2, cv2.LINE_AA)
        cv.put(m, np.broadcast_to(np.array([1.0, 0.82, 0.48], np.float32), (10, 1, 3)), x + 2, y + 92, a_all)
        pr = ease_out((t - t0 - 0.45) / 0.45)
        cv.line(self.role_lt, x + 2, y + 112, pr * a_all, 8 * (1 - pr))
        return cv.apply(fr, glow=0.4)

    def prayer_line(self, fr, t, t0, t1):
        a_in = ease_in_out((t - t0) / 0.9)
        a_all = a_in * (1 - ease_in_out((t - (t1 - 0.45)) / 0.45))
        ln = self.prayer
        y = 1290
        scrim(fr, 540, y + 60, 560, 190, 0.45 * a_all)
        cv = Canvas()
        pa = stagger(t, t0, ln.n, 0.05, 0.8)
        spread = 1.0 + 0.04 * ease_in_out((t - t0) / (t1 - t0))
        cv.line(ln, 540 - ln.w / 2, y, [p * a_all for p in pa], [10 * (1 - p) for p in pa], spread=spread, centre=540)
        return cv.apply(fr, glow=0.5, glow_sigma=18)

    def event(self, fr, t, t0, t1):
        a_all = 1 - ease_in_out((t - (t1 - 0.35)) / 0.35)
        scrim(fr, 540, 430, 640, 290, 0.66 * a_all * ease_out((t - t0) / 0.3))
        cv = Canvas()
        p1 = ease_in_out((t - t0) / 0.8)
        cv.wipe(self.kn1, 540 - self.kn1.w / 2, 278, p1, a_all)
        p2 = ease_in_out((t - t0 - 0.35) / 0.8)
        cv.wipe(self.kn2, 540 - self.kn2.w / 2, 360, p2, a_all)
        pe = ease_out((t - t0 - 0.9) / 0.6)
        ornament(cv, 540, 520, 150 * pe, a_all * pe)
        cv.line(self.en, 540 - self.en.w / 2, 548, pe * a_all, 8 * (1 - pe))
        return cv.apply(fr, glow=0.5)

    def end(self, fr, t, t0, t1):
        a = ease_out((t - t0) / 0.4)
        scrim(fr, 540, 560, 640, 330, 0.66 * a)
        cv = Canvas()
        ln = self.end_name
        pn = stagger(t, t0 + 0.05, ln.n, 0.035, 0.45)
        spread = 1.0 + 0.05 * ease_out((t - t0) / (t1 - t0))
        cv.line(ln, 540 - ln.w / 2, 430, pn, [18 * (1 - p) for p in pn], spread=spread, centre=540)
        po = ease_out((t - t0 - 0.55) / 0.7)
        ornament(cv, 540, 548, 200 * po, po)
        pr = ease_out((t - t0 - 0.75) / 0.5)
        cv.line(self.end_role, 540 - self.end_role.w / 2, 572, pr, 8 * (1 - pr), spread=1 + 0.03 * po, centre=540)
        pc = ease_out((t - t0 - 1.35) / 0.6)
        pulse = 0.85 + 0.15 * math.sin(2 * math.pi * 0.9 * max(0.0, t - t0 - 1.95))
        cv.line(self.end_cta, 540 - self.end_cta.w / 2, 650, pc * pulse, 10 * (1 - pc))
        return cv.apply(fr, glow=0.55)

    def draw(self, fr, t, spans):
        for t0, t1, kind in spans:
            if t0 <= t < t1:
                fr = {"hook": self.hook, "lower": self.lower_third, "prayer": self.prayer_line,
                      "event": self.event, "end": self.end}[kind](fr, t, t0, t1)
        return fr
