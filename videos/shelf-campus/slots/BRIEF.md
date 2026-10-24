# Overlay slots: shared brief (SHELF CAMPUS, founders reveal)

You are building animated graphics for a 60.7 s Instagram reel (1080x1920, 30 fps) that reveals
**SHELF CAMPUS**: "your AI-powered academic memory that lives on WhatsApp". Students send it their notes
(PDFs) in a WhatsApp chat, ask for them back later, and tell it their deadlines and reminders. No new app.

The reel is a recut of the founders' own talking-head video. **Jnanottam** (topographic-print tee, yellow
sunglasses) and **Kartik** (maroon tee, yellow sunglasses) sit at a desk; each sits on the **right half**
of the frame (head centre x ~ 760-880, head top y ~ 680-830, face y ~ 850-1250). Above and left of
them is an empty beige wall: that wall is your canvas.

The arc, and how the compositor treats the wall (you only make the graphics):
| out time | section | wall look (done by the compositor, not you) |
|---|---|---|
| 0.000-9.933 | HOOK + CHAOS: academic life as a CRIME SCENE (notes scattered across WhatsApp groups) | tense grade, red/blue police-light sweeps across the wall |
| 9.933-11.233 | freeze frame, case-file stamps | desaturated freeze, slow push |
| 11.700-22.767 | FOUNDERS (drop 1 at 11.700) | the wall is re-lit **deep navy** (person untouched); the SHELF world |
| 22.767-27.433 | REVEAL: black, a ping, the logo (drop 2 at 25.683) | full-frame graphic |
| 27.433-32.100 | "your AI-powered academic memory... that lives on WhatsApp" | deep navy wall |
| 32.100-45.500 | DEMO: the product in a WhatsApp chat | full-frame graphic |
| 45.500-56.967 | PAYOFF + CALL TO ACTION | bright, clean, warm natural wall |
| 56.967-60.667 | END CARD | full-frame graphic |

The music is "The Kill 2" (Lex Amarni & 2muchmotion): 102.89 BPM, one beat = 0.583 s, one bar =
2.333 s. Your SPEC lists the beat times inside your window (`*` = bar downbeat). Land arrivals and
accents on beats or on the spoken word the SPEC names: that is what makes the edit feel expensive.

A Python compositor stacks your renders over the graded footage. It also does: camera punch-ins and
shakes, flashes, glitches and RGB split on the footage, freeze frames, the person cut-outs (so "behind"
layers sit behind the person), the captions (their own layer), and all sound. It listens to your
report: every new card, bubble or slam you list gets its own sound on that frame.

## Layers
- **front**: over everything except captions. Keep it off faces unless the SPEC says otherwise.
- **behind**: on the wall, UNDER the person cut-out. The person's head and body occlude it; design it to
  be partly hidden (that is the effect). The compositor moves behind layers with the footage's camera.
- **full**: an opaque full-frame scene (you paint the background too). It IS the picture.

## Quality bar
Premium, high-energy, made by a top editor for a brand launch. Motion must feel expensive and intentional:
- crisp eases (expo / power3 / power4 / back), never linear for arrivals; staggered entrances; overshoot
  where something lands; fast moves get a short CSS blur (motion-blur feel) that resolves to sharp
- text always readable while it holds; nothing jittery unless it is a deliberate glitch beat
- one idea per beat, landed hard; depth (shadow, glow, glass, slight 3D tilt) instead of flat shapes
- the WhatsApp UI must look REAL at a glance (recognisable in 3 frames), then slightly elevated

## Look
**SHELF world** (`design/shelf.css`): navy glass, silver Sora type, one cool blue glow
(`--shelf-blue #4f9dff`, `rgba(var(--glow), a)`), the chrome logo mark `design/shelf-mark.png`
(446x510, transparent; a 3D chrome shelf shaped like an S). The brand lockup: the mark, then **SHELF**
(Sora 800, silver gradient) with **CAMPUS** under or beside it (Sora 600, letter-spacing ~0.32em).
**Crime-scene world** (hook only): police tape (`--tape #ffd60a` with black `--tape-ink` text),
yellow evidence tents with black numbers, red string `--string #c1121f`, red rubber-stamp ink
`--stamp #d7262f` with a worn texture. Tokens are in `design/shelf.css`.
**WhatsApp** (both worlds), dark mode, as an iPhone would show it:
- iOS banner: radius ~44 px, fill rgba(30,30,32,0.86), 1 px rgba(255,255,255,0.10) edge, big soft shadow;
  round avatar (~92 px) with a small WhatsApp app badge on its corner; title 600 ~34 px #fff; body
  "Sender: message" 400 ~30 px rgba(235,235,245,0.85); time "now" ~26 px at the right.
- chat: background #0B141A (a faint doodle wallpaper at 4-6% is fine), header #202C33 (avatar, name
  #E9EDEF 600, status "online"/"typing..." in #25D366), incoming bubbles #202C33, outgoing #005C4B,
  text #E9EDEF, timestamps #8696A0 small at the bubble's bottom-right, read ticks #53BDEB, a corner tail
  on the first bubble of a run. Document bubble: red #E5534B PDF page icon with a folded corner, file
  name, "24 pages · PDF · 3.1 MB" in #8696A0. Unread pills: #25D366 with dark #111B21 numbers.
- **SHELF Campus inside WhatsApp** is a contact: avatar = the shelf mark on a navy circle, name
  "SHELF Campus", status "online".
