"""Per-frame image effects for the SHELF CAMPUS compositor. Frames are float32 RGB in [0, 1], 1080x1920.

Grade and wall looks need the person matte (1 = person): the wall is re-lit on its own, the founders keep
natural skin. Camera helpers, flashes, glitches, shockwaves and grain come from the S.H.E.L.F reel's kit.
"""
import cv2
import numpy as np

W, H = 1080, 1920
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def lum(img):
    return (img @ LUMA)[..., None]


# ---------- grade ----------
def s_curve(x, k=0.20):
    """Filmic contrast: midtone slope 1 + k*2*pi/... endpoints fixed."""
    return np.clip(x - k * np.sin(2 * np.pi * x) / (2 * np.pi), 0, 1)


def hue_sat_boost(img, h0, h1, amount, sat_min=0.25):
    """Saturation boost for hues in [h0, h1] degrees (the yellow sunglasses: ~38-62)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)          # float input: H in degrees 0-360, S, V in 0-1
    h, s = hsv[..., 0], hsv[..., 1]
    w = np.clip(1 - np.abs(h - (h0 + h1) / 2) / ((h1 - h0) / 2), 0, 1) * np.clip((s - sat_min) / 0.2, 0, 1)
    hsv[..., 1] = np.clip(s * (1 + amount * w), 0, 1)
    hsv[..., 2] = np.clip(hsv[..., 2] * (1 + 0.06 * amount * w), 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def clarity(img, amount=0.22, sigma=14, fine=0.30):
    """Local contrast on luminance (large radius) plus fine sharpening: 'expensive lens' crispness."""
    l = lum(img)[..., 0]
    big = cv2.GaussianBlur(l, (0, 0), sigma)
    small = cv2.GaussianBlur(l, (0, 0), 1.1)
    detail = (l - big) * amount + (l - small) * fine
    mid = 1 - np.abs(l - 0.5) * 1.6                      # keep it out of the deepest shadows / brightest highlights
    return np.clip(img + (detail * np.clip(mid, 0.25, 1))[..., None], 0, 1)


def grade(img, look):
    """The base commercial grade, then a per-section look.
    looks: 'tense' (the hook), 'night' (the founders on the navy wall), 'day' (payoff), 'freeze'."""
    x = s_curve(img, 0.22 if look != "day" else 0.18)
    l = lum(x)
    sh = np.clip(1 - l * 2.4, 0, 1)
    hi = np.clip((l - 0.55) * 2.2, 0, 1)
    if look == "tense":
        x = x + sh * np.array([-0.010, 0.006, 0.020], np.float32) + hi * np.array([0.006, 0.002, -0.006], np.float32)
        sat = 0.94
    elif look == "night":
        x = x + sh * np.array([-0.012, 0.000, 0.022], np.float32) + hi * np.array([0.004, 0.004, 0.006], np.float32)
        sat = 1.02
    elif look == "freeze":
        sat = 0.30
    else:   # day
        x = x + sh * np.array([-0.004, 0.002, 0.010], np.float32) + hi * np.array([0.012, 0.006, -0.008], np.float32)
        x = x * 1.025
        sat = 1.08
    l = lum(x)
    x = l + (x - l) * sat
    x = np.clip(x, 0, 1)
    if look != "freeze":
        x = hue_sat_boost(x, 36, 64, 0.38)                # the yellow glasses pop
    return clarity(x, 0.20 if look != "freeze" else 0.35)


# ---------- the wall (person matte m: H x W x 1, 1 = person) ----------
_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)


def blob(cx, cy, rx, ry):
    return np.exp(-(((_XX - cx) / rx) ** 2 + ((_YY - cy) / ry) ** 2))[..., None]


def wall_night(img, m, head=(780, 900), k=1.0):
    """Re-light the wall to deep navy (texture kept), a soft blue bloom behind the head. k: 0..1 blend."""
    l = lum(img)
    navy = l * np.array([0.075, 0.115, 0.215], np.float32) + np.array([0.008, 0.015, 0.042], np.float32)
    navy = navy + blob(head[0], head[1] - 120, 600, 680) * np.array([0.10, 0.20, 0.45], np.float32) * 0.42
    navy = navy + blob(head[0] - 420, 420, 520, 520) * np.array([0.03, 0.06, 0.14], np.float32) * 0.6
    bg = img * (1 - k) + navy * k
    return img * m + bg * (1 - m)


def wall_police(img, m, t, beat=0.58315, k=1.0):
    """Red and blue beacon light sweeping across the wall, alternating on the 8th notes."""
    ph = (t / (beat / 2)) % 2.0                           # 0..2: red leads, then blue leads
    red = 0.35 + 0.65 * max(0.0, np.sin(np.pi * ph)) if ph < 1 else 0.25
    blue = 0.35 + 0.65 * max(0.0, np.sin(np.pi * (ph - 1))) if ph >= 1 else 0.25
    sweep = (t * 0.75) % 1.0
    xr = -100 + 1280 * (0.5 + 0.5 * np.sin(2 * np.pi * sweep))
    xb = 1180 - 1280 * (0.5 + 0.5 * np.sin(2 * np.pi * sweep + 1.3))
    light = blob(xr, 560, 640, 900) * np.array([1.0, 0.08, 0.10], np.float32) * red * 0.80
    light += blob(xb, 640, 640, 900) * np.array([0.10, 0.28, 1.0], np.float32) * blue * 0.85
    bg = img * 0.72
    bg = 1 - (1 - bg) * (1 - np.clip(light * k, 0, 1))
    spill = 1 - (1 - img) * (1 - np.clip(light * 0.22 * k, 0, 1))  # a little on the person too
    return spill * m + bg * (1 - m)


def wall_day(img, m, k=1.0):
    """Payoff: a cleaner, brighter, warm-white wall."""
    l = lum(img)
    clean = l + (img - l) * 0.70
    clean = clean * 1.05 + np.array([0.012, 0.008, 0.000], np.float32)
    bg = img * (1 - k) + np.clip(clean, 0, 1) * k
    return img * m + bg * (1 - m)


def rim(img, m, color=(0.55, 0.75, 1.0), strength=0.7, width=7, blur=5):
    """Edge light on the person's silhouette (a backlight from the navy wall)."""
    mm = m[..., 0]
    edge = np.clip(mm - cv2.erode(mm, np.ones((width, width), np.uint8)), 0, 1)
    glow = cv2.GaussianBlur(edge, (0, 0), blur)[..., None] * np.array(color, np.float32)
    return screen(img, np.clip(glow * strength * 1.6, 0, 1))


