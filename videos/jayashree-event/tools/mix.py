"""The soundtrack: the song's 65 s instrumental window, plus temple sounds and transitions on the picture's events.

  python3 tools/mix.py   ->  renders/audio/mix.wav          song + effects, -14 LUFS, -1 dBTP
                             renders/audio/mix_nomusic.wav  the effects alone, at the same gain (for when
                                                            Instagram mutes the song and it is re-added from
                                                            Instagram's own library)
Effects: synthesised bells, aarti bell, ghungroo and shankh (tools/sounds.py, tuned to the song's C#), and the
library (library/sfx: whooshes on the whips, the slow-motion swell into the breath, the build and bass hit
into the drop, the fire bed under the aarti flames).
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl  # noqa: E402
import sfx  # noqa: E402
import sounds as S  # noqa: E402

SR = 48000
OUT = os.path.join(edl.ROOT, "renders/audio")
N = int(round(edl.DURATION * SR))
b = edl.b
WHIPS = [s["t"] for s in edl.SHOTS if s["x"] == "whip"]
FLASHES = [s["t"] for s in edl.SHOTS if s["x"] == "flash" and s["t"] < edl.STOP - 0.01]


def song():
    x, sr = sf.read(os.path.join(edl.ROOT, "renders/analysis/song.wav"), always_2d=True)
    assert sr == SR
    i = int(round(edl.SONG_IN * SR))
    y = x[i:i + N].astype(np.float64)
    y[:int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
    k = int(1.6 * SR)
    y[-k:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
    return y


def put(buf, x, t, gain_db, hit=0.0, hp=None):
    """Mix x (N, 2) into buf so that x's sample at `hit` s lands on reel time t."""
    if hp:
        x = sosfilt(butter(2, hp, btype="high", fs=SR, output="sos"), x, axis=0)
    i = int(round((t - hit) * SR))
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[:j - i] * 10 ** (gain_db / 20)


def lib(buf, sfx_id, t, gain_db, length=None, hp=60, fade_in=0.0):
    x, hit = sfx.load(sfx_id, SR)
    if length:
        x = x[:int((hit + length) * SR)].copy()
        k = min(len(x), int(0.25 * SR))
        x[-k:] *= np.linspace(1, 0, k)[:, None]
    if fade_in:
        k = int(fade_in * SR)
        x[:k] *= np.linspace(0, 1, k)[:, None]
    put(buf, x, t, gain_db, hit=hit, hp=hp)


