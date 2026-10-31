"""Per-frame image effects for the TaxWise reel compositor. Frames are float32 RGB in [0, 1], 1080x1920.
Adapted from the S.H.E.L.F reel's fxlib, plus the TaxWise look: the room re-lit to midnight navy, a gold aura."""
import cv2
import numpy as np

W, H = 1080, 1920
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

# brand palette (linear-ish display RGB, 0..1)
NAVY_DEEP = np.array([0.012, 0.020, 0.038], np.float32)     # shadows of the re-lit room
NAVY_WALL = np.array([0.062, 0.090, 0.150], np.float32)     # the white wall, re-lit: muted midnight navy
ROYAL = np.array([0.122, 0.169, 0.549], np.float32)         # #1F2B8C, the brand's blue (used sparingly)
GOLD = np.array([1.0, 0.80, 0.46], np.float32)
GOLD_HI = np.array([1.0, 0.93, 0.76], np.float32)
WARM_WHITE = np.array([1.0, 0.95, 0.86], np.float32)


def luma(img):
    return (img @ LUMA)[..., None]


def smoothstep(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


# ---------- the look ----------
_LN = 4096
_LX = np.linspace(0, 1, _LN, dtype=np.float32)


def _lut(x):
    """Index of x in the 4096-step LUT domain (x in 0..1)."""
    return np.clip(x * (_LN - 1) + 0.5, 0, _LN - 1).astype(np.int32)


_NAVY_LUT = None


def relight(img, pool=None):
    """The room behind him as a dim midnight-navy set: brightness kept as a soft gradient (so the window,
    the soffit and the wall still read, faintly), colour replaced by navy; `pool` adds the royal-blue light."""
    global _NAVY_LUT
    if _NAVY_LUT is None:
        _NAVY_LUT = (NAVY_DEEP + (NAVY_WALL - NAVY_DEEP) * (_LX ** 1.35)[:, None]).astype(np.float32)
    l = luma(img)
    out = _NAVY_LUT[_lut(l[..., 0])]
    out += (img - l) * np.float32(0.06)                             # a trace of the original colour, for life
    if pool is not None:
        out += pool
    return out


_DESK_LUT = np.stack([np.clip(_LX * g, 0, 1) ** 1.08 for g in (0.60, 0.50, 0.44)], 1).astype(np.float32)


def grade_desk(img):
    """The desk in front of him: dark, rich wood that frames the bottom of the picture."""
    l = luma(img)
    x = l + (img - l) * np.float32(0.80)
    i = _lut(x)
    return np.stack([_DESK_LUT[i[..., c], c] for c in range(3)], -1)


_SKIN_LUT = np.clip(np.clip(_LX * 1.03 + 0.005, 0, 1) - 0.16 * np.sin(2 * np.pi * np.clip(_LX * 1.03 + 0.005, 0, 1))
                    / (2 * np.pi), 0, 1).astype(np.float32)


def grade_person(img):
    """Him: a clean, warm, gently contrasted skin grade (filmic S, warm highlights, cooler shadows)."""
    x = _SKIN_LUT[_lut(img)]
    l = luma(x)
    hi = smoothstep(0.45, 0.95, l)
    sh = 1 - smoothstep(0.05, 0.40, l)
    x += hi * np.array([0.020, 0.008, -0.016], np.float32) + sh * np.array([-0.006, 0.000, 0.010], np.float32)
    l = luma(x)
    return np.clip(l + (x - l) * np.float32(1.06), 0, 1)


def grade_scene(img):
    """The final touch on everything: a warm-gold roll-off in the highlights."""
    l = luma(img)
    hi = smoothstep(0.65, 1.0, l)
    return np.clip(img + hi * np.array([0.012, 0.004, -0.012], np.float32), 0, 1)


def _radial(cx=W / 2, cy=H / 2, rx=W * 0.62, ry=H * 0.62):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip(1 - np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)


_VIG = _radial()


def vignette(img, amount=0.2):
    return img * (np.float32(1 - amount) + np.float32(amount) * _VIG)


_GRAIN = None


def grain(img, n, amount=0.018):
    """Film grain: one of 16 precomputed half-res fields, shifted per frame (deterministic), stronger in the mids."""
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(7000)
        _GRAIN = [rng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(16)]
    g = _GRAIN[n % 16]
    g = np.roll(g, ((n * 37) % (H // 2), (n * 53) % (W // 2)), axis=(0, 1))
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    l = luma(img)
    return np.clip(img + g * (np.float32(amount) * (0.35 + 0.65 * (1 - np.abs(l - 0.5) * 2))), 0, 1)


def screen(base, layer, alpha=1.0):
    return 1 - (1 - base) * (1 - np.clip(layer * alpha, 0, 1))


def pool(cx, cy, r, color, k):
    """A soft pool of light (additive), e.g. the royal-blue backlight behind him."""
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    m = np.exp(-d * d * 1.6)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return m * color * k


# ---------- the person ----------
def decontaminate(img, m, B):
    """Pull the original (bright) wall out of his semi-transparent edges. Luminance only: from
    I = m F + (1 - m) B, the edge's true brightness is (L(I) - (1 - m) L(B)) / m, and the observed colour is
    scaled to it. Dark hair loses its white wash; the hue is never amplified, so skin against the white
    wall (nearly as bright as it) can't turn red the way a full colour unmix does at low alpha."""
    mm = m[..., None]
    li = luma(img)
    lf = (li - (1 - mm) * luma(B)) / np.maximum(mm, 0.3)
    k = np.clip(lf / np.maximum(li, 1e-3), 0.15, 1.05)
    w = smoothstep(0.97, 0.70, mm) * (mm > 0.01)                 # 1 on the soft edge, 0 where solid
    return img * (1 - w + w * k)


def local_background(img, m, plate, sigma=14.0):
    """The wall right behind his edges, from THIS frame: the surrounding background pushed in under his
    outline (normalised convolution at half size). No exposure mismatch with the live frame, unlike a plate.
    Deep inside his silhouette (never visible) it falls back to the shot's clean plate."""
    w = 1.0 - cv2.dilate((m > 0.02).astype(np.float32), np.ones((7, 7), np.uint8))
    hh, ww = m.shape
    hs, ws = max(1, hh // 2), max(1, ww // 2)
    ws_ = cv2.resize(w, (ws, hs), interpolation=cv2.INTER_AREA)
    num = cv2.GaussianBlur(cv2.resize(img, (ws, hs), interpolation=cv2.INTER_AREA) * ws_[..., None], (0, 0), sigma / 2)
    den = cv2.GaussianBlur(ws_, (0, 0), sigma / 2)[..., None]
    est = cv2.resize(num / np.maximum(den, 1e-4), (ww, hh), interpolation=cv2.INTER_LINEAR)
    conf = cv2.resize(np.clip(den / 0.08, 0, 1), (ww, hh), interpolation=cv2.INTER_LINEAR)[..., None]
    est = est * conf + plate * (1 - conf)
    wf = w[..., None]
    return img * wf + est * (1 - wf)


def refine_alpha(img, m, B, sigma=10.0):
    """Tighten the matte's soft edge with a colour key: in the edge band, each pixel's opacity is its
    projection onto the line from the nearby wall colour B to the nearby foreground colour (hair, skin),
    trusted where those two differ (dark hair on the white wall: strongly). The rembg matte runs a few px
    fat; those pixels are pure wall and would otherwise glow as a pale ring on the navy."""
    band = (m > 0.003) & (m < 0.65)                              # the soft outer tail only, never the core
    if not band.any():
        return m
    solid = (m >= 0.985).astype(np.float32)
    hh, ww = m.shape
    hs, ws = max(1, hh // 2), max(1, ww // 2)
    sm = cv2.resize(solid, (ws, hs), interpolation=cv2.INTER_AREA)
    num = cv2.GaussianBlur(cv2.resize(img, (ws, hs), interpolation=cv2.INTER_AREA) * sm[..., None], (0, 0), sigma / 2)
    den = cv2.GaussianBlur(sm, (0, 0), sigma / 2)[..., None]
    Fl = cv2.resize(num / np.maximum(den, 1e-4), (ww, hh), interpolation=cv2.INTER_LINEAR)
    d = Fl - B
    dd = (d * d).sum(-1)
    a = ((img - B) * d).sum(-1) / np.maximum(dd, 1e-6)
    a = np.clip(a, 0, 1)
    conf = np.clip((np.sqrt(dd) - 0.08) / 0.25, 0, 1)            # how far apart hair/skin and wall are
    darker = (B - Fl) @ LUMA                                     # only where the foreground is DARK (hair, beard):
    conf = conf * np.clip((darker - 0.25) / 0.15, 0, 1)         # skin is nearly as bright as the white wall
    out = m.copy()
    k = conf[band]
    out[band] = np.minimum(m[band] * (1 - k) + a[band] * k, m[band] + 0.08)
    return out


def rim_band(m, width=11):
    """Where a backlight would catch him: a thin band inside his outline, most on edges facing up."""
    m8 = (m * 255).astype(np.uint8)
    inner = cv2.erode(m8, np.ones((width, width), np.uint8)).astype(np.float32) / 255
    band = cv2.GaussianBlur(np.clip(m - inner, 0, 1), (0, 0), 2.5) * m
    ms = cv2.GaussianBlur(m, (0, 0), 6)
    gy = cv2.Sobel(ms, cv2.CV_32F, 0, 1, ksize=5)
    gx = cv2.Sobel(ms, cv2.CV_32F, 1, 0, ksize=5)
    up = np.clip(gy / (np.sqrt(gx * gx + gy * gy) + 1e-6), 0, 1)
    return (band * (0.30 + 0.70 * up))[..., None]


def backlight(img, band, strength, color=GOLD):
    """Light, not paint: the gold added in proportion to what it lands on (hair strands catch it, the dark
    gaps stay dark), plus a little sheen so even black hair picks up an edge."""
    if strength <= 0.01:
        return img
    return img + band * strength * (img * 2.4 + 0.035) * color


def halo(m, strength, color=GOLD, sigma=38):
    """The aura behind him: his silhouette, blurred wide (computed at quarter size), added to the wall."""
    if strength <= 0.01:
        return None
    small = cv2.resize(m, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(small, (0, 0), sigma / 4)
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return (b[..., None] * color * strength).astype(np.float32)


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


# ---------- transitions and hits ----------
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
    """Digital tear: horizontal slices displaced, one channel offset."""
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


def flash(img, color, alpha):
    if alpha <= 0.002:
        return img
    a = np.float32(alpha)
    return img * (1 - a) + np.asarray(color, np.float32) * a


def zoom_blur(img, k, cx=W / 2, cy=H / 2, taps=7):
    """Radial (zoom) blur: the average of copies scaled up to 1 + 0.09k about (cx, cy). k in 0..1."""
    if k <= 0.01:
        return img
    acc = img.copy()
    for i in range(1, taps):
        s = 1 + 0.09 * k * i / (taps - 1)
        acc += cv2.warpAffine(img, camera_matrix(s, cx, cy), (W, H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REFLECT101)
    return acc / taps


def light_leak(img, t, k, warm=True, side=0.0):
    """A soft drifting leak from the frame edge (screen-blended)."""
    if k <= 0.01:
        return img
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    cx = float(W * (0.08 + side + 0.12 * np.sin(t * 0.7)))         # python floats: a numpy float64 scalar
    cy = float(H * (0.22 + 0.08 * np.cos(t * 0.5)))                 # would promote the whole frame to float64
    r = np.sqrt(((xx - cx) / (W * 0.55)) ** 2 + ((yy - cy) / (H * 0.4)) ** 2)
    m = np.clip(1 - r, 0, 1) ** 2
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    col = np.array([1.0, 0.62, 0.26] if warm else [0.35, 0.50, 1.0], np.float32) * np.float32(k)
    return screen(img, m * col)


def over(base, rgba):
    """Straight-alpha RGBA over base."""
    a = rgba[..., 3:4]
    return rgba[..., :3] * a + base * (1 - a)


def load_rgba(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    im = im.astype(np.float32) / 255
    if im.ndim == 2:
        im = np.dstack([im, im, im])
    if im.shape[2] == 3:
        im = np.dstack([im, np.ones(im.shape[:2], np.float32)])
    return np.dstack([im[..., 2::-1], im[..., 3:4]])
