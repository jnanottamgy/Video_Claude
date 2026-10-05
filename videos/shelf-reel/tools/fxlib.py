"""Per-frame image effects for the S.H.E.L.F reel compositor. Frames are float32 RGB in [0, 1], 1080x1920."""
import cv2
import numpy as np

W, H = 1080, 1920


# ---------- old caption removal ----------
CAP_FILL = np.array([244, 216, 129], np.int16)   # RGB of the burned-in captions' yellow fill
CAP_Y0, CAP_Y1 = 1290, 1470


def caption_mask(rgb8):
    """Pixels of the burned-in caption (yellow fill + its black outline) in the caption band."""
    band = rgb8[CAP_Y0:CAP_Y1]
    fill = (np.abs(band.astype(np.int16) - CAP_FILL).max(axis=2) < 44).astype(np.uint8)
    dark = (band.max(axis=2) < 85).astype(np.uint8)
    fill &= cv2.dilate(dark, np.ones((7, 7), np.uint8))
    if fill.sum() < 60:
        return None
    fill = cv2.morphologyEx(fill, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    m = fill | (dark & cv2.dilate(fill, np.ones((11, 11), np.uint8)))
    return cv2.dilate(m, np.ones((7, 7), np.uint8))


def remove_captions(rgb8, prev_mask=None):
    """Inpaint the old captions. The previous frame's mask is OR-ed in to catch fade/pop frames."""
    m = caption_mask(rgb8)
    if prev_mask is not None:
        m = prev_mask if m is None else (m | prev_mask)
    if m is None:
        return rgb8, None
    out = rgb8.copy()
    band = np.ascontiguousarray(out[CAP_Y0:CAP_Y1])
    out[CAP_Y0:CAP_Y1] = cv2.inpaint(band, m * 255, 7, cv2.INPAINT_TELEA)
    return out, caption_mask(rgb8)


# ---------- grade ----------
def _curve(x, lift, gamma, gain):
    return np.clip((x * gain + lift * (1 - x)), 0, 1) ** gamma


def grade(img, mood):
    """A restrained filmic grade. mood 0 = PROBLEM (cooler, tenser), 1 = S.H.E.L.F (warmer, cleaner)."""
    # gentle S-curve: midtone slope 1.18, endpoints fixed
    x = np.clip(img - 0.18 * np.sin(2 * np.pi * img) / (2 * np.pi), 0, 1)
    l = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    l = l[..., None]
    # split-tone: shadows toward teal, highlights toward warm; strength depends on mood
    sh = np.clip(1 - l * 2.2, 0, 1)
    hi = np.clip((l - 0.55) * 2.2, 0, 1)
    teal = np.array([-0.012, 0.004, 0.018], np.float32) * (1.25 - 0.35 * mood)
    warm = np.array([0.016, 0.006, -0.012], np.float32) * (0.6 + 0.6 * mood)
    x = x + sh * teal + hi * warm
    # saturation: a touch lower in the problem world, richer in the S.H.E.L.F world
    sat = 0.93 + 0.12 * mood
    x = l + (x - l) * sat
    return np.clip(x, 0, 1)


def _radial():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1 - np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)


_VIG = _radial()          # 1 in the centre, falling off toward the corners
EDGE = 1 - _VIG           # 0 in the centre, 1 at the corners


def vignette(img, amount=0.16):
    return img * (1 - amount + amount * _VIG)


def red_alarm(img, k):
    """Red light bleeding in from the frame edges (the panic beats)."""
    e = EDGE * k
    return img * (1 - e) + np.array([0.9, 0.08, 0.05], np.float32) * e


