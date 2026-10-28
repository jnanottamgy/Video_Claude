"""Jayashree D Jain: event reel. Every shot of the output, on the song's beat grid.

The music is "BLEND OF RAAG" (sagarswarup x SunixThakor), played from song 84.134 s to 149.5 s
(65.37 s): the 88 BPM groove (no vocals, so her singing shots never fight a different voice), a 15.7 s
"breath" where the drums drop out (song 114.8-130.5), the second drop's swoop at song 130.5, the
climax, and the rhythm stopping at song 145.3 into a soft pad for the end card.

Reel time t = song time - SONG_IN; reel beat k sits at k * BEAT.
  python3 tools/edl.py     # print the shot list
"""
import os

FPS = 30
W, H = 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONG = os.path.join(ROOT, "renders/src/song_blend_of_raag.mp3")
SONG_IN = 84.134                 # a downbeat of the groove (beat grid: 73.225 + k * 0.6818)
BEAT = 0.6818                    # 88.0 BPM
DURATION = 149.5 - SONG_IN       # 65.366 s
TOTAL = int(round(DURATION * FPS))


def b(k):
    """Reel time of beat k."""
    return k * BEAT


BREATH = b(45)                   # the drums drop out (song 114.815)
DROP2 = b(68)                    # the swoop and the drums back (song 130.496)
STOP = b(90)                     # the rhythm has stopped: end card (song 145.496)

# shots: t = start (reel s), clip, src = source in-point (s), speed (< 1 = optical-flow slow motion),
#   x = transition INTO this shot: cut | flash | dissolve | whip | drop,
#   z = (zoom at start, at end) about c = (x, y) normalised (a push-in by default), rays = god rays from
#   (x, y, strength), look = grade (gold | candle), hires = decode the 4K original (heavy crops)
SHOTS = [
    # ---- GROOVE A: the world of the event, cut on the tabla ----
    dict(t=b(0), clip="3397", src=1.90, x="cut", z=(1.0, 1.10), c=(0.38, 0.56), note="HOOK: her mid-phrase, hand rising"),
    dict(t=b(4), clip="3399", src=1.50, x="flash", z=(1.12, 1.0), c=(0.5, 0.35), rays=(0.5, 0.04, 0.35), note="the hall: scale"),
    dict(t=b(6), clip="3387", src=0.80, x="cut", z=(1.0, 1.06), rays=(0.5, -0.05, 0.22), note="Tirthankaras under golden umbrellas"),
    dict(t=b(8), clip="3376", src=3.40, x="whip", z=(1.0, 1.08), c=(0.42, 0.62), rays=(0.12, 0.15, 0.30), note="her profile, arched windows"),
    dict(t=b(12), clip="3385", src=0.60, x="cut", c=(0.5, 0.55), note="dholak"),
    dict(t=b(14), clip="3372", src=1.20, x="cut", note="keys"),
    dict(t=b(16), clip="3449", src=0.80, x="flash", z=(1.0, 1.10), c=(0.28, 0.60), rays=(0.5, 0.30, 0.35), note="her in the chandelier hall"),
    dict(t=b(20), clip="3393", src=2.60, x="cut", rays=(0.5, 0.08, 0.35), note="aarti lamps"),
    dict(t=b(22), clip="3382", src=0.40, x="cut", note="offerings"),
    dict(t=b(24), clip="3373", src=2.20, x="whip", z=(1.0, 1.10), c=(0.5, 0.72), note="her, the crowd on the screen behind"),
    dict(t=b(28), clip="3388", src=0.80, x="cut", note="saffron and yellow sarees, puja"),
    dict(t=b(30), clip="3384", src=1.60, x="cut", note="sadhvis in white"),
    dict(t=b(32), clip="3371", src=1.00, x="flash", z=(1.05, 1.16), c=(0.5, 0.78), note="her with the musicians, the logo on screen"),
    dict(t=b(36), clip="3395", src=0.40, x="cut", rays=(0.5, 0.0, 0.25), note="the stage of idols"),
    dict(t=b(38), clip="3394", src=1.20, x="cut", z=(1.07, 1.0), note="rows of devotees with their plates"),
    dict(t=b(40), clip="3443", src=0.20, x="whip", z=(1.0, 1.12), c=(0.55, 0.80), note="her at the mic, the hall on screen"),
    # ---- BREATH: the drums drop out, time slows ----
    dict(t=BREATH, clip="3407", src=0.15, speed=0.5, x="dissolve", z=(1.04, 1.12), c=(0.48, 0.5), look="candle",
         note="her warm close-up: it's a prayer"),
    dict(t=34.55, clip="3393", src=4.00, speed=0.55, x="dissolve", z=(1.05, 1.12), c=(0.6, 0.6), look="candle",
         rays=(0.5, 0.08, 0.5), note="aarti flames, slow"),
    dict(t=37.30, clip="3389", src=0.60, speed=0.5, x="dissolve", z=(1.80, 1.90), c=(0.70, 0.72), look="candle",
         hires=True, note="folded hands holding a diya"),
    dict(t=39.90, clip="3387", src=2.20, speed=0.6, x="dissolve", z=(1.0, 1.08), look="candle", rays=(0.5, -0.1, 0.5),
         note="the idols, light rays: EVENT TITLE"),
    dict(t=43.05, clip="3391", src=1.00, speed=0.6, x="dissolve", z=(1.0, 1.18), look="candle", rays=(0.5, 0.0, 0.4),
         ramp=True, note="hands raised, ramping into the drop"),
    # ---- DROP 2: the climax ----
    dict(t=DROP2, clip="3403", src=1.00, x="drop", z=(1.18, 1.24), c=(0.5, 0.74), note="the hall lifts its hands"),
    dict(t=b(70), clip="3397", src=0.30, x="whip", c=(0.4, 0.55), note="her, singing out"),
    dict(t=b(72), clip="3405", src=2.00, x="cut", note="the dance"),
    dict(t=b(74), clip="3408", src=0.80, x="cut", note="dholak"),
    dict(t=b(76), clip="3412", src=4.30, x="flash", c=(0.68, 0.70), note="the chief guest at the podium"),
    dict(t=b(78), clip="3405", src=9.20, x="whip", note="the dance, closer"),
    dict(t=b(80), clip="3379", src=0.30, x="cut", c=(0.45, 0.6), note="her profile"),
    dict(t=b(82), clip="3456", src=0.40, x="cut", note="a dignitary garlanded, on the big screen"),
    dict(t=b(84), clip="3402", src=1.60, x="whip", note="the crowd and the cameras"),
    dict(t=b(86), clip="3445", src=1.20, x="cut", note="dholak, the guru on screen"),
    dict(t=b(88), clip="3401", src=0.90, x="cut", note="the whole hall, a pan"),
    # ---- the rhythm stops: end card ----
    dict(t=STOP, clip="3376", src=5.10, speed=0.5, x="flash", z=(1.02, 1.08), c=(0.45, 0.55), look="candle",
         rays=(0.12, 0.15, 0.30), note="her, slow: END CARD"),
]
for i, s in enumerate(SHOTS):
    s["end"] = SHOTS[i + 1]["t"] if i + 1 < len(SHOTS) else DURATION
    s["i"] = i
    s.setdefault("speed", 1.0)
    s.setdefault("look", "gold")
    s.setdefault("c", (0.5, 0.5))
    s.setdefault("rays", None)
    s.setdefault("hires", False)
    s.setdefault("ramp", False)
    s.setdefault("z", (1.0, min(1.10, 1.0 + 0.03 * (s["end"] - s["t"]))))

