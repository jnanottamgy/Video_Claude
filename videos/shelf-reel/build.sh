#!/usr/bin/env bash
# Rebuild the S.H.E.L.F reel, v2: WhatsApp-first, cut to the song, in two cuts.
#
# Inputs (kept OUT of git — the repo is public):
#   renders/source.mp4        the edited reel (IMG_9598), 1080x1920 HEVC, full-range BT.709
#   renders/song.mp3          the song their edit is cut to (Travis Scott x Vizion "My Eyes")
#   renders/transcript.json   the text of each caption chunk, read off the frames (see tools/beats.py)
# Outputs: renders/SHELF_reel_v2_full.mp4 (1:49), renders/SHELF_reel_v2_short.mp4 (0:48, the main
#          post) and renders/SHELF_reel_v2_short_nomusic.mp4 (if Instagram mutes the song)
#
# Tools: the HyperFrames CLI (npx), ffmpeg, python3 with numpy/scipy/opencv/soundfile/librosa, and
# for the person mattes a venv with rembg (u2net_human_seg): /root/vfx-venv (see tools/mattes.py).
set -euo pipefail
cd "$(dirname "$0")"

# 1. analysis: the source's audio, its burned-in captions, speech onsets, word timings, and the
#    dialogue on its own (their mix minus the song, which sits in it unprocessed: tools/dialogue.py)
ffmpeg -y -v error -i renders/source.mp4 -vn -ac 2 -ar 48000 -c:a pcm_s16le renders/source_audio.wav
python3 tools/read_captions.py
python3 tools/speech_env.py
python3 tools/beats.py > /dev/null
python3 tools/dialogue.py

# 2. person mattes for the words that sit behind the founders and the freeze frames
U2NET_HOME=/root/vfx-models /root/vfx-venv/bin/python tools/mattes.py

# 3. overlays: every slot is a HyperFrames project rendered to a transparent PNG sequence
#    (render one at a time: each PNG frame needs ~8 MB of capture scratch space)
for p in slots/viral/hook_title slots/notifs/storm_hook slots/hud/hud slots/notifs/cards slots/notifs/storm \
         slots/tiles/problem slots/tiles/oneplace slots/viral/cta_end slots/titles/*/; do
  (cd "$p" && npx --yes hyperframes@0.8.114 render . --format png-sequence -q high -o ./renders/png --quiet)
done
python3 tools/build_captions.py
python3 tools/build_captions.py --render

# 4. the full cut: picture (tools/composite.py), sound (tools/mix_audio.py: dialogue + the song laid by
#    tools/music.py + sound design), mux
python3 tools/composite.py --out renders/SHELF_reel_v2_video.mp4
python3 tools/mix_audio.py
ffmpeg -y -v error -i renders/SHELF_reel_v2_video.mp4 -i renders/mix.wav -map 0:v -map 1:a -c:v copy \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart renders/SHELF_reel_v2_full.mp4

# 5. the short cut (ranges of the full picture, the song re-laid) and its no-music version
python3 tools/shortcut.py
ls -la renders/SHELF_reel_v2_*.mp4
