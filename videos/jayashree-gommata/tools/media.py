"""The source video: frame access, its usable area, and crops.

The source is the client's YouTube copy of the Kaveri Dham programme. It carries a burned-in live ticker (rows
330-345 of 360), a date/time box (bottom right, from row 321) and a channel logo (top left). Every crop stays
inside the clean area: x 48-617, y 0-320 of a 640x360 frame. That area is kept in normalised coordinates, so a
sharper copy of the same video (1080p, renders/src/hd/*.mp4) drops in with the same crops.
"""
import glob
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
CLEAN = (48 / 640, 0.0, 617 / 640, 320 / 360)       # x0, y0, x1, y1 (fractions of the frame)


def source():
    """The sharpest copy available: renders/src/hd/*.mp4 if present, else the 360p Drive copy."""
    hd = sorted(glob.glob(os.path.join(ROOT, "renders/src/hd/*.mp4")))
    return hd[0] if hd else os.path.join(ROOT, "renders/src/drive/gommata_source.mp4")


def size(path=None):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path or source()], capture_output=True, text=True, check=True).stdout
    w, h = out.strip().split(",")
    return int(w), int(h)


class Reader:
    """Sequential frame reader for one source range (decodes once, frame-accurately)."""

    def __init__(self, t0, t1, path=None):
        self.path = path or source()
        self.w, self.h = size(self.path)
        self.f0 = int(round(t0 * FPS))
        n = int(round(t1 * FPS)) - self.f0 + 2
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, self.f0 / FPS - 2.0):.3f}", "-i", self.path,
               "-ss", f"{min(2.0, self.f0 / FPS):.3f}", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        k = len(raw) // (self.w * self.h * 3)
        self.frames = np.frombuffer(raw[:k * self.w * self.h * 3], np.uint8).reshape(k, self.h, self.w, 3)

    def at(self, t):
        """The frame at source time t (nearest frame; clamped to the decoded range)."""
        i = int(round(t * FPS)) - self.f0
        return self.frames[min(max(i, 0), len(self.frames) - 1)]


def crop_box(w, h, cx, cy, cw, aspect):
    """A crop of width cw (fraction of the clean width) centred at (cx, cy) (fractions of the clean area), of the
    given aspect, clamped inside the clean area. -> x0, y0, x1, y1 in pixels (float)."""
    X0, Y0, X1, Y1 = CLEAN[0] * w, CLEAN[1] * h, CLEAN[2] * w, CLEAN[3] * h
    pw = min(cw * (X1 - X0), X1 - X0, (Y1 - Y0) * aspect)
    ph = pw / aspect
    x = X0 + cx * (X1 - X0) - pw / 2
    y = Y0 + cy * (Y1 - Y0) - ph / 2
    x = min(max(x, X0), X1 - pw)
    y = min(max(y, Y0), Y1 - ph)
    return x, y, x + pw, y + ph


def warp(img, box, out_w, out_h, interp=cv2.INTER_LANCZOS4):
    """Resample the box (x0, y0, x1, y1, sub-pixel) of img to out_w x out_h."""
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0) / out_w, (y1 - y0) / out_h
    m = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(img, m, (out_w, out_h), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


def sharpen(x, amount=0.55, sigma=1.4):
    """An unsharp mask for the upscaled footage (float RGB)."""
    return np.clip(x + (x - cv2.GaussianBlur(x, (0, 0), sigma)) * amount, 0, 1)
