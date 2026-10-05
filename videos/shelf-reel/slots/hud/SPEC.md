# SPEC — hud v2 (exam countdown + WhatsApp voice call)

One output: `slots/hud/hud/` → window **14.300 → 51.833 s** (37.533 s = **1126 frames**), layer **front**.
Keep the v1 countdown (it was approved) and rebuild the phone call as a **WhatsApp voice call**
(see the WhatsApp look in `slots/BRIEF.md`). Sync the racing clock to the song.
Registry starting points: `number-wheel` or `number-pop-in` (digits), `count-up`; anything from
`catalog --query "phone call screen"` / `"timer pill"` that fits.

## Story
At 14.5 s the student says "...in 8 hours". A countdown to the exam appears and keeps ticking in
the corner while he calls his friend Ishaan on WhatsApp. During his breakdown (44.6 s on) time races
with the music. When the co-founders take over (51.833 s, hard cut, DROP 1) the HUD must be gone.

## Shots under this window (output s; reference frames in renders/ref/)
- 12.33-15.87 student sitting on bed, mid frame (out_014.60)
- 15.87-17.40 stands up, facepalm (out_016.50) · 17.40-18.80 at desk dialing · 18.80-20.23 laptop over-shoulder (out_018.80)
- 20.23-27.17 on the phone at his desk (out_022.00) · 27.17-34.27 Ishaan on phone (out_028.00, out_030.50)
- 34.27-39.30 third friend on phone (out_035.00, out_037.50) · 39.30-44.40 student on phone (out_040.80)
- 44.40-48.03 student at laptop: "What the f*ck, why are my notes scattered in so many groups?" (out_045.00)
- 48.03-51.83 head in hand, defeated (out_047.00, out_050.00)

## Countdown (as v1)
- "in"@14.54, "8"@14.80, "hours"@15.07.
- **Slam at 14.80**: big "08:00:00" (JetBrains Mono 800, ~180-200 px, red `--alert` with glow, tiny
  "EXAM IN" label above in Inter 700 letterspaced), centred, y ≈ 420-640 (check out_014.60). Lands
  hard: scale ~1.3→1 with blur→0 in ~0.12 s, small overshoot.
- Holds, then **15.70-16.10**: shrinks and flies into a compact HUD pill at top-left (x = 64,
  y ≈ 276): red pulsing dot + "EXAM IN 07:59:59" (`.hud-pill`, mono digits).
- Ticks DOWN once per second from 08:00:00 at 15.07 (07:59:59 at 16.07, ...).
- **Breakdown — the clock races ON THE MUSIC:**
  - 44.65 → 48.568: the display jumps forward on every 8th note (44.691 44.895 45.099 45.303 45.507
    45.711 45.915 46.119 46.324 46.528 46.732 46.936 47.140 47.344 47.548 47.752 47.956 48.160 48.364),
    each jump bigger than the last (seconds, then whole minutes).
  - 48.568 → 51.425 (the bass drops out): jumps on every 16th (every 0.102 s), minutes blur.
  - **Whole hours fall** with a hard flip + flash at **49.385**, **50.609** and **51.221** (the last two
    are the song's 808 pickups): 07 → 06 → 05 → 04. Ends around 04:1x:xx.
  - The pill turns full red and pulses on every beat (49.385, 49.793, 50.201, 50.609, 51.017, 51.425);
    digits jitter slightly.
- **51.45-51.80**: glitch-out (RGB-offset copies jitter, collapse to a line, gone). Nothing visible after 51.80.

## WhatsApp voice call (Ishaan)
- Ring tones play at **16.10-17.13** and **18.67-20.17**. **15.90**: a WhatsApp call card slides down
  from the top (centred, y ≈ 330, width ~760, WhatsApp dark glass #0B141A/#1F2C34 at ~92%):
  - top line: small WhatsApp glyph + "WhatsApp voice call" (#8696A0, Inter 500 ~24 px)
  - avatar circle with "I" (soft purple gradient), name "Ishaan" (#E9EDEF, 600 ~40 px)
  - status "Calling…" (animated dots) → **"Ringing…" at 16.10** (WhatsApp shows Ringing once the
    other phone rings)
  - a tiny lock glyph + "End-to-end encrypted" (#8696A0, ~20 px) — the WhatsApp detail people notice
  - a row of round buttons (speaker, video, mute) and a red end-call button (#EA0038), all small
  - the avatar sends out a pulse ring on each ring tone
- **Connected at 21.28** ("What's up bro?"): status becomes a timer "0:00" counting up in real
  seconds in #25D366. By ~22.0 the card collapses into a compact green pill at the top-right (right
  edge at x = 1016, y ≈ 276): WhatsApp glyph + "Ishaan 0:0x" — must not collide with the exam pill.
- **Call ends at 44.40** (cut to the laptop shot): the pill flashes red "Call ended" and slides away
  by 44.90.

Avoid covering faces in 20-44 s (heads are around y 450-1000 in those shots). Content stays at y >= 270.
