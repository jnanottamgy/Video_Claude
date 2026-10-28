"""Filmstrips of chosen clips: a frame every `step` s, labelled clip / time, one row per clip.
  python3 tools/filmstrip.py OUT.jpg STEP CLIP [CLIP ...]     (clip ids like 3407)
"""
import os
import subprocess
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, step, ids = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
TW, TH, MAXN = 112, 199, 16
rows = []
for cid in ids:
    p = os.path.join(ROOT, f"renders/proxy/IMG_{cid}.mp4")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={1 / step},scale={TW}:{TH}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, TH, TW, 3)[:MAXN].copy()
    tiles = []
    for k, im in enumerate(fr):
        cv2.rectangle(im, (0, 0), (TW, 13), (0, 0, 0), -1)
        cv2.putText(im, (f"{cid} " if k == 0 else "") + f"{k * step:.1f}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 255), 1)
        tiles.append(im)
    while len(tiles) < MAXN:
        tiles.append(np.zeros((TH, TW, 3), np.uint8))
    rows.append(np.hstack(tiles))
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(out)
