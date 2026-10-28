# Jayashree D Jain: event reel

The client's team asked for an Instagram reel from the footage of her recent event, to go viral. They
didn't need her singing or her own voice heard: an edit of the event, a little focused on her, with the
dignitaries who attended. They wanted it cultural and classical but cinematic, with warmth in the grade,
VFX and sound design.

- **Source:** 58 iPhone clips (4K HEVC, mostly HLG HDR, portrait) from the client's Google Drive. The
  folder link is kept out of git: the repo is public.
- **The event:** the Siddha Navagraha Tirthankara Maha Aradhana (ಸಿದ್ಧ ನವಗ್ರಹ ತೀರ್ಥಂಕರ ಮಹಾ ಆರಾಧನ),
  as read from the on-site banner. It was held at Palace Grounds, Bangalore, on Sunday 25 October 2026.
- **Her:** Jina Gaana Visharade (the title conferred on her) Jayashree D Jain, Jain Devotional Vocalist.
- **v1** (commit 6202701) ran 65 s on "BLEND OF RAAG". **v2** moves to the song they chose next,
  "Chanakya" by Rishab Rikhiram Sharma, the 45 s edit audio. They also asked for a quicker pace
  everywhere except her shots, and for the title, role, place and date on screen.
- **v3** (this one) replaces the v2 hook ("This is not a concert. / it's a prayer."), which they didn't
  like. Of four options previewed on the frames, they chose "Jai Jinendra / an evening of pure bhakti.".
- **Output:** 39.1 s, 1080x1920, 30 fps.

## The cut (tools/edl.py)
The song is in D at 140 BPM. The grid was fitted to its kicks and snares to within 14 ms. A sitar intro
builds with no percussion, the beat comes in at 11.84 s and the bass a bar later. The reel plays it from
4.13 s, so the intro keeps 18 pulses of the build.

| Output | Music | Picture |
|---|---|---|
| 0-7.7 | the sitar build | **hook**: her mid-phrase, a bell on frame one: JAI / JINENDRA (the Jain greeting). Then aarti flames in slow motion: "an evening of pure bhakti." Then her close-up in slow motion: JINA GAANA VISHARADE / JAYASHREE D JAIN / JAIN DEVOTIONAL VOCALIST |
| 7.71 | **the beat comes in** | flash, zoom burst, shake: the hall's hands go up |
| 7.7-35.1 | the beat | the event, quick. B-roll runs 2 pulses (0.86 s), or a 3-3-2 burst on the song's accents (bar + 0, 1.5, 3, 4). Her shots are held for 4 pulses (1.7 s), every fourth or fifth shot. The event card (Kannada title, English, PALACE GROUNDS, BANGALORE, SUNDAY · 25 OCTOBER 2026) rides over four quick shots of the idols and aarti. Then the dignitaries: the chief guest at the podium, the dais in pink turbans, a garlanding on the big screen. The climax is the dance, the dholak, the whole hall |
| 35.1-39.1 | the last phrase and the fade | her in slow motion; end card: the honorific, her name, her role, follow for more |

She is on screen for 51% of the reel.

## Picture (tools/composite.py, look.py, fx.py, titles.py)
- **Decode:** HLG is tone-mapped to SDR with hable at 100 nits (tools/media.py) into 1080x1920 proxies.
  Heavy crops (the diya, the dais) are decoded from the 4K originals.
- **Grade:** a warm golden look baked into a 256³ LUT, with two looks: `gold`, and a warmer `candle` for
  the intro's slow motion and the end card. It runs:
  - a warm white balance and a filmic curve with a long highlight shoulder;
  - warm-brown shadows and golden highlights;
  - hue-selective saturation: saffron, marigold and maroon up; yellow sarees held back; blue LED walls
    and chairs down; skin protected.
  - After the LUT: clarity, bloom on the lamps and chandeliers, red halation, a warm vignette and fine
    grain.
- **Light:** god rays streaming from the chandeliers, windows and the idols' canopy; rising golden dust
  and bokeh; procedural light leaks on flash cuts and drifting through the intro and end card.
- **Motion:**
  - slow push-ins framed per shot, and punch-ins on every cut after the drop;
  - whip pans with motion blur;
  - DIS optical-flow slow motion;
  - a shake, a zoom blur and a chromatic kick on the drop and on the bass;
  - an exposure pulse on the song's accents.
- **Titles:** Cinzel, Marcellus, Cormorant Garamond italic and Noto Serif Kannada, in ivory-to-gold.
  Latin titles reveal letter by letter, the Kannada line writes on, all over a soft warm scrim. Every
  title stays inside Instagram's safe zone.

## Sound (tools/mix.py, sounds.py)
- **Song:** from 4.13 s with a 0.25 s fade-in, through to the track's own fade.
- **Synthesised temple sounds, tuned to the song's Sa (D):**
  - brass bells, from detuned mode pairs: one on the hook, the deep bell on the drop and the end card, a
    bell on Pa for the event card;
  - the aarti hand bell over the flames, a shankh on the drop, ghungroo on the light flashes.
- **Library (library/sfx):**
  - a riser and bass hit into the drop;
  - swells into the intro's dissolves;
  - whooshes on the whips;
  - the fire bed under the aarti.
- **Master:** -14 LUFS, then a 4x-oversampled limiter at -1.2 dBFS for the track's own 0 dBFS peaks. A
  no-music mix ships too, in case Instagram mutes the song.
