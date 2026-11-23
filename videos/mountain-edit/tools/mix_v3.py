"""REEL 3 soundtrack ("TORE UP"): the edit audio untouched, the sound design under and around it.

  python3 tools/mix_v3.py [-v]   ->  renders/audio/reel3_mix.wav  (-14 LUFS integrated, -1 dBTP: Instagram)

- Engines follow the picture: each car shot's own audio (and the jeep's, winding up into the drop) is re-sampled
  through its time map, so it screams at full speed, groans in slow motion and dies on a freeze.
- Every tear gets a paper rip (synthesised: a crackle of fibres over a torn-noise body, rising as it opens).
- The rewind gets a tape rewind: the last two seconds of the song itself, reversed and sped up, wobbling.
- Library effects on the rest: whooshes on the moves, flashes and shutters on the photos and freezes, impacts on
  the drop and the title slams, lock-on chirps, data bursts and counter ticks under the callouts, a riser into
  the drop, slashes on the pushes, glitches at the end.
"""
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl_v3 as edl  # noqa: E402
import sfx  # noqa: E402
from mix import REL, hp, limit, rms_db  # noqa: E402
from mix_v2 import varispeed  # noqa: E402

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders/audio")
N = int(round(edl.DURATION * SR))
A = edl.AUDIO

LOCK = lambda t: [(t, "nextel", -21), (t + 0.07, "digital-text", -21), (t + 0.12, "counter", -26, 0.35)]
CUES = [
    # the road up
    (0.15, "lowpass-woosh", -22), (1.79, "slow-woosh", -22), (5.10, "woosh-4", -18), (A["P3"], "shine", -18),
    (A["P3"], "cinematic-woosh", -23), *LOCK(7.18), (A["B21"], "camera-click", -12), (A["B21"], "old-flash", -14),
    (A["B29"], "slow-woosh", -21),
    # the build: loading up, the riser into the drop
    (12.78, "gun-reload", -20, 0.5), (12.80, "slow-motion", -20), (A["DROP"] - 0.01, "riser", -19, 1.4),
    # the drop
    (A["DROP"], "bass-woosh-1", -12), (A["DROP"], "cinematic-electric-hit", -15, 1.6), (A["DROP"] + 0.01, "wind-impact", -19, 1.2),
    (14.0, "slow-motion", -16), *LOCK(14.06), (A["S1"], "sword-impact", -19, 0.9), (15.6, "fast-swoosh", -16),
    (A["S2"], "woosh-2", -16), (A["S2"], "sword-slash-1", -21), (16.52, "slow-motion", -18), *LOCK(16.56), (17.42, "fast-swoosh", -17),
    (A["S3"], "woosh-3", -16), (A["S3"], "sword-slash-3", -22), (18.17, "camera-click", -15), (18.17, "beat-slowing", -18, 0.5),
    *LOCK(18.2), (18.99, "fast-swoosh", -18),
    (A["S4"], "woosh-2", -17), (A["S4"], "sword-slash-1", -22), (19.89, "slow-motion", -18), *LOCK(19.93), (20.74, "fast-swoosh", -17),
    # the triptych lands panel by panel
    (A["S5"], "woosh-5", -17), (A["S5"] + 0.04, "digital-text", -21), (A["N5a"], "woosh-5", -17), (A["N5a"] + 0.04, "digital-text", -21),
    (A["N5b"], "woosh-5", -17), (A["N5b"] + 0.04, "digital-text", -21),
    # headlights, the whip, the teal drift
    (A["S6"], "old-flash", -16), (A["S6"], "woosh-3", -18), (23.55, "slow-motion", -18), (23.56, "shine", -18),
    (24.16, "fast-swoosh", -16), (A["S7"], "cinematic-woosh", -18), (24.95, "slow-motion", -18), *LOCK(25.0), (25.86, "fast-swoosh", -17),
    # the rewind, the freeze and the title torn in two
    (A["S8"], "glitchy-woosh", -18), (A["S8"], "alien-digital-glitch", -22, 0.8), (A["GL"], "camera-click", -12),
    (A["GL"], "sword-impact", -14, 1.2), (A["GL"], "old-flash", -16), (A["GL"] + 0.07, "sword-slash-3", -20),
    # the second section
    (A["DROPB"], "bass-woosh-2", -16), (A["Q1"], "camera-click", -12), (A["Q1"], "old-flash", -14),
    (A["Q2"], "camera-click", -12), (A["Q2"], "old-flash", -14),
    (A["ROLL"], "sword-slash-2", -18), *[(t, "camera-click", -19, 0.3) for t in (32.928, 33.139, 33.349, 33.56, 33.765, 33.867)],
    (A["R2"], "cinematic-woosh", -18), (A["R2"], "wind-impact", -20, 1.2),
    (A["PB3"], "sword-impact", -14, 1.4), (A["PB3"], "cinematic-electric-hit", -16, 1.4),
    (A["L1"], "glitchy-woosh", -18), (A["L2"], "alien-digital-glitch", -20, 0.35),
]
LOW_OK = {"bass-woosh-1", "bass-woosh-2"}
REL3 = dict(REL, **{"lightning-strike": -6, "nextel": -12, "gun-reload": -12, "lowpass-woosh": -9})

ENGINES = [("T08", -4, 120), ("T09", 0, 100), ("T10", -2, 110), ("T11", -2, 110), ("T12", -3, 110), ("T14", -3, 110),
           ("T15", -1, 100)]
TEARS = [(A["P2"], -2, 1), (A["P4"], -2, 2), (A["DROPB"], 0, 3), (A["PB2"], -2, 4)]


