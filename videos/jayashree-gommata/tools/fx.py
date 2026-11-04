"""The light and motion effects, all deterministic in time (float RGB frames in [0, 1], 1080x1920).

god rays, golden dust and bokeh, light leaks, whip-pan blur, zoom blur, chromatic aberration.
"""
import math

import cv2
import numpy as np

W, H = 1080, 1920
GOLD = np.array([1.0, 0.78, 0.42], np.float32)


def screen(x, layer):
    return 1 - (1 - x) * (1 - np.clip(layer, 0, 1))


# ---------------------------------------------------------------- god rays
def god_rays(x, px, py, strength, thresh=0.80, length=0.55, tint=(1.0, 0.84, 0.55)):
    """Light shafts streaming from (px, py) (normalised; may sit outside the frame) through the bright parts."""
    if strength <= 0:
        return x
    sw, sh = W // 4, H // 4
    small = cv2.resize(x, (sw, sh), interpolation=cv2.INTER_AREA)
    L = small.max(2, keepdims=True)
    src = small * np.clip((L - thresh) / (1 - thresh), 0, 1) ** 1.2
    cx, cy = px * sw, py * sh
    acc = np.zeros_like(src)
    n = 28
    wsum = 0.0
    for j in range(n):
        s = 1 + length * j / n                        # sample further and further out along the ray
        m = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
        wj = (1 - j / n) ** 1.3
        acc += cv2.warpAffine(src, m, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * wj
        wsum += wj
    rays = cv2.GaussianBlur(acc / wsum, (0, 0), 1.5) * np.array(tint, np.float32)
    rays = cv2.resize(rays, (W, H), interpolation=cv2.INTER_LINEAR)
    return screen(x, rays * strength * 2.4)


# ---------------------------------------------------------------- golden dust, bokeh
class Dust:
    """Rising golden motes (small, sharp-ish, twinkling) and a few large soft bokeh orbs."""

    def __init__(self, seed=7, n=150, n_bokeh=12):
        r = np.random.default_rng(seed)
        self.x0 = r.uniform(0, W, n)
        self.y0 = r.uniform(0, H, n)
        self.vy = r.uniform(18, 70, n)               # px/s upwards
        self.vx = r.uniform(-12, 12, n)
        self.sway = r.uniform(4, 22, n)
        self.fs = r.uniform(0.15, 0.6, n)
        self.ph = r.uniform(0, 2 * np.pi, n)
        self.size = r.choice([1.2, 1.6, 2.2, 3.0, 4.2], n, p=[0.3, 0.3, 0.2, 0.13, 0.07])
        self.bri = r.uniform(0.35, 1.0, n)
        self.tw = r.uniform(0.8, 3.0, n)
        self.bx0 = r.uniform(0, W, n_bokeh)
        self.by0 = r.uniform(0, H, n_bokeh)
        self.bvy = r.uniform(8, 22, n_bokeh)
        self.bvx = r.uniform(-6, 6, n_bokeh)
        self.br = r.uniform(28, 85, n_bokeh)
        self.bb = r.uniform(0.25, 0.6, n_bokeh)
        self.bph = r.uniform(0, 2 * np.pi, n_bokeh)
        self.sprites = {}

    def sprite(self, sigma):
        k = round(sigma * 10) / 10
        if k not in self.sprites:
            rad = int(math.ceil(k * 3.2))
            yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1].astype(np.float32)
            g = np.exp(-(xx ** 2 + yy ** 2) / (2 * k * k))
            core = np.exp(-(xx ** 2 + yy ** 2) / (2 * (k * 0.45) ** 2))
            self.sprites[k] = (0.65 * g + 0.6 * core)
        return self.sprites[k]

    def bokeh(self, r):
        k = int(r)
        if ("b", k) not in self.sprites:
            rad = k + 6
            yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1].astype(np.float32)
            d = np.sqrt(xx ** 2 + yy ** 2)
            disc = np.clip((k - d) / 5 + 0.5, 0, 1)                  # soft-edged disc
            ring = np.exp(-((d - k * 0.92) ** 2) / (2 * (k * 0.06) ** 2)) * 0.5
            self.sprites[("b", k)] = disc * 0.55 + ring * disc.max()
        return self.sprites[("b", k)]

    def layer(self, t, amount, bokeh_amount=None):
        """Additive light layer (H, W, 3) for time t."""
        acc = np.zeros((H, W), np.float32)
        if amount > 0:
            y = (self.y0 - self.vy * t) % (H + 40) - 20
            x = (self.x0 + self.vx * t + self.sway * np.sin(2 * np.pi * self.fs * t + self.ph)) % (W + 40) - 20
            tw = 0.55 + 0.45 * np.sin(2 * np.pi * self.tw * t + self.ph * 3)
            for i in range(len(x)):
                sp = self.sprite(self.size[i])
                _blit(acc, sp * (self.bri[i] * tw[i] * amount), x[i], y[i])
        ba = amount if bokeh_amount is None else bokeh_amount
        if ba > 0:
            by = (self.by0 - self.bvy * t) % (H + 200) - 100
            bx = (self.bx0 + self.bvx * t) % (W + 200) - 100
            for i in range(len(bx)):
                pulse = 0.7 + 0.3 * np.sin(0.7 * t + self.bph[i])
                _blit(acc, self.bokeh(self.br[i]) * (self.bb[i] * pulse * ba * 0.35), bx[i], by[i])
        return acc[..., None] * GOLD


