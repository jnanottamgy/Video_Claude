"""Mount flat transparent renders onto the walls of the reel, in perspective.

One pinhole camera, two walls, both measured from the reel snapshot (snapshot px):

  LEFT wall (S.H.E.L.F)       ceiling junction y = 0.4625x + 108.6   (x>=152 is the fan blade)
                              headboard edge   y = -0.0713x + 415.4
                              -> VP1 = (574.8, 374.4)
  BACK wall (LAUNCHING SOON)  pelmet edge      y = -0.1001x + 295.8
                              soffit edge      slope -0.146 (two far-end outliers dropped)
                              -> VP2 = (-780, 374.4), on the same horizon

The walls meet at a right angle, which fixes the focal length:
  f^2 = -(VP1 - c) . (VP2 - c)   ->  f ~ 1684 px in the 1080x1920 frame.
The left wall passes through a point on the headboard; the back wall passes through
the inner corner (x = 290), which lies on the left wall — so the planes meet exactly
where the real walls do.

Each flat canvas is laid on its wall as a rectangle and projected back into the frame,
giving an exact homography. Warping is done on premultiplied alpha with 2x
supersampling, so soft glows and shadow edges don't pick up dark fringes.

  python3 tools/wall_warp.py --test 7.0     # one composited still with layer outlines
  python3 tools/wall_warp.py                # all frames -> renders/wall_png/
"""
import argparse
import glob
import os

import cv2
import numpy as np

W_OUT, H_OUT = 1080, 1920
CX, CY = W_OUT / 2, H_OUT / 2
SNAP_W, SNAP_H, SNAP_TOP = 390, 696, 3.5  # snapshot carries ~3.5px of UI chrome above the video


def snap_to_frame(x, y):
    return np.array([x * (W_OUT / SNAP_W), (y - SNAP_TOP) * (H_OUT / (SNAP_H - SNAP_TOP))])


VP1 = snap_to_frame(574.8, 374.4)
VP2 = snap_to_frame(-780.0, 374.4)
C = np.array([CX, CY])
F = float(np.sqrt(-np.dot(VP1 - C, VP2 - C)))

HEADBOARD = snap_to_frame(110, 407)  # on the left wall
CORNER = snap_to_frame(290, 330)     # on both walls

# name: (flat frames dir, wall, centre in frame px, on-screen px per flat px at centre, anchor in flat px)
LAYERS = {
    "shelf": ("renders/flat_png", "left", (298, 748), 0.60, (539.5, 665.0)),
    "launch": ("../shelf-launch-soon/renders/flat_png", "back", (932, 905), 0.235, (530.0, 330.0)),
}


def ray(p):
    return np.array([(p[0] - CX) / F, (p[1] - CY) / F, 1.0])


def wall_basis(vp):
    """Unit vectors on the wall: `right` maps to image-rightwards, `down` to image-down."""
    h = ray(vp)
    h /= np.linalg.norm(h)
    if vp[0] < CX:  # this wall recedes to the left; flip so +x still reads left-to-right
        h = -h
    down = np.array([0.0, 1.0, 0.0])
    down = down - h * np.dot(h, down)
    down /= np.linalg.norm(down)
    return h, down, np.cross(h, down)


def intersect(pixel, n, p0):
    r = ray(pixel)
    return r * (np.dot(n, p0) / np.dot(n, r))


LEFT = wall_basis(VP1)
LEFT_P0 = ray(HEADBOARD)  # depth 1 by convention; everything else is relative to it
BACK = wall_basis(VP2)
BACK_P0 = intersect(CORNER, LEFT[2], LEFT_P0)  # the corner point, on the left wall
WALLS = {"left": (LEFT, LEFT_P0), "back": (BACK, BACK_P0)}


