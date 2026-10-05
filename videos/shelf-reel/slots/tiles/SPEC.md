# SPEC — tiles v2 (the problem as scattered WhatsApp messages; then S.H.E.L.F answers in WhatsApp)

Two outputs, layer **front**, WhatsApp look (see `slots/BRIEF.md`). The v1 choreography (glass tiles
popping on words, multiplying, orbiting, tangling, then docking into one panel) was approved: keep
it, but every "tile" is now a **WhatsApp dark-mode message bubble from a different chat** — a tiny
coloured sender/chat label on top, then the content. Registry ideas: `catalog --query "chat bubble"`,
`"message stack"`, `"cards orbit"`, `"connection lines graph"`, `"phone mockup"`, `"typing indicator"`.

The six bubble types (each with a clean inline-SVG glyph; mix chats and file names when multiplying):
- FILES → document bubble: [pdf] "Unit3_Notes_FINAL_v2.pdf · 14 pages" (Unofficial Group)
- INFORMATION → text bubble with the grey "Forwarded many times" label: "exam hall changed to Block C"
  (CSE 2nd Year)
- DEADLINES → pinned-message bubble (pin glyph, red clock): "Assignment due 11:59 PM" (Official Class Group)
- REMINDERS → voice-note bubble: play triangle + waveform + "0:47" (Mom / Ishaan) or "lab record tomorrow!!"
- DOCUMENTS → doc / photo bubbles: "Syllabus_copy.pdf", "IMG_2034.jpg", "PYQ_2022 (blurry).jpg" (Boys Group)
- PERSONAL INFO → doc bubbles: "Hall_ticket.pdf", "Fee_receipt.pdf", "ID_card.jpg" (Project Team / Mom)

## 1) `slots/tiles/problem/` — window **70.133 → 83.433 s** (13.3 s = **399 frames**)
Music: the full first drop. Quarter-note beats (* bar, s snare): 70.200 70.608s 71.017 71.425*
71.833 72.241s 72.649 73.057* 73.465 73.874s 74.282 74.690* 75.098 75.506s 75.914 76.323* 76.731
77.139s 77.547 77.955* 78.363 78.771s 79.180 79.588* 79.996 80.404s 80.812 81.220* 81.628 82.037s
82.445 82.853* 83.261. The word cues come first; when a multiply/pop has no word cue, put it on
these beats or on the 8ths between them. Every bubble on screen gives a tiny scale pulse
(1.0 → 1.025 → 1.0) on each bar downbeat (*).

Shot A 70.20-77.03 — Jnanottam in front of a bathroom mirror (out_070.50, out_072.50, out_075.00):
"your files are everywhere, your information is everywhere, your deadlines, your reminders,
your documents, your personal information"
- **70.374** "files": the FILES bubble pops in near him (not over his face)
- **70.944** "everywhere": it multiplies into ~7 smaller copies scattered around the frame (staggered
  pops on the 8ths: 70.944, 71.05, 71.15…)
- **71.794** "information": INFORMATION bubble; **72.454** "everywhere": it multiplies the same way
- **73.544** DEADLINES · **74.104** REMINDERS · **74.974** DOCUMENTS · **75.684** PERSONAL INFO
- by ~76.5 the frame is cluttered with ~22-26 bubbles of mixed sizes (0.45-0.85), slight rotations,
  all drifting slowly
Shot B 77.03-80.63 — Kartik sitting, holding a can (out_078.00):
"and somehow you're expected to remember all of it"
- at the 77.034 cut the bubbles swirl into orbits around HIS head (2-3 rings, perspective tilt, in
  front of and behind the head via scale/opacity), accelerating through **77.574** "somehow",
  **78.944** "remember"; at **79.484-80.094** "all of it" the orbit spins fastest and tightest (overload)
Shot C 80.63-83.37 — Jnanottam in a dark wardrobe nook (out_081.50):
"but doesn't it sound a little complicated?"
- at 80.634 the bubbles scatter to random spots and get connected by tangled glowing lines (thin
  strands crossing everywhere, WhatsApp-green turning red), growing through **81.034** "but doesn't
  it", **81.864** "sound a little", peaking at **82.214** "complicated?" (lines pulse red, slight jitter)
- **83.334-83.40**: everything vanishes in 2 frames (hard reset — the music resets too; the next line
  is "the problem we're solving is pretty simple"). Nothing visible after 83.40.

## 2) `slots/tiles/oneplace/` — window **89.033 → 92.767 s** (3.733 s = **112 frames**)
THE PAYOFF: S.H.E.L.F is an AI agent you chat with **on WhatsApp**. DROP 2 (the biggest, most
hyped part of the song) has just hit at 88.167 on the word "S.H.E.L.F". Kartik lies on a bed,
hands steepled (out_089.60, out_091.60): "an agent that helps you keep all of it in one place".
8th-note grid: 89.184 89.388 89.592 89.796* 90.000 90.204 90.408 90.612s 90.816 91.021 91.225
91.429* 91.633 91.837 92.041 92.245s 92.449 92.653.
- **89.033-89.388**: a floating WhatsApp chat (a glass phone card with a slight 3D tilt, ~600 px
  wide) flies in with motion blur and lands on **89.388**. Header: the S.H.E.L.F avatar
  (`design/shelf-mark.png` in a dark-navy circle), name **"S.H.E.L.F"** (#E9EDEF, 600), status
  "online" (#25D366). A few small message silhouettes from the problem section can streak in and
  dock into it on the way (the chaos becoming one chat).
- **89.592** ("an agent"): outgoing bubble (#005C4B): "where are the unit 3 notes??" + blue ticks
- **89.796**: header status → "typing…" (#25D366) and a typing-dots bubble
- **90.204**: incoming doc bubble: [pdf] "Unit3_Notes_CR.pdf · 14 pages" + a small chip
  "from Unofficial Group"
- **90.612**: doc bubble: [pdf] "Syllabus_copy.pdf · 3 pages" + chip "from Official Class Group"
- **91.021**: photo-album bubble (4 blurry paper thumbnails, "+8") "Solved PYQs 2019-24" + chip
  "from Boys Group"
- **91.429**: text bubble: "Exam at 9:00 AM. I'll remind you at 7:30." with a small bell glyph
- **92.245** ("place"): the whole chat glows; a light sweep crosses it; the "S.H.E.L.F" name in the
  header shimmers silver → blue. Hold to the end: **the last frame must still show the full chat**.
Every bubble pops on its 8th with a small overshoot. Keep his face clear (check the reference
frames); the chat may overlap his shoulder/chest/hands. Nothing in the caption band y 1290-1460.