def _blit(acc, sp, x, y):
    r = sp.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    x0, y0, x1, y1 = xi - r, yi - r, xi + r + 1, yi + r + 1
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1c <= x0c or y1c <= y0c:
        return
    acc[y0c:y1c, x0c:x1c] += sp[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)]


# ---------------------------------------------------------------- light leaks
_lw, _lh = W // 8, H // 8
_ly, _lx = np.mgrid[0:_lh, 0:_lw].astype(np.float32)
LEAK_COLOURS = [np.array(c, np.float32) for c in ((1.0, 0.42, 0.08), (1.0, 0.72, 0.28), (0.95, 0.22, 0.10),
                                                  (1.0, 0.86, 0.55))]


def leak(t, seed, intensity, drift=1.0):
    """A warm light leak: three big soft blobs sliding across, re-seeded per event. Returns (H, W, 3)."""
    if intensity <= 0:
        return None
    r = np.random.default_rng(seed)
    acc = np.zeros((_lh, _lw, 3), np.float32)
    side = r.integers(0, 2)
    for k in range(3):
        cx = r.uniform(-0.1, 0.5) if side == 0 else r.uniform(0.5, 1.1)
        cy = r.uniform(0.0, 1.0)
        vx = r.uniform(0.15, 0.45) * (1 if side == 0 else -1) * drift
        vy = r.uniform(-0.15, 0.15) * drift
        sx, sy = r.uniform(0.25, 0.55), r.uniform(0.25, 0.6)
        col = LEAK_COLOURS[r.integers(0, len(LEAK_COLOURS))]
        px, py = (cx + vx * t) * _lw, (cy + vy * t) * _lh
        g = np.exp(-(((_lx - px) / (sx * _lw)) ** 2 + ((_ly - py) / (sy * _lh)) ** 2))
        acc += g[..., None] * col * r.uniform(0.6, 1.0)
    acc = cv2.resize(acc, (W, H), interpolation=cv2.INTER_CUBIC)
    return np.clip(acc * intensity, 0, 1)


# ---------------------------------------------------------------- motion
def whip_blur(x, px):
    """Horizontal motion blur of length |px| (box), for whip pans."""
    k = int(abs(px))
    if k < 2:
        return x
    return cv2.blur(x, (k, 1), borderType=cv2.BORDER_REFLECT)


