"""The SHELF CAMPUS founders reel recut: every segment of the output timeline, and the song's edit.

Output: 1080x1920, 30 fps, ~60.7 s. Times are seconds; `out` is the output timeline, `src` the
source reel (renders/src/founders_reel_original.mp4, 72.17 s, the team's own 1:12 edit).

The cut is built around three musical events of the song (Lex Amarni & 2muchmotion, "The Kill 2",
102.89 BPM, beat k at song time SONG_PHASE + k * BEAT):
  D   drop 1 (song 9.400)  lands on the name in "I'm JNANOTTAM"
  R   the bass stops (song 62.467, the breakdown) on the hard cut to black before the reveal
  D2  drop 2 (song 65.383) lands on "SHELF" in "Meet SHELF Campus"
Everything else is placed relative to those, and picture cuts sit on the beat grid where they can.

  python3 tools/edl.py          # print the timeline
"""
import json
import os

FPS = 30
W, H = 1080, 1920
SRC = "renders/src/founders_reel_original.mp4"
SONG = "renders/src/song_the_kill_2.mp3"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BEAT = 0.58315            # s per beat (102.89 BPM), fitted over the whole song
SONG_PHASE = 0.070        # song time of beat 0 (bar lines every 4 beats)
SONG_DROP1 = 9.400        # beat 16: bass + hats enter
SONG_STOP = 62.467        # beat 107: the bass stops (breakdown)
SONG_DROP2 = 65.383       # beat 112: drop 2


def fr(t):
    """Snap a time to the frame grid."""
    return round(t * FPS) / FPS


# ---- the three anchors (output time) ----
A_FREEZE = fr(9.92)                 # K's "Bro, what assignment!" ends: tape stop, freeze, stamps
B_START = fr(11.22)                 # cut to J; "I'm" in silence
D = fr(B_START + (16.18 - 15.70))   # drop 1 on "JNANOTTAM" (src 16.18) = 11.700


def beat(k, base=None):
    """Output time of the k-th beat after drop 1 (or after `base`)."""
    return (D if base is None else base) + k * BEAT


R = fr(beat(19))                    # hard cut to black on the bass stop = 22.781
D2 = R + (SONG_DROP2 - SONG_STOP)   # drop 2 = 25.697 (not frame-snapped: music time)


def beat2(k):
    return D2 + k * BEAT


# ---- segments ----
# kind: talk (footage + its own sound), freeze (hold one source frame), gfx (full-frame graphics slot),
# split (the two-founders poster: both cut-outs over a graphics background)
# who: J = Jnanottam (topographic tee), K = Kartik (maroon tee)
SEGMENTS = []


def seg(kind, out0, out1, src=None, who=None, text="", **kw):
    s = dict(kind=kind, out0=fr(out0), out1=fr(out1), src=src, who=who, text=text, **kw)
    SEGMENTS.append(s)
    return s


# A. HOOK + CHAOS (the song's muffled intro, then a tape stop)
seg("talk", 0.000, 2.450, 0.40, "J", "Your phone has 256 gigs of storage.", id="A1")
seg("talk", 2.450, 4.250, 4.22, "K", "And you still can't find the [bleep] notes?", id="A2")
seg("talk", 4.250, 7.070, 7.04, "J", "Maths in one group, Computer Science in another.", id="A3a")
seg("talk", 7.070, 8.400, 10.07, "J", "And the assignment deadline?", id="A3b", punch=1.14)
seg("talk", 8.400, A_FREEZE, 12.90, "K", "Bro, what assignment!", id="A4")
seg("freeze", A_FREEZE, B_START, 14.40, "K", "", id="A5")
# B. THE FOUNDERS (drop 1)
seg("talk", B_START, 13.270, 15.70, "J", "I'm Jnanottam.", id="B1")
seg("freeze", 13.270, beat(3), 17.75, "J", "", id="B1f")
seg("talk", beat(3), beat(6), 18.50 - (beat(4) - beat(3)), "K", "I'm Kartik.", id="B2")       # "Kar-" on beat 4
seg("split", beat(6), beat(11), None, "JK", "", id="B3", j_src=16.40, k_src=19.30)
seg("talk", beat(11), 21.085, 20.43, "J", "We got tired of watching students lose their minds.", id="B4")
seg("talk", 21.085, R, 25.15, "K", "So we built something for it.", id="B5")
# C. THE REVEAL (breakdown, then drop 2 on "SHELF")
seg("gfx", R, beat2(3), None, None, "", id="C0", slot="logo_reveal",
    vo=[dict(src0=28.62, src1=30.40, out0=D2 - (29.45 - 28.62), text="Meet SHELF Campus.", who="J")])
