# SPEC: the wall titles behind HK Vinay (3 behind slots + a shared skyline)

Read `slots/BRIEF.md` first. All three slots below are **behind** layers: transparent, composited on the
re-lit (dim midnight navy) wall under his cut-out. Design in source coordinates (where he is: see the brief).
The compositor zooms the camera about his face (805, 960). The visible window is listed per slot: content
outside it is off-screen at that moment.

**You also make the reel's Singapore skyline**: a refined single-weight **gold line-art** silhouette drawn as
SVG paths (strokes, round caps). Make it recognisably Singapore and elegant, never cartoonish:
- Marina Bay Sands (three towers and the SkyPark "ship" across the top);
- the ArtScience Museum lotus;
- the Singapore Flyer wheel;
- a few slim CBD towers;
- the Supertrees.
Draw it with `stroke-dasharray` so it can **draw itself on**. Use it in `hook_behind` and `finale_behind`
(copy the same SVG into both slots).

## 1. `hook_behind` (behind) window 0.000-6.100 = 183 frames
Camera: 1.42x on his face at 0.0 (visible about x 320-1080, y 285-1635), easing out to 1.12x by 3.1 (visible
about x 115-1080, y 105-1815), then a slow push to 1.18x by 6.1.
- beats: 0.00 0.50* 1.00 1.50 2.00 2.50* 3.00 3.50 4.00 4.50* 5.00 5.50 6.00
- words: Big@0.41 ambitions.@0.89 deserve@2.03 bigger@2.59 horizons.@3.07 And@3.71 we're@3.95 taking@4.35
  ours@4.75 global.@5.31

Direction:
- **0.00-0.50:** a thin gold **horizon line** ignites from a bright point near his head, at about y 760
  (just above it), and races out left and right across the wall with a light flare at the head. It is the
  first thing the eye catches.
- **2.03 ("deserve") to 3.07 ("horizons"):**
  - the Singapore skyline draws itself up out of the horizon line, rising to about y 430, spread across the
    upper wall, its base on the line;
  - at 3.07 the drawing completes with a glint, and a warm gold **sunrise glow** swells behind the
    skyline;
  - **A NEW HORIZON** (Cormorant 600, ivory, ~110 px, wide-ish tracking; or italic "a new" over caps
    "HORIZON"; your call) rises out of a mask at about y 300-420, landing on 3.00/3.07.
- **3.71-5.31 ("And we're taking ours global"):**
  - the skyline and title ease back (dim, drift up);
  - a **gold wireframe globe** (latitude/longitude ellipses, ~300 px radius, centre about (520, 560))
    spins up behind his head;
  - on 5.31 ("global") it completes with a pulse ring and a soft royal-blue rim glow (the one blue
    touch).
- Hold to 6.10 (the cut to the next shot).

## 2. `name_behind` (behind) window 6.100-12.500 = 192 frames
Camera: an "aura" pull-out from 1.45x at 6.10 to 1.00x at 7.40 (fast, expo-out), so the whole frame is visible
from 7.4. A hold until 8.5, then a slow push-in to 1.22x by 12.5 (visible about x 195-1080, y 175-1745).
- beats: 6.50* 7.00 7.50 8.00 8.50* 9.00 9.50 10.00 10.50* 11.00 11.50 12.00
- words: I@6.32 am@6.48 HK@6.64 Vinay,@7.12 managing@7.68 partner@8.08 at@8.40 TaxWise.@8.56 And@9.49
  I'm@9.81 excited@10.13 to@10.61 announce@10.77 our@11.33 expansion@11.65 into@12.37
- **The music drops out at 8.50, on "TaxWise".** It is a held bass drone until the drop at 12.50 on
  "Singapore" (the next slot is a full-screen slam).

Direction:
- **6.64-7.40:** his name, huge, behind him: **HK VINAY** (Cormorant 600 ivory, ~220-260 px; "HK" can be
  gold).
  - It arrives as the camera pulls out (it should feel like the pull-out reveals it), letters rising out
    of a mask, staggered.
  - Lay it out so part of it tucks behind his head (his head is x 700-910 from y 800 down): for example
    "HK" on a line at y ~420-620 and "VINAY" at y ~620-860, left-aligned at x ~80.
- **7.68 ("managing"):** **MANAGING PARTNER** (Montserrat 600, tracked caps, ~34 px) slides in beside or under
  the name with a gold hairline drawing out.
- **8.56 ("TaxWise"; the music cuts out):** the TW mark draws itself on in gold (stroke, then fill), ~150 px
  wide, beside **TAXWISE CONSULTANTS** (the wordmark). It completes by ~9.2 with a shine.
- **9.49-12.37 (the build):**
  - everything dims slowly to about 40%;
  - a single gold line starts to grow across the wall at about y 300, like a fuse or a loading line. It
    reaches the far edge exactly at 12.50;
  - on "expansion" (11.65) the word **EXPANSION** appears as huge outlined (stroke-only, gold) capitals
    across the upper wall;
  - on "into" (12.37) the outline starts flooding with gold, fully filled by 12.50;
  - the slot ends at 12.50: the compositor cuts to white-gold on the drop.

## 3. `finale_behind` (behind) window 42.370-48.250 = 176 frames
Camera: 1.05x at 42.37, easing into a push to 1.30x by 48.25, accelerating over the last second (at 1.30x the
visible window is about x 390-1080, y 220-1700).
- beats: 42.50* 43.00 43.50 44.00 44.50* 45.00 45.50 46.00 46.50* 47.00 47.50 48.00
- words: TaxWise,@43.07 now@44.27 in@44.43 Singapore,@44.59 and@45.39 trust@45.63 us,@45.95 this@46.43
  is@46.59 just@46.75 the@46.99 beginning.@47.15

Direction:
- **43.07 ("TaxWise"):** the TW mark assembles large behind him (T drops, W rises, diamond pops; ~260 px
  wide, upper wall around x 380-640, y 330-620), with a shine on 43.50.
- **44.27-44.59 ("now in Singapore"):**
  - the skyline from the hook draws on again along a horizon line at about y 760;
  - a gold location pin drops onto it on 44.59 with a pulse ring;
  - **NOW IN SINGAPORE** (Montserrat 700 tracked caps ~44 px, gold, or Cormorant): your layout, above the
    mark or below the skyline line, inside the visible window.
- **45.63-47.15 ("trust us, this is just the beginning"):**
  - the sunrise glow behind the skyline grows steadily brighter and warmer;
  - by 48.0-48.25 the whole upper wall blooms to a bright gold light (alpha ~0.9 in the centre). The
    compositor uses that bloom to cut to the end card at 48.25.

## Report
Per slot: frame count and the cue list (output times), as in the brief.
