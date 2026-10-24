# SHELF CAMPUS: founders reveal, the recut

Source: the founders' own 72 s Instagram reel (Jnanottam and Kartik to camera, plus 14 s of the floor
under a voice-over) and the song they picked, "The Kill 2" (Lex Amarni & 2muchmotion). Brief: "top
class... crazy... more VFX, more SFX, studio-grade audio and colour, full graphics for everything we
explain, WhatsApp everything". Their script (Reel 02) was the reference. Output: 60.7 s, 1080x1920, 30 fps.

## The cut (tools/edl.py)
Three moments of the song carry the story (102.89 BPM, measured):
| Output | Beat | What lands |
|---|---|---|
| 0.0-9.9 | HOOK + CHAOS: "your academic life is a crime scene" | the song's muffled intro (one bar looped so it lasts), police lights on the wall, the 256 GB bar, a WhatsApp storm, an evidence board |
| 9.9-11.2 | tape stop, freeze, case-file stamps | ACADEMIC WEAPON. ORGANISATIONAL DISASTER. in silence |
| 11.70 | **drop 1 on "JNANOTTAM"** | the wall goes deep navy; flash, shockwave, glint, the name slams in behind him |
| 14.03 | KARTIK on the bar | the same, then the two-founders poster (both cut out, side by side) |
| 22.77 | **the bass stops on the cut to black** | one ping in the dark, the logo emerges through the breakdown |
| 25.68 | **drop 2 on "SHELF"** in "Meet SHELF Campus" | the logo slams, lightning, CAMPUS on the next syllable |
| 32.1-45.5 | the demo (replaces the floor shot) | a WhatsApp chat with SHELF, every message on a beat, SAVE / FIND / TRACK / ACTUALLY SUBMIT IT |
| 45.5-56.97 | payoff + CTA, reordered to alternate the founders as in the script | bass-hit freeze on "useful", the semester update |
| 56.97-60.67 | end card | ends on a bar line: the loop restarts the intro |
Cut: the "close up, confident delivery" blooper (Jnanottam reading a stage direction). Bleeped: the
f-word (the library's radio beep over a matched tone, a censor bar on the mouth, a redaction bar in the
captions).

## Picture (tools/composite.py, direction.py, fxlib.py)
Grade: filmic S-curve, local-contrast clarity, the yellow sunglasses lifted, per-section looks (tense,
freeze, night, day). The wall is re-lit on its own through person mattes (u2net_human_seg + guided
filter, tools/mattes.py): police beacons in the hook, deep navy with a rim light for the founders, a
cleaner warm white for the payoff. Camera moves centre on the sunglasses (found per frame). Graphics are
HyperFrames slots (slots/BRIEF.md + SPEC_*.md), built in parallel; "behind" slots sit under the person.
Captions are drawn last (tools/captions.py, Sora 800), only where the words are not already big type.

## Sound (tools/dialogue.py, mix.py)
Dialogue, classical DSP only: denoise per recorded clip, late-reverb suppression, broadcast EQ, de-ess;
then each line levelled (Kartik sat 12-20 dB under Jnanottam), compressed, saturated lightly. The song
is re-cut on bar lines (above), ducked and speech-band carved under every line (>= 7 dB speech over
music + effects on every line, tools/audio_check.py). Sound design from the SFX library (library/sfx, by
hit point) plus synthesised UI sounds; the drops land out of a 100 ms vacuum. Master: -14 LUFS, -1 dBTP.
A no-music mix ships too, in case Instagram mutes the song.