seg("talk", beat2(3), 30.006, 31.10, "K", "Your AI-powered academic memory", id="C2")
seg("talk", 30.006, beat2(11), 35.36, "J", "that lives on WhatsApp.", id="C3")
# D. THE DEMO (full-frame phone, voice-over from the reel's floor shot)
seg("gfx", beat2(11), beat2(34), None, None, "", id="D", slot="demo",
    vo=[dict(src0=38.40, src1=40.52, out0=34.000 - 0.05, text="Got notes? Just shelf it."),
        dict(src0=41.90, src1=43.42, out0=36.330 - 0.06, text="Need them back? Ask."),
        dict(src0=45.74, src1=47.68, out0=38.660 - 0.08, text="Deadlines handled."),
        dict(src0=49.30, src1=50.88, out0=41.000 - 0.07, text="Reminders sorted.")])
# E. THE PAYOFF (reordered to alternate J / K, as in the script)
seg("talk", beat2(34), 46.975, 55.50, "J", "Your notes aren't lost.", id="E1")
seg("talk", 46.975, 48.895, 52.23, "K", "Your deadlines aren't a surprise anymore.", id="E2")
seg("talk", 48.895, 49.975, 58.12, "J", "And your WhatsApp?", id="E3")
seg("talk", 49.975, 51.685, 60.04, "K", "Finally doing something useful.", id="E4")
seg("freeze", 51.685, beat2(46), 61.74, "K", "", id="E4f")
# F. CALL TO ACTION
seg("talk", beat2(46), 54.672, 62.85, "K", "Built by students, for students.", id="F1")
seg("talk", 54.672, 56.955, 69.567, "K", "Your semester just got an upgrade.", id="F2")
seg("gfx", 56.955, beat2(60), None, None, "", id="F3", slot="end_card")

TOTAL = round(SEGMENTS[-1]["out1"] * FPS)            # frames
DURATION = TOTAL / FPS

# the song's edit: (out0, out1, song0) pieces; out1 of the last piece is the end of the reel
MUSIC = [
    (0.000, 7.068, 0.000),                       # intro bars 0-2
    (7.068, A_FREEZE, 4.735),                    # bar 2 again (the intro is a steady loop), then bar 3: tape stop at A_FREEZE
    (D, R, SONG_DROP1),                          # drop 1, 19 beats
    (R, DURATION, SONG_STOP),                    # breakdown -> drop 2 -> to the end
]

# bleep: "fucking" in K's line (src), replaced by the radio beep, plus a censor bar on his mouth
BLEEP_SRC = (5.14, 5.54)


def out_of_src(src_t, seg_id):
    s = next(x for x in SEGMENTS if x.get("id") == seg_id)
    return s["out0"] + (src_t - s["src"])


def at(t):
    """The segment playing at output time t."""
    for s in SEGMENTS:
        if s["out0"] <= t + 1e-9 < s["out1"]:
            return s
    return SEGMENTS[-1]


def src_frame(n):
    """Source frame index (or None for graphics) shown at output frame n."""
    t = n / FPS
    s = at(t)
    if s["kind"] == "talk":
        return int(round((s["src"] + t - s["out0"]) * FPS))
    if s["kind"] == "freeze":
        return int(round(s["src"] * FPS))
    return None


def song_time(t):
    for a, b, s0 in MUSIC:
        if a <= t < b:
            return s0 + (t - a)
    return None


def beats_out(t0, t1):
    """Song beat times (output s) inside [t0, t1): [(t, is_bar)]."""
    out = []
    for a, b, s0 in MUSIC:
        k0 = int((s0 - SONG_PHASE) / BEAT) - 1
        for k in range(k0, k0 + 400):
            st = SONG_PHASE + k * BEAT
            t = a + (st - s0)
            if t >= b:
                break
            if t >= max(a, t0) and t < t1:
                out.append((round(t, 3), k % 4 == 0))
    return out


def dump():
    data = dict(fps=FPS, total=TOTAL, D=D, R=R, D2=D2, segments=SEGMENTS, music=MUSIC,
                beats=beats_out(0, DURATION))
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    json.dump(data, open(os.path.join(ROOT, "renders", "edl.json"), "w"), indent=1)


if __name__ == "__main__":
    for s in SEGMENTS:
        src = f"src {s['src']:6.2f}-{s['src'] + s['out1'] - s['out0']:6.2f}" if s["src"] is not None else " " * 17
        print(f"{s['id']:4s} {s['kind']:6s} {s['out0']:7.3f}-{s['out1']:7.3f} ({s['out1'] - s['out0']:5.2f})  {src}  {s['who'] or '':2s} {s['text']}")
    print(f"total {TOTAL} frames = {DURATION:.3f} s   D={D:.3f}  R={R:.3f}  D2={D2:.3f}")
    dump()
