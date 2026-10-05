# SPEC — viral v2 (the hook title on frame 1, the "send this" end card)

Two NEW slots: create each by copying the template (`cp -r slots/_template slots/viral/<name>`),
then build its index.html. Layer **front**. Read `slots/BRIEF.md` first (WhatsApp look, rules,
render lock). These two layers exist for one reason each, backed by Instagram's own guidance:
the ranker predicts whether people skip in the first 3 seconds, and "sends" (people DMing the reel
to a friend) are the strongest signal for reaching non-followers.

## 1) `slots/viral/hook_title/` — window **0.000 → 3.467 s** (**104 frames**)
The reel's first frame IS the thumbnail and the scroll-stopper. Footage: a student at his laptop
mid-breakdown under an exploding WhatsApp notification storm (another layer), shouting "What the
f*ck, why are my notes scattered in so many groups?" (references: renders/ref/out_000.05.png,
out_000.60.png, out_001.50.png, out_002.40.png — ignore the old yellow captions near y 1375).
- Text (Sora 800, tight tracking, the biggest type in the reel):
  line 1 **"14 groups."** (white), line 2 **"0 notes."** (WhatsApp green #25D366).
  ~118-132 px cap height, centred, inside **y 300-640** (Instagram's best hook zone: 15-35% of the
  height). Must read in under a second over a chaotic background: give it a heavy soft dark
  shadow / outline and, if needed, a dark rounded plate behind (rgba(8,12,18,0.55), radius 36).
- **Fully visible on frame 1** (no fade-in): it starts at full opacity with a tiny settle
  (scale 1.06 → 1.0 over the first 5 frames).
- A small red pill above line 1, "EXAM IN 8 HRS" (Inter 800, letterspaced, #FF3B30 fill, white text),
  pops in on **0.389** (a beat).
- **0.797 = DROP 1** on "f*ck": the whole title PUNCHES (scale 1.0 → 1.12 → 1.0 over ~6 frames, a
  2-frame RGB split, a white flash on the letter edges), then sits; a subtle beat pulse
  (1.0 → 1.02 → 1.0) on 1.614 and 2.430.
- **3.25-3.40**: it glitches out (RGB-offset slices, 3-4 frames) — gone by 3.40. Nothing after 3.40.
- Keep his face (x 600-900, y 250-560 in out_000.60) as clear as the layout allows: the title can
  overlap the top of his head but not his eyes/mouth.

## 2) `slots/viral/cta_end/` — window **105.000 → 108.567 s** (3.567 s = **107 frames**)
The ending. Footage: the S.H.E.L.F logo on the bedroom wall with "LAUNCHING SOON" typed on the
right wall (the team's own reveal), then a freeze on that frame from 107.0 (references:
renders/ref/out_104.50.png, out_108.00.png). The reel then loops straight back to frame 1.
Beats (drop 2 continues): 105.306s 105.714 106.122* 106.530 106.938s 107.347 107.755* 108.163
- **106.122** (bar downbeat): a WhatsApp/iMessage-style message bubble pops up from below (white
  #FFFFFF bubble, radius 40, slight shadow, dark text Inter 700 ~44 px):
  **send this to the friend who says**
  **"check the other group"** (this line in #00A884 or bold)
  with a paper-plane "send" glyph (generic, drawn in SVG) at the right that does a little fly-off
  wiggle on **106.938** and **107.755**.
- Position: centred, **y ≈ 1000-1250** (above the Instagram caption area; nothing below 1260), never
  over the wall logo or the "LAUNCHING SOON" text — check both references.
- It holds to the last frame (the last frame must still show it, fully legible).
- Optional: a tiny "S.H.E.L.F · launching soon on WhatsApp" lower tag under the bubble (Inter 600,
  ~26 px, silver) that fades in on 107.347.