def wall_quad(wall, center, scale, flat_size, anchor):
    (right, down, n), p0 = WALLS[wall]
    c = intersect(center, n, p0)
    k = scale * c[2] / F  # wall units per flat px, so `scale` = on-screen px per flat px at the centre
    fw, fh = flat_size
    src = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
    dst = []
    for x, y in src:
        p = c + k * (x - anchor[0]) * right + k * (y - anchor[1]) * down
        dst.append([F * p[0] / p[2] + CX, F * p[1] / p[2] + CY])
    return src, np.float32(dst)


def load_premultiplied(path):
    bgra = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    a = bgra[:, :, 3:4]
    return np.concatenate([bgra[:, :, :3] * a, a], axis=2)


def warp(pm, H, ss):
    big = cv2.warpPerspective(pm, H, (W_OUT * ss, H_OUT * ss), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return cv2.resize(big, (W_OUT, H_OUT), interpolation=cv2.INTER_AREA)


def over(top, bottom):
    return top + bottom * (1.0 - top[:, :, 3:4])


def unpremultiply(pm):
    a = pm[:, :, 3:4]
    rgb = np.where(a > 1e-5, pm[:, :, :3] / np.maximum(a, 1e-5), 0.0)
    return np.concatenate([np.clip(rgb, 0, 1), a], axis=2)


def snapshot_background(path):
    im = cv2.imread(path, cv2.IMREAD_COLOR)[int(round(SNAP_TOP)):, :]
    return cv2.resize(im, (W_OUT, H_OUT), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="renders/wall_png")
    ap.add_argument("--snapshot", default="assets/reel-snapshot.png")
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--test", type=float, default=None, help="render one composited still at this time (s)")
    ap.add_argument("--test-out", default="/tmp/wall_test.jpg")
    args = ap.parse_args()

    print(f"camera: f = {F:.0f}px  VP1 = ({VP1[0]:.0f},{VP1[1]:.0f})  VP2 = ({VP2[0]:.0f},{VP2[1]:.0f})")
    print(f"walls meet at {np.degrees(np.arccos(abs(np.dot(LEFT[0], BACK[0])))):.1f} deg")

    layers = []
    for name, (flat, wall, center, scale, anchor) in LAYERS.items():
        frames = sorted(glob.glob(os.path.join(flat, "*.png")))
        h0, w0 = cv2.imread(frames[0], cv2.IMREAD_UNCHANGED).shape[:2]
        src, dst = wall_quad(wall, center, scale, (w0, h0), anchor)
        layers.append((name, frames, cv2.getPerspectiveTransform(src, dst * args.ss), dst))
        print(f"  {name:7s} -> {wall} wall, quad " + " ".join(f"({x:.0f},{y:.0f})" for x, y in dst))
    n = min(len(fr) for _, fr, _, _ in layers)

    def frame(i):
        acc = np.zeros((H_OUT, W_OUT, 4), np.float32)
        for _, frames, H, _ in layers:
            acc = over(warp(load_premultiplied(frames[i]), H, args.ss), acc)
        return acc

    if args.test is not None:
        pm = frame(min(n - 1, int(round(args.test * 30))))
        comp = pm[:, :, :3] + snapshot_background(args.snapshot) * (1 - pm[:, :, 3:4])
        img = (comp * 255).clip(0, 255).astype(np.uint8)
        for _, _, _, dst in layers:
            cv2.polylines(img, [dst.astype(np.int32).reshape(-1, 1, 2)], True, (60, 60, 255), 1, cv2.LINE_AA)
        cv2.imwrite(args.test_out, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("test still ->", args.test_out)
        return

    os.makedirs(args.out, exist_ok=True)
    for i in range(n):
        res = unpremultiply(frame(i))
        cv2.imwrite(os.path.join(args.out, f"frame_{i + 1:06d}.png"), (res * 255 + 0.5).clip(0, 255).astype(np.uint8))
        if i % 75 == 0:
            print(f"  composited {i + 1}/{n}")
    print(f"done: {n} frames -> {args.out}")


if __name__ == "__main__":
    main()