# ---------- camera ----------
def camera_matrix(scale=1.0, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0, rot=0.0):
    M = cv2.getRotationMatrix2D((cx, cy), rot, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    return M


def warp(img, M, border=cv2.BORDER_REFLECT101, interp=cv2.INTER_CUBIC):
    if np.allclose(M, [[1, 0, 0], [0, 1, 0]]):
        return img
    return cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=border)


def shake_offset(t, t0, amp, decay, freq=19.0, seed=0):
    """Damped handheld jolt: smooth noise (sum of sines) times an exponential decay."""
    if t < t0:
        return 0.0, 0.0, 0.0
    u = t - t0
    e = amp * np.exp(-u / decay)
    ph = seed * 1.7
    dx = e * (np.sin(2 * np.pi * freq * u + ph) * 0.7 + np.sin(2 * np.pi * freq * 1.73 * u + 2 * ph) * 0.3)
    dy = e * (np.cos(2 * np.pi * freq * 0.91 * u + ph) * 0.7 + np.sin(2 * np.pi * freq * 1.37 * u + 3 * ph) * 0.3)
    rot = e * 0.045 * np.sin(2 * np.pi * freq * 0.63 * u + ph)
    return dx, dy, rot


# ---------- looks ----------
def screen(base, layer, alpha=1.0):
    return 1 - (1 - base) * (1 - layer * alpha)


def over(base, rgba):
    a = rgba[..., 3:4]
    return rgba[..., :3] * a + base * (1 - a)


