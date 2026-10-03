"""Make the wall overlay usable in phone editors, which can't read transparent video.

Two plain H.264 MP4 routes from the same RGBA frames (renders/wall_png):

1. GREEN SCREEN — the overlay over pure green, keyed out in the editor.
   REJECTED for this overlay (kept behind --with-greenscreen for comparison):
   simulated keying of the encoded file averaged ~12.5 levels of error vs ~2.3
   for the two-layer route, and visibly turned the translucent glass mark
   GREEN, dropped its halo, and ate thin tagline strokes. A keyer has no notion
   of partial transparency, and this overlay is full of it.

2. TWO-LAYER BLEND — exact. Any alpha-over composite  out = P + (1-a)W
   (P = premultiplied colour, W = the footage) can be split into two layers a
   phone editor *can* do, with no alpha at all:
       layer 1, blend MULTIPLY:  M = (1 - a) / (1 - P)     (white where empty)
       layer 2, blend SCREEN:    S = P                     (black where empty)
   because  screen(W*M, S) = 1 - (1 - W*M)(1 - S) = P + (1-a)W.   (per channel)
   Glows, shadows, fades and blur all survive.

  python3 tools/phone_versions.py            # encode both routes
  python3 tools/phone_versions.py --qc       # simulate both workflows on the snapshot, measure error
"""
import argparse
import glob
import os
import subprocess

import cv2
import numpy as np

FRAMES = "renders/wall_png"
OUT = "renders/out"
SFX = "renders/out/SHELF_sfx.wav"
GREEN = np.array([0.0, 1.0, 0.0])  # RGB
H264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def rgba(path):
    bgra = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float64) / 255.0
    return bgra[:, :, 2::-1], bgra[:, :, 3:4]  # RGB straight colour, alpha


def layers(c, a):
    p = c * a
    green = p + (1 - a) * GREEN
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(1 - p > 1e-6, (1 - a) / (1 - p), 1.0)
    return green, np.clip(m, 0, 1), p


def encoder(path, audio):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
           "-framerate", "30", "-i", "-"]
    if audio:
        cmd += ["-i", SFX, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
    return subprocess.Popen(cmd + H264 + ["-movflags", "+faststart", path], stdin=subprocess.PIPE)


def to8(x):
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()


def encode(with_green=False):
    frames = sorted(glob.glob(os.path.join(FRAMES, "*.png")))
    enc = {
        "mul": encoder(f"{OUT}/SHELF_overlay_layer1_MULTIPLY.mp4", audio=True),
        "scr": encoder(f"{OUT}/SHELF_overlay_layer2_SCREEN.mp4", audio=False),  # sound on one layer only
    }
    if with_green:
        enc["green"] = encoder(f"{OUT}/SHELF_overlay_GREENSCREEN.mp4", audio=True)
    for i, f in enumerate(frames):
        g, m, s = layers(*rgba(f))
        for k, x in (("green", g), ("mul", m), ("scr", s)):
            if k in enc:
                enc[k].stdin.write(to8(x))
    for p in enc.values():
        p.stdin.close()
        p.wait()
    print(f"encoded {len(frames)} frames x {len(enc)} files")


def decode(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).astype(np.float64) / 255.0


def chroma_key(img, tol=0.30, soft=0.12):
    """A typical phone-editor keyer: distance from the key colour in CbCr, plus green-spill clamp."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    cb = -0.1146 * r - 0.3854 * g + 0.5 * b
    cr = 0.5 * r - 0.4542 * g - 0.0458 * b
    gcb, gcr = -0.3854, -0.4542
    d = np.sqrt((cb - gcb) ** 2 + (cr - gcr) ** 2)
    a = np.clip((d - tol) / soft, 0, 1)[..., None]
    despill = img.copy()
    despill[..., 1] = np.minimum(g, np.maximum(r, b))
    return despill, a


def qc(snapshot, out_dir):
    import sys
    sys.path.insert(0, "tools")
    import wall_warp as w
    bg = w.snapshot_background(snapshot)[:, :, ::-1]  # RGB
    frames = sorted(glob.glob(os.path.join(FRAMES, "*.png")))
    tiles = []
    for t in (0.85, 3.6, 8.0):
        c, a = rgba(frames[min(len(frames) - 1, int(round(t * 30)))])
        ideal = c * a + (1 - a) * bg
        # route 2: exactly what an editor does — multiply layer, then screen layer — from the ENCODED files
        m = decode(f"{OUT}/SHELF_overlay_layer1_MULTIPLY.mp4", t)
        s = decode(f"{OUT}/SHELF_overlay_layer2_SCREEN.mp4", t)
        blend = 1 - (1 - bg * m) * (1 - s)
        # route 1: key the ENCODED green-screen file, then composite (if it was built)
        gpath = f"{OUT}/SHELF_overlay_GREENSCREEN.mp4"
        if os.path.exists(gpath):
            gfill, ga = chroma_key(decode(gpath, t))
            keyed = gfill * ga + (1 - ga) * bg
        else:
            keyed = ideal * 0
        region = a[..., 0] > 0.01  # judge only where the overlay actually is
        for name, x in (("two-layer", blend), ("greenscreen", keyed)):
            err = np.abs(x - ideal)[region] * 255
            print(f"  t={t:4.2f}s  {name:12s} vs exact: mean {err.mean():5.2f}  p99 {np.percentile(err, 99):5.1f}  "
                  f"max {err.max():5.1f}  (0-255 levels, over {region.sum()} overlay px)")
        crop = (slice(380, 1060), slice(60, 1080))
        row = [ideal, blend, keyed]
        tiles.append(np.hstack([cv2.resize((x[crop] * 255).clip(0, 255).astype(np.uint8), (340, 227)) for x in row]))
    sheet = np.vstack(tiles)[:, :, ::-1]
    cv2.imwrite(os.path.join(out_dir, "phone_routes_qc.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("sheet columns: exact | two-layer (Multiply+Screen) | green screen keyed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", action="store_true")
    ap.add_argument("--snapshot", default="assets/reel-snapshot.png")
    ap.add_argument("--qc-dir", default="/tmp")
    ap.add_argument("--with-greenscreen", action="store_true", help="also encode the rejected green-screen route")
    args = ap.parse_args()
    qc(args.snapshot, args.qc_dir) if args.qc else encode(args.with_greenscreen)
