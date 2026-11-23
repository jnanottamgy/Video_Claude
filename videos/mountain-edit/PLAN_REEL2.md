# Reel 2: "REDLINE"

A 10.7 s reel cut to a new edit audio. It uses the same trip footage as the DNA reel (summit, rally stage, monsoon
ledge) and is delivered the same ways: a horizontal 16:9 master, a 9:16 Instagram version (the 16:9 picture
centred on black) and a cover.

The brief, in short:
- Cars that look fast: full speed, then a sudden drop into slow motion, with graphics locking onto the car.
- Transitions whose motion means something.
- Motion graphics.
- Full sound design.

## The audio (`renders/audio/reel2.wav`, 10.71 s)

85.9 BPM, with 0.69875 s beats. Beat 1 of the drop bar falls at 4.27 s.

| Time | What happens |
|---|---|
| 0.00–4.0 | Melodic intro with no drums. The intro beats fall at 0.08, 0.78, 1.48, 2.18, 2.88 and 3.58. |
| 3.58–3.9 | A pitch rise. |
| 4.0–4.27 | A near-silent gap: the breath before the drop. |
| **4.275** | **The drop (808).** |
| 4.974 | Snare. |
| 5.34–5.72 | Small 808 notes. |
| **6.248** | **808 hit**, with a snare at 6.35. |
| 7.07 | 808 retrigger. |
| 7.768 | Snare. The sub then drops out: the break. |
| 8.0–8.9 | A whistle line, pitch-bending around 800 Hz. |
| **9.051** | **The 808 returns**: the climax. |
| 9.16 | Snare. |
| 9.5 and 9.9 | 808 glides. |
| 10.563 | The last snare. |
| 10.71 | End. |

Cut and flash times are snapped to the start of the frame that contains the hit (`edl_v2.snap`). The sound design
uses the exact times (`edl_v2.AUDIO`).

## Screen direction (measured with `tools/motion.py`)

| Car moves right to left | Car moves left to right | Head-on |
|---|---|---|
| 0396 (white/red Polo), 0395 (white/red Polo), 0397 (#14 Polo), 0465 (#53 orange Gypsy) | 0461 (#65 teal Polo) | 0467 (green Gypsy with headlights), and 0397 on its approach |

The drop is built as one continuous leftward rush:
- The silhouette in 0430 is mirrored, so his strike travels left like every car after it.
- Every push transition carries the leftward motion into the next shot.
- The finale reverses it: the teal Polo drifts the other way and freezes.

## Storyboard (`tools/edl_v2.py`)

| Out | Shot | Speed | Transition in / graphics |
|---|---|---|---|
| 0.00 | V01 0434: shades close-up | 0.5x | Fade in. A lens glint. The push accelerates **into his lens**. |
| 1.47 | V02 0438: POV over the valley | 0.5x | **Out of the lens**: keeps zooming forward from 0.5x scale, with radial blur, green lens tint and the lens rim. |
| 2.17 | V03 0418: the pull-back on him | 1.5x | Vertical push (the tilt carries on). |
| 2.87 | V04 0430 (mirrored): silhouette, sun | 0.45x → 0.12x → 3.6x | Zoom-out match. Wind-up; the breath (colour drains, bars close in); the strike snaps out on the drop. |
| **4.27** | V05 0396: Polo pass | 2.6x → **0.22x** → 2.8x | **A hole punched through from his fist** (shockwave reveal). Target lock and callout. |
| 4.97 | V06 0465: #53 Gypsy door | 2.4x → **freeze** → 2.6x | Push left, with chevrons. Callout on the "53" sticker. |
| 5.67 | V07 0395: Polo drift | 2.4x → **0.25x** → 2.6x | Push left. Callout on the drift. |
| **6.23** | V08 0397: car 14 head-on | **0.2x on the 808**, then 3.2x past | Hard cut, flash, shockwave. Full HUD lock. |
| 7.07 | V09 0465: Gypsy into its own dust | 2.8x → 1.1x | Whip left. |
| 7.77 | V10 7910: clouds, then him on the ledge | 0.5x | **The dust becomes cloud** (luma dissolve). Letterbox back. |
| 8.47 | V11 0434: the summit, the sun | 0.7x → 2.4x | Vertical push. The 808 creeps back in, pulling toward the sun. |
| **9.03** | V12 0467: headlights rushing in | 2.4x | **The sun becomes headlights** (light match). Warp streaks, headlight flares. |
| 9.50 | V13 0396: a car side fills the frame | 0.8x | Zoom-through. |
| 9.83 | V14 0461: the teal Polo, #65 | 2.4x → 0.18x → **freeze** | Car-body wipe. The world drains to monochrome; outline; REDLINE behind it; callout. |
| 10.53 | — | — | Red flash, glitch. Black on the last frame. |

The telemetry strip runs along the bottom of the rally sections. Its revs, speed, gear and playback rate follow the
shot's real time map: 2.60X when fast, 0.22X in red when slow, FREEZE on the freezes.

The callout numbers (speed, drift, G) are styling, not measurements.

## How it's built

- **Velocity edits.** `fx2.speedmap` turns a speed profile into a time map. The profile is linear in speed between
  keys, so two keys a frame apart give a sudden slow. An anchor pins the hero moment to a beat.
- **Motion blur at full speed.** `render.src_frame` averages every source frame the shutter spans. A
  phase-correlation estimate of the dominant motion then smears those copies into a continuous streak.
- **Smooth slow motion.** `render.flow_mix` builds in-between frames from DIS optical flow in both directions.
  The orange Gypsy passes too close and too fast for clean in-betweens (about 325 px per source frame), so it gets
  a freeze frame instead.
- **Transitions.** A shot's `tx` mixes the outgoing and incoming shots across the cut (`render.active_tx` /
  `render.mix`), using one of these: push, shock reveal, luma dissolve, light match or edge wipe. The zoom-throughs
  are view moves: an accelerating push-in, then an ease-out zoom from below 1x on the next shot, both radially
  blurred.
- **Mattes.** `EDL=edl_v2 python3 tools/prep.py V05 V07 V08 V14` builds mattes, only over each shot's `matte_t`
  stretch. The HUD locks use the largest blob, median-filtered over 7 frames (`render.track_box`).

## Sound (`tools/mix_v2.py`)

- **The engines follow the picture.** Each rally shot's own audio is re-sampled through its time map (varispeed).
  The engine screams up at 2.6x, groans down in slow motion and winds to silence on a freeze.
- **Effects from the library.** Whooshes follow every transition. On top of those:
  - bass sweeps on the drop and the climax;
  - a lightning crack on the 808 hit;
  - slow-motion swells and tape-stops wherever time drops;
  - Nextel chirps on the target locks, with data bursts and counter ticks under the callouts;
  - a camera shutter and flashbulb on the final freeze.
- **Levels.** The effects bus sits 8 LU under the song. The master is -14 LUFS with -1 dBTP peaks.

## Run it

```
EDL=edl_v2 python3 tools/prep.py V05 V07 V08 V14        # car mattes
EDL=edl_v2 python3 tools/render.py --chunk 40             # renders/picture_v2/picture.mp4
python3 tools/mix_v2.py                                   # renders/audio/reel2_mix.wav
tools/deliver_v2.sh                                       # renders/deliver/REDLINE_*
```
