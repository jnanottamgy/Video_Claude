"""Contact sheet of the EDL: each shot's first, middle and last source frame, labelled.

  python3 tools/storyboard.py OUT.jpg [FIRST_SHOT LAST_SHOT]
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

PROXY = os.path.join(edl.ROOT, "renders/proxy")
TW, TH = 150, 266


def grab(clip, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", os.path.join(PROXY, f"IMG_{clip}.mp4"),
                          "-frames:v", "1", "-vf", f"scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    if len(raw) != TW * TH * 3:
        return np.zeros((TH, TW, 3), np.uint8)
    return np.frombuffer(raw, np.uint8).reshape(TH, TW, 3).copy()


def main():
    out = sys.argv[1]
    a, z = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(edl.SHOTS) - 1)
    shots = edl.SHOTS[a:z + 1]
    cols = 4                                   # shots per row, 3 frames each
    rows = (len(shots) + cols - 1) // cols
    cw = 3 * TW + 16
    sheet = np.full((rows * (TH + 34), cols * cw, 3), 24, np.uint8)
    for n, s in enumerate(shots):
        r, c = divmod(n, cols)
        x0, y0 = c * cw, r * (TH + 34)
        e = s["end"] - 1e-3
        for j, t in enumerate((s["t"], (s["t"] + e) / 2, e)):
            sheet[y0 + 30:y0 + 30 + TH, x0 + j * TW:x0 + (j + 1) * TW] = grab(s["clip"], edl.src_time(s, t))
        cv2.putText(sheet, f"{s['i']} {s['t']:.2f} {s['clip']}@{s['src']:.1f} {s['note'][:26]}", (x0 + 3, y0 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == "__main__":
    main()
