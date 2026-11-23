"""A review board: render frames at the given times and tile them with labels.
  python3 tools/board.py OUT.jpg t1 t2 ...   (or a range: --range T0 T1 STEP)"""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render, media
out = sys.argv[1]
if sys.argv[2] == "--range":
    a, b, st = map(float, sys.argv[3:6]); ts = list(np.arange(a, b, st))
else:
    ts = [float(x) for x in sys.argv[2:]]
tiles = []
for t in ts:
    f = media.frame_of(t)
    im = (cv2.resize(render.frame(f), (480, 270), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8)
    s = render.shot_at(f)
    cv2.putText(im, f"{t:.2f} {s['id'] if s else ''}", (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1, cv2.LINE_AA)
    tiles.append(im)
cols = 4
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, cv2.cvtColor(np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(ts))
