# Jayashree D Jain: event reel

Brief, from the client's team: an Instagram reel from the footage of her recent event, to go viral. They
didn't need her singing or her own voice heard: an edit of the event, a little focused on her, with the
dignitaries who attended. They wanted it cultural and classical but cinematic, with warmth in the grade,
VFX and sound design. It should run about a minute, over the raag mashup they sent.

- **Source:** 58 iPhone clips (4K HEVC, mostly HLG HDR, portrait) from the client's Google Drive. The
  folder link is kept out of git: the repo is public.
- **Music:** "BLEND OF RAAG (Indian Classical Mashup Trilogy Finale)" by sagarswarup × Sunix Thakor.
- **Event:** the Siddha Navagraha Tirthankara Maha Aradhana (ಸಿದ್ಧ ನವಗ್ರಹ ತೀರ್ಥಂಕರ ಮಹಾ ಆರಾಧನ), as
  read from the on-site banner.
- **Output:** 65.4 s, 1080x1920, 30 fps.

## The cut (tools/edl.py)
The song runs from 1:24.134 to 2:29.5 of the track, 88 BPM, and is instrumental throughout. Her
on-screen singing never fights another voice, and every cut lands on its beat grid.

| Output | Music | Picture |
|---|---|---|
| 0-2.7 | groove, from a downbeat | **hook**: her mid-phrase, a bell on frame one. THIS IS NOT / A CONCERT. |
| 2.7-30.7 | the groove | the world of the event: the hall, the Tirthankaras, the musicians, aarti, offerings, sadhvis. About every other shot is her; her name sits on the first (5.6 s). Cuts on 2 beats, her shots on 4; light-leak flashes and whip pans |
| 30.7-46.4 | **the breath**: the drums drop out | optical-flow slow motion and cross-dissolves. Her close-up ("it's a prayer."), aarti flames, hands holding a diya (from the 4K original), the idols under god rays with the event's name in Kannada, raised hands speeding into the drop |
| 46.36 | **drop 2** | flash, zoom burst, shake: the hall's hands go up |
| 46.4-61.4 | the climax | 2-beat cuts: her, the dance, the dholak, the chief guest at the podium, a dignitary garlanded on the big screen, the full-hall pan |
| 61.4-65.4 | the rhythm stops, a pad | her in slow motion; end card: name, CLASSICAL VOCALIST, follow for more |

## Picture (tools/composite.py, look.py, fx.py, titles.py)
- **Decode:** HLG is tone-mapped to SDR with hable at 100 nits (tools/media.py) into 1080x1920 proxies.
  The diya close-up is decoded from the 4K original for a 1.9x crop.
- **Grade:** a warm golden look baked into a 256³ LUT, with two looks: `gold`, and a warmer `candle` for
  the breath and end card. It runs:
  - a warm white balance and a filmic curve with a long highlight shoulder;
  - warm-brown shadows and golden highlights;
  - hue-selective saturation: saffron, marigold and maroon up; yellow sarees held back; blue LED walls
    and chairs down; skin protected.
  - After the LUT: clarity, bloom on the lamps and chandeliers, red halation, a warm vignette and fine
    grain.
- **Light:** god rays streaming from the chandeliers, windows and the idols' canopy; rising golden dust
  and bokeh; procedural light leaks on flash cuts and drifting through the breath.
- **Motion:** slow push-ins framed per shot, punch-ins on the cuts, whip pans with motion blur, DIS
  optical-flow slow motion, a speed ramp into the drop, a shake, zoom blur and chromatic kick on the
  drop.
- **Titles:** Cinzel, Marcellus, Cormorant Garamond italic and Noto Serif Kannada, in ivory-to-gold.
  Latin titles reveal letter by letter, the Kannada line writes on, all over a soft warm scrim. Every
  title stays inside Instagram's safe zone.

## Sound (tools/mix.py, sounds.py)
- **Song:** the window above, a 1.6 s fade under the end card.
- **Synthesised temple sounds, tuned to the song's Sa (C#):**
  - brass bells, from detuned mode pairs: a struck bell on the hook, the deep bell into the breath, on
    the drop and under the end card;
  - the aarti hand bell over the flames, ghungroo shimmers on the light flashes, a shankh on the drop.
- **Library (library/sfx):** whooshes on the whips, the slow-motion swell into the breath, the build and
  bass hit into the drop, the fire bed under the aarti.
- **Master:** -14 LUFS, -1 dBTP. A no-music mix ships too, in case Instagram mutes the song: re-add the
  track there from 1:24.
