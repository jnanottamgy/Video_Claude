"""The recut's edit decision list: which source frames make each output frame.

Source is renders/source.mp4 (1080x1920, 30 fps, 3595 frames). All positions are FRAMES.
Segment kinds:
  cut      plays src [a, b) at `speed` (frame-blended when speed > 1)
  rewind   a VHS rewind sweep from src `a` back to src `b` over `n` output frames
  freeze   holds src frame `a` for `n` output frames
Audio per segment:
  orig     the source mix (dialogue + their music) under this exact source range
  sd       sound design only: the source audio is muted here
  rewind   the source audio reversed and sped up, as a tape rewind
  tail     the source audio continues past the picture (end hold), then fades

Every dialogue line keeps its original timing: speed is only changed where nobody speaks.
"""
FPS = 30

SEGMENTS = [
    # HOOK: open on the breakdown ("what the f...why are my notes scattered..."), then rewind to the start
    dict(id="H1", kind="cut", a=1577, b=1681, audio="orig"),
    dict(id="H2", kind="rewind", a=1680, b=24, n=24, audio="rewind"),
    # 1 WAKE UP: 17 s of no dialogue, compressed with speed ramps; sound design replaces their intro bed
    dict(id="P1a", kind="cut", a=24, b=72, audio="orig"),                  # alarm: 11:51, Snooze (their real alarm)
    dict(id="P1b", kind="cut", a=162, b=223, speed=1.25, audio="sd"),       # asleep, eyes open
    dict(id="P1c", kind="cut", a=223, b=332, speed=2.4, audio="sd"),        # sits up
    dict(id="P1d", kind="cut", a=363, b=433, speed=1.6, audio="sd"),        # picks up the phone
    dict(id="P1e", kind="cut", a=456, b=512, audio="orig", fade_in=0.35),   # reads it; their bass enters at src 16.0
    # 2 PANIC: "F... I have an exam in 8 hours"
    dict(id="P2", kind="cut", a=512, b=618, audio="orig"),
    # 3 CALL SETUP: rings at src 20.83-21.86 and 23.40-24.90 play; the third (26.41-27.91) is cut
    dict(id="P3", kind="cut", a=618, b=749, audio="orig"),                    # ring 2 ends at src 24.90
    # 4 THE CALL: Ishaan, the CR, the official group, the boys group
    dict(id="P4", kind="cut", a=852, b=1577, audio="orig"),
    # 5 BREAKDOWN: "why are my notes scattered in so many groups?" + the notification storm
    dict(id="P5a", kind="cut", a=1577, b=1686, audio="orig"),
    dict(id="P5b", kind="cut", a=1686, b=1800, audio="orig"),
    # 6 THE FOUNDERS (their own whip-blur in 1844-1856 is skipped; ours replaces it)
    dict(id="P6a", kind="cut", a=1857, b=1968, audio="orig"),
    dict(id="P6b", kind="cut", a=1968, b=2085, audio="orig"),
    dict(id="P6c", kind="cut", a=2112, b=2239, audio="orig"),                               # runs on so the freeze lands on a beat
    dict(id="P6c_f", kind="freeze", a=2238, n=15, audio="orig", src_audio=(2239, 2254)),   # silence after "...here at SHELF"
    dict(id="P6c_x", kind="freeze", a=2238, n=22, audio="sd"),                              # name card; P6d lands on a beat
    dict(id="P6d", kind="cut", a=2254, b=2376, audio="orig"),
    dict(id="P6d_f", kind="freeze", a=2375, n=10, audio="orig", src_audio=(2376, 2386)),
    dict(id="P6d_x", kind="freeze", a=2375, n=27, audio="sd"),                              # P7 lands on a beat
    # 7 THE PROBLEM, 8 THE SOLUTION: untouched timing
    dict(id="P7", kind="cut", a=2386, b=2781, audio="orig"),
    dict(id="P8", kind="cut", a=2781, b=3063, audio="orig"),
    # 9 TEASE -> STAY TUNED -> wall reveal (fully revealed until src 116.1, where their fade begins)
    dict(id="P9a", kind="cut", a=3063, b=3163, audio="orig"),
    dict(id="P9a_h", kind="freeze", a=3162, n=7, audio="sd"),   # under the glitch: STAY TUNED lands on a bar
    dict(id="P9b", kind="cut", a=3163, b=3483, audio="orig"),
    dict(id="END", kind="freeze", a=3482, n=47, audio="tail", src_audio=(3483, 3530)),   # ends where the song loops into the hook
]


