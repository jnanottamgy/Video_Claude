"""REEL 2 soundtrack: the edit audio, untouched, with the sound design under and around it.

  python3 tools/mix_v2.py [-v]   ->  renders/audio/reel2_mix.wav  (-14 LUFS integrated, -1 dBTP: Instagram)

The cars sound the way they move: each rally shot's own engine audio is re-sampled through the shot's time map
(varispeed), so the engine screams up in pitch at full speed, groans down when time drops into slow motion, and
winds down to nothing on the freeze frame. Around it: whooshes that follow every motion transition, impacts on
the 808 hits, slow-motion swells and tape-stops where time slows, data blips and counter ticks under the graphics,
a riser into the drop and a bass sweep into the climax.
"""
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl_v2 as edl  # noqa: E402
import sfx  # noqa: E402
from media import info  # noqa: E402
from mix import REL, hp, limit, rms_db  # noqa: E402

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders/audio")
N = int(round(edl.DURATION * SR))
E = edl
A = edl.AUDIO

# (time, effect, gain dB[, length s]) -- each effect's hit (its loudest moment) lands on its time
CUES = [
    # the intro: the lens catches the sun, the zoom through it, the pull-back, the wind-up
    (0.30, "shine", -17), (1.40, "woosh-4", -17), (1.479, "slow-woosh", -21), (2.178, "woosh-5", -20),
    (2.877, "slow-woosh", -22), (3.62, "riser", -20, 0.7), (4.02, "gun-reload", -21, 0.5), (4.03, "slow-motion", -20),
    # THE DROP: the strike, the shockwave, the first car
    (A["DROP"], "bass-woosh-1", -12), (A["DROP"], "cinematic-electric-hit", -15, 1.6), (A["DROP"] + 0.01, "wind-impact", -18, 1.2),
    (4.44, "slow-motion", -17), (4.46, "nextel", -22), (4.53, "digital-text", -21), (4.56, "counter", -26, 0.35),
    (A["SN1"], "woosh-2", -16), (A["SN1"], "sword-slash-1", -21),
    (5.18, "beat-slowing", -19, 0.5), (5.20, "nextel", -22), (5.27, "digital-text", -21), (5.30, "counter", -26, 0.3),
    (A["B3"], "woosh-3", -16), (A["B3"], "sword-slash-3", -22),
    (5.86, "slow-motion", -18), (5.88, "nextel", -22), (5.95, "digital-text", -21), (5.98, "counter", -26, 0.25),
    # the 808 hit freezes time on car 14
    (A["HIT2"], "lightning-strike", -15, 1.4), (A["HIT2"], "sword-impact", -17, 1.2), (6.27, "slow-motion", -16),
    (6.30, "nextel", -21), (6.37, "digital-text", -20), (6.42, "counter", -25, 0.4), (6.62, "digital-text", -24),
    (6.84, "fast-swoosh", -15), (A["RT"], "woosh-2", -15),
    # into the dust, and the dust becomes cloud
    (7.55, "wind-impact", -18, 1.4), (A["SN2"], "lowpass-woosh", -17), (A["SN2"] + 0.05, "slow-woosh", -22),
    (A["B7"], "slow-woosh", -20),
    # the 808 creeps back: pulled toward the sun
    (A["HIT3"], "bass-woosh-2", -12), (A["HIT3"] - 0.02, "riser", -19, 0.9),
    # the final: headlights, through, the wipe, the freeze
    (9.166, "woosh-3", -20), (A["E1"], "woosh-4", -16), (A["E2"], "woosh-5", -16), (A["E2"] + 0.02, "sword-slash-1", -20),
    (10.04, "beat-slowing", -16, 0.8), (A["E3"], "camera-click", -12), (A["E3"], "old-flash", -15),
    (A["E3"] + 0.01, "sword-impact", -14, 1.0), (10.26, "digital-text", -21), (10.30, "counter", -25, 0.25),
    (A["SN3"], "glitchy-woosh", -16), (A["SN3"], "cinematic-electric-hit", -16, 0.5),
]
LOW_OK = {"bass-woosh-1", "bass-woosh-2"}
REL2 = dict(REL, **{"lightning-strike": -6, "nextel": -12, "gun-reload": -12, "lowpass-woosh": -9})

