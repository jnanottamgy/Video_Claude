"""Composite the S.H.E.L.F reveal onto the real (handheld) clip — a drop-in replacement shot.

Uses renders/real/camera.npz from solve_camera.py: the camera K, both wall planes, and per-frame
wall homographies H_wall[n] (frame-0 px -> frame-n px). Each sign is laid on its wall in frame 0
(placement below), so for frame n the flat canvas maps by  H_wall[n] @ P_wall.

Integration with the footage:
  - exposure: the signs follow the camera's auto-exposure (wall-patch brightness vs frame 0)
  - sharpness: a slight blur so CG edges match the footage's softness (measured, see --measure)
  - grain: per-frame noise matched to the footage's own noise on a flat wall patch
  - levels: the clip is FULL-range BT.709; output keeps it, so the swapped clip matches its neighbours

  python3 tools/composite_real.py --test           # placement check at worst-case frames
  python3 tools/composite_real.py --measure        # footage sharpness / noise / exposure
  python3 tools/composite_real.py                  # full render -> renders/real/SHELF_IMG_9596.mp4
"""
import argparse
import glob
import os
import subprocess

import cv2
import numpy as np

SRC = "renders/real/source.MOV"
OUT = "renders/real/SHELF_IMG_9596.mp4"
W, H, FPS = 1080, 1920, 30
CAM = np.load("renders/real/camera.npz")
K, KI = CAM["K"], np.linalg.inv(CAM["K"])
PLANES = {"left": (CAM["N_L"], float(CAM["D_L"])), "back": (CAM["N_B"], float(CAM["D_B"]))}
HW = {"left": CAM["H_left"], "back": CAM["H_back"]}
VP = {"left": (1547.0, 1000.0), "back": (-2123.0, 1000.0)}

# name: (flat frames, wall, centre in frame-0 px, on-screen px per flat px at centre, anchor = ink-bbox centre in flat px)
LAYERS = {
    "shelf": ("renders/flat_png", "left", (285, 712), 0.60, (539.5, 665.0)),
    "launch": ("../shelf-launch-soon/renders/flat_png", "back", (890, 880), 0.205, (530.0, 330.0)),
}
WALL_PATCH = (430, 560, 520, 640)      # x0,y0,x1,y1: blank left wall, frame 0 — exposure + noise reference
DECODE_VF = "scale=in_color_matrix=bt709:in_range=full"
SFX = "renders/out/SHELF_sfx.wav"
CLIP_AUDIO = "renders/real/clip_audio.wav"
# Measured on this clip (--measure): edges rise 10-90% over 2.0 px (sigma ~0.78) vs ~1 px for the render;
# extra blur = sqrt(0.78^2 - 0.40^2). Grain: high-pass std ~0.6/255 on blank wall. Exposure: steady (+-0.9%).
MATCH_SIGMA = 0.65
GRAIN = np.array([0.57, 0.55, 0.65]) / 255.0


def ray(p):
    return KI @ np.array([p[0], p[1], 1.0])


def basis(wall):
    n, d = PLANES[wall]
    h = ray(VP[wall]); h /= np.linalg.norm(h)
    if VP[wall][0] < K[0, 2]:
        h = -h
    down = np.array([0.0, 1.0, 0.0]); down -= h * (h @ down); down /= np.linalg.norm(down)
    return h, down, n, d


def placement(wall, center, scale, size, anchor):
    right, down, n, d = basis(wall)
    r = ray(center); c = r * (d / (n @ r))
    k = scale * c[2] / K[0, 0]
    fw, fh = size
    src = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
    dst = []
    for x, y in src:
        p = c + k * (x - anchor[0]) * right + k * (y - anchor[1]) * down
        q = K @ p; dst.append(q[:2] / q[2])
    return cv2.getPerspectiveTransform(src, np.float32(dst))


def footage():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", DECODE_VF, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


def footage_frame(n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"select=eq(n\\,{n}),{DECODE_VF}", "-vframes", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)


def flat_premul(path):
    bgra = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    rgb, a = bgra[:, :, 2::-1], bgra[:, :, 3:4]
    return np.concatenate([rgb * a, a], axis=2)


