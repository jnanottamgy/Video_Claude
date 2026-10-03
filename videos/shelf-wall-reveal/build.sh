#!/usr/bin/env bash
# Rebuild every S.H.E.L.F wall deliverable from source.
#   1. HyperFrames renders both flat lockups as transparent RGBA frames
#        - this project:          the S.H.E.L.F mark + name reveal  (left wall)
#        - ../shelf-launch-soon:  LAUNCHING SOON, typed out         (back wall)
#   2. tools/wall_warp.py mounts each onto its wall in perspective and composites them
#   3. tools/mix_sfx.py builds the synced sound-effects stem
#   4. ffmpeg encodes the alpha overlays with sound (+ a preview, if the snapshot is present)
set -euo pipefail
cd "$(dirname "$0")"

for p in . ../shelf-launch-soon; do
  (cd "$p" && npx --yes hyperframes render . --skill=motion-graphics --format png-sequence -q high -o ./renders/flat_png)
done
python3 tools/wall_warp.py
python3 tools/mix_sfx.py

mkdir -p renders/out
SFX=renders/out/SHELF_sfx.wav
# QuickTime Animation: lossless RGBA, and far smaller than ProRes 4444 here because it
# run-length-encodes the ~95% of each frame that is transparent.
ffmpeg -y -loglevel error -framerate 30 -i renders/wall_png/frame_%06d.png -i "$SFX" \
  -map 0:v -map 1:a -c:v qtrle -pix_fmt argb -c:a pcm_s24le -shortest renders/out/SHELF_wall-overlay_alpha.mov
ffmpeg -y -loglevel error -framerate 30 -i renders/wall_png/frame_%06d.png -i "$SFX" \
  -map 0:v -map 1:a -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -auto-alt-ref 0 -row-mt 1 \
  -c:a libopus -b:a 160k -shortest renders/out/SHELF_wall-overlay_alpha.webm

# Preview needs the reel snapshot, which is kept out of git (it's a photo of a private room).
if [ -f assets/reel-snapshot.png ]; then
  python3 -c "import sys; sys.path.insert(0,'tools'); import wall_warp as w, cv2; cv2.imwrite('renders/out/_bg.png', (w.snapshot_background('assets/reel-snapshot.png')*255).clip(0,255).astype('uint8'))"
  ffmpeg -y -loglevel error -loop 1 -framerate 30 -i renders/out/_bg.png -framerate 30 -i renders/wall_png/frame_%06d.png -i "$SFX" \
    -filter_complex "[0:v][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]" -map "[v]" -map 2:a \
    -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 256k -shortest -movflags +faststart renders/out/SHELF_wall-preview.mp4
fi
ls -la renders/out/
