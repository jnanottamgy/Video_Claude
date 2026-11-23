# Mountain edit: what the inspiration reels do

The client's brief: a horizontal mountain reel, "full aura farm", slow motion where it earns it, shot on vertical
footage. Their own audio is coming. Seven inspiration reels came from a Drive folder (the link stays out of git).
They are downloaded to `renders/src/inspo/r1..r7.mp4` (gitignored; `names.txt` maps them to the original titles).

How they were read:
- `tools/analyze_inspo.py` measures each reel:
  - cuts;
  - camera motion from dense optical flow (pan, zoom and roll per frame, measured inside the picture area so
    letterbox bars don't hide it);
  - the grade, flashes and letterboxing;
  - the beat grid and sound hits by band.
- `tools/spectro_inspo.py` draws each soundtrack's spectrogram with the cuts marked.
- Then every reel was looked at 4-5 frames a second, with close-ups of each technique.

## The seven reels

| | What it is | Picture | Length | Avg shot | Sound |
|---|---|---|---|---|---|
| r1 | Lyric mood piece: a lone hiker, cloud inversions, glacier | 16:9 letterboxed in 9:16 | 14.8 s | 2.5 s | Sad melodic song with 808s (~131 BPM). After the drop, a cut on every bar (1.83 s) |
| r2 | Monologue edit, "I am not like everybody else" | 16:9 | 14.2 s | ~0.5 s, plus flash frames (60 cuts) | Spoken voice over a sub drone. Flash frames on the sub hits |
| r3 | "Creed x Snow": a snowboard VFX showcase | 16:9 | 17.9 s | 0.6 s | Rock song. 66% of cuts within 70 ms of a drum hit |
| r4 | CapCut screen recording of a Himalayan sunrise summit edit | 16:9 project | 14.7 s | 0.57 s | Music hook, then the Kobe Bryant quote over a drone, then the beat drops at 6.67 s |
| r5 | CapCut template, "giving up is not in the blood, sir" | 16:9 project | 15.6 s | 0.87 s | Spoken line, drop at 3.9 s, then cuts every 2 beats (129 BPM) |
| r6 | Nepal trip: the summit as the hook, then the flights there | 16:9, 24 fps | 14.3 s | 0.46 s | Hook, 0.18 s of silence, the same Kobe quote, drop at 6.83 s |
| r7 | "Die for it": Triund and Laka Glacier, Himachal | ~4:3 letterboxed in 9:16 | 21.5 s | 0.40 s | Song with a heavy kick. The bass is cut, with stutter cuts, before each drop |

What they share:
- All seven are horizontal pictures, even the ones posted as vertical reels. A horizontal deliverable is right.
- Six of seven are built around one line (a quote or a lyric) shown word by word.
- Five of seven use red as the type colour.

## The blueprint they share (about 15 s)

1. **Hook, 0-2.5 s.** One of two shapes:
   - a single striking hero image, held (r1, r5);
   - a burst of 4-8 cuts at 0.1-0.5 s on the music's intro hits (r2, r4, r6, r7).
2. **The line, ~2.5-6.8 s.** The quote or lyric plays:
   - the music falls back to a drone or a sparse bed;
   - shots get long (1.5-4 s) and slow: a slow push-in on a face, a locked-off wide;
   - the words appear one at a time on the voice, mostly placed *behind* the person.
3. **The gap.** Either 0.1-0.35 s of near-silence (r1 7.05-7.40, r4 2.10-2.22, r6 2.30-2.48), or a build with
   the bass filtered out under 0.1 s stutter cuts (r7 3.85-4.50).
4. **The drop, on the punchline word.** A hard cut, a white flash or white subject cutout, and the bass slams back
   on the beat: r1 7.40, r4 6.67, r5 3.90, r6 6.83, r7 4.50.
5. **The montage, ~7-13 s.**
   - One shot per 1-2 beats (0.4-0.9 s), each with one move: a zoom punch, a speed ramp, a split screen, a
     frame-in-frame.
   - Longer reels add a second gap, stutter, flash and re-drop (r7 14.4-15.9).
6. **The out, the last 1.5-2.5 s.** One held hero shot in slow motion, then a fade to black or the frame
   shrinking into a small card on black (r3, r6). Examples of the held shot:
   - walking toward and past the lens (r7);
   - a summit silhouette (r4);
   - an alpenglow peak racking into focus (r5).

## Text

- **Word by word, on the syllable.** Words stack into a 3-5 line block, then clear on the next phrase.
- **Behind the subject (6 of 7 reels): the most repeated trick.** The person's matte sits over the words:
  - r1: "COULDN'T";
  - r4: "Dream" behind the group;
  - r5: "Giving up is not in the blood" around the head, and "HONORABLE" behind the hiker;
  - r6: "WHAT YOU" behind the hood;
  - r7: "TRIUND", "DIE FOR IT", "ALIVE FOR IT".
- **Two faces, 3-6x apart in size.** The key word is huge and heavy; the joining words are small, in a contrasting
  style:
  - r2, r4: a serif italic;
  - r6: a handwritten marker;
  - r1, r5: a small sans.
- **Colour.** Red and white in r2, r4, r5, r6, r7. In r1, pink and white on a teal grade, the complementary pair.
- **Edges.**
  - Words bleed off the frame edge (r4 "What", "consciousness").
  - A title is split into fill and outline across the subject (r7 "TRIUND": the letters crossing the hiker are
    outline only).
- **Key word card.** One word fills the frame and the shot is re-tinted under it (r4 "Dream" on a brown wash).
- **Location title.** "TRIUND" huge, with "LAKA" and "GLACIER" small in the corners (r7).
- **Glitch word.** "DIFFERENT", distressed and displaced (r2).
- **Entrances.** Motion blur on type entrances (r5 "HONORABLE").
- **Free fonts close to these:**
  - Anton or Bebas Neue (r7's condensed red);
  - Poppins Black or Montserrat Black (r4, r5);
  - Archivo Black, or a wide black sans (r6);
  - Playfair Display Italic (r2, r4);
  - Permanent Marker (r6).

## Transitions

- **Hard cut** on a beat or hit. It's the default.
- **Flash frame.** 1-2 white frames on a sub hit, then the shot fades back up from white over about 6 frames
  (r2 1.03-1.80).
- **White subject cutout.** For 1-3 frames the person's silhouette is filled solid white:
  - r4 0.8, 8.4, 10.2, 11.6;
  - r7 8.75, 10.75;
  - r5 7.4, half-transparent.
- **Invert frame** on a hit (r2 0.0, 7.5; r7 12.75).
- **Frame-in-frame.** The next shot appears as a rectangle inside the current one, then grows to full frame
  (r3 2.5-3.7; r5 5.8-6.6; r7 6.25, 15.5).
- **Slices.** The next shot is revealed through slanted parallelogram strips (r3 5.25-6.0).
- **Split screen.** Top and bottom (r7 7.5-9.0, r3 12.75), or left and right (r5 8.4-12.0, r7 13.5). In r5 a third
  shot is inset on top.
- **Light.** A light streak or X-wipe (r5 11.25), a light leak (r7 14.75).
- **Zooms.**
  - A zoom-out whip at the end of a shot (r7 12.3: 70‰ a frame for 2 frames).
  - A zoom punch at a speed-ramp point (r3 4.85: 92‰ in one frame).
- **Roll.** Roll moves on fast cuts (r3, up to 258‰ of roll in a shot).
- **Walk past the lens.** The person walks into the camera until the body fills the frame (r7, the last shot).
- **Shrink to a card.** The last frame scales down to a small rectangle on black (r3 17.1, r6 13.75).
- **Smear opening.** A B&W silhouette under a streaking sky: a time-lapse with heavy frame blending (r3 0-1.6).

## VFX and looks

- **Person mattes do most of the work:** text behind, white cutouts, double exposure, pop-outs.
- **Double exposure.**
  - A rider's head in silhouette on white, filled with a chairlift shot (r3 13.25-14.5).
  - The snowboard then breaks *out* of the silhouette.
- **CRT scanlines.** A B&W close-up of an eye with scanlines, and a window of action inside it (r3 10.25-12).
- **Strobe and shake.** Bright and dark frames alternate, with an artificial shake in a 3-frame cycle, at the
  climax (r2 12.1-14.1).
- **Smaller touches:**
  - falling-snow particles (r6);
  - a fisheye GoPro look (r3);
  - a rack focus from blur to sharp on the last peak (r5 14.0).

## Motion tracking and HUD

- **Tracked points.** Points on the person with coordinate readouts and thin spline lines joining them, following
  the person (r4 0.0-1.0).
- **Detection boxes.** Thin boxes around heads, dotted guide lines and tiny labels (r4 4.4-6.0).
- **Scanner HUD.** A band reading "DETECTING...", x/y coordinates, corner brackets and crosshair lines over a drone
  shot of climbers (r5 12.4-13.4).

## Camera and speed (measured)

- **Stillness is the aura.**
  - r1: 5 of 6 shots locked off (0.0 px a frame).
  - r7: almost every shot locked off.
  - The person moves slowly in a frame that doesn't.
- **Slow drone orbit.** It pulls out, then eases into a push-in (r1 0-3.8 s).
- **Slow push-in on the face** during the quote (r6 2.83-5.21 s: 12% over 2.4 s).
- **Speed ramp.** Fast into the action, slow through its peak, with a zoom punch at the switch (r3 4.4-6.2: motion
  rises from 4 to 13 px a frame at take-off, then holds 2 px a frame through the air).
- **Zoom bounce on the beat.** A keyframed push for 12 frames, then a pull (r6 6.85-8.46).
- **Slow motion for the ending.** Walking toward and past the lens (r7 18.85-21.2).
- **Artificial shake** at the climax (r2).

## Sound

- **Gap, then drop** (above). In r7, the bass is filtered out for 0.65 s under 0.1 s stutter cuts, then slams
  back on the title (3.85-4.55).
- **Under the spoken line,** the music drops to a drone. The beat returns on the punchline word.
- **Cuts land on drum hits** more than on a strict beat grid.
  - r3: 66% of cuts within 70 ms of a hit.
  - r1: after the drop, a cut on every bar.
- **Added effects are sparse.** The music's own hits carry the edit. What's added:
  - an impact or boom on drops and titles;
  - a whoosh under fast moves;
  - the filter and tape effects;
  - flash frames sit on sub hits (r2).

## Colour

| Reel | Grade |
|---|---|
| r1 | Teal monochrome, crushed blacks (mean luma 0.08-0.25), pink type as the complement |
| r2 | High-contrast B&W, a few colour shots |
| r3 | Cool teal skies, dense contrast; B&W eye inserts |
| r4 | Sunrise: an orange horizon band against cold blue-grey, silhouettes |
| r5 | Bright natural snow, deep blue sky, an alpenglow close |
| r6 | Teal-orange film look at 24 fps; warm amber cabin interiors |
| r7 | Faded warm beige haze (lifted blacks, low saturation), alternating with teal-green forest |

## The shots that make it (look for these in the footage)

- **Scale.** An extreme wide with a tiny figure (r1, r7, r5's drone).
- **Silhouettes.** A silhouette on a ridge against the sky or the sunrise (r1, r4, r7).
- **The summit.** Arms out wide on top (r4).
- **Hero angles.** A low-angle hero against the sky (r3, r6, r7).
- **Looking out.** Over the shoulder, looking out over the valley (r1, r7).
- **Close-ups:**
  - goggles with reflections (r5, r6);
  - an eye (r3);
  - boots in snow (r5);
  - hands on straps and poles (r7).
- **POV.** A selfie with the range behind (r5, r6).
- **Foreground framing.** Shooting through something: trees, a plane window (r7, r6).
- **The group** walking or standing together (r4, r6).
- **Walk past the lens** (r7).
- **Story.** r6 opens on the summit, the payoff, as the hook, then goes back to the journey: start at the end.

## For our edit

### Vertical footage to a horizontal reel

The inspiration's own tricks are what make vertical clips work in a 16:9 frame:
- **Crop to 16:9.** This uses 32% of a vertical clip's height.
  - From 4K vertical (2160x3840), the crop is 2160x1215: a clean 1080p.
  - From 1080x1920, it's 1080x608: a 1.8x upscale, soft. Use it sparingly.
- **Reframe per shot.** The crop window follows the person or the horizon, eased (tracked).
- **2.39:1 inside 16:9** for landscapes. This needs only 1080x452 from a 1080-wide clip; it looks cinematic and
  hides the crop.
- **Show the vertical as vertical:**
  - two or three verticals side by side (split screen);
  - a vertical card in a frame-in-frame over a darkened, blurred copy of itself.
- **AI outpainting** to widen a few hero shots is possible, at a cost.

### Library effects for each move (library/sfx)

| Move | Effects |
|---|---|
| Drop, title slam | bass-woosh-1, cinematic-electric-hit, sword-impact |
| Summit reveal | wind-impact |
| The gap | beat-slowing (tape stop) into silence |
| Stutter build | build-up-1, build-up-3, riser |
| Zoom, whip, slices | woosh-1..5, fast-swoosh, cinematic-woosh |
| Invert, glitch | glitchy-woosh, alien-digital-glitch |
| White flash, cutout | old-flash, camera-click |
| Tracking HUD | digital-text, counter, radio-beep, night-vision |
| Title, alpenglow | shine |
| Slow-motion ending | slow-motion |

There's no wind or mountain-air bed in the library yet. One would help under the quiet sections.

### Still needed
- The audio (coming).
- The footage, with its resolution and frame rate. 4K helps the crops; 60 or 120 fps gives real slow motion.
- The line, if the audio has words. Place names for a title card (like r7's "TRIUND").
