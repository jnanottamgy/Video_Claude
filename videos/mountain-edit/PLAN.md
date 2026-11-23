# Mountain edit: "DNA" reel

The client's trip reel, cut to an edit audio of Kendrick Lamar's "DNA." (50.3 s). The brief, in their words:
very cinematic, "aura farm", motion tracking, flashes, SFX, VFX, graphics; photos made to look like video; for
Instagram; horizontal (their footage is mostly vertical). Inspiration analysed in INSPO.md.

Inputs (all gitignored; the Drive link stays out of git):
- `renders/src/footage/`: 23 iPhone clips and 3 photos (935 MB).
- `renders/src/audio/dna_edit.mp3`: the edit audio, 50.83 s, 128 kb/s MP3, decoded to `renders/audio/dna.wav`.

## The audio (measured: tools/lyrics_asr.py, renders/analysis/audio/*)

- **Grid.** 130 BPM after the intro (0.4615 s a beat, 1.846 s a bar). Both drops sit on it: 15.24 and 30.01, 8 bars
  apart.
- **Words.** Timed by Parakeet (offline). Whisper gives a second reading. Times are approximate (±0.1 s).

| Time (s) | Section | What happens |
|---|---|---|
| 0-0.95 | Cold open | Near silence, "I got" whispered at 0.48 |
| 0.95-15.25 | Intro | Quiet: about 20 dB under the drop sections. See the intro detail below |
| 15.25-28.45 | Drop 1 | The beat switch, full 808, a crash at 16.2. See the drop 1 detail below |
| 28.45-30.0 | Break | The 808 is cut; vocals carry on ("stackin' up the footage") |
| 30.0-45.5 | Drop 2 | Lyric images ripe for literal matching. See the drop 2 detail below |
| 45.5 | The slide | A big transient and an 808 glide down |
| 47.0-50.33 | Outro | Hats drop out. "I don't compromise" 48.8-49.0, "I just finna die" 49.7-50.2, then a hard stop at 50.33 |

**Intro, 0.95-15.25 s:**
- 808 booms at 1.04, 4.56, 8.32 and 10.26.
- "Loyalty" 0.88, "royalty" 1.84, "DNA" 3.28.
- The Fox News sample, 3.9-7.5.
- "I live a better... life", 9.68-10.9.
- A gap at 11.58-11.95.
- "This is my heritage" 11.9-12.4, "all I'm inheritin'" 12.9-13.3, "money and power" 13.8-14.2, "the makin' of
  marriages" 14.6-15.2.
- A sub blip at 14.28.

**Drop 1, 15.25-28.45 s:**
- "Tell me somethin'" ~16.9.
- "Can't tell me nothin'" 17.8-18.3.
- "I'd rather die" 18.8-19.3, "than listen to you" 19.5-20.2.
- "My DNA not for imitation" 20.6-21.7, "your DNA an abomination" 22.6-23.4.
- "This how it is when you in the Matrix" 24.3-25.6.
- "Reapin' what you sowin'" 26.6-27.2.

**Drop 2, 30.0-45.5 s:**
- "Walkin' in the building" 31.3-31.8.
- "Diamond in the ceiling" 32.2-32.7, "marble on the floor" 33.0-33.6.
- "Peekin' out the window" 34.9-35.5.
- "Paparazzi" 39.8, "through the cameras" 41.0.

## The footage

