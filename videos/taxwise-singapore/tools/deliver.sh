#!/usr/bin/env bash
# The deliverables: the picture (renders/picture/picture.mp4) muxed with the soundtrack, encoded for upload.
#
#   tools/deliver.sh  ->  renders/deliver/TAXWISE_Singapore_reel.mp4           the post (song + voice + sound design)
#                         renders/deliver/TAXWISE_Singapore_reel_nomusic.mp4   voice + sound design only, for a
#                                                                              platform that mutes the song
#                         renders/deliver/TAXWISE_cover.jpg                    cover: the hook ("A NEW HORIZON")
#                         renders/deliver/TAXWISE_cover_end.jpg                alternative cover: the logo end card
#                         renders/deliver/TAXWISE_cover_grid_preview.jpg       how the cover crops in the 3:4 grid
# One master serves Instagram Reels, YouTube Shorts, LinkedIn and WhatsApp Status (9:16, 1080x1920, 30 fps).
# Two-pass H.264 High at ~10 Mbps (the platforms re-encode anyway; a clean, high-bitrate upload survives it
# best), 2 s GOP, BT.709 tags, AAC 320 kb/s 48 kHz, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
D=renders/deliver
P=renders/picture/picture.mp4
mkdir -p "$D"
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$P")
want=$(python3 -c "import sys; sys.path.insert(0, 'tools'); import edl; print(edl.TOTAL)")
echo "picture: $n frames (want $want)"
[ "$n" = "$want" ] || { echo "frame count mismatch" >&2; exit 1; }
SCRATCH=${TMPDIR:-/tmp}
enc() {  # video audio out
  local log; log=$(mktemp -u "$SCRATCH/x264pass.XXXX")
  local v=(-c:v libx264 -preset slow -b:v 10000k -maxrate 15000k -bufsize 20000k -profile:v high -level 4.2
           -g 60 -keyint_min 60 -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709)
  ffmpeg -y -v error -i "$1" "${v[@]}" -pass 1 -passlogfile "$log" -an -f mp4 /dev/null
  ffmpeg -y -v error -i "$1" -i "$2" -map 0:v -map 1:a "${v[@]}" -pass 2 -passlogfile "$log" \
    -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart "$3"
  rm -f "$log"*
  echo "$3 $(du -h "$3" | cut -f1)"
}
enc "$P" renders/audio/mix.wav "$D/TAXWISE_Singapore_reel.mp4"
enc "$P" renders/audio/mix_nomusic.wav "$D/TAXWISE_Singapore_reel_nomusic.mp4"
# covers:
# - the hook with A NEW HORIZON over the skyline (3.55 s), rendered without the caption and moved down 90 px
#   (the top rows of plain navy wall stretched to fill) so the title sits inside the profile grid's 3:4 crop;
# - the logo end card (51.0 s), straight from the picture.
python3 tools/composite.py --stills 3.55 --nocaps
python3 - "$D/TAXWISE_cover.jpg" <<'PY'
import sys, cv2, numpy as np
im = cv2.imread("renders/verify/still_003.55.jpg")
top = cv2.resize(im[:12], (im.shape[1], 90), interpolation=cv2.INTER_LINEAR)
cv2.imwrite(sys.argv[1], np.vstack([top, im[:-90]]), [cv2.IMWRITE_JPEG_QUALITY, 95])
PY
ffmpeg -y -v error -ss 51.0 -i "$P" -frames:v 1 -q:v 2 "$D/TAXWISE_cover_end.jpg"
ffmpeg -y -v error -i "$D/TAXWISE_cover.jpg" -vf "crop=1080:1440:0:240" -q:v 2 "$D/TAXWISE_cover_grid_preview.jpg"
ls -la "$D"
