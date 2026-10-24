"""Word-synced captions, drawn last over the picture (Sora 800, caps, white with a dark outline).

Each chunk is 1-3 words that appear as they are spoken (a short pop), the word being spoken lights up:
tape yellow in the crime-scene hook, SHELF blue after the drop; WHATSAPP is always WhatsApp green.
Times are output seconds (tools/words_out.py, with the ASR's misheard words corrected by hand).
Lines whose words are already on screen as big type (the names, "AI-powered academic memory", the demo,
"built by students") have no captions (direction.NO_CAPTIONS).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "renders/fonts/sora-latin-800-normal.ttf")
SIZE, Y, MAXW = 78, 1375, 960
YELLOW, BLUE, GREEN = (255, 214, 10), (143, 199, 255), (37, 211, 102)
HOOK_END = 11.2

# (chunk end, [(word, start)]); a chunk shows from its first word until its end time
CHUNKS = [
    (0.54, [("YOUR", 0.07), ("PHONE", 0.14), ("HAS", 0.38)]),
    (1.74, [("256", 0.54), ("GIGS", 1.42)]),
    (2.46, [("OF", 1.74), ("STORAGE.", 1.90)]),
    (2.87, [("AND", 2.55), ("YOU", 2.62), ("STILL", 2.71)]),
    (3.39, [("CAN'T", 2.87), ("FIND", 3.19), ("THE", 3.27)]),
    (4.26, [("#BLEEP", 3.39), ("NOTES?", 3.83)]),
    (4.93, [("MATHS", 4.37), ("IN", 4.77)]),
    (5.57, [("ONE", 4.93), ("GROUP,", 5.09)]),
    (6.53, [("COMPUTER", 5.57), ("SCIENCE", 5.95)]),
    (7.06, [("IN", 6.53), ("ANOTHER.", 6.69)]),
    (7.83, [("AND", 7.13), ("THE", 7.20), ("ASSIGNMENT", 7.27)]),
    (8.40, [("DEADLINE?", 7.83)]),
    (9.10, [("BRO,", 8.49)]),
    (9.93, [("WHAT", 9.12), ("ASSIGNMENT!", 9.30)]),
    (19.19, [("WE", 18.20), ("GOT", 18.55), ("TIRED", 18.87)]),
    (20.15, [("OF", 19.19), ("WATCHING", 19.35), ("STUDENTS", 19.67)]),
    (21.08, [("LOSE", 20.15), ("THEIR", 20.39), ("MINDS.", 20.63)]),
    (22.13, [("SO", 21.20), ("WE", 21.40), ("BUILT", 21.57)]),
    (22.76, [("SOMETHING", 22.13), ("FOR", 22.45), ("IT.", 22.62)]),
    (31.08, [("THAT", 30.07), ("LIVES", 30.28), ("ON", 30.84)]),
    (32.09, [("WHATSAPP.", 31.08)]),
    (46.14, [("YOUR", 45.60), ("NOTES", 45.74)]),
    (46.96, [("AREN'T", 46.14), ("LOST.", 46.54)]),
    (47.58, [("YOUR", 47.07), ("DEADLINES", 47.20)]),
    (48.46, [("AREN'T", 47.58), ("A", 47.90), ("SURPRISE", 47.98)]),
    (48.89, [("ANYMORE.", 48.46)]),
    (49.96, [("AND", 49.00), ("YOUR", 49.08), ("WHATSAPP?", 49.30)]),
    (50.53, [("FINALLY", 50.07)]),
    (51.33, [("DOING", 50.53), ("SOMETHING", 50.85)]),
    (51.69, [("USEFUL.", 51.33)]),
    (55.64, [("YOUR", 54.84), ("SEMESTER", 55.08)]),
    (56.95, [("JUST", 55.64), ("GOT", 55.88), ("AN", 56.04), ("UPGRADE.", 56.20)]),
]

_font = {}


def font(size):
    if size not in _font:
        _font[size] = ImageFont.truetype(FONT, size)
    return _font[size]


def _layout(words, size):
    f = font(size)
    space = f.getlength(" ") * 1.4                                     # room for a popping word
    widths = [f.getlength("FUCKING" if w == "#BLEEP" else w) for w, _ in words]
    total = sum(widths) + space * (len(words) - 1)
    if total > MAXW and size > 54:
        return _layout(words, size - 4)
    x = 540 - total / 2
    pos = []
    for w in widths:
        pos.append((x, w))
        x += w + space
    return size, pos


_cache = {}


BAND = (1180, 1580)          # captions are drawn into this horizontal band only (fast), then placed at y = BAND[0]


def frame(t, n):
    """(RGBA float band, y0) caption layer at output time t, or None."""
    for end, words in CHUNKS:
        if words[0][1] <= t < end:
            break
    else:
        return None
    key = id(words)
    if key not in _cache:
        _cache.clear()
        _cache[key] = _layout(words, SIZE)
    size, pos = _cache[key]
    y0 = BAND[0]
    img = Image.new("RGBA", (1080, BAND[1] - BAND[0]), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (1080, BAND[1] - BAND[0]), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(img), ImageDraw.Draw(shadow)
    for k, ((w, ws), (x, wd)) in enumerate(zip(words, pos)):
        if t < ws:
            continue
        nxt = words[k + 1][1] if k + 1 < len(words) else end
        live = ws <= t < nxt
        u = (t - ws) / 0.12
        sc = 1.0 + 0.13 * max(0.0, 1 - u) ** 2                  # pop: 1.13 -> 1.0 over ~4 frames
        s = int(round(size * sc))
        f = font(s)
        wx = x + wd / 2 - f.getlength("FUCKING" if w == "#BLEEP" else w) / 2
        wy = Y - s * 0.62 - y0
        if w == "#BLEEP":                                         # the censored word: a glitching black bar
            jit = (n * 37 % 7) - 3 if live else 0
            box = [wx - 6 + jit, wy + s * 0.12, wx + f.getlength("FUCKING") + 6 + jit, wy + s * 0.98]
            ds.rounded_rectangle([box[0], box[1] + 6, box[2], box[3] + 6], 14, fill=(0, 0, 0, 120))
            d.rounded_rectangle(box, 14, fill=(14, 14, 18, 255), outline=(255, 59, 48, 255), width=5)
            for j in range(3):
                yy = box[1] + 10 + j * (box[3] - box[1] - 20) / 2.5
                d.line([box[0] + 14, yy, box[2] - 14, yy], fill=(255, 59, 48, 150), width=3)
            continue
        if "WHATSAPP" in w:
            col = GREEN
        elif "SHELF" in w:
            col = BLUE
        elif live:
            col = YELLOW if t < HOOK_END else BLUE
        else:
            col = (255, 255, 255)
        ds.text((wx, wy + 7), w, font=f, fill=(0, 0, 0, 150), stroke_width=9, stroke_fill=(0, 0, 0, 150))
        d.text((wx, wy), w, font=f, fill=col + (255,), stroke_width=7, stroke_fill=(10, 12, 18, 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    out = Image.alpha_composite(shadow, img)
    return np.asarray(out, np.float32) / 255, y0
