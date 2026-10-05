"""The music map: which part of the song plays under each stretch of the reel, and its beat grid.

The song (renders/song.mp3, Travis Scott x Vizion "My Eyes", 147.0 BPM, half-time feel: kick on 1,
snare on 3) has a free-time ambient intro (0-56 s), a groove that fades in (56-64), a hi-hat build
(64-68.9), a one-bar gap with the bass out (68.92-70.55), 808 pickups (70.96, 71.57) and DROP 1 at
72.187. A breakdown with no hats runs 150.55-162.8, then 0.76 s of dead silence, then DROP 2 (the
busier, more hyped one) at 163.613. Grid measured from the audio: T = 0.40815 s, phase 0.3528 s,
bar lines on beat index % 4 == 0.

The reel follows the song's arc instead of the song being chopped under the picture:
  hook       the pre-drop bar, so drop 1 slams on "f*ck"
  rewind     tape-rewind of the hook (picture and sound)
  story      from the ambient intro; the bass drops out as he puts his head in his hand and
             drop 1 lands on the white flash into the founders
  the turn   "but the problem we're solving is pretty simple": cut to the breakdown, so the
             0.76 s silence falls on "so we built" and drop 2 hits on "S.H.E.L.F"
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

T = 0.40815                    # beat (s)
PHASE = 0.3528                 # first beat (song s)
DROP1, DROP2 = 72.187, 163.613
GAP1, SILENCE2 = 68.922, 162.85

O = lambda sid: edl.BY_ID[sid]["o"] / edl.FPS
SHELF_WORD = O("P8") + 4.797   # "S.H.E.L.F" onset, measured: 4.797 s into P8

# (output start, output end, song time at output start); the rewind is built from the hook
MAP = [
    ("hook", 0.0, O("H2"), DROP1 - 0.797),                         # drop 1 on "f*ck" (0.797)
    ("rewind", O("H2"), O("P1a"), None),
    ("story", O("P1a"), O("P8"), DROP1 - O("P6a") + O("P1a")),     # drop 1 on the founders' white flash
    ("drop2", O("P8"), edl.TOTAL / edl.FPS, DROP2 - SHELF_WORD + O("P8")),
]


def song_time(t):
    """Song position (s) under output time t, or None during the rewind."""
    for name, a, b, s0 in MAP:
        if a <= t < b:
            return None if s0 is None else s0 + (t - a)
    return None


def grid(t0, t1, sub=1):
    """Output times of song beats (sub=2: 8ths, 4: 16ths) inside [t0, t1), with their beat index
    (fractional for subdivisions). Bars: index % 4 == 0."""
    out = []
    for name, a, b, s0 in MAP:
        if s0 is None:
            continue
        lo, hi = max(a, t0), min(b, t1)
        if lo >= hi:
            continue
        s_lo, s_hi = s0 + lo - a, s0 + hi - a
        k0 = int(np.ceil((s_lo - PHASE) / (T / sub) - 1e-9))
        k = k0
        while PHASE + k * T / sub < s_hi - 1e-9:
            st = PHASE + k * T / sub
            out.append((a + st - s0, k / sub))
            k += 1
    return out


if __name__ == "__main__":
    for name, a, b, s0 in MAP:
        print(f"{name:7s} out {a:7.3f}-{b:7.3f}  " + (f"song {s0:7.3f}-{s0 + b - a:7.3f}" if s0 is not None else "(rewind)"))
    for label, s in [("drop 1 (hook)", DROP1), ("gap 1", GAP1), ("drop 1", DROP1), ("silence 2", SILENCE2), ("drop 2", DROP2)]:
        hits = [round(a + s - s0, 3) for n, a, b, s0 in MAP if s0 is not None and a <= a + s - s0 < b]
        print(f"{label:14s} song {s:7.3f} -> out {hits}")
