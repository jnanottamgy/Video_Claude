"""QA of the finished picture: every cut of the EDL, one frame before / on / after, with the mix's
waveform under each row (so a cut inside a word, a late slam or a dead gap shows up at a glance).

  python3 tools/qa_cuts.py [renders/video.mp4] [out.jpg]
"""
import os
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

os.chdir(edl.ROOT)
video = sys.argv[1] if len(sys.argv) > 1 else "renders/video.mp4"
out = sys.argv[2] if len(sys.argv) > 2 else "renders/verify/qa_cuts.jpg"
mix, sr = sf.read("renders/audio/mix.wav")
mono = mix.mean(axis=1)
TW = 180


def grab(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1", "-vf", f"scale={TW}:-2",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    h = len(raw) // (TW * 3)
    return np.frombuffer(raw, np.uint8).reshape(h, TW, 3).copy() if h else np.zeros((320, TW, 3), np.uint8)


rows = []
cuts = [s["out0"] for s in edl.SEGMENTS[1:]]
for c in cuts:
    tiles = []
    for d in (-2, -1, 0, 1):
        t = c + d / edl.FPS + 0.001
        im = grab(t)
        cv2.putText(im, f"{t:.2f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    row = np.hstack(tiles)
    wav = np.zeros((60, row.shape[1], 3), np.uint8)
    a, b = int((c - 0.6) * sr), int((c + 0.6) * sr)
    seg = mono[max(0, a):b]
    if len(seg):
        k = np.array_split(np.abs(seg), row.shape[1])
        for x, chunk in enumerate(k):
            v = int(min(1.0, chunk.max() if len(chunk) else 0) * 28)
            cv2.line(wav, (x, 30 - v), (x, 30 + v), (90, 200, 255), 1)
        cx = int(row.shape[1] * 0.5)
        cv2.line(wav, (cx, 0), (cx, 59), (0, 0, 255), 1)
    rows.append(np.vstack([row, wav]))
cols = 3
while len(rows) % cols:
    rows.append(np.zeros_like(rows[0]))
grid = np.vstack([np.hstack(rows[i:i + cols]) for i in range(0, len(rows), cols)])
os.makedirs(os.path.dirname(out), exist_ok=True)
cv2.imwrite(out, grid, [cv2.IMWRITE_JPEG_QUALITY, 82])
print(out, grid.shape)
