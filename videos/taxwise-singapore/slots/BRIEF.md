# Graphics slots: shared brief (TaxWise Consultants, Singapore expansion)

You are building animated graphics for a 52.0 s Instagram reel (1080x1920, 30 fps). It is an announcement
film for **TaxWise Consultants**, a chartered-accountancy and finance firm from Bangalore and Chennai.
**HK Vinay**, their Managing Partner, announces their expansion into **Singapore**. It also runs on
YouTube Shorts and LinkedIn. The client asked for "studio grade, cinematic, international corporate film,
a little bit Gen Z, crazy animations, full graphics for everything he explains". It has to look like a
top agency made it for a brand launch.

## The film (output seconds; your SPEC has the details for your window)
| out | what we see | what he says |
|---|---|---|
| 0.00-6.10 | **HOOK**: HK Vinay at his desk; slow pull-out from a close-up | "Big ambitions deserve bigger horizons. And we're taking ours global." |
| 6.10-12.50 | **INTRO**: aura pull-out, then a slow push-in. The music drops out at 8.50 on "TaxWise" | "I am HK Vinay, Managing Partner at TaxWise. And I'm excited to announce our expansion into..." |
| 12.50 | **THE DROP** on "SINGAPORE": the beat slams back | "...Singapore." |
| 12.50-14.22 | full graphic: the Singapore reveal | (the word lands, then music) |
| 14.22-25.47 | full graphic: the team and the services (his voice-over) | "With a dedicated team of over thirty in-house specialists, we bring together expertise across finance, taxation, payroll, compliance and advisory." |
| 25.47-35.57 | full graphic: the globe, India to Singapore (voice-over). A new lead melody lifts at 24.50 | "From supporting businesses in India to helping them navigate Singapore's financial landscape, we are building stronger connections across borders." |
| 35.57-42.37 | HK Vinay again: aura pull-out, values on the wall behind him | "Our commitment remains the same: expertise, transparency and building lasting relationships." |
| 42.37-48.25 | HK Vinay: the last line, slow push-in | "TaxWise, now in Singapore. And trust us, this is just the beginning." |
| 48.25-52.00 | full graphic: the logo end card. The drums stop at 48.50 and a chord rings out | |

**Music:** "Timeless Instrumental", 120 BPM. One beat = 0.500 s, one bar = 2.000 s, downbeats at
0.5, 2.5, 4.5 ... 12.5 (the drop) ... 48.5 (every 2 s from 0.5). Your SPEC lists the beats in your window
(`*` = downbeat) and every spoken word with its start time. Land arrivals on beats or on the named
word: that sync is what makes the edit feel expensive. Hard hits are on the downbeats.

## Layers (say in your report which one each output is)
- **full**: an opaque 1080x1920 scene (paint the background too). It IS the picture.
- **behind**: a transparent canvas composited on the wall **under HK Vinay's cut-out**. His head and
  shoulders occlude it. Design for that: big type that tucks behind his head is the effect.
  - The compositor re-lights the wall and window behind him to a dim midnight navy (the office stays
    faintly visible), so ivory and gold read beautifully there.
  - The compositor also moves your layer with the footage's camera (zooms). Design in **source-frame
    coordinates** (below); your SPEC says how far the camera is zoomed in, which tells you what is
    visible.
- **front**: transparent, over everything (captions excepted). Keep it off his face.

**Where he is** (source coordinates, 1080x1920, the same in every shot within ~40 px; see
`renders/analysis/ref_A.jpg`, `ref_B.jpg`, `ref_E.jpg`, `ref_F.jpg` from `videos/taxwise-singapore/`):
- head (hair top to chin): x 700-910, y 800-1070; face centre about (805, 960);
- shoulders and torso: x 560-1080, y 1020-1340, then the desk hides him;
- his laptop on a stand at the left (x 0-330, y 840-1290), a phone on a stand (x 400-520, y 1110-1300);
  the desk edge is at y ~1290-1340;
- **the free wall**: everything above y ~780, and x 0-640 down to y ~1100 (left of him).
Behind-layer content must sit there. It can tuck behind his head, but never below y 1200 (the desk is
in front of the wall there).

## Look: "midnight navy, champagne gold, ivory"
The design system is `design/taxwise.css` (linked in the template); read it.
- **Navy grounds:** `.tw-ground` is a full-frame midnight navy with a soft royal-blue pool of light.
- **Ivory display type:** Cormorant Garamond, 600 (`.tw-display`), italic 500 for quotes.
- **Sans:** Montserrat, for labels (`.tw-label`, tracked caps), numbers (`.tw-num`, 800) and UI.
- **Gold:** real metal (`.tw-gold-text` gradient, `.tw-hairline`, `--tw-gold-sheen` for a light sweep),
  never flat yellow.
- **Royal blue** (`--tw-royal`, `--tw-royal-hi`) is the brand's own colour. Use it **only a little**
  (the client was explicit): a rim light, a glow, one detail. The film is navy + gold + ivory.
- **Depth:** glass cards (`.tw-glass`), soft shadows, a gentle 3D tilt (`perspective`), parallax between
  layers, a few fine gold particles or dust in light. Subtle film grain and vignetting are added later by
  the compositor: don't add your own.

