"""The ~48 s cut, built from the full v2 render.

Instagram reach is best for 30-60 s reels, and its ranker compares watch time with reels of the
same length, so the main post is a tighter cut of the same edit: the hook, the 11:51 alarm, the
panic, three "it's in another group" beats, the breakdown into drop 1, one founder line, then
"so we built S.H.E.L.F" over drop 2 and the WhatsApp chat, and the "send this" ending that loops.

Picture: frames of renders/SHELF_reel_v2_video.mp4 (overlays, captions and looks baked in).
Sound: the full cut's dialogue and SFX stems re-cut with the picture (30 ms joins at every cut);
the song is laid again so the build, the gap, both drops and the loop land exactly where they do
in the full cut: one continuous run from the alarm to drop 1, then the full cut's alignment.

  python3 tools/shortcut.py      -> renders/SHELF_reel_v2_short.mp4 and ..._short_nomusic.mp4
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402
import mix_audio as MX  # noqa: E402
import music as MU  # noqa: E402

FPS, W, H, SR = edl.FPS, 1080, 1920, MX.SR
LONG = "renders/SHELF_reel_v2_video.mp4"

# (start, end) on the FULL cut's timeline (s), and how the song runs under it:
#   hook   as in the full cut (the pre-drop bar, then the tape rewind)
#   story  one continuous stretch of the song, laid so it reaches the full cut's alignment exactly
#          where the breakdown starts (so the gap and drop 1 land as before)
#   long   the full cut's alignment (each range re-anchors; the first one is the turn)
RANGES = [
    (0.000, 4.267, "hook"),       # hook + rewind
    (4.267, 5.400, "story"),      # 11:51 alarm, crash zoom
    (10.900, 12.333, "story"),    # he reads it
    (12.333, 15.400, "story"),    # "F*ck. I have an exam in 8 hours" + the countdown slam
    (21.133, 22.133, "story"),    # the WhatsApp call connects: "What's up bro?"
    (22.533, 23.333, "story"),    # "Bro, Ishaan,"
    (25.700, 27.067, "story"),    # "do you have the notes?"
    (27.300, 31.433, "story"),    # "Bro, the CR sent all the notes on the unofficial group"
    (35.067, 38.667, "story"),    # "the syllabus copy the teacher sent on the official class group, bro"
    (39.533, 42.733, "story"),    # "also in the boys group, Zaid sent all the solved PYQs"
    (44.400, 51.833, "story"),    # the breakdown: hats build, the bass drops out...
    (51.833, 55.267, "story"),    # ...drop 1: "clearly he hasn't heard about SHELF."
    (83.900, 92.767, "long"),     # "pretty simple. So we built S.H.E.L.F" — silence, drop 2, the chat
    (104.200, 108.567, "long"),   # the wall, LAUNCHING SOON, "send this to the friend who says..."
]


def frames(a, b):
    return int(round(a * FPS)), int(round(b * FPS))


def layout():
    """[(range, short start s, length s)] with every boundary on a frame."""
    out, o = [], 0
    for a, b, mode in RANGES:
        f0, f1 = frames(a, b)
        out.append(((f0 / FPS, f1 / FPS, mode), o / FPS, (f1 - f0) / FPS))
        o += f1 - f0
    return out, o


def music_map(lay):
    """[(short t0, short t1, song t0 or None)] for the short cut."""
    story = [(r, o, n) for r, o, n in lay if r[2] == "story"]
    k = next(i for i, (r, o, n) in enumerate(story) if abs(r[0] - 44.4) < 0.02)
    s0 = MU.song_time(44.4) - sum(n for r, o, n in story[:k])     # reach the breakdown on the full cut's alignment
    out = [(0.0, MU.MAP[0][2], MU.MAP[0][3]), (MU.MAP[1][1], MU.MAP[1][2], None)]
    t0 = story[0][1]
    out.append((t0, story[-1][1] + story[-1][2], s0))
    for r, o, n in lay:
        if r[2] == "long":
            out.append((o, o + n, MU.song_time(r[0])))
    return out


def recut(x, lay, fade=0.03):
    y = np.zeros((int(round(sum(n for _, _, n in lay) * SR)) + SR, 2))
    for (a, b, _), o, n in lay:
        seg = x[int(round(a * SR)):int(round(a * SR)) + int(round(n * SR))]
        MX.place(y, MX.fade(seg, fade, fade), o)
    return y


def build_music(song, mm, total):
    M = np.zeros((int(total * SR) + SR, 2))
    gain = {0: MX.MUSIC_GAIN["hook"], 2: MX.MUSIC_GAIN["story"]}
    for i, (a, b, s0) in enumerate(mm):
        if s0 is None:
            continue
        x = MX.seg(song, s0, s0 + (b - a))
        nxt = mm[i + 1] if i + 1 < len(mm) else None
        if i == 2:                                                     # story run: tape-stops into the turn
            x = MX.fade(MX.tape_stop(x, 0.24), 0.25, 0.0)
        elif i == 0:
            x = MX.fade(x, 0.005, 0.015)
        else:
            x = MX.fade(x, 0.010, 0.010 if nxt else 0.04)
        MX.place(M, x, a, 0, gain.get(i, MX.MUSIC_GAIN["drop2"]))
    return M


def phase(song_t):
    return ((song_t - MU.PHASE) / MU.T) % 4


def main():
    lay, nf = layout()
    total = nf / FPS
    mm = music_map(lay)
    print(f"short cut: {nf} frames = {total:.2f} s")
    for (a, b, mode), o, n in lay:
        print(f"  {o:6.2f}-{o + n:6.2f}  <- full {a:7.3f}-{b:7.3f}  {mode}")
    for a, b, s0 in mm:
        print(f"  music {a:6.2f}-{b:6.2f}  " + (f"song {s0:7.3f}-{s0 + b - a:7.3f}" if s0 is not None else "(rewind)"))
    # rhythm checks: each music jump should keep the bar phase; the end should loop into the hook
    for (a, b, s0), (c, d, s1) in zip(mm[2:], mm[3:]):
        print(f"  jump at {c:6.2f}: bar phase {phase(s0 + b - a):.2f} -> {phase(s1):.2f}")
    end_song = mm[-1][2] + (mm[-1][1] - mm[-1][0])
    print(f"  loop: end phase {phase(end_song):.2f}, hook starts at {phase(MU.MAP[0][3]):.2f}")

    # sound
    Dl = sf.read("renders/stem_D.wav", dtype="float64")[0]
    Bl = sf.read("renders/stem_B.wav", dtype="float64")[0]
    song = MX.load("renders/song.mp3")
    n = int(total * SR)
    Ds, Bs = recut(Dl, lay)[:n], recut(Bl, lay)[:n]
    Ms = MX.carve(build_music(song, mm, total)[:n], MX.speech_env(Ds))
    full = MX.OUT
    MX.OUT = "renders/mix_short.wav"
    MX.master(Ds + Ms + Bs)
    MX.OUT = "renders/mix_short_nomusic.wav"
    MX.master(Ds + Bs)
    MX.OUT = full

    # picture: the selected frames of the full render, in order
    want = []
    for (a, b, _), o, n in lay:
        f0, f1 = frames(a, b)
        want.extend(range(f0, f1))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", LONG, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                           stdout=subprocess.PIPE, bufsize=W * H * 3)
    size = W * H * 3 // 2
    tmp = "renders/short_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}",
                            "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                            "-profile:v", "high", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    need = {}
    for i, f in enumerate(want):
        need.setdefault(f, []).append(i)
    frames_out = [None] * len(want)
    f, nxt = 0, 0
    while nxt < len(want):
        buf = dec.stdout.read(size)
        if len(buf) < size:
            raise RuntimeError(f"the full render ended at frame {f}")
        for i in need.get(f, []):
            frames_out[i] = buf
        while nxt < len(want) and frames_out[nxt] is not None:
            enc.stdin.write(frames_out[nxt])
            frames_out[nxt] = None
            nxt += 1
        f += 1
    dec.kill()
    enc.stdin.close()
    enc.wait()
    for mix, out in (("renders/mix_short.wav", "renders/SHELF_reel_v2_short.mp4"),
                     ("renders/mix_short_nomusic.wav", "renders/SHELF_reel_v2_short_nomusic.mp4")):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out], check=True)
        print("->", out)


if __name__ == "__main__":
    if "--plan" in sys.argv:
        lay, nf = layout()
        mm = music_map(lay)
        print(f"{nf} frames = {nf / FPS:.2f} s")
        for a, b, s0 in mm:
            print(f"  music {a:6.2f}-{b:6.2f}  " + (f"song {s0:7.3f}" if s0 is not None else "(rewind)"))
        for (a, b, s0), (c, d, s1) in zip(mm[2:], mm[3:]):
            print(f"  jump at {c:6.2f}: bar phase {phase(s0 + b - a):.2f} -> {phase(s1):.2f}")
        end_song = mm[-1][2] + (mm[-1][1] - mm[-1][0])
        print(f"  loop: end phase {phase(end_song):.2f}, hook starts at {phase(MU.MAP[0][3]):.2f}")
    else:
        main()
