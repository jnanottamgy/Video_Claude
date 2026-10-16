"""The CR aura edit's timeline: output time (s) -> source frame, per segment, plus the beat grid.

Source: one 30 fps WhatsApp video. Podcast setup S 0-12.9 s; the CR clips S 13.17-30.87 s; the
song (a ~108 BPM trap/phonk beat) starts with its first downbeat at S 13.085 and runs exactly
8 bars to the end of the file.

Output: 30 fps, 1080x1920. The hook is the podcast tightened to its four lines; the song's first
downbeat lands at DROP = 4.0 s, and from there every cut sits on the song's 808 pattern
(3-3-4-3-3 eighths per two bars).
"""
FPS = 30
DROP = 4.0                      # output time of the song's first downbeat
SONG_T0 = 13.085                # source time of that downbeat
EIGHTH = 60 / 108 / 2           # 0.27778 s
BAR = EIGHTH * 8
SONG_BARS = 8
SONG_END = DROP + SONG_BARS * BAR          # 21.778: the next downbeat (the source ends here)
END = SONG_END + 1.75                      # end card + tail

# 808 hits in eighths from the drop (measured: 3-3-4-3-3 per two bars, fills at 31-32 and 56.5-62)
K808 = [0, 3, 6, 10, 13, 16, 19, 22, 26, 29, 31, 32, 35, 38, 42, 45, 48, 51, 54, 56.5, 58, 61, 62, 64]
CLAPS = [4 + 8 * k for k in range(8)]      # beat 3 of every bar


def tq(n):
    """Output time of eighth-note n after the drop."""
    return DROP + n * EIGHTH


def song_src_time(t_out):
    return SONG_T0 + (t_out - DROP)


