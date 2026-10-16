# CR aura edit

An aura-farming edit of a WhatsApp meme video about the user's class CR (class representative).
The source video, its frames, mattes and every render stay in the gitignored `renders/`. Only the
tools, fonts and these notes are committed.

## The source (30.9 s, 576x1024, 30 fps, WhatsApp ~0.9 Mbps)

The meme is a podcast clip followed by the CR on a beat: he is the real G.O.A.T.

**Podcast, 0–12.9 s.** The lines, transcribed locally with `tools/transcribe.py` (Whisper turbo via sherpa-onnx):

| time (s) | speaker | line |
| --- | --- | --- |
| 0.25 | she | "I can imitate goats." |
| 4.09 | host | "Please do." |
| 4.95 | she | "MAAA!" |
| 7.35 | host | "Take two." |
| 7.5–11 | she | laughs, "I can't believe I'm doing this", a second bleat |

**CR clips, 13.17–30.87 s.** Eleven clips (frame ranges are source frames):

| clip | frames | what he does |
| --- | --- | --- |
| A | 402–441 | behind the monitors |
| B | 442–474 | on his phone at the board |
| C | 475–508 | turns and smiles |
| D | 509–542 | the stare |
| E | 543–577 | chin pose |
| F | 578–609 | typing |
| G | 610–643 | smiling, red curtains |
| H | 644–677 | thumbs-up, then turns away |
| I | 678–709 | the smirk |
| J | 710–743 | close smile |
| K | 744–925 | waves, walks off across the lab, turns back and smiles |

**Song.** A ~108 BPM trap/phonk beat.
- The first downbeat is at 13.085 s, and the song runs exactly 8 bars to the end of the file.
- The 808 plays a 3-3-4-3-3 eighth-note pattern per two bars, with fills at eighths 31–32 and 56.5–62.
- Claps fall on beat 3 of every bar.

## The edit (23.5 s, 1080x1920, 30 fps); see `tools/edl.py`

### Hook, 0–3.7 s

- The podcast, tightened to four lines with captions and a natural grade: "I can imitate goats." / "Please do." / "MAAA!" (zoom punch) / "Take two."
- The host's last frame desaturates and the tape stops.
- So the CR becomes "take two", the real G.O.A.T.

### Strobe, 3.7–4.0 s

His silhouette parts flash on black, one frame each: head, then body, then the whole of him. Each part shows as a white matte and then as a red cut-out.

### Drop, 4.0 s

- The song's first downbeat.
- A white flash, a shockwave, chromatic aberration, and the letterbox bars slam in.
- **THE G.O.A.T.** (gold Cinzel) appears on the board *behind* his head during the stare, at half speed. He leans in and covers it.

### The rest, one move per 808 hit

| time (s) | move |
| --- | --- |
| 5.11 | white silhouette flash on the clap |
| 5.67 | the turn, slow motion with flow interpolation and echo trails |
| 6.78 | the chin pose frozen; the background dims, a gold aura outline and "+1000 AURA" appear |
| 7.61 | the phone shot pushes in, then a zoom-blur suck to white |
| 8.44 | double exposure: the stare silhouette on white, filled with the walk-off shots, changing every eighth. The music is low-passed. The last two frames are a solid black silhouette. |
| 10.11 | the filter opens on the hit: typing |
| 11.22 | the smile; the red curtains flash white on three eighths |
| 12.06 | thumbs-up into the lens, then a whip as he turns away… |
| 12.89 | …a whip into the smirk with a shockwave, then a silhouette flash on the next hit |
| 14.56 | close smile with an RGB-split hit and a light leak |
| 15.67 | the wave, slow motion, then the walk at 2x |
| 17.33 | the walk-off; **CLASS / REPRESENTATIVE** sits on the far wall behind everyone, drifting with the camera at 45 % |
| 19.69 | he turns back and smiles while the camera pushes in 1.85x; aura glow |
| 21.78 | end card on the final downbeat: impact, **THE G.O.A.T.** + CLASS REPRESENTATIVE, then a fade |

### Look

- Real-ESRGAN general v3 4x upscale, supersampled to 1080x1920 (the clarity pass, `tools/enhance.py`).
- Curtain reds tamed, teal-warm grade, bloom, vignette, sharpening, grain.
- 7.2 % letterbox from the drop on.

### Sound (`tools/mix.py`)

- Hook dialogue lifted to sit ~6 dB under the music, with 30 ms fades on every edge.
- The song laid from the drop.
- SFX are short impact attacks only, because the 808 owns the low end:
  - synthesised shutter clicks on every white flash
  - a reverse swell and a glitch into the strobe
  - sub booms on the big hits
  - risers into the filter opening and the end card
  - sparkle on the titles
- The final downbeat is re-struck with a reverb tail.
- Two-pass loudnorm to −14 LUFS / −1 dBTP. There is also a no-music mix.

## Rebuild

```
python3 tools/transcribe.py renders/analysis/audio.wav renders/analysis/transcript.json   # optional
python3 tools/enhance.py renders/src/source.mp4 renders/src/enhanced.mp4                  # ~30 min CPU (bf16)
U2NET_HOME=/root/vfx-models /root/vfx-venv/bin/python tools/mattes.py                     # person mattes
python3 ../aura-edit/tools/analyze_ref.py renders/src/source.mp4 renders/analysis         # camera pan (wall track)
python3 tools/mix.py
python3 tools/composite.py --out renders/cr_aura_video.mp4        # --preview for 540x960
ffmpeg -i renders/cr_aura_video.mp4 -i renders/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k renders/CR_aura.mp4
```

### Models

- **Whisper turbo and Silero VAD:** sherpa-onnx builds from the k2-fsa GitHub releases, in `/root/asr-models`. The usual Whisper and Hugging Face hosts are blocked in this sandbox.
- **Real-ESRGAN v3 weights:** xinntao's GitHub release, in `/root/vfx-models/realesrgan`.

### Fonts

Cinzel and Inter, both under the OFL; the licences are in `assets/fonts/`.
