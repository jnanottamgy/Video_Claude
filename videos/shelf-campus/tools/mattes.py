"""Person mattes for every talking-head frame: words slam in BEHIND the founders, freeze frames cut them out.

u2net_human_seg (rembg) predicts a 320 px mask; a guided filter against the full-res frame snaps its
edges to real edges (hair, glasses, shoulders), and a 3-frame temporal median removes single-frame
flicker. Mattes are 8-bit PNGs named by SOURCE frame: renders/mattes/f_<n>.png

  python3 tools/mattes.py            # every range below (skips frames already done)
"""
import os
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image

os.environ.setdefault("U2NET_HOME", "/root/vfx-models")
from rembg import new_session, remove  # noqa: E402

W, H, FPS = 1080, 1920, 30
SRC = "renders/src/founders_reel_original.mp4"
OUT = "renders/mattes"
# source frames with a person in shot: everything except the floor B-roll (1125-1544) and the
# "close up, confident delivery" blooper (1965-2084), which are cut
RANGES = [(0, 1124), (1545, 1964), (2085, 2164)]


def frames(a, b):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, a - 0.01) / FPS:.6f}", "-i", SRC,
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
    os.makedirs(OUT, exist_ok=True)
    sess = new_session("u2net_human_seg")
    t0 = time.time()
    for a, b in RANGES:
        todo = [n for n in range(a, b + 1) if not os.path.exists(f"{OUT}/f_{n:05d}.png")]
        if not todo:
            continue
        a, b = min(todo), max(todo)
        raw = {}
        for n, rgb in frames(max(0, a - 1), b + 1):
            m = np.asarray(remove(Image.fromarray(rgb), session=sess, only_mask=True), np.float32) / 255
            g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            raw[n] = np.clip(guided(g, m), 0, 1)
            k = n - 1
            if a <= k <= b and k - 1 in raw:
                st = [raw[j] for j in (k - 1, k, k + 1)]
                cv2.imwrite(f"{OUT}/f_{k:05d}.png", (np.median(np.stack(st), axis=0) * 255 + 0.5).astype(np.uint8))
                raw.pop(k - 1, None)
            if n % 50 == 0:
                print(f"frame {n}  {time.time() - t0:.0f}s", flush=True)
        for k in (a, b):                       # range ends: no 3-frame window
            if not os.path.exists(f"{OUT}/f_{k:05d}.png") and k in raw:
                cv2.imwrite(f"{OUT}/f_{k:05d}.png", (raw[k] * 255 + 0.5).astype(np.uint8))
        print(f"range {a}-{b} done", flush=True)


if __name__ == "__main__":
    main()
