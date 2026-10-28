"""The soundtrack: the client's "Chanakya" edit audio from its sitar build, plus temple sounds and transitions on
the picture's events.

  python3 tools/mix.py   ->  renders/audio/mix.wav          song + effects, -14 LUFS, -1 dBTP
                             renders/audio/mix_nomusic.wav  the effects alone, at the same gain (for when
                                                            Instagram mutes the song and it is re-added from
                                                            Instagram's own library)
Effects: synthesised bells, aarti bell, ghungroo and shankh (tools/sounds.py, tuned to the song's Sa, D), and
the library (library/sfx: a riser and bass hit into the drop, swells into the intro's dissolves, whooshes on
the whips, the fire bed under the aarti flames).
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
D, B, E = edl.DROP, edl.BASS, edl.END
WHIPS = [s["t"] for s in edl.SHOTS if s["x"] == "whip"]
FLASHES = [s["t"] for s in edl.SHOTS if s["x"] == "flash" and s["t"] < E - 0.01]


def song():
    x, sr = sf.read(edl.SONG, always_2d=True)
    assert sr == SR
    i = int(round(edl.SONG_IN * SR))
    y = x[i:i + N].astype(np.float64)
    if len(y) < N:
        y = np.vstack([y, np.zeros((N - len(y), 2))])
    k = int(0.25 * SR)                                        # it starts inside the sitar's fade-in
    y[:k] *= np.linspace(0, 1, k)[:, None] ** 2
    k = int(0.6 * SR)
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

    sh = edl.SHOTS
    # the opening: a bell struck on frame one, ankle bells under it
    put(fxb, S.mid_bell(seed=2), 0.0, -9); ev("mid bell (D5)", 0.0, -9)
    put(fxb, S.ghungroo(seed=31), 0.0, -17); ev("ghungroo", 0.0, -17)
    # the intro's dissolves: a soft swell into each
    for s in sh[1:3]:
        lib(fxb, "slow-woosh", s["t"], -20); ev("slow-woosh", s["t"], -20)
    # the aarti: the hand bell rung over the flames, and the flames themselves
    aarti = sh[1]
    put(fxb, S.aarti(dur=aarti["end"] - aarti["t"] + 0.3), aarti["t"] - 0.3, -20); ev("aarti hand bell", aarti["t"] - 0.3, -20)
    lib(fxb, "fire", aarti["t"] - 0.35, -16, length=aarti["end"] - aarti["t"] + 0.4, hp=120, fade_in=0.4)
    ev("fire bed", aarti["t"] - 0.35, -16)
    # her name: a small bell as the honorific writes on
    put(fxb, S.ting(seed=4), edl.TEXT[2][0] + 0.05, -15); ev("ting (D6)", edl.TEXT[2][0] + 0.05, -15)
    # the DROP: a riser into it, then the bass hit, the deep bell and the shankh together
    lib(fxb, "build-up-1", D, -19); ev("build-up-1 (ends on the drop)", D, -19)
    lib(fxb, "bass-woosh-2", D, -11, hp=70); ev("bass-woosh-2", D, -11)
    put(fxb, S.big_bell(seed=8), D, -10); ev("big bell (D4)", D, -10)
    put(fxb, S.shankh(seed=5), D + 0.02, -16); ev("shankh (D4)", D + 0.02, -16)
    # flashes of light (the bass coming in among them): a ghungroo shake and a soft swell on the cut
    for k, t in enumerate(FLASHES):
        put(fxb, S.ghungroo(seed=40 + k), t - 0.03, -15); ev("ghungroo", t - 0.03, -15)
        lib(fxb, "slow-woosh", t, -23); ev("slow-woosh", t, -23)
    # whip pans
    for t in WHIPS:
        lib(fxb, "fast-swoosh", t, -16); ev("fast-swoosh", t, -16)
    # the event card: a bell on Pa, a shimmer as the Kannada writes on
    put(fxb, S.bell(S.PA, 4.5, 2.0, seed=7, strike=0.22), edl.TEXT[3][0], -12); ev("bell (A4)", edl.TEXT[3][0], -12)
    put(fxb, S.ghungroo(seed=55, spread=0.5, count=50), edl.TEXT[3][0] + 0.1, -20)
    ev("ghungroo", edl.TEXT[3][0] + 0.1, -20)
    # the end card: the deep bell rings out as the song fades, a small bell on her name, ankle bells on the CTA
    put(fxb, S.big_bell(seed=9), E, -8); ev("big bell (D4)", E, -8)
    lib(fxb, "slow-woosh", E, -16); ev("slow-woosh", E, -16)
    put(fxb, S.ting(seed=12), edl.TEXT[4][0] + 0.1, -16); ev("ting (D6)", edl.TEXT[4][0] + 0.1, -16)
    put(fxb, S.ghungroo(seed=77, spread=0.4), edl.TEXT[4][0] + 1.35, -20); ev("ghungroo", edl.TEXT[4][0] + 1.35, -20)
    k = int(0.5 * SR)
    fxb[-k:] *= np.linspace(1, 0, k)[:, None]
    return fxb, log


def master(src, dst, target=-14.0, ceiling_db=-1.2):
    """Gain to the target loudness, then a 4x-oversampled lookahead limiter for the song's own 0 dBFS peaks
    (latency-compensated, so the picture stays in sync)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i_in = float(r.stderr.rsplit("I:", 1)[1].split("LUFS")[0])
    gain = target - i_in
    lim = 10 ** (ceiling_db / 20)
    af = (f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={lim:.4f}:attack=3:release=80:level=false:latency=true,"
          f"aresample={SR}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-c:a", "pcm_s24le", dst], check=True)
    return i_in, gain


def main():
    os.makedirs(OUT, exist_ok=True)
    music = song()
    fxb, log = effects()
    mix = music + fxb
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    i_in, g = master(raw, os.path.join(OUT, "mix.wav"))
    # the effects alone, at the gain the full mix received
    m = sf.read(os.path.join(OUT, "mix.wav"))[0]
    gain = np.sqrt((m ** 2).mean() / max(1e-12, (mix ** 2).mean()))
    nm = fxb * gain
    peak = np.abs(nm).max()
    if peak > 0.89:
        nm *= 0.89 / peak
    sf.write(os.path.join(OUT, "mix_nomusic.wav"), nm.astype(np.float32), SR, subtype="PCM_24")
    json.dump(log, open(os.path.join(OUT, "sfx_log.json"), "w"), indent=1)
    print(f"mix: input {i_in} LUFS, gain {g:+.2f} dB, limited at -1.2 dBFS; {len(log)} effects; "
          f"samples {N} ({N / SR:.3f} s)")


if __name__ == "__main__":
    main()
