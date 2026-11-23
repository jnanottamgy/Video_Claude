#!/usr/bin/env bash
# REEL 2 deliverables: the picture (renders/picture_v2/picture.mp4) muxed with its mix (renders/audio/reel2_mix.wav).
#
#   tools/deliver_v2.sh  ->  renders/deliver/REDLINE_reel_16x9.mp4      1920x1080 master (horizontal)
#                            renders/deliver/REDLINE_reel_IG_9x16.mp4   1080x1920 for Reels: the 16:9 picture centred on black
#                            renders/deliver/REDLINE_cover.jpg          the Reels cover (tools/cover_v2.py)
# Same encode as the first reel: H.264 High, CRF 17 with a 12 Mb/s ceiling, 2 s GOP, BT.709, AAC 320 kb/s, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver
P=renders/picture_v2/picture.mp4
A=renders/audio/reel2_mix.wav
mkdir -p "$D"
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$P")
want=$(EDL=edl_v2 python3 -c "import sys; sys.path.insert(0, 'tools'); import render; print(render.NFRAMES)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
v=(-c:v libx264 -preset slow -crf 17 -maxrate 12000k -bufsize 24000k -profile:v high -level 4.2 -g 60 -keyint_min 30
   -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
ffmpeg -y -v error -i "$P" -i "$A" -map 0:v -map 1:a "${v[@]}" -c:a aac -b:a 320k -ar 48000 -shortest \
  -movflags +faststart "$D/REDLINE_reel_16x9.mp4"
ffmpeg -y -v error -i "$P" -i "$A" -map 0:v -map 1:a \
  -vf "scale=1080:608:flags=lanczos,pad=1080:1920:0:656:black,setsar=1" "${v[@]}" -c:a aac -b:a 320k -ar 48000 \
  -shortest -movflags +faststart "$D/REDLINE_reel_IG_9x16.mp4"
python3 tools/cover_v2.py
ls -la "$D"
