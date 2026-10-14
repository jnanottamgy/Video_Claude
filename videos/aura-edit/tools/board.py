"""One labelled board of the reference edit's techniques (a frame of each, with its timing).

  python3 tools/board.py renders/ref/reference.mp4 renders/analysis/effects_board.jpg
"""
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

TILES = [
    (4, "Cutout strobe intro", "0.0-0.46s · body parts flash white→red, 1 frame each"),
    (58, "Hand-over-lens wipe", "2.2-2.6s · next shot revealed behind the hand"),
    (116, "Echo + match dissolve", "4.7-5.0s · ghost trails, warm→teal, lands with shake"),
    (160, "White silhouette flash", "6.38 / 6.67 / 6.96s · new person flashes white for 1 frame"),
    (214, "Double exposure", "7.7-10.1s · inner clip swaps every 6 frames, music muffled"),
    (240, "Threshold silhouette", "9.9-10.1s · solid black cut-out, then the drop"),
    (348, "Squad assembles", "13.9-15.0s · tripod stop-motion, one person per 8th note"),
    (320, "Lyric word pop", "13.25-13.71s · serif caps, hard in / hard out"),
    (375, "White mask flash", "15.6-15.8 & 18.2-18.4s · regions flash white, 1 frame each"),
    (398, "Orbit spin", "16.46-16.79s · in-camera spin, one 8th-note long"),
    (473, "Block reveal", "19.0-19.9s · line → bar → cross → blocks → B&W shot"),
    (516, "Logo walk-by", "21.0-22.0s · logo sits behind him, his walk reveals it"),
]
BAND = (437, 843)          # the 16:9 picture inside the 9:16 letterbox
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"


def main():
    src, out = sys.argv[1], sys.argv[2]
    want = {f for f, _, _ in TILES}
    cap = cv2.VideoCapture(src)
    got, i = {}, 0
    while len(got) < len(want):
        ok, fr = cap.read()
        if not ok:
            break
        if i in want:
            got[i] = cv2.cvtColor(fr[BAND[0]:BAND[1]], cv2.COLOR_BGR2RGB)
        i += 1
    tw, th, lh, pad, cols = 480, 270, 64, 14, 4
    rows = (len(TILES) + cols - 1) // cols
    img = Image.new("RGB", (cols * tw + (cols + 1) * pad, 92 + rows * (th + lh) + (rows + 1) * pad), (16, 16, 18))
    d = ImageDraw.Draw(img)
    fb, fs, ft = (ImageFont.truetype(FONT.format(s), n) for s, n in (("-Bold", 21), ("", 15), ("-Bold", 30)))
    d.text((pad, 18), "Reference edit: the 12 moves", font=ft, fill=(245, 245, 245))
    d.text((pad, 58), "25.5 s · 24 fps · 16:9 letterboxed in 9:16 · ~95 BPM phonk, one scene per bar (2.52 s)",
           font=fs, fill=(170, 170, 175))
    for k, (f, title, sub) in enumerate(TILES):
        r, c = divmod(k, cols)
        x, y = pad + c * (tw + pad), 92 + pad + r * (th + lh + pad)
        img.paste(Image.fromarray(cv2.resize(got[f], (tw, th), interpolation=cv2.INTER_AREA)), (x, y))
        d.text((x, y + th + 8), f"{k + 1}. {title}", font=fb, fill=(255, 196, 64))
        d.text((x, y + th + 36), sub, font=fs, fill=(205, 205, 210))
    img.save(out, quality=90)
    print(out, img.size)


if __name__ == "__main__":
    main()
