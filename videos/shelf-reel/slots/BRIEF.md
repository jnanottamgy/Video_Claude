# Overlay slots — shared brief (v2: WhatsApp-first, cut to the music)

You are building animated overlay layers for a 1:49 Instagram reel (1080x1920, 30 fps) that
teases **S.H.E.L.F**, a startup building an AI agent **that lives inside WhatsApp** and keeps your
scattered notes, files, deadlines and reminders in one place. The reel is a skit: a student wakes
at 11:51 PM with an exam in 8 hours, calls his friend Ishaan on WhatsApp, and finds every piece of
study material scattered across WhatsApp groups (Unofficial Group, Official Class Group, Boys
Group). He breaks down; then the two co-founders (Jnanottam and Kartik, both in yellow
sunglasses) explain the problem and introduce S.H.E.L.F — which you chat with on WhatsApp.

**v2 changes everything to WhatsApp.** The notifications are WhatsApp notifications, the call is
a WhatsApp voice call, the scattered stuff is WhatsApp messages/documents/voice notes, and the
payoff shows S.H.E.L.F answering inside a WhatsApp chat. The reel is now cut to a song
(Travis Scott x Vizion "My Eyes", 147 BPM, half-time feel: kick on beat 1, snare on beat 3; one
beat = 0.408 s, one bar = 1.633 s). Your SPEC lists the beat times inside your window: land
arrivals and accents on them where the SPEC says so — that is what makes the edit feel expensive.

A Python compositor stacks your renders over the graded footage. **You only make the overlay
graphics.** The compositor separately handles: footage grade, camera shake, punch-in zooms,
flashes, glitch/RGB split on footage, freeze-frame treatment, person cut-outs (so "behind"
layers sit behind the person), captions (their own layer), and all sound (it listens to your
render: every new card/bubble that appears gets its own pop, on the frame it appears).

## Quality bar
Premium, high-energy, made-by-a-top-editor. Motion must feel expensive and intentional:
- crisp eases (expo/power3/power4/back), never linear; staggered arrivals; overshoot where it lands
- fast moves get a short CSS blur (motion-blur feel) that resolves to sharp
- text always readable when it holds; nothing jittery unless it is a deliberate glitch beat
- restraint: one idea per beat, but make that idea land hard
- the WhatsApp UI must look REAL at a glance (a viewer should recognise it in 3 frames), then
  slightly elevated: richer depth, glow, glass, motion — not a flat screenshot

## WhatsApp look (required, v2)
The student's phone is an iPhone in dark mode, so notifications are **iOS banners in dark mode
showing WhatsApp messages**, and chats are **WhatsApp dark mode**:
- iOS banner: rounded rect radius ~44 px, fill rgba(30,30,32,0.82) with `backdrop-filter: blur`
  feel (fake it with a soft inner gradient), 1 px rgba(255,255,255,0.10) edge, big soft shadow.
  Left: the chat's round avatar (~92 px) with a small **WhatsApp app badge** (~38 px rounded square)
  overlapping its bottom-right corner. Text (Inter): title = chat name (600, ~34 px, #FFFFFF);
  body = "Sender: message" (400, ~30 px, rgba(235,235,245,0.85)); right: "now" / "2m"
  (~24 px, rgba(235,235,245,0.55)). Grouped notifications read like "12 new messages".
- WhatsApp badge/app icon: draw it yourself as inline SVG: a #25D366 rounded square (radius 24%)
  with the white glyph — a round speech bubble outline with a small tail at the bottom-left and a
  phone handset inside. No downloaded logo files.
- WhatsApp dark-mode chat: background #0B141A (subtle doodle wallpaper allowed at 4-6% opacity),
  header bar #202C33 with avatar + name (#E9EDEF, 600) + status ("online" / "typing…" in #25D366),
  incoming bubbles #202C33, outgoing bubbles #005C4B, text #E9EDEF, timestamps #8696A0 (small,
  bottom-right inside the bubble), read ticks #53BDEB (two small check marks), bubbles have the
  little corner tail on the first bubble of a run. Sender names in groups use WhatsApp's
  per-person colours (e.g. #53BDEB, #FFB74D, #F06292, #A5D6A7, #CE93D8).
- Document bubble: a PDF icon (red #E5534B page with a folded corner), file name, "14 pages · PDF ·
  2.1 MB" line in #8696A0. Photo bubble: rounded thumbnails (draw blurry paper-texture rectangles,
  never real photos). Voice note: play triangle, waveform bars, "0:47", green mic dot.
- Accents: WhatsApp green #25D366 (badges, unread counts — green circle with dark #111B21 number),
  teal #00A884 for buttons.
- S.H.E.L.F's own world keeps the design system in `design/shelf.css` (navy glass, silver Sora,
  blue glow, `design/shelf-mark.png`). Where S.H.E.L.F appears INSIDE WhatsApp (as a contact /
  business chat), use the WhatsApp UI with the shelf mark as its avatar and "S.H.E.L.F" as its name.
