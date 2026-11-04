"""The titles: ivory-to-gold serif type with a soft shadow and a warm glow (from her event reel, same family).

Fonts (renders/fonts, tools/fonts.sh): Cinzel (her name), Marcellus (small caps lines), Cormorant Garamond
italic (the English meaning), Noto Serif Kannada (the lyrics, shaped by raqm).
Safe zone: Instagram covers the top ~200 px and the bottom ~380 px, and the right edge has the buttons, so the
type lives between y 250 and y 1500, x 80 and x 1000.
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


# ---------------------------------------------------------------- this reel's titles
HONORIFIC = "JINA GAANA VISHARADE"
NAME = "JAYASHREE D JAIN"
EVENT_KN = "ಭಗವಾನ್ ಬಾಹುಬಲಿ ಸ್ವಾಮಿ ಪ್ರತಿಷ್ಠಾ ಮಹೋತ್ಸವ"
EVENT_PLACE = "KAVERI DHAM \u00b7 BASTI HOSAKOTE"
EVENT_DATE = "25 NOVEMBER 2023"
SONG_EN = "Cheluvara Cheluva Namma Gommata Deva"
SIGNOFF = "JAI JINENDRA"
ARTIST_Y = 358                     # the artist block (above the window)
LYRIC_Y = 1358                     # the lyric block (below the window)


def fit_line(text, face, size, maxw, **kw):
    """A Line, shrunk until it fits maxw."""
    while True:
        ln = Line(text, face, size, **kw)
        if ln.w <= maxw or size <= 20:
            return ln
        size -= 2


class Titles:
    def __init__(self, lyrics):
        self.hon = Line(HONORIFIC, MARCELLUS, 31, tracking=11)
        self.name = Line(NAME, CINZEL, 70, tracking=6)
        self.lyr = {}
        for ly in lyrics:
            if ly["kn"] not in self.lyr:
                self.lyr[ly["kn"]] = (fit_line(ly["kn"], KANNADA, 58, 900, per_char=False),
                                      fit_line(ly["en"], ITALIC, 44, 900, tracking=0.4, stops=IVORY_STOPS))
        self.ev_kn = fit_line(EVENT_KN, KANNADA_M, 50, 900, per_char=False)
        self.ev_place = Line(EVENT_PLACE, MARCELLUS, 31, tracking=8)
        self.ev_date = Line(EVENT_DATE, MARCELLUS, 26, tracking=9, stops=IVORY_STOPS)
        self.jai = Line("ಜೈ", KANNADA, 300, per_char=False)
        self.song_kn = fit_line(lyrics[0]["kn"], KANNADA, 56, 900, per_char=False)
        self.song_en = Line(SONG_EN, ITALIC, 40, tracking=0.4, stops=IVORY_STOPS)
        self.sign = Line(SIGNOFF, CINZEL, 44, tracking=10)

    # the artist block: from the first frame, a glow when she first appears
    def artist(self, fr, t, t0, t1, hi=None):
        cv = Canvas()
        ph = stagger(t, t0, self.hon.n, 0.02, 0.4)
        cv.line(self.hon, 540 - self.hon.w / 2, ARTIST_Y, ph, [8 * (1 - p) for p in ph])
        pn = stagger(t, t0 + 0.2, self.name.n, 0.035, 0.45)
        cv.line(self.name, 540 - self.name.w / 2, ARTIST_Y + 46, pn, [16 * (1 - p) for p in pn], spread=1.0,
                centre=540)
        po = ease_out((t - t0 - 0.7) / 0.6)
        ornament(cv, 540, ARTIST_Y + 150, 190 * po, po)
        glow = 0.45
        if hi is not None and hi <= t < hi + 1.6:
            glow += 0.55 * math.sin(math.pi * (t - hi) / 1.6)
        return cv.apply(fr, glow=glow)

    def lyric(self, fr, t, ly):
        kn, en = self.lyr[ly["kn"]]
        t0, t1 = ly["t0"], ly["t1"]
        a_out = 1 - ease_in_out((t - (t1 - 0.28)) / 0.28)
        cv = Canvas()
        cv.wipe(kn, 540 - kn.w / 2, LYRIC_Y, ease_in_out((t - t0) / 0.55), a_out, ramp=160)
        pe = ease_out((t - t0 - 0.3) / 0.5)
        cv.line(en, 540 - en.w / 2, LYRIC_Y + 92, pe * a_out, 10 * (1 - pe))
        return cv.apply(fr, glow=0.42, glow_sigma=12)

    def event(self, fr, t, t0, t1):
        a_out = 1 - ease_in_out((t - (t1 - 0.3)) / 0.3)
        cv = Canvas()
        cv.wipe(self.ev_kn, 540 - self.ev_kn.w / 2, LYRIC_Y - 4, ease_in_out((t - t0) / 0.6), a_out, ramp=160)
        pp = stagger(t, t0 + 0.35, self.ev_place.n, 0.015, 0.35)
        cv.line(self.ev_place, 540 - self.ev_place.w / 2, LYRIC_Y + 80, [p * a_out for p in pp],
                [8 * (1 - p) for p in pp])
        pd = ease_out((t - t0 - 0.7) / 0.45)
        cv.line(self.ev_date, 540 - self.ev_date.w / 2, LYRIC_Y + 132, pd * a_out, 8 * (1 - pd))
        return cv.apply(fr, glow=0.42)

    def jai_card(self, fr, t, t0, t1, cy):
        u = (t - t0) / 0.32
        a = ease_out(u) * (1 - ease_in_out((t - (t1 - 0.25)) / 0.25))
        cv = Canvas()
        _, m = self.jai.parts[0]
        sc = 1.35 - 0.35 * ease_out(u)
        m2 = cv2.resize(m, (int(m.shape[1] * sc), int(m.shape[0] * sc)), interpolation=cv2.INTER_LINEAR)
        col = np.broadcast_to(self.jai.colour(m2.shape[0]), (m2.shape[0], 1, 3))
        cv.put(m2, col, 540 - m2.shape[1] / 2, cy - m2.shape[0] / 2, a)
        return cv.apply(fr, glow=0.75, glow_sigma=22, shadow=0.85)

    def end(self, fr, t, t0, t1):
        cv = Canvas()
        p1 = ease_in_out((t - t0 - 0.1) / 0.7)
        cv.wipe(self.song_kn, 540 - self.song_kn.w / 2, LYRIC_Y, p1, 1.0, ramp=160)
        pe = ease_out((t - t0 - 0.45) / 0.5)
        cv.line(self.song_en, 540 - self.song_en.w / 2, LYRIC_Y + 88, pe, 10 * (1 - pe))
        po = ease_out((t - t0 - 0.8) / 0.6)
        ornament(cv, 540, LYRIC_Y + 168, 170 * po, po)
        ps = stagger(t, t0 + 1.0, self.sign.n, 0.03, 0.45)
        cv.line(self.sign, 540 - self.sign.w / 2, LYRIC_Y + 196, ps, [12 * (1 - p) for p in ps], spread=1.0,
                centre=540)
        return cv.apply(fr, glow=0.5)