**The TaxWise mark (TW shield)** is your hero asset: `design/tw-mark.js` gives `twMarkSVG({fill, stroke,
strokeWidth, cls})` and `TW_PATHS.t / .w / .diamond`. It has three parts (the arched T, the W shield, the
diamond under it; viewBox 0 0 1000 1114.1) so it can animate:
- **assemble**: the T drops in from above, the W rises, the diamond pops last with a glint;
- **draw-on**: a gold stroke traces the outlines (`stroke-dasharray`), then the fill floods in;
- **shine**: a sheen sweeps across it, clipped to the mark;
- **iris**: the shield shape grows until it fills the frame, revealing what is behind it.
- Colours: the mark is gold on navy, or ivory on navy. Never stretch it, recolour it into other hues,
  or add effects that hide its shape.
- The wordmark is **TAXWISE** (Montserrat 700, letter-spacing ~0.12em) over **CONSULTANTS** (Montserrat
  500, ~0.42em). Website: **twchartered.com**. Offices: **BANGALORE | CHENNAI | SINGAPORE**.

## Quality bar
- **Motion is premium and intentional:**
  - expo / power3 / power4 / back eases; never linear for arrivals;
  - staggered entrances; overshoot where things land;
  - fast moves get a short CSS blur (motion-blur feel) that resolves to sharp;
  - masked reveals (text rising out of a line), light sweeps on gold, numbers that count.
- **Gen-Z energy in the rhythm, not in cheap effects:** fast, punchy cuts between states on the beat;
  bold kinetic type; one or two playful touches (a satisfying "tick", a pulse ring, a cursor-like
  glint).
- **Readability:**
  - every word on screen must be readable while it holds (at least ~0.8 s fully on);
  - ivory or gold on navy, high contrast;
  - type sizes: display 90-220 px, labels 26-40 px; nothing under 24 px.
- **One idea per beat, landed hard.** Clean, generous negative space. No clutter, no stock-template
  look, no flat boxes.
- **No emoji anywhere** (the renderer has no emoji font): draw icons and flags as inline SVG.
- **No invented facts:** use only what he says and what this brief lists (30+ in-house specialists;
  finance, taxation, payroll, compliance, advisory; India, Bangalore, Chennai, Singapore; cross-border
  finance; expertise, transparency, lasting relationships; twchartered.com).
- **No other brands' logos** (generic UI conventions are fine).

## Hard technical rules
1. Canvas 1080x1920, 30 fps. behind/front: **transparent** (nothing paints the root). full: opaque.
2. Each output is its own HyperFrames project:
   - create it with `cp -r slots/_template slots/<name>` (from `videos/taxwise-singapore/`), then edit
     `slots/<name>/index.html`;
   - the template has `vendor/gsap.min.js` (CDNs are blocked here: never load scripts or fonts from the
     network) and `design/` (a symlink to the shared design system: fonts, tokens, the mark);
   - extra libraries and data you need (e.g. `slots/_shared/geo/`): **copy** them into your slot
     (`lib/`, `assets/`) and load them with relative paths.
3. t = 0 of your composition is your window start (output seconds) from the SPEC.
   - `data-duration` on the stage and the scene must equal the window length, so the render has EXACTLY
     `round(length * 30)` frames.
   - Cue times in the SPEC are output seconds: subtract the window start.
4. HyperFrames rules (read `/home/user/Video_Claude/.claude/skills/hyperframes-core/SKILL.md` and
   `/home/user/Video_Claude/.claude/skills/hyperframes-animation/SKILL.md` first):
   - one paused GSAP timeline on `window.__timelines["main"]`, and `tl.seek(0)` at the end;
   - timed elements have `class="clip"`, `data-start`, `data-duration`;
   - **deterministic only**: no Math.random, no Date.now, no requestAnimationFrame loops. Use a seeded
     PRNG (mulberry32 with a fixed seed) and drive everything from the timeline: per-frame drawing (canvas,
     a globe) goes in an `onUpdate` of a tween on a proxy object, so every frame renders from
     `tl.time()` alone;
   - use `immediateRender: false` on later tweens of an already-tweened property.
5. Always use the pinned CLI: `npx --yes hyperframes@0.8.191 ...`
   - **check**: `npx --yes hyperframes@0.8.191 check`. Fix errors; contrast warnings on a transparent
     canvas are expected.
   - **render** under the shared lock, one project at a time (several builders share this 4-core
     machine). Run this as ONE bash command with a long timeout (~20 min):
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
   - Then verify the frame count (`ls renders/png | wc -l`). Frame N (1-based) = output time window start
     + (N-1)/30.
   - **Look at your frames** (composite a few over navy, or for behind slots over
     `renders/analysis/ref_*.jpg`, with python/opencv into a contact sheet in your own scratch dir) and
     fix what is off before you report. Iterate at least once.
6. Safe zones (Instagram UI) for anything that must be read:
   - y 250-1500 and x 60-1020;
   - avoid x > 930 for y > 1100 (the like/comment rail);
   - full scenes: nothing important below y 1500 (the caption and username overlay).
   - During the talking-head sections the compositor draws captions in the band y 1300-1480: behind and
     front layers stay out of it.
7. Work ONLY inside your own slot directories.
   - Do not run git.
   - Do not modify files elsewhere (not the template, not `_shared`, not `design/`).
   - Do not copy footage or reference frames into a slot.
8. Do not ask questions. If something is ambiguous, choose the most obvious interpretation and say so in
   your report.

## Your report (final message)
For each slot:
- its name and layer, its window, and its frame count;
- its **cue list**: every arrival, slam, tick, sweep, pulse and transition with its output time and a few
  words ("14.80 counter starts", "16.34 30+ slams"). The sound designer puts an effect on each one, so be
  complete and exact;
- anything you could not do.

Keep it short.