def paper_tear(dur=0.5, seed=0):
    """A paper rip: fibre crackle over a torn-noise body, swelling then fading, the crackle brightening."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.clip(t / 0.03, 0, 1) * np.exp(-np.clip(t - 0.08, 0, None) / (dur * 0.35))
    noise = rng.standard_normal(n)
    crack = (rng.random(n) < 0.035 * env) * (0.4 + rng.random(n)) * 6
    crack = np.convolve(crack, np.exp(-np.arange(40) / 6), "same")
    hi = sosfilt(butter(2, [1200, 9000], "bandpass", fs=SR, output="sos"), noise * crack + noise * env * 0.25)
    body = sosfilt(butter(2, [180, 900], "bandpass", fs=SR, output="sos"), rng.standard_normal(n)) * env * 0.9
    y = hi + body
    y /= np.abs(y).max() + 1e-9
    return np.stack([y, np.roll(y, 37)], 1)


def tape_rewind(music, t0, t1):
    """The song's last two seconds before t0, reversed, sped up 2.3x and wobbling, cut to fit [t0, t1)."""
    a = max(0, int((t0 - 2.3) * SR))
    seg = music[a:int(t0 * SR)][::-1]
    fast = resample_poly(seg, 10, 23, axis=0)
    n = int((t1 - t0) * SR)
    fast = fast[:n]
    k = np.arange(len(fast))
    wob = 1 + 0.25 * np.sin(2 * np.pi * 9 * k / SR)
    y = sosfilt(butter(2, [250, 6000], "bandpass", fs=SR, output="sos"), fast, axis=0) * wob[:, None]
    f = int(0.03 * SR)
    y[:f] *= np.linspace(0, 1, f)[:, None]
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    return y


def main():
    os.makedirs(OUT, exist_ok=True)
    song, sr = sf.read(os.path.join(OUT, "reel3.wav"), always_2d=True)
    assert sr == SR
    music = np.zeros((N, 2))
    music[:min(N, len(song))] = song[:N]
    fx_lo, fx_hi, eng = np.zeros((N, 2)), np.zeros((N, 2)), np.zeros((N, 2))
    levels = []
    for c in CUES:
        t, sid, g = c[:3]
        length = c[3] if len(c) > 3 else None
        x, hit = sfx.load(sid, SR)
        seg = x[max(0, int((hit - 0.35) * SR)):int((hit + 0.3) * SR)].mean(1)
        w = int(0.05 * SR)
        own = max(-40.0, 20 * np.log10(np.sqrt(np.convolve(seg ** 2, np.ones(w) / w, "valid")).max() + 1e-9)) if len(seg) > w else -20.0
        here = max(rms_db(music, t - 0.05, t + 0.3), -38.0)
        gain = min(6.0, here + REL3.get(sid, -9) + (g + 15) * 0.5 - own)
        levels.append((round(t, 3), sid, round(gain, 1)))
        sfx.place(fx_lo if sid in LOW_OK else fx_hi, sid, t, gain_db=gain, length=length)
    for t, g, seed in TEARS:                                   # paper rips, peaking just after each tear opens
        y = paper_tear(0.5, seed)
        here = max(rms_db(music, t, t + 0.4), -38.0)
        y *= 10 ** ((here - 4 + g) / 20) / (np.sqrt((y ** 2).mean()) + 1e-9)
        i = int((t - 0.02) * SR)
        fx_hi[i:i + len(y)] += y[:max(0, min(len(y), N - i))]
        levels.append((round(t, 3), "paper tear", g))
    rw = tape_rewind(music, A["S8"], A["GL"])
    here = max(rms_db(music, A["S8"], A["GL"]), -38.0)
    rw *= 10 ** ((here - 6) / 20) / (np.sqrt((rw ** 2).mean()) + 1e-9)
    i = int(A["S8"] * SR)
    fx_hi[i:i + len(rw)] += rw[:N - i]
    for sid, g, hpf in ENGINES:
        s = edl.SPECS[sid]
        ta, tb = s["t0"] - 0.04, s["t1"] + 0.06
        y = hp(varispeed(s, ta, tb), hpf)
        k = int(0.03 * SR)
        y[:k] *= np.linspace(0, 1, k)[:, None]
        y[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))[:, None]
        r = np.sqrt((y ** 2).mean()) + 1e-9
        here = max(rms_db(music, s["t0"], s["t1"]), -38.0)
        y *= 10 ** ((here - 7 + g) / 20) / r
        i = int(ta * SR)
        j = min(N, i + len(y))
        eng[i:j] += y[:j - i]
        levels.append((round(s["t0"], 3), "engine " + sid, g))
    if "-v" in sys.argv:
        for row in levels:
            print(row)
    fx = hp(fx_lo, 60) + hp(fx_hi, 130) + eng
    meter = pyln.Meter(SR)
    trim = (meter.integrated_loudness(music) - 7.0) - meter.integrated_loudness(fx)      # effects 7 LU under the song
    fx *= 10 ** (trim / 20)
    print(f"effects trimmed {trim:+.1f} dB")
    mix = music + fx
    e = int(edl.END * SR)
    mix[e:] *= np.linspace(1, 0, len(mix) - e)[:, None] ** 2
    lufs = meter.integrated_loudness(mix)
    out = limit(mix * 10 ** ((-14.0 - lufs) / 20), -1.0)
    sf.write(os.path.join(OUT, "reel3_mix.wav"), out.astype(np.float32), SR, subtype="FLOAT")
    print(f"mix: song {meter.integrated_loudness(music):.1f} LUFS, effects {meter.integrated_loudness(fx):.1f} LUFS alone, "
          f"in {lufs:.1f} -> {meter.integrated_loudness(out):.1f} LUFS, peak {20 * np.log10(np.abs(out).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
