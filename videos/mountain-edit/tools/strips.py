"""Timestamped strips of one clip range, for picking moments.
  python3 tools/strips.py OUT.jpg CLIP T0 T1 FPS [COLS]"""
import json, subprocess, sys
import cv2, numpy as np
out, clip, t0, t1, fps = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 12
p = f"renders/src/footage/{clip}"
trc = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                                 "-of", "json", p], capture_output=True, text=True).stdout)["streams"][0].get("color_transfer", "")
tm = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if trc == "arib-std-b67" else ""
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", p, "-vf",
                      f"{tm}fps={fps},scale='if(gt(iw,ih),240,-2)':'if(gt(iw,ih),-2,240)'", "-f", "image2pipe", "-vcodec", "png", "-"],
                     capture_output=True).stdout
ims, i = [], 0
while i < len(raw):
    j = raw.find(b"\x89PNG", i + 8); j = len(raw) if j < 0 else j
    ims.append(cv2.imdecode(np.frombuffer(raw[i:j], np.uint8), cv2.IMREAD_COLOR)); i = j
h, w = ims[0].shape[:2]
tiles = []
for k, im in enumerate(ims):
    im = cv2.resize(im, (w, h))
    cv2.putText(im, f"{t0 + k / fps:.2f}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
    tiles.append(im)
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(out, len(ims))
