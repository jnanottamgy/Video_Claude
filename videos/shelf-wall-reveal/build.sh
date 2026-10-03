#!/usr/bin/env bash
# Rebuild every S.H.E.L.F deliverable from source.
#   1. HyperFrames renders the flat lockup as transparent RGBA frames
#   2. tools/wall_warp.py mounts it onto the reel's wall in perspective
#   3. ffmpeg encodes the alpha overlays (+ a preview, if the snapshot is present)
set -euo pipefail
cd "$(dirname "$0")"

npx --yes hyperframes render . --skill=motion-graphics --format png-sequence -q high -o ./renders/flat_png
python3 tools/wall_warp.py --scale 0.60 --cx 298 --cy 748

mkdir -p renders/out
# QuickTime Animation: lossless RGBA, and ~5x smaller than ProRes 4444 here because it
# run-length-encodes the ~97% of each frame that is transparent (15 MB vs 70 MB).
alpha_mov()  { ffmpeg -y -loglevel error -framerate 30 -i "$1/frame_%06d.png" -c:v qtrle -pix_fmt argb "$2"; }
alpha_webm() { ffmpeg -y -loglevel error -framerate 30 -i "$1/frame_%06d.png" -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -auto-alt-ref 0 -row-mt 1 "$2"; }

alpha_mov  renders/wall_png renders/out/SHELF_wall-overlay_alpha.mov
alpha_webm renders/wall_png renders/out/SHELF_wall-overlay_alpha.webm
alpha_mov  renders/flat_png renders/out/SHELF_lockup-flat_alpha.mov
alpha_webm renders/flat_png renders/out/SHELF_lockup-flat_alpha.webm

# Preview needs the reel snapshot, which is kept out of git (it's a photo of a private room).
if [ -f assets/reel-snapshot.png ]; then
  python3 -c "import sys; sys.path.insert(0,'tools'); import wall_warp as w, cv2; cv2.imwrite('renders/out/_bg.png', (w.snapshot_background('assets/reel-snapshot.png')*255).clip(0,255).astype('uint8'))"
  ffmpeg -y -loglevel error -loop 1 -framerate 30 -i renders/out/_bg.png -framerate 30 -i renders/wall_png/frame_%06d.png \
    -filter_complex "[0:v][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]" -map "[v]" \
    -c:v libx264 -preset slow -crf 18 -movflags +faststart renders/out/SHELF_wall-preview.mp4
fi
ls -la renders/out/
