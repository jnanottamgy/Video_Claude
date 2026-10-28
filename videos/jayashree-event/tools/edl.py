"""Jayashree D Jain: event reel (v2). Every shot of the output, on the song's pulse grid.

The music is "Chanakya" (Rishab Rikhiram Sharma), the client's 45 s edit audio, played from song 4.130 s to
43.197 s (39.07 s). In D, 140 BPM. A sitar intro builds without percussion, hi-hats rise from song 10.1, the
beat comes in at song 11.844 (the drop) and the bass a bar later (13.556). The rhythm runs on to the last
hit at song ~41.4 and the track fades out.

The intro carries the hook (JAI JINENDRA, then "an evening of pure bhakti.") and her name in slow motion.
From the drop the event is cut quick: B-roll on 2 pulses, or the song's 3-3-2 accents (bar + 0, 1.5, 3, 4).
Her shots are held for 4.

Reel time t = song time - SONG_IN; pulse k sits at k * PULSE (pulse 18 is the drop, bars of 4 from there).
  python3 tools/edl.py     # print the shot list
"""
import os

FPS = 30
W, H = 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONG = os.path.join(ROOT, "renders/analysis/song_chanakya.wav")
PULSE = 60 / 140.0               # 0.4286 s; grid fitted to the kicks and snares (14 ms rms)
DROP_SONG = 11.844               # the beat comes in
SONG_IN = DROP_SONG - 18 * PULSE  # 4.130: the intro keeps 18 pulses of the sitar build
DURATION = 1172 / FPS            # 39.067 s: to song 43.197, the fade's tail under the end card's bell
TOTAL = 1172
SA = 293.66                      # D4, the song's tonic (bells and shankh are tuned to it)


def p(k):
    """Reel time of pulse k."""
    return k * PULSE


DROP = p(18)                     # the beat comes in (song 11.844)
BASS = p(22)                     # the bass comes in, a bar later (song 13.556)
END = p(82)                      # the last phrase: the end card (song 39.27)

# shots: t = start (reel s), clip, src = source in-point (s), speed (< 1 = optical-flow slow motion),
#   x = transition INTO this shot: cut | flash | dissolve | whip | drop,
#   z = (zoom at start, at end) about c = (x, y) normalised (a push-in by default), rays = god rays from
#   (x, y, strength), look = grade (gold | candle), hires = decode the 4K original (heavy crops),
#   her = a shot of Jayashree (held longer, never cut quick)
SHOTS = [
    # ---- INTRO: the sitar builds; slow, warm, three lines of type ----
    dict(t=p(0), clip="3397", src=1.90, x="cut", z=(1.0, 1.10), c=(0.38, 0.56), her=True,
         note="HOOK: her mid-phrase, hand rising: JAI JINENDRA"),
    dict(t=p(5), clip="3393", src=4.00, speed=0.55, x="dissolve", z=(1.05, 1.12), c=(0.6, 0.6), look="candle",
         rays=(0.5, 0.08, 0.5), note="aarti flames, slow: an evening of pure bhakti."),
    dict(t=p(10), clip="3407", src=0.15, speed=0.5, x="dissolve", z=(1.04, 1.14), c=(0.48, 0.5), look="candle",
         her=True, note="her warm close-up, slow: JINA GAANA VISHARADE / JAYASHREE D JAIN"),
    # ---- DROP: the beat comes in; the event, quick ----
    dict(t=DROP, clip="3403", src=1.00, x="drop", z=(1.18, 1.24), c=(0.5, 0.74), note="the hall lifts its hands"),
    dict(t=p(20), clip="3387", src=0.80, x="cut", rays=(0.5, -0.05, 0.22), note="Tirthankaras under golden umbrellas"),
    dict(t=BASS, clip="3376", src=3.40, x="flash", z=(1.0, 1.06), c=(0.42, 0.62), rays=(0.12, 0.15, 0.30), her=True,
         note="her profile, arched windows (the bass comes in)"),
    dict(t=p(26), clip="3385", src=0.60, x="cut", c=(0.5, 0.55), note="dholak"),
    dict(t=p(27.5), clip="3372", src=1.20, x="cut", note="keys"),
    dict(t=p(29), clip="3399", src=1.50, x="cut", z=(1.10, 1.06), c=(0.5, 0.35), note="the hall: scale"),
    dict(t=p(30), clip="3449", src=0.80, x="whip", z=(1.0, 1.08), c=(0.28, 0.60), rays=(0.5, 0.30, 0.30), her=True,
         note="her in the chandelier hall"),
    # the event card rides over four quick shots
    dict(t=p(34), clip="3395", src=0.40, x="flash", rays=(0.5, 0.0, 0.25), note="the stage of idols: EVENT CARD"),
    dict(t=p(36), clip="3393", src=2.60, x="cut", rays=(0.5, 0.08, 0.3), note="aarti lamps"),
    dict(t=p(38), clip="3388", src=0.80, x="cut", note="saffron and yellow sarees, puja"),
    dict(t=p(40), clip="3451", src=2.00, x="cut", z=(1.08, 1.14), c=(0.5, 0.55), rays=(0.5, 0.33, 0.3),
         note="aarti under the chandelier"),
    dict(t=p(42), clip="3371", src=1.00, x="whip", z=(1.05, 1.14), c=(0.5, 0.78), her=True,
         note="her with the musicians, the logo on screen"),
    dict(t=p(46), clip="3384", src=1.60, x="cut", note="sadhvis in white"),
    dict(t=p(48), clip="3389", src=0.60, x="cut", z=(1.80, 1.86), c=(0.70, 0.72), hires=True,
         note="hands holding a diya"),
    # the dignitaries
    dict(t=p(50), clip="3412", src=4.30, x="flash", c=(0.68, 0.70), note="the chief guest at the podium"),
    dict(t=p(52), clip="3413", src=1.50, x="cut", z=(1.55, 1.62), c=(0.45, 0.72), hires=True,
         note="the dais: dignitaries in pink turbans"),
    dict(t=p(54), clip="3379", src=0.30, x="whip", c=(0.45, 0.6), her=True, note="her profile"),
    dict(t=p(58), clip="3456", src=0.40, x="cut", note="a dignitary garlanded, on the big screen"),
    dict(t=p(60), clip="3405", src=2.00, x="cut", note="the dance"),
    dict(t=p(62), clip="3408", src=0.80, x="cut", note="dholak"),
    dict(t=p(64), clip="3391", src=1.00, x="cut", z=(1.0, 1.06), rays=(0.5, 0.0, 0.3), note="hands raised"),
    # the climax
    dict(t=p(66), clip="3443", src=0.20, x="flash", z=(1.0, 1.08), c=(0.55, 0.80), her=True,
         note="her at the mic, the hall on screen"),
    dict(t=p(70), clip="3405", src=9.20, x="cut", note="the dance, closer"),
    dict(t=p(71.5), clip="3402", src=1.60, x="cut", note="the crowd and the cameras"),
    dict(t=p(73), clip="3445", src=1.20, x="cut", note="dholak, the guru on screen"),
    dict(t=p(74), clip="3401", src=0.90, x="whip", note="the whole hall, a pan"),
    dict(t=p(76), clip="3403", src=4.20, x="cut", z=(1.18, 1.22), c=(0.5, 0.74), note="the hall, hands up"),
    dict(t=p(78), clip="3373", src=2.20, x="flash", z=(1.0, 1.08), c=(0.5, 0.72), her=True,
         note="her, the crowd on the screen behind"),
    # ---- the last phrase: end card ----
    dict(t=END, clip="3376", src=5.10, speed=0.5, x="flash", z=(1.02, 1.08), c=(0.45, 0.55), look="candle",
         rays=(0.12, 0.15, 0.30), her=True, note="her, slow: END CARD"),
]
DISSOLVES = {1: 0.5, 2: 0.8}     # shot index -> cross-dissolve length (s) into it
for i, s in enumerate(SHOTS):
    s["end"] = SHOTS[i + 1]["t"] if i + 1 < len(SHOTS) else DURATION
    s["i"] = i
    s.setdefault("speed", 1.0)
    s.setdefault("look", "gold")
    s.setdefault("c", (0.5, 0.5))
    s.setdefault("rays", None)
    s.setdefault("hires", False)
    s.setdefault("ramp", False)
    s.setdefault("her", False)
    s.setdefault("z", (1.0, min(1.10, 1.0 + 0.03 * (s["end"] - s["t"]))))

