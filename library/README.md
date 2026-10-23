# Editing library

Reusable assets for edits, shared by every project under `videos/`.

## Sound effects: `library/sfx/`

The **user's preferred SFX set**, added 2026-10-23. They found the old minimal set boring: use these
generously. Build-ups, bass whooshes, sword impacts and slashes, electric hits, lightning, glitches,
tape-stops, slow-mo swells. The media-use skill's 19 Pixabay files are still fine to use too.

**Contents:** 28 effects (the `nikovax` set), cut from a sound-effect showcase video the user sent.
- Each effect is trimmed from its first sound to the end of its tail.
- Each is peak-normalised to −1 dBFS, at 48 kHz.
- All effects are listed in `sfx/manifest.json` with a category, length, description and `hit_s`.

| category | effects |
| --- | --- |
| riser | build-up-1, build-up-2, build-up-3 |
| whoosh | woosh-1…4, fast-swoosh, slow-woosh, glitchy-woosh, lowpass-woosh, bass-woosh-1, bass-woosh-2 |
| impact | sword-impact, cinematic-electric-hit, wind-impact, lightning-strike |
| slash | sword-slash-1, sword-slash-2 (a four-slash flurry), sword-slash-3 |
| glitch / transition | alien-digital-glitch, beat-slowing (tape stop), slow-motion (slow-mo swell) |
| ui / foley | radio-beep, radio-switch, gun-reload |
| ambience | fire, rain (13–14 s beds) |

**Alignment:** `hit_s` is the moment inside the file that belongs on the cut or beat. `align` says how it was measured:
- `transient`: an impact's sharpest onset.
- `peak`: a whoosh's loudest point.
- `end`: where a riser stops.
- `start`: the first attack.

`tools/sfx.py` places a file so `hit_s` lands on the event:

```python
sys.path.insert(0, "/home/user/Video_Claude/library/tools"); import sfx
sfx.place(buf, "bass-woosh-1", t_drop, gain_db=-10)
sfx.place(buf, "sword-slash-2", t_cut, gain_db=-12, length=0.4)
```

Mixing notes from use:
- **Bass woosh, sword impact:** the bass woosh and the sword impact carry a lot of sub. Over a track with an 808, high-pass them (~70 Hz) or trim them so they don't fight the bass.
- **Fire, rain:** the beds sit around −15 dB relative to the hits, so add gain to the beds rather than raising everything else.

## Why the audio isn't in git, and how to get it back

The repo is public and these files come from a third-party pack, so `*.wav` stays ignored. Only
`manifest.json` and the tools are committed. The container is wiped between some sessions (it was
on 2026-10-23), so the audio lives in a **private backup artifact** that the user owns:

> https://claude.ai/artifact/PQbmuZcLGS5irz7F8AVH9n
> (`sfx/<id>.wav`, 16-bit 48 kHz, sample-exact copies, plus a page to play them)

To restore in a fresh session:

1. Run `python3 library/tools/sfx.py check`. It prints the missing ids and the exact Artifact call.
2. Make the Artifact tool call: `action: read`, `url` the backup above, and `paths` the list it printed, with `out_dir` set to a scratch folder.
3. Run `python3 library/tools/sfx.py restore <that folder>`.

Alternatively, re-run `python3 library/tools/extract_nikovax.py <showcase.mov>` on the original video if the user sends it again.

`tools/build_sfx_page.py` (with `sfx_page_template.html`) rebuilds the backup page from the manifest.
