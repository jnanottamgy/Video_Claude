"""V2 effects: the speed engine (time maps, shockwaves, speed lines), motion transitions between two shots, and the
motion-graphics callouts that animate onto a car when it drops into slow motion.

Everything works in output pixels (1920x1080) on float RGB 0..1 images.
"""
import functools
import math

import cv2
import numpy as np

import gfx
import look
from media import FPS, H, W

# ----------------------------------------------------------------------------------------- time maps

def speedmap(anchor, segs, t0=None, t1=None):
    """A source-time map from a speed profile: segs = [(out_t, speed), ...], speed linear between keys (so a ramp
    from 3.0x to 0.25x over two frames is a "sudden slow"), constant outside. anchor = (out_t, src_t) pins one
    moment (e.g. the frame where the car is broadside lands on a beat). Returns f(t) -> src time, with .speed(t)."""
    ks = np.array(segs, float)
    lo = (t0 if t0 is not None else ks[0, 0]) - 1.0
    hi = (t1 if t1 is not None else ks[-1, 0]) + 1.0
    grid = np.arange(lo, hi, 0.0005)
    v = np.interp(grid, ks[:, 0], ks[:, 1])
    s = np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(grid))])
    s += anchor[1] - np.interp(anchor[0], grid, s)

    def f(t):
        return float(np.interp(t, grid, s))
    f.speed = lambda t: float(np.interp(t, ks[:, 0], ks[:, 1]))
    f.segs = segs
    return f


def speed_of(spec, t, src_of):
    s = spec.get("src")
    if callable(s) and hasattr(s, "speed"):
        return s.speed(t)
    if callable(s):
        h = 0.5 / FPS
        return (s(t + h) - s(t - h)) / (2 * h)
    return s[1] if s is not None else 1.0


# ----------------------------------------------------------------------------------------- geometry helpers

@functools.lru_cache(maxsize=2)
def _grid(w=W, h=H):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


def scale_about(img, k, px, py, border=cv2.BORDER_REFLECT101):
    """Scale an output-size image by k about (px, py)."""
    m = np.float32([[k, 0, px * (1 - k)], [0, k, py * (1 - k)]])
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def shift(img, dx, dy=0.0, border=cv2.BORDER_CONSTANT):
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def radial_blur(img, px, py, amount, n=10):
    """Zoom blur about (px, py): the average of n copies scaled from 1 to 1 + amount."""
    if amount < 0.004:
        return img
    acc = np.zeros_like(img)
    for i in range(n):
        acc += scale_about(img, 1 + amount * i / (n - 1), px, py)
    return acc / n


def dir_blur(img, dx, dy, n=9):
    """Motion blur along (dx, dy) pixels (centred)."""
    L = math.hypot(dx, dy)
    if L < 1.5:
        return img
    n = int(min(24, max(n, L / 6)))
    acc = np.zeros_like(img)
    for i in range(n):
        u = i / (n - 1) - 0.5
        acc += shift(img, dx * u, dy * u, cv2.BORDER_REFLECT101)
    return acc / n


# ----------------------------------------------------------------------------------------- the speed engine

