"""Graphics: type, the scanner HUD, the DNA helix, ATGC code rain, glints, light leaks.

Overlays are premultiplied RGBA float32 (H, W, 4): composite with over(img, ov).
"""
import functools
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "renders/fonts")
F_BIG = os.path.join(FONTS, "anton-latin-400-normal.ttf")
F_MONO = os.path.join(FONTS, "jetbrains-mono-latin-400-normal.ttf")
F_MONOB = os.path.join(FONTS, "jetbrains-mono-latin-700-normal.ttf")
F_SERIF = os.path.join(FONTS, "instrument-serif-latin-400-italic.ttf")
F_SANS = os.path.join(FONTS, "inter-latin-800-normal.ttf")
WHITE = (1.0, 1.0, 1.0)
RED = (0.93, 0.07, 0.09)
HUDC = (0.92, 0.96, 1.0)


@functools.lru_cache(None)
def font(path, size):
    return ImageFont.truetype(path, size)


@functools.lru_cache(maxsize=256)
def text(s, path=F_BIG, size=200, color=WHITE, tracking=0.0, stroke=0, stroke_only=False):
    """A text sprite: premultiplied RGBA float32, tightly cropped (plus a small pad). tracking in em."""
    f = font(path, size)
    pad = int(size * 0.25) + stroke * 2
    # measure with letter spacing
    widths = [f.getlength(ch) for ch in s]
    sp = tracking * size
    tw = int(sum(widths) + sp * max(0, len(s) - 1)) + 2 * pad
    asc, desc = f.getmetrics()
    th = asc + desc + 2 * pad
    im = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for ch, w in zip(s, widths):
        if stroke_only:
            d.text((x, pad), ch, font=f, fill=0, stroke_width=stroke, stroke_fill=255)
            d.text((x, pad), ch, font=f, fill=0)
        else:
            d.text((x, pad), ch, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        x += w + sp
    a = np.asarray(im).astype(np.float32) / 255
    if stroke_only:   # keep only the outline ring
        inner = Image.new("L", (tw, th), 0)
        di = ImageDraw.Draw(inner)
        x = pad
        for ch, w in zip(s, widths):
            di.text((x, pad), ch, font=f, fill=255)
            x += w + sp
        a = np.clip(a - np.asarray(inner).astype(np.float32) / 255, 0, 1)
    ys, xs = np.nonzero(a > 0.01)
    if len(ys):
        y0, y1 = max(0, ys.min() - 4), min(th, ys.max() + 5)
        x0, x1 = max(0, xs.min() - 4), min(tw, xs.max() + 5)
        a = a[y0:y1, x0:x1]
    out = np.zeros(a.shape + (4,), np.float32)
    out[..., :3] = a[..., None] * np.array(color, np.float32)
    out[..., 3] = a
    out.setflags(write=False)
    return out


def blank():
    return np.zeros((H, W, 4), np.float32)


def place(ov, spr, cx, cy, scale=1.0, alpha=1.0, blur=0.0, angle=0.0):
    """Composite a sprite onto an overlay, centred at (cx, cy), scaled/rotated, with optional blur."""
    if alpha <= 1e-3 or scale <= 1e-3:
        return ov
    sh, sw = spr.shape[:2]
    m = cv2.getRotationMatrix2D((sw / 2, sh / 2), angle, scale)
    m[0, 2] += cx - sw / 2
    m[1, 2] += cy - sh / 2
    # warp only into the bounding region
    bw, bh = sw * scale * 1.5 + 4, sh * scale * 1.5 + 4
    x0, y0 = int(max(0, cx - bw / 2)), int(max(0, cy - bh / 2))
    x1, y1 = int(min(W, cx + bw / 2)), int(min(H, cy + bh / 2))
    if x1 <= x0 or y1 <= y0:
        return ov
    m[0, 2] -= x0
    m[1, 2] -= y0
    warped = cv2.warpAffine(spr, m, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if blur > 0.3:
        warped = cv2.GaussianBlur(warped, (0, 0), blur)
    warped *= alpha
    reg = ov[y0:y1, x0:x1]
    reg[...] = warped + reg * (1 - warped[..., 3:4])
    return ov


def over(img, ov):
    """Premultiplied overlay onto an RGB image."""
    return img * (1 - ov[..., 3:4]) + ov[..., :3]


def slam(t, t0, dur=0.12, from_scale=1.35):
    """Scale and alpha for a word slamming in at t0 (fast ease-out)."""
    d = t - t0
    if d < 0:
        return None
    u = min(1.0, d / dur)
    e = 1 - (1 - u) ** 3
    return from_scale + (1 - from_scale) * e, min(1.0, d / 0.04 + 0.2)


# ---------------------------------------------------------------- HUD (drawn on a uint8 premultiplied canvas)

class Hud:
    """Lines and boxes with cv2 (anti-aliased) and mono text with PIL, on a premultiplied RGBA canvas."""

    def __init__(self):
        self.c = np.zeros((H, W, 4), np.uint8)

    def _col(self, color, a):
        return (int(color[0] * 255 * a), int(color[1] * 255 * a), int(color[2] * 255 * a), int(255 * a))

    shadow = 0.45

    def line(self, p, q, color=HUDC, a=0.9, th=2):
        if self.shadow:
            cv2.line(self.c, (int(p[0]) + 2, int(p[1]) + 2), (int(q[0]) + 2, int(q[1]) + 2), self._col((0, 0, 0), a * self.shadow),
                     th + 1, cv2.LINE_AA)
        cv2.line(self.c, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), self._col(color, a), th, cv2.LINE_AA)

    def rect(self, x0, y0, x1, y1, color=HUDC, a=0.9, th=2, fill=False):
        cv2.rectangle(self.c, (int(x0), int(y0)), (int(x1), int(y1)), self._col(color, a), -1 if fill else th, cv2.LINE_AA)

    def circle(self, c, r, color=HUDC, a=0.9, th=2):
        cv2.circle(self.c, (int(c[0]), int(c[1])), int(r), self._col(color, a), th, cv2.LINE_AA)

    def arc(self, c, r, a0, a1, color=HUDC, a=0.9, th=2):
        cv2.ellipse(self.c, (int(c[0]), int(c[1])), (int(r), int(r)), 0, a0, a1, self._col(color, a), th, cv2.LINE_AA)

    def brackets(self, x0, y0, x1, y1, color=HUDC, a=0.95, th=3, frac=0.22):
        L = min(x1 - x0, y1 - y0) * frac
        for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            self.line((x, y), (x + sx * L, y), color, a, th)
            self.line((x, y), (x, y + sy * L), color, a, th)

    def text(self, s, x, y, size=20, color=HUDC, a=0.95, path=F_MONO, anchor="la", bg=None):
        f = font(path, size)
        x0, y0, x1, y1 = f.getbbox(s, anchor=anchor)
        pad = 4
        w, h = int(x1 - x0) + 2 * pad, int(y1 - y0) + 2 * pad
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).text((pad - x0, pad - y0), s, font=f, fill=255, anchor=anchor)
        m = np.asarray(im).astype(np.float32) / 255 * a
        X, Y = int(x + x0 - pad), int(y + y0 - pad)
        if bg is not None:
            self.rect(X - 2, Y, X + w + 2, Y + h, bg[0], bg[1], fill=True)
        xa, ya, xb, yb = max(0, X), max(0, Y), min(W, X + w), min(H, Y + h)
        if xb <= xa or yb <= ya:
            return
        mm = m[ya - Y:yb - Y, xa - X:xb - X][..., None]
        reg = self.c[ya:yb, xa:xb].astype(np.float32)
        if self.shadow and bg is None:
            sh = cv2.GaussianBlur(mm[..., 0], (0, 0), 1.5)[..., None] * self.shadow
            sh = np.roll(np.roll(sh, 2, 0), 2, 1)
            reg = reg * (1 - sh) + sh * np.array([0, 0, 0, 255], np.float32)
        col = np.array([color[0], color[1], color[2], 1.0], np.float32) * 255
        self.c[ya:yb, xa:xb] = np.clip(mm * col + reg * (1 - mm), 0, 255).astype(np.uint8)

    def overlay(self):
        return self.c.astype(np.float32) / 255


