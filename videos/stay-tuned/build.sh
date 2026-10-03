#!/usr/bin/env bash
# Rebuild the 3s STAY TUNED IN / TO KNOW card (1080x1920, 30fps) from source.
#   1. HyperFrames renders the composition, silent
#   2. tools/mix_sfx.py builds the sound, timed off HIT in index.html
#   3. ffmpeg muxes the two
set -euo pipefail
cd "$(dirname "$0")"

npx --yes hyperframes@0.8.114 render . --skill=motion-graphics -q high -o ./renders/video_silent.mp4
python3 tools/mix_sfx.py
ffmpeg -y -loglevel error -i renders/video_silent.mp4 -i renders/sfx.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart renders/STAY_TUNED_IN_TO_KNOW.mp4
ls -la renders/STAY_TUNED_IN_TO_KNOW.mp4
