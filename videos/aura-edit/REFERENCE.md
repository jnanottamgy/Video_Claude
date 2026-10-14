# Aura edit: analysis of the reference reel

The reference is a 25.5 s Instagram travel reel (Yosemite, three friends). The user wants its style
applied to their own footage. The reference file itself stays out of git (`renders/ref/`, gitignored).
None of its media is committed.

Re-run the measurements:

```
python3 tools/analyze_ref.py renders/ref/reference.mp4 renders/analysis   # per-frame + audio metrics
python3 tools/contact.py renders/ref/reference.mp4 out.png "184-244:2" --beats renders/analysis/audio.json
python3 tools/syncmap.py renders/analysis out.png 8 17                       # spectrogram + events
python3 tools/board.py renders/ref/reference.mp4 renders/analysis/effects_board.jpg
```

## Format

| | |
| --- | --- |
| Frame | 720×1280 (IG download), 24 fps, 608 frames |
| Picture | 16:9 (720×406) **letterboxed** in the 9:16 frame: 437 px black top and bottom, every frame |
| Grade | warm golden-hour mids and highs (Lab b +10…+18) and teal-green landscapes (a −8…−12). Blacks are lifted (p1 ≈ 12–25), highlights roll off (p99 ≈ 210–230) and saturation is moderate. There is no grain overlay and no vignette. One B&W insert. |
| Footage | about half the shots are **stills** or locked-off tripod frames (zero motion). Energy comes from cuts and flashes, not from camera moves. |

## The music and the sync system

- **Song character:** phonk/trap at about **95 BPM**: bar 2.52 s, beat 0.63 s, 8th 0.315 s, 16th 0.158 s. It has a heavy sustained 808.
  - In every bar, the 808 plays for about 1.7 s, **drops out for the last ~0.85 s**, then slides back in on the next downbeat.
  - The 808 is out at 1.67–2.37, 4.19–5.05, 6.73–7.58, 9.25–10.10, 11.78–12.63, 14.30–15.15, 16.83–17.68, 19.35–20.21 and 21.88–22.73.
  - librosa's beat tracker reports 128 BPM. It locks onto the dotted-8th syncopation (0.47 s), so ignore it and use the 808 grid.
- **Rule 1: one scene per bar.** Every major scene change lands on the 808 re-entry (the bar downbeat):
  - 2.58: hand wipe lands
  - 5.0: echo dissolve
  - 7.67: double exposure
  - 10.17: the drop
  - 12.71, 15.21, 17.75, 20.21
- **Rule 2: tricks live in the 808 gap.** The last ~0.85 s of a bar holds a fill that builds tension, and the next downbeat resolves it:
  - white silhouette flashes (6.38 / 6.67 / 6.96, on 8ths)
  - threshold frames (9.88)
  - squad stop-motion (13.92–15.0)
  - block reveal (18.96–19.92)
- **Rule 3: subdivisions.**
  - 8th notes: jump cuts and person flashes.
  - 16ths and 32nds: region flashes (15.63 / 15.79, then 18.21 / 18.29 / 18.38 two frames apart).
  - The double exposure's inner clips swap every 6 frames (4/s), free-running. That works because the music is muffled there and has no hats to clash with.
- **Rule 4: filter breakdown.**
  - The whole double exposure bar (7.6–10.1) is **low-passed**: nothing above ~2 kHz, against ~16 kHz elsewhere.
  - The filter sweeps open over the last ~0.5 s, and the drop at 10.15 lands on the cut to the boardwalk.
  - Whether the song does this or the editor automated it, we reproduce it on the music track.
- **Cut placement:** cuts sit 0–2 frames *before* the hit they belong to. The first full shot appears at 0.458, ahead of the 0.509 hit.
- **Ending:** the logo arrives on beat 2 of bar 9 (21.0). Picture and music then fade to black together over 24.2–25.2.

## Sound effects

There are very few. The song carries the edit. Sounds the editor added show up **above the song's 16 kHz codec ceiling**:

- **Camera-shutter clicks** at 15.43, 15.60 and 15.77. These are three 25–40 ms comb-filtered clicks reaching 20 kHz, on the waterfall flashes, about one frame ahead of the picture.
- **Short ticks** under the white silhouette flashes, at 6.32–6.45, 6.60–6.74 and 6.97–7.06.
- A probable **hit/snap at the drop** (10.11–10.16).

Everything else (claps, hats, slides) is the song, and the visuals are cut to it.

## Shot by shot (frame = round(t × 24))

