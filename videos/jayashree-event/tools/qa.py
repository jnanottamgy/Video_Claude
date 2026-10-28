"""Checks on the rendered picture.

  python3 tools/qa.py sheet OUT.jpg [STEP]     # a frame every STEP s across the reel, labelled
  python3 tools/qa.py motion                   # per-frame change; flags frozen frames and jumps inside shots
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

VIDEO = os.path.join(edl.ROOT, "renders/video.mp4")


def frames(w=180, h=320):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", VIDEO, "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    while True:
        raw = p.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            break
        yield np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def sheet(out, step=1.0):
    pick = {int(round(k * step * edl.FPS)) for k in range(int(edl.DURATION / step) + 1)}
    ims = []
    for n, f in enumerate(frames()):
        if n in pick:
            im = f.copy()
            cv2.putText(im, f"{n / edl.FPS:.1f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
            ims.append(im)
    cols = 11
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(out, np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 88])


def motion():
    prev = None
    cuts = {int(np.ceil(s["t"] * edl.FPS - 1e-6)) for s in edl.SHOTS}
    diffs = []
    for n, f in enumerate(frames(270, 480)):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        diffs.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
    d = np.array(diffs)
    print(f"{len(d)} frames (want {edl.TOTAL})")
    for n in range(2, len(d) - 1):
        s = edl.shot_at(n / edl.FPS)
        near_cut = any(abs(n - c) <= 5 for c in cuts)
        if d[n] < 0.15 and not near_cut:
            print(f"frozen? frame {n} ({n / edl.FPS:.2f}s) shot {s['i']} {s['clip']} diff {d[n]:.3f}")
        med = np.median(d[max(0, n - 6):n + 6])
        if not near_cut and d[n] > 4 * med + 3:
            print(f"jump?   frame {n} ({n / edl.FPS:.2f}s) shot {s['i']} {s['clip']} diff {d[n]:.2f} (local {med:.2f})")


if __name__ == "__main__":
    if sys.argv[1] == "sheet":
        sheet(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
    else:
        motion()