def load_rgba(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    im = im.astype(np.float32) / 255
    if im.shape[2] == 3:
        im = np.dstack([im, np.ones(im.shape[:2], np.float32)])
    return np.dstack([im[..., 2::-1], im[..., 3:4]])


def flash(img, color, alpha):
    if alpha <= 0.002:
        return img
    return img * (1 - alpha) + np.array(color, np.float32) * alpha


def chroma(img, px):
    """Lateral chromatic aberration: R and B pushed apart from the centre."""
    if px <= 0.2:
        return img
    out = img.copy()
    for c, s in ((0, 1.0), (2, -1.0)):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + s * px / (W / 2))
        out[..., c] = cv2.warpAffine(img[..., c], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return out


def glitch(img, n, strength):
    """Digital tear: horizontal slices displaced, one channel offset, a few blocky rows."""
    if strength <= 0:
        return img
    rng = np.random.default_rng(9100 + n)
    out = img.copy()
    y = 0
    while y < H:
        hgt = int(rng.integers(8, 90))
        if rng.random() < 0.35 * strength:
            shift = int(rng.normal(0, 60 * strength))
            out[y:y + hgt] = np.roll(img[y:y + hgt], shift, axis=1)
            if rng.random() < 0.5:
                ch = int(rng.integers(0, 3))
                out[y:y + hgt, :, ch] = np.roll(img[y:y + hgt, :, ch], shift + int(rng.normal(0, 25 * strength)), axis=1)
        y += hgt
    return out


def censor(img, n, cx, cy, w=250, h=96):
    """The bleep's censor bar: a pixelated, glitching block over the mouth with an RGB-split edge."""
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    x0, y0 = max(0, x0), max(0, y0)
    reg = img[y0:y0 + h, x0:x0 + w]
    if reg.size == 0:
        return img
    pix = cv2.resize(cv2.resize(reg, (max(1, w // 22), max(1, h // 22)), interpolation=cv2.INTER_AREA), (reg.shape[1], reg.shape[0]),
                     interpolation=cv2.INTER_NEAREST)
    rng = np.random.default_rng(31000 + n)
    blk = pix * 0.35 + np.array([0.02, 0.02, 0.03], np.float32) * 0.65
    for _ in range(3):                                       # glitch slices through the bar
        yy = int(rng.integers(0, max(1, reg.shape[0] - 10)))
        hh = int(rng.integers(6, 18))
        blk[yy:yy + hh] = np.roll(blk[yy:yy + hh], int(rng.integers(-30, 30)), axis=1)
        blk[yy:yy + hh, :, int(rng.integers(0, 3))] += 0.25
    out = img.copy()
    out[y0:y0 + reg.shape[0], x0:x0 + reg.shape[1]] = np.clip(blk, 0, 1)
    sl = out[y0 - 4:y0 + reg.shape[0] + 4, max(0, x0 - 10):x0 + reg.shape[1] + 10]
    sl[..., 0] = np.roll(sl[..., 0], 5, axis=1)
    sl[..., 2] = np.roll(sl[..., 2], -5, axis=1)
    return out


def zoom_blur(img, k, cx=W / 2, cy=H / 2, taps=7):
    if k <= 0.01:
        return img
    acc = img.copy()
    for i in range(1, taps):
        M = camera_matrix(1 + 0.09 * k * i / (taps - 1), cx, cy)
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return acc / taps


_GRID = None


def shockwave(img, u, cx=W / 2, cy=H / 2, amp=28.0, width=90.0):
    """A refraction ring expanding from (cx, cy); u = seconds since the hit (0..~0.5)."""
    global _GRID
    if u < 0 or u > 0.55:
        return img
    if _GRID is None:
        _GRID = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    xs, ys = _GRID
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    radius = 2400 * (u / 0.55) ** 0.7
    ring = np.exp(-((r - radius) / width) ** 2) * amp * (1 - u / 0.55)
    return cv2.remap(img, (xs - dx / r * ring).astype(np.float32), (ys - dy / r * ring).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT101)


def glint(img, x, y, size, k):
    """Anamorphic star on a lens: a hot core plus horizontal/diagonal streaks; k in [0, 1]."""
    if k <= 0.01:
        return img
    x0, x1, y0, y1 = int(max(0, x - size * 3)), int(min(W, x + size * 3)), int(max(0, y - size * 2)), int(min(H, y + size * 2))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - x, yy - y
    core = np.exp(-(dx ** 2 + dy ** 2) / (2 * (size * 0.18) ** 2))
    hz = np.exp(-(dy ** 2) / (2 * (size * 0.03) ** 2)) * np.exp(-np.abs(dx) / (size * 1.6))
    vt = np.exp(-(dx ** 2) / (2 * (size * 0.03) ** 2)) * np.exp(-np.abs(dy) / (size * 0.9))
    d1 = np.exp(-((dx - dy) ** 2) / (2 * (size * 0.035) ** 2)) * np.exp(-np.abs(dx + dy) / (size * 0.7))
    d2 = np.exp(-((dx + dy) ** 2) / (2 * (size * 0.035) ** 2)) * np.exp(-np.abs(dx - dy) / (size * 0.7))
    s = np.clip((core * 1.2 + hz + 0.7 * vt + 0.45 * (d1 + d2)) * k, 0, 1)[..., None] * np.array([1.0, 0.97, 0.88], np.float32)
    out = img.copy()
    out[y0:y1, x0:x1] = screen(img[y0:y1, x0:x1], s)
    return out


def bloom(img, thresh=0.78, sigma=22, amount=0.16):
    hi = np.clip(img - thresh, 0, 1) / (1 - thresh)
    return screen(img, cv2.GaussianBlur(hi, (0, 0), sigma) * amount)


def _radial():
    r = np.sqrt(((_XX - W / 2) / (W * 0.62)) ** 2 + ((_YY - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1 - np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)


_VIG = _radial()


def vignette(img, amount=0.16):
    return img * (1 - amount + amount * _VIG)


def grain(img, n, amount=0.018):
    rng = np.random.default_rng(7000 + n)
    g = rng.standard_normal((H // 2, W // 2, 1)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    l = img.mean(axis=2, keepdims=True)
    return np.clip(img + g * amount * (0.35 + 0.65 * (1 - np.abs(l - 0.5) * 2)), 0, 1)


def desat(img, k):
    l = lum(img)
    return img * (1 - k) + l * k
