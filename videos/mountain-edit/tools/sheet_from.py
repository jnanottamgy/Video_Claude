"""A contact sheet of a rendered video between two times, read back from the file (not re-rendered).
  python3 tools/sheet_from.py VIDEO OUT.jpg T0 T1 FPS [COLS]"""
import subprocess
import sys

import cv2
import numpy as np

vid, out, t0, t1, fps = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 6
w, h = 384, 216
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", vid, "-vf",
                      f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).copy()
tiles = []
for k, im in enumerate(fr):
    cv2.putText(im, f"{t0 + k / fps:.2f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    tiles.append(im)
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(fr))