# ---------- segments ----------
# Each segment: out [t0, t1) seconds; source frames via 'src' = (f_start, speed) or a list of
# (t_rel, src_frame) keys (linear between keys = speed ramps / freezes). 'fx' names effect passes
# the compositor applies; 'cam' is the segment's own camera move (scale at start -> end, centre).
SEGMENTS = [
    # ---- HOOK: the podcast, full frame, natural ----
    dict(id="her_claim", t0=0.0, t1=2.06, src=(6, 1.0), audio=(0.20, 2.26), fx=["podcast"]),
    dict(id="host_please", t0=2.06, t1=2.68, src=(120, 1.0), audio=(4.00, 4.62), fx=["podcast"]),
    dict(id="her_maaa", t0=2.68, t1=3.2467, src=(148, 1.0), audio=(4.933, 5.50), fx=["podcast", "maaa_punch"]),
    dict(id="host_take2", t0=3.2467, t1=3.70, keys=[(0.0, 217.5), (0.38, 228.9), (0.4533, 228.9)],
         audio=(7.25, 7.70), fx=["podcast", "take2_freeze"]),
    # ---- the strobe: his silhouettes flash white/red on black (9 frames) ----
    dict(id="strobe", t0=3.70, t1=DROP, src=(521, 0.0), fx=["strobe"]),
    # ---- PHRASE 1: the reveal ----
    # the stare at the green board, half speed, THE G.O.A.T. behind him
    dict(id="stare", t0=DROP, t1=tq(6), keys=[(0.0, 513), (tq(3) - DROP, 520), (tq(6) - DROP, 528)],
         fx=["cine", "title_goat", "hero_hit"], cam=(1.0, 1.06, 0.5, 0.33)),
    # the turn to camera, half speed with ghost trails
    dict(id="turn", t0=tq(6), t1=tq(10), keys=[(0.0, 484), (tq(10) - tq(6), 503)], fx=["cine", "echo"],
         cam=(1.04, 1.0, 0.45, 0.35)),
    # the chin pose, frozen, aura outline + "+1000 AURA"
    dict(id="pose", t0=tq(10), t1=tq(13), keys=[(0.0, 556), (0.20, 561), (tq(13) - tq(10), 561)],
         fx=["cine", "aura", "plus1000"], cam=(1.0, 1.08, 0.48, 0.42)),
    # on the phone at the board, push in, then the suck into phrase 2
    dict(id="phone", t0=tq(13), t1=tq(16), keys=[(0.0, 448), (tq(16) - tq(13), 470)], fx=["cine", "suck_out"],
         cam=(1.0, 1.10, 0.5, 0.3)),
    # ---- PHRASE 2: the montage ----
    # double exposure: the chin-pose silhouette on white, filled with his other clips (muffled music)
    dict(id="dblexp", t0=tq(16), t1=tq(22), src=(561, 0.0), fx=["dblexp"]),
    # typing at the lab PC
    dict(id="typing", t0=tq(22), t1=tq(26), keys=[(0.0, 580), (tq(26) - tq(22), 609)], fx=["cine"],
         cam=(1.08, 1.0, 0.45, 0.5)),
    # the smile with the red curtains flashing white on the eighths
    dict(id="smile", t0=tq(26), t1=tq(29), keys=[(0.0, 612), (tq(29) - tq(26), 637)], fx=["cine", "curtain_flash"],
         cam=(1.0, 1.06, 0.45, 0.3)),
    # thumbs-up into the lens, then the turn-away whip into phrase 3
    dict(id="thumb", t0=tq(29), t1=tq(32), keys=[(0.0, 645), (0.45, 656), (tq(32) - tq(29), 676)], fx=["cine", "whip_out"],
         cam=(1.0, 1.05, 0.55, 0.45)),
    # ---- PHRASE 3 ----
    # the smirk with the backpack
    dict(id="smirk", t0=tq(32), t1=tq(38), keys=[(0.0, 680), (tq(35) - tq(32), 694), (tq(35) - tq(32) + 0.0333, 694),
                                                  (tq(38) - tq(32), 709)],
         fx=["cine", "whip_in", "smirk_hits"], cam=(1.0, 1.14, 0.5, 0.33)),
    # the close smile
    dict(id="close", t0=tq(38), t1=tq(42), keys=[(0.0, 712), (tq(42) - tq(38), 741)], fx=["cine", "chroma_hit"],
         cam=(1.06, 1.0, 0.5, 0.35)),
    # the wave, half speed, then the walk at 2x
    dict(id="wave", t0=tq(42), t1=tq(48), keys=[(0.0, 744), (tq(45) - tq(42), 758), (tq(48) - tq(42), 806)],
         fx=["cine", "echo_light"]),
    # ---- PHRASE 4: the finale ----
    # the walk-off, CLASS REPRESENTATIVE on the far wall behind him
    dict(id="walkoff", t0=tq(48), t1=tq(56.5), keys=[(0.0, 806), (tq(54) - tq(48), 862), (tq(56.5) - tq(48), 905)],
         fx=["cine", "title_cr"]),
    # he turns back and smiles: slow, zooming in, then freeze
    dict(id="turnback", t0=tq(56.5), t1=tq(64), keys=[(0.0, 905), (tq(61) - tq(56.5), 921), (tq(64) - tq(56.5), 922)],
         fx=["cine", "finale_zoom", "aura_small"]),
    # end card: freeze, THE G.O.A.T. + CLASS REPRESENTATIVE, fade out
    dict(id="endcard", t0=SONG_END, t1=END, src=(922, 0.0), fx=["cine", "finale_zoom", "aura_small", "endcard"]),
]


def segment_at(t):
    for s in SEGMENTS:
        if s["t0"] <= t < s["t1"]:
            return s
    return SEGMENTS[-1]


def src_frame(seg, t):
    """Fractional source frame for output time t inside seg."""
    u = t - seg["t0"]
    if "keys" in seg:
        ks = seg["keys"]
        if u <= ks[0][0]:
            return ks[0][1]
        for (a, fa), (b, fb) in zip(ks, ks[1:]):
            if u <= b:
                return fa + (fb - fa) * (u - a) / max(b - a, 1e-6)
        return ks[-1][1]
    f0, speed = seg["src"]
    return f0 + speed * u * FPS


def frame_count():
    return int(round(END * FPS))


if __name__ == "__main__":
    for s in SEGMENTS:
        print(f"{s['id']:12s} {s['t0']:6.3f}-{s['t1']:6.3f} ({s['t1'] - s['t0']:.3f}s)  src {src_frame(s, s['t0']):.1f} -> {src_frame(s, s['t1'] - 1e-6):.1f}  {s['fx']}")
    print("808 hits:", [round(tq(n), 3) for n in K808])
    print("frames:", frame_count(), "duration", END)
