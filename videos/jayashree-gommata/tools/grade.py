"""The grade, v2: contrast and clarity for a washed-out, overexposed 360p stream.

v1 ran her event reel's gold LUT over this footage, and that lifted it further: the window's darkest parts sat at
12-46% and its midtones at 61-79%. The source itself is overexposed: 68-76% of every statue frame is pure
white, and the black stone reads mid-grey. Per shot, measured once from frames across the shot, so it can't
flicker:
  1. levels: the shot's 0.7th luma percentile becomes black and its 99.7th white;
  2. a gamma that brings the median to ~0.42, then an S-curve, and a soft shoulder that keeps blown skies at a
     clean warm white (~0.93) instead of v1's cream;
  3. colour:
       - a touch of warmth;
       - vibrance: muted colours up most (saris, the flag, marigolds), skin kept natural;
       - blue skies kept blue;
  4. clarity, all at source resolution before the enlargement:
       - a light edge-preserving denoise (the stream's blocking would otherwise sharpen up);
       - local contrast (CLAHE on L, low clip);
     then, after the enlargement, a two-radius unsharp mask.
  python3 tools/grade.py OUT.jpg   # before/after sheet for the shots
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import media  # noqa: E402

_clahe = cv2.createCLAHE(clipLimit=1.25, tileGridSize=(8, 8))
TARGET_MEDIAN = 0.44                # of the subject: the pixels that aren't blown sky or white cloth
GAMMA_RANGE = (0.9, 1.45)


def luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


def measure(frames):
    """Per-shot levels and gamma from a few uint8 frames (cropped to the shot's area)."""
    L = np.concatenate([luma(f.astype(np.float32) / 255).ravel() for f in frames])
    lo, hi = np.percentile(L, 0.7), np.percentile(L, 99.7)
    hi = max(hi, lo + 0.25)
    Ln = (L - lo) / (hi - lo)
    sub = Ln[Ln < 0.9]
    if len(sub) < 0.08 * len(Ln):
        sub = Ln
    m = float(np.clip(np.median(sub), 0.05, 0.95))
    gamma = float(np.clip(np.log(TARGET_MEDIAN) / np.log(m), *GAMMA_RANGE))
    return dict(lo=float(lo), hi=float(hi), gamma=gamma, subject_median=m)


def _curve(x):
    """S-curve about 0.42 with a soft shoulder to 0.93 (whites stay a clean warm white, not paper)."""
    xs = np.array([0.0, 0.05, 0.15, 0.30, 0.42, 0.60, 0.78, 0.90, 1.0, 1.2])
    ys = np.array([0.0, 0.030, 0.105, 0.255, 0.400, 0.610, 0.790, 0.880, 0.925, 0.94])
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(xs, ys)(np.clip(x, 0, 1.2)).astype(np.float32)


_LUT = None


def curve_lut():
    global _LUT
    if _LUT is None:
        _LUT = _curve(np.linspace(0, 1.2, 4097))
    return _LUT


def tone(img, p):
    """uint8 RGB -> float RGB graded (levels, gamma, curve, warmth, vibrance)."""
    x = img.astype(np.float32) / 255
    x = np.clip((x - p["lo"]) / (p["hi"] - p["lo"]), 0, 1.2)
    x = np.power(np.maximum(x, 0), p["gamma"])
    lut = curve_lut()
    x = lut[np.clip((x / 1.2 * 4096).astype(np.int32), 0, 4096)]
    x = x * np.array([1.02, 1.0, 0.965], np.float32)                     # a touch of warmth
    # vibrance: lift muted colours most; protect skin a little; never push past natural
    mx, mn = x.max(2, keepdims=True), x.min(2, keepdims=True)
    s = (mx - mn) / np.maximum(mx, 1e-4)
    L = luma(x)[..., None]
    r, g, b = x[..., 0:1], x[..., 1:2], x[..., 2:3]
    hue = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    skin = np.exp(-0.5 * ((((hue - 25) + 180) % 360 - 180) / 12) ** 2) * np.exp(-0.5 * ((s - 0.35) / 0.18) ** 2)
    sky = np.exp(-0.5 * ((((hue - 215) + 180) % 360 - 180) / 22) ** 2)
    shade = np.clip((L - 0.12) / 0.33, 0, 1)                               # no boost in the shadows
    k = 1 + 0.38 * (1 - s) ** 1.5 * (1 - 0.6 * skin) * (1 - 0.65 * sky) * shade
    # the black stone: muted blue-greys go charcoal at any brightness (the stream's blue cast, not the granite);
    # real blue sky and the flag's blue are saturated and keep their colour
    cool = np.exp(-0.5 * ((((hue - 222) + 180) % 360 - 180) / 34) ** 2) * np.clip((0.40 - s) / 0.25, 0, 1)
    k = k * (1 - 0.8 * cool)
    x = L + (x - L) * k
    x = x + np.array([0.016, 0.006, -0.008], np.float32) * (1 - L) ** 2      # warm shadows: charcoal, not navy
    return np.clip(x, 0, 1)


def clarity_src(img_u8):
    """At source resolution: a light edge-preserving denoise, then local contrast on L (CLAHE)."""
    d = cv2.fastNlMeansDenoisingColored(img_u8, None, 3, 3, 5, 13)
    lab = cv2.cvtColor(d, cv2.COLOR_RGB2LAB)
    lab[..., 0] = _clahe.apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def sharpen_out(x):
    """After the enlargement: fine detail (r ~1 px) and a broader edge lift (r ~3 px)."""
    a = x + (x - cv2.GaussianBlur(x, (0, 0), 1.0)) * 0.60
    a = a + (a - cv2.GaussianBlur(a, (0, 0), 3.2)) * 0.15
    return np.clip(a, 0, 1)


if __name__ == "__main__":
    import edl
    import layout as LY
    import look
    out = sys.argv[1]
    table = look.lut("gold")
    rows = []
    for name in ("face", "stage", "pour", "legs", "kalasha", "umbrella"):
        sh = next(s for s in edl.SHOTS if s["name"] == name)
        r = media.Reader(sh["src"], sh["src"] + (sh["t1"] - sh["t0"]))
        box = media.crop_box(r.w, r.h, sh["cx"], sh["cy"], sh["cw"], LY.ASPECT)
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        samples = [r.at(sh["src"] + (sh["t1"] - sh["t0"]) * q)[y0:y1, x0:x1] for q in (0.1, 0.5, 0.9)]
        p = measure(samples)
        src = r.at(sh["src"] + (sh["t1"] - sh["t0"]) / 2)
        old = LY.window(look.apply(src, table), box)
        new_src = clarity_src((tone(src, p) * 255 + 0.5).astype(np.uint8))
        new = sharpen_out(media.warp(new_src, box, LY.WIN_W, LY.WIN_H).astype(np.float32) / 255)
        rows.append(np.hstack([old, new]))
        print(name, {k: round(v, 3) for k, v in p.items()})
    sheet = np.vstack([cv2.resize(rw, (rw.shape[1] // 2, rw.shape[0] // 2), interpolation=cv2.INTER_AREA) for rw in rows])
    cv2.imwrite(out, cv2.cvtColor((sheet * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(out)
