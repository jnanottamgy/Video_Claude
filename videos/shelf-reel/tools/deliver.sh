#!/usr/bin/env bash
# Instagram-ready encodes of the v2 cuts, the cover, and page posters.
#
#   tools/deliver.sh [poster_dir]  -> renders/deliver_v2/{SHELF_reel_v2_main, _main_nomusic, _full}.mp4,
#                                     SHELF_cover.jpg (+ poster_short.jpg / poster_full.jpg in poster_dir)
# Two-pass H.264 High at ~7.5 Mbps (visually transparent next to the CRF 17 masters; Instagram
# re-encodes anyway), 2 s GOP, BT.709 tags, AAC 256k, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver_v2
mkdir -p "$D"
enc() {  # in out
  local log; log=$(mktemp -u /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/x264pass.XXXX)
  local v=(-c:v libx264 -preset slow -b:v 7500k -maxrate 12000k -bufsize 15000k -profile:v high -level 4.2
           -g 60 -keyint_min 60 -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
  ffmpeg -y -v error -i "$1" "${v[@]}" -pass 1 -passlogfile "$log" -an -f mp4 /dev/null
  ffmpeg -y -v error -i "$1" "${v[@]}" -pass 2 -passlogfile "$log" -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$2"
  rm -f "$log"*
  echo "$2 $(du -h "$2" | cut -f1)"
}
enc renders/SHELF_reel_v2_short.mp4 "$D/SHELF_reel_v2_main.mp4"
enc renders/SHELF_reel_v2_short_nomusic.mp4 "$D/SHELF_reel_v2_main_nomusic.mp4"
enc renders/SHELF_reel_v2_full.mp4 "$D/SHELF_reel_v2_full.mp4"
# the cover: the hook frame after the drop, title punched in, storm exploding (inside the 3:4 grid crop),
# rendered without the caption layer so it reads as a designed thumbnail, not a paused video
python3 - "$D/SHELF_cover.jpg" <<'PY'
import sys; sys.path.insert(0, "tools")
import cv2, numpy as np
import composite as C
c = C.Comp(); c.captions = []
im = c.frame(39)
cv2.imwrite(sys.argv[1], cv2.cvtColor((im * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
PY
if [ $# -ge 1 ]; then
  ffmpeg -y -v error -ss 1.30 -i renders/SHELF_reel_v2_video.mp4 -frames:v 1 -vf scale=540:-2 -q:v 4 "$1/poster_short.jpg"
  ffmpeg -y -v error -ss 91.90 -i renders/SHELF_reel_v2_video.mp4 -frames:v 1 -vf scale=540:-2 -q:v 4 "$1/poster_full.jpg"
fi
ls -la "$D"
