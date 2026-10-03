"""Mount the flat transparent lockup onto the reel's wall, in perspective.

The wall model is measured from the reel snapshot (snapshot pixel coords):
  ceiling junction   y = 0.4625x + 108.6   (clean samples x=44..140; x>=152 is the fan blade)
  headboard top edge y = -0.0713x + 415.4
  -> horizontals on the wall converge to VP = (574.8, 374.4); verticals stay vertical.

A pinhole camera with that vanishing point fixes the wall plane's orientation.
A rectangle laid on that plane is projected back into the frame, which gives the
exact homography from the flat canvas onto the wall. Warping is done on
premultiplied alpha with 2x supersampling, so soft glows and shadow edges don't
pick up dark fringes.

  python3 tools/wall_warp.py --test 7.0          # one composited still, with the quad drawn
  python3 tools/wall_warp.py                     # all frames -> renders/wall_png/
"""
import argparse
import glob
import os

import cv2
import numpy as np

W_OUT, H_OUT = 1080, 1920
CX, CY = W_OUT / 2, H_OUT / 2
SNAP_W, SNAP_H, SNAP_TOP = 390, 696, 3.5  # snapshot has ~3.5px of UI chrome above the video


def snap_to_frame(x, y):
    return x * (W_OUT / SNAP_W), (y - SNAP_TOP) * (H_OUT / (SNAP_H - SNAP_TOP))


VP = snap_to_frame(574.8, 374.4)
WALL_REF = snap_to_frame(110, 407)  # a point on the headboard edge, i.e. on the wall plane


def wall_quad(f, center, scale, flat_size, anchor):
    """Project the flat canvas corners onto the wall. Returns (src, dst) float32 4x2."""
    dh = np.array([(VP[0] - CX) / f, (VP[1] - CY) / f, 1.0])
    dh /= np.linalg.norm(dh)
    up = np.array([0.0, 1.0, 0.0])
    dv = up - dh * np.dot(dh, up)  # image-vertical, made orthogonal to the wall horizontal
    dv /= np.linalg.norm(dv)
    n = np.cross(dh, dv)
    p0 = np.array([(WALL_REF[0] - CX) / f, (WALL_REF[1] - CY) / f, 1.0])

    def on_wall(px, py):
        r = np.array([(px - CX) / f, (py - CY) / f, 1.0])
        return r * (np.dot(n, p0) / np.dot(n, r))

    c = on_wall(*center)
    k = scale * c[2] / f  # wall units per flat pixel, so `scale` = on-screen px per flat px at the anchor
    fw, fh = flat_size
    src = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
    dst = []
    for x, y in src:
        p = c + k * (x - anchor[0]) * dh + k * (y - anchor[1]) * dv
        dst.append([f * p[0] / p[2] + CX, f * p[1] / p[2] + CY])
    return src, np.float32(dst)


def warp_frame(path, H, ss):
    bgra = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    a = bgra[:, :, 3:4]
    pm = np.concatenate([bgra[:, :, :3] * a, a], axis=2)  # premultiply before resampling
    big = cv2.warpPerspective(pm, H, (W_OUT * ss, H_OUT * ss), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out = cv2.resize(big, (W_OUT, H_OUT), interpolation=cv2.INTER_AREA)
    return out  # premultiplied BGRA float


def unpremultiply(pm):
    a = pm[:, :, 3:4]
    rgb = np.where(a > 1e-5, pm[:, :, :3] / np.maximum(a, 1e-5), 0.0)
    return np.concatenate([np.clip(rgb, 0, 1), a], axis=2)


def snapshot_background(path):
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    im = im[int(round(SNAP_TOP)):, :]
    return cv2.resize(im, (W_OUT, H_OUT), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flat", default="renders/flat_png")
    ap.add_argument("--out", default="renders/wall_png")
    ap.add_argument("--snapshot", default="assets/reel-snapshot.png")
    ap.add_argument("--f", type=float, default=1387.0, help="focal length in output px (iPhone 1x ~ 1387)")
    ap.add_argument("--cx", type=float, default=290.0, help="lockup centre, output px")
    ap.add_argument("--cy", type=float, default=730.0)
    ap.add_argument("--scale", type=float, default=0.50, help="on-screen px per flat px at the centre")
    ap.add_argument("--anchor", type=float, nargs=2, default=[539.5, 665.0], help="lockup bbox centre in the flat canvas")
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--test", type=float, default=None, help="render one composited still at this time (s)")
    ap.add_argument("--test-out", default=None)
    args = ap.parse_args()

    frames = sorted(glob.glob(os.path.join(args.flat, "*.png")))
    h0, w0 = cv2.imread(frames[0], cv2.IMREAD_UNCHANGED).shape[:2]
    src, dst = wall_quad(args.f, (args.cx, args.cy), args.scale, (w0, h0), args.anchor)
    H = cv2.getPerspectiveTransform(src, dst * args.ss)
    print("flat canvas -> wall quad (output px):")
    for s, d in zip(src, dst):
        print(f"  ({s[0]:6.0f},{s[1]:6.0f}) -> ({d[0]:7.1f},{d[1]:7.1f})")

    if args.test is not None:
        i = min(len(frames) - 1, int(round(args.test * 30)))
        pm = warp_frame(frames[i], H, args.ss)
        bg = snapshot_background(args.snapshot)
        comp = pm[:, :, :3] + bg * (1 - pm[:, :, 3:4])
        img = (comp * 255).clip(0, 255).astype(np.uint8)
        cv2.polylines(img, [dst.astype(np.int32).reshape(-1, 1, 2)], True, (60, 60, 255), 1, cv2.LINE_AA)
        out = args.test_out or f"/tmp/wall_test_{args.test:.2f}.jpg"
        cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("test still ->", out)
        return

    os.makedirs(args.out, exist_ok=True)
    for i, p in enumerate(frames):
        res = unpremultiply(warp_frame(p, H, args.ss))
        cv2.imwrite(os.path.join(args.out, f"frame_{i + 1:06d}.png"), (res * 255 + 0.5).clip(0, 255).astype(np.uint8))
        if i % 60 == 0:
            print(f"  warped {i + 1}/{len(frames)}")
    print(f"done: {len(frames)} frames -> {args.out}")


if __name__ == "__main__":
    main()
