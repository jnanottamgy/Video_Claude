# SPEC: India to Singapore (`globe`, full)

Read `slots/BRIEF.md` first. One continuous full-screen scene: a premium 3D globe, India to Singapore, while HK
Vinay speaks over it.

`globe` (full) window 25.470-35.570 = 303 frames
- beats: 25.50 26.00 26.50* 27.00 27.50 28.00 28.50* 29.00 29.50 30.00 30.50* 31.00 31.50 32.00 32.50* 33.00
  33.50 34.00 34.50* 35.00 35.50
- words: From@25.60 supporting@26.00 businesses@26.56 in@27.28 India@27.52 to@28.16 helping@28.40 them@28.88
  navigate@29.12 Singapore's@29.92 financial@30.72 landscape.@31.20 We@31.89 are@32.21 building@32.37
  stronger@32.77 connections.@33.25 Across@33.74 borders.@34.38
- Music: the new lead melody has just come in (24.50), so it's soaring and emotional. Every downbeat is a
  good place for a camera move to land.

## Tools and data (copy into your slot)
`slots/_shared/geo/` has:
- `d3-array.min.js` and `d3-geo.min.js` (load d3-array first);
- `topojson-client.min.js`;
- world-atlas `land-50m.json` and `countries-50m.json` (Natural Earth);
- `countries-110m.json`, if you prefer lighter shapes.

Load the JSON with a synchronous XHR or inline it into a `<script>` as a JS object: no network.

Render the globe with **d3.geoOrthographic** into an SVG or a `<canvas>`.
- Every frame is drawn from the timeline only: one tween on a proxy object with `onUpdate` that sets
  `projection.rotate([...])` and `.scale(...)` from the proxy's values and redraws.
- No requestAnimationFrame, no randomness.
- Keep it fast: precompute the land dots once.

## Look
- The sphere: deep navy ocean with a subtle inner gradient, a thin **royal-blue atmosphere rim** glow (the
  one blue touch) and a soft gold specular highlight.
- Land as a **fine dot matrix** (halftone dots on a lat/long grid, ~3-4 px, gold at ~70% opacity, brighter
  near the lit side) or as solid navy-600 with fine gold coastlines. Your call; the dot matrix looks more
  premium.
- Pins: gold teardrops or dots with pulse rings. Labels: Montserrat 700 tracked caps, ~28-34 px, ivory on
  a small glass pill.
- Arcs: great-circle arcs (`d3.geoInterpolate`), lifted above the surface for height, with a gold
  comet-head and a fading tail. Draw the visible (front-hemisphere) part only.
- Cities (longitude, latitude):
  - Bangalore (77.59, 12.97);
  - Chennai (80.27, 13.08);
  - Singapore (103.82, 1.35).

## Direction
- **25.47 (match cut):** the scene **starts as a gold wireframe sphere centred at (540, 900), radius 400 px**
  (latitude ellipses and meridians, gold/ivory ~2 px strokes, on the navy ground). The previous scene ends on
  exactly that. Over 25.47-26.20 the sphere fills with the Earth, the wireframe fading into the graticule.
- **25.60-27.52 ("From supporting businesses in India"):**
  - the globe spins (eased, from around the Atlantic) and settles on **India** right on 27.52, zooming
    from radius 400 to ~560;
  - on 27.52 the **BANGALORE** and **CHENNAI** pins pop (staggered 0.12 s), with labels.
  - India's outline glows gold for a moment.
- **28.16-29.92 ("to helping them navigate Singapore's"):**
  - the globe rotates east so both India and Singapore are in view;
  - a gold **arc** launches from the India pins (28.40) and travels to **Singapore**, its comet-head
    arriving exactly on **29.92**;
  - there, a big pulse ring and a larger gold pin appear, with a label **SINGAPORE** and a small **NEW
    OFFICE** tag under it.
- **30.72-31.60 ("financial landscape"):** a slow, confident push toward Singapore, with fine particles of
  light rising off the arc.
- **31.89-33.25 ("we are building stronger connections"):**
  - more arcs fire between Bangalore/Chennai and Singapore in both directions (3-5 arcs, different heights,
    staggered on the beats 32.0, 32.5, 33.0), weaving a bridge of light;
  - on 33.25 they all glow at once.
- **33.74-34.38 ("across borders"):** the camera eases back, and the titles land.
  - **INDIA × SINGAPORE** at about y 300-420: Cormorant 600 ivory ~110 px, with the × in gold. Land it
    on 33.74.
  - **CROSS-BORDER FINANCE** under it: Montserrat 600 tracked caps, gold, ~36 px. Land it on 34.38.
  - **TAX · COMPLIANCE · ADVISORY** at about y 1440: Montserrat 500 tracked, ivory-dim, ~28 px. Land it on
    34.60.
- **35.20-35.57:** a bright gold pulse expands from Singapore's pin to fill the frame by 35.50 (alpha up
  to ~0.85). The compositor cuts back to HK Vinay through it.

## Report
Frame count and the cue list (output times), as in the brief.
