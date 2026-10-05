# S.H.E.L.F reel — the recut

Source: the team's finished 2:00 Instagram reel (a skit + the S.H.E.L.F reveal). Brief: "make it
top class… crazy… VFX, SFX, wow factor". Output: 1:49, 1080x1920, 30 fps.

## Constraint that shapes everything
The source's dialogue and music bed are one mixed track (stem separation was not available).
So every spoken line keeps its exact timing and audio. Speed, order and sound design change only
where nobody speaks, and every join gets a 30 ms fade plus a sound that masks the music jump.

## Story arc and what changed
| Output time | Beat | Treatment |
|---|---|---|
| 0.0–3.5 | **Hook (new)**: the breakdown line as a cold open | notification storm teaser, punch-ins, red hit |
| 3.5–4.3 | **Rewind (new)** | VHS rewind through the whole story backwards, tape chatter |
| 4.3–12.3 | Wake-up: 17 s compressed to 8 s | alarm crash zoom, speed ramps (frame-blended), ticking clock, heartbeat into the riser |
| 12.3–15.9 | "F*ck — I have an exam in 8 hours" | red panic hit, 08:00:00 countdown slams in, then lives in the corner |
| 15.9–44.4 | The call | calling/in-call UI, rings kept (third ring cut), whip cuts, a card per group chat |
| 44.4–51.8 | Breakdown | cards blow apart, notification storm, racing clock, vertigo push, glitch-out |
| 51.8–70.2 | Founders | white flash to calm, sunglasses glints, giant words BEHIND them (person mattes), freeze-frame name cards with a tape-stop |
| 70.2–83.3 | "Your files are everywhere…" | glass tiles multiply, orbit Kartik, tangle at "complicated?" |
| 83.3–92.7 | "…pretty simple. So we built S.H.E.L.F" | hard reset to calm, the S.H.E.L.F payoff hit, tiles dock into one panel |
| 92.7–108.9 | Tease → STAY TUNED → wall reveal | lean-in + glitch into the card, end hold (the 2.4 s black tail removed) |

## System
- Captions rebuilt: old burned-in captions inpainted out, new word-synced captions (Sora 800; amber
  in the problem world, S.H.E.L.F blue in the founders' world).
- Grade: restrained S-curve + split-tone; cooler/tenser before the founders, warmer after.
  Vignette + fine grain glue footage and graphics.
- Sound: -14 LUFS / -1 dBTP. Every visual hit has a sound on the same frame. Cues for the
  notifications and tiles come from the overlay renders themselves.

## Files
`tools/edl.py` (cut list) · `tools/direction.py` (every camera move and look) ·
`tools/composite.py` (the frame engine) · `tools/mix_audio.py` (sound) · `slots/*` (HyperFrames
overlays, see `slots/BRIEF.md`) · `design/` (shared fonts, tokens, logo mark) · `build.sh`.

## v2 — WhatsApp-first, cut to the song (Oct 5)
Brief: notifications should be WhatsApp (the class's notes live in WhatsApp groups), S.H.E.L.F
itself runs on WhatsApp, and the edit should follow the song their reel is cut to ("My Eyes",
147 BPM), which builds and gets more hyped. Plus: what Instagram needs for a reel to travel.

**Sound.** The song sits in their mix unprocessed at -17.5 dB from sample 0, so it is subtracted
(tools/dialogue.py) instead of separated: clean dialogue, music removed by 22-30 dB. The song is
then laid continuously (tools/music.py) instead of being chopped with the picture:
| Output | Song | What lands |
|---|---|---|
| 0.0-3.5 | the pre-drop bar | drop 1 on "f*ck" (0.797) |
| 4.3-51.8 | ambient intro → groove (35.6) → hi-hat build (43.7) | the bass drops out as his head goes into his hand (48.57); 808 pickups 50.61, 51.22 |
| 51.8 | DROP 1 | the white flash into the founders |
| 83.4 | the breakdown | the hard reset ("pretty simple") |
| 87.4-88.2 | 0.76 s of dead silence, then DROP 2 | "so we built…" in silence, "S.H.E.L.F" on the drop |
| end | drop 2 | the last frame loops into the hook on the beat |
The founders' freeze frames and every cut after them were moved by 1-9 frames to sit on beats.
Music is carved under speech (speech band -11 dB, lows kept), dialogue is levelled; -14 LUFS.

**Picture.** WhatsApp everywhere (slots/BRIEF.md v2): iOS banners with WhatsApp group messages,
a WhatsApp voice call, the scattered stuff as WhatsApp documents/voice notes/forwards, and the
payoff as S.H.E.L.F answering inside a WhatsApp chat. On the music: beat bumps on every bar in the
drops, tunnel vision (colour drains) in the bass-out gap and the silence, radial blur and a
shockwave on each drop, the storm and the racing clock on the song's 8ths and 16ths.

**Instagram** (research, cited in the delivery notes): a "14 groups. 0 notes." title on frame 1
(the ranker predicts sub-3 s skips), a send-this ending (sends drive non-follower reach), a beat-
seamless loop, the f-word bleeped with a WhatsApp ping (strong language is not recommended to
teen accounts), and a 48 s main cut (tools/shortcut.py: 30-60 s reels get the best reach) with
the full 1:49 as part 2.