def target_box(h, box, t, label="SUBJECT 01", data=(), color=HUDC, accent=RED, lock=1.0, f=0):
    """A tracked-target box: corner brackets that snap in (lock 0->1), a label tag, data lines, a centre reticle."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    grow = 1 + 0.6 * (1 - lock) ** 2
    bw, bh = (x1 - x0) * grow / 2, (y1 - y0) * grow / 2
    a = min(1.0, 0.25 + lock)
    h.brackets(cx - bw, cy - bh, cx + bw, cy + bh, color, a, 3)
    # reticle at the centre: a small rotating ring with ticks
    r = max(10, min(bw, bh) * 0.16)
    rot = (f * 9) % 360
    h.arc((cx, cy), r, rot, rot + 70, accent, 0.9 * a, 2)
    h.arc((cx, cy), r, rot + 180, rot + 250, accent, 0.9 * a, 2)
    h.line((cx - r * 0.4, cy), (cx + r * 0.4, cy), color, 0.7 * a, 1)
    h.line((cx, cy - r * 0.4), (cx, cy + r * 0.4), color, 0.7 * a, 1)
    if lock > 0.6:
        tx, ty = cx - bw, cy - bh - 34
        h.text(label, tx, ty, 20, (1, 1, 1), 0.98, F_MONOB, bg=(accent, 0.92))
        for k, s in enumerate(data):
            h.text(s, cx + bw + 12, cy - bh + 4 + k * 24, 17, color, 0.9)


def viewfinder(h, f, tc_offset=0.0, rec=True, label="SEQ // DNA", color=HUDC):
    """Camera viewfinder furniture: corner marks, REC dot, timecode, a label."""
    m, L = 46, 60
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        h.line((x, y), (x + sx * L, y), color, 0.75, 2)
        h.line((x, y), (x, y + sy * L), color, 0.75, 2)
    t = f / 30 + tc_offset
    tc = f"{int(t // 3600):02d}:{int(t // 60) % 60:02d}:{int(t) % 60:02d}:{int(f % 30):02d}"
    if rec and (f // 15) % 2 == 0:
        cv2.circle(h.c, (m + 30, m + 38), 9, (237, 18, 23, 255), -1, cv2.LINE_AA)
    h.text("REC", m + 46, m + 26, 22, color, 0.9, F_MONOB)
    h.text(tc, W - m - 12, m + 26, 22, color, 0.9, F_MONO, anchor="ra")
    h.text(label, m + 16, H - m - 44, 18, color, 0.8, F_MONO)


def progress(h, x, y, w, frac, label, color=HUDC, accent=RED, size=18):
    n = 24
    k = int(round(frac * n))
    h.text(label, x, y - 28, size, color, 0.9)
    for i in range(n):
        x0 = x + i * (w / n)
        h.rect(x0, y, x0 + w / n - 3, y + 10, accent if i < k else color, 0.95 if i < k else 0.25, fill=True)
    h.text(f"{int(frac * 100):3d}%", x + w + 12, y - 6, size, color, 0.95, F_MONOB)


def points(h, pts, color=HUDC, accent=RED, link=True):
    """Tracked feature points: small squares, linked to near neighbours (a constellation)."""
    pts = np.asarray(pts, np.float32)
    if len(pts) == 0:
        return
    if link and len(pts) > 2:
        d = np.linalg.norm(pts[:, None] - pts[None], axis=-1)
        for i in range(len(pts)):
            for j in np.argsort(d[i])[1:3]:
                if d[i, j] < 260:
                    h.line(pts[i], pts[j], color, 0.35, 1)
    for k, (x, y) in enumerate(pts):
        s = 4
        h.rect(x - s, y - s, x + s, y + s, accent if k % 5 == 0 else color, 0.9, 1)


# ---------------------------------------------------------------- DNA helix

def helix(ov, cx, cy, height, radius, rot, progress=1.0, turns=2.2, alpha=1.0, color=WHITE, accent=RED,
          tilt=0.18, rungs=26, th=3):
    """A rotating double helix, drawn bottom-up to `progress`, depth-shaded, on a premultiplied overlay."""
    if alpha <= 0.01 or progress <= 0.0:
        return ov
    ss = 2
    x0 = int(cx - radius * 1.6); x1 = int(cx + radius * 1.6)
    y0 = int(cy - height / 2 - radius); y1 = int(cy + height / 2 + radius)
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
    cw, ch = (x1 - x0) * ss, (y1 - y0) * ss
    if cw <= 0 or ch <= 0:
        return ov
    can = np.zeros((ch, cw, 4), np.uint8)
    n = 220
    ys = np.linspace(0.5, -0.5, n) * height
    k = int(n * progress)
    ang = rot + 2 * math.pi * turns * (ys / height)
    segs = []
    for s, ph in ((0, 0.0), (1, math.pi)):
        a = ang + ph
        X = cx + radius * np.cos(a)
        Z = np.sin(a)
        Y = cy + ys + tilt * radius * Z
        for i in range(k - 1):
            z = (Z[i] + Z[i + 1]) / 2
            segs.append((z, (X[i], Y[i]), (X[i + 1], Y[i + 1]), "s", s))
    for r in range(rungs):
        i = int((r + 0.5) / rungs * n)
        if i >= k:
            break
        a = ang[i]
        p = (cx + radius * math.cos(a), cy + ys[i] + tilt * radius * math.sin(a))
        q = (cx + radius * math.cos(a + math.pi), cy + ys[i] + tilt * radius * math.sin(a + math.pi))
        segs.append((0.0, p, q, "r", r))
    segs.sort(key=lambda s: s[0])                       # back to front
    for z, p, q, kind, idx in segs:
        depth = 0.35 + 0.65 * (z + 1) / 2
        col = accent if (kind == "r" and idx % 3 == 0) else color
        a = alpha * (0.55 if kind == "r" else depth)
        t = th if kind == "s" else max(1, th - 1)
        P = (int((p[0] - x0) * ss), int((p[1] - y0) * ss))
        Q = (int((q[0] - x0) * ss), int((q[1] - y0) * ss))
        cv2.line(can, P, Q, (int(col[0] * 255 * a), int(col[1] * 255 * a), int(col[2] * 255 * a), int(255 * a)),
                 int(t * ss), cv2.LINE_AA)
        if kind == "r":
            for E in (P, Q):
                cv2.circle(can, E, int(3 * ss), (int(col[0] * 255 * a), int(col[1] * 255 * a), int(col[2] * 255 * a),
                                                 int(255 * a)), -1, cv2.LINE_AA)
    small = cv2.resize(can, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    reg = ov[y0:y1, x0:x1]
    reg[...] = small + reg * (1 - small[..., 3:4])
    return ov


# ---------------------------------------------------------------- ATGC code rain

@functools.lru_cache(None)
def _glyphs(size=26):
    f = font(F_MONOB, size)
    out = {}
    for ch in "ATGC01":
        im = Image.new("L", (int(size * 0.75), int(size * 1.15)), 0)
        ImageDraw.Draw(im).text((2, 0), ch, font=f, fill=255)
        out[ch] = np.asarray(im).astype(np.float32) / 255
    return out


def code_rain(ov, t, alpha=1.0, color=(0.25, 1.0, 0.45), seed=3, size=26, density=1.0, letters="ATGC"):
    """Columns of falling A/T/G/C, bright heads and fading trails (the "Matrix" moment)."""
    g = _glyphs(size)
    gh, gw = next(iter(g.values())).shape
    cols = W // gw
    rng = np.random.default_rng(seed)
    speed = rng.uniform(380, 900, cols)
    phase = rng.uniform(0, H * 2, cols)
    trail = rng.integers(8, 22, cols)
    active = rng.random(cols) < 0.85 * density
    chars = rng.integers(0, len(letters), (cols, 80))
    flick = int(t * 18)
    for c in range(cols):
        if not active[c]:
            continue
        head = (phase[c] + speed[c] * t) % (H + trail[c] * gh) - trail[c] * gh * 0.2
        hr = int(head // gh)
        for k in range(trail[c]):
            r = hr - k
            y = r * gh
            if y < -gh or y >= H:
                continue
            ch = letters[(chars[c, (r + (flick if k < 2 else 0)) % 80]) % len(letters)]
            a = alpha * (1.0 if k == 0 else 0.85 * (1 - k / trail[c]) ** 1.3)
            col = (0.85, 1.0, 0.9) if k == 0 else color
            m = g[ch]
            x = c * gw
            ya, yb = max(0, y), min(H, y + gh)
            if yb <= ya:
                continue
            mm = m[ya - y:yb - y, :min(gw, W - x)] * a
            reg = ov[ya:yb, x:x + mm.shape[1]]
            reg[..., :3] = mm[..., None] * np.array(col, np.float32) + reg[..., :3] * (1 - mm[..., None])
            reg[..., 3] = mm + reg[..., 3] * (1 - mm)
    return ov


# ---------------------------------------------------------------- glints and light

@functools.lru_cache(None)
def star(size=180):
    """A 4-point star flare sprite (additive): long thin rays and a soft core."""
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    core = np.exp(-(r / (size * 0.06)) ** 2)
    rays = (np.exp(-(np.abs(yy) / 1.6) ** 2) * np.exp(-np.abs(xx) / (size * 0.42)) +
            np.exp(-(np.abs(xx) / 1.6) ** 2) * np.exp(-np.abs(yy) / (size * 0.42)))
    diag = (np.exp(-((xx - yy) / 2.2) ** 2) + np.exp(-((xx + yy) / 2.2) ** 2)) * np.exp(-r / (size * 0.15)) * 0.35
    s = np.clip(core * 1.2 + rays * 0.9 + diag, 0, 1.5)
    return s


def add_star(img, x, y, scale, strength, color=(1.0, 0.97, 0.9), angle=0.0):
    s = star()
    sz = s.shape[0]
    k = max(0.05, scale)
    m = cv2.getRotationMatrix2D((sz / 2, sz / 2), angle, k)
    m[0, 2] += x - sz / 2
    m[1, 2] += y - sz / 2
    half = int(sz * k / 2) + 2
    x0, y0, x1, y1 = max(0, int(x) - half), max(0, int(y) - half), min(W, int(x) + half), min(H, int(y) + half)
    if x1 <= x0 or y1 <= y0:
        return img
    m[0, 2] -= x0
    m[1, 2] -= y0
    w = cv2.warpAffine(s, m, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    img[y0:y1, x0:x1] = 1 - (1 - img[y0:y1, x0:x1]) * (1 - np.clip(w[..., None] * strength * np.array(color, np.float32), 0, 1))
    return img


def light_leak(img, t, strength=0.5, seed=1, colors=((1.0, 0.45, 0.12), (1.0, 0.15, 0.08), (1.0, 0.8, 0.45))):
    """Drifting warm light leaks (screen-blended soft blobs), computed at low resolution."""
    rng = np.random.default_rng(seed)
    sw, sh = W // 8, H // 8
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    acc = np.zeros((sh, sw, 3), np.float32)
    for k, col in enumerate(colors):
        px, py = rng.uniform(-0.2, 1.2), rng.uniform(-0.2, 1.2)
        vx, vy = rng.uniform(-0.35, 0.35), rng.uniform(-0.2, 0.2)
        rad = rng.uniform(0.25, 0.55)
        cx, cy = (px + vx * t) * sw, (py + vy * t) * sh
        g = np.exp(-(((xx - cx) / (rad * sw)) ** 2 + ((yy - cy) / (rad * sh * 1.4)) ** 2))
        acc += g[..., None] * np.array(col, np.float32)
    big = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
    return 1 - (1 - img) * (1 - np.clip(big * strength, 0, 1))
