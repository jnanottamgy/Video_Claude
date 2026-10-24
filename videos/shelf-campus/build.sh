#!/usr/bin/env bash
# Rebuild the SHELF CAMPUS founders reel (60.7 s, 1080x1920, 30 fps) from the team's own 72 s reel.
#
# Inputs (kept OUT of git — the repo is public):
#   renders/src/founders_reel_original.mp4   the founders' edited reel (Google Drive download)
#   renders/src/song_the_kill_2.mp3          the song they chose (Lex Amarni & 2muchmotion, "The Kill 2")
#   library/sfx/nikovax/*.wav                the SFX library (restore: python3 library/tools/sfx.py check)
# Output: renders/deliver/SHELF_CAMPUS_reel.mp4 (+ _nomusic.mp4, the cover)
#
# Tools: ffmpeg, python3 (numpy scipy opencv soundfile pyloudnorm librosa pillow fonttools+brotli rembg
# sherpa-onnx), the HyperFrames CLI (npx, pinned per slot), and the local ASR models in /root/asr-models
# (Whisper turbo + Silero VAD + Parakeet TDT v2, from the k2-fsa GitHub releases).
set -euo pipefail
cd "$(dirname "$0")"

# 1. analysis: word timings, person mattes, the cut list, reference stills, the brand fonts as TTF
python3 tools/words.py > /dev/null
python3 tools/words_out.py
python3 tools/mattes.py
python3 tools/edl.py > /dev/null
python3 tools/ref_frame.py --set
python3 tools/split_people.py
python3 - <<'PY'
import os
from fontTools.ttLib import TTFont
os.makedirs("renders/fonts", exist_ok=True)
for f in os.listdir("design/fonts"):
    if f.startswith(("sora", "inter-latin-7", "inter-latin-8")) and f.endswith(".woff2"):
        t = TTFont(f"design/fonts/{f}"); t.flavor = None; t.save(f"renders/fonts/{f[:-6]}.ttf")
PY

# 2. graphics: every slot is a HyperFrames project rendered to a PNG sequence (see slots/BRIEF.md);
#    render one at a time (each needs a lot of capture scratch space)
for p in slots/*/; do
  case "$p" in slots/_*) continue ;; esac
  (cd "$p" && rm -rf renders/png && npx --yes "$(node -p 'require("./package.json").scripts.render.split(" ")[2]')" \
     render . --format png-sequence -q high -o ./renders/png --quiet)
done

# 3. sound: studio dialogue, then the mix (song re-cut, sound design, -14 LUFS master)
python3 tools/dialogue.py
python3 tools/mix.py
python3 tools/audio_check.py

# 4. picture, in parallel parts, then the mux and the Instagram encodes
python3 tools/composite.py --jobs 3
tools/deliver.sh