| Clip | Source | Content |
|---|---|---|
| 0418 | V 4K60 | Hero: black tee, shades, arms crossed on the summit; the camera pulls back to the rock edge |
| 0434 | H 4K60 | Shades close-up with a reflection, back of the head, then walking to the summit edge, sun flare |
| 0430 | H 60 | Silhouette on the ridge with the sun, moving / posing |
| 0439 | V 4K60 | Top-down on a friend lying on the rock, crane up to the valley |
| 0438 | H 4K60 | POV legs on the rock, pan across the valley and the sun |
| 0405, 0441 | V 60 | POV walking on rock to the edge, sunrise haze over the forest |
| 2902 | V 4K60 HDR | A person on the rock edge over the valley (iPhone 16, HLG: needs tonemapping) |
| 7910 | V 4K30 | Shirtless push-ups on a cliff ledge in the clouds (monsoon green) |
| 9948 | V 4K30 | Blue raincoat, walking up a green slope in mist |
| 9685 | V 60 | Jeep ride on a red dirt trail through green hills |
| 0462 | V 60 | Two friends walking a forest road |
| 0472 | V 60 | Looking up at the canopy while walking (42 s) |
| 0446 | V 60 | Friends at a forest pond, whip pan |
| 0437 | H 4K60 | Two-person selfie, goofy |
| 0389 | V 60 | Washing and pushing a white hatchback |
| 0393 | H 4K30 | Rally service park, cars and dust |
| 0395, 0396, 0461 | V 60 | Rally car through the coffee estate in dust; 0396 has a whip with the car close |
| 0397 | H 4K30 | Rally car down the estate road, dust over spectators |
| 0465 | V 4K30 | Orange car through the estate, dust |
| 0467 | H 30 | Estate road, car passes, blue rally car |
| 0402 (photo) | | Mirror selfie of the two, low light |
| 0413 (photo) | | The hero on the summit (a still of 0418's setting) |
| 4838 (photo) | | A sideways selfie lying back on a motorbike (rotate 90°) |

Most vertical clips are 1080x1920: a straight 16:9 crop is 1080x608, a 1.8x upscale. So:
- the 4K clips and the horizontal clips carry full-frame moments;
- the 1080p verticals go into split screens, frame-in-frame cards, fast action (blur hides it), or 2.39:1.

## Exact hits (tools: renders/analysis/audio/*; frame = floor(t * 30))

- **Intro booms.** 0.951, 4.412, 8.200, 10.149. The gap ends at 11.97; the sub blip is at 14.26.
- **Drop 1.** 15.187 (frame 455). The crash is at 16.20.
- **The break.** The bass falls at 28.482 (frame 854).
- **Drop 2.** 29.879 (frame 896).
- **The slide.** 45.49. The hats go out at 46.83. The last sound is at 50.378.
- **The grid after the intro:** T(k) = 15.187 + 0.45913 k (130.7 BPM). Drop 2 is k = 32, the bass cut k = 29, the
  slide k = 66.

## Concept: "DNA scanner"

The motion tracking is a story device: a scanner HUD locks onto the people and the cars, sequences them, and
"matches" them to the song's words. It reads real tracker data: boxes, points, coordinates and a frame counter.
- **Type.** Anton for the big words, in white and red. JetBrains Mono for the HUD. Instrument Serif Italic for small
  contrast words.
- **Bars.** The intro and outro are letterboxed to 2.39:1. The bars slam open on drop 1 and close again at 47.0.

## Storyboard

| Time (s) | Section | Shots |
|---|---|---|
| 0-0.95 | Cold open | Black, film grain, a thin DNA helix drawing itself, HUD typing "SEQUENCING SUBJECT 01" |
| 0.95-15.19 | Intro | 2.39:1, slow motion, cool and desaturated. See the intro detail below |
| 15.19-28.48 | Drop 1 | The rally: full 16:9, warm dust, heavy effects. See the drop 1 detail below |
| 28.48-29.88 | Break | 0430 silhouette punch in slow motion, glowing outline, "SEQUENCE 99%". A 2-frame stutter of the hero shots, then black |
| 29.88-45.49 | Drop 2 | The summit and the monsoon, lyrics matched literally. See the drop 2 detail below |
| 45.49-46.83 | The slide | The hero photo 0413 in parallax with a dolly-zoom on the 808 slide: "DNA MATCH 100%" |
| 46.83-50.38 | Outro | Bars close. See the outro detail below |

**Intro, 0.95-15.19 s:**

| Time (s) | Shot | Detail |
|---|---|---|
| 0.95 | 0418 hero | Close up, slow motion; "LOYALTY" behind him |
| 1.84 | 0434 shades | Close-up; "ROYALTY" (red) behind his head |
| 2.65 | 0434 orbit | The orbit round his head; "DNA." behind, scanner HUD locks on |
| 4.41-8.20 | Broadcast look | Black and white, scanlines, "● LIVE" and a timecode, under the Fox News sample: 0430 silhouette strike, then 7910 push-ups in the clouds, then the 0439 crane-up |
| 8.20 | 0462 | Friends walking; colour returns |
| 9.68 | 0437 | The selfie |
| 10.15 | 0402 | The mirror-selfie photo in parallax, with a flash |
| 11.58-11.97 | Black | The gap |
| 11.97 | 0405 sunrise valley | "HERITAGE" in outline |
| 12.88 | 0438 | POV pan across the valley |
| 13.76-15.19 | Stutter build | Rally teasers (2-4 frames each) between "MONEY" / "POWER" cards and flashes, accelerating; the blip at 14.26 gets a white flash; black for the last 3 frames |

**Drop 1, 15.19-28.48 s:**

| Time (s) | Shot | Detail |
|---|---|---|
| 15.19 | 0397 close pass | "DNA." red behind the car, flash, zoom punch, shake |
| 16.20 | 0395 | Drift |
| 16.96 | 0465 | Orange Gypsy pass |
| 17.76 | 0396 dust, slow motion | "CAN'T TELL ME NOTHIN'", word by word |
| 18.80 | 0467 | Headlights head-on; "I'D RATHER DIE" |
| 19.52 | 0461 | Teal drift |
| 20.64 | Triptych | Three cars (0395 / 0461 / 0465); "NOT FOR IMITATION" |
| 22.56 | 0396 whip | Negative, RGB split; "ABOMINATION" |
| 23.44 | 0397 | Dust and spectators |
| 24.32 | 0465 dust | ATGC code rain, "MATRIX" glitch at 25.5 |
| 25.92 | Rapid cuts | 0393 / 0467 / 0395 |
| 27.52 | "Stackin' up the footage" | A 4x4 grid of the trip's clips, collapsing at 28.48 |

Target-lock HUD boxes track the cars throughout.

**Drop 2, 29.88-45.49 s:**

| Time (s) | Shot | Detail |
|---|---|---|
| 29.88 | 0434 | Walk to the edge into the sun, with a white-cutout flash |
| 31.28 | Split | 0462 / 9948 walking: "walkin'" |
| 32.16 | 0472 canopy | Diamond glints: "diamond in the ceiling" |
| 33.04 | 0441 POV | The rock floor: "marble on the floor" |
| 33.92 | 9685 jeep | Seen through a window card that opens to full at 34.88: "peekin' out the window" |
| 35.84 | 0446 | Friends at the pond: "pool" |
| 36.72 | 7910 | Push-ups in the clouds |
| 38.64 | 0418 | Pull-back |
| 39.84 | 0461 photographers | Flash strobes and shutter flicker: "paparazzi" |
| 40.48 | 0402 photo | A flash pop: "cameras" |
| 40.96 | 0437 | Selfie |
| 42.0-45.49 | Aura montage | Every 2 beats: 0439 wide, 0438, 0405, 9948, 0430, the 4838 bike photo |

**Outro, 46.83-50.38 s:**

| Time (s) | Shot | Detail |
|---|---|---|
| 46.83 | 0434 | Standing at the edge, tracked HUD |
| 48.8 | 0434 | "I DON'T COMPROMISE" behind him, word by word |
| 49.68 | Title card | Helix + "DNA." over his white silhouette; black at 50.37 |

## Picture (tools/edl.py, render.py)

**Framing:**
- Every shot is a 16:9 window (or a panel) in the clip's display pixels.
- 4K clips are decoded straight to output scale. 1080p verticals are upscaled with a gentle unsharp.

**The intro words.** Words behind subjects use rembg mattes cached per output frame (tools/prep.py):
- isnet for people and cars, refined with a guided filter;
- holes inside silhouettes (mirrored lenses) are flood-filled.

**Tracking:**
- The HUD target boxes follow the matte's bounding box: the head for people, the whole car for cars.
- Point constellations are fixed in the subject's box, so they move with it.
- The HUD hides while a whip blurs the frame.

**Photos (0402, 0413, 4838):**
- Each photo is split into the person (matte) and an inpainted background.
- The two layers move at different speeds (2.5D parallax).
- The 808 slide uses this as a dolly zoom: the background pushes 1.42x while he stays almost still.

**Transitions:**
- whips (directional blur + slide, the speed peaking at the cut);
- a zoom-through into the build;
- white flashes;
- 2-frame white cut-outs and inverts;
- a CRT broadcast section (B&W, scanlines, a rolling bar, tears, LIVE bug) under the news sample;
- panels: the triptych "NOT FOR IMITATION" and the 3x3 "footage" grid;
- a window card for "peekin' out the window";
- a two-frame stutter before drop 2.

**Speed:**
- 60 fps sources play at 0.5x for slow motion.
- Ramps (PCHIP time maps) on the drifts (C2, C6) and on drop 2's walk (E1).

**Finishing:**
- grades per section: intro cool/desaturated with a sky ND, rally contrasty dust, summit teal-orange, crew neutral;
- halation, aberration on the hits, vignette, grain;
- 2.39:1 bars in the intro, the break and the outro, which slam open on the drops.

**Render:** `python3 tools/render.py` (4 workers, about 10 min) -> renders/picture/picture.mp4. Review boards:
`python3 tools/board.py OUT.jpg t1 t2 ...`.

## Sound (tools/mix.py)

- The song plays untouched.
- **Cues.** About 95 cues from library/sfx, each set relative to the song's short-term level where it lands, by
  type:
  - impacts about 6 dB under it;
  - whooshes about 8 dB under;
  - HUD beeps about 13 dB under.
- **Engines.** The real engine pass-bys from five rally clips sit under drop 1, aligned to the passes on screen.
- **Filtering.** Everything but the two drop hits is high-passed at 140 Hz, so nothing fights the 808.
- **The effects bus** is trimmed to 11 LU under the song.
- **Master:** -14 LUFS, -1 dBTP (Instagram).

## Deliver (tools/deliver.sh)

- `DNA_reel_16x9.mp4`: 1920x1080, the master.
- `DNA_reel_IG_9x16.mp4`: 1080x1920 for Reels, the 16:9 picture centred on black.
- `DNA_cover.jpg`: the Reels cover.

## Review notes (v1)

Checked on contact sheets of the rendered picture (6 fps) and frame strips around the cuts.

**Fixed:**
- **Placement.** "ROYALTY" now sits behind his hair, clear of the mirrored lenses (which read as background in the
  matte). "DNA." in B3 sits right, revealing as his head turns. "HERITAGE" moved to a frame that shows the valley.
- **The MONEY / POWER cards.** They no longer take the global flash, which washed them grey.
- **A black frame at the head of each panel shot.** Panels now show from the frame their appear time falls in.
- **The renderer.** The first render ran out of memory (12 cached sources x 4 workers) and the pool hung. Now:
  - a worker drops its decoded sources when it moves to the next shot;
  - chunks are about 190 frames;
  - the pool fails loudly;
  - finished chunks are kept (`--fresh` redoes them).

**Added:**
- a 2.2% zoom pulse on every beat in both drops (not on matted shots, whose mattes are pulse-free);
- brighter, larger code rain;
- a lower sun-flare threshold.