- The WhatsApp glyph/badge: draw it yourself as inline SVG (a #25D366 rounded square, white round
  speech-bubble outline with a small tail at the bottom-left and a phone handset inside). A ready-made
  kit is in `slots/_shared/` (`wa-kit.css`, `wa-kit.js`: banners, glyphs, a seeded keyframe sampler;
  `wa-storm.js`: a notification-storm planner). Copy what you use INTO your slot (`lib/`).
- No emoji anywhere (the renderer has no emoji font): draw every icon as SVG. No other real brands
  (no Apple logo, Google, Windows...). Generic phone hardware and iOS conventions are fine.

## Hard technical rules
1. Canvas 1080x1920, 30 fps. front/behind: **transparent background** (nothing paints the root). full: opaque.
2. Each output is its own HyperFrames project: `cp -r slots/_template slots/<name>` (from
   `videos/shelf-campus/`), then edit `slots/<name>/index.html`. The template has `vendor/gsap.min.js`
   (CDNs are blocked here: never load scripts from the network) and `design/` -> the shared design
   system (`<link rel="stylesheet" href="./design/shelf.css" />`, fonts Sora, Inter, JetBrains Mono, VT323).
   Put images you need inside the slot (e.g. `cp ../../design/shelf-mark.png assets/` or reference
   `./design/shelf-mark.png`).
3. t = 0 of your composition is your window start (output seconds) from the SPEC. `data-duration` on the
   stage and scene must equal the window length, so the render has EXACTLY `round(length * 30)` frames.
   Cue times in the SPEC are output seconds: subtract the window start.
4. HyperFrames rules: one paused GSAP timeline on `window.__timelines["main"]`, `tl.seek(0)` at the end;
   timed elements have `class="clip"`, `data-start`, `data-duration`; deterministic only (no Math.random,
   no Date.now: use a seeded PRNG such as mulberry32 with a fixed seed). Use `immediateRender: false`
   on later tweens of an already-tweened property. Read `/home/user/Video_Claude/.claude/skills/hyperframes-core/SKILL.md`
   and `/home/user/Video_Claude/.claude/skills/hyperframes-animation/SKILL.md` before authoring.
5. Always use the pinned CLI: `npx --yes hyperframes@0.8.191 ...`
   - check: `npx --yes hyperframes@0.8.191 check` (fix errors; on a transparent canvas, contrast and
     "last line" warnings are expected)
   - **render under the shared lock, one project at a time** (several builders share this machine). Run
     this as ONE bash command with a long timeout (~20 min):
     ```bash
     L=/tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/hf-render.lock
     until mkdir "$L" 2>/dev/null; do
       [ -n "$(find "$L" -maxdepth 0 -mmin +25 2>/dev/null)" ] && rmdir "$L"   # stale (>25 min): take it
       sleep 15
     done
     trap 'rmdir "$L" 2>/dev/null' EXIT
     rm -rf ./renders/png && npx --yes hyperframes@0.8.191 render . --format png-sequence -q high -o ./renders/png
     rmdir "$L"; trap - EXIT
     ```
     Then verify the frame count (`ls renders/png | wc -l`). Frame N (1-based) = output time
     window start + (N-1)/30.
6. Safe zones (Instagram UI) for anything that must be read: y 270-1500, x 64-1016, and avoid x > 940 for
   y > 1100 (the like/comment rail). During talking heads **never place anything in the caption band
   y 1290-1460** (captions own it). full scenes have no captions unless the SPEC says so.
7. Work ONLY inside your own slot directories. Do not run git. Do not modify files elsewhere (not the
   template, not `_shared`, not `design/`). Do not copy footage or reference frames into a slot.
8. Do not ask questions. If something is ambiguous, choose the most obvious interpretation and say so in
   your report.

## Use the registry first
The HyperFrames registry has polished building blocks (notification stacks, chat bubbles, typing
indicators, phone mockups, glitch text, stamps, light sweeps, count-ups...):
`npx --yes hyperframes@0.8.191 catalog --query "<what it should do>"`, install with
`npx --yes hyperframes@0.8.191 add <name> --dir . --no-clipboard`, then adapt to this look, a transparent
background, your content and timing. See `/home/user/Video_Claude/.claude/skills/hyperframes-registry/SKILL.md`.
Earlier SHELF work you may borrow from (read-only): `videos/shelf-reel/slots/` (titles behind the same
two founders, WhatsApp notification storm and cards, a WhatsApp chat with SHELF answering, an end card).

## Check your work against the real footage (from `videos/shelf-campus/`)
- `renders/ref/out_<t>.png`: ungraded footage at output time t (talking-head segments only).
- front layer: `python3 tools/preview_over.py <slot>/renders/png/frame_000040.png renders/ref/out_012.25.png /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/<name>.jpg --half`
- behind layer (person cut back on top; `--wall dark` shows the navy wall of 11.7-32.1 s):
  `python3 tools/preview_behind.py <slot>/renders/png/frame_000040.png 12.25 /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/<name>.jpg --half --wall dark`
- any other output time: `python3 tools/ref_frame.py <t> /tmp/claude-0/-home-user-Video-Claude/a453a68b-0178-511a-8cf8-a8069ad179ec/scratchpad/ref_<t>.png`
Then LOOK at the result (Read the jpg). Iterate until it looks premium over the real footage: legible,
on the beat, nothing over faces unless intended, nothing clipped, nothing in the caption band.

## Report back
For each output: absolute path of `renders/png`, window start (s), frame count, layer (front / behind /
full), one line on what it does, **the output times at which new elements appear or slam** (they drive
the sound design; say what each is: "card pops", "stamp slam", "whoosh-in", "glitch", "ping"...), and
anything the compositor must know.