def effects():
    fxb = np.zeros((N, 2))
    log = []

    def ev(name, t, g):
        log.append(dict(t=round(t, 3), sfx=name, gain_db=g))

    # the opening: a bell struck on frame one, ankle bells under it
    put(fxb, S.mid_bell(seed=2), 0.0, -9); ev("mid bell (C#5)", 0.0, -9)
    put(fxb, S.ghungroo(seed=31), 0.0, -17); ev("ghungroo", 0.0, -17)
    # flashes of light: a ghungroo shake and a soft swell on the cut
    for k, t in enumerate(FLASHES):
        put(fxb, S.ghungroo(seed=40 + k), t - 0.03, -14); ev("ghungroo", t - 0.03, -14)
        lib(fxb, "slow-woosh", t, -21); ev("slow-woosh", t, -21)
    # whip pans
    for t in WHIPS:
        name = "woosh-3" if t < edl.DROP2 else "fast-swoosh"
        lib(fxb, name, t, -15); ev(name, t, -15)
    # the name appears: a small bell
    put(fxb, S.ting(seed=4), edl.TEXT[1][0] + 0.12, -17); ev("ting (C#6)", edl.TEXT[1][0] + 0.12, -17)
    # BREATH: the drums drop out, time slows, the deep bell
    lib(fxb, "slow-motion", edl.BREATH, -10, hp=40); ev("slow-motion swell", edl.BREATH, -10)
    put(fxb, S.big_bell(seed=1), edl.BREATH, -8.5); ev("big bell (C#4)", edl.BREATH, -8.5)
    # the aarti: the hand bell rung over the flames, and the flames themselves
    aarti = [s for s in edl.SHOTS if s["clip"] == "3393" and s["speed"] < 1][0]
    put(fxb, S.aarti(dur=aarti["end"] - aarti["t"]), aarti["t"] - 0.25, -19); ev("aarti hand bell", aarti["t"] - 0.25, -19)
    lib(fxb, "fire", aarti["t"] - 0.3, -15, length=aarti["end"] - aarti["t"] + 0.2, hp=120, fade_in=0.5)
    ev("fire bed", aarti["t"] - 0.3, -15)
    # the idols and the event's name: a bell on Pa, a shimmer as the Kannada writes on
    idols = [s for s in edl.SHOTS if s["clip"] == "3387" and s["speed"] < 1][0]
    put(fxb, S.bell(S.PA, 4.5, 2.0, seed=7, strike=0.22), idols["t"], -10); ev("bell (G#4)", idols["t"], -10)
    put(fxb, S.ghungroo(seed=55, spread=0.5, count=50), edl.TEXT[3][0], -19); ev("ghungroo", edl.TEXT[3][0], -19)
    # DROP 2: the build, the bass hit, the shankh and the deep bell together
    lib(fxb, "build-up-2", edl.DROP2, -17); ev("build-up-2 (ends on the drop)", edl.DROP2, -17)
    lib(fxb, "bass-woosh-2", edl.DROP2, -11, hp=70); ev("bass-woosh-2", edl.DROP2, -11)
    put(fxb, S.big_bell(seed=8), edl.DROP2, -11); ev("big bell (C#4)", edl.DROP2, -11)
    put(fxb, S.shankh(seed=5), edl.DROP2 + 0.02, -16.5); ev("shankh (C#4)", edl.DROP2 + 0.02, -16.5)
    # the rhythm stops: the deep bell rings out under the end card
    put(fxb, S.big_bell(seed=9), edl.STOP, -7); ev("big bell (C#4)", edl.STOP, -7)
    lib(fxb, "slow-woosh", edl.STOP, -15); ev("slow-woosh", edl.STOP, -15)
    put(fxb, S.ting(seed=12), edl.TEXT[4][0] + 0.1, -16); ev("ting (C#6)", edl.TEXT[4][0] + 0.1, -16)
    # a closing ankle-bell shimmer under "follow for more"
    put(fxb, S.ghungroo(seed=77, spread=0.4), edl.TEXT[4][0] + 1.35, -20); ev("ghungroo", edl.TEXT[4][0] + 1.35, -20)
    k = int(0.4 * SR)
    fxb[-k:] *= np.linspace(1, 0, k)[:, None]
    return fxb, log


def loudnorm(src, dst, target=-14.0, tp=-1.0):
    """Two-pass EBU R128 normalisation with ffmpeg (linear gain when possible)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", dst],
                   check=True)
    return j


def main():
    os.makedirs(OUT, exist_ok=True)
    music = song()
    fxb, log = effects()
    mix = music + fxb
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    j = loudnorm(raw, os.path.join(OUT, "mix.wav"))
    # the effects alone, at the gain the full mix received
    m = sf.read(os.path.join(OUT, "mix.wav"))[0]
    gain = np.sqrt((m ** 2).mean() / max(1e-12, (mix ** 2).mean()))
    nm = fxb * gain
    peak = np.abs(nm).max()
    if peak > 0.89:
        nm *= 0.89 / peak
    sf.write(os.path.join(OUT, "mix_nomusic.wav"), nm.astype(np.float32), SR, subtype="PCM_24")
    json.dump(log, open(os.path.join(OUT, "sfx_log.json"), "w"), indent=1)
    print(f"mix: input {j['input_i']} LUFS -> -14; {len(log)} effects; samples {N} ({N / SR:.3f} s)")


if __name__ == "__main__":
    main()
