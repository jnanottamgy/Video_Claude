#!/usr/bin/env bash
# Join the full cut's picture from section renders (composite.py --range), check it, add the mix.
#
#   tools/assemble.sh       -> renders/SHELF_reel_v2_video.mp4 (picture) and SHELF_reel_v2_full.mp4
# Sections are rendered separately so finished stretches never wait on overlays still in progress;
# every boundary is a frame (n = t * 30), so the parts butt together exactly.
set -euo pipefail
cd "$(dirname "$0")/.."
P=renders/v2parts
parts=(p_0.0-4.3.mp4 p_4.3-30.0.mp4 p_30.0-51.8.mp4 p_51.8-70.1.mp4 p_70.1-92.8.mp4 p_92.8-105.0.mp4 p_105.0-108.6.mp4)
: > "$P/list.txt"
for p in "${parts[@]}"; do
  [ -f "$P/$p" ] || { echo "missing $P/$p" >&2; exit 1; }
  echo "file '$p'" >> "$P/list.txt"
done
ffmpeg -y -v error -f concat -safe 0 -i "$P/list.txt" -c copy -movflags +faststart renders/SHELF_reel_v2_video.mp4
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 renders/SHELF_reel_v2_video.mp4)
want=$(python3 -c "import sys; sys.path.insert(0, 'tools'); import edl; print(edl.TOTAL)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
python3 tools/mix_audio.py
ffmpeg -y -v error -i renders/SHELF_reel_v2_video.mp4 -i renders/mix.wav -map 0:v -map 1:a -c:v copy \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart renders/SHELF_reel_v2_full.mp4
ls -la renders/SHELF_reel_v2_full.mp4
