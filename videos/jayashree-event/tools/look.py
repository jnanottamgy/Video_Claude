"""The look: a warm, golden, filmic grade baked into a 256^3 LUT, plus the light effects done per frame.

The colour pipeline (white balance -> filmic curve -> split tone -> hue-selective saturation) is applied
once to every 8-bit RGB triple and stored as a LUT, so a frame grades with a single gather. Bloom,
halation, vignette and grain are done per frame in float.
  python3 tools/look.py OUT.jpg CLIP@T ...   # before/after sheet
"""
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "renders/cache")

LOOKS = {
    # warmth: blue-channel cut and red lift; matte: lifted black; contrast: midtone slope; sat: global
    "gold": dict(wb=(1.045, 0.995, 0.91), matte=0.012, sat=0.97, warm_sat=1.28, yellow_sat=0.94, red_sat=1.25,
                 blue_sat=0.50, skin_sat=1.02, shadow_tint=(0.018, 0.005, -0.004), high_tint=(1.0, 0.94, 0.84)),
    # the breath: softer and warmer still, a candle-lit feel
    "candle": dict(wb=(1.06, 1.0, 0.86), matte=0.020, sat=0.95, warm_sat=1.28, yellow_sat=0.92, red_sat=1.2,
                   blue_sat=0.42, skin_sat=1.0, shadow_tint=(0.026, 0.008, -0.010), high_tint=(1.0, 0.94, 0.80)),
}


def _curve(x):
    """Filmic tone curve: a slightly lifted toe, midtone contrast, a long soft shoulder."""
    xs = np.array([0.0, 0.06, 0.15, 0.30, 0.50, 0.70, 0.85, 0.95, 1.0])
    ys = np.array([0.0, 0.034, 0.104, 0.254, 0.476, 0.702, 0.846, 0.931, 0.962])
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(xs, ys)(np.clip(x, 0, 1))


def _hue_gain(h, s, p):
    """Saturation gain by hue (degrees): saffron/marigold/maroon up, cyan/blue down, skin protected."""
    g = np.ones_like(h)
    warm = np.exp(-0.5 * ((((h - 24) + 180) % 360 - 180) / 16) ** 2)          # saffron, marigold orange
    yellow = np.exp(-0.5 * ((((h - 54) + 180) % 360 - 180) / 12) ** 2)        # the yellow sarees: held back
    red = np.exp(-0.5 * ((((h - 355) + 180) % 360 - 180) / 16) ** 2)          # maroon / crimson / pink
    blue = np.exp(-0.5 * ((((h - 210) + 180) % 360 - 180) / 38) ** 2)         # cyan .. blue (LED walls, chairs)
    skin = np.exp(-0.5 * ((((h - 24) + 180) % 360 - 180) / 10) ** 2) * np.exp(-0.5 * ((s - 0.35) / 0.15) ** 2)
    g = g + (p["warm_sat"] - 1) * warm + (p["yellow_sat"] - 1) * yellow + (p["red_sat"] - 1) * red \
        + (p["blue_sat"] - 1) * blue
    g = g * (1 - skin) + p["skin_sat"] * skin
    return g * p["sat"]


def _pipeline(rgb, p):
    """rgb float (N,3) in [0,1] -> graded (N,3)."""
    x = rgb * np.array(p["wb"], np.float32)
    x = _curve(x)
    x = p["matte"] + (1 - p["matte"]) * x
    L = (0.2126 * x[:, 0] + 0.7152 * x[:, 1] + 0.0722 * x[:, 2])[:, None]
    x = x + np.array(p["shadow_tint"]) * (1 - L) ** 2.5
    x = x * (1 + (np.array(p["high_tint"]) - 1) * L ** 2)
    # hue-selective saturation about the luma
    mx, mn = x.max(1), x.min(1)
    s = (mx - mn) / np.maximum(mx, 1e-6)
    r, g, b = x[:, 0], x[:, 1], x[:, 2]
    h = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    L = (0.2126 * r + 0.7152 * g + 0.0722 * b)[:, None]
    x = L + (x - L) * _hue_gain(h, s, p)[:, None]
    return np.clip(x, 0, 1)


