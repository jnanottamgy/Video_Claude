# SPEC: founders (7 outputs): the drop, the names, the poster, "lose their minds", "built something"

Read `slots/BRIEF.md` first. From the drop at **11.700** the wall behind the founders is re-lit **deep
navy** by the compositor (preview with `--wall dark`): this is the SHELF world (silver Sora, blue glow).
The compositor adds a white flash + shockwave on 11.700 and on 14.033.

Beats (drop 1, full drums): 11.700* 12.284 12.867 13.450 14.033* 14.616 15.199 15.782 16.366* 16.949
17.532 18.115 18.698* 19.281 19.864 20.448 21.031* 21.614 22.197. At **22.767** the bass stops and the
picture hard-cuts to black.

## 1) `slots/name_j_behind/` · behind · 11.233 → 13.433 (66 frames)
Jnanottam (refs `out_011.28.png`, `out_012.25.png`, `out_013.21.png`): "I'm" 11.30 (in silence), then
**"JNANOTTAM" on the drop 11.700**. 13.267-13.433 is a freeze of him.
- "JNANOTTAM" giant (`.giant`: Sora 800, silver gradient, blue glow), one line spanning the frame
  (it may bleed off both edges), placed so his head covers part of it (baseline ~ y 860-900; his head top
  is ~ y 700-740). Nothing before 11.700. On 11.700 the letters SLAM in (staggered 1 frame each from the
  centre out, scale 1.35 → 1 with blur → sharp, white-hot for 3 frames then silver), a light sweep across
  on 12.284, a slow drift/zoom (1.0 → 1.04) to the end, a glow pulse on 12.867 and on the freeze 13.267.

## 2) `slots/name_k_behind/` · behind · 13.433 → 15.200 (53 frames)
Kartik (refs `out_013.48.png`, `out_014.32.png`, `out_015.14.png`): "I'm" 13.76, **"KARTIK" on the bar
14.033**. Same treatment as JNANOTTAM (bigger: 6 letters), his head (x ~ 700-1060, top y ~ 820) covering
the right part of the word. Slam on 14.033, sweep on 14.616, hold to the cut.

## 3) `slots/lowers/` · front · 11.233 → 15.200 (119 frames)
Lower thirds, left side, x 64-620, y ~ 1130-1270 (above the caption band; faces are on the right):
navy glass bar with a blue edge glow, name in Sora 700 caps, role in Inter 600 letterspaced.
- "JNANOTTAM" / "CO-FOUNDER": in on **11.80** (wipe from the left, 0.3 s), out by 13.40.
- "KARTIK" / "CO-FOUNDER": in on **14.10**, out by 15.18.
(No company name yet: SHELF CAMPUS is revealed later.)

## 4) `slots/poster_bg/` · full · 15.200 → 18.100 (87 frames)  and  5) `slots/poster_text/` · front · same window
"TWO FOUNDERS." A poster moment with no dialogue (music only). The compositor composites BOTH founders cut
out of their shots, side by side: Jnanottam on the left (head ~ x 300, y 930-1150), Kartik on the right
(head ~ x 895, y 1000-1220), bodies to the bottom edge. See `renders/ref/split_people.png` (RGBA, the
exact layout) and `renders/ref/split_preview.jpg`. Stack: poster_bg, then the two cut-outs, then poster_text.
- **poster_bg** (opaque): deep navy studio backdrop with depth: a soft radial blue glow behind their heads,
  a faint perspective grid / light beams, a few drifting dust particles, a slow push. Subtle; they are the
  subject. No text here.
- **poster_text** (transparent): three lines stacked in y ~ 300-820, each SLAMS on a beat (Sora 800,
  silver, white-hot on arrival, blue glow):
  **15.199** "TWO FOUNDERS." · **15.782** "ONE SHARED BRAIN CELL." · **16.366** "QUESTIONABLE SLEEP SCHEDULE."
  (scale the lines so each fits x 64-1016; line 1 the biggest). On 16.949 a small detail lands, e.g. a
  thin rule and "EST. 2026" or "CO-FOUNDERS" tags pointing to each of them. Gentle beat pulse on 17.532.
  Exit fast at 18.0-18.1 (the next shot hard-cuts in).

## 6) `slots/minds_behind/` · behind · 18.100 → 21.100 (90 frames)
Jnanottam (refs `out_018.15.png`, `out_019.60.png`, `out_021.04.png`): "We got tired of watching students
lose their minds." We 18.20, got 18.55, tired 18.87, watching 19.35, students **19.67**, lose **20.15**,
their 20.39, minds **20.63**.
On the navy wall, upper-left: on "students" a small crowd of stressed messages pops (WhatsApp bubbles:
"exam tomorrow??", "which unit is in syllabus", "send notes", "I'm cooked") stacking fast; on "lose their
minds" a system error dialog SLAMS in: title "brain.exe", text "brain.exe has stopped responding",
buttons [Wait] [Close the program], with a red error icon; on 20.63 it glitches/duplicates (cascading
copies, classic error-window cascade) until the cut. Keep it out of his face.

## 7) `slots/built_behind/` · behind · 21.100 → 22.767 (50 frames)
Kartik (refs `out_021.15.png`, `out_021.93.png`, `out_022.71.png`): "So we built something for it."
So 21.20, built **21.57**, something **22.13**, for it 22.45-22.69.
Foreshadowing: on the navy wall above/left of him, a **blueprint** of the SHELF mark draws itself in thin
glowing blue lines (construction lines, dimension ticks, a grid): starts on "built" 21.57, completes on
"something" 22.13 (lines flash brighter), small label "PROJECT: ??? · v0.1" (JetBrains Mono). On 22.60-
22.76 everything powers down (flicker out): the picture cuts to black at 22.767.
