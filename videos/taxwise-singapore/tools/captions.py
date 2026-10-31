"""Captions for the on-camera sections: Gen-Z word pops in Montserrat 800 caps, key words in brand gold.

Each chunk (2-3 words, as he phrases them) owns the caption band (y ~1300-1480, x centred on 520 to keep
clear of Instagram's like/comment rail). Its words pop in exactly as he says them (scale 0.7 -> 1.08 -> 1,
5 frames), ivory on a deep-navy outline and soft shadow; the key words are gold metal. Not captioned:
- his self-introduction (6.3-9.4): the wall's name card IS the caption there;
- the full-screen graphics (they carry their own type).

  python3 tools/captions.py 3.2 38.5   # write test stills of the captions alone to renders/verify/
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

W, H = edl.W, edl.H
FONT = os.path.join(edl.ROOT, "design/fonts/montserrat-latin-800-normal.woff2")
SIZE, MIN_SIZE, MAXW = 70, 56, 820
CX, CY = 520, 1392
IVORY = (244, 239, 227)
INK = (8, 14, 30)
GOLD_STOPS = [(0.0, (250, 232, 178)), (0.5, (226, 190, 112)), (1.0, (172, 128, 60))]
GOLD_WORDS = {"AMBITIONS", "HORIZONS", "GLOBAL", "EXCITED", "EXPANSION", "COMMITMENT", "EXPERTISE",
              "TRANSPARENCY", "LASTING", "RELATIONSHIPS", "TAXWISE", "SINGAPORE", "TRUST", "BEGINNING"}

# chunks as he phrases them, in order; each section's captions end at its cut
CHUNKS = [
    ("A1", "BIG AMBITIONS"), ("A1", "DESERVE BIGGER HORIZONS"), ("A1", "AND WE’RE TAKING"), ("A1", "OURS GLOBAL"),
    ("A2", "AND I’M EXCITED"), ("A2", "TO ANNOUNCE"), ("A2", "OUR EXPANSION"), ("A2", "INTO"),
    ("A3", "OUR COMMITMENT"), ("A3", "REMAINS THE SAME"), ("A3", "EXPERTISE"), ("A3", "TRANSPARENCY"),
    ("A3", "AND BUILDING"), ("A3", "LASTING RELATIONSHIPS"),
    ("A4", "TAXWISE"), ("A4", "NOW IN SINGAPORE"), ("A4", "AND TRUST US"), ("A4", "THIS IS JUST"), ("A4", "THE BEGINNING"),
]
SECTION_END = {"A1": 6.10, "A2": 12.50, "A3": 42.37, "A4": 48.25}
SKIP = (6.25, 9.40)                     # "I am HK Vinay, managing partner at TaxWise." (the name card)


def norm(w):
    return w.upper().replace("'", "’").strip(".,:;!?")


def build():
    """[(t0, t1, [(word, t_word, gold)])] in output seconds."""
    words = [w for w in edl.words() if not (SKIP[0] <= w["s"] < SKIP[1])]
    out, i = [], 0
    for seg, text in CHUNKS:
        toks = text.split()
        got = []
        while len(got) < len(toks):
            w = words[i]
            i += 1
            if w["seg"] != seg:
                continue
            assert norm(w["w"]) == toks[len(got)], (norm(w["w"]), toks, w)
            got.append((toks[len(got)], w["s"], toks[len(got)] in GOLD_WORDS))
        out.append([seg, got])
    chunks = []
    for k, (seg, got) in enumerate(out):
        t0 = got[0][1] - 0.07
        nxt = out[k + 1] if k + 1 < len(out) else None
        t1 = SECTION_END[seg]
        if nxt and nxt[0] == seg:
            t1 = min(t1, nxt[1][0][1] - 0.07)
        chunks.append((t0, t1, got))
    return chunks


def _gold_fill(h):
    ys = np.linspace(0, 1, h)
    col = np.zeros((h, 3))
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in GOLD_STOPS], [s[1][c] for s in GOLD_STOPS])
    return col


class Captions:
    def __init__(self):
        self.chunks = build()
        self.cache = {}
        self.fonts = {}

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = ImageFont.truetype(FONT, size)
        return self.fonts[size]

    def word_img(self, word, size, gold):
        """RGBA (premultiplied float) patch of one word: shadow, navy outline, ivory or gold fill."""
        key = (word, size, gold)
        if key in self.cache:
            return self.cache[key]
        f = self.font(size)
        stroke = max(2, round(size * 0.05))
        x0, y0, x1, y1 = f.getbbox(word, stroke_width=stroke)
        pad = 24
        w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
        org = (pad - x0, pad - y0)
        fill = Image.new("L", (w, h), 0)
        ImageDraw.Draw(fill).text(org, word, font=f, fill=255)
        outl = Image.new("L", (w, h), 0)
        ImageDraw.Draw(outl).text(org, word, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        shadow = outl.filter(ImageFilter.GaussianBlur(size * 0.12))
        F = np.asarray(fill, np.float32) / 255
        O = np.asarray(outl, np.float32) / 255
        S = np.roll(np.asarray(shadow, np.float32) / 255, round(size * 0.07), axis=0) * 0.62
        if gold:
            col = np.repeat(_gold_fill(h)[:, None, :], w, axis=1) / 255
        else:
            col = np.ones((h, w, 3)) * np.array(IVORY) / 255
        ink = np.array(INK, np.float32) / 255
        a = np.clip(S + O - S * O, 0, 1)                     # shadow under the outline
        rgb = ink * (O * (1 - F))[..., None] + col * F[..., None] + ink * (S * (1 - O))[..., None]
        out = np.dstack([rgb, a]).astype(np.float32)          # premultiplied rgb, alpha
        self.cache[key] = (out, org, (x0, y0, x1, y1), pad)
        return self.cache[key]

    def layout(self, words, size):
        f = self.font(size)
        space = f.getlength(" ")
        widths = [f.getlength(w) for w, _, _ in words]
        total = sum(widths) + space * (len(words) - 1)
        lines = [list(range(len(words)))]
        if total > MAXW and len(words) > 1:                    # two balanced lines
            best = None
            for k in range(1, len(words)):
                a = sum(widths[:k]) + space * (k - 1)
                b = sum(widths[k:]) + space * (len(words) - k - 1)
                if best is None or max(a, b) < best[0]:
                    best = (max(a, b), k)
            lines = [list(range(best[1])), list(range(best[1], len(words)))]
        return lines, widths, space

    def fit(self, words):
        size = SIZE
        while size > MIN_SIZE:
            lines, widths, space = self.layout(words, size)
            if max(sum(widths[i] for i in ln) + space * (len(ln) - 1) for ln in lines) <= MAXW:
                break
            size -= 2
        return size

    def render(self, t):
        """RGBA overlay (premultiplied) for output time t, or None."""
        ch = next((c for c in self.chunks if c[0] <= t < c[1]), None)
        if ch is None:
            return None
        t0, t1, words = ch
        size = self.fit(words)
        lines, widths, space = self.layout(words, size)
        f = self.font(size)
        asc, desc = f.getmetrics()
        lh = size * 1.08
        canvas = np.zeros((H, W, 4), np.float32)                 # (rows outside the band stay empty)
        y_mid0 = CY - lh * (len(lines) - 1) / 2
        out_k = np.clip((t1 - t) / 0.12, 0, 1) if t1 == SECTION_END["A4"] else 1.0    # hard cuts elsewhere
        for li, ln in enumerate(lines):
            lw = sum(widths[i] for i in ln) + space * (len(ln) - 1)
            x = CX - lw / 2
            yc = y_mid0 + li * lh
            for i in ln:
                word, tw, gold = words[i]
                p = (t - max(tw - 0.05, t0)) / 0.17
                if p < 0:
                    x += widths[i] + space
                    continue
                s = float(np.interp(p, [0, 0.55, 1], [0.70, 1.08, 1.0])) if p < 1 else 1.0
                alpha = float(np.clip(p / 0.3, 0, 1)) * out_k
                fs = max(8, int(round(size * s)))
                img, org, bb, pad = self.word_img(word, fs, gold)
                # centre the scaled word on the unscaled word's centre
                cx = x + widths[i] / 2
                ww = self.font(fs).getlength(word)
                left = int(round(cx - ww / 2 - org[0]))
                top = int(round(yc - (asc * s) * 0.5 - org[1] - (asc * s) * 0.22))
                h_, w_ = img.shape[:2]
                a0, b0 = max(0, top), max(0, left)
                a1, b1 = min(H, top + h_), min(W, left + w_)
                if a1 > a0 and b1 > b0:
                    patch = img[a0 - top:a1 - top, b0 - left:b1 - left] * alpha
                    reg = canvas[a0:a1, b0:b1]
                    reg[..., :3] = patch[..., :3] + reg[..., :3] * (1 - patch[..., 3:4])
                    reg[..., 3:4] = patch[..., 3:4] + reg[..., 3:4] * (1 - patch[..., 3:4])
                x += widths[i] + space
        return canvas


BAND = (1180, 1620)                                             # every caption lives in these rows


def over_premul(base, layer):
    if layer is None:
        return base
    a, b = BAND
    base[a:b] = layer[a:b, :, :3] + base[a:b] * (1 - layer[a:b, :, 3:4])
    return base


if __name__ == "__main__":
    c = Captions()
    for t0, t1, ws in c.chunks:
        print(f"{t0:6.2f}-{t1:6.2f}  " + " ".join(f"{w}{'*' if g else ''}@{tw:.2f}" for w, tw, g in ws))
    os.makedirs(os.path.join(edl.ROOT, "renders/verify"), exist_ok=True)
    for s in sys.argv[1:]:
        t = float(s)
        bg = np.full((H, W, 3), 0.18, np.float32)
        img = over_premul(bg, c.render(t))
        cv2.imwrite(os.path.join(edl.ROOT, f"renders/verify/cap_{t:06.2f}.jpg"),
                    cv2.cvtColor((img * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
