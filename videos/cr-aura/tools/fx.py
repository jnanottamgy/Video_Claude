"""Per-frame image effects for the CR aura edit. Frames are float32 RGB in [0, 1]; any size
(1080x1920 final, 540x960 previews). Adapted from videos/shelf-reel/tools/fxlib.py, plus the aura
looks: bloom, letterbox, glow outline, echo, double exposure, region flashes, flow interpolation."""
import functools

import cv2
import numpy as np

LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def luma(img):
    return img @ LUM


@functools.lru_cache(maxsize=8)
def _radial(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
    return np.clip(1 - np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)


@functools.lru_cache(maxsize=8)
def _grid(h, w):
    return np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))


# ---------- the look ----------
def grade(img, warmth=1.0, sat=0.92, contrast=1.0, lift=0.022, teal=1.0):
    """Teal shadows / warm highlights, gentle S-curve, lifted blacks, rolled-off highlights."""
    x = np.clip(img - 0.18 * contrast * np.sin(2 * np.pi * img) / (2 * np.pi), 0, 1)
    l = luma(x)[..., None]
    sh = np.clip(1 - l * 2.3, 0, 1)
    hi = np.clip((l - 0.5) * 2.0, 0, 1)
    x = x + sh * np.array([-0.020, 0.006, 0.030], np.float32) * teal + hi * np.array([0.022, 0.008, -0.020], np.float32) * warmth
    x = l + (x - l) * sat
    x = lift + x * (1 - lift - 0.03)            # lifted blacks, highlights stop short of clip
    return np.clip(x, 0, 1)