def lut(name):
    """The 256^3 LUT for a look, uint8, cached on disk."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"lut_{name}.npy")
    key = repr(sorted(LOOKS[name].items()))
    if os.path.exists(path) and open(path + ".key").read() == key:
        return np.load(path, mmap_mode="r")
    out = np.empty((256, 256, 256, 3), np.uint8)
    v = np.arange(256, dtype=np.float32) / 255
    g, b = np.meshgrid(v, v, indexing="ij")
    gb = np.stack([g.ravel(), b.ravel()], 1)
    for r in range(256):
        rgb = np.concatenate([np.full((gb.shape[0], 1), v[r], np.float32), gb], 1)
        out[r] = (_pipeline(rgb, LOOKS[name]) * 255 + 0.5).astype(np.uint8).reshape(256, 256, 3)
    np.save(path, out)
    open(path + ".key", "w").write(key)
    return np.load(path, mmap_mode="r")


def apply(img, table):
    """Grade a uint8 RGB frame through a LUT."""
    i = (img[..., 0].astype(np.int32) << 16) | (img[..., 1].astype(np.int32) << 8) | img[..., 2]
    return np.asarray(table).reshape(-1, 3)[i]


def bloom(x, amount=0.30, thresh=0.86, tint=(1.0, 0.80, 0.52)):
    """Glow from the highlights (lamps, chandeliers, windows): two blur radii, warm tinted. x float RGB."""
    h, w = x.shape[:2]
    small = cv2.resize(x, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    L = small.max(2, keepdims=True)
    hi = small * np.clip((L - thresh) / (1 - thresh), 0, 1) ** 1.5
    g1 = cv2.GaussianBlur(hi, (0, 0), 6)
    g2 = cv2.GaussianBlur(hi, (0, 0), 22)
    glow = (0.55 * g1 + 0.45 * g2) * np.array(tint, np.float32)
    glow = cv2.resize(glow, (w, h), interpolation=cv2.INTER_LINEAR)
    return 1 - (1 - x) * (1 - np.clip(glow * amount * 2.2, 0, 1))          # screen


def halation(x, amount=0.18):
    """Film halation: a red-orange fringe bleeding from bright edges."""
    h, w = x.shape[:2]
    small = cv2.resize(x, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    L = small.mean(2)
    hi = np.clip((L - 0.8) / 0.2, 0, 1)
    r = cv2.GaussianBlur(hi, (0, 0), 3.5) - cv2.GaussianBlur(hi, (0, 0), 1.0) * 0.6
    r = cv2.resize(np.clip(r, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
    return np.clip(x + r * amount * np.array([1.0, 0.35, 0.10], np.float32), 0, 1)


_vig = {}


def vignette(x, strength=0.30, tint=(0.10, 0.05, 0.02)):
    """Darken the corners towards a warm brown."""
    h, w = x.shape[:2]
    if (h, w) not in _vig:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.8 + ((yy - h / 2) / (h / 2)) ** 2)
        _vig[(h, w)] = np.clip((d - 0.55) / 0.85, 0, 1) ** 1.6
    m = _vig[(h, w)][..., None] * strength
    return x * (1 - m) + np.array(tint, np.float32) * m


def grain(x, seed, amount=0.035):
    """Luma-weighted film grain, ~1.5 px, different every frame."""
    h, w = x.shape[:2]
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((h // 2, w // 2)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
    L = x.mean(2, keepdims=True)
    wgt = 0.5 + 1.6 * L * (1 - L)                                       # strongest in the mids
    return np.clip(x + n[..., None] * amount * wgt, 0, 1)


def clarity(x, amount=0.22):
    """Local contrast: lift detail against a wide blur (done at quarter size)."""
    h, w = x.shape[:2]
    base = cv2.resize(cv2.GaussianBlur(cv2.resize(x, (w // 4, h // 4), interpolation=cv2.INTER_AREA), (0, 0), 5),
                      (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(x + (x - base) * amount, 0, 1)


def finish(x, seed, bloom_amt=0.30, hal=0.16, vig=0.36, grain_amt=0.032, clar=0.22):
    x = clarity(x, clar)
    x = bloom(x, bloom_amt)
    x = halation(x, hal)
    x = vignette(x, vig)
    return grain(x, seed, grain_amt)


if __name__ == "__main__":
    import subprocess
    import sys
    out = sys.argv[1]
    look = os.environ.get("LOOK", "gold")
    table = lut(look)
    rows = []
    for spec in sys.argv[2:]:
        c, t = spec.split("@")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", t, "-i", os.path.join(ROOT, f"renders/proxy/IMG_{c}.mp4"),
                              "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)
        b = finish(apply(a, table).astype(np.float32) / 255, 1)
        b = (b * 255 + 0.5).astype(np.uint8)
        tw = int(os.environ.get("TW", 360))
        pair = np.hstack([cv2.resize(a, (tw, tw * 16 // 9), interpolation=cv2.INTER_AREA),
                          cv2.resize(b, (tw, tw * 16 // 9), interpolation=cv2.INTER_AREA)])
        rows.append(pair)
    cols = int(os.environ.get("COLS", 3))
    while len(rows) % cols:
        rows.append(np.zeros_like(rows[0]))
    grid = np.vstack([np.hstack(rows[i:i + cols]) for i in range(0, len(rows), cols)])
    cv2.imwrite(out, cv2.cvtColor(grid, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
