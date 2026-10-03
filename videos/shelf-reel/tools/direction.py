"""The edit's direction: every camera move and look effect, in OUTPUT seconds.

The compositor renders these; mix_sfx.py reads the same list, so each punch, whip, glitch and
flash gets its sound on the same frame. Times are tied to measured word onsets
(renders/words.json) and to the cuts in edl.py.

Camera (applied to footage and the "behind" layers, which live in the scene):
  shot(t0, t1, push=(s0, s1), c=(cx, cy))     a gentle push-in over the shot, centred on (cx, cy)
  punch(t, amt, c, att, hold, rel)            snap zoom: +amt in `att` s, hold, ease back over `rel` s
  shake(t, amp, decay, freq)                  damped jolt, amp in px
Look:
  flash(t, rgb, a, decay) · chroma(t, px, decay) · glitch(t0, t1, k) · glint(t, x, y, size, dur)
  whip(t, dx) (directional smear across a cut) · leak(t0, t1, k, warm) · red(t0, t1, k) (alarm tint)
  freeze(t0, t1, src_frame) (founder intro: bg desaturated/darkened, person keeps colour + rim)
  vhs(t0, t1) · fade(t0, t1) (to black)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

O = lambda sid: edl.BY_ID[sid]["o"] / edl.FPS          # segment start (output s)
src = edl.out_time                                       # (src_t, seg) -> output s

SHOTS = [
    # t0, t1, push s0 -> s1, zoom centre (full-res px)
    (0.000, O("H2"), (1.00, 1.07), (820, 760)),          # hook: laptop breakdown
    (O("P1a"), O("P1b"), (1.00, 1.10), (660, 1160)),      # alarm (the crash zoom is a punch)
    (O("P1b"), O("P1c"), (1.04, 1.12), (400, 880)),       # asleep
    (O("P1c"), O("P1d"), (1.00, 1.03), (540, 960)),       # sits up (fast)
    (O("P1d"), O("P1e"), (1.00, 1.04), (560, 900)),       # picks up the phone (fast)
    (O("P1e"), O("P2"), (1.00, 1.22), (480, 1100)),       # reads it: slow dread push into the phone
    (O("P2"), O("P3"), (1.00, 1.04), (580, 820)),         # "F... I have an exam in 8 hours"
    (O("P3"), src(22.133, "P3"), (1.06, 1.00), (300, 960)),   # stands up (pull back)
    (src(22.133, "P3"), src(23.533, "P3"), (1.00, 1.05), (470, 960)),   # dials
    (src(23.533, "P3"), O("P4"), (1.00, 1.05), (540, 1000)),            # laptop over-shoulder
    (O("P4"), src(35.333, "P4"), (1.00, 1.06), (620, 840)),             # on the phone
    (src(35.333, "P4"), src(42.433, "P4"), (1.00, 1.06), (540, 880)),   # Ishaan
    (src(42.433, "P4"), src(47.467, "P4"), (1.00, 1.05), (400, 880)),   # friend 2
    (src(47.467, "P4"), O("P5a"), (1.00, 1.05), (680, 840)),            # back to him
    (O("P5a"), O("P5b"), (1.00, 1.05), (820, 760)),       # breakdown
    (O("P5b"), O("P6a"), (1.00, 1.16), (760, 880)),       # head in hand: vertigo push under the storm
    (O("P6a"), O("P6b"), (1.00, 1.05), (520, 800)),       # Jnanottam, top-down
    (O("P6b"), O("P6c"), (1.00, 1.05), (440, 880)),
    (O("P6c"), O("P6c_f"), (1.00, 1.06), (480, 880)),
    (O("P6c_f"), O("P6d"), (1.06, 1.10), (480, 880)),     # freeze: keep drifting in
    (O("P6d"), O("P6d_f"), (1.00, 1.06), (560, 840)),     # Kartik
    (O("P6d_f"), O("P7"), (1.06, 1.10), (560, 840)),
    (O("P7"), src(86.367, "P7"), (1.00, 1.05), (520, 1000)),            # mirror
    (src(86.367, "P7"), src(89.967, "P7"), (1.00, 1.06), (640, 880)),   # can
    (src(89.967, "P7"), O("P8"), (1.00, 1.07), (520, 920)),             # dark nook
    (O("P8"), src(96.033, "P8"), (1.04, 1.00), (500, 1000)),            # "pretty simple": calm pull-back
    (src(96.033, "P8"), src(98.433, "P8"), (1.00, 1.05), (480, 840)),   # chair
    (src(98.433, "P8"), O("P9a"), (1.00, 1.05), (520, 880)),            # bed
    (O("P9a"), O("P9b"), (1.00, 1.08), (520, 880)),       # "...what does SHELF do?"
    (O("P9b"), src(108.433, "P9b"), (1.00, 1.00), (540, 960)),          # STAY TUNED card (designed already)
    (src(108.433, "P9b"), O("END"), (1.00, 1.03), (540, 760)),          # wall reveal
    (O("END"), edl.TOTAL / edl.FPS, (1.03, 1.06), (540, 760)),          # end hold
]

# ---------------- camera hits ----------------
PUNCH = [
    # hook
    (0.25, 0.10, (820, 760), 0.06, 0.25, 0.5),     # "What"
    (0.80, 0.08, (820, 760), 0.05, 0.6, 0.6),      # "f*ck"
    (2.80, 0.05, (820, 760), 0.08, 0.3, 0.4),      # "many groups?"
    # alarm crash zoom into the lock screen
    (O("P1a") + 0.18, 0.32, (660, 1160), 0.22, 1.2, 0.0),
    (O("P1b") + 0.95, 0.07, (400, 880), 0.10, 0.5, 0.0),          # his eyes open
    # panic
    (13.21, 0.15, (580, 820), 0.05, 0.55, 0.45),   # "F*ck"
    (14.80, 0.06, (580, 820), 0.05, 0.4, 0.3),     # "8 hours" (with the clock slam)
    # the call
    (25.01, 0.10, (620, 840), 0.05, 0.35, 0.5),    # "today"
    (26.20, 0.04, (620, 840), 0.06, 0.2, 0.3),     # "notes?"
    (30.22, 0.05, (540, 880), 0.06, 0.4, 0.4),     # "unofficial group"
    (37.46, 0.05, (400, 880), 0.06, 0.4, 0.4),     # "class group"
    (40.40, 0.05, (680, 840), 0.06, 0.4, 0.4),     # "boys group"
    # breakdown
    (44.65, 0.10, (820, 760), 0.05, 0.25, 0.4),    # "What"
    (45.20, 0.10, (820, 760), 0.04, 0.9, 0.7),     # "f*ck"
    (46.36, 0.04, (820, 760), 0.05, 0.3, 0.3),     # "scattered"
    # founders
    (54.88, 0.06, (520, 800), 0.05, 0.3, 0.4),     # "SHELF."
    (57.65, 0.08, (440, 880), 0.10, 0.6, 0.4),     # "y'all": leans at the viewer
    (60.83, 0.06, (480, 880), 0.06, 0.4, 0.5),     # "Jnanottam"
    (66.30, 0.06, (560, 840), 0.06, 0.4, 0.5),     # "Kartik"
    (70.91, 0.05, (520, 1000), 0.05, 0.15, 0.3),   # "everywhere"
    (72.42, 0.05, (520, 1000), 0.05, 0.15, 0.3),   # "everywhere"
    (79.45, 0.06, (640, 880), 0.05, 0.5, 0.4),     # "all of it"
    (82.18, 0.08, (520, 920), 0.05, 0.5, 0.4),     # "complicated?"
    (88.13, 0.12, (480, 840), 0.05, 0.45, 0.5),    # "S.H.E.L.F" — the payoff
    (92.19, 0.04, (520, 880), 0.08, 0.3, 0.4),     # "place"
    (95.25, 0.22, (520, 760), 0.55, 0.3, 0.0),     # "do?" — slow lean into his face, into the card
]
SHAKE = [
    (0.25, 12, 0.30, 17), (0.80, 18, 0.45, 15), (1.96, 7, 0.25, 19),
    (O("P1a") + 0.18, 6, 1.4, 31),                 # the phone buzzing
    (13.21, 22, 0.55, 14), (14.80, 10, 0.35, 16),
    (25.01, 9, 0.30, 16),
    (44.65, 14, 0.35, 16), (45.20, 24, 0.60, 13), (46.36, 9, 0.30, 18), (47.20, 8, 0.30, 18),
    (49.2, 3, 2.5, 7), (50.4, 5, 1.4, 9), (51.1, 8, 0.7, 12),          # anxiety builds under the storm
    (54.88, 7, 0.25, 17), (79.45, 9, 0.35, 16), (82.18, 12, 0.40, 15),
    (88.13, 16, 0.45, 14),
]

# ---------------- looks ----------------
FLASH = [
    (0.80, (1.0, 0.25, 0.2), 0.22, 0.25),
    (O("H2"), (1, 1, 1), 0.55, 0.12),              # tape grabs
    (O("P1a"), (1, 1, 1), 0.45, 0.18),             # rewind lands on the alarm
    (13.21, (1.0, 0.2, 0.15), 0.24, 0.35),         # "F*ck"
    (14.80, (1, 1, 1), 0.25, 0.12),                # clock slam
    (45.20, (1.0, 0.2, 0.15), 0.32, 0.40),         # "f*ck"
    (O("P6a"), (1, 1, 1), 0.95, 0.30),             # chaos -> white -> the founders
    (O("P6c_f"), (1, 1, 1), 0.80, 0.18),           # freeze: shutter flash
    (O("P6d_f"), (1, 1, 1), 0.80, 0.18),
    (O("P8"), (1, 1, 1), 0.35, 0.20),              # hard reset to calm
    (88.13, (0.55, 0.75, 1.0), 0.45, 0.35),        # S.H.E.L.F: blue light burst
]
CHROMA = [(0.80, 9, 0.25), (13.21, 10, 0.3), (44.65, 6, 0.2), (45.20, 14, 0.4), (46.36, 6, 0.25), (82.18, 8, 0.3), (88.13, 6, 0.25)]
GLITCH = [
    (3.36, O("H2"), 0.6),                          # hook freezes into the rewind
    (45.20, 45.36, 0.9), (46.36, 46.46, 0.6),
    (51.45, O("P6a"), 1.0),                        # chaos tears apart before the white flash
    (82.18, 82.34, 0.7),                           # "complicated?"
    (95.70, O("P9b"), 1.0),                        # "...do?" -> STAY TUNED
]
RED = [(13.21, 15.0, 0.10), (44.65, 48.0, 0.07), (48.0, O("P6a"), 0.12)]      # alarm tint, pulsing
GLINT = [  # the sunglasses catch the light on each founder's entrance; the wall logo at the end
    (O("P6a") + 0.42, 482, 822, 120, 0.55),
    (O("P6d") + 0.30, 506, 860, 110, 0.55),
    (107.05, 388, 540, 120, 0.65),                 # the logo on the wall catches the light: final beat
]
WHIP = [  # a smear across these cuts (dx > 0: content moves right)
    (src(22.133, "P3"), 1), (src(35.333, "P4"), -1), (src(42.433, "P4"), 1), (src(47.467, "P4"), -1),
    (src(86.367, "P7"), 1), (src(89.967, "P7"), -1), (src(96.033, "P8"), 1), (src(98.433, "P8"), -1),
    (O("P6b"), 1), (O("P6c"), -1), (O("P6d"), 1),
]
LEAK = [(O("P6a"), O("P6a") + 1.2, 0.30, True), (O("P8"), O("P8") + 1.5, 0.22, False), (88.13, 89.0, 0.35, False)]
FREEZE = [(O("P6c_f"), O("P6d"), 2233), (O("P6d_f"), O("P7"), 2366)]
VHS = [(O("H2"), O("P1a"))]
FADE = [(edl.TOTAL / edl.FPS - 0.6, edl.TOTAL / edl.FPS)]