def grain(img, n, amount=0.022):
    rng = np.random.default_rng(7000 + n)
    g = rng.standard_normal((H // 2, W // 2, 1)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    l = img.mean(axis=2, keepdims=True)
    return np.clip(img + g * amount * (0.35 + 0.65 * (1 - np.abs(l - 0.5) * 2)), 0, 1)


# ---------- camera ----------
def camera(img, scale=1.0, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0, rot=0.0, border=cv2.BORDER_REFLECT101):
    if scale == 1.0 and dx == 0 and dy == 0 and rot == 0:
        return img
    M = cv2.getRotationMatrix2D((cx, cy), rot, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=border)


def camera_matrix(scale=1.0, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0, rot=0.0):
    M = cv2.getRotationMatrix2D((cx, cy), rot, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    return M


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
def chroma(img, px):
    """Lateral chromatic aberration: R and B pushed apart from the centre."""
    if px <= 0.2:
        return img
    out = img.copy()
    for c, s in ((0, 1.0), (2, -1.0)):
        sc = 1 + s * px / (W / 2)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, sc)
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


def vhs(img, n, strength=1.0):
    """Tape rewind: tracking wobble, chroma bleed, scanlines, noise band, lifted blacks."""
    rng = np.random.default_rng(12000 + n)
    rows = np.arange(H, dtype=np.float32)
    wob = (np.sin(rows / 37.0 + n * 1.3) * 6 + np.sin(rows / 7.3 + n * 4.1) * 2) * strength
    band_y = int(rng.integers(0, H))
    wob += 70 * strength * np.exp(-((rows - band_y) / 40.0) ** 2)
    mapx = (np.arange(W, dtype=np.float32)[None, :] + wob[:, None]).astype(np.float32)
    mapy = np.repeat(rows[:, None], W, axis=1).astype(np.float32)
    out = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    out[..., 0] = np.roll(out[..., 0], int(7 * strength), axis=1)
    out[..., 2] = np.roll(out[..., 2], -int(7 * strength), axis=1)
    out = cv2.GaussianBlur(out, (0, 0), 1.1)
    out[::3] *= 0.86
    noise = rng.random((H // 4, W // 4, 1)).astype(np.float32)
    out += (cv2.resize(noise, (W, H), interpolation=cv2.INTER_NEAREST)[..., None] - 0.5) * 0.10 * strength
    nb = slice(max(0, band_y - 14), min(H, band_y + 14))
    out[nb] = out[nb] * 0.5 + rng.random((out[nb].shape[0], W, 1)).astype(np.float32) * 0.5
    l = out.mean(axis=2, keepdims=True)
    out = l + (out - l) * 0.75
    return np.clip(out * 0.92 + 0.05, 0, 1)


def flash(img, color, alpha):
    if alpha <= 0.002:
        return img
    c = np.array(color, np.float32)
    return img * (1 - alpha) + c * alpha


def screen(base, layer, alpha=1.0):
    return 1 - (1 - base) * (1 - layer * alpha)


def glint(img, x, y, size, k):
    """Anamorphic star on a lens: a hot core plus horizontal/diagonal streaks; k in [0, 1] is intensity."""
    if k <= 0.01:
        return img
    yy, xx = np.ogrid[0:H, 0:W]
    dx, dy = (xx - x).astype(np.float32), (yy - y).astype(np.float32)
    core = np.exp(-(dx ** 2 + dy ** 2) / (2 * (size * 0.18) ** 2))
    hz = np.exp(-(dy ** 2) / (2 * (size * 0.03) ** 2)) * np.exp(-np.abs(dx) / (size * 1.6))
    vt = np.exp(-(dx ** 2) / (2 * (size * 0.03) ** 2)) * np.exp(-np.abs(dy) / (size * 0.9))
    d1 = np.exp(-((dx - dy) ** 2) / (2 * (size * 0.035) ** 2)) * np.exp(-np.abs(dx + dy) / (size * 0.7))
    d2 = np.exp(-((dx + dy) ** 2) / (2 * (size * 0.035) ** 2)) * np.exp(-np.abs(dx - dy) / (size * 0.7))
    s = (core * 1.2 + hz + 0.7 * vt + 0.45 * (d1 + d2)) * k
    col = np.array([1.0, 0.97, 0.88], np.float32)
    return screen(img, np.clip(s, 0, 1)[..., None] * col)


def light_leak(img, t, k, warm=True):
    """A soft drifting leak from the frame edge (screen-blended)."""
    if k <= 0.01:
        return img
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    cx, cy = W * (0.1 + 0.15 * np.sin(t * 0.7)), H * (0.2 + 0.1 * np.cos(t * 0.5))
    r = np.sqrt(((xx - cx) / (W * 0.55)) ** 2 + ((yy - cy) / (H * 0.4)) ** 2)
    m = np.clip(1 - r, 0, 1) ** 2
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    col = np.array([1.0, 0.55, 0.22] if warm else [0.35, 0.62, 1.0], np.float32)
    return screen(img, m * col * k)


def over(base, rgba):
    """Straight-alpha RGBA over base."""
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


def zoom_blur(img, k, cx=W / 2, cy=H / 2, taps=7):
    """Radial (zoom) blur: the average of copies scaled up to 1 + 0.09k about (cx, cy). k in 0..1."""
    if k <= 0.01:
        return img
    acc = img.copy()
    for i in range(1, taps):
        s = 1 + 0.09 * k * i / (taps - 1)
        M = camera_matrix(s, cx, cy)
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
    mx = (xs - dx / r * ring).astype(np.float32)
    my = (ys - dy / r * ring).astype(np.float32)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)


def tunnel(img, k):
    """Tension: drain colour, darken, close the vignette in. k in 0..1."""
    if k <= 0.005:
        return img
    l = img.mean(axis=2, keepdims=True)
    img = img * (1 - 0.45 * k) + l * 0.45 * k
    img = img * (1 - 0.10 * k)
    return vignette(img, 0.30 * k)