- No emoji anywhere (the renderer has no emoji font) — draw any icon as SVG. No other real brands
  (no Google, Apple logo, Gmail, Drive…). iOS UI conventions are fine.

## Hard technical rules
1. Canvas 1080x1920, 30 fps, **transparent background** (nothing paints the root/stage).
2. Each output is its own HyperFrames project directory (already scaffolded, with
   `vendor/gsap.min.js` and `design/` → the shared design system). `design/shelf.css` has fonts
   (Sora, Inter, JetBrains Mono, VT323), tokens and base components. Link it with
   `<link rel="stylesheet" href="./design/shelf.css" />`. A NEW slot is created by copying
   `slots/_template` (`cp -r slots/_template slots/<group>/<name>` then edit its index.html).
3. t = 0 of your composition is the window start given in your SPEC (output-timeline seconds).
   `data-duration` on the stage must equal the window length, so the render has EXACTLY
   `round(length * 30)` frames. Cue times in the SPEC are output-timeline seconds: subtract
   the window start.
4. HyperFrames rules: one paused GSAP timeline on `window.__timelines["main"]`, `tl.seek(0)`
   at the end; timed elements have `class="clip"`, `data-start`, `data-duration`; deterministic
   only (no Math.random / Date.now — use a seeded PRNG such as mulberry32 with a fixed seed).
   Use `immediateRender: false` on later tweens of an already-tweened property.
5. Always use the pinned CLI: `npx --yes hyperframes@0.8.114 ...`
   - check: `npx --yes hyperframes@0.8.114 check` (fix errors; transparent-canvas contrast
     warnings are expected and fine)
   - render: `npx --yes hyperframes@0.8.114 render . --format png-sequence -q high -o ./renders/png`
   - **Render lock (several builders share this machine's disk):** wrap EVERY full render in the
     lock below, and render one project at a time. Quick `check` runs need no lock.
     ```bash
     L=/tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/hf-render.lock
     until mkdir "$L" 2>/dev/null; do
       [ -n "$(find "$L" -maxdepth 0 -mmin +30 2>/dev/null)" ] && rmdir "$L"   # stale (>30 min): take it
       sleep 20
     done
     trap 'rmdir "$L" 2>/dev/null' EXIT
     rm -rf ./renders/png && npx --yes hyperframes@0.8.114 render . --format png-sequence -q high -o ./renders/png
     rmdir "$L"; trap - EXIT
     ```
     Run that as ONE bash command (with a long timeout, ~20 min). Verify the frame count after.
6. Safe zones (Instagram UI): keep content at y >= 270 and y <= 1500, x in 64..1016, and avoid
   x > 940 for y > 1100 (like/comment rail). **Never place anything in the caption band
   y 1290-1460** — captions are a separate layer there. Don't cover faces unless the SPEC says the
   moment is meant to be overwhelming.
7. Work ONLY inside your own slot directories. Do not run git. Do not modify files elsewhere.
   Do not copy footage or reference frames into your slot directory.
8. Do not ask questions. If something is ambiguous, choose the most obvious interpretation.

## Use the registry first
The HyperFrames registry (`npx --yes hyperframes@0.8.114 catalog --query "<what it should do>"`)
has polished building blocks (notification stacks, chat bubbles, typing indicators, phone
mockups…). Install with `npx --yes hyperframes@0.8.114 add <name> --dir . --no-clipboard`, then
adapt: WhatsApp look, transparent background, your content and timing. Read
`/root/.claude/skills/hyperframes-registry/SKILL.md` for wiring blocks/components, and
`/root/.claude/skills/hyperframes-core/SKILL.md` + `/root/.claude/skills/hyperframes-animation/SKILL.md`
before authoring. (`/root/.claude/skills/hyperframes/SKILL.md` is the router if you need more.)
A previous (v1, non-WhatsApp) version of your slot already exists in its directory: read it for
the choreography that was approved, then rebuild the look. Its v1 renders are backed up.

## Check your work against the real footage
`renders/ref/out_<t>.png` (in `videos/shelf-reel/`) are footage frames at output time t.
They still show the OLD burned-in yellow captions near y=1375, which will be removed:
ignore those. After rendering, composite frames over the matching reference and LOOK:

    cd /home/user/Video_Claude/videos/shelf-reel
    python3 tools/preview_over.py <slot>/renders/png/frame_000040.png renders/ref/out_045.00.png /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/<name>.jpg --half

(Frame N of a render is output time = window start + (N-1)/30.) Make your own reference frames
for any other time with `python3 tools/ref_frame.py <t> /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/ref_<t>.png`.
Iterate until it looks premium over the real footage: legible, recognisably WhatsApp, nothing
over faces unless intended, nothing clipped, nothing in the caption band.

## Report back
For each output: absolute path of `renders/png`, window start (s), frame count, layer
(`front` or `behind`), one line on what it does, the times at which new cards/bubbles appear
(they drive the sound), and anything the compositor must know.
