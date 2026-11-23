"""The REEL 3 cover (1080x1920): car 14 frozen head-on, cut from the 4K frame as a vertical, the world drained
around it, a white outline, TORE torn in two above the roof and UP. below the bumper, the HUD tag.

  python3 tools/cover_v3.py  ->  renders/deliver/TOREUP_cover.jpg (and a 3:4 grid-crop preview)
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx2  # noqa: E402
import gfx  # noqa: E402
import look  # noqa: E402
import media  # noqa: E402

CW, CH = 1080, 1920
ROOT = media.ROOT


def main():
    out_dir = os.path.join(ROOT, "renders/deliver")
    os.makedirs(out_dir, exist_ok=True)
    cx = 2230
    fr, _ = media.decode("0397", 4.16, 4.16 + 1.5 / 30, band=(cx - 608, 0, 1216, 2160))
    img = cv2.resize(fr[0], (CW, CH), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    cache = os.path.join(ROOT, "renders/cache/photo/cover_v3.png")
    if os.path.exists(cache):
        m = cv2.imread(cache, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    else:
        from PIL import Image
        from rembg import new_session, remove
        u8 = (img * 255).astype(np.uint8)
        m = np.asarray(remove(Image.fromarray(u8), session=new_session("isnet-general-use"), only_mask=True)).astype(np.float32) / 255
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        cv2.imwrite(cache, (m * 255).astype(np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0.5).astype(np.uint8), 8)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = m * cv2.GaussianBlur((lab == k).astype(np.float32), (0, 0), 2)
    g = look.grade(img, "rally")
    L = look.luma(g)[..., None]
    bg = np.clip(look.scurve(L, 1.4) * np.array([0.86, 0.93, 1.02], np.float32) * 0.58, 0, 1)
    mm = m[..., None]
    out = g * mm + bg * (1 - mm)
    ys, xs = np.nonzero(m > 0.5)
    top, bot = int(np.percentile(ys, 1)), int(np.percentile(ys, 99))
    x0, x1 = np.percentile(xs, 1), np.percentile(xs, 99)
    # TORE above the roof (its foot tucked behind the car), UP. below the bumper
    ov = np.zeros((CH, CW, 4), np.float32)
    gfx.W, gfx.H = CW, CH
    for word, col, y, seed in (("TORE", gfx.WHITE, top - 120, 5), ("UP.", gfx.RED, bot + 190, 9)):
        spr = fx2.torn_sprite(gfx.text(word, gfx.F_BIG, 400, col, 0.03), 26, seed)
        s = min(1.0, CW * 0.9 / spr.shape[1])
        spr = cv2.resize(spr, (int(spr.shape[1] * s), int(spr.shape[0] * s)), interpolation=cv2.INTER_AREA)
        ya = int(y - spr.shape[0] / 2)
        xa = (CW - spr.shape[1]) // 2
        ya0, yb0 = max(0, ya), min(CH, ya + spr.shape[0])
        piece = spr[ya0 - ya:yb0 - ya]
        reg = ov[ya0:yb0, xa:xa + spr.shape[1]]
        reg[...] = piece + reg * (1 - piece[..., 3:4])
    out = out * (1 - ov[..., 3:4]) + ov[..., :3]
    out = out * (1 - mm) + g * mm                       # the car in front of the type
    b = (m > 0.5).astype(np.uint8)
    dil = cv2.dilate(b, np.ones((9, 9), np.uint8))
    ring = cv2.GaussianBlur((dil - b).astype(np.float32), (0, 0), 1.0)[..., None]
    bloom = np.clip(cv2.GaussianBlur(dil.astype(np.float32), (0, 0), 26) - b, 0, 1)[..., None]
    out = 1 - (1 - out) * (1 - bloom * 0.55 * np.array(gfx.RED, np.float32))
    out = out * (1 - ring) + ring
    h = np.zeros((CH, CW, 4), np.uint8)
    hud = gfx.Hud.__new__(gfx.Hud)
    hud.c = h
    hud.shadow = 0.45
    hud.brackets(max(20, x0 - 24), top - 24, min(CW - 20, x1 + 24), bot + 24, (1, 1, 1), 0.95, 5, 0.12)
    hud.shadow = 0
    hud.text("CAR 14 // VW POLO", 60, 110, 30, (1, 1, 1), 1.0, gfx.F_MONOB, anchor="la", bg=(gfx.RED, 0.95))
    hud.text("STATUS  TORE UP", 60, 162, 26, (1, 1, 1), 0.95, gfx.F_MONOB, anchor="la")
    nseg, bx0, bx1, by = 30, 60, CW - 60, CH - 90
    seg = (bx1 - bx0) / nseg
    for i in range(nseg):
        col = gfx.RED if i >= nseg * 0.8 else (1, 1, 1)
        hud.rect(bx0 + i * seg + 2, by - (12 + 14 * i / nseg), bx0 + (i + 1) * seg - 3, by, col, 0.92, fill=True)
    hov = h.astype(np.float32) / 255
    out = out * (1 - hov[..., 3:4]) + hov[..., :3]
    vy, vx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    vr = np.sqrt(((vx - CW / 2) / (CW / 2)) ** 2 * 0.5 + ((vy - CH / 2) / (CH / 2)) ** 2)
    out = np.clip(out, 0, 1) * (1 - 0.35 * np.clip(vr, 0, 1.4) ** 2.2)[..., None]
    rng = np.random.default_rng(1)
    gr = cv2.GaussianBlur(rng.standard_normal((CH, CW)).astype(np.float32), (0, 0), 0.7)
    out = np.clip(out + gr[..., None] * 0.018, 0, 1)
    p = os.path.join(out_dir, "TOREUP_cover.jpg")
    cv2.imwrite(p, cv2.cvtColor((out * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
    grid = out[(CH - 1440) // 2:(CH - 1440) // 2 + 1440]
    cv2.imwrite(os.path.join(out_dir, "TOREUP_cover_grid_preview.jpg"),
                cv2.cvtColor((grid * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(p)


if __name__ == "__main__":
    main()
