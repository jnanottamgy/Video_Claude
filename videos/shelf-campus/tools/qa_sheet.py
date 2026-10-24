"""QA contact sheets from a rendered reel: frames across windows around chosen moments.

  python3 tools/qa_sheet.py renders/rough_cut.mp4 out.jpg 0.25,3.5,13.2  [--span 1.2] [--n 6]
Each row is one moment: --n frames evenly over [t - span/2, t + span/2], labelled with their time.
"""
import argparse
import subprocess

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("out")
ap.add_argument("times")
ap.add_argument("--span", type=float, default=1.2)
ap.add_argument("--n", type=int, default=6)
ap.add_argument("--w", type=int, default=200)
a = ap.parse_args()
rows = []
for t in (float(x) for x in a.times.split(",")):
    tiles = []
    for k in range(a.n):
        tt = max(0.0, t - a.span / 2 + a.span * k / max(1, a.n - 1))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tt:.3f}", "-i", a.video, "-frames:v", "1", "-vf",
                              f"scale={a.w}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        h = len(raw) // (a.w * 3)
        im = np.frombuffer(raw, np.uint8).reshape(h, a.w, 3).copy() if h else np.zeros((int(a.w * 16 / 9), a.w, 3), np.uint8)
        cv2.putText(im, f"{tt:.2f}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    rows.append(np.hstack(tiles))
cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
