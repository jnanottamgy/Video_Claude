#!/usr/bin/env bash
# The Instagram deliverables: the picture (renders/video.mp4) muxed with the soundtrack, encoded for upload.
#
#   tools/deliver.sh  ->  renders/deliver/JAYASHREE_event_reel.mp4          the post (the song included)
#                         renders/deliver/JAYASHREE_event_reel_nomusic.mp4  effects only, for when Instagram
#                                                                           mutes the song (re-add it there
#                                                                           from 1:24 of the track)
#                         renders/deliver/JAYASHREE_cover.jpg               the cover (the hook frame)
#                         renders/deliver/JAYASHREE_cover_end.jpg           an alternative cover (the end card)
# Two-pass H.264 High at ~9 Mbps (Instagram re-encodes anyway; a clean, high-bitrate upload survives it
# best), 2 s GOP, BT.709 tags, AAC 256 kb/s 48 kHz, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver
mkdir -p "$D"
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 renders/video.mp4)
want=$(python3 -c "import sys; sys.path.insert(0, 'tools'); import edl; print(edl.TOTAL)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
SCRATCH=${TMPDIR:-/tmp}
enc() {  # video audio out
  local log; log=$(mktemp -u "$SCRATCH/x264pass.XXXX")
  local v=(-c:v libx264 -preset slow -b:v 9000k -maxrate 14000k -bufsize 18000k -profile:v high -level 4.2
           -g 60 -keyint_min 60 -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
  ffmpeg -y -v error -i "$1" "${v[@]}" -pass 1 -passlogfile "$log" -an -f mp4 /dev/null
  ffmpeg -y -v error -i "$1" -i "$2" -map 0:v -map 1:a "${v[@]}" -pass 2 -passlogfile "$log" \
    -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$3"
  rm -f "$log"*
  echo "$3 $(du -h "$3" | cut -f1)"
}
enc renders/video.mp4 renders/audio/mix.wav "$D/JAYASHREE_event_reel.mp4"
enc renders/video.mp4 renders/audio/mix_nomusic.wav "$D/JAYASHREE_event_reel_nomusic.mp4"
# covers: the hook with its line fully written on (1.6 s), and the end card (64.6 s), straight from the picture
ffmpeg -y -v error -ss 1.6 -i renders/video.mp4 -frames:v 1 -q:v 2 "$D/JAYASHREE_cover.jpg"
ffmpeg -y -v error -ss 64.6 -i renders/video.mp4 -frames:v 1 -q:v 2 "$D/JAYASHREE_cover_end.jpg"
# what the profile grid shows (3:4, centred)
ffmpeg -y -v error -i "$D/JAYASHREE_cover.jpg" -vf "crop=1080:1440:0:240" -q:v 2 "$D/JAYASHREE_cover_grid_preview.jpg"
ls -la "$D"
