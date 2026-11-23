"""The REEL 2 cover (1080x1920): the teal Polo frozen mid-drift from the full vertical frame, the world drained
around it, a white outline, REDLINE behind its roof, the HUD tag.

  python3 tools/cover_v2.py  ->  renders/deliver/REDLINE_cover.jpg (and a 3:4 grid-crop preview)
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx  # noqa: E402
import look  # noqa: E402
import media  # noqa: E402

CW, CH = 1080, 1920
ROOT = media.ROOT


def main():
    out_dir = os.path.join(ROOT, "renders/deliver")
    os.makedirs(out_dir, exist_ok=True)
    fr, _ = media.decode("0461", 10.44, 10.44 + 1.5 / 60)
    img = fr[0].astype(np.float32) / 255
    assert img.shape[:2] == (CH, CW), img.shape
    cache = os.path.join(ROOT, "renders/cache/photo/cover_v2.png")
    if os.path.exists(cache):
        m = cv2.imread(cache, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    else:
        from PIL import Image
        from rembg import new_session, remove
        m = np.asarray(remove(Image.fromarray(fr[0]), session=new_session("isnet-general-use"), only_mask=True)).astype(np.float32) / 255
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        cv2.imwrite(cache, (m * 255).astype(np.uint8))
    # keep only the car: the largest blob
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0.5).astype(np.uint8), 8)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = m * cv2.GaussianBlur((lab == k).astype(np.float32), (0, 0), 2)
    g = look.grade(img, "rally")
    L = look.luma(g)[..., None]
    bg = np.clip(look.scurve(L, 1.4) * np.array([0.86, 0.93, 1.02], np.float32) * 0.6, 0, 1)
    yy = np.linspace(0, 1, CH, dtype=np.float32)[:, None, None]
    bg = bg * (1 - 0.45 * np.clip((0.4 - yy) / 0.4, 0, 1))                 # darker towards the top
    mm = m[..., None]
    out = g * mm + bg * (1 - mm)
    ys, xs = np.nonzero(m > 0.5)
    top = int(np.percentile(ys, 1))
    # REDLINE behind the roof
    spr = gfx.text("REDLINE", gfx.F_BIG, 330, gfx.RED, 0.03)
    s = min(1.0, CW * 0.94 / spr.shape[1])
    spr = cv2.resize(spr, (int(spr.shape[1] * s), int(spr.shape[0] * s)), interpolation=cv2.INTER_AREA)
    ov = np.zeros((CH, CW, 4), np.float32)
    y0 = top - int(spr.shape[0] * 0.82)
    x0 = (CW - spr.shape[1]) // 2
    ov[y0:y0 + spr.shape[0], x0:x0 + spr.shape[1]] = spr
    out = out * (1 - ov[..., 3:4]) + ov[..., :3]
    out = out * (1 - mm) + g * mm
    # the outline and a red bloom
    b = (m > 0.5).astype(np.uint8)
    dil = cv2.dilate(b, np.ones((9, 9), np.uint8))
    ring = cv2.GaussianBlur((dil - b).astype(np.float32), (0, 0), 1.0)[..., None]
    bloom = np.clip(cv2.GaussianBlur(dil.astype(np.float32), (0, 0), 26) - b, 0, 1)[..., None]
    out = 1 - (1 - out) * (1 - bloom * 0.55 * np.array(gfx.RED, np.float32))
    out = out * (1 - ring) + ring
    # HUD tag and brackets around the car
    x_0, x_1, y_1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 99)
    gfx.W, gfx.H = CW, CH                  # the HUD draws on a portrait canvas here
    h = np.zeros((CH, CW, 4), np.uint8)
    hud = gfx.Hud.__new__(gfx.Hud)
    hud.c = h
    hud.shadow = 0.45
    hud.brackets(max(20, x_0 - 18), top - 18, min(CW - 20, x_1 + 18), y_1 + 18, (1, 1, 1), 0.95, 5, 0.12)
    hud.shadow = 0
    hud.text("CAR 65 // VW POLO", max(20, x_0 - 18), y_1 + 34, 30, (1, 1, 1), 1.0, gfx.F_MONOB, anchor="la",
             bg=(gfx.RED, 0.95))
    hud.text("DRIFT 41 DEG  //  STATUS FROZEN", max(20, x_0 - 18), y_1 + 92, 26, (1, 1, 1), 0.95, gfx.F_MONOB, anchor="la")
    # a rev bar at the foot of the frame, in the red
    n, bx0, bx1, by = 30, 60, CW - 60, CH - 230
    seg = (bx1 - bx0) / n
    for i in range(n):
        col = gfx.RED if i >= n * 0.8 else (1, 1, 1)
        hud.rect(bx0 + i * seg + 2, by - (12 + 14 * i / n), bx0 + (i + 1) * seg - 3, by, col, 0.92, fill=True)
    hud.text("REV LIMIT", bx0, by + 16, 24, (1, 1, 1), 0.9, gfx.F_MONOB, anchor="la")
    hud.text("FULL SEND", bx1, by + 16, 24, (1, 1, 1), 1.0, gfx.F_MONOB, anchor="ra", bg=(gfx.RED, 0.95))
    hov = h.astype(np.float32) / 255
    out = out * (1 - hov[..., 3:4]) + hov[..., :3]
    vy, vx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    vr = np.sqrt(((vx - CW / 2) / (CW / 2)) ** 2 * 0.5 + ((vy - CH / 2) / (CH / 2)) ** 2)
    out = np.clip(out, 0, 1) * (1 - 0.35 * np.clip(vr, 0, 1.4) ** 2.2)[..., None]
    rng = np.random.default_rng(1)
    gr = cv2.GaussianBlur(rng.standard_normal((CH, CW)).astype(np.float32), (0, 0), 0.7)
    out = np.clip(out + gr[..., None] * 0.018, 0, 1)
    p = os.path.join(out_dir, "REDLINE_cover.jpg")
    cv2.imwrite(p, cv2.cvtColor((out * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
    grid = out[(CH - 1440) // 2:(CH - 1440) // 2 + 1440]
    cv2.imwrite(os.path.join(out_dir, "REDLINE_cover_grid_preview.jpg"),
                cv2.cvtColor((grid * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(p)


if __name__ == "__main__":
    main()
