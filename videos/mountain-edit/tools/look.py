"""The grade and the finishing: per-section looks, grain, halation, vignette, aberration, flashes, bars.

All images are float32 RGB 0..1, 1920x1080.
"""
import functools

import cv2
import numpy as np

W, H = 1920, 1080
REC709 = np.array([0.2126, 0.7152, 0.0722], np.float32)


def luma(x):
    return x @ REC709


def scurve(x, contrast=1.0, pivot=0.42):
    """A filmic S-curve around a pivot: contrast > 1 deepens shadows and rolls highlights off."""
    x = np.clip(x, 0, 1)
    lo = pivot * (x / pivot) ** contrast
    hi = 1 - (1 - pivot) * ((1 - x) / (1 - pivot)) ** contrast
    return np.where(x < pivot, lo, hi)


def split_tone(x, shadow=(0.0, 0.0, 0.0), high=(0.0, 0.0, 0.0), balance=0.45):
    """Tint shadows and highlights separately (offsets in RGB, applied by luminance weight)."""
    L = luma(x)[..., None]
    ws = np.clip((balance - L) / balance, 0, 1) ** 1.5
    wh = np.clip((L - balance) / (1 - balance), 0, 1) ** 1.2
    return x + ws * np.array(shadow, np.float32) + wh * np.array(high, np.float32)


def saturate(x, s, vib=0.0):
    L = luma(x)[..., None]
    if vib:
        sat = np.abs(x - L).max(-1, keepdims=True)
        s = s + vib * (1 - np.clip(sat * 3, 0, 1))         # lift the dull colours more than the vivid ones
    return L + (x - L) * s


def levels(x, black=0.0, white=1.0, gamma=1.0):
    x = np.clip((x - black) / max(1e-4, white - black), 0, 1)
    return x ** (1 / gamma) if gamma != 1.0 else x


LOOKS = {
    # cool, desaturated, deep: the intro's quiet aura (sun stays warm in the highlights)
    "intro": dict(black=0.035, white=0.97, gamma=0.96, contrast=1.30, sat=0.72, vib=0.05,
                  shadow=(-0.02, 0.005, 0.03), high=(0.035, 0.012, -0.03)),
    # punchy, warm dust, crushed blacks: the rally
    "rally": dict(black=0.04, white=0.95, gamma=1.0, contrast=1.36, sat=0.92, vib=0.08,
                  shadow=(-0.02, 0.0, 0.025), high=(0.02, 0.008, -0.02)),
    # golden teal-orange, the summit and the monsoon
    "summit": dict(black=0.03, white=0.96, gamma=0.98, contrast=1.28, sat=0.95, vib=0.15,
                   shadow=(-0.025, 0.008, 0.03), high=(0.045, 0.018, -0.03)),
    # neutral-ish for the crew moments
    "crew": dict(black=0.03, white=0.97, gamma=1.0, contrast=1.22, sat=0.9, vib=0.08,
                 shadow=(-0.015, 0.0, 0.02), high=(0.03, 0.012, -0.02)),
}


def sky_grad(x, strength=0.35, top=0.0, bottom=0.62):
    """A graduated ND: darken the top of the frame (the sky) towards `bottom` (fraction of height)."""
    yy = np.linspace(0, 1, H, dtype=np.float32)
    g = np.clip((bottom - yy) / max(1e-3, bottom - top), 0, 1) ** 1.3
    return x * (1 - strength * g)[:, None, None]


def grade(x, name, amount=1.0):
    if name in (None, "none"):
        return x
    if name == "bw":
        return bw(x)
    p = LOOKS[name]
    y = levels(x, p["black"], p["white"], p["gamma"])
    y = scurve(y, p["contrast"])
    y = saturate(y, p["sat"], p["vib"])
    y = split_tone(y, p["shadow"], p["high"])
    y = np.clip(y, 0, 1)
    return y if amount >= 1 else x + (y - x) * amount


def bw(x, tint=(0.97, 1.0, 1.03), contrast=1.55):
    """High-contrast black and white with a cold tint (the broadcast section)."""
    L = luma(x)
    L = scurve(levels(L, 0.04, 0.94), contrast)
    return np.clip(L[..., None] * np.array(tint, np.float32), 0, 1)


@functools.lru_cache(None)
def _grain_bank(n=12, seed=7):
    rng = np.random.default_rng(seed)
    bank = []
    for _ in range(n):
        g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.6)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        bank.append(g / g.std())
    return bank


