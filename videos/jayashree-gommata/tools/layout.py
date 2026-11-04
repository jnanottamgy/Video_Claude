"""The vertical frame: the footage in a gold-bordered window, over a soft, glowing, blurred copy of itself.

The source is a 16:9 stream (360p today), so a full-screen 9:16 crop would be ~6x enlarged and mushy. Instead the
footage sits in a 4:3 window (enlarged ~2.2x, with care), and the 9:16 canvas around it is the same shot,
heavily blurred, warm and dark. The window has a temple-gold double border with small lotus-bud ornaments; the
title block lives above it and the lyrics below.
  python3 tools/layout.py OUT.jpg SRC_T [SRC_T ...]   # stills, for checking the look
"""
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import media  # noqa: E402

W, H = 1080, 1920
ASPECT = 4 / 3
WIN_W = 936
WIN_H = int(round(WIN_W / ASPECT))                        # 702
WIN_X = (W - WIN_W) // 2                                  # 72
WIN_CY = 945                                              # window centre (y)
WIN_Y = WIN_CY - WIN_H // 2                               # 554
GOLD = np.array([1.0, 0.80, 0.46], np.float32)
GOLD_DEEP = np.array([0.86, 0.60, 0.28], np.float32)


def background(src, box, darken=0.40):
    """The canvas behind the window: the shot's centre column, blurred and darkened (float RGB 1080x1920)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sh, sw = src.shape[:2]
    cy0, cy1 = media.CLEAN[1] * sh, media.CLEAN[3] * sh            # stay off the ticker and the timestamp
    cx0, cx1 = media.CLEAN[0] * sw, media.CLEAN[2] * sw
    h = min((y1 - y0) * 1.12, cy1 - cy0)
    w = min(h * W / H, cx1 - cx0)
    cx = min(max(cx, cx0 + w / 2), cx1 - w / 2)
    cy = min(max(cy, cy0 + h / 2), cy1 - h / 2)
    small = media.warp(src, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 135, 240, cv2.INTER_AREA)
    small = cv2.GaussianBlur(small.astype(np.float32) / 255, (0, 0), 7)
    big = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
    L = big.mean(2, keepdims=True)
    big = L + (big - L) * 0.8                                # a little less saturated than the window
    return np.clip(big * darken + np.array([0.035, 0.018, 0.006], np.float32), 0, 1)


def window(src, box, sharp=0.55):
    """The footage for the window (float RGB WIN_W x WIN_H)."""
    img = media.warp(src, box, WIN_W, WIN_H).astype(np.float32) / 255
    return media.sharpen(img, sharp, 1.3)


_frame_cache = {}


def frame_art():
    """The window's border, shadow and ornaments as (alpha, colour) layers for the full canvas, cached."""
    if "art" in _frame_cache:
        return _frame_cache["art"]
    s = 3                                                     # supersample
    art = np.zeros((H * s, W * s), np.uint8)
    x0, y0, x1, y1 = WIN_X * s, WIN_Y * s, (WIN_X + WIN_W) * s, (WIN_Y + WIN_H) * s
    for off, th in ((-7, 1.4), (-17, 2.6)):                  # inner hairline, outer line
        o = int(-off * s)
        cv2.rectangle(art, (x0 - o, y0 - o), (x1 + o, y1 + o), 255, int(th * s), cv2.LINE_AA)
    # corner ornaments: a small diamond on each outer corner, with two dots along the edges
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        ox = -17 * s if cx == x0 else 17 * s
        oy = -17 * s if cy == y0 else 17 * s
        px, py = cx + ox, cy + oy
        d = 9 * s
        pts = np.array([[px, py - d], [px + d, py], [px, py + d], [px - d, py]], np.int32)
        cv2.fillConvexPoly(art, pts, 255, cv2.LINE_AA)
        for k in (1, 2):
            sx = 1 if cx == x0 else -1
            sy = 1 if cy == y0 else -1
            cv2.circle(art, (px + sx * (16 + 10 * k) * s, py), int(2.2 * s), 255, -1, cv2.LINE_AA)
            cv2.circle(art, (px, py + sy * (16 + 10 * k) * s), int(2.2 * s), 255, -1, cv2.LINE_AA)
    # a lotus bud at the top and bottom centre of the outer line
    for cy, up in ((y0 - 17 * s, True), (y1 + 17 * s, False)):
        cx = (x0 + x1) // 2
        sg = -1 if up else 1
        for k, (rx, ry) in enumerate(((22, 13), (13, 22), (6, 26))):
            cv2.ellipse(art, (cx, cy + sg * ry * s // 2), (rx * s // 2 + 4 * s, ry * s // 2 + 3 * s), 0, 0, 360,
                        0, -1, cv2.LINE_AA)
        for ang in (-32, 32):
            cv2.ellipse(art, (cx + int(math.sin(math.radians(ang)) * 9 * s), cy + sg * 9 * s), (5 * s, 13 * s), ang * sg,
                        0, 360, 255, -1, cv2.LINE_AA)
        cv2.ellipse(art, (cx, cy + sg * 12 * s), (6 * s, 16 * s), 0, 0, 360, 255, -1, cv2.LINE_AA)
        cv2.circle(art, (cx, cy - sg * 4 * s), int(3 * s), 255, -1, cv2.LINE_AA)
    a = cv2.resize(art, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    # the colour: a vertical gold gradient with a little shimmer along the lines
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    col = GOLD * (1 - yy * 0.25) + GOLD_DEEP * yy * 0.25
    col = np.broadcast_to(col, (H, W, 3)).copy()
    sh = np.zeros((H, W), np.float32)
    sh[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W] = 1
    shadow = cv2.GaussianBlur(sh, (0, 0), 26)
    _frame_cache["art"] = (a, col, shadow)
    return _frame_cache["art"]


def compose(bg, win, glint=None, pulse=0.0):
    """Window into canvas, with its shadow and the gold border (and an optional glint position 0..1 along it)."""
    a, col, shadow = frame_art()
    out = bg * (1 - 0.55 * shadow[..., None])
    out[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W] = win
    if glint is not None:
        # a bright spot travelling clockwise round the border
        per = 2 * (WIN_W + WIN_H)
        d = (glint % 1.0) * per
        if d < WIN_W:
            gx, gy = WIN_X + d, WIN_Y - 17
        elif d < WIN_W + WIN_H:
            gx, gy = WIN_X + WIN_W + 17, WIN_Y + d - WIN_W
        elif d < 2 * WIN_W + WIN_H:
            gx, gy = WIN_X + WIN_W - (d - WIN_W - WIN_H), WIN_Y + WIN_H + 17
        else:
            gx, gy = WIN_X - 17, WIN_Y + WIN_H - (d - 2 * WIN_W - WIN_H)
        y0, y1, x0, x1 = int(max(0, gy - 90)), int(min(H, gy + 90)), int(max(0, gx - 90)), int(min(W, gx + 90))
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        g = np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * 34.0 ** 2))
        boost = np.ones((H, W), np.float32)
        boost[y0:y1, x0:x1] += g * 1.6
        aa = np.clip(a * boost, 0, 1)
        cc = np.clip(col * boost[..., None], 0, 1)
    else:
        aa, cc = a, col
    if pulse > 0:                                              # the border flares on a cut
        aa = np.clip(aa * (1 + 0.8 * pulse), 0, 1)
        cc = np.clip(cc * (1 + 0.45 * pulse), 0, 1)
    out = out * (1 - aa[..., None]) + cc * aa[..., None]
    return out


if __name__ == "__main__":
    import look
    out = sys.argv[1]
    table = look.lut("gold")
    stills = []
    for t in sys.argv[2:]:
        t = float(t)
        r = media.Reader(t, t + 0.1)
        src = r.at(t)
        box = media.crop_box(r.w, r.h, 0.5, 0.45, 0.72, ASPECT)
        graded = look.apply(src, table)
        fr = compose(background(graded, box), window(graded, box), glint=0.1)
        fr = look.finish(fr, 1)
        stills.append((fr * 255 + 0.5).astype(np.uint8))
    sheet = np.hstack([cv2.resize(s, (540, 960), interpolation=cv2.INTER_AREA) for s in stills])
    cv2.imwrite(out, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(out.replace(".jpg", "_full.jpg"), cv2.cvtColor(stills[0], cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(out)