def tame_reds(img, k=0.25):
    """The lab's curtains are a saturated red that dominates; pull their saturation down a little."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    red = np.clip((r - np.maximum(g, b)) * 3.0 - 0.4, 0, 1)[..., None]
    l = luma(img)[..., None]
    return img * (1 - k * red) + (l * 0.9 + img * 0.1) * k * red


def bloom(img, thresh=0.72, amount=0.35, sigma_frac=0.018):
    """Halation: blur the highlights and screen them back, warm-tinted."""
    h, w = img.shape[:2]
    l = luma(img)
    m = np.clip((l - thresh) / (1 - thresh), 0, 1)[..., None]
    hi = img * m
    small = cv2.resize(hi, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    s = max(1.0, sigma_frac * h / 4)
    b = cv2.GaussianBlur(small, (0, 0), s) * 0.6 + cv2.GaussianBlur(small, (0, 0), s * 3) * 0.4
    b = cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR) * np.array([1.0, 0.86, 0.72], np.float32)
    return screen(img, b, amount)


def vignette(img, amount=0.2):
    h, w = img.shape[:2]
    return img * (1 - amount + amount * _radial(h, w))


def grain(img, n, amount=0.03):
    h, w = img.shape[:2]
    rng = np.random.default_rng(7000 + n)
    g = rng.standard_normal((h // 2, w // 2, 1)).astype(np.float32)
    g = cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
    l = img.mean(axis=2, keepdims=True)
    return np.clip(img + g * amount * (0.35 + 0.65 * (1 - np.abs(l - 0.5) * 2)), 0, 1)


def sharpen(img, amount=0.45, sigma=1.2):
    b = cv2.GaussianBlur(img, (0, 0), sigma)
    return np.clip(img + (img - b) * amount, 0, 1)


def letterbox(img, frac):
    """Cinematic bars; frac = bar height as a fraction of frame height (each)."""
    if frac <= 0:
        return img
    h = img.shape[0]
    b = int(round(h * frac))
    out = img.copy()
    out[:b] = 0
    out[h - b:] = 0
    return out


# ---------- camera ----------
def camera_matrix(w, h, scale=1.0, cx=None, cy=None, dx=0.0, dy=0.0, rot=0.0):
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    M = cv2.getRotationMatrix2D((cx, cy), rot, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    return M


def camera(img, scale=1.0, cx=None, cy=None, dx=0.0, dy=0.0, rot=0.0, interp=cv2.INTER_CUBIC):
    if abs(scale - 1) < 1e-4 and abs(dx) < 1e-3 and abs(dy) < 1e-3 and abs(rot) < 1e-4:
        return img
    h, w = img.shape[:2]
    M = camera_matrix(w, h, scale, cx, cy, dx, dy, rot)
    return cv2.warpAffine(img, M, (w, h), flags=interp, borderMode=cv2.BORDER_REFLECT101)


def shake_offset(u, amp, decay, freq=17.0, seed=0):
    """Damped jolt u seconds after a hit: (dx, dy, rot)."""
    if u < 0:
        return 0.0, 0.0, 0.0
    e = amp * np.exp(-u / decay)
    ph = seed * 1.7
    dx = e * (np.sin(2 * np.pi * freq * u + ph) * 0.7 + np.sin(2 * np.pi * freq * 1.73 * u + 2 * ph) * 0.3)
    dy = e * (np.cos(2 * np.pi * freq * 0.91 * u + ph) * 0.7 + np.sin(2 * np.pi * freq * 1.37 * u + 3 * ph) * 0.3)
    rot = e * 0.05 * np.sin(2 * np.pi * freq * 0.63 * u + ph)
    return dx, dy, rot


# ---------- hits ----------
def chroma(img, px):
    """Lateral chromatic aberration: R and B scaled apart about the centre by px at the edge."""
    if px <= 0.2:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    for c, s in ((0, 1.0), (2, -1.0)):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, 1 + s * px / (w / 2))
        out[..., c] = cv2.warpAffine(img[..., c], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return out


def rgb_split(img, px, angle=0.0):
    """Hard RGB split: R and B channels shifted px in opposite directions."""
    if px < 0.5:
        return img
    dx, dy = px * np.cos(angle), px * np.sin(angle)
    out = img.copy()
    h, w = img.shape[:2]
    for c, s in ((0, 1), (2, -1)):
        M = np.float32([[1, 0, s * dx], [0, 1, s * dy]])
        out[..., c] = cv2.warpAffine(img[..., c], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return out


def glitch(img, n, strength):
    """Digital tear: horizontal slices displaced, one channel offset."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    rng = np.random.default_rng(9100 + n)
    out = img.copy()
    y = 0
    while y < h:
        hgt = int(rng.integers(max(4, h // 240), max(8, h // 22)))
        if rng.random() < 0.35 * strength:
            shift = int(rng.normal(0, 0.055 * w * strength))
            out[y:y + hgt] = np.roll(img[y:y + hgt], shift, axis=1)
            if rng.random() < 0.5:
                ch = int(rng.integers(0, 3))
                out[y:y + hgt, :, ch] = np.roll(img[y:y + hgt, :, ch], shift + int(rng.normal(0, 0.023 * w * strength)), axis=1)
        y += hgt
    return out


def flash(img, color, alpha):
    if alpha <= 0.002:
        return img
    return img * (1 - alpha) + np.array(color, np.float32) * alpha


def screen(base, layer, alpha=1.0):
    return 1 - (1 - base) * (1 - layer * alpha)


def zoom_blur(img, k, cx=None, cy=None, taps=8, reach=0.10):
    """Radial (zoom) blur toward (cx, cy); k in 0..1."""
    if k <= 0.01:
        return img
    h, w = img.shape[:2]
    acc = img.copy()
    for i in range(1, taps):
        M = camera_matrix(w, h, 1 + reach * k * i / (taps - 1), cx, cy)
        acc += cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return acc / taps


def motion_blur(img, k, angle_deg=0.0, length_frac=0.06):
    """Directional blur (whips); k in 0..1."""
    if k <= 0.01:
        return img
    h, w = img.shape[:2]
    L = max(3, int(length_frac * w * k)) | 1
    ker = np.zeros((L, L), np.float32)
    ker[L // 2, :] = 1.0 / L
    R = cv2.getRotationMatrix2D((L / 2 - 0.5, L / 2 - 0.5), angle_deg, 1.0)
    ker = cv2.warpAffine(ker, R, (L, L))
    ker /= max(ker.sum(), 1e-6)
    return cv2.filter2D(img, -1, ker, borderType=cv2.BORDER_REFLECT101)


def shockwave(img, u, cx=None, cy=None, amp=0.026, width=0.085, life=0.55):
    """A refraction ring expanding from (cx, cy); u = seconds since the hit. amp/width as frame-width fractions."""
    if u < 0 or u > life:
        return img
    h, w = img.shape[:2]
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    xs, ys = _grid(h, w)
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    radius = 2.25 * w * (u / life) ** 0.7
    ring = np.exp(-((r - radius) / (width * w)) ** 2) * amp * w * (1 - u / life)
    return cv2.remap(img, (xs - dx / r * ring).astype(np.float32), (ys - dy / r * ring).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)


def glint(img, x, y, size, k, col=(1.0, 0.95, 0.82)):
    """Anamorphic lens star: hot core plus streaks; k in 0..1."""
    if k <= 0.01:
        return img
    h, w = img.shape[:2]
    yy, xx = np.ogrid[0:h, 0:w]
    dx, dy = (xx - x).astype(np.float32), (yy - y).astype(np.float32)
    core = np.exp(-(dx ** 2 + dy ** 2) / (2 * (size * 0.18) ** 2))
    hz = np.exp(-(dy ** 2) / (2 * (size * 0.025) ** 2)) * np.exp(-np.abs(dx) / (size * 2.2))
    vt = np.exp(-(dx ** 2) / (2 * (size * 0.03) ** 2)) * np.exp(-np.abs(dy) / (size * 0.8))
    s = (core * 1.2 + hz + 0.5 * vt) * k
    return screen(img, np.clip(s, 0, 1)[..., None] * np.array(col, np.float32))


def light_leak(img, t, k, warm=True, side=0):
    """A soft drifting leak from a frame edge (screen-blended)."""
    if k <= 0.01:
        return img
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h:4, 0:w:4].astype(np.float32)
    cx = w * ((0.08 if side == 0 else 0.92) + 0.12 * np.sin(t * 0.9))
    cy = h * (0.25 + 0.12 * np.cos(t * 0.6))
    r = np.sqrt(((xx - cx) / (w * 0.6)) ** 2 + ((yy - cy) / (h * 0.42)) ** 2)
    m = np.clip(1 - r, 0, 1) ** 2
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
    col = np.array([1.0, 0.52, 0.2] if warm else [0.35, 0.62, 1.0], np.float32)
    return screen(img, m * col * k)


def tunnel(img, k):
    """Drain colour, darken, close the vignette in (tension). k in 0..1."""
    if k <= 0.005:
        return img
    l = img.mean(axis=2, keepdims=True)
    img = img * (1 - 0.5 * k) + l * 0.5 * k
    return vignette(img * (1 - 0.12 * k), 0.32 * k)


def desat(img, k):
    if k <= 0.003:
        return img
    l = luma(img)[..., None]
    return img * (1 - k) + l * k


# ---------- compositing ----------
def over(base, rgba):
    a = rgba[..., 3:4]
    return rgba[..., :3] * a + base * (1 - a)


def matte_up(m_small, guide_rgb, r=10, eps=2e-3):
    """Upsample a low-res matte to the guide's size and snap it to the guide's edges (guided filter)."""
    h, w = guide_rgb.shape[:2]
    p = cv2.resize(m_small, (w, h), interpolation=cv2.INTER_LINEAR)
    I = luma(guide_rgb)
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return np.clip(box(a) * I + box(b), 0, 1)


def keep_blob(m, seed=None, thresh=0.5, min_frac=0.002):
    """Keep only one person: the connected component containing / nearest the seed (x, y), or the largest."""
    mb = (m > thresh).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mb, connectivity=8)
    if n <= 2:
        return m
    h, w = m.shape
    cand = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > min_frac * h * w]
    if not cand:
        return m
    if seed is None:
        k = max(cand, key=lambda i: stats[i, cv2.CC_STAT_AREA])
    else:
        sx, sy = seed
        if 0 <= int(sy) < h and 0 <= int(sx) < w and lab[int(sy), int(sx)] in cand:
            k = lab[int(sy), int(sx)]
        else:
            k = min(cand, key=lambda i: (cents[i][0] - sx) ** 2 + (cents[i][1] - sy) ** 2)
    keep = (lab == k).astype(np.uint8)
    keep = cv2.dilate(keep, np.ones((9, 9), np.uint8))       # keep the soft edge around the blob
    return m * keep


def aura_glow(img, m, t, k=1.0, color=(1.0, 0.82, 0.42), size_frac=0.035, inner=0.0):
    """A glowing outline around the subject: blurred matte outside the subject, screen-blended.
    t animates a slow shimmer; k is intensity (0..1.5)."""
    if k <= 0.01:
        return img
    h, w = img.shape[:2]
    s = size_frac * w
    small = cv2.resize(m, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(small, (0, 0), s / 4 * 0.5)
    g2 = cv2.GaussianBlur(small, (0, 0), s / 4 * 1.6)
    g = cv2.resize(g1 * 0.65 + g2 * 0.55, (w, h), interpolation=cv2.INTER_LINEAR)
    shimmer = 0.85 + 0.15 * np.sin(t * 9.0)
    outside = np.clip(g - m * (1 - inner), 0, 1)[..., None] * k * shimmer
    return screen(img, np.clip(outside * 1.6, 0, 1) * np.array(color, np.float32))


def rim(m, width_frac=0.004):
    """A thin edge band of the matte (for a crisp white outline)."""
    h, w = m.shape
    r = max(1, int(width_frac * w))
    er = cv2.erode(m, np.ones((2 * r + 1, 2 * r + 1), np.uint8))
    return np.clip(m - er, 0, 1)


def region_flash(img, mask, alpha, color=(1.0, 1.0, 1.0)):
    if alpha <= 0.01:
        return img
    a = (mask * alpha)[..., None]
    return img * (1 - a) + np.array(color, np.float32) * a


def red_mask(img, person=None):
    """The red curtains: strongly red, bright enough, minus the person."""
    hsv = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    hh, ss, vv = hsv[..., 0].astype(np.int16), hsv[..., 1], hsv[..., 2]
    m = (((hh <= 8) | (hh >= 170)) & (ss > 110) & (vv > 70)).astype(np.float32)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.GaussianBlur(m, (0, 0), 2.0)
    if person is not None:
        m = m * (1 - np.clip(person * 1.2, 0, 1))
    return m


def echo(frames, decay=0.55, keep=0.45):
    """Ghost trails: decaying copies of the previous frames under the current one (newest last)."""
    acc = frames[-1].copy()
    wsum, wgt = 1.0, 1.0
    for f in reversed(frames[:-1]):
        wgt *= decay
        acc += f * wgt
        wsum += wgt
    return np.clip(acc / wsum * (1 - keep) + frames[-1] * keep, 0, 1)


# ---------- time ----------
_DIS = None


def flow_interp(a, b, u, scale=0.5):
    """Frame between a (u=0) and b (u=1) by bidirectional optical-flow warping (DIS on half-res grey)."""
    global _DIS
    if u <= 1e-3:
        return a
    if u >= 1 - 1e-3:
        return b
    if _DIS is None:
        _DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    h, w = a.shape[:2]
    sw, sh = int(w * scale), int(h * scale)
    ga = cv2.resize((luma(a) * 255).astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA)
    gb = cv2.resize((luma(b) * 255).astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA)
    fab = _DIS.calc(ga, gb, None)
    fba = _DIS.calc(gb, ga, None)
    fab = cv2.resize(fab, (w, h), interpolation=cv2.INTER_LINEAR) / scale
    fba = cv2.resize(fba, (w, h), interpolation=cv2.INTER_LINEAR) / scale
    xs, ys = _grid(h, w)
    # pixel at p in the middle frame came from a at p - u*fab and from b at p - (1-u)*fba
    wa = cv2.remap(a, xs - u * fab[..., 0], ys - u * fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    wb = cv2.remap(b, xs - (1 - u) * fba[..., 0], ys - (1 - u) * fba[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return wa * (1 - u) + wb * u


def ease_out_cubic(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out_cubic(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_in_cubic(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3