def grain(x, f, amount=0.035):
    """Film grain, strongest in the mid-tones, a new pattern every frame."""
    g = _grain_bank()[f % 12]
    L = luma(x)
    w = 4 * L * (1 - L) + 0.25
    return np.clip(x + (g * w * amount)[..., None], 0, 1)


@functools.lru_cache(None)
def _vignette(strength, roundness=1.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * roundness + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(1 + roundness)
    return (1 - strength * np.clip(r, 0, 1.5) ** 2.2)[..., None].astype(np.float32)


def vignette(x, strength=0.35):
    return x * _vignette(round(strength, 3))


def halation(x, threshold=0.78, strength=0.22, tint=(1.0, 0.45, 0.25), sigma=18):
    """Highlights bleed a warm glow (film halation / bloom), computed at quarter resolution."""
    L = luma(x)
    hi = np.clip((L - threshold) / (1 - threshold), 0, 1)
    small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / 4)
    glow = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * np.array(tint, np.float32)
    return 1 - (1 - x) * (1 - np.clip(glow * strength, 0, 1))


def aberration(x, amount):
    """Radial chromatic aberration: red scaled out, blue scaled in, by `amount` (fraction, e.g. 0.006)."""
    if amount <= 1e-4:
        return x
    out = x.copy()
    for ch, s in ((0, 1 + amount), (2, 1 - amount)):
        m = np.float32([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]])
        out[..., ch] = cv2.warpAffine(x[..., ch], m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return out


def rgb_split(x, dx):
    """A horizontal channel split (glitch)."""
    if abs(dx) < 0.5:
        return x
    out = x.copy()
    m = np.float32([[1, 0, dx], [0, 1, 0]])
    out[..., 0] = cv2.warpAffine(x[..., 0], m, (W, H), borderMode=cv2.BORDER_REFLECT101)
    m = np.float32([[1, 0, -dx], [0, 1, 0]])
    out[..., 2] = cv2.warpAffine(x[..., 2], m, (W, H), borderMode=cv2.BORDER_REFLECT101)
    return out


def glitch_blocks(x, f, strength=1.0, seed=0):
    """Horizontal slices displaced sideways, a few of them colour-shifted."""
    rng = np.random.default_rng(seed * 1000 + f)
    out = x.copy()
    for _ in range(int(6 + 10 * strength)):
        y0 = int(rng.integers(0, H - 20))
        h = int(rng.integers(6, 60))
        dx = int(rng.normal(0, 60 * strength))
        out[y0:y0 + h] = np.roll(x[y0:y0 + h], dx, axis=1)
        if rng.random() < 0.3:
            out[y0:y0 + h, :, int(rng.integers(0, 3))] *= 0.4
    return out


def flash(x, a, color=(1.0, 1.0, 1.0)):
    """A flash: screen-blend towards a colour by a (0..1)."""
    if a <= 1e-3:
        return x
    c = np.array(color, np.float32) * min(1.0, a)
    return 1 - (1 - x) * (1 - c)


def invert(x, a=1.0, tint=(1.0, 0.92, 0.92)):
    y = (1 - x) * np.array(tint, np.float32)
    return x + (y - x) * a


def bars(x, ratio):
    """Letterbox to `ratio` (e.g. 2.39); ratio <= 16/9 means none."""
    if ratio <= W / H + 1e-3:
        return x
    bh = int(round((H - W / ratio) / 2))
    x[:bh] = 0
    x[H - bh:] = 0
    return x


def shake(f, t0, amp, dur, seed=0, freq=26.0):
    """Shake offsets (dx, dy, roll) at frame f for a hit at time t0 (decaying over dur seconds)."""
    t = f / 30.0 - t0
    if t < 0 or t > dur:
        return 0.0, 0.0, 0.0
    e = (1 - t / dur) ** 2
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 3)
    return (amp * e * np.sin(freq * t * 6.28 / 6 + ph[0]) + amp * 0.5 * e * np.sin(freq * 1.7 * t + ph[1]),
            amp * 0.7 * e * np.sin(freq * 1.3 * t + ph[2]),
            amp * 0.012 * e * np.sin(freq * 0.9 * t + ph[1]))


def env_hit(t, t0, attack=0.0, decay=0.25, shape=2.0):
    """An envelope for a hit: 0 before t0, rises over attack, decays over `decay` seconds."""
    d = t - t0
    if d < -attack or d > decay:
        return 0.0
    if d < 0:
        return 1 + d / max(attack, 1e-6)
    return (1 - d / decay) ** shape