| t (s) | frames | What happens | How |
| --- | --- | --- | --- |
| 0.00–0.42 | 0–10 | **Cutout strobe intro:** the first shot's subject in parts (shoulders, head, ear/nose, sunglasses outline). Each part shows as a solid white matte for 1 frame, then as a red-tinted cutout for 1 frame, on black. | person/part mattes, 1-frame holds |
| 0.458 | 11 | Hard cut to the full selfie shot (river, sunglasses), ahead of the 0.509 hit | |
| 2.17–2.58 | 52–62 | **Hand-over-lens wipe:** his hand sweeps across the lens. The next shot (backlit silhouette in haze) is revealed behind the moving hand, completing on the downbeat. | in-camera hand + rotoscoped hand layer over shot B |
| 2.58–4.63 | 62–111 | Silhouette shot, static, with a slow ~2° roll and drift | keyframed rotate/position |
| 4.67–5.04 | 112–121 | **Echo + match dissolve:** he turns with ghost trails (frame echo), dissolving warm→teal into the next guy standing in the same spot. Two frames hold (121–122), then a 4-frame shake (123–126). | echo/time-trail + cross-dissolve + shake keys |
| 6.38, 6.67, 6.96 | 153, 160, 167 | **White silhouette flashes:** a locked shot where people jump in one at a time. Each new person/pose flashes as a solid cream-white silhouette for 1 frame (with a tick SFX). | person matte filled #F7F7EE |
| 7.67–10.13 | 184–243 | **Double exposure:** a head-and-shoulders profile photo as a silhouette on white, filled with landscape clips that swap every 6 frames (184, 190, 196 … 237). The bottom edge is feathered and brushy. It pushes in ~1.45× over the bar while the music is low-passed. Frames 237–243 are a **threshold** version (solid black silhouette on white). | matte + screen/multiply blend, scale keys |
| 10.17 | 244 | **The drop:** cut to the boardwalk walk-away shot | |
| 10.83, 11.13, 11.46 | 260, 267, 275 | **Squad assembles 1:** a pose shot where the 2nd and 3rd friend appear (jump cuts on 8ths) | stills/locked shot |
| 12.71 | 305 | Cut to a wide valley with a fence (still) | |
| 13.25–13.71 | 318–329 | **"CRAZY"** in orange (#FFA500-ish) high-contrast serif caps (Times/Baskerville-bold style), centred. Hard pop in and out, 12 frames, on a vocal hit. | text layer |
| 13.92, 14.25, 14.50, 15.0 | 334, 342, 348, 360 | **Squad assembles 2:** tripod stop-motion, friends appear one by one on the fence | locked-off stills |
| 15.21 | 365 | Cut to a waterfall (still) | |
| 15.63, 15.79 | 375, 379 | **White mask flashes:** the background region, then the falls, flash pure white for 1 frame each, with shutter-click SFX | region masks |
| 16.46–16.79 | 395–402 | **Orbit spin:** low angle, pink sky, the camera spins around him (~40°/s, motion-blurred trees) | in-camera |
| 16.79 | 403 | Cut: he gazes at the mountains, slow push-in | scale keys |
| 17.13 | 411 | Cut: beanie + fog, a head turn to camera | |
| 17.75 | 426 | Cut: lake/forest still | |
| 18.21, 18.29, 18.38 | 437, 439, 441 | **White mask flashes** on the sky, then the water, then the peak, two frames apart | region masks |
| 18.96–19.92 | 455–478 | **Block reveal:** a 1-px line becomes a horizontal bar, a vertical bar crosses it, then stepped blocks expand. Inside is a B&W high-contrast silhouette shot, which is full by 19.92. | animated rectangle masks |
| 20.21 | 485 | Cut on the downbeat to the final wide shot: he walks left→right in front of Half Dome at sunset | |
| 21.0–22.0 | 504–528 | **Logo walk-by:** a white monogram sits *behind* him. His trailing edge wipes it on as he walks past, then it holds. | person matte over the logo layer, wipe tracked to his back |
| 24.2–25.2 | 580–604 | Fade to black (picture and music) | |

## Recreating it with the user's footage

All of these effects can be built here:
- Person mattes come from `rembg u2net_human_seg` in `/root/vfx-venv`, used by `../shelf-reel/tools/mattes.py`.
- Region masks for sky and water come from colour/luma keys.
- The compositing pipeline is the one in `../shelf-reel/tools/composite.py`.
- The music grid comes from the 808 / onset analysis above, run on whatever song we use.

A few moves need specific shots:

1. A clear close-up of the main person, for the **cutout intro**.
2. A **hand covering the lens** at the end of one clip, for the hand wipe. Without it we use a whip or blur wipe.
3. A **backlit or silhouette** shot against bright sky.
4. Two shots with the person **in the same spot**, for the echo match dissolve.
5. A **locked-off (tripod) shot where friends walk in one at a time**. This one shot covers both the silhouette flashes and the squad-assembles stop-motion.
6. A **profile photo against bright sky**, plus 6–10 short scenic clips, for the double exposure.
7. Scenic shots with clear sky, water or peaks, for the white mask flashes.
8. A spin/orbit selfie.
9. A wide shot of the person **walking across the frame**, for the logo or name walk-by, plus the logo or name text.
10. The song. Same song or another: we re-derive bars and the 808 gaps from it.

**Format:** the reference is horizontal footage letterboxed into vertical. We can match that (cinematic) or fill the vertical frame. Full-screen vertical uses more of the phone screen, and the letterbox is the look.
