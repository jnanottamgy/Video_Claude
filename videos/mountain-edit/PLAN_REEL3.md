# Reel 3: "TORE UP"

A 37.8 s reel cut to the "Tore Up" edit audio (Don Toliver, TikTok version). It uses the same trip footage as the
other reels and is delivered the same ways: a horizontal 16:9 master, the 9:16 Instagram version (the 16:9 picture
centred on black) and a cover.

The brief:
- Cars that look fast: full speed, then a sudden drop into slow motion, with graphics on the car.
- Transitions whose motion means something.
- Motion graphics and motion tracking.
- Photos made to move like video.
- Flashes, full sound design, an aura.

## The audio (`renders/audio/reel3.wav`, 38.27 s)

142.55 BPM: beats are 0.4209 s and phrases are 8 beats (3.367 s). The timings below are measured; the lyrics are
not reliably transcribable, so nothing is synced to words.

| Time | What happens |
|---|---|
| 0.106 / 3.473 / 6.841 / 10.208 | Intro phrases (sustained bass, no drums), each preceded by a short gap. |
| 12.75–13.1 | The breath. |
| 13.19–13.48 | An 808 roll in. |
| **13.584** | **DROP.** |
| 14.408 16.093 17.768 19.467 21.139 22.821 24.464 26.184 | A snare every 4 beats. |
| 26.2–27.35 | An 808 glide-up, peaking at 27.035. |
| 27.5–28.25 | The dip. |
| **28.299** | **Second section.** |
| 32.93–33.87 | An 808 roll in eighths. |
| 35.035 | The last phrase. |
| 37.54 / 37.66 | The last 808s. |

Cut, flash and shake times are snapped to the frame that contains the hit (`edl_v3.A`). The sound design uses the
exact times (`edl_v3.AUDIO`).

## Storyboard (`tools/edl_v3.py`)

| Out | Shot | What it does |
|---|---|---|
| 0.0 | T01 9685: jeep POV on the red trail | Fade in on the first bass note, light leak. |
| 1.77 | T02 2902: the summit edge at dawn | **Sky to sky**: a luma dissolve. |
| 3.47 | T03 0441: POV walk on the rock | **The first paper tear** opens the phrase. The walk pushes forward into… |
| 5.13 | T04 0434: him walking to the edge | …a zoom-through, so the forward motion carries over. |
| 6.83 | T05 0418: him, close | Light match. A **"MAIN CHARACTER"** lock, tracked on his matte. |
| 8.50 | T06 0413: the same summit as a **photo that moves** (2.5D) | A camera flash: the moment frozen into a memory. |
| 10.20 | T07 0439: crane up from the rock to the sun | Paper tear. |
| 11.87 | T08 9685: back on the road | The jeep winds up. The breath (colour drains, the bars close in). Then it floors it: 0.1x → 7x, warp streaks, a zoom down the trail. |
| **13.57** | T09 0397: **car 14 rushing at the lens** | Out of the zoom-through. Slow motion from 14.0 with the HUD lock and callout, then 3.2x past, left. |
| 16.07 | T10 0396: Polo pass | Push left. 1.8x → **0.2x** on the snare → 2.8x. |
| 17.77 | T11 0465: #53 Gypsy | Push left. 2.4x → **freeze** on the 808 → 2.6x into its dust. |
| 19.47 | T12 0395: Polo drift | Push left. 2.4x → **0.22x** → 2.6x. |
| 21.13 | T13: **triptych** | CAR 65 / TARGET 02 / CAR 14 land on three 808 notes. |
| 22.80 | T14 0467: headlights rushing in | Flash. Slow in the glare, then the real camera whip out. |
| 24.43 | T15 0461: #65 teal Polo | Light match. It drifts the other way: fast → **0.22x** → fast. |
| **26.17** | T16: **REWIND** | The 808 glides up and the tape rewinds through the whole drop: VHS tracking, REW, a timecode running back. |
| **27.03** | T17: **freeze** | Car 14 stopped dead, the world drained, outline. **TORE** (white) and **UP.** (red) torn in two, the pieces drifting apart. |
| 28.27 | T18 0434: the summit and the sun | **The freeze-frame tears open** onto it. |
| 29.97 / 30.80 | T19 0402 / T19b 4838: **photos that move** | Camera flashes. |
| 31.63 | T20 7910: push-ups in the clouds | Paper tear. |
| 32.90 | T21: **stutter** | One hero frame per 808 in the roll, each with a flash, every other one inverted. |
| 34.43 | T22 0430: the silhouette against the sun | **TORE UP.** behind him from 35.03 (his matte), torn, drifting apart. Glitch, red flash, black at 37.7. |

**Graphics:**
- The telemetry strip runs through the drop: revs, km/h, gear and playback rate (2.40X / 0.20X / FREEZE)
  follow each shot's real time map.
- Chevrons race with the pushes.
- The callouts' numbers are styling, not measurements.

## New in this reel (`tools/fx2.py`)

- `tear`: the frame cracks from the top down and the two halves peel apart along a jagged multi-scale line, with
  white paper-fibre edges and soft shadows, revealing the next shot.
- `torn_sprite`: type torn in two along a jagged diagonal, with fibre edges; `render.draw_words` takes
  `torn=sep` (a number, or a function of time).
- `vhs`: rows wobble, a tracking band climbs and tears the picture sideways, chroma bleeds, scanlines and snow.
- `flash_pop`, and the `flash` transition: a camera flash across the cut.
- `edl_v3.draw_rewind`: plays each car shot backwards in turn (graphics included) under `vhs`.
- `edl_v3.draw_stutter`: one frame per note.

## Sound (`tools/mix_v3.py`)

- **Engines** follow each shot's time map, the jeep's included as it winds up into the drop.
- **Paper rips** are synthesised: fibre crackle over a torn-noise body.
- **The tape rewind** is the song's own last 2.3 s, reversed, sped up and wobbling.
- **Library effects** on every move, flash, lock and slam.
- **Levels:** the effects sit 7 LU under the song. The master is -14 LUFS with -1 dBTP peaks.

## Run it

```
EDL=edl_v3 python3 tools/prep.py T09 T17 T10 T12 T15 T05 T22     # mattes
EDL=edl_v3 python3 tools/render.py --chunk 40                     # renders/picture_v3/picture.mp4
python3 tools/mix_v3.py                                           # renders/audio/reel3_mix.wav
tools/deliver_v3.sh                                               # renders/deliver/TOREUP_*
```
