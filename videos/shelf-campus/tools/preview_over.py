"""Check an overlay frame in context: alpha-composite a slot PNG over a footage reference frame.

  python3 tools/preview_over.py <overlay.png> <reference.png> <out.jpg> [--half]
"""
import sys
import cv2
import numpy as np

ov = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
bg = cv2.imread(sys.argv[2]).astype(np.float32) / 255
a = ov[:, :, 3:4]
out = ov[:, :, :3] * a + bg * (1 - a)
if "--half" in sys.argv:
    out = cv2.resize(out, (540, 960), interpolation=cv2.INTER_AREA)
cv2.imwrite(sys.argv[3], (out * 255).clip(0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
