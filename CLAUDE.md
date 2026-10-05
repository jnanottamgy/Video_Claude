# Video_Claude — working notes for Claude Code

An AI video-production workspace. 35 skills across five upstream projects. See
`README.md` for the full inventory.

## Picking an engine

Four engines are installed and they overlap. Choose by the *input*, not by taste:

| The user has… | Use |
| --- | --- |
| Raw footage to cut (talking head, montage, tutorial, interview) | `video-use` |
| A brief/URL/PR and wants motion graphics, no footage | `/hyperframes` (routes itself) |
| An existing React codebase, or wants video as React components | `remotion-best-practices` (router) |
| A UI or social motion graphic close to a stock template (toasts, AI chat, prompt typing, CTA, stat bars, HUD) | `nullmotion`: copy the template, change the text, render with HyperFrames |
| A need to *generate* voiceover, music, images, or AI clips | toolkit skills: `elevenlabs`, `acestep`, `ideogram4`, `ltx2`, `qwen-edit` |
| Raw encode/convert/concat work | `ffmpeg` |

`/hyperframes` is the mandatory entry point for HyperFrames work — it resumes
project state and installs creation workflows on demand. Don't hand-build a
HyperFrames composition without reading it first.

## Where things live

- `.agents/skills/<name>/` — real skill directories. Edit here.
- `.claude/skills/<name>` — symlinks into the above. Don't edit; they're links.
- `vendor/claude-code-video-toolkit/` — the toolkit's own checkout. **Its skills
  reference `tools/`, `lib/`, `scripts/`, `templates/` relative to that directory**,
  not to the repo root. When a toolkit skill says `tools/voiceover.py`, it means
  `vendor/claude-code-video-toolkit/tools/voiceover.py`.
- `video-use` references its helpers by bare name (`transcribe.py`, `render.py`) —
  those are at `.agents/skills/video-use/helpers/`.
- `vendor/nullmotion/` — the Null Motion app, fetched by `scripts/fetch-nullmotion.sh`
  (`setup.sh` runs it). **Gitignored: upstream has no licence and this repo is public.**
  Never commit it, or a template copied from it; copies go to the gitignored `edit/nullmotion/`.

## Transcription: two backends, different costs

- **ElevenLabs Scribe** (`ELEVENLABS_API_KEY`) — paid. Word-level timestamps,
  speaker diarization, filler tagging. `video-use`'s cut logic depends on this
  level of detail.
- **Whisper** — free, local, offline. `whisper take01.mp4 --model small
  --output_format srt`. Good for a rough transcript or when no key is set.

Never run a paid transcription as a setup or smoke test — it costs real money.
Ask before transcribing a long file.

## Known environment gotcha: blocked CDNs

In sandboxed sessions `cdn.jsdelivr.net`, `unpkg.com` and `cdnjs.cloudflare.com` are
blocked. A fresh HyperFrames scaffold loads GSAP from jsdelivr, so `hyperframes
render` captures every frame and then fails the correctness gate with
`sub_timeline_script_failure`. This is a network block, not a broken composition.

Fix: `scripts/vendor-cdn-deps.sh <project-dir>` pulls the package from npm (the
registry is reachable) and rewrites the `<script src>` to a local `vendor/` copy.
Then re-render. Verified working — produces a real 1920x1080 MP4.

Whisper model weights are blocked the same way; the CLI works, the download doesn't.

## Conventions

- Video outputs go to `edit/` or a project subdirectory — both are gitignored.
  Keep renders and raw footage out of git.
- Never commit `.env`. Never echo an API key into tool output.
- Re-running `./setup.sh` is safe and idempotent.
- After a fresh Claude Code web session, run `./setup.sh` — the container starts
  without ffmpeg or the Python packages. The skills themselves are committed and
  need no fetch.
