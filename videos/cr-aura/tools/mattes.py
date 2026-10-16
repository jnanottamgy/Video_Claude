"""Person mattes for the CR clips: rembg u2net_human_seg on the source frames, edges snapped with a
guided filter, then a 3-frame temporal median against flicker.

  /root/vfx-venv/bin/python tools/mattes.py [a-b]        (default: every CR frame, 395-925)

Writes 8-bit 576x1024 PNGs, renders/mattes/raw_<f>.png. The compositor upsamples them against the
enhanced 1080x1920 frame and keeps only the CR's blob (see composite.py: cr_matte()).
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

SRC = "renders/src/source.mp4"
OUT = "renders/mattes"
W, H, FPS = 576, 1024, 30


def frames(a, b):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, a - 0.01) / FPS:.6f}", "-i", SRC,
                          "-frames:v", str(b - a + 1), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    for n in range(a, b + 1):
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            return
        yield n, np.frombuffer(buf, np.uint8).reshape(H, W, 3)


def guided(I, p, r=6, eps=1e-3):
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def main():
    a, b = (int(v) for v in (sys.argv[1] if len(sys.argv) > 1 else "395-925").split("-"))
    os.makedirs(OUT, exist_ok=True)
    os.environ.setdefault("U2NET_HOME", "/root/vfx-models")
    sess = new_session("u2net_human_seg")
    raw = {}
    for n, rgb in frames(max(0, a - 1), b + 1):
        m = np.asarray(remove(Image.fromarray(rgb), session=sess, only_mask=True), np.float32) / 255
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        raw[n] = np.clip(guided(g, m), 0, 1)
        if n % 50 == 0:
            print("matte", n, flush=True)
    for n in range(a, b + 1):
        stack = [raw[k] for k in (n - 1, n, n + 1) if k in raw]
        m = np.median(np.stack(stack), axis=0) if len(stack) == 3 else raw[n]
        cv2.imwrite(f"{OUT}/raw_{n:05d}.png", (m * 255 + 0.5).astype(np.uint8))
    print("done", a, b)


if __name__ == "__main__":
    main()
