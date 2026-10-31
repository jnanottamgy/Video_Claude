"""A karaoke-style guide for re-recording HK Vinay's voice-over on the reel's exact timing.

The reel plays at the top (so he can see his own lips for the on-camera lines). Below it, his lines appear one at a
time in big type; each word fills with gold exactly when he said it in the reel (tools/karaoke_timing.py), at the
same speed. A 3-2-1 count-in (with beeps in the guide version) leads into the first word; three dots fill before
every following line; the next line is previewed underneath.

  python3 tools/karaoke.py  ->  renders/deliver/TAXWISE_VO_karaoke_with_guide.mp4  his original voice as a guide
                                                                                    (for earphones) + count-in beeps
                                renders/deliver/TAXWISE_VO_karaoke_silent.mp4      the same, no sound at all
The video runs PRE seconds of count-in, then the reel's 52 s, then an end card.
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import dialogue as Dg  # noqa: E402
import edl  # noqa: E402
import karaoke_timing as KT  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
PRE, POST = 4.0, 2.0
TOTAL = PRE + edl.DURATION + POST
FONT = os.path.join(edl.ROOT, "design/fonts/montserrat-latin-{}-normal.woff2")
BG = (11, 22, 38)
GOLD, WHITE, DIM, GREY = (236, 200, 120), (240, 238, 232), (110, 122, 140), (150, 158, 172)
OUT = os.path.join(edl.ROOT, "renders/deliver")
PIC = os.path.join(edl.ROOT, "renders/picture/picture.mp4")
LINES = KT.lines()
FIRST = LINES[0]["words"][0]["s"]                      # the first word (reel time)
BEEPS = [PRE + FIRST - 3, PRE + FIRST - 2, PRE + FIRST - 1]

fonts = {}


def font(weight, size):
    k = (weight, size)
    if k not in fonts:
        fonts[k] = ImageFont.truetype(FONT.format(weight), size)
    return fonts[k]


def activations():
    """Reel time at which each line becomes the current one."""
    act = [-PRE]
    for i in range(1, len(LINES)):
        prev_end = LINES[i - 1]["words"][-1]["e"]
        act.append(max(LINES[i]["words"][0]["s"] - 1.6, prev_end + 0.15))
    return act


ACT = activations()


def layout(words, f, maxw=960, gap=None):
    """Greedy word wrap -> [(x, y_line, word)] with centred lines."""
    space = f.getlength(" ")
    rows, row, w = [], [], 0.0
    for wd in words:
        ww = f.getlength(wd["w"])
        if row and w + space + ww > maxw:
            rows.append((row, w))
            row, w = [], 0.0
        w = w + (space if row else 0) + ww
        row.append(wd)
    if row:
        rows.append((row, w))
    out = []
    for r, (row, rw) in enumerate(rows):
        x = (W - rw) / 2
        for wd in row:
            out.append((x, r, wd))
            x += f.getlength(wd["w"]) + space
    return out, len(rows)


def draw_line(img, d, line, t, y0):
    f = font(800, 66)
    lh = 84
    items, nrows = layout(line["words"], f)
    for x, r, wd in items:
        y = y0 + r * lh
        if t >= wd["e"]:
            d.text((x, y), wd["w"], font=f, fill=GOLD)
        elif t < wd["s"]:
            d.text((x, y), wd["w"], font=f, fill=WHITE if t > wd["s"] - 2.5 else GREY)
        else:                                            # the word being said: gold sweeps across it
            d.text((x, y), wd["w"], font=f, fill=WHITE)
            u = (t - wd["s"]) / max(wd["e"] - wd["s"], 1e-3)
            ww = f.getlength(wd["w"])
            layer = Image.new("RGBA", (int(ww) + 8, lh + 20), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((0, 0), wd["w"], font=f, fill=GOLD + (255,))
            cut = int(np.clip(u, 0, 1) * (ww + 4))
            if cut > 0:
                img.paste(layer.crop((0, 0, cut, lh + 20)), (int(x), int(y)), layer.crop((0, 0, cut, lh + 20)))
    return nrows * lh


def frame(n, pic):
    t = n / FPS - PRE                                    # reel time
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # the reel, small, at the top
    if pic is not None:
        p = Image.fromarray(pic).resize((540, 960), Image.BILINEAR)
        if t < 0 or t >= edl.DURATION:
            p = Image.eval(p, lambda v: int(v * 0.45))
        img.paste(p, (270, 60))
        d.rectangle((268, 58, 811, 1021), outline=(120, 100, 60), width=2)
    # the current line
    i = max(k for k in range(len(LINES)) if ACT[k] <= t) if t >= ACT[0] else 0
    line = LINES[i]
    first = line["words"][0]["s"]
    on_cam = line["kind"] == "A"
    hdr = f"LINE {i + 1} OF {len(LINES)}  ·  " + ("ON CAMERA: MATCH YOUR LIPS" if on_cam else "VOICE-OVER")
    f_h = font(600, 30)
    d.text(((W - f_h.getlength(hdr)) / 2, 1062), hdr, font=f_h, fill=GOLD if on_cam else (150, 190, 235))
    # count-in: three dots fill over the 1.5 s before the line's first word
    if first - 1.6 <= t < first:
        for k in range(3):
            lit = t >= first - 1.5 + 0.5 * k
            cx = W / 2 + (k - 1) * 46
            d.ellipse((cx - 12, 1118, cx + 12, 1142), fill=GOLD if lit else (60, 70, 88))
    if t < 0:                                            # the opening countdown, in sync with the beeps
        rem = FIRST - t
        msg = "GET READY" if rem > 3.0 else str(int(np.ceil(rem - 1e-6)))
        f_c = font(800, 120 if rem <= 3.0 else 64)
        d.text(((W - f_c.getlength(msg)) / 2, 1500), msg, font=f_c, fill=WHITE)
    hgt = draw_line(img, d, line, t, 1170)
    # the next line, previewed
    if i + 1 < len(LINES) and t >= 0:
        nxt = " ".join(w["w"] for w in LINES[i + 1]["words"])
        f_n = font(500, 32)
        words, s = nxt.split(), ""
        for w in words:
            if f_n.getlength(s + " " + w + " ...") > 900:
                s += " ..."
                break
            s = (s + " " + w).strip()
        msg = "NEXT:  " + s
        d.text(((W - f_n.getlength(msg)) / 2, max(1210 + hgt, 1650)), msg, font=f_n, fill=DIM)
    if t >= edl.DURATION - 0.0:
        f_e = font(800, 72)
        for k, msg in enumerate(("THAT'S IT", "STOP RECORDING")):
            d.text(((W - f_e.getlength(msg)) / 2, 1450 + k * 100), msg, font=f_e, fill=GOLD if k == 0 else WHITE)
    # progress through the reel + timecode
    u = np.clip(t / edl.DURATION, 0, 1)
    d.rectangle((60, 1868, 1020, 1876), fill=(40, 50, 66))
    d.rectangle((60, 1868, 60 + int(960 * u), 1876), fill=GOLD)
    tc = f"{max(t, 0):5.1f} s"
    f_t = font(600, 26)
    d.text((W - 60 - f_t.getlength(tc), 1828), tc, font=f_t, fill=GREY)
    return np.asarray(img)


def guide_audio():
    """His original voice, cut as in the reel, shifted by PRE; three count-in beeps."""
    ref = Dg.load_src()
    n = int(TOTAL * SR)
    a = np.zeros((n, 2))
    for s in edl.SEGMENTS:
        x = ref[int(s["src"] * SR):int(s["src_end"] * SR)].copy()
        k = int(0.02 * SR)
        x[:k] *= np.linspace(0, 1, k)[:, None]
        x[-k:] *= np.linspace(1, 0, k)[:, None]
        i = int((s["out"] + PRE) * SR)
        a[i:i + len(x)] += x
    a *= 0.25 / max(1e-6, np.sqrt(np.mean(a[np.abs(a).max(1) > 1e-4] ** 2)) * 4)
    for t in BEEPS:
        m = int(0.09 * SR)
        tt = np.arange(m) / SR
        b = np.sin(2 * np.pi * 1000 * tt) * np.minimum(1, tt / 0.005) * np.minimum(1, (0.09 - tt) / 0.01) * 0.3
        i = int(t * SR)
        a[i:i + m] += b[:, None]
    return np.clip(a, -0.98, 0.98)


def main():
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "karaoke_guide.wav")
    sf.write(wav, guide_audio().astype(np.float32), SR, subtype="PCM_16")
    silent = os.path.join(OUT, "TAXWISE_VO_karaoke_silent.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", PIC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)

    def read():
        buf = dec.stdout.read(W * H * 3)
        return np.frombuffer(buf, np.uint8).reshape(H, W, 3) if len(buf) == W * H * 3 else None

    first = read()                                       # reel frame 0: shown (dimmed) during the count-in
    cur, idx = first, 0
    for n in range(int(round(TOTAL * FPS))):
        k = n - int(round(PRE * FPS))                    # the reel frame for this output frame
        if 0 <= k < edl.TOTAL:
            while idx < k:
                nxt = read()
                if nxt is None:
                    break
                cur, idx = nxt, idx + 1
            pic = cur
        elif k < 0:
            pic = first
        else:
            pic = cur
        enc.stdin.write(frame(n, pic).tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()
    guide = os.path.join(OUT, "TAXWISE_VO_karaoke_with_guide.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", guide], check=True)
    os.remove(wav)
    print("->", guide, "and", silent, f"({TOTAL:.1f} s)")


if __name__ == "__main__":
    main()
