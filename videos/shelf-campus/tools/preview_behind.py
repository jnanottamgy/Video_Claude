"""Check a "behind" overlay frame in context: footage, then the overlay, then the person cut back on top.

  python3 tools/preview_behind.py <overlay.png> <output_time_s> <out.jpg> [--half] [--wall dark]
Uses the person matte of the source frame shown at that output time (renders/mattes/f_<n>.png).
--wall dark previews the founders-section look, where the compositor re-lights the wall to deep navy.
For "front" layers use tools/preview_over.py with a renders/ref/out_<t>.png frame.
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

ov_path, t, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
ov = cv2.imread(ov_path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
n = edl.src_frame(int(round(t * edl.FPS)))
if n is None:
    sys.exit(f"output time {t} is a full-frame graphic, not footage")
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(n + 0.25) / edl.FPS:.4f}", "-i", os.path.join(edl.ROOT, edl.SRC),
                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
bg = np.frombuffer(raw, np.uint8).reshape(edl.H, edl.W, 3).astype(np.float32) / 255
mp = os.path.join(edl.ROOT, f"renders/mattes/f_{n:05d}.png")
m = cv2.imread(mp, cv2.IMREAD_GRAYSCALE).astype(np.float32)[..., None] / 255 if os.path.exists(mp) else np.zeros((edl.H, edl.W, 1), np.float32)
person = bg
if "--wall" in sys.argv and sys.argv[sys.argv.index("--wall") + 1] == "dark":
    yy = np.linspace(0, 1, edl.H, dtype=np.float32)[:, None, None]
    navy = np.array([0.10, 0.055, 0.025], np.float32) * (1.15 - 0.5 * yy)      # BGR: deep navy, lighter at the top
    bg = bg * 0.22 + navy
a = ov[:, :, 3:4]
comp = ov[:, :, :3] * a + bg * (1 - a)
comp = comp * (1 - m) + person * m
if "--half" in sys.argv:
    comp = cv2.resize(comp, (540, 960), interpolation=cv2.INTER_AREA)
cv2.imwrite(out, (comp * 255).clip(0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ok", out, "source frame", n)
