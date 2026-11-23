"""The Instagram cover (1080x1920): the summit photo, "DNA." behind him, the scanner lock, the helix.

  python3 tools/cover.py  ->  renders/deliver/DNA_cover.jpg (and a 3:4 grid-crop preview)
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402
import gfx  # noqa: E402
import look  # noqa: E402
import render  # noqa: E402

CW, CH = 1080, 1920


def main():
    out_dir = os.path.join(render.ROOT, "renders/deliver")
    os.makedirs(out_dir, exist_ok=True)
    img, bg, m = render.photo_layers("F1")               # the summit photo, its background and his matte
    ih, iw = img.shape[:2]
    # fit the photo's width to the cover; keep him in the lower middle
    k = CW / iw
    cy = ih * 0.52
    M = np.float32([[k, 0, 0], [0, k, CH / 2 - k * cy]])
    warp = lambda x: cv2.warpAffine(x, M, (CW, CH), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT101)
    pic, mat = warp(img), warp(m)
    # grade with the intro look, darkening the sky
    yy = np.linspace(0, 1, CH, dtype=np.float32)[:, None, None]
    g = pic * (1 - 0.5 * np.clip((0.55 - yy) / 0.55, 0, 1) ** 1.3)
    g = look.saturate(look.scurve(look.levels(g, 0.035, 0.97, 0.96), 1.3), 0.72)
    g = np.clip(look.split_tone(g, (-0.02, 0.005, 0.03), (0.035, 0.012, -0.03)), 0, 1)
    # DNA. behind him
    spr = gfx.text("DNA.", gfx.F_BIG, 520, gfx.RED, 0.02)
    ov = np.zeros((CH, CW, 4), np.float32)
    sh, sw = spr.shape[:2]
    s = min(1.0, CW * 0.94 / sw)
    spr2 = cv2.resize(spr, (int(sw * s), int(sh * s)), interpolation=cv2.INTER_AREA)
    y0 = int(CH * 0.515 - spr2.shape[0] / 2)
    x0 = int((CW - spr2.shape[1]) / 2)
    ov[y0:y0 + spr2.shape[0], x0:x0 + spr2.shape[1]] = spr2
    out = g * (1 - ov[..., 3:4]) + ov[..., :3]
    mm = render.fill_holes(cv2.resize(mat, (1920, 1080)))           # fill_holes works at the reel size
    mm = cv2.resize(mm, (CW, CH))[..., None]
    out = out * (1 - mm) + g * mm
    # scanner lock on his head
    ys, xs = np.nonzero(mat > 0.5)
    if len(xs):
        hx0, hx1 = np.percentile(xs, 2), np.percentile(xs, 98)
        hy0 = np.percentile(ys, 0.5)
        head = (hx0 + (hx1 - hx0) * 0.25, hy0 - 10, hx1 - (hx1 - hx0) * 0.25, hy0 + (hx1 - hx0) * 0.5)
        h = np.zeros((CH, CW, 4), np.uint8)
        hud = gfx.Hud.__new__(gfx.Hud)
        hud.c = h
        x0b, y0b, x1b, y1b = head
        L = 26
        for (x, y, sx, sy) in ((x0b, y0b, 1, 1), (x1b, y0b, -1, 1), (x0b, y1b, 1, -1), (x1b, y1b, -1, -1)):
            cv2.line(h, (int(x), int(y)), (int(x + sx * L), int(y)), (235, 245, 255, 255), 3, cv2.LINE_AA)
            cv2.line(h, (int(x), int(y)), (int(x), int(y + sy * L)), (235, 245, 255, 255), 3, cv2.LINE_AA)
        hov = h.astype(np.float32) / 255
        out = out * (1 - hov[..., 3:4]) + hov[..., :3]
        lab = gfx.text("SUBJECT 01", gfx.F_MONOB, 30, (1, 1, 1))
        tag = np.zeros((lab.shape[0] + 8, lab.shape[1] + 16, 3), np.float32) + np.array(gfx.RED, np.float32)
        tx, ty = int(x1b + 14), int(y0b)
        if ty > 0:
            out[ty:ty + tag.shape[0], tx:tx + tag.shape[1]] = tag
            a = lab[..., 3:4]
            out[ty + 4:ty + 4 + lab.shape[0], tx + 8:tx + 8 + lab.shape[1]] = (
                out[ty + 4:ty + 4 + lab.shape[0], tx + 8:tx + 8 + lab.shape[1]] * (1 - a) + lab[..., :3])
    # a thin helix up the left edge, and the corner marks
    hov = np.zeros((1080, 1920, 4), np.float32)
    gfx.helix(hov, 140, 540, 760, 54, 0.9, 1.0, alpha=0.9)
    hov = cv2.resize(hov[:, :280], (int(280 * CH / 1080 / 1.5), int(CH / 1.5)))
    hy = int(CH * 0.08)
    hx = CW - hov.shape[1] - 10
    out[hy:hy + hov.shape[0], hx:hx + hov.shape[1]] = out[hy:hy + hov.shape[0], hx:hx + hov.shape[1]] * (1 - hov[..., 3:4]) + hov[..., :3]
    vg = np.sqrt(((np.mgrid[0:CH, 0:CW][1] - CW / 2) / (CW / 2)) ** 2 * 0.5 + ((np.mgrid[0:CH, 0:CW][0] - CH / 2) / (CH / 2)) ** 2)
    out = out * (1 - 0.35 * np.clip(vg, 0, 1.4) ** 2.2)[..., None]
    rng = np.random.default_rng(1)
    gr = cv2.GaussianBlur(rng.standard_normal((CH, CW)).astype(np.float32), (0, 0), 0.7)
    out = np.clip(out + gr[..., None] * 0.02, 0, 1)
    p = os.path.join(out_dir, "DNA_cover.jpg")
    cv2.imwrite(p, cv2.cvtColor((out * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
    grid = out[int((CH - 1440) / 2):int((CH - 1440) / 2) + 1440]
    cv2.imwrite(os.path.join(out_dir, "DNA_cover_grid_preview.jpg"),
                cv2.cvtColor((grid * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(p)


if __name__ == "__main__":
    main()