# text: (start, end, kind)
TEXT = [
    (0.00, b(4) - 0.04, "hook"),
    (5.62, 8.10, "lower"),
    (31.00, 34.40, "prayer"),
    (40.15, 42.92, "event"),
    (STOP + 0.30, DURATION + 0.1, "end"),
]


def shot_at(t):
    for s in SHOTS:
        if s["t"] - 1e-9 <= t < s["end"]:
            return s
    return SHOTS[-1]


def src_time(s, t):
    """Source time in the clip for reel time t inside shot s (speed ramps on the shot into the drop)."""
    u = t - s["t"]
    if s["ramp"]:                                             # 0.6x, then rushing into the drop (2x at the end)
        dur = s["end"] - s["t"]
        k = max(0.0, (u - dur * 0.55) / (dur * 0.45))
        return s["src"] + 0.6 * u + 0.9 * dur * 0.45 * k ** 2
    return s["src"] + u * s["speed"]


if __name__ == "__main__":
    import json
    stats = json.load(open(os.path.join(ROOT, "renders/analysis/clipstats.json")))
    for s in SHOTS:
        n = stats[f"IMG_{s['clip']}.mp4"]["n"] / FPS
        need = src_time(s, s["end"] - 1e-3)
        flag = "" if need <= n else f"  <-- needs {need:.2f}s, clip is {n:.2f}s"
        print(f"{s['i']:2d} {s['t']:6.2f}-{s['end']:6.2f} ({s['end'] - s['t']:4.2f})  {s['clip']} @{s['src']:4.2f} "
              f"x{s['speed']:.2f} {s['x']:8s} {s['note']}{flag}")
    print(f"total {DURATION:.3f} s = {TOTAL} frames;  breath {BREATH:.2f}  drop2 {DROP2:.2f}  stop {STOP:.2f}")
