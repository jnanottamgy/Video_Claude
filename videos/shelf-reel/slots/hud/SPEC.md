# SPEC — hud (exam countdown + phone call UI)

One output: `slots/hud/hud/` → window **14.300 → 51.833 s** (37.533 s = **1126 frames**), layer **front**.
Registry starting points: `number-wheel` or `number-pop-in` (digits), `count-up`;
anything from `catalog --query "phone call screen"` / `"timer pill"` that fits.

## Story
At 14.5 s the student says "...in 8 hours". A countdown to the exam appears and keeps ticking
in the corner while he phones his friend Ishaan. During his breakdown (44.6 s on) time races.
When the co-founders take over (51.833 s, hard cut to a calm new scene) the HUD must be gone.

## Shots under this window (output s; reference frames in renders/ref/)
- 12.33-15.87 student sitting on bed, mid frame (out_014.60)
- 15.87-17.40 stands up, facepalm (out_016.50) · 17.40-18.80 at desk dialing · 18.80-20.23 laptop over-shoulder (out_018.80)
- 20.23-27.17 on the phone at his desk (out_022.00) · 27.17-34.27 Ishaan on phone (out_028.00, out_030.50)
- 34.27-39.30 third friend on phone (out_035.00, out_037.50) · 39.30-44.40 student on phone (out_040.80)
- 44.40-48.03 student at laptop: "What the f*ck, why are my notes scattered in so many groups?" (out_045.00)
- 48.03-51.83 head in hand, defeated (out_050.00)

## Cues
### Countdown
- "in"@14.54, "8"@14.80, "hours"@15.07.
- **Slam at 14.80**: big "08:00:00" (JetBrains Mono 800, ~180-200 px, red `--alert` with glow,
  tiny "EXAM IN" label above in Inter 700 letterspaced). Centered, y ≈ 420-640 (above his head,
  check out_014.60). Lands hard: scale ~1.3→1 with blur→0 in ~0.12 s, small overshoot.
- Holds, then **15.70-16.10**: shrinks and flies into a compact HUD pill at top-left
  (x = 64, y ≈ 236): red pulsing dot + "EXAM IN 07:59:59" (`.hud-pill`, mono digits).
- Ticks DOWN once per second from 08:00:00 at 15.07 (07:59:59 at 16.07, ...).
- **Breakdown 44.65 → 51.4**: the clock starts racing (time-lapse) — seconds become a blur, minutes
  then hours fall, ending around 05:4x:xx; the pill turns full red and pulses faster; digits
  jitter slightly.
- **51.45-51.80**: glitch-out (RGB-offset copies jitter, collapse to a line, gone). Nothing visible
  after 51.80.

### Phone call (Ishaan)
- Ring tones play at **16.10-17.13** and **18.67-20.17**. **15.90**: an in-call card slides down
  from the top (centered, y ≈ 330, width ~760): avatar circle with "I" initial (soft gradient),
  name "Ishaan", status "Calling…" (animated dots), a small green phone glyph. The avatar sends
  out a pulse ring on each ring tone.
- **Connected at 21.28** ("What's up bro?"): status becomes a timer "00:00" counting up in real
  seconds, green dot. By ~22.0 the card collapses into a compact pill at the top-right
  (right edge at x = 1016, y ≈ 236): phone glyph + "Ishaan 00:0x". It must not collide with the
  exam pill on the left.
- **Call ends at 44.40** (cut to the laptop shot): pill flashes red "Call ended" and slides away by 44.90.

Avoid covering faces in 20-44 s (heads are around y 450-1000 in those shots).
