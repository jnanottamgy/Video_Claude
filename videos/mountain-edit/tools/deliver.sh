#!/usr/bin/env bash
# The deliverables: the picture (renders/picture/picture.mp4) muxed with the mix (renders/audio/mix.wav).
#
#   tools/deliver.sh  ->  renders/deliver/DNA_reel_16x9.mp4      1920x1080 master (horizontal, as briefed)
#                         renders/deliver/DNA_reel_IG_9x16.mp4   1080x1920 for Reels: the 16:9 picture centred on black
#                         renders/deliver/DNA_cover.jpg          the Reels cover (tools/cover.py)
# H.264 High, CRF 16 with a 20 Mb/s ceiling (Instagram re-encodes; a clean, rich upload survives it best), 2 s GOP,
# BT.709 tags, AAC 320 kb/s 48 kHz, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver
P=renders/picture/picture.mp4
A=renders/audio/mix.wav
mkdir -p "$D"
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$P")
want=$(python3 -c "import sys; sys.path.insert(0, 'tools'); import render; print(render.NFRAMES)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
v=(-c:v libx264 -preset slow -crf 16 -maxrate 20000k -bufsize 40000k -profile:v high -level 4.2 -g 60 -keyint_min 30
   -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
ffmpeg -y -v error -i "$P" -i "$A" -map 0:v -map 1:a "${v[@]}" -c:a aac -b:a 320k -ar 48000 -shortest \
  -movflags +faststart "$D/DNA_reel_16x9.mp4"
ffmpeg -y -v error -i "$P" -i "$A" -map 0:v -map 1:a \
  -vf "scale=1080:608:flags=lanczos,pad=1080:1920:0:656:black,setsar=1" "${v[@]}" -c:a aac -b:a 320k -ar 48000 \
  -shortest -movflags +faststart "$D/DNA_reel_IG_9x16.mp4"
python3 tools/cover.py
ls -la "$D"