def shockwave(img, cx, cy, u, strength=38.0, width=70.0, rmax=1500.0, light=0.35, chroma=True):
    """An expanding refraction ring from (cx, cy): u in 0..1 is its progress. Pixels at the ring are pushed outward,
    the ring catches light and splits colour a little."""
    if u <= 0 or u >= 1:
        return img
    xx, yy = _grid()
    dx, dy = xx - cx, yy - cy
    d = np.sqrt(dx * dx + dy * dy) + 1e-3
    e = 1 - (1 - u) ** 2.2
    r = rmax * e
    fade = (1 - u) ** 1.3
    prof = np.exp(-((d - r) / width) ** 2)
    disp = strength * fade * (prof * ((d - r) / width)) * 1.6       # a lens: the ring compresses what it crosses
    mx, my = (xx - dx / d * disp).astype(np.float32), (yy - dy / d * disp).astype(np.float32)
    out = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    if chroma:
        k = 0.12
        f32 = lambda x: x.astype(np.float32)
        mr = cv2.remap(np.ascontiguousarray(img[..., 0]), f32(xx - dx / d * disp * (1 + k)), f32(yy - dy / d * disp * (1 + k)),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
        mb = cv2.remap(np.ascontiguousarray(img[..., 2]), f32(xx - dx / d * disp * (1 - k)), f32(yy - dy / d * disp * (1 - k)),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
        out = np.dstack([mr, out[..., 1], mb])
    if light > 0:
        glow = (prof * fade * light)[..., None]
        out = 1 - (1 - out) * (1 - glow)
    return out


def speed_lines(img, t, direction, alpha, seed=1, n=34, color=(1.0, 1.0, 1.0), axis="x", band=(0.08, 0.92)):
    """Thin streaks racing across the frame in the travel direction (direction -1: right to left)."""
    if alpha <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    ov = np.zeros((H, W), np.float32)
    for i in range(n):
        y = (band[0] + (band[1] - band[0]) * rng.random()) * (H if axis == "x" else W)
        L = (0.18 + 0.5 * rng.random()) * W
        v = (2.6 + 3.5 * rng.random()) * W                   # px per second
        ph = rng.random() * (W + L)
        th = 1 + int(rng.random() * 2.2)
        a = 0.35 + 0.65 * rng.random()
        x = (ph + v * t) % (W + L) - L
        if direction < 0:
            x = W - x - L
        if axis == "x":
            cv2.line(ov, (int(x), int(y)), (int(x + L), int(y)), a, th, cv2.LINE_AA)
        else:
            cv2.line(ov, (int(y), int(x * H / W)), (int(y), int((x + L) * H / W)), a, th, cv2.LINE_AA)
    k = (31, 1) if axis == "x" else (1, 31)
    ov = cv2.blur(ov, k)
    # fade the streaks towards the frame centre: they live at the edges, the car stays clean
    xx, yy = _grid()
    edge = np.clip((np.abs(yy - H / 2) / (H / 2)) ** 0.8 * 1.25 if axis == "x" else (np.abs(xx - W / 2) / (W / 2)) * 1.2, 0, 1)
    ov = ov * edge * alpha
    return 1 - (1 - img) * (1 - ov[..., None] * np.array(color, np.float32))


def time_slow(img, u, strength=1.0):
    """The instant time drops: a cold desaturated pulse, crushed edges and a slight colour split (u: 0..1 after)."""
    if u < 0 or u >= 1:
        return img
    e = (1 - u) ** 2 * strength
    L = look.luma(img)[..., None]
    cold = L * np.array([0.82, 0.95, 1.12], np.float32)
    out = img * (1 - 0.55 * e) + cold * 0.55 * e
    out = look.aberration(out, 0.01 * e)
    return look.vignette(out, 0.5 * e)


# ----------------------------------------------------------------------------------------- transitions
# Each takes A and B (the two shots' finished images at this frame) and u (0..1 across the transition).

def ease_io(u):
    return u * u * (3 - 2 * u)


def push(A, B, u, direction=-1, axis="x", blur=0.22, curve=2.4):
    """A slides out and B slides in, travelling the same way (direction -1: towards the left), with motion blur
    peaking at the cut, like one fast camera move carrying the car's motion into the next shot."""
    # position: accelerate into the cut, decelerate after (exponential feel)
    if u < 0.5:
        p = 0.5 * (2 * u) ** curve
        sp = curve * (2 * u) ** (curve - 1)
    else:
        p = 1 - 0.5 * (2 * (1 - u)) ** curve
        sp = curve * (2 * (1 - u)) ** (curve - 1)
    size = W if axis == "x" else H
    off = direction * p * size
    canvas_dx = off
    bl = direction * blur * size * sp * 0.5
    if axis == "x":
        a = shift(A, canvas_dx, 0)
        b = shift(B, canvas_dx - direction * W, 0)
        out = a + b                                           # they tile the frame with no overlap
        out = dir_blur(out, bl, 0)
    else:
        a = shift(A, 0, canvas_dx)
        b = shift(B, 0, canvas_dx - direction * H)
        out = dir_blur(a + b, 0, bl)
    return out


def shock_reveal(A, B, u, cx, cy, rmax=2300.0):
    """B opens inside a ring expanding from (cx, cy) (the fist): a hole punched through to the next shot."""
    e = 1 - (1 - u) ** 2.4
    r = rmax * e
    xx, yy = _grid()
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    m = np.clip((r - d) / 26.0 + 0.5, 0, 1)[..., None]
    out = A * (1 - m) + B * m
    return shockwave(out, cx, cy, min(0.999, max(0.001, e * 0.9)), strength=55, width=60, rmax=r / max(e * 0.9, 1e-3),
                     light=0.6)


def luma_wipe(A, B, u, soft=0.12, bloom=0.5):
    """The brightest parts of A (dust in the sun) turn into B first, then everything: dust becomes cloud."""
    L = cv2.GaussianBlur(cv2.resize(look.luma(A), (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 7)
    L = cv2.resize(L, (W, H), interpolation=cv2.INTER_LINEAR)
    thr = 1.05 - 1.25 * ease_io(u)
    m = np.clip((L - thr) / soft + 0.5, 0, 1)[..., None]
    out = A * (1 - m) + B * m
    g = math.sin(math.pi * u) * bloom
    if g > 0.01:
        out = look.halation(out, 0.55, g, (1.0, 0.95, 0.9), 30)
        out = out * (1 - 0.35 * g) + 0.35 * g
    return out


def light_match(A, B, u, peak=0.98):
    """A's highlights bloom to white, B comes out of the white (a sun becomes a pair of headlights)."""
    if u < 0.5:
        k = (u / 0.5) ** 2
        out = look.halation(A, 0.5, 1.6 * k, (1.0, 0.92, 0.8), 40)
        return out * (1 - peak * k) + peak * k
    k = ((1 - u) / 0.5) ** 1.6
    out = look.halation(B, 0.5, 1.4 * k, (1.0, 0.95, 0.9), 40)
    return out * (1 - peak * k) + peak * k


def edge_wipe(A, B, u, direction=-1, soft=90.0, blur=0.12):
    """A soft edge sweeps across in the travel direction (a car body passing the lens), B behind it."""
    e = ease_io(u)
    xx, _ = _grid()
    if direction < 0:
        pos = W * (1 - e) - soft
        m = np.clip((xx - pos) / soft, 0, 1)
    else:
        pos = W * e + soft
        m = np.clip((pos - xx) / soft, 0, 1)
    out = A * (1 - m[..., None]) + B * m[..., None]
    return dir_blur(out, direction * blur * W * math.sin(math.pi * u), 0)


# ----------------------------------------------------------------------------------------- motion graphics

ACC = gfx.RED
INK = (1.0, 1.0, 1.0)


def _p(t, t0, d):
    return float(np.clip((t - t0) / d, 0, 1))


def _eo(u):
    return 1 - (1 - u) ** 3


def callout(h, anchor, t, t_in, title, rows=(), side=1, rise=170, run=250, color=INK, accent=ACC, size=46, f=0,
            out_t=None):
    """A leader line that draws itself from a point on the car to a label, then the label wipes on and its data
    rows type in. side: +1 label to the right of the anchor, -1 to the left. Near the top of frame the label
    hangs below the anchor instead."""
    if t < t_in or (out_t is not None and t >= out_t):
        return
    ax, ay = anchor
    p1 = _eo(_p(t, t_in, 0.10))                    # the line
    p2 = _eo(_p(t, t_in + 0.08, 0.10))             # the label block
    p3 = _p(t, t_in + 0.14, 0.25)                  # the rows typing
    fade = 1.0 if out_t is None else float(np.clip((out_t - t) / 0.06, 0, 1))
    h.circle((ax, ay), 8, color, 0.95 * fade, -1)
    ring = _p(t, t_in, 0.35)
    if ring < 1:
        h.circle((ax, ay), 10 + 56 * _eo(ring), accent, 0.95 * (1 - ring) * fade, 3)
    up = ay - rise > 130
    vy = -1 if up else 1
    ex, ey = ax + side * rise * 0.6, ay + vy * rise            # the elbow
    lx, ly = ex + side * run, ey                               # the end of the run
    L1 = math.hypot(ex - ax, ey - ay)
    L2 = abs(lx - ex)
    d = p1 * (L1 + L2)
    if d <= L1:
        h.line((ax, ay), (ax + (ex - ax) * d / L1, ay + (ey - ay) * d / L1), color, 0.95 * fade, 3)
    else:
        h.line((ax, ay), (ex, ey), color, 0.95 * fade, 3)
        h.line((ex, ey), (ex + side * (d - L1), ey), color, 0.95 * fade, 3)
    if p2 <= 0:
        return
    tw = int(len(title) * size * 0.62 + 30)
    th = int(size * 1.32)
    x0 = lx if side > 0 else lx - tw
    y0 = ly - th - 8 if up else ly + 8
    wv = int(tw * p2)
    if side > 0:
        h.rect(x0, y0, x0 + wv, y0 + th, accent, 0.96 * fade, fill=True)
    else:
        h.rect(x0 + tw - wv, y0, x0 + tw, y0 + th, accent, 0.96 * fade, fill=True)
    if p2 > 0.6:
        old = h.shadow
        h.shadow = 0
        h.text(title, x0 + 15, y0 + th / 2, size, (1, 1, 1), fade, gfx.F_MONOB, anchor="lm")
        h.shadow = old
    ry = ly + 16 if up else y0 + th + 14
    rs = int(size * 0.66)
    for k, r in enumerate(rows):
        s = r(t, f) if callable(r) else r
        n = int(len(s) * float(np.clip(p3 * 1.6 - k * 0.25, 0, 1)))
        if n <= 0:
            continue
        cur = "_" if n < len(s) else ""
        rx = x0 if side > 0 else x0 + tw
        h.text(s[:n] + cur, rx, ry + k * (rs * 1.3), rs, color, 0.97 * fade, gfx.F_MONOB,
               anchor="la" if side > 0 else "ra")


def lock_box(h, box, t, t_in, color=INK, accent=ACC, f=0, label=None, out_t=None):
    """Corner brackets that slam in from wide onto the car and lock, with a rotating reticle."""
    if box is None or t < t_in or (out_t is not None and t >= out_t):
        return
    lock = _eo(_p(t, t_in, 0.14))
    fade = 1.0 if out_t is None else float(np.clip((out_t - t) / 0.06, 0, 1))
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(x0, 24), max(y0, 24), min(x1, W - 24), min(y1, H - 24)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    g = 1 + 0.9 * (1 - lock)
    bw, bh = (x1 - x0) / 2 * g, (y1 - y0) / 2 * g
    h.brackets(cx - bw, cy - bh, cx + bw, cy + bh, color, 0.97 * fade, 5, 0.14)
    r = max(18, min(bw, bh) * 0.11)
    rot = (f * 11) % 360
    h.arc((cx, cy), r, rot, rot + 80, accent, 0.97 * fade, 4)
    h.arc((cx, cy), r, rot + 180, rot + 260, accent, 0.97 * fade, 4)
    h.line((cx - r * 0.45, cy), (cx + r * 0.45, cy), color, 0.8 * fade, 2)
    h.line((cx, cy - r * 0.45), (cx, cy + r * 0.45), color, 0.8 * fade, 2)
    if label and lock > 0.7:
        old = h.shadow
        h.shadow = 0
        h.text(label, cx - bw, cy - bh - 10, 26, (1, 1, 1), fade, gfx.F_MONOB, anchor="lb", bg=(accent, 0.95 * fade))
        h.shadow = old


def counter(t, t0, t1, v0, v1, fmt="{:03d}", jitter=0):
    """A number that counts from v0 to v1 across [t0, t1] (ease-out), with optional last-digit jitter."""
    u = _eo(_p(t, t0, max(1e-3, t1 - t0)))
    v = v0 + (v1 - v0) * u
    if jitter:
        v += (int(t * 97) % 3 - 1) * jitter
    return fmt.format(int(round(v)))


def tach(h, t, rpm, speed_kmh, gear, label, slow=False, alpha=1.0, f=0, y=None, rate=""):
    """The rally telemetry strip along the bottom: a segmented rev bar with a red zone, the playback rate, gear and
    speed. rpm in 0..1. Sized to stay legible at phone size."""
    if alpha <= 0.01:
        return
    y = H - 70 if y is None else y
    x0, x1 = 80, W - 80
    n = 40
    seg = (x1 - x0 - 330) / n
    lit = int(round(rpm * n))
    for i in range(n):
        xa = x0 + i * seg
        on = i < lit
        red = i >= n * 0.8
        col = gfx.RED if red else (1, 1, 1)
        a = (0.95 if on else 0.2) * alpha
        if on and red and (f // 2) % 2 == 0 and rpm > 0.9:
            a = 0.4 * alpha
        hgt = 14 + int(16 * i / n)
        h.rect(xa + 2, y - hgt, xa + seg - 3, y, col, a, fill=True)
    old = h.shadow
    h.text(label, x0, y - 44, 26, (1, 1, 1), 0.95 * alpha, gfx.F_MONOB, anchor="lb")
    h.text(f"{speed_kmh:03d}", x1 - 92, y + 4, 84, (1, 1, 1), 0.98 * alpha, gfx.F_MONOB, anchor="rb")
    h.text("KM/H", x1, y - 6, 24, (1, 1, 1), 0.9 * alpha, gfx.F_MONOB, anchor="rb")
    h.text(f"GEAR {gear}", x1 - 92, y - 84, 22, gfx.RED if slow else (1, 1, 1), 0.95 * alpha, gfx.F_MONOB, anchor="rb")
    if rate:
        h.shadow = 0
        lw = int(len(label) * 26 * 0.62) + 24
        h.text(f" {rate} ", x0 + lw, y - 44, 24, (1, 1, 1), alpha, gfx.F_MONOB, anchor="lb",
               bg=(gfx.RED if slow else (0.1, 0.1, 0.1), 0.95 * alpha))
    h.shadow = old


def chevrons(ov_h, t, t0, direction=-1, n=3, y=None, alpha=1.0, size=150, color=(1, 1, 1)):
    """A burst of chevrons streaking across with the motion (graphic motion that rides a push)."""
    u = _p(t, t0, 0.28)
    if u <= 0 or u >= 1:
        return
    y = H / 2 if y is None else y
    e = _eo(u)
    a = alpha * (1 - u) ** 0.7
    for i in range(n):
        k = i / max(1, n - 1)
        x = W * (1.1 - 1.4 * e) - k * size * 0.75 if direction < 0 else W * (-0.1 + 1.4 * e) + k * size * 0.75
        s = size * (0.6 + 0.4 * k)
        d = 1 if direction < 0 else -1
        p = [(x + d * s * 0.5, y - s), (x - d * s * 0.5, y), (x + d * s * 0.5, y + s)]
        for q0, q1 in ((p[0], p[1]), (p[1], p[2])):
            ov_h.line(q0, q1, color, a * (0.45 + 0.55 * (1 - k)), 14)


def warp_lines(img, t, alpha, cx=W / 2, cy=H / 2, n=60, seed=5, color=(1.0, 1.0, 1.0)):
    """Streaks radiating from (cx, cy) and racing outward: the world rushing past a head-on car."""
    if alpha <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    ov = np.zeros((H, W), np.float32)
    R = math.hypot(W, H) * 0.6
    for i in range(n):
        ang = rng.random() * 2 * math.pi
        sp = 0.9 + 1.6 * rng.random()
        ph = rng.random()
        u = (ph + t * sp) % 1.0
        r0 = R * (0.18 + 0.9 * u ** 1.7)
        r1 = r0 + R * (0.06 + 0.25 * u)
        c, s_ = math.cos(ang), math.sin(ang)
        a = (0.4 + 0.6 * rng.random()) * min(1.0, u * 4)
        cv2.line(ov, (int(cx + c * r0), int(cy + s_ * r0)), (int(cx + c * r1), int(cy + s_ * r1)), a,
                 1 + int(rng.random() * 2.5), cv2.LINE_AA)
    ov = cv2.GaussianBlur(ov, (0, 0), 1.2) * alpha
    return 1 - (1 - img) * (1 - ov[..., None] * np.array(color, np.float32))


def flares(img, pts, strength, color=(0.65, 0.82, 1.0), streak=260.0):
    """Anamorphic streaks and glows on light sources (headlights) at pts [(x, y), ...]."""
    if strength <= 0.01 or not pts:
        return img
    xx, yy = _grid(W // 4, H // 4)
    acc = np.zeros((H // 4, W // 4), np.float32)
    for (x, y) in pts:
        dx, dy = xx - x / 4, yy - y / 4
        acc += np.exp(-(dy / 1.4) ** 2) * np.exp(-np.abs(dx) / (streak / 4))
        acc += np.exp(-(dx ** 2 + dy ** 2) / (2 * 7.0 ** 2)) * 0.9
    fl = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
    add = np.clip(fl[..., None] * np.array(color, np.float32) * strength, 0, 1)
    return 1 - (1 - img) * (1 - add)
