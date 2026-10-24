"""Every camera move and look in the SHELF CAMPUS reel, on the output timeline (seconds).

Positions marked "glasses" are found per source frame by tools/composite.py (the founders' yellow
sunglasses are the most reliable landmark in every shot), so pushes and punches centre on the eyes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

S = {s["id"]: s for s in edl.SEGMENTS if "id" in s}
o0 = lambda sid: S[sid]["out0"]
o1 = lambda sid: S[sid]["out1"]
D, R, D2 = edl.D, edl.R, edl.D2
FREEZE_HIT = o0("E4f")

# looks: (t0, t1, grade look, wall treatment)
LOOKS = [
    (0.000, o0("A5"), "tense", "police"),
    (o0("A5"), o1("A5"), "freeze", None),
    (o0("B1"), D, "night", None),                 # "I'm" in the hush: natural wall, cool grade
    (D, R, "night", "night"),                     # drop 1: the wall goes deep navy
    (o0("C2"), o1("C3"), "night", "night"),
    (o0("E1"), o1("F2"), "day", "day"),
]

# base camera per segment: (segment, scale at start, scale at end); centred on the glasses
SHOTS = {
    "A1": (1.10, 1.05), "A2": (1.00, 1.04), "A3a": (1.00, 1.045), "A3b": (1.14, 1.18), "A4": (1.00, 1.03),
    "A5": (1.00, 1.05), "B1": (1.00, 1.05), "B1f": (1.05, 1.05), "B2": (1.00, 1.04), "B4": (1.00, 1.05),
    "B5": (1.00, 1.07), "C2": (1.00, 1.05), "C3": (1.00, 1.05), "E1": (1.00, 1.04), "E2": (1.00, 1.04),
    "E3": (1.00, 1.03), "E4": (1.00, 1.06), "E4f": (1.06, 1.06), "F1": (1.00, 1.04), "F2": (1.00, 1.05),
}
# frame 1 slams in: A1 eases 1.10 -> 1.03 over its first 0.35 s, then pushes slowly to 1.05
OPEN_SETTLE = (0.35, 1.03)

# punches: (time, extra scale, attack s, hold s, release s); centred on the glasses
PUNCH = [
    (9.42, 0.12, 0.08, 9.0, 0.0),                # "assignment!" (held into the freeze)
    (D, 0.10, 0.05, 0.10, 0.55),                 # drop 1: JNANOTTAM
    (14.033, 0.09, 0.05, 0.10, 0.50),            # KARTIK
    (28.05, 0.03, 0.06, 0.05, 0.30),             # AI-powered
    (31.08, 0.06, 0.05, 0.25, 0.40),             # WhatsApp
    (o0("E1"), 0.10, 0.0, 0.0, 0.30),            # landing back from the demo: zoomed in, settling out
    (49.30, 0.08, 0.10, 9.0, 0.0),               # "...and your WhatsApp?"
    (FREEZE_HIT, 0.10, 0.06, 9.0, 0.0),          # the bass-hit freeze
    (56.20, 0.06, 0.06, 9.0, 0.0),               # "upgrade"
]

# damped handheld jolts: (time, amplitude px, decay s, frequency Hz)
SHAKE = [
    (0.00, 16, 0.18, 17), (8.49, 12, 0.14, 19), (9.42, 18, 0.20, 18), (3.39, 6, 0.30, 21),
    (D, 22, 0.22, 16), (14.033, 18, 0.20, 17), (20.15, 8, 0.25, 20), (31.08, 8, 0.16, 18),
    (FREEZE_HIT, 20, 0.20, 16), (56.20, 8, 0.18, 18),
]

# flashes: (time, rgb, alpha, decay s)
FLASH = [
    (D, (1, 1, 1), 0.75, 0.08),
    (14.033, (1, 1, 1), 0.50, 0.07),
    (o0("B3"), (0.75, 0.85, 1.0), 0.45, 0.10),
    (o0("C2"), (0.6, 0.75, 1.0), 0.35, 0.10),
    (FREEZE_HIT, (1, 1, 1), 0.70, 0.10),
    (o0("F1"), (0.8, 0.9, 1.0), 0.30, 0.08),
    (56.20, (1, 0.98, 0.92), 0.35, 0.14),
]

# shockwaves (refraction rings) from the glasses: drop 1, KARTIK, the freeze hit
SHOCK = [D, 14.033, FREEZE_HIT]

# chromatic aberration kicks: (time, px, decay s)
CHROMA = [(0.03, 6, 0.08), (8.49, 6, 0.08), (9.42, 10, 0.12), (D, 12, 0.14), (14.033, 9, 0.12),
          (20.63, 8, 0.10), (FREEZE_HIT, 14, 0.16), (o0("F1"), 10, 0.10)]

# digital glitch spans: (t0, t1, strength)
GLITCH = [(2.40, 2.47, 0.5), (20.63, 20.80, 0.35), (R - 0.17, R, 0.6), (FREEZE_HIT, FREEZE_HIT + 0.12, 0.8),
          (o0("F1") - 0.07, o0("F1") + 0.07, 0.7)]

# power-down flicker before the cut to black: (t0, t1)
FLICKER = [(R - 0.17, R)]

# zoom-blur bursts: (time, amount)
ZBLUR = [(D, 0.8), (14.033, 0.5), (o0("C2"), 0.5), (o0("B4"), 0.4), (o0("E1"), 0.6), (FREEZE_HIT, 0.6)]

# sunglasses glints: (time, size px, duration s)
GLINT = [(D + 0.05, 150, 0.45), (14.033 + 0.05, 140, 0.42), (31.10, 120, 0.40), (56.22, 130, 0.45)]

# the bleep's censor bar (output span), placed relative to the glasses of that frame
CENSOR = (edl.out_of_src(edl.BLEEP_SRC[0], "A2") - 0.02, edl.out_of_src(edl.BLEEP_SRC[1], "A2") + 0.02)
MOUTH_FROM_GLASSES = (-22, 124)

# segments with no captions (names, kinetic words or full-frame graphics carry the words)
NO_CAPTIONS = {"B1", "B1f", "B2", "B3", "C0", "C2", "D", "F1", "F3", "A5", "E4f"}
