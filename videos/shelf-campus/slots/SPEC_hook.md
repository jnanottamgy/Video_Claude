# SPEC: hook (4 outputs): the scroll-stopper and the "crime scene"

Read `slots/BRIEF.md` first. Concept for the hook: **your academic life is a crime scene**. The missing
notes are the victim, WhatsApp groups are where the evidence is scattered. Police tape, evidence tents,
case-file stamps, all mixed with real-looking WhatsApp UI. Tense, funny, fast.

Beats in this stretch (song intro, muffled, no drums yet): 0.070* 0.653 1.236 1.819 2.403* 2.986 3.569
4.152 4.735* 5.318 5.901 6.485 7.068* 7.651 8.234 8.818 9.401*. The music tape-stops at 9.93 and the
stamps play in silence (the compositor puts a big hit on each slam).

## 1) `slots/hook_title/` · front · 0.000 → 2.600 (78 frames)
Shot: Jnanottam to camera (refs `renders/ref/out_000.05.png`, `out_001.23.png`, `out_002.41.png`), head
top y ~ 680-740, face x ~ 640-940, y ~ 850-1150. He says "Your phone has 256 gigs of storage."
- **Frame 1 must already read** (it is the thumbnail and the scroll-stopper): two strips of yellow police
  tape ("CRIME SCENE · DO NOT CROSS · CRIME SCENE ·", black Inter 800 / Sora 800 caps, slight fabric sheen
  and soft shadow) crossing the TOP of the frame diagonally (one ~ -9°, one ~ +6°), bleeding off both edges,
  inside y ~ 250-640, never over his face.
- Title on the tape area (Sora 800, the biggest type of the hook, white with a heavy dark soft shadow / thin
  black outline so it reads over a busy wall), centred, inside y 300-640:
  line 1 **"YOUR ACADEMIC LIFE"**, line 2 **"IS A CRIME SCENE."** (line 2 in `--tape` yellow, or white on
  a black tape strip: your call). Fully visible on frame 1 with only a tiny settle (scale 1.04 → 1.0 over
  5 frames). Small pulse on 0.653 and on the bar 2.403 (scale 1 → 1.03 → 1).
- Exit: at **2.40-2.55** the tape snaps away (one strip whips off left, the other right, with blur) and the
  title collapses (scale down + slice glitch). Fully gone by 2.567. Nothing after that.

## 2) `slots/storage_behind/` · behind · 0.000 → 2.467 (74 frames)
Same shot. On the wall just above / around his head (his hair should cover part of it), an oversized
**storage meter** in iOS settings style, dark glass card ~ 860 px wide, centred x ~ 540, y ~ 640-900
(below the title, above his eyes; check with `tools/preview_behind.py ... 1.2`):
- header "Storage" (Inter 700) and a big counter (Sora 800): "**255.9 GB** of 256 GB used".
- a segmented bar: Photos (yellow), Apps (blue), System (grey), and a huge **WhatsApp** segment (green,
  labelled "WhatsApp · 214 GB"), filling left to right.
Cues (his words): "two-fifty-six" 0.54-1.40 (the counter rolls 0 → 256 fast and lands on 1.40), "gigs"
1.42, "storage" **1.90**: the bar hits 100%, turns red (`--alert`) with a "Storage Full" red pill, a short
shake. Holds to the end of the window (hard cut at 2.467).

## 3) `slots/storm_behind/` · behind · 2.467 → 4.267 (54 frames)
Shot: Kartik (refs `out_002.52.png`, `out_003.37.png`, `out_004.21.png`): "And you still can't find the
[BLEEP] notes?" (still 2.71, can't 2.87, find 3.19, the bleep 3.39-3.79, "notes?" **3.83**).
A WhatsApp **notification storm** on the wall around and above him (behind him): iOS banners piling up,
fast, on the 8ths and 16ths of 2.403* 2.986 3.569 4.152 (start ~2.50, densest ~3.4-3.9). Groups: "DBMS
2nd Yr", "CSE-B Official", "Boys Group", "Unofficial CSE", "Lab Batch B", "Class Reps", "Exam Doubts".
Lines (no emoji): "anyone has unit 3 notes??", "check the other group", "who has the DBMS pdf",
"bro send notes", "This message was deleted", "notes kahan hai", "47 new messages", "PDF pls". The
`wa-storm.js` planner in `slots/_shared/` does this choreography: reuse it. At **3.83** ("notes?") a
WhatsApp search bar card slams in front of the storm (still behind him), with "notes" typed in it and
"No results found" in red-ish grey. Hard cut at 4.267.

## 4) `slots/stamps/` · front · 9.933 → 11.233 (39 frames)
Picture: a FREEZE FRAME of Kartik mid-"assignment!" (ref `out_009.98.png`, `out_010.58.png`; the
compositor desaturates it and pushes in slowly). Silence. Two red rubber stamps (`--stamp`, worn ink
texture, double rule border, Sora 800 / a heavy condensed caps), each slams from scale ~1.6 with a 2-frame
blur, lands with a tiny bounce and an ink-spatter puff:
- **9.95**: "ACADEMIC WEAPON." rotated ~ -8°, upper-left area (y ~ 380-560)
- **10.53**: "ORGANISATIONAL DISASTER." rotated ~ +5°, below it (y ~ 600-800), overlapping the first a bit
- optional: a small typewriter "CASE #0047 · SUBJECT: KARTIK" tag (JetBrains Mono, paper label) at 10.10
Hold to the end (hard cut to Jnanottam at 11.233). Keep his face (x 700-1060, y 830-1260) clear.
