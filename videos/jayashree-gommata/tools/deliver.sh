#!/usr/bin/env bash
# The deliverables: the picture (renders/picture/picture.mp4) muxed with the soundtrack, encoded for upload,
# and the covers.
#
#   tools/deliver.sh  ->  renders/deliver/JAYASHREE_Cheluvara_Cheluva_reel_v2.mp4   1080x1920, 30 fps, 33 s
#                         renders/deliver/JAYASHREE_Cheluvara_Cheluva_cover.jpg   the cover (the hook frame)
#                         renders/deliver/JAYASHREE_cover_grid_preview.jpg        how it crops in the 3:4 grid
# Two-pass H.264 High at ~10 Mbps (the platforms re-encode anyway; a clean, high-bitrate upload survives it best),
# a 2 s GOP, BT.709 tags, AAC 320 kb/s 48 kHz, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver
P=renders/picture/picture.mp4
mkdir -p "$D"
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$P")
want=$(python3 -c "import sys; sys.path.insert(0, 'tools'); import edl; print(edl.TOTAL)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
OUT="$D/JAYASHREE_Cheluvara_Cheluva_reel_v2.mp4"
log=$(mktemp -u "${TMPDIR:-/tmp}/x264pass.XXXX")
v=(-c:v libx264 -preset slow -b:v 10000k -maxrate 15000k -bufsize 20000k -profile:v high -level 4.2
   -g 60 -keyint_min 60 -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
ffmpeg -y -v error -i "$P" "${v[@]}" -pass 1 -passlogfile "$log" -an -f mp4 /dev/null
ffmpeg -y -v error -i "$P" -i renders/audio/mix.wav -map 0:v -map 1:a "${v[@]}" -pass 2 -passlogfile "$log" \
  -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart "$OUT"
rm -f "$log"*
echo "$OUT $(du -h "$OUT" | cut -f1)"
# the cover: the hook frame (the statue's face, her name, the first line), and its 3:4 grid crop
ffmpeg -y -v error -ss 3.50 -i "$P" -frames:v 1 -q:v 2 "$D/JAYASHREE_Cheluvara_Cheluva_cover.jpg"
ffmpeg -y -v error -i "$D/JAYASHREE_Cheluvara_Cheluva_cover.jpg" -vf "crop=1080:1440:0:240" -q:v 2 \
  "$D/JAYASHREE_cover_grid_preview.jpg"
ls -la "$D"
