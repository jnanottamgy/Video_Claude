# Video_Claude

An AI video-production workspace for Claude Code. **34 skills** from four upstream
projects are installed and wired up, covering the whole pipeline: transcribe and
cut real footage, generate voiceover/music/imagery, compose in HTML or React, and
render to MP4.

Open Claude Code in this directory and describe the video you want.

```bash
./setup.sh      # system deps (ffmpeg, python packages) — run once per machine/session
claude
```

## What's installed

| Source | Skills | What it does |
| --- | --- | --- |
| [browser-use/video-use](https://github.com/browser-use/video-use) | `video-use`, `manim-video` | **Edits real footage by conversation.** Drop raw takes in a folder, get `final.mp4`. Cuts filler words and dead air, colour grades, burns subtitles, keeps session memory in `project.md`. |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | `hyperframes` + 8 `hyperframes-*` / `media-use` | **Write HTML, render video.** Composition contract, GSAP/Lottie/Three.js animation, audio mixing, a ~400-item block registry, and an asset resolver. Start at `/hyperframes` — it routes to the rest and installs creation workflows on demand. |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | 12 × `remotion-*` | **Video as React.** Official Remotion skills — create, caption, animate, preview in Studio, render, upgrade. `remotion-best-practices` is the router. |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) | `ffmpeg`, `elevenlabs`, `acestep`, `ideogram4`, `ltx2`, `qwen-edit`, `moviepy`, `runpod`, `playwright-recording`, `frontend-design`, `remotion` | **Generation + encoding.** AI voiceover, music, image and video generation on open-source models via your own GPU, plus raw FFmpeg and browser screen-recording. Also ships 14 slash commands (`/video`, `/setup`, `/brand`, …). |

Run `/hyperframes` for HTML-based motion graphics, `remotion-best-practices` for
React video, or just describe footage you want edited and `video-use` takes over.

### About OpenAI Whisper

[openai/whisper](https://github.com/openai/whisper) was also requested. It is **not a
skill** — it has no `SKILL.md` and nothing for an agent to load. It is a Python
speech-recognition library, so it is installed as one (`setup.sh` runs
`pip install openai-whisper`) and any skill can call it.

It matters here because `video-use` transcribes through **ElevenLabs Scribe, which
is a paid API**. Whisper is the free, local, offline alternative:

```bash
whisper take01.mp4 --model small --output_format srt
```

Use it to rough out a transcript at no cost; use Scribe when you need word-level
timestamps, speaker diarization and filler tagging, which is what `video-use`'s
cutting logic is built around.

## Layout

```
.agents/skills/     real skill directories (source of truth)
.claude/skills/     symlinks into the above — what Claude Code loads
.claude/commands/   14 slash commands from the toolkit
vendor/
  claude-code-video-toolkit/   toolkit checkout; its skills reference
                               tools/, lib/, templates/ at this root
setup.sh            installs ffmpeg + python packages
.env.example        API keys — copy to .env
```

Skills are **committed to this repo**, so a fresh clone or a new Claude Code web
session has them immediately with no network fetch. Only system dependencies need
`./setup.sh`.

## API keys

Copy `.env.example` to `.env` and fill in what you actually use. Only one key is
needed to get started:

- `ELEVENLABS_API_KEY` — transcription and voiceover. Required for `video-use`'s
  cutting workflow. ([get one](https://elevenlabs.io/app/settings/api-keys))

Everything else (`RUNPOD_API_KEY`, `IDEOGRAM_API_KEY`, R2 storage) is optional and
only used by the toolkit's cloud-generation skills.

## Requirements

- **ffmpeg** — hard requirement, installed by `setup.sh`
- **Node.js 22+** — HyperFrames needs 22+, Remotion needs 18+
- **Python 3.10+** — for `video-use` helpers and whisper

## Restricted networks (Claude Code web sessions)

Sandboxed environments often block public CDNs. Two things break, both with fixes:

**HyperFrames renders fail** at the final correctness gate:

```
sub_timeline_script_failure: A sub-composition timeline script failed to load
  (https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js)
```

Scaffolds load GSAP from jsdelivr. The npm registry is usually still reachable, so
vendor it locally and re-render:

```bash
scripts/vendor-cdn-deps.sh path/to/project   # pulls the package from npm, rewrites the <script> tag
cd path/to/project && npx hyperframes render
```

**Whisper cannot fetch model weights** — its CDN (`openaipublic.azureedge.net`) and
the Hugging Face mirror are commonly blocked. The `whisper` CLI installs and runs
fine; only the first-run weight download fails. Either run whisper on an unrestricted
machine, or copy a `.pt` model into `~/.cache/whisper/` and it will work offline.

## Notes

- The toolkit's `remotion-official` skill is **not** wired into `.claude/skills`: it
  is a vendored snapshot of Remotion's own router (v4.0.522) that declares the same
  frontmatter name as the upstream `remotion-best-practices` (v4.0.525) installed
  from `remotion-dev/skills`. Two skills sharing one name breaks resolution, so the
  newer upstream copy wins. The files remain under
  `vendor/claude-code-video-toolkit/.claude/skills/remotion-official`.
- The toolkit checkout is trimmed of its `examples/`, `assets/`, `showcase/`,
  `docs/` and `tests/` directories (~19 MB of demo media). Its code — `tools/`,
  `lib/`, `scripts/`, `templates/`, `brands/` — is intact, which is what its skills
  reference. For the full upstream checkout, clone it separately.
- Upstream licences: hyperframes Apache-2.0; video-use, the toolkit and whisper MIT.
