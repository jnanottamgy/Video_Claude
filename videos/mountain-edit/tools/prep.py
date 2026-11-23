"""Mattes for the shots that need them (words behind people and cars, white cut-outs, glows, HUD locks).

Each matte is computed on the exact base frame the compositor draws (view moves included), by rembg
(isnet-general-use for people and cars, u2net_human_seg for quick human ones), then refined against the frame
with a guided filter so hair and edges follow the picture.
  python3 tools/prep.py [SHOT ...]   ->  renders/cache/matte/<shot>/<frame>.png   (existing frames are kept)
"""
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402
import render  # noqa: E402

MODELS = {"isnet": "isnet-general-use", "human": "u2net_human_seg"}


def guided(I, p, r=6, eps=1e-4):
    """He et al. guided filter (grey guide), box filters at full res."""
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def main():
    from PIL import Image
    from rembg import new_session, remove
    ids = sys.argv[1:] or [s["id"] for s in edl.SHOTS if s.get("matte")]
    sessions = {}
    for sid in ids:
        spec = edl.SPECS[sid]
        model = MODELS[spec["matte"]]
        if model not in sessions:
            sessions[model] = new_session(model)
        d = os.path.join(render.CACHE, "matte", sid)
        os.makedirs(d, exist_ok=True)
        t0 = time.time()
        n = 0
        for f in range(spec["F0"], spec["F1"]):
            out = os.path.join(d, f"{f:05d}.png")
            if os.path.exists(out):
                continue
            img = render.base(spec, f / render.FPS, f)
            u8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
            m = np.asarray(remove(Image.fromarray(u8), session=sessions[model], only_mask=True)).astype(np.float32) / 255
            grey = cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            mr = np.clip((guided(grey, m) - 0.04) / 0.92, 0, 1)
            cv2.imwrite(out, (mr * 255 + 0.5).astype(np.uint8))
            n += 1
        print(f"{sid}: {n} frames in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
