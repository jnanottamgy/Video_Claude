---
name: nullmotion
description: Null Motion's 26 ready-made HyperFrames motion templates (notification toasts, AI chat simulation, prompt typing, app-icon lineups, CTA pills and clicks, stat bars, leaderboard, line growth, candlesticks, phone mockup, kinetic headline, blur logo reveal, cinematic HUD), plus its ad-breakdown viewer that plays a finished motion-graphics ad over black-and-white per-section drafts. Use when a UI-style or social motion graphic close to one of these templates is wanted, as an overlay for footage or a standalone clip: copy the closest template, change its text, and render it with HyperFrames instead of building from scratch. Also use when someone mentions Null Motion or NullMotion. For a fully custom motion design, use /hyperframes.
---

# Null Motion

[blixvip/NullMotion](https://github.com/blixvip/NullMotion) (release 1.0.0) is a local web
app, not a packaged skill. It is fetched into `vendor/nullmotion/` and this skill wraps it.

**It has no licence, so it is never committed.** All rights stay with its author, and it ships
other creators' ads in `showcase/`. This repo is public, so:

- Never commit `vendor/nullmotion/` or a template copied from it. Both are gitignored when
  they sit in the default places.
- Templates are fine for drafts, pitches and internal work. Before a template's code or exact
  look goes into a published or client video, the user should get the author's permission
  (GitHub issue or the project's Discord), or rebuild the idea from scratch with
  `/hyperframes`. Say this when a template is headed for publication.
- Some templates show third-party trademarks (Adobe, Premiere Pro, Photoshop, After Effects,
  Claude, Gemini, Perplexity icons in `05-app-icons` and `27-icon-stack-rise`). Swap them out
  before anything is published.

## Setup

`./setup.sh` runs `scripts/fetch-nullmotion.sh`, which fetches the pinned commit. It is safe
to re-run. If `vendor/nullmotion/` is missing, run that script.

## Templates

Every template is a self-contained HyperFrames composition: a `#root` with
`data-composition-id`, one paused GSAP timeline on `window.__timelines["root"]`, and
`class="clip"` timing. Most have a **transparent background** and are styled for dark footage.

```bash
node .agents/skills/nullmotion/scripts/template.mjs                      # list all 26
node .agents/skills/nullmotion/scripts/template.mjs 07-chat-sim          # copy to edit/nullmotion/07-chat-sim/
node .agents/skills/nullmotion/scripts/template.mjs 07-chat-sim --bg '#0b0b0c'   # solid background, for MP4
```

The copy is standalone. It gets its own GSAP and shared assets (in the app they load from
one level up), and the Inter variable font that the templates name but never load. Without
Inter they fall back to a generic font. Copies go to `edit/`, which is gitignored. The script
warns if you copy into a folder that git would publish.

| Vertical 1080×1920 | Landscape 1920×1080 |
| --- | --- |
| `05-app-icons` logos rise into a lineup · `07-chat-sim` typed AI chat · `08-prompt-bar` prompt typing · `24-showreel-notify` title + phone alert · `27-cinematic-hud-overlay` sci-fi HUD (8 s) · `27-icon-stack-rise` mark unfolds into a product family | Overlays: `01-cta-pill` subscribe pill · `06-notification` toast stack · `12-blur-reveal` logo unblurs · `18-cta-click` button press · `22-kinetic-headline` one-word emphasis · `26-null-manifesto` brand statement (Null Motion's own brand: rebrand it). Explainers: `02-three-step` · `03-slide-showcase` · `04-morph-panel`. Data: `13-compare-bars` · `14-leaderboard` · `15-bar-3d` · `16-line-growth` · `10-candlestick`. UI: `17-integrations-grid` · `19-phone-showcase` · `20-search-typing` · `21-connector-list` · `23-prompt-composer` · `09-grid-network` |

Templates run 4–8 s at 30 fps. Run the script with no arguments for exact lengths.

### Adapting a template

1. Copy it, then read its `index.html` before editing: the text, colours and timings are
   inline, and the GSAP timeline sits at the bottom.
2. Change copy and colours to the user's brand, and keep every animated element's text
   length roughly the same, or re-time the tweens that reveal it. To change length, scale
   `data-duration` on `#root` and its clips together with the timeline.
3. Keep the HyperFrames contract intact: one paused timeline registered on
   `window.__timelines["root"]`, no `Math.random()` or wall-clock time, no network fetches.
   `26-null-manifesto` builds its timeline in `window.startRender()`; keep that call.
4. Render from the copy's folder:

```bash
npx --yes hyperframes@0.8.114 render . --format mov -o name.mov    # overlay: ProRes 4444 with transparency
npx --yes hyperframes@0.8.114 render . -q delivery -o name.mp4     # standalone clip
```

**Transparent templates turn white in MP4.** An MP4 cannot carry transparency, so HyperFrames
renders the background pure white, and the light text most templates use disappears. For a
standalone MP4, copy with `--bg`. For an overlay on footage, render MOV (ProRes 4444,
`yuva444p12le`) or `--format png-sequence`, and composite it (see `ffmpeg`, or
`/hyperframes` to place it in a composition). Check frames before delivering: some templates
end on an exit animation, so their last half-second is meant to look cut off.

Lint warnings such as `studio_missing_editable_id` and `nested_structure_needs_subcomposition`
are Studio-editing hints. They don't affect the render.

## The breakdown viewer (the app itself)

```bash
cd vendor/nullmotion && npm start      # http://127.0.0.1:4343, Node 22+, no install step
npm test                               # 6 tests; all pass on the pinned commit
```

- `/` is the launch-film preview: a finished ad on top, with one plain black-and-white
  HyperFrames draft per section underneath, synced frame for frame. **Download → Whole
  preview** exports it to MP4 using WebCodecs.
- `/index.html` is the template gallery, and `/editor` is a reference-timeline editor.
- Generation and rendering inside the app are deliberately not connected and return `501`.
- `public/drafts.mjs` is the draft engine. Each section is described by one or two "beats"
  (`text`, `logo`, `phone`, `window`, `input`, `chat`, `cards`, `list`, `chart`, `cloud`…).
  It's a good pattern for black-and-white animatics before polishing a motion piece.

**In a Claude Code web session the user cannot open the app.** It runs on the container's
localhost. Use Playwright screenshots to show it. Export also fails there: the bundled
Chromium has no H.264, so it can neither play the showcase films nor encode MP4. Exporting
needs Chrome or Edge on the user's own machine (`git clone` the upstream repo, then
`npm start`).

Importing your own reference ads needs the separate MotionClone project and FFmpeg
(`scripts/import-motionclone.py`, then `node scripts/plan-sections.mjs`). Imported media
stays in the app's gitignored `.local-media/` and `public/references/`.
