"""Text layers for the CR aura edit, rendered with PIL as straight-alpha RGBA float32 at frame size.

Cinzel (OFL) for the cinematic titles, Inter for the hook subtitles. Gold = a vertical
light-to-deep gradient with a soft warm glow, so the titles read as metal under light.
"""
import functools
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
GOLD = [(255, 241, 196), (246, 205, 112), (214, 152, 52), (162, 103, 26)]


@functools.lru_cache(maxsize=64)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size))


def _text_mask(text, fnt, tracking=0.0):
    """White-on-black L image of the text with letter spacing (tracking in em); returns (img, x_offsets)."""
    size = fnt.size
    widths = [fnt.getlength(ch) for ch in text]
    gap = tracking * size
    total = sum(widths) + gap * (len(text) - 1)
    asc, desc = fnt.getmetrics()
    pad = int(size * 0.6)
    im = Image.new("L", (int(total) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for ch, w in zip(text, widths):
        d.text((x, pad), ch, font=fnt, fill=255)
        x += w + gap
    return im, pad


def _gradient(h, w, stops):
    ys = np.linspace(0, 1, h)[:, None]
    n = len(stops) - 1
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        vals = np.array([s[c] for s in stops], np.float32) / 255
        out[..., c] = np.interp(ys, np.linspace(0, 1, n + 1), vals)
    return out


@functools.lru_cache(maxsize=64)
def text_rgba(text, fontname, size, style="gold", tracking=0.06, glow=0.5, stroke=0):
    """Tight RGBA (float32) of a text line. style: gold | white | goldline."""
    fnt = font(fontname, size)
    m, pad = _text_mask(text, fnt, tracking)
    if stroke:
        m = m.filter(ImageFilter.MaxFilter(stroke * 2 + 1))
    a = np.asarray(m, np.float32) / 255
    h, w = a.shape
    ys, xs = np.nonzero(a > 0.02)
    y0, y1 = ys.min(), ys.max() + 1
    if style == "gold":
        rgb = _gradient(y1 - y0, w, GOLD)
        full = np.zeros((h, w, 3), np.float32)
        full[y0:y1] = rgb
    else:
        full = np.ones((h, w, 3), np.float32) * np.array([1.0, 0.98, 0.94], np.float32)
    rgba = np.dstack([full, a])
    if glow > 0:
        g = cv2.GaussianBlur(a, (0, 0), size * 0.14) * glow
        gcol = np.array([1.0, 0.72, 0.30] if style == "gold" else [1.0, 0.95, 0.85], np.float32)
        ga = np.clip(g, 0, 1)
        out_a = a + ga * (1 - a)
        out_rgb = (full * a[..., None] + gcol * (ga * (1 - a))[..., None]) / np.maximum(out_a[..., None], 1e-4)
        rgba = np.dstack([out_rgb, out_a])
    return rgba.astype(np.float32)


def place(canvas_hw, rgba, cx, cy, scale=1.0, alpha=1.0):
    """Full-frame RGBA with the text centred at (cx, cy), scaled, faded."""
    H, W = canvas_hw
    out = np.zeros((H, W, 4), np.float32)
    if alpha <= 0.003:
        return out
    t = rgba
    if abs(scale - 1) > 1e-3:
        t = cv2.resize(t, (max(1, int(t.shape[1] * scale)), max(1, int(t.shape[0] * scale))), interpolation=cv2.INTER_CUBIC)
    h, w = t.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya:
        return out
    out[ya:yb, xa:xb] = t[ya - y0:yb - y0, xa - x0:xb - x0]
    out[..., 3] *= alpha
    return out


def subtitle_rgba(text, size=46):
    """Hook subtitle: Inter 800, warm white, dark outline + soft shadow (readable on any frame)."""
    fnt = font("Inter-800.ttf", size)
    asc, desc = fnt.getmetrics()
    w = int(fnt.getlength(text)) + 60
    h = asc + desc + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((30, 20), text, font=fnt, fill=(255, 250, 240, 255), stroke_width=max(2, size // 14), stroke_fill=(10, 10, 12, 230))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((30, 26), text, font=fnt, fill=(0, 0, 0, 150), stroke_width=max(2, size // 14), stroke_fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    sh.alpha_composite(im)
    return np.asarray(sh, np.float32) / 255


def with_shadow(rgba, blur_frac=0.08, opacity=0.55, dy_frac=0.03):
    """The text over a soft dark shadow (for light backgrounds). Returns a padded RGBA."""
    h, w = rgba.shape[:2]
    pad = int(h * 0.5)
    a = np.pad(rgba[..., 3], pad)
    sh = cv2.GaussianBlur(a, (0, 0), max(1.0, h * blur_frac))
    dy = int(h * dy_frac)
    sh = np.roll(sh, dy, axis=0) * opacity
    rgb = np.pad(rgba[..., :3], ((pad, pad), (pad, pad), (0, 0)))
    ta = a
    out_a = ta + sh * (1 - ta)
    out_rgb = rgb * (ta / np.maximum(out_a, 1e-4))[..., None]          # shadow colour is black
    return np.dstack([out_rgb, out_a]).astype(np.float32)