# text: (start, end, kind)
TEXT = [
    (0.00, p(5) - 0.10, "hook"),
    (p(5) + 0.20, p(10) - 0.15, "second"),
    (p(10) + 0.20, DROP, "name"),
    (p(34) + 0.05, p(42) + 0.30, "event"),
    (END + 0.30, DURATION + 0.1, "end"),
]

# the song's accents inside each bar (pulses from the bar line), for exposure pulses and cut bursts
ACCENTS = (0.0, 1.5, 3.0)


def shot_at(t):
    for s in SHOTS:
        if s["t"] - 1e-9 <= t < s["end"]:
            return s
    return SHOTS[-1]


def src_time(s, t):
    """Source time in the clip for reel time t inside shot s (a speed ramp on shots marked ramp)."""
    u = t - s["t"]
    if s["ramp"]:                                             # 0.6x, then rushing out (2x at the end)
        dur = s["end"] - s["t"]
        k = max(0.0, (u - dur * 0.55) / (dur * 0.45))
        return s["src"] + 0.6 * u + 0.9 * dur * 0.45 * k ** 2
    return s["src"] + u * s["speed"]


if __name__ == "__main__":
    import json
    stats = json.load(open(os.path.join(ROOT, "renders/analysis/clipstats.json")))
    her = 0.0
    for s in SHOTS:
        n = stats[f"IMG_{s['clip']}.mp4"]["n"] / FPS
        need = src_time(s, s["end"] - 1e-3)
        flag = "" if need <= n else f"  <-- needs {need:.2f}s, clip is {n:.2f}s"
        her += (s["end"] - s["t"]) if s["her"] else 0
        print(f"{s['i']:2d} {s['t']:6.2f}-{s['end']:6.2f} ({s['end'] - s['t']:4.2f})  {s['clip']} @{s['src']:4.2f} "
              f"x{s['speed']:.2f} {s['x']:8s} {'HER ' if s['her'] else ''}{s['note']}{flag}")
    print(f"total {DURATION:.3f} s = {TOTAL} frames; song {SONG_IN:.3f}-{SONG_IN + DURATION:.3f}; "
          f"drop {DROP:.3f}  bass {BASS:.3f}  end card {END:.3f}; her on screen {her:.1f} s ({her / DURATION:.0%})")
