#!/usr/bin/env bash
# Rebuild the S.H.E.L.F reel recut.
#
# Inputs (kept OUT of git — the repo is public):
#   renders/source.mp4        the edited reel (IMG_9598), 1080x1920 HEVC, full-range BT.709
#   renders/transcript.json   the text of each caption chunk, read off the frames (see tools/beats.py)
# Output: renders/SHELF_reel_recut.mp4
#
# Tools: the HyperFrames CLI (npx), ffmpeg, python3 with numpy/scipy/opencv, and for the person
# mattes a venv with rembg (u2net_human_seg): /root/vfx-venv (see tools/mattes.py).
set -euo pipefail
cd "$(dirname "$0")"

# 1. analysis: the source's audio, its burned-in captions, speech onsets, word timings
ffmpeg -y -v error -i renders/source.mp4 -vn -ac 2 -ar 48000 -c:a pcm_s16le renders/source_audio.wav
python3 tools/read_captions.py
python3 tools/speech_env.py
PYTHONPATH=tools python3 tools/beats.py > /dev/null

# 2. person mattes for the words that sit behind the founders
U2NET_HOME=/root/vfx-models /root/vfx-venv/bin/python tools/mattes.py

# 3. overlays: every slot is a HyperFrames project rendered to a transparent PNG sequence
#    (render one at a time: each PNG frame needs ~8 MB of capture scratch space)
for p in slots/notifs/storm_hook slots/hud/hud slots/notifs/cards slots/notifs/storm slots/tiles/problem \
         slots/tiles/oneplace slots/titles/*/; do
  (cd "$p" && npx --yes hyperframes@0.8.114 render . --format png-sequence -q high -o ./renders/png --quiet)
done
python3 tools/build_captions.py
python3 tools/build_captions.py --render

# 4. picture, sound, mux
python3 tools/composite.py --out renders/SHELF_reel_video.mp4
python3 tools/mix_audio.py
ffmpeg -y -v error -i renders/SHELF_reel_video.mp4 -i renders/mix.wav -map 0:v -map 1:a -c:v copy \
  -c:a aac -b:a 256k -shortest -movflags +faststart renders/SHELF_reel_recut.mp4
ls -la renders/SHELF_reel_recut.mp4
