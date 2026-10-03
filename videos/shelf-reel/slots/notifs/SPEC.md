# SPEC — notifs (group-chat cards + notification storms)

Three outputs, all layer **front**. Registry starting points: `notification-stack` (component),
`notification-pileup` (component), `notification-cascade` (block). Retheme them to the
PROBLEM-world tokens in `design/shelf.css` (`.notif`: dark phone banners, red badges).

Group-chat app icon: draw your own generic chat-bubble glyph on colored rounded squares
(indigo #5E5CE6 for "Unofficial Group", blue #0A84FF for "Official Class Group",
orange #FF9F0A for "Boys Group"). File icons: generic page glyph (red for PDF, blue for
images). No real app names. Times like "now", "2m". No emoji.

Card copy to draw from (mix freely in the storms; keep each line short):
- Unofficial Group — "CR: all the notes, units 1-5" · "47 new messages"
- Official Class Group — "Teacher: syllabus copy attached" · "128 new messages"
- Boys Group — "Zaid: solved PYQs" · "who has unit 3??" · "PYQ_2022 (blurry).jpg"
- Ishaan — "bro check the group" · "voice message (0:42)"
- Files — "Notes_FINAL_v3.pdf" · "notes_unit4 (1).jpg" · "Syllabus copy.pdf"
- Reminders — "EXAM" · "did you study??"
- Mail — "Fwd: Fwd: notes" · Calendar — "Assignment due 11:59 PM"

## 1) `slots/notifs/cards/` — window **30.000 → 45.600 s** (15.6 s = **468 frames**)
The friends say where each set of notes is. One card per mention, stacking like a lock screen
(newest on top at y ≈ 330, older ones pushed down ~185 px each and slightly scaled/dimmed).
- **30.22** ("unofficial group"): Unofficial Group — "CR: all the notes, units 1-5", badge 12
- **37.01** ("the official class group"): Official Class Group — "Teacher: syllabus copy attached", badge 48
- **40.40** ("also in the boys group, Zaid sent all the solved PYQs"): Boys Group — "Zaid: solved PYQs", badge 99+
  (a red badge count can tick up on the older cards as new ones arrive)
- **44.40** hard cut to the laptop shot; the stack starts trembling (small shake, red badge pulse).
- **44.65** ("What the f*ck"): the three cards BLOW APART — fly outward off-screen with rotation
  and motion blur, gone by ~45.20. Nothing visible after 45.30.
Shots: 30-34.3 Ishaan (out_030.50), 34.3-39.3 third friend (out_035.00, out_037.50),
39.3-44.4 student (out_040.80), 44.4+ laptop (out_045.00). Faces sit around y 500-1000:
keep cards in the upper band (y 300-850) and let them overlap shoulders, not eyes/mouths
where you can avoid it.

## 2) `slots/notifs/storm/` — window **44.600 → 51.833 s** (7.233 s = **217 frames**)
THE chaos moment: "What the f*ck — why are my notes scattered in so many groups?" then 3.8 s
of him defeated, head in hand.
- **44.65** "What": burst of 6-8 cards from the centre outward to scattered positions
- **45.58** "why are my notes", **46.36** "scattered" (cards spread to every corner, rotated -14..14°,
  scales 0.55-1.0, overlapping), **47.20** "many groups?" (another wave)
- **48.03-51.4** (head in hand, out_050.00): arrivals keep ACCELERATING (pileup), badges count up,
  the whole storm slowly drifts/rotates for vertigo, density peaks around 51.3 (most of the frame
  covered, his head may be partly covered — it's the climax).
- **51.45-51.80**: everything is sucked to the centre / collapses to nothing. Nothing visible after 51.80.

## 3) `slots/notifs/storm_hook/` — window **0.000 → 3.467 s** (3.467 s = **104 frames**)
The reel's cold open (same laptop shot, out_000.60, out_002.40): a teaser of the storm, synced to
"What"@0.25, "f*ck"@0.80, "why are my notes"@1.18-1.66, "scattered"@1.96 (cards fling outward),
"many groups?"@2.80-3.25 (fast pileup of small cards). Keep his face mostly readable
(he is right of centre, head around x 600-900, y 250-560 in out_000.60). Do NOT clear at the end:
the last frame stays full (the compositor freezes it and rewinds).
