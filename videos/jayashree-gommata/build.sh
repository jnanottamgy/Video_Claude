#!/usr/bin/env bash
# Rebuild the "Cheluvara Cheluva Namma Gommata Deva" reel for Jayashree D Jain's Instagram (33 s, 1080x1920, 30 fps).
#
# Inputs (kept OUT of git: the repo is public):
#   renders/src/drive/gommata_source.mp4   the client's YouTube copy of the Kaveri Dham programme (11:44, 360p),
#                                          from their Drive
#   renders/src/hd/*.mp4                   optional: a sharper copy of the same video; used instead when present
#                                          (the crops are kept in normalised coordinates)
#   library/sfx/nikovax/*.wav              the SFX library (restore: python3 library/tools/sfx.py check)
# Output: renders/deliver/JAYASHREE_Cheluvara_Cheluva_reel_v2.mp4 (+ the cover)
#
# Tools: ffmpeg, python3 (numpy scipy opencv pillow+raqm soundfile pyloudnorm librosa), npm (for the fonts).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders/audio renders/logs
[ -f renders/fonts/noto-serif-kannada-kannada-700-normal.ttf ] || tools/fonts.sh

# 1. the soundtrack: her finale, one continuous take, with temple sounds tuned to Sa (G#), -14 LUFS
ffmpeg -y -v error -i renders/src/drive/gommata_source.mp4 -vn -ar 48000 -c:a pcm_f32le renders/audio/source.wav
python3 tools/mix.py

# 2. the picture: 4 parallel parts, then joined
for i in 0 1 2 3; do python3 tools/composite.py --part "$i/4" > "renders/logs/part_$i.log" 2>&1 & done; wait
python3 tools/composite.py --join 4

# 3. the upload file and the cover
tools/deliver.sh
