# SPEC — notifs v2 (WhatsApp group cards + WhatsApp notification storms)

Three outputs, all layer **front**, all WhatsApp (see the WhatsApp look in `slots/BRIEF.md`).
Registry starting points: `notification-stack` (component), `notification-pileup` (component),
`notification-cascade` (block). Rebuild the v1 choreography in each directory with the new look.

Chats (avatar = coloured circle with a simple white SVG glyph or initials, plus the WhatsApp badge):
- **Unofficial Group** (indigo #5E5CE6, two-person glyph) · **Official Class Group** (blue #0A84FF,
  graduation-cap glyph) · **Boys Group** (orange #FF9F0A, "BG") · **Ishaan** (purple gradient, "I")
- extras for the storms: **CSE 2nd Year** · **Lab Batch B** · **Hostel Wing C** · **Project Team** ·
  **Class Reps** · **Zaid** · **Mom**

Message copy (mix freely in the storms; keep each line short; no emoji):
- Unofficial Group — "CR: [pdf] Notes_unit1-5.pdf" · "CR: all the notes, units 1-5" · "47 new messages"
- Official Class Group — "Prof. Mehta: Syllabus copy attached" · "128 new messages"
- Boys Group — "Zaid: [photo] Solved PYQs (12 photos)" · "who has unit 3??" · "PYQ_2022 (blurry).jpg"
- Ishaan — "bro check the group" · "[mic] Voice message (0:42)"
- CSE 2nd Year — "@everyone exam is at 9 sharp" · "This message was deleted"
- Lab Batch B — "anyone has the record??" · Hostel Wing C — "who took my charger"
- Project Team — "Forwarded many times: unit 4 notes.pdf" · Class Reps — "sir said only units 1-3"
- Zaid — "send notes pls" · Mom — "Beta, did you eat?"
- summary banners: "47 messages from 9 chats" · "128 messages from 14 chats" · "999+ unread"
[pdf]/[photo]/[mic] = a small inline SVG glyph before the text.

## 1) `slots/notifs/cards/` — window **30.000 → 45.600 s** (15.6 s = **468 frames**)
The friends say where each set of notes is. One WhatsApp banner per mention, stacking like an iOS
lock screen (newest on top at y ≈ 330, older ones pushed down ~185 px each, slightly scaled/dimmed).
Each card lands with a quick drop from above (blur → sharp) and a green unread-count pill pulse.
- **30.22** ("unofficial group"): Unofficial Group — "CR: [pdf] Notes_unit1-5.pdf", pill 47
- **37.01** ("the official class group"): Official Class Group — "Prof. Mehta: Syllabus copy attached", pill 128
- **40.40** ("also in the boys group, Zaid sent all the solved PYQs"): Boys Group —
  "Zaid: [photo] Solved PYQs (12 photos)", pill 99+ (older cards' pills tick up as new ones arrive)
- Beats in this stretch (the groove is fading in; use them for small secondary accents only):
  37.140* 37.548 37.956s 38.365 38.773* 39.181 39.589s 39.997 40.405* 40.813 41.222s 41.630 42.038*
  42.446 42.854s 43.262 43.671* 44.079 44.487s (* bar downbeat, s = snare)
- **44.40** hard cut to the laptop shot: the stack trembles, pills pulse red-to-green fast.
- **44.65** ("What the f*ck"): the three cards BLOW APART — fly outward off-screen with rotation and
  motion blur, gone by ~45.20. Nothing visible after 45.30.
Shots: 30-34.3 Ishaan (out_030.50), 34.3-39.3 third friend (out_035.00, out_037.50),
39.3-44.4 student (out_040.80), 44.4+ laptop (out_045.00). Faces sit around y 500-1000: keep cards
in the upper band (y 300-850), overlapping shoulders rather than eyes/mouths where you can.

## 2) `slots/notifs/storm/` — window **44.600 → 51.833 s** (7.233 s = **217 frames**)
THE chaos moment, built on the song: the hi-hats build, then **the bass drops out at 48.568** (only
hats and a heartbeat remain), two 808 pickups hit at **50.609** and **51.221**, and **DROP 1 lands
at 51.833** on a hard cut to the co-founders (white flash, done by the compositor).
8th-note grid (land arrivals on these): 44.691 44.895 45.099 45.303* 45.507 45.711 45.915 46.119s
46.324 46.528 46.732 46.936* 47.140 47.344 47.548 47.752s 47.956 48.160 48.364 48.568* 48.772
48.976 49.181 49.385s 49.589 49.793 49.997 50.201* 50.405 50.609 50.813 51.017s 51.221 51.425 51.629
- **44.65** "What": burst of 6-8 WhatsApp banners from the centre outward
- **45.58** "why are my notes", **46.36** "scattered" (banners spread to every corner, rotated -14..14°,
  scales 0.55-1.0, overlapping), **47.20** "many groups?" (another wave)
- **47.87-48.57** (cut to head in hand at 48.03, out_050.00): arrivals on every 8th
- **48.568 → 51.42** (bass gone): arrivals on every **16th** (twice per 8th: 0.102 s apart), the pileup
  ACCELERATES and densifies, summary banners appear ("128 messages from 14 chats", "999+ unread"),
  the whole storm slowly rotates/drifts for vertigo. Most of the frame is covered by ~51.3 (his head
  may be partly covered — it's the climax).
- **50.609** and **51.221** (808 pickups): the whole storm JOLTS — a 3-frame scale punch (1.0 → 1.05 →
  1.0) and a white edge-glow flash on every banner.
- **51.425-51.80**: everything is sucked to the centre and collapses to nothing (fast, accelerating).
  Nothing visible after 51.80.

## 3) `slots/notifs/storm_hook/` — window **0.000 → 3.467 s** (3.467 s = **104 frames**)
The reel's COLD OPEN — frame 1 is the most important frame of the whole reel (it decides whether
people keep watching). Same laptop shot (out_000.05, out_000.60, out_001.50, out_002.40).
**Frame 1 must already show 3-4 WhatsApp banners in motion** (no empty first frame, no slow fade).
The music is the pickup bar of the drop: **DROP 1 lands at 0.797** exactly on "f*ck".
8th-note grid: 0.185 0.389 0.593 0.797*(DROP) 1.001 1.205 1.409 1.614s 1.818 2.022 2.226 2.430* 2.634
2.838 3.042 3.246s 3.450
- 0.000-0.79: a banner pops on each 8th (0.185, 0.389, 0.593) on top of the ones already there
- **0.797** DROP ("f*ck"): a big burst — 6+ banners fling outward from the laptop at once
- "why are my notes"@1.18-1.66, "scattered"@1.96 (cards fling outward again), "many groups?"@2.80-3.25
  (fast pileup of small banners on the 8ths)
- Keep his face mostly readable (he is right of centre, head around x 600-900, y 250-560 in
  out_000.60). A hook title will sit at y ≈ 300-620 centred (another layer): keep banners at
  <= 60% opacity or outside x 140-940 in that band during 0-3.3 s so the title stays readable.
- Do NOT clear at the end: the last frame stays full (the compositor freezes it and rewinds).
