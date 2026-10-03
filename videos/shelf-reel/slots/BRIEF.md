# Overlay slots — shared brief

You are building animated overlay layers for a 1:49 Instagram reel (1080x1920, 30 fps) that
teases **S.H.E.L.F**, a startup building an AI agent that keeps your scattered files, notes,
deadlines and reminders in one place. The reel is a skit: a student wakes at 11:51 with an
exam in 8 hours, phones friends for notes, finds them scattered across group chats
(Unofficial Group, Official Class Group, Boys Group), breaks down; then the two co-founders
(Jnanottam and Kartik, both in yellow sunglasses) explain the problem and introduce S.H.E.L.F.

A Python compositor stacks your renders over the graded footage. **You only make the overlay
graphics.** The compositor separately handles: footage grade, camera shake, punch-in zooms,
flashes, glitch/RGB split on footage, freeze-frame treatment, person cut-outs (so "behind"
layers sit behind the person), captions (their own layer), and all sound.

## Quality bar
Premium, high-energy, made-by-a-top-editor. Motion must feel expensive and intentional:
- crisp eases (expo/power3/power4/back), never linear; staggered arrivals; overshoot where it lands
- fast moves get a short CSS blur (motion-blur feel) that resolves to sharp
- text always readable when it holds; nothing jittery unless it is a deliberate glitch beat
- restraint: one idea per beat, but make that idea land hard

## Hard technical rules
1. Canvas 1080x1920, 30 fps, **transparent background** (nothing paints the root/stage).
2. Each output is its own HyperFrames project directory (already scaffolded for you from
   `slots/_template`, with `vendor/gsap.min.js` and `design/` → the shared design system).
   `design/shelf.css` has fonts (Sora, Inter, JetBrains Mono, VT323), color tokens and base
   components (`.notif`, `.tile`, `.giant`, `.hud-pill`). Link it with
   `<link rel="stylesheet" href="./design/shelf.css" />` and use its tokens. `design/shelf-mark.png`
   is the glass S.H.E.L.F logo mark (510x446, transparent).
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
6. No emoji (the renderer has no emoji font). No real brand names or logos (no WhatsApp,
   Google, Apple, Gmail, Drive…). Draw generic icons as inline SVG.
7. Safe zones (Instagram UI): keep content at y >= 230 and y <= 1500, x in 64..1016, and avoid
   x > 940 for y > 1100 (like/comment rail). **Never place anything in the caption band
   y 1290-1460** — captions are a separate layer there.
8. Work ONLY inside your own slot directory. Do not run git. Do not modify files elsewhere.
   Do not copy footage or reference frames into your slot directory.
9. Do not ask questions. If something is ambiguous, choose the most obvious interpretation.

## Use the registry first
The HyperFrames registry (`npx --yes hyperframes@0.8.114 catalog --query "<what it should do>"`)
has polished building blocks; your SPEC names the ones to start from. Install with
`npx --yes hyperframes@0.8.114 add <name> --dir . --no-clipboard`, then adapt: retheme to
`design/shelf.css`, transparent background, your content and timing. Read
`/root/.claude/skills/hyperframes-registry/SKILL.md` for wiring blocks/components, and
`/root/.claude/skills/hyperframes-core/SKILL.md` + `/root/.claude/skills/hyperframes-animation/SKILL.md`
before authoring. (`/root/.claude/skills/hyperframes/SKILL.md` is the router if you need more.)

## Check your work against the real footage
`renders/ref/out_<t>.png` (in `videos/shelf-reel/`) are footage frames at output time t.
They still show the OLD burned-in yellow captions near y=1375, which will be removed:
ignore those. After rendering, composite frames over the matching reference and LOOK:

    cd /home/user/Video_Claude/videos/shelf-reel
    python3 tools/preview_over.py <slot>/renders/png/frame_000040.png renders/ref/out_045.00.png /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/<name>.jpg --half

(Frame N of a render is output time = window start + (N-1)/30.) Iterate until it looks
premium over the real footage: legible, nothing over faces unless intended, nothing clipped.

## Report back
For each output: absolute path of `renders/png`, window start (s), frame count, layer
(`front` or `behind`), one line on what it does, and anything the compositor must know.
