"""Contact sheets of the client's footage: one row per clip, N frames evenly spaced, each fitted in a square box.
  python3 tools/footage_sheets.py OUT_PREFIX N clip1 clip2 ...   (rows of 6 clips per sheet)"""
import json, subprocess, sys
import cv2, numpy as np

def probe(p):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=color_transfer:format=duration", "-of", "json", p], capture_output=True, text=True).stdout)
    return float(d["format"]["duration"]), d["streams"][0].get("color_transfer", "")

def frame(p, t, hlg):
    vf = "scale=-2:360"
    if hlg:
        vf = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", p, "-frames:v", "1", "-vf", vf,
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)

B = 230
out, n, clips = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
rows = []
for p in clips:
    dur, trc = probe(p)
    tiles = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        im = frame(p, t, trc == "arib-std-b67")
        canvas = np.full((B, B, 3), 24, np.uint8)
        if im is not None:
            s = B / max(im.shape[:2]); im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
            y0, x0 = (B - im.shape[0]) // 2, (B - im.shape[1]) // 2
            canvas[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
        cv2.putText(canvas, f"{t:.1f}", (4, B - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(canvas)
    label = np.full((B, 120, 3), 0, np.uint8)
    name = p.split("/")[-1].split(".")[0].replace("IMG_", "")
    cv2.putText(label, name, (6, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(label, f"{dur:.1f}s", (6, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    rows.append(np.hstack([label] + tiles))
for i in range(0, len(rows), 6):
    cv2.imwrite(f"{out}_{i // 6 + 1}.jpg", np.vstack(rows[i:i + 6]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(len(rows), "clips")
