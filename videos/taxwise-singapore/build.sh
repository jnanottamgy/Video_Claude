#!/usr/bin/env bash
# Rebuild the TaxWise Consultants Singapore-expansion reel (52.0 s, 1080x1920, 30 fps) from the team's edit.
#
# Inputs (kept OUT of git: the repo is public):
#   renders/src/drive/reel_original.mp4        the team's 56 s reel (HK Vinay at his desk), from their Drive
#   renders/src/song_timeless_instrumental.mp3 the song they supplied ("Timeless Instrumental")
#   library/sfx/nikovax/*.wav                  the SFX library (restore: python3 library/tools/sfx.py check)
#   /root/asr-models                           offline ASR (Silero VAD + Parakeet TDT 0.6b v2, sherpa-onnx)
# Output: renders/deliver/TAXWISE_Singapore_reel.mp4 (+ _nomusic.mp4, the covers)
#
# Tools: ffmpeg, python3 (numpy scipy opencv pillow+raqm soundfile pyloudnorm rembg sherpa-onnx), node + npx.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders/analysis renders/audio

# 1. analysis: the song and the reel's audio at 48 kHz, every spoken word with its time
ffmpeg -y -v error -i renders/src/song_timeless_instrumental.mp3 -ar 48000 -c:a pcm_s24le renders/analysis/song.wav
ffmpeg -y -v error -i renders/src/drive/reel_original.mp4 -vn -ar 48000 -c:a pcm_s24le renders/analysis/reel_audio.wav
python3 tools/words.py
python3 tools/edl.py

# 2. his cut-out (person mattes for the on-camera frames), the clean plates and desk lines
python3 tools/mattes.py
python3 tools/plates.py

# 3. the graphics: one HyperFrames project per slot (see slots/BRIEF.md and slots/SPEC_*.md)
for s in hook_behind name_behind singapore_slam team_services globe values_behind finale_behind end_card; do
  (cd "slots/$s" && rm -rf renders/png && npx --yes hyperframes@0.8.191 render . --format png-sequence -q high -o ./renders/png)
done

# 4. the sound: studio dialogue, then the mix (song + voice + sound design), -14 LUFS
python3 tools/dialogue.py
python3 tools/mix.py

# 5. the picture: 4 parallel parts, then joined
for i in 0 1 2 3; do python3 tools/composite.py --part "$i/4" & done; wait
python3 tools/composite.py --join 4

# 6. the platform files
tools/deliver.sh
