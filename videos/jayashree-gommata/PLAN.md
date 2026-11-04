# Jayashree D Jain: "Cheluvara Cheluva Namma Gommata Deva" reel

The first of a series of clips for her Instagram account, cut from her performance video. The brief:
- choose the best part and make it professional;
- bring the culture out;
- grade, VFX, SFX and transitions, built to travel on Instagram.

## The source
- **What it is:** the client's YouTube copy of the Kaveri Dham programme, 11:44 long and 640x360, from their
  Drive. The Drive link is kept out of git: the repo is public. The programme is the Bhagavan Bahubali Swamy
  Pratishtha Mahotsava at Basadi (Basti) Hosakote, Mandya district, on 25 November 2023.
- **Her:** Jina Gaana Visharade Smt. Jayashree D Jain, Horanadu. She sings two songs, "Cheluvara Cheluva Namma
  Gommata Deva" (0:00-6:44) and "Bandevu Kaveri Purake".
- **The picture:**
  - she is on stage only in the first 36 s, in one wide static shot;
  - the rest is the ceremony around the black stone Gommata, often handheld: the abhisheka pours at the head,
    the legs carved with creepers, the feet with flowers, the kalasha line, the Jain flag, the dancing
    devotees, and one blue-sky shot with the red chhatra.
- **What every crop excludes:** a live ticker, a date/time box and a channel logo are burned in. tools/media.py
  keeps all crops inside the clean area, in normalised coordinates. A sharper copy (renders/src/hd/*.mp4) drops
  straight in.
- **Lyrics:** from offline Whisper (turbo, Kannada) in sliding windows, corrected by hand. The refrain is:
  - A: ಚೆಲುವರ ಚೆಲುವ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ, "fairest of the fair, our Lord Gommata";
  - B: ಇವ ತ್ಯಾಗ ವೀರ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ, "the hero of renunciation, our Lord Gommata".

## The cut (tools/edl.py)
The song's finale plays as one continuous take, source 6:13.98-6:44.6, with no musical edits:
- the last refrain: A B A, then B three times, the last ending on a long held note;
- the chant "ಜೈ ಬೋಲೋ ಗೊಮ್ಮಟೇಶ್ವರ ಬಾಹುಬಲಿ ಭಗವಾನ್ ಕೀ — ಜೈ!";
- the song's own ending.

It hooks on the title line from frame one and pays off on a shouted "Jai!". The rhythm:
- ~138 BPM, Sa = G# (the drone's strongest pitch);
- the tabla's bass stroke falls every 4 beats, and each line starts on one;
- every cut lands on a stroke, except the flash cut on "ಜೈ!".

| Reel | Picture | Text |
|---|---|---|
| 0-4.1 | the statue's face, devotees pouring above, push-in, god rays | A |
| 4.1-7.5 | her, singing | B; her name glows |
| 7.5-11.0 | the pours at the head, two angles | A |
| 11.0-14.5 | the legs carved with creepers; the feet with flowers | the event, in Kannada and English |
| 14.5-19.6 | the kalasha line, the flag and the saffron robes, the dancing devotees | B |
| 19.6-23.0 | her, the held note | B |
| 23.0-27.7 | the flag and the statue; the chhatra against the blue sky | the chant |
| 27.7-29.4 | flash, zoom burst, petal burst: the face | ಜೈ |
| 29.4-33.0 | her | the song's title, JAI JINENDRA |

## Picture (tools/composite.py, layout.py, look.py, fx.py, titles.py)
- **Layout:** the 360p source can't fill a 9:16 frame cleanly (it would be enlarged ~6x).
  - The footage sits in a 4:3 window, enlarged ~2.2-3x (Lanczos and a light unsharp mask), with a
    temple-gold double border, lotus-bud and diamond ornaments, a glint that travels round it, and a flare on
    every cut.
  - The canvas is deep temple maroon, with the shot blurred into a soft glow, a slowly turning gold lotus
    mandala and a warm halo behind the window.
- **Grade (v2, tools/grade.py):** the client found v1 too bright and asked for more contrast, better colour and
  clarity.
  - **Why v1 was milky:** her event reel's gold LUT had lifted a source that was already washed out. The
    window's darkest parts sat at 12-46% and its midtones at 61-79%. 68-76% of each statue frame is blown
    white, and the black stone read mid-grey.
  - **Measured per shot,** once, from three frames (so nothing flickers):
    - levels: the 0.7th luma percentile becomes black and the 99.7th white;
    - a gamma that brings the subject's median to ~0.44 (the blown sky is ignored in the measurement);
    - an S-curve with a soft shoulder, so whites stay a clean warm white instead of v1's cream.
  - **Colour:**
    - a touch of warmth;
    - vibrance on muted colours (saris, the flag, marigolds), with skin, blue sky and shadows protected;
    - the stream's blue cast on the stone neutralised to charcoal, with warm shadows.
  - **Clarity:** at source resolution, an edge-preserving denoise (against the stream's blocking) and gentle
    CLAHE local contrast; after the enlargement, a two-radius unsharp mask.
  - **No haze:** no bloom or god rays in the window. A soft graduated filter and the window's own vignette
    tame the white areas. Grain and a vignette finish the frame.
- **VFX:**
  - golden dust and bokeh;
  - falling flower petals (marigold, yellow, rose, pink, jasmine): the song's own ಪುಷ್ಪ ವೃಷ್ಟಿ;
  - on "ಜೈ!", a burst of petals with a flash, a zoom burst and a light leak.
- **Titles:** the same family as her event reel: Cinzel, Marcellus, Cormorant Garamond italic and Noto Serif
  Kannada, ivory to gold.
  - Her name stays up for the whole reel.
  - The lyrics write on in Kannada with the English meaning below.
  - The event card, the big ಜೈ and the end card are drawn the same way.
  - All type stays inside Instagram's safe zone.

## Sound (tools/mix.py, sounds.py)
- **Song:**
  - her recording, untouched in timing;
  - processing is only a 35 Hz high-pass and +2.5 dB of air above 6 kHz, because the YouTube copy is dark.
- **Temple sounds**, synthesised and tuned to Sa:
  - a deep bell on the first frame;
  - a small bell as she appears;
  - a shankh under "ಜೈ ಬೋಲೋ";
  - the deep bell, a ghungroo shimmer and a soft library whoosh on "ಜೈ!";
  - a tanpura drone under the end card, fading so the loop restarts on the bell.
  All of them sit ~15 dB under her.
- **Master:** -14 LUFS, -1 dBTP.

## Rebuild
`./build.sh` (see it for the inputs, which are kept out of git).
