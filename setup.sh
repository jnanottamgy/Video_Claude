#!/usr/bin/env bash
# Rebuild the video workspace's system dependencies.
#
# The skills themselves are committed to this repo (.agents/skills + .claude/skills),
# so they need no network. This script installs the binaries and Python packages
# that cannot be committed — run it after cloning, and in any fresh
# Claude Code web session (the container starts empty).
set -euo pipefail

say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

say "ffmpeg / ffprobe"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "already present: $(ffmpeg -version | head -1)"
elif command -v apt-get >/dev/null 2>&1; then
  ${SUDO:-$([ "$(id -u)" -eq 0 ] || echo sudo)} apt-get update -qq
  ${SUDO:-$([ "$(id -u)" -eq 0 ] || echo sudo)} DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg
else
  echo "Install ffmpeg manually: https://ffmpeg.org/download.html" >&2
fi

say "Python packages"
PIP_FLAGS=""
python3 -m pip install --help 2>/dev/null | grep -q break-system-packages && PIP_FLAGS="--break-system-packages"
# video-use helpers need these; openai-whisper is the free local transcription
# fallback (large — it pulls torch). Set SKIP_WHISPER=1 to omit it.
python3 -m pip install $PIP_FLAGS requests librosa matplotlib pillow numpy
if [ "${SKIP_WHISPER:-0}" != "1" ]; then
  python3 -m pip install $PIP_FLAGS openai-whisper
fi

say "Node toolchain"
if command -v node >/dev/null 2>&1; then
  echo "node $(node --version)  (HyperFrames needs 22+, Remotion needs 18+)"
else
  echo "Install Node.js 22+: https://nodejs.org" >&2
fi

say "Verify"
ffmpeg -version 2>/dev/null | head -1 || echo "ffmpeg MISSING"
python3 -c "import requests, librosa, numpy; print('python helpers OK')" || true
python3 -c "import whisper; print('whisper OK')" 2>/dev/null || echo "whisper not installed (optional)"
echo "skills wired: $(ls .claude/skills 2>/dev/null | wc -l)"

cat <<'NOTE'

Done. API keys are NOT set by this script — copy .env.example to .env and fill in
whichever you need:
  ELEVENLABS_API_KEY  transcription + voice for video-use and the toolkit
See README.md for which skill needs what.
NOTE
