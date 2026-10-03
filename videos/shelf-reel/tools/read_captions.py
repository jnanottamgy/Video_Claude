"""Find every burned-in caption in the source reel: when it appears, when it leaves, where it sits.

The reel's captions are warm-yellow text (RGB ~244,216,129) with a black outline, centred near
y = 1375. A pixel counts as caption ink when it has that fill colour AND sits next to outline-dark
pixels. A new caption starts whenever the ink mask changes shape.

  python3 tools/read_captions.py  ->  renders/captions_raw.json  +  renders/caption_sheets/*.jpg
"""
import json, os, subprocess
import cv2
import numpy as np

SRC, W, H, FPS = "renders/source.mp4", 1080, 1920, 30
Y0, BH = 1300, 160                       # band searched for captions
FILL = np.array([129, 216, 244])         # BGR


def frames():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"crop={W}:{BH}:0:{Y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * BH * 3)
        if len(b) < W * BH * 3:
            return
        yield np.frombuffer(b, np.uint8).reshape(BH, W, 3)


def ink(img):
    d = np.abs(img.astype(np.int16) - FILL).max(axis=2)
    fill = (d < 34).astype(np.uint8)
    dark = (img.max(axis=2) < 70).astype(np.uint8)
    m = fill & cv2.dilate(dark, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return m if m.sum() > 120 else np.zeros_like(m)


def bbox(m):
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()) + Y0, int(xs.max()), int(ys.max()) + Y0]


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


segs, cur, prev, shots = [], None, None, {}
k = np.ones((5, 5), np.uint8)
for n, img in enumerate(frames()):
    m = ink(img)
    on = m.sum() > 0
    iou = 0.0
    if on and prev is not None and prev.sum() > 0:
        a, b = cv2.dilate(m, k), cv2.dilate(prev, k)
        iou = (a & b).sum() / max((a | b).sum(), 1)
    if cur is not None and (not on or iou < 0.55):
        cur["end"] = n; segs.append(cur); cur = None
    if on:
        if cur is None:
            cur = {"start": n, "bbox": bbox(m)}
        cur["bbox"] = union(cur["bbox"], bbox(m))
        if n - cur["start"] in (0, 4):           # a frame safely inside the caption (past any pop-in)
            shots[cur["start"]] = img.copy()
    prev = m
if cur is not None:
    cur["end"] = n + 1; segs.append(cur)
segs = [s for s in segs if s["end"] - s["start"] >= 3]          # drop 1-2 frame flickers
for s in segs:
    s["t0"], s["t1"] = round(s["start"] / FPS, 3), round(s["end"] / FPS, 3)
print(len(segs), "captions")
json.dump(segs, open("renders/captions_raw.json", "w"), indent=1)

# Reading sheets: one row per caption, labelled with its index and time.
os.makedirs("renders/caption_sheets", exist_ok=True)
rows = []
for i, s in enumerate(segs):
    x0, _, x1, _ = s["bbox"]
    cx = (x0 + x1) // 2
    crop = shots[s["start"]][20:140, max(0, cx - 330):min(W, cx + 330)]
    crop = cv2.copyMakeBorder(crop, 0, 0, 0, 660 - crop.shape[1], cv2.BORDER_CONSTANT)
    label = np.zeros((120, 260, 3), np.uint8)
    cv2.putText(label, f"#{i}", (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
    cv2.putText(label, f"{s['t0']:.2f}-{s['t1']:.2f}", (8, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    rows.append(np.hstack([label, crop]))
for j in range(0, len(rows), 16):
    cv2.imwrite(f"renders/caption_sheets/sheet_{j // 16:02d}.jpg", np.vstack(rows[j:j + 16]), [cv2.IMWRITE_JPEG_QUALITY, 88])