def seg_len(s):
    if s["kind"] == "cut":
        return round((s["b"] - s["a"]) / s.get("speed", 1.0))
    return s["n"]


def layout():
    """Each segment with its output start frame `o` and length `n`."""
    out, o = [], 0
    for s in SEGMENTS:
        n = seg_len(s)
        out.append({**s, "o": o, "n": n})
        o += n
    return out


LAYOUT = layout()
TOTAL = LAYOUT[-1]["o"] + LAYOUT[-1]["n"]
BY_ID = {s["id"]: s for s in LAYOUT}


def out_time(src_t, seg_id):
    """Output time (s) of source time `src_t` (s), inside segment `seg_id`."""
    s = BY_ID[seg_id]
    if s["kind"] != "cut":
        raise ValueError(f"{seg_id} is not a cut")
    sp = s.get("speed", 1.0)
    f = src_t * FPS
    if not (s["a"] - 1 <= f <= s["b"] + 1):
        raise ValueError(f"src {src_t:.3f}s is outside {seg_id} [{s['a'] / FPS:.3f}, {s['b'] / FPS:.3f})")
    return (s["o"] + (f - s["a"]) / sp) / FPS


def seg_of(src_t, prefer=None):
    """The (last, or preferred) cut segment containing source time `src_t`."""
    f = src_t * FPS
    hits = [s for s in LAYOUT if s["kind"] == "cut" and s["a"] <= f < s["b"]]
    if prefer:
        hits = [s for s in hits if s["id"] == prefer] or hits
    return hits[-1]["id"] if hits else None


# v1 (the first delivered cut) had other hold lengths; cue times measured on it map through here
V1_N = {"END": 66, "P6c": 122, "P6c_f": 20, "P6c_x": 24, "P6d": 113, "P6d_f": 19, "P6d_x": 24, "P9a_h": 0}


def from_v1(t):
    """Output time in this cut of what sat at output time `t` in v1 (same segment, same offset)."""
    o = 0
    for s in LAYOUT:
        n = V1_N.get(s["id"], s["n"])
        if o <= t * FPS < o + n or s is LAYOUT[-1]:
            return (s["o"] + min(t * FPS - o, max(n, s["n"]))) / FPS
        o += n
    return t


def src_frame(out_f):
    """(segment, source position in frames, blend span) for output frame `out_f`."""
    for s in LAYOUT:
        if s["o"] <= out_f < s["o"] + s["n"]:
            k = out_f - s["o"]
            if s["kind"] == "cut":
                sp = s.get("speed", 1.0)
                return s, s["a"] + k * sp, sp
            if s["kind"] == "freeze":
                return s, float(s["a"]), 1.0
            return s, None, None      # rewind: handled by the compositor
    raise IndexError(out_f)


if __name__ == "__main__":
    for s in LAYOUT:
        src = f"src {s['a'] / FPS:7.3f}-{s.get('b', s['a']) / FPS:7.3f}" if s["kind"] != "rewind" else f"rewind {s['a'] / FPS:.2f}->{s['b'] / FPS:.2f}"
        print(f"{s['id']:6s} {s['kind']:7s} out {s['o'] / FPS:7.3f}-{(s['o'] + s['n']) / FPS:7.3f} ({s['n']:3d}f)  {src}  x{s.get('speed', 1.0)}  audio={s['audio']}")
    print(f"TOTAL {TOTAL} frames = {TOTAL / FPS:.2f}s")
