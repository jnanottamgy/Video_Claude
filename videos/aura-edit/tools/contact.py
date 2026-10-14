"""Labelled contact sheets of chosen frames, cropped to the picture inside the letterbox.

  python3 tools/contact.py VIDEO OUT.png SPEC [--cols 6] [--w 300] [--crop y0:y1] [--beats renders/analysis/audio.json]

SPEC: comma-separated frame ranges, each "a-b" or "a-b:step" (inclusive), e.g. "0-12,50-66:2".
Each tile is labelled with its frame number and time; a tile within half a frame of a detected beat
is marked B, one within half a frame of an onset is marked o.
"""
import argparse
import json

import cv2
import numpy as np


def frames_of(spec):
    out = []
    for part in spec.split(","):
        rng, _, step = part.partition(":")
        a, _, b = rng.partition("-")
        out.extend(range(int(a), int(b or a) + 1, int(step or 1)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("spec")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--w", type=int, default=300)
    ap.add_argument("--crop", default="437:843")
    ap.add_argument("--beats", default=None)
    a = ap.parse_args()
    want = frames_of(a.spec)
    y0, y1 = (int(v) for v in a.crop.split(":"))
    beats, onsets = [], []
    if a.beats:
        au = json.load(open(a.beats))
        beats, onsets = au["beats"], au["onsets"]
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    got = {}
    i, need = 0, set(want)
    while need:
        ok, fr = cap.read()
        if not ok:
            break
        if i in need:
            got[i] = fr[y0:y1]
            need.discard(i)
        i += 1
    tw = a.w
    th = int(round((y1 - y0) * tw / 720))
    rows = (len(want) + a.cols - 1) // a.cols
    sheet = np.full((rows * (th + 22) + 4, a.cols * (tw + 4) + 4, 3), 24, np.uint8)
    for k, f in enumerate(want):
        r, c = divmod(k, a.cols)
        x, y = 4 + c * (tw + 4), 4 + r * (th + 22)
        if f in got:
            sheet[y + 18:y + 18 + th, x:x + tw] = cv2.resize(got[f], (tw, th), interpolation=cv2.INTER_AREA)
        t = f / fps
        tag = ""
        if any(abs(t - b) <= 0.5 / fps + 1e-6 for b in beats):
            tag += " B"
        if any(abs(t - o) <= 0.5 / fps + 1e-6 for o in onsets):
            tag += " o"
        cv2.putText(sheet, f"f{f} {t:.3f}s{tag}", (x + 2, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (80, 220, 255) if tag else (220, 220, 220), 1, cv2.LINE_AA)
    cv2.imwrite(a.out, sheet)
    print(a.out, sheet.shape[1], "x", sheet.shape[0])


if __name__ == "__main__":
    main()
