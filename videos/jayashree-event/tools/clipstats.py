"""Per-frame stats of every working copy (renders/proxy): sharpness, camera motion, brightness.
  python3 tools/clipstats.py  ->  renders/analysis/clipstats.json  {clip: {n, sharp[], motion[], luma[]}}
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PX = os.path.join(ROOT, "renders/proxy")
W, H = 270, 480


def stats(name):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(PX, name), "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    sharp, motion, luma, prev = [], [], [], None
    win = cv2.createHanningWindow((W, H), cv2.CV_32F)
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        g = np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32)
        sharp.append(float(cv2.Laplacian(g, cv2.CV_32F).var()))
        luma.append(float(g.mean()))
        if prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g, win)
            motion.append(float(np.hypot(dx, dy)))
        else:
            motion.append(0.0)
        prev = g
    return name, dict(n=len(sharp), sharp=sharp, motion=motion, luma=luma)


if __name__ == "__main__":
    names = sorted(f for f in os.listdir(PX) if f.endswith(".mp4"))
    with ProcessPoolExecutor(4) as ex:
        out = dict(ex.map(stats, names))
    json.dump(out, open(os.path.join(ROOT, "renders/analysis/clipstats.json"), "w"))
    for k, v in out.items():
        m = np.array(v["motion"]); s = np.array(v["sharp"])
        print(f"{k:14s} {v['n']:4d}f  motion med {np.median(m):5.2f} p90 {np.percentile(m, 90):5.2f}  sharp med {np.median(s):7.1f}  luma {np.mean(v['luma']):5.1f}")