def zoom_blur(x, amount, cx=0.5, cy=0.5, n=10):
    """Radial blur about (cx, cy): the average of the frame scaled up to 1 + amount."""
    if amount <= 0.003:
        return x
    acc = np.zeros_like(x)
    for j in range(n):
        s = 1 + amount * j / (n - 1)
        m = np.float32([[s, 0, cx * W * (1 - s)], [0, s, cy * H * (1 - s)]])
        acc += cv2.warpAffine(x, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def chroma(x, px):
    """Chromatic aberration: red pushed out, blue pulled in, by px at the frame edge."""
    if px < 0.3:
        return x
    out = x.copy()
    for ch, sgn in ((0, 1), (2, -1)):
        s = 1 + sgn * px / (W / 2)
        m = np.float32([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]])
        out[..., ch] = cv2.warpAffine(x[..., ch], m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


# ---------------------------------------------------------------- for this reel: rays in any image, petals, mandala
def rays_in(x, px, py, strength, thresh=0.82, length=0.5, tint=(1.0, 0.86, 0.58)):
    """god_rays for an image of any size (the window): shafts from (px, py), normalised."""
    if strength <= 0:
        return x
    h, w = x.shape[:2]
    sw, sh = max(8, w // 4), max(8, h // 4)
    small = cv2.resize(x, (sw, sh), interpolation=cv2.INTER_AREA)
    L = small.max(2, keepdims=True)
    src = small * np.clip((L - thresh) / (1 - thresh), 0, 1) ** 1.2
    cx, cy = px * sw, py * sh
    acc = np.zeros_like(src)
    n, wsum = 24, 0.0
    for j in range(n):
        s = 1 + length * j / n
        m = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
        wj = (1 - j / n) ** 1.3
        acc += cv2.warpAffine(src, m, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * wj
        wsum += wj
    r = cv2.resize(cv2.GaussianBlur(acc / wsum, (0, 0), 1.5) * np.array(tint, np.float32), (w, h),
                   interpolation=cv2.INTER_LINEAR)
    return screen(x, r * strength * 2.2)


PETAL_COLOURS = [((0.98, 0.55, 0.12), 0.34), ((1.0, 0.76, 0.22), 0.26), ((0.80, 0.07, 0.16), 0.18),
                 ((0.93, 0.36, 0.50), 0.12), ((0.98, 0.95, 0.88), 0.10)]   # marigold, yellow, rose, pink, jasmine


class Petals:
    """Flower petals drifting down (pushpa vrishti): a steady fall and bursts. Deterministic in time."""

    def __init__(self, seed=21, n=420, burst_t=None, burst_n=160):
        r = np.random.default_rng(seed)
        self.n = n
        self.x0 = r.uniform(-40, W + 40, n)
        self.t0 = r.uniform(-12, 40, n)                       # when each petal enters at the top
        self.vy = r.uniform(70, 150, n)
        self.sway = r.uniform(10, 46, n)
        self.fs = r.uniform(0.25, 0.7, n)
        self.ph = r.uniform(0, 2 * np.pi, n)
        self.rot0 = r.uniform(0, 360, n)
        self.vr = r.uniform(-90, 90, n)
        self.flip = r.uniform(0.6, 1.8, n)
        self.size = r.choice([10, 13, 16, 20, 26], n, p=[0.22, 0.3, 0.26, 0.14, 0.08]).astype(float)
        cols, probs = zip(*PETAL_COLOURS)
        self.col = np.array(cols, np.float32)[r.choice(len(cols), n, p=np.array(probs) / sum(probs))]
        self.rank = r.uniform(0, 1, n)                        # density threshold: a petal shows if rank < density
        # the burst: petals flung up and out from the window's centre, then falling
        self.burst_t = burst_t
        bn = burst_n
        self.bx = r.normal(540, 120, bn)
        self.by = r.normal(860, 90, bn)
        ang = r.uniform(-np.pi, 0, bn)
        sp = r.uniform(420, 1100, bn)
        self.bvx, self.bvy = np.cos(ang) * sp, np.sin(ang) * sp
        self.brot0 = r.uniform(0, 360, bn)
        self.bvr = r.uniform(-260, 260, bn)
        self.bsize = r.choice([12, 16, 20, 26], bn, p=[0.25, 0.35, 0.25, 0.15]).astype(float)
        self.bcol = np.array(cols, np.float32)[r.choice(len(cols), bn, p=np.array(probs) / sum(probs))]
        self.cache = {}

    def sprite(self, size, ang, squash):
        key = (int(size), int(ang) // 6 * 6, round(squash, 1))
        if key not in self.cache:
            s = 3
            rad = int(size * 1.2) + 2
            im = np.zeros((rad * 2 * s, rad * 2 * s), np.uint8)
            c = (rad * s, rad * s)
            cv2.ellipse(im, c, (int(size * 0.5 * s), max(1, int(size * 0.28 * squash * s))), key[1], 0, 360, 255, -1,
                        cv2.LINE_AA)
            m = cv2.resize(im, (rad * 2, rad * 2), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
            shade = cv2.GaussianBlur(m, (0, 0), size * 0.12 + 0.5)
            self.cache[key] = (m, 0.75 + 0.25 * shade)
        return self.cache[key]

    def draw(self, x, t, density, burst=True):
        """Composite the petals onto x (H, W, 3) in place; density 0..1 sets how many fall."""
        out = x
        if density > 0:
            age = t - self.t0
            ys = -40 + self.vy * age
            vis = (age > 0) & (ys < H + 40) & (self.rank < density)
            for i in np.nonzero(vis)[0]:
                px = self.x0[i] + self.sway[i] * np.sin(2 * np.pi * self.fs[i] * t + self.ph[i])
                squash = 0.35 + 0.65 * abs(np.cos(self.flip[i] * t + self.ph[i]))
                m, sh = self.sprite(self.size[i], self.rot0[i] + self.vr[i] * t, squash)
                _petal(out, m, sh, self.col[i], px, ys[i], 0.92)
        if burst and self.burst_t is not None and self.burst_t <= t < self.burst_t + 4.0:
            u = t - self.burst_t
            g = 900.0
            for i in range(len(self.bx)):
                drag = np.exp(-u * 1.6)
                px = self.bx[i] + self.bvx[i] * (1 - drag) / 1.6
                py = self.by[i] + self.bvy[i] * (1 - drag) / 1.6 + 0.5 * g * u * u * 0.35
                if py > H + 40:
                    continue
                squash = 0.35 + 0.65 * abs(np.cos(3 * u + i))
                m, sh = self.sprite(self.bsize[i], self.brot0[i] + self.bvr[i] * u, squash)
                _petal(out, m, sh, self.bcol[i], px, py, 0.95 * min(1.0, (4.0 - u) / 0.8))
        return out


def _petal(acc, m, sh, col, x, y, alpha):
    r = m.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    x0, y0, x1, y1 = xi - r, yi - r, xi - r + m.shape[1], yi - r + m.shape[0]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1c <= x0c or y1c <= y0c:
        return
    a = (m[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)] * alpha)[..., None]
    c = col * sh[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)][..., None]
    reg = acc[y0c:y1c, x0c:x1c]
    reg[:] = reg * (1 - a) + c * a


def mandala(diameter=1640, s=2):
    """A gold line mandala (alpha mask, float, diameter x diameter): lotus petals, rings and dots."""
    D = diameter * s
    im = np.zeros((D, D), np.uint8)
    c = (D // 2, D // 2)
    R = D // 2 - 4 * s
    for rr, th in ((1.0, 3), (0.97, 1), (0.74, 2), (0.71, 1), (0.47, 2), (0.30, 1)):
        cv2.circle(im, c, int(R * rr), 255, max(1, th * s), cv2.LINE_AA)
    for ring, n, r0, r1, wide in ((0, 32, 0.74, 0.97, 0.55), (1, 24, 0.47, 0.71, 0.6), (2, 16, 0.30, 0.47, 0.7)):
        for k in range(n):
            a = 2 * np.pi * (k + 0.5 * (ring % 2)) / n
            pts = []
            for u in np.linspace(0, 1, 40):                  # a pointed lotus petal outline
                rr = r0 + (r1 - r0) * u
                half = wide * np.pi / n * np.sin(np.pi * u) ** 0.8 * (1 - 0.6 * u)
                pts.append((rr, a - half))
            pts += [(r, b + 2 * (a - b)) for r, b in reversed(pts)]
            poly = np.array([[c[0] + R * r * np.cos(b), c[1] + R * r * np.sin(b)] for r, b in pts], np.int32)
            cv2.polylines(im, [poly], True, 255, max(1, int(1.3 * s)), cv2.LINE_AA)
    for k in range(64):
        a = 2 * np.pi * k / 64
        cv2.circle(im, (int(c[0] + R * 0.855 * np.cos(a)), int(c[1] + R * 0.855 * np.sin(a))), int(2.2 * s), 255, -1,
                   cv2.LINE_AA)
    return cv2.resize(im, (diameter, diameter), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
