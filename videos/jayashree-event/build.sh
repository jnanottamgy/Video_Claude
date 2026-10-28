#!/usr/bin/env bash
# Rebuild the Jayashree D Jain event reel (v6: 39.1 s, 1080x1920, 30 fps) from the client's event footage.
#
# Inputs (kept OUT of git: the repo is public):
#   renders/src/drive/IMG_*.MOV               the client's 58 event clips (their Google Drive folder)
#   renders/src/song_chanakya.mp3             the track they chose ("Chanakya", Rishab Rikhiram Sharma, edit audio)
#   library/sfx/nikovax/*.wav                 the SFX library (restore: python3 library/tools/sfx.py check)
# Output: renders/deliver/JAYASHREE_event_reel_v6.mp4 (+ _nomusic.mp4, the covers)
#
# Tools: ffmpeg (with zscale), python3 (numpy scipy opencv pillow+raqm soundfile librosa fonttools+brotli), npm.
set -euo pipefail
cd "$(dirname "$0")"

# 1. analysis: SDR proxies, per-clip statistics, the song at 48 kHz, the title fonts
tools/proxies.sh
python3 tools/clipstats.py
mkdir -p renders/analysis
ffmpeg -y -v error -i renders/src/song_chanakya.mp3 -ar 48000 -c:a pcm_s24le renders/analysis/song_chanakya.wav
[ -f renders/fonts/cinzel-latin-700-normal.ttf ] || tools/fonts.sh
python3 tools/edl.py

# 2. the picture: 4 workers, about 10 minutes on 4 cores
python3 tools/composite.py render 4

# 3. the sound: song window + temple sounds + library effects, -14 LUFS
python3 tools/mix.py

# 4. checks and the Instagram files
python3 tools/qa.py motion
tools/deliver.sh
