"""Frames of a clip at chosen source times, with a grid labelled in display pixels, for setting views.
  python3 tools/grab.py OUT.jpg CLIP t1 t2 ... [--h 420]"""
import sys

import cv2
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import media  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
th = 420
if "--h" in sys.argv:
    th = int(sys.argv[sys.argv.index("--h") + 1])
    args.remove(str(th))
out, clip, times = args[0], args[1], [float(x) for x in args[2:]]
i = media.info(clip)
tiles = []
for t in times:
    fr, _ = media.decode(clip, t, t + 1.5 / i["fps"], scale=th / i["h"])
    im = cv2.cvtColor(fr[0], cv2.COLOR_RGB2BGR).copy()
    k = im.shape[0] / i["h"]
    step = 200 if max(i["w"], i["h"]) <= 2000 else 400
    for x in range(0, i["w"], step):
        cv2.line(im, (int(x * k), 0), (int(x * k), im.shape[0]), (0, 255, 255), 1)
        cv2.putText(im, str(x), (int(x * k) + 2, im.shape[0] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 255), 1)
    for y in range(0, i["h"], step):
        cv2.line(im, (0, int(y * k)), (im.shape[1], int(y * k)), (0, 255, 255), 1)
        cv2.putText(im, str(y), (2, int(y * k) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 255), 1)
    cv2.putText(im, f"{t:.2f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    tiles.append(im)
hh = max(t.shape[0] for t in tiles)
cv2.imwrite(out, np.hstack([cv2.copyMakeBorder(t, 0, hh - t.shape[0], 0, 4, cv2.BORDER_CONSTANT) for t in tiles]),
            [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out)
