"""Contact sheets of every clip (3 frames each) so the footage can be read at a glance.
  python3 tools/overview.py  ->  renders/analysis/overview_<k>.jpg
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import media  # noqa: E402

TW = 150
names = media.clips()
tiles = []
for n in names:
    d = media.probe(n)["duration"]
    for k, u in enumerate((0.15, 0.5, 0.85)):
        im = cv2.cvtColor(media.frame(n, d * u, TW), cv2.COLOR_RGB2BGR).copy()
        label = f"{n[4:8]} {d * u:.1f}" if k == 0 else f"{d * u:.1f}"
        cv2.rectangle(im, (0, 0), (TW, 16), (0, 0, 0), -1)
        cv2.putText(im, label, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    print(n, f"{d:.1f}s", "HDR" if media.probe(n)["hdr"] else "SDR", flush=True)
per = 36                                       # 12 clips x 3 frames per sheet, 9 columns (3 clips per row)
os.makedirs(os.path.join(media.ROOT, "renders/analysis"), exist_ok=True)
for s in range(0, len(tiles), per):
    chunk = tiles[s:s + per]
    while len(chunk) % 9:
        chunk.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(chunk[i:i + 9]) for i in range(0, len(chunk), 9)]
    cv2.imwrite(os.path.join(media.ROOT, f"renders/analysis/overview_{s // per + 1}.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 84])
