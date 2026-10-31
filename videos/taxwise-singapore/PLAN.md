# TaxWise Consultants: Singapore expansion reel

TaxWise Consultants (twchartered.com) is a chartered-accountancy and finance firm in Bangalore and Chennai, and
it is opening in Singapore. Managing Partner **HK Vinay** announces it on camera. The team had already cut a
56 s reel. The brief was to turn it into a studio-grade, cinematic, slightly Gen-Z film for Instagram (and
Shorts, LinkedIn, WhatsApp), with:
- a hook and "full crazy graphics" for everything he explains;
- the TaxWise logo animated and used throughout;
- the gold and royal-blue brand theme, used only lightly;
- his "aura" (the pull-outs);
- the SFX library, used generously;
- their song ("Timeless Instrumental") under it all.

- **Source:** the team's reel (1080x1920, 30 fps). He talks at his desk, and 23 s of it is a camera
  pointed at a cabinet while he keeps talking. Their Drive link is kept out of git: the repo is public.
- **Output:** 52.0 s, 1080x1920, 30 fps, -14 LUFS.

## The cut (tools/edl.py)
His eleven lines run in order. The director's cues ("Okay", "Go", "take one, start", "Go") are cut. The
cabinet footage is dropped, and those lines play as voice-over on full-screen graphics. Every word's time
comes from offline ASR (Silero VAD + Parakeet, tools/words.py).

The song is 120 BPM (a bar every 2 s, downbeats from 0.5) and plays from 187.542 s. Its own structure
lands on his words:
- the drums drop out on "TaxWise" (8.5);
- half a beat of silence carries "into...";
- the beat slams back on "SINGAPORE" (12.5);
- a new lead lifts in at 24.5;
- six bars are lifted out at 30.5, on a 2-bar progression, so the seam is spectrally invisible;
- the drums stop 0.8 s after "this is just the beginning", and one chord rings over the logo.

| Output | Picture | He says |
|---|---|---|
| 0-6.1 | **Hook.** Slow pull-out from a close-up. A gold horizon line ignites, the Singapore skyline draws itself on, and A NEW HORIZON rises. The city eases back and a gold wireframe globe spins up | "Big ambitions deserve bigger horizons. And we're taking ours global." |
| 6.1-12.5 | **Aura pull-out** (1.45x to 1x) reveals HK VINAY on the wall behind him, then MANAGING PARTNER and the TW mark drawing itself on. The music drops out. A loading line sparks across the wall word by word, and EXPANSION floods with gold | "I am HK Vinay, Managing Partner at TaxWise. And I'm excited to announce our expansion into..." |
| 12.5-14.2 | **The drop.** SINGAPORE slams in letter by letter, the mark assembles, NOW IN, the pin | "...Singapore." |
| 14.2-25.5 | **The team.** Gold points form 30+ people, the counter slams 30+. They condense into the TW mark, and five services burst out on their words. At the lift the network glows: ONE CONNECTED FINANCE FUNCTION | "With a dedicated team of over thirty in-house specialists..." |
| 25.5-35.6 | **The globe** (a match cut from the network's sphere). A gold dot-matrix Earth, BANGALORE and CHENNAI, comets to SINGAPORE (NEW OFFICE), a bridge of arcs, INDIA × SINGAPORE | "From supporting businesses in India to helping them navigate Singapore's financial landscape..." |
| 35.6-42.4 | Through a gold pulse, back to him with an aura pull-out. OUR COMMITMENT, then Expertise, Transparency, Lasting relationships land on the wall behind him with punch-ins | "Our commitment remains the same..." |
| 42.4-48.3 | The mark assembles behind him, the skyline draws on again, and a pin drops on Marina Bay Sands: NOW IN SINGAPORE. A sunrise grows into a gold bloom | "TaxWise, now in Singapore. And trust us, this is just the beginning." |
| 48.3-52.0 | **The logo end card**, dissolved through the bloom: TAXWISE CONSULTANTS, BANGALORE \| CHENNAI \| SINGAPORE, twchartered.com | (one chord rings out) |

## Graphics (slots/)
- Eight HyperFrames compositions, built in parallel from one brief (slots/BRIEF.md) and four specs (slots/SPEC_*.md).
- **The brand system:** design/taxwise.css (midnight navy, champagne gold, ivory, a little royal blue;
  Cormorant Garamond and Montserrat, OFL) and the TW mark rebuilt as clean symmetric vector geometry in three
  parts (design/tw-mark.js, tools/logo_vector.py), so it can assemble, draw on and shine.
- **Wall layers** (`*_behind`) are designed in source coordinates. They sit on the wall behind him and
  move with the camera.
- **The globe** shows India's official boundary.

## Picture (tools/composite.py, fx.py, plates.py, captions.py)
- **Him:** person mattes (tools/mattes.py: rembg + guided filter + temporal median), then:
  - the matte's soft tail tightened with a colour key against the wall, where his hair is dark;
  - his edges decontaminated (luminance only) against the wall behind them, estimated from the same frame;
  - a warm, clean skin grade;
  - a gold hair light from behind, which flares on the aura pull-outs, with a soft gold halo on the wall.
- **The room:** re-lit as a muted midnight-navy set, with a touch of royal blue behind his head. The desk is
  graded as dark wood below its back edge. Per shot, that edge is a straight line, measured from the clean
  plate: the slope from the front edge, the height from bare-wall columns.
- **The camera:** zooms about his measured face position per shot: the pull-outs, the pushes, the punch-ins.
- **Hits:** flash, zoom blur, chromatic kick, shake and a glitch cut, on the drop and every transition.
- **Captions:** Montserrat 800 word pops, with key words in gold, on the on-camera sections only. They are
  skipped during his name card, which is its own caption.
- **Finishing:** vignette and grain.

## Sound (tools/dialogue.py, tools/mix.py)
- **Voice:** classical DSP only:
  - a band-split mono (the two phone capsules summed below 1.5 kHz, the left one above);
  - an 80 Hz high-pass, per-take spectral denoise and late-reverb suppression;
  - broadcast EQ and a de-esser.
  - Background noise is 15 dB lower (SNR 23.8 dB to 38.4 dB).
  - Every line is levelled to the same loudness, then a fader ride, a 3:1 compressor and a peak catcher.
- **Song:** ducked in the speech band only under his voice (the kick, bass and shimmer stay), and lifted
  where he is silent. The drop is the loudest moment.
- **Sound design:** about 290 effects, on every cue the graphics builders reported:
  - all 28 effects of the library (risers, bass whooshes, sword slashes and impacts, electric hit,
    lightning, glitches, tape stop, slow-mo, radio, reload, fire and rain beds);
  - plus synthesised glints, pops, ticks, sparks, comets and sub hits, tuned to the song (B minor).
- **Master:** -14 LUFS, -1 dBTP. Voice-to-bed is about 15 dB in the speech band.

## Rebuild
`./build.sh` (see it for the inputs, which are kept out of git).
