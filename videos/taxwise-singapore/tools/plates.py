"""Clean background plates and desk masks for the four on-camera shots (the camera is locked off in each).

For each shot: the mean of every sampled frame's background pixels (where the person matte is ~0, his
outline dilated), so the wall, window and desk come out without him; the few pixels he never uncovers are
inpainted. The compositor uses the plate to pull the bright wall out of his hair edges (decontamination)
when the room is re-lit navy, and the desk mask to grade the desk as dark wood instead of re-lighting it.

  python3 tools/plates.py   ->  renders/plates/plate_<shot>.png, desk_<shot>.png
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

W, H = edl.W, edl.H
OUT = os.path.join(edl.ROOT, "renders/plates")
MATTES = os.path.join(edl.ROOT, "renders/mattes")
# source frame ranges actually shown (from edl.PICTURE), per shot
RANGES = {"A": (39, 222), "B": (284, 476), "E": (1248, 1452), "F": (1500, 1677)}


def frames(a, b, step):
    """Source frames a..b (every `step`) as full-range RGB uint8."""
    out = {}
    want = set(range(a, b, step))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0, a - 0.01) / edl.FPS:.6f}", "-i", edl.SRC,
                          "-frames:v", str(b - a), "-vf", "scale=in_color_matrix=bt709:in_range=tv:out_range=full",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    for f in range(a, b):
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        if f in want:
            out[f] = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.stdout.close()
    p.wait()
    return out


def plate(shot):
    a, b = RANGES[shot]
    fr = frames(a, b, 4)
    acc = np.zeros((H, W, 3), np.float64)
    wsum = np.zeros((H, W), np.float64)
    for f, img in fr.items():
        m = cv2.imread(os.path.join(MATTES, f"f_{f:05d}.png"), cv2.IMREAD_GRAYSCALE)
        if m is None:
            continue
        person = cv2.dilate((m > 8).astype(np.uint8), np.ones((25, 25), np.uint8))
        w = 1.0 - person
        acc += img * w[..., None]
        wsum += w
    hole = (wsum < 0.5).astype(np.uint8)
    pl = (acc / np.maximum(wsum, 1)[..., None]).clip(0, 255).astype(np.uint8)
    if hole.any():
        pl = cv2.inpaint(pl, hole * 255, 9, cv2.INPAINT_TELEA)
    return pl, hole


def _ransac(xs, ys, tol, seed=1, minsep=60):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(800):
        i, j = rng.choice(len(xs), 2, replace=False)
        if abs(xs[i] - xs[j]) < minsep:
            continue
        a = (ys[j] - ys[i]) / (xs[j] - xs[i])
        b = ys[i] - a * xs[i]
        inl = np.abs(ys - (a * xs + b)) < tol
        if best is None or inl.sum() > best[0]:
            best = (inl.sum(), inl)
    return np.polyfit(xs[best[1]], ys[best[1]], 1)


def desk(pl):
    """The desk: everything below the BACK edge of its top, a straight line in each locked-off shot.
    - Its slope: the desk's front edge (glossy top -> darker front panel), a long clean line found as the
      strongest luminance drop per column, RANSAC-fitted. The back edge runs parallel to it.
    - Its height: the columns where bare wall meets the glossy top with nothing on the desk in between
      (14 px of bright neutral wall right above the first glossy-orange pixel).
    Below it the desk top and front are graded as wood; above it the room is re-lit. A soft 16 px feather
    sitting a little low, so any error reads as shadow at the back of the desk."""
    f = pl.astype(np.float32)
    lum = f @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rb = f[..., 0] - f[..., 2]
    gl = cv2.GaussianBlur(lum, (0, 0), 1.5)
    g = np.zeros_like(gl)
    g[2:-2] = gl[4:] - gl[:-4]
    xs, ys = [], []
    for x in range(0, 650, 3):
        seg = g[1395:1470, x]
        k = int(np.argmin(seg))
        if seg[k] < -14:
            xs.append(x)
            ys.append(1395 + k)
    a, fb = _ransac(np.array(xs, float), np.array(ys, float), 3)
    pts = []
    for x in range(380, 700, 2):
        crb, cl = rb[1300:1440, x], lum[1300:1440, x]
        idx = np.nonzero((crb > 38) & (f[1300:1440, x, 0] > 120))[0]
        if len(idx):
            k = idx[0]
            if k >= 16 and (crb[k - 16:k - 2] < 26).all() and (cl[k - 16:k - 2] > 150).all():
                pts.append((x, 1300 + k))
    pts = np.array(pts, float)
    b = float(np.median(pts[:, 1] - a * pts[:, 0]))
    edge = a * np.arange(W) + b
    yy = np.arange(H)[:, None]
    u = np.clip((yy - (edge[None, :] - 4)) / 16.0, 0, 1)
    m = u * u * (3 - 2 * u)
    print(f"  desk back edge: y = {a:.4f} x + {b:.1f} (front edge + {fb - b:.0f} px; {len(pts)} clean columns)")
    return (m * 255).clip(0, 255).astype(np.uint8)


def main():
    os.makedirs(OUT, exist_ok=True)
    for shot in RANGES:
        pl, hole = plate(shot)
        cv2.imwrite(os.path.join(OUT, f"plate_{shot}.png"), cv2.cvtColor(pl, cv2.COLOR_RGB2BGR))
        cv2.imwrite(os.path.join(OUT, f"desk_{shot}.png"), desk(pl))
        print(f"plate {shot}: {hole.mean() * 100:.2f}% never uncovered (inpainted)")


if __name__ == "__main__":
    main()
