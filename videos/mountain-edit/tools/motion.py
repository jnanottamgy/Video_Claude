"""Motion in a source range, frame by frame: the camera's pan (median flow) and the moving object's motion
(flow of the pixels that move against the camera), with where that object is.
  python3 tools/motion.py CLIP T0 T1 [STEP]   (display coordinates normalised 0..1; flow in px/frame at 480 px wide)"""
import subprocess, sys
import cv2, numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import media

clip, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
step = float(sys.argv[4]) if len(sys.argv) > 4 else 1 / 30
i = media.info(clip)
w = 480 if i["w"] >= i["h"] else 270
h = int(round(i["h"] * w / i["w"] / 2) * 2)
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", i["path"], "-vf",
                      f"fps={1 / step:.4f},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
print(f"{clip} {i['w']}x{i['h']} @{i['fps']:.0f}fps  analysed at {w}x{h}, step {step:.3f}s")
print("   t    cam_dx cam_dy |  obj_dx obj_dy  obj_x obj_y  obj_area")
for k in range(1, len(fr)):
    f = cv2.calcOpticalFlowFarneback(fr[k - 1], fr[k], None, 0.5, 4, 21, 3, 5, 1.1, 0)
    cam = np.median(f.reshape(-1, 2), 0)
    res = f - cam
    mag = np.hypot(res[..., 0], res[..., 1])
    thr = max(2.0, np.percentile(mag, 92))
    mk = mag > thr
    if mk.sum() > 30:
        ys, xs = np.nonzero(mk)
        od = res[mk].mean(0)
        ox, oy, area = xs.mean() / w, ys.mean() / h, mk.mean()
    else:
        od, ox, oy, area = (0, 0), 0, 0, 0
    print(f"{t0 + k * step:6.2f}  {cam[0]:+6.1f} {cam[1]:+6.1f} | {od[0]:+7.1f} {od[1]:+6.1f}  {ox:5.2f} {oy:5.2f}  {area:5.3f}")