# the rally shots whose engines follow their time maps: (shot, gain dB, high-pass Hz)
ENGINES = [("V05", -2, 110), ("V06", -2, 110), ("V07", -3, 110), ("V08", 0, 100), ("V09", -5, 120),
           ("V12", -3, 110), ("V13", -5, 120), ("V14", -1, 100)]


def clip_audio(clip, t0, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t0):.3f}", "-t", f"{dur:.3f}", "-i", info(clip)["path"],
                          "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64), max(0.0, t0)


def varispeed(spec, ta, tb):
    """The shot's own audio re-sampled through its time map over output [ta, tb): pitch follows the speed."""
    src = spec["src"]
    f = src if callable(src) else (lambda t: src[0] + (t - spec["t0"]) * src[1])
    ts = np.arange(int(ta * SR), int(tb * SR)) / SR
    ss = np.array([f(t) for t in ts[::48]])                       # the map every millisecond, then interpolated
    ss = np.interp(ts, ts[::48], ss)
    a0, a1 = ss.min() - 0.05, ss.max() + 0.05
    x, start = clip_audio(spec["clip"], a0, a1 - a0)
    pos = (ss - start) * SR
    pos = np.clip(pos, 0, len(x) - 2)
    i = np.floor(pos).astype(int)
    fr = (pos - i)[:, None]
    y = x[i] * (1 - fr) + x[i + 1] * fr
    # where time stands still the audio would hold one sample: fade it to silence with the speed
    sp = np.abs(np.gradient(ss) * SR)
    y *= np.clip(sp / 0.15, 0, 1)[:, None]
    return y


def main():
    os.makedirs(OUT, exist_ok=True)
    song, sr = sf.read(os.path.join(OUT, "reel2.wav"), always_2d=True)
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
        if len(seg) > w:
            e = np.sqrt(np.convolve(seg ** 2, np.ones(w) / w, "valid"))
            own = max(-40.0, 20 * np.log10(e.max() + 1e-9))
        else:
            own = -20.0
        here = max(rms_db(music, t - 0.05, t + 0.3), -38.0)
        gain = min(6.0, here + REL2.get(sid, -9) + (g + 15) * 0.5 - own)
        levels.append((t, sid, round(gain, 1)))
        sfx.place(fx_lo if sid in LOW_OK else fx_hi, sid, t, gain_db=gain, length=length)
    # engines: each rally shot's audio through its own time map, with short fades at its edges
    for sid, g, hpf in ENGINES:
        s = edl.SPECS[sid]
        ta = s["t0"] - 0.04
        tb = s["t1"] + 0.06
        y = varispeed(s, ta, tb)
        y = hp(y, hpf)
        k = int(0.03 * SR)
        y[:k] *= np.linspace(0, 1, k)[:, None]
        y[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))[:, None]
        r = np.sqrt((y ** 2).mean()) + 1e-9
        here = max(rms_db(music, s["t0"], s["t1"]), -38.0)
        y *= 10 ** ((here - 7 + g) / 20) / r
        i = int(ta * SR)
        j = min(N, i + len(y))
        eng[i:j] += y[:j - i]
        levels.append((round(s["t0"], 3), "engine " + sid, round(20 * np.log10(10 ** ((here - 7 + g) / 20) / r), 1)))
    if "-v" in sys.argv:
        for row in levels:
            print(row)
    fx = hp(fx_lo, 60) + hp(fx_hi, 130) + eng
    meter = pyln.Meter(SR)
    trim = (meter.integrated_loudness(music) - 7.0) - meter.integrated_loudness(fx)     # effects 7 LU under the song
    fx *= 10 ** (trim / 20)
    print(f"effects trimmed {trim:+.1f} dB")
    mix = music + fx
    e = int(edl.END * SR)
    mix[e:] *= np.linspace(1, 0, len(mix) - e)[:, None] ** 2
    lufs = meter.integrated_loudness(mix)
    out = limit(mix * 10 ** ((-14.0 - lufs) / 20), -1.0)
    sf.write(os.path.join(OUT, "reel2_mix.wav"), out.astype(np.float32), SR, subtype="FLOAT")
    print(f"mix: song {meter.integrated_loudness(music):.1f} LUFS, effects {meter.integrated_loudness(fx):.1f} LUFS alone, "
          f"in {lufs:.1f} -> {meter.integrated_loudness(out):.1f} LUFS, peak {20 * np.log10(np.abs(out).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