def layer_stack(i, n, layers, ss=2):
    acc = np.zeros((H, W, 4), np.float32)
    S = np.diag([ss, ss, 1.0])
    for frames, wall, P in layers:
        Hn = S @ HW[wall][n] @ P
        big = cv2.warpPerspective(flat_premul(frames[i]), Hn, (W * ss, H * ss), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        lay = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
        acc = lay + acc * (1 - lay[:, :, 3:4])
    return acc


def build_layers():
    out = []
    for name, (flat, wall, center, scale, anchor) in LAYERS.items():
        frames = sorted(glob.glob(os.path.join(flat, "*.png")))
        h0, w0 = cv2.imread(frames[0], cv2.IMREAD_UNCHANGED).shape[:2]
        out.append((frames, wall, placement(wall, center, scale, (w0, h0), anchor)))
    return out


def ink_bbox(stack):
    ys, xs = np.where(stack[:, :, 3] > 0.03)
    return xs.min(), xs.max(), ys.min(), ys.max()


def test(out_dir):
    """Placement check: the held state of both signs, on the frames where the camera is at its extremes."""
    layers = build_layers()
    hold = int(8.0 * FPS)                        # everything is on the wall by 8s
    drift = np.array([cv2.perspectiveTransform(np.float32([[[300, 750]]]), h)[0, 0] for h in HW["left"]])
    picks = sorted({0, int(np.argmax(drift[:, 0])), int(np.argmin(drift[:, 1])), int(np.argmax(drift[:, 1])), len(drift) - 1})
    tiles = []
    for n in picks:
        fr = footage_frame(n).astype(np.float32) / 255
        for k, (frames, wall, P) in enumerate(layers):
            st = layer_stack(hold, n, [(frames, wall, P)])
            x0, x1, y0, y1 = ink_bbox(st)
            print(f"  frame {n:3d}  {list(LAYERS)[k]:6s} ink x {x0:4d}..{x1:4d}  y {y0:4d}..{y1:4d}")
        st = layer_stack(hold, n, layers)
        comp = st[:, :, :3] + fr * (1 - st[:, :, 3:4])
        img = cv2.cvtColor((comp * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        cv2.putText(img, f"frame {n}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 3)
        tiles.append(cv2.resize(img, (360, 640), interpolation=cv2.INTER_AREA))
    cv2.imwrite(os.path.join(out_dir, "real_placement.jpg"), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print("frames shown:", picks)


def render():
    layers = build_layers()
    gain = np.load("renders/real/exposure.npy") if os.path.exists("renders/real/exposure.npy") else None
    n_frames = len(HW["left"])
    dur = n_frames / FPS
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-",
         # sound: the reveal's effects over the clip's own room tone (-54 LUFS), both from t=0
         "-i", SFX, "-i", CLIP_AUDIO,
         "-filter_complex", f"[1:a]atrim=0:{dur:.4f},asetpts=PTS-STARTPTS[s];[2:a]atrim=0:{dur:.4f},asetpts=PTS-STARTPTS[r];"
                            f"[s][r]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.84:level=disabled[a]",
         "-map", "0:v", "-map", "[a]",
         # keep the clip's FULL-range BT.709 so the swapped shot matches its neighbours
         "-vf", "scale=out_color_matrix=bt709:out_range=full,format=yuv420p",
         "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high",
         "-color_range", "pc", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-c:a", "aac", "-b:a", "256k", "-t", f"{dur:.4f}", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    for n, fr in enumerate(footage()):
        st = layer_stack(n, n, layers)
        st = cv2.GaussianBlur(st, (0, 0), MATCH_SIGMA)            # premultiplied: blurs colour and coverage together
        if gain is not None:
            st[:, :, :3] *= gain[n].astype(np.float32)
        base = fr.astype(np.float32) / 255.0
        out = st[:, :, :3] + base * (1.0 - st[:, :, 3:4])
        rng = np.random.default_rng(1000 + n)                      # fresh grain each frame, same every render
        out += rng.standard_normal(out.shape).astype(np.float32) * GRAIN.astype(np.float32) * st[:, :, 3:4]
        enc.stdin.write((out * 255.0 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
        if n % 60 == 0:
            print(f"  composited {n + 1}/{n_frames}")
    enc.stdin.close(); enc.wait()
    print("->", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--out-dir", default="/tmp")
    a = ap.parse_args()
    if a.test:
        test(a.out_dir)
    else:
        render()
