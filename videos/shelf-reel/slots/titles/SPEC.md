# SPEC — titles (giant words behind the founders + freeze-frame name cards)

"behind" layers are composited UNDER a person cut-out: the words sit on the wall/bed behind the
speaker and his head/body occludes them. Design them to be partly hidden — that's the effect.
Use `.giant` from `design/shelf.css` (Sora 800, silver gradient, blue glow) as the base look.
Registry starting points: `mk-emphasis-type` (oversized word behind subject),
`caption-parallax-layers`, `freeze-frame-dressing` (for the name cards — retheme it to the
S.H.E.L.F look: silver rules, Sora, blue glow; no paper/tape), `rgb-glitch-text`.

Measure placement from the reference frames (renders/ref/, output time in the name).

| output dir | window (output s) | frames | layer | cue |
|---|---|---|---|---|
| `shelf_behind` | 54.100 → 55.533 | 43 | behind | "about SHELF." — "SHELF"@54.88 |
| `jnanottam_behind` | 60.600 → 64.967 | 131 | behind | "I am Jnanottam"@60.83, freeze 63.50-64.967 |
| `kartik_behind` | 66.100 → 70.167 | 122 | behind | "and I'm Kartik"@66.30, freeze 68.733-70.167 |
| `simple_behind` | 85.450 → 86.667 | 37 | behind | "is pretty simple"@85.75 |
| `shelf2_behind` | 87.950 → 89.067 | 34 | behind | "so we built S.H.E.L.F"@88.13 |
| `namecard_j` | 63.400 → 64.967 | 47 | front | freeze card for Jnanottam |
| `namecard_k` | 68.633 → 70.167 | 46 | front | freeze card for Kartik |

## Each beat
- **shelf_behind** — Jnanottam lies on his back, top-down shot, sunglasses (out_054.50). He says
  "clearly he hasn't heard about SHELF." "SHELF" lands at 54.88: letters slam in with a short
  stagger (scale ~1.2→1, blur→0), one light sweep. Span the frame width around his head/chest so
  his head covers part of the word. Holds to the cut.
- **jnanottam_behind** — lying on his front on a bed, hands clasped, wall behind
  (out_061.00; the freeze frame is out_064.00). "JNANOTTAM" is long: one line ~190-220 px that
  may bleed off both edges with a slow drift, or two stacked lines. Rise-in on 60.83; slow drift;
  at the freeze (63.50) flash brighter (glow pulse) and hold.
- **kartik_behind** — standing against a black tile grid (out_066.20; freeze out_069.00). "KARTIK"
  big behind his head/shoulders, reveal on 66.30, flash at the freeze (68.733), hold.
- **simple_behind** — Kartik in a bathroom, calm (out_085.50). "SIMPLE." appears on 85.75:
  the calm beat after chaos — clean fade/scale, maybe a thin underline drawing. No glitch.
- **shelf2_behind** — Jnanottam in a desk chair (out_088.20). The product name lands at 88.13:
  "S.H.E.L.F" big, with `design/shelf-mark.png` above or beside it, a light burst behind the
  letters. This is the payoff: biggest, cleanest hit in the reel.
- **namecard_j / namecard_k** (front) — during each freeze the compositor darkens and
  desaturates the background and keeps the founder in full colour. Add the role line under (or
  beside) the giant name: "CO-FOUNDER" (Sora 700, letterspaced) + "S.H.E.L.F" small, with thin
  silver rules/brackets; snap in at the freeze start (63.50 / 68.733) with a quick slide and
  hold. Keep clear of the caption band (y 1290-1460) and of the face. Match the giant name's
  layout so they read as one lockup.
