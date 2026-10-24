"""The two-founders poster (segment B3): both founders cut out of their own shots, side by side.

Layout shared by the compositor and the builders' reference: renders/ref/split_people.png (RGBA).
  python3 tools/split_people.py
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

# (source frame, scale, dx, dy): J on the left, K on the right; K drawn first (J overlaps him)
LAYOUT = {"K": (579, 0.84, 174, 307), "J": (492, 0.84, -340, 307)}      # bottoms on the frame edge, K's right edge off-frame


def src_rgb(n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(n + 0.25) / edl.FPS:.4f}", "-i", os.path.join(edl.ROOT, edl.SRC),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(edl.H, edl.W, 3).astype(np.float32) / 255


def cutout(who, rgb=None, matte=None):
    """RGBA float (H, W, 4) of one founder placed on the poster canvas."""
    n, s, dx, dy = LAYOUT[who]
    rgb = src_rgb(n) if rgb is None else rgb
    m = cv2.imread(os.path.join(edl.ROOT, f"renders/mattes/f_{n:05d}.png"), 0).astype(np.float32) / 255 if matte is None else matte
    if who == "J":       # his matte runs into the chair at his shot's right edge: feather it out instead of a hard line
        m = m * np.clip((1065 - np.arange(edl.W, dtype=np.float32)) / 200, 0, 1)[None, :]
    M = np.float32([[s, 0, dx], [0, s, dy]])
    c = cv2.warpAffine(rgb, M, (edl.W, edl.H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))
    a = cv2.warpAffine(m, M, (edl.W, edl.H), flags=cv2.INTER_LINEAR, borderValue=0)
    return np.dstack([c, a])


def people():
    out = np.zeros((edl.H, edl.W, 4), np.float32)
    for who in ("K", "J"):
        l = cutout(who)
        a = l[..., 3:4]
        out[..., :3] = l[..., :3] * a + out[..., :3] * (1 - a)
        out[..., 3:4] = a + out[..., 3:4] * (1 - a)
    return out


if __name__ == "__main__":
    p = people()
    os.makedirs(os.path.join(edl.ROOT, "renders/ref"), exist_ok=True)
    rgba = (np.dstack([p[..., 2::-1], p[..., 3:4]]) * 255).clip(0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(edl.ROOT, "renders/ref/split_people.png"), rgba)
    bg = np.zeros_like(p[..., :3]); bg[:] = (0.03, 0.05, 0.10)
    prev = p[..., :3] * p[..., 3:4] + bg * (1 - p[..., 3:4])
    cv2.imwrite(os.path.join(edl.ROOT, "renders/ref/split_preview.jpg"),
                cv2.cvtColor((cv2.resize(prev, (540, 960)) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    print("renders/ref/split_people.png")
