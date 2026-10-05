"""Person mattes for the text-behind-subject shots and the freeze-frame cut-outs.

u2net_human_seg (rembg) predicts a 320 px mask; a guided filter against the full-res frame
snaps its edges to real edges (hair, shoulders), and a 3-frame temporal median removes
single-frame flicker. Mattes are 8-bit PNGs named by SOURCE frame: renders/mattes/f_<n>.png

  U2NET_HOME=/root/vfx-models /root/vfx-venv/bin/python tools/mattes.py
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

W, H = 1080, 1920
OUT = "renders/mattes"
# Source frame ranges [a, b] whose person is composited over a "behind" layer (see slots/titles/SPEC.md)
RANGES = {
    "shelf_behind": (1925, 1968),
    "jnanottam_behind": (2147, 2239),
    "kartik_behind": (2288, 2376),
    "simple_behind": (2844, 2881),
    "shelf2_behind": (2919, 2953),
}


def frames(a, b):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, a - 0.01) / edl.FPS:.6f}", "-i", "renders/source.mp4",
                          "-frames:v", str(b - a + 1), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    for n in range(a, b + 1):
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            return
        yield n, np.frombuffer(buf, np.uint8).reshape(H, W, 3)


def guided(I, p, r=8, eps=1e-3):
    """He et al. guided filter (grey guide), box filters at full res."""
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def main():
    """All ranges, or only the named ones; --missing skips frames that already have a matte."""
    os.makedirs(OUT, exist_ok=True)
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(RANGES)
    missing = "--missing" in sys.argv
    sess = new_session("u2net_human_seg")
    for name in names:
        a, b = RANGES[name]
        if missing:
            todo = [n for n in range(a, b + 1) if not os.path.exists(f"{OUT}/f_{n:05d}.png")]
            if not todo:
                continue
            a, b = min(todo), max(todo)
        raw = {}
        for n, rgb in frames(max(0, a - 1), b + 1):
            m = np.asarray(remove(Image.fromarray(rgb), session=sess, only_mask=True), np.float32) / 255
            g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            raw[n] = (np.clip(guided(g, m), 0, 1), g)
        for n in range(a, b + 1):
            stack = [raw[k][0] for k in (n - 1, n, n + 1) if k in raw]
            m = np.median(np.stack(stack), axis=0) if len(stack) == 3 else raw[n][0]
            cv2.imwrite(f"{OUT}/f_{n:05d}.png", (m * 255 + 0.5).astype(np.uint8))
        print(f"{name}: frames {a}-{b} done", flush=True)


if __name__ == "__main__":
    main()
