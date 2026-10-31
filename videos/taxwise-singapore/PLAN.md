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

## Sound, v5: his re-recorded voice (tools/adr.py, tools/dialogue.py)
- **The takes:** HK Vinay re-recorded his six lines to the karaoke guide (below), one file per line.
  - They are phone recordings, AAC 64 kb/s mono (clean up to about 12 kHz).
  - The room is dry. 200 ms after a phrase his voice is 38-50 dB down; the office was 20 dB, Adobe 41.
  - Every line is clear. The offline recogniser hears each one as scripted, apart from its usual slips on
    "horizons" and "in-house", which it also made on the original.
  - Two takes begin with the phone's gain-pumped room noise, so each line fades in 60-100 ms before its first
    word.
- **The fit (tools/adr.py), the way dialogue-replacement tools work:**
  - **Matching.** Dynamic time warping matches each take to the original, using the echo-free Adobe version
    as the timing guide.
  - **Anchors.** They are every onset after a pause, plus word onsets on camera and the words the graphics
    are cued on.
  - **Placement.** Dynamic programming places the anchors. A missed anchor costs more when the audio would
    run ahead of his lips.
  - **Pauses first.** The pauses absorb the differences, keeping 80 ms of natural decay and 40 ms before each
    word. Only then do the words speed up or slow down: at most 22% on camera, 16-20% on the voice-over.
  - **Virtual pauses.** Where the original paused but the take runs on (15 places, for example "our ...
    expansion", "navigate ... Singapore's", "building ... lasting"), a short silence opens at the take's
    quietest point.
  - **Rendering.** WSOLA renders the result with the pitch untouched.
  - **Result.** An independent envelope check puts 90% of the on-camera words within 40 ms of the original
    (96% within 80 ms). The graphics' cue words ("thirty", the five services, "India", "Singapore's",
    "connections", "across borders") are within 20 ms. 40-85% of each line's speech plays untouched; the
    rest mostly changes speed by under 10%.
- **EQ (dialogue.py):** the same broad EQ on all six lines:
  - a 75 Hz high-pass;
  - +2.5 dB at 320 Hz, the body a phone mic loses;
  - -2.5 dB at 2.8 kHz, its honk;
  - +3 dB at 5.1 kHz, to fill a notch the phone's mic puts there.
  Then each line is matched toward the six's average: 60% of the smoothed difference, at most 4 dB. They were
  recorded minutes apart, with the phone held a little differently. Nothing else.
- **Mix:** the v3 chain, unchanged. -14.2 LUFS, -1.2 dBTP. His voice sits 17.8 dB over the music and effects
  in the speech band; the drop is still the loudest moment.

## Sound, v4: the voice
The room's echo is baked into the phone recording. The client ran the original
(renders/deliver/TAXWISE_voice_for_Adobe_Enhance.wav) through Adobe Podcast "Enhance Speech" and sent it back.
- dialogue.py aligns it to the original by FFT cross-correlation (the offset was 1 sample) and high-passes it at
  70 Hz. Nothing else.
- Echo: 200 ms after a phrase the voice is now 43-46 dB down (the original was 14-19 dB down).
- Lip sync is exact on every line.
- The mix chain below is unchanged.
- An offline transcription of Adobe's version mishears a few words ("ambitions", "horizons", "payroll",
  "trust us"). The client confirmed they sound off: Adobe blurs consonants at high strength. Hence the re-record
  (v5, above).

## Re-recording the voice (tools/karaoke_timing.py, tools/karaoke.py)
- **The guide:** a 58 s karaoke video (renders/deliver/TAXWISE_VO_karaoke_*.mp4):
  - the reel plays at the top, so he can match his lips on the on-camera lines;
  - his lines are below it, and every word fills with gold at the moment he said it in the reel;
  - before the first line, a 3-2-1 count-in with beeps;
  - before every other line, three dots fill;
  - the next line is previewed.
- **The timing:** the word times come from the ASR. Each script word maps one to one onto an ASR word. The 28
  phrase-initial starts that the ASR put early are snapped to the onset of his voice.
- **Two versions:** one has his original voice, to hear in earphones. The other is silent, for when the guide
  plays in the same room as the microphone.
- He recorded each line as its own file, on a phone, in a dry room (v5, above).

## Sound (tools/dialogue.py, tools/mix.py), v3
- **History:** v1 and v2 processed the phone recording heavily:
  - v1: denoise, dereverb, a fader ride and 3:1 compression;
  - v2: WPE dereverberation, a harmonic exciter and a downward expander.
  The client heard it as muffled and echoey, then as "very very wrong". v3 starts fresh with the opposite
  approach: keep his voice as recorded.
- **Voice:** his original stereo recording from the team's reel, kept stereo (summing the two phone capsules to
  mono comb-filters the highs). Only linear processing:
  - a 75 Hz high-pass;
  - -2 dB at 250 Hz, +2.5 dB presence at 3.5 kHz, +2 dB air from 8 kHz;
  - the room's width narrowed a little (side x 0.7).
  In the mix, every line is set to the same integrated loudness, then a light stereo-linked 2:1 compressor
  (about 1.5 dB while talking) and a peak catcher. Lip sync is checked by cross-correlation against the
  original: within 0.3 ms on every line.
- **Song:**
  - a smooth broadband duck under his voice (-7 dB), held 0.5 s so it doesn't pump in short pauses;
  - lifted where he is silent;
  - no ducking through the drop, so the beat hits at full level on "SINGAPORE".
- **Effects:** 71 curated cues from the library (whooshes on the transitions and the type, the drop's bass hit,
  risers into the drop, the lift and the bloom, the logo's sting) plus a few glints tuned to the song (B minor).
- **Balance:** his voice is about 16 dB over the music and effects in the speech band, and the music bed sits
  about 10 LU under him. The drop is the loudest moment.
- **Master:** -14 LUFS, -1 dBTP.

## Rebuild
`./build.sh` (see it for the inputs, which are kept out of git).
