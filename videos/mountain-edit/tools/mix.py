"""The soundtrack: the edit audio, untouched, with sound design laid under and around it.

  python3 tools/mix.py   ->  renders/audio/mix.wav  (-14 LUFS integrated, -1 dBTP: Instagram)

The song carries the low end. The effects live mostly above it: whooshes on whips and cuts, flash pops and
shutter clicks on the flashes, glitches on the inverts and the Matrix, HUD beeps on the target locks, slashes on
the word slams, risers into the drops, a tape stop on the bass cut, and the real engine pass-bys from the rally
clips under drop 1. Everything except the two drop hits is high-passed at 140 Hz so nothing fights the 808.
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
import edl  # noqa: E402
import sfx  # noqa: E402
from media import info  # noqa: E402

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders/audio")
N = int(round(edl.DURATION * SR))
D1, D2, T = edl.D1, edl.D2, edl.T

# (time, effect, gain dB[, length s]) -- the hit point of each effect lands on its time
CUES = [
    # cold open: the HUD wakes up
    (0.15, "digital-text", -24), (0.55, "counter", -27, 0.4),
    # the intro words
    (0.951, "old-flash", -16), (1.15, "radio-beep", -27, 0.5), (1.84, "fast-swoosh", -20),
    (2.70, "radio-beep", -28, 0.4), (3.10, "digital-text", -24), (3.28, "cinematic-electric-hit", -17, 1.6),
    # the broadcast
    (4.412, "radio-switch", -15), (4.42, "alien-digital-glitch", -24, 0.35), (5.70, "radio-switch", -23), (6.90, "radio-switch", -23),
    (8.200, "cinematic-woosh", -17), (9.68, "woosh-3", -20),
    # the mirror-selfie flash
    (10.149, "camera-click", -13), (10.16, "old-flash", -15),
    (12.40, "shine", -19), (12.88, "slow-woosh", -22),
    # money and power, the stutter build
    (13.76, "sword-impact", -19, 0.9), (14.08, "sword-impact", -17, 0.9), (13.93, "fast-swoosh", -25),
    (14.26, "old-flash", -16), (14.45, "fast-swoosh", -25), (14.60, "fast-swoosh", -26), (14.72, "fast-swoosh", -26),
    (14.84, "fast-swoosh", -26), (14.94, "camera-click", -20), (D1, "build-up-1", -17),
    # drop 1
    (D1, "bass-woosh-1", -14), (D1, "cinematic-electric-hit", -16, 2.2), (16.20, "woosh-2", -15),
    (16.96, "fast-swoosh", -17), (17.76, "sword-slash-3", -20), (18.32, "sword-slash-1", -18),
    (19.28, "sword-impact", -15, 1.2), (20.64, "woosh-1", -17), (20.64, "sword-slash-1", -19), (20.88, "sword-slash-3", -19),
    (21.36, "sword-slash-1", -19), (21.52, "sword-impact", -16, 1.0),
    (22.56, "alien-digital-glitch", -15, 0.5), (22.58, "glitchy-woosh", -17), (23.44, "cinematic-electric-hit", -15, 1.2),
    (23.90, "woosh-4", -21), (24.32, "night-vision", -17), (24.70, "digital-text", -22), (25.05, "digital-text", -23),
    (25.52, "alien-digital-glitch", -13, 0.6), (25.92, "fast-swoosh", -21), (26.38, "woosh-3", -21), (26.84, "fast-swoosh", -22),
    (27.07, "woosh-5", -21), (27.30, "fast-swoosh", -22),
    # stackin' up the footage: a shutter per tile
    *[(27.52 + n * edl.BEAT / 4, "camera-click", -21, 0.3) for n in range(9)], (27.52, "counter", -24, 0.9),
    # the break
    (28.482, "beat-slowing", -13), (28.50, "slow-motion", -16), (29.62, "digital-text", -20), (D2, "riser", -18),
    # drop 2
    (D2, "bass-woosh-1", -14), (D2, "wind-impact", -16), (31.28, "fast-swoosh", -19), (31.52, "sword-slash-3", -23),
    (32.16, "shine", -13), (32.56, "shine", -17), (33.04, "woosh-3", -19), (33.92, "slow-woosh", -22),
    (34.88, "cinematic-woosh", -17), (35.84, "woosh-4", -21), (36.72, "wind-impact", -20), (38.70, "radio-beep", -22, 0.5),
    # paparazzi, cameras
    (39.84, "camera-click", -12), (40.00, "camera-click", -13), (40.16, "camera-click", -12), (40.32, "camera-click", -13),
    (39.85, "old-flash", -17), (40.17, "old-flash", -17), (40.48, "camera-click", -12), (40.49, "old-flash", -15),
    (40.96, "camera-click", -12), (40.97, "old-flash", -15),
    # the montage
    (T(58), "woosh-1", -19), (T(60), "woosh-2", -19), (T(62), "woosh-5", -19), (T(64), "woosh-3", -19),
    # the slide and the outro
    (T(66), "bass-woosh-2", -14), (T(66), "slow-motion", -18), (46.40, "radio-beep", -20, 0.5), (46.83, "slow-woosh", -20),
    (47.00, "radio-beep", -24, 0.5), (49.04, "sword-impact", -15, 1.2), (49.68, "cinematic-electric-hit", -14, 1.0),
    (49.70, "shine", -17), (50.24, "old-flash", -15),
]
LOW_OK = {"bass-woosh-1", "bass-woosh-2"}     # the drop hits keep a little low end (high-passed at 70 Hz)

# real engine pass-bys from the rally clips: (clip, source seconds, where that source moment lands, gain, length)
ENGINES = [("0397", 3.55, 15.187 + (4.10 - 3.70) / 0.85, 4.10, -17, 1.3),
           ("0465", 5.70, 16.96 + (6.17 - 5.90), 6.17, -18, 1.0),
           ("0467", 6.05, 18.80, 6.05, -19, 0.9),
           ("0461", 9.70, 19.52 + (10.17 - 9.90) / 0.5, 10.17, -19, 1.1),
           ("0396", 4.30, 22.56 + (4.58 - 4.30) / 0.5, 4.58, -19, 0.9)]


def hp(x, f):
    sos = butter(2, f, "highpass", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0)


def clip_audio(clip, t0, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", info(clip)["path"], "-vn",
                          "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def limit(x, ceiling_db=-1.0, look=0.002, rel=0.08):
    """A 4x-oversampled peak limiter (smooth gain, lookahead)."""
    from scipy.ndimage import minimum_filter1d
    from scipy.signal import resample_poly
    up = resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(1)
    c = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    L = int(look * SR * 4)
    g = minimum_filter1d(need, 2 * L + 1)
    a = np.exp(-1 / (rel * SR * 4))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
        out[i] = cur
    return resample_poly(up * out[:, None], 1, 4, axis=0)[:len(x)]


# where each effect sits against the song's short-term level at its moment (dB); a cue's own gain adjusts it
REL = {"bass-woosh-1": -3, "bass-woosh-2": -4, "cinematic-electric-hit": -6, "sword-impact": -6, "wind-impact": -7,
       "old-flash": -6, "camera-click": -5, "sword-slash-1": -6, "sword-slash-3": -6, "sword-slash-2": -6,
       "woosh-1": -8, "woosh-2": -8, "woosh-3": -8, "woosh-4": -9, "woosh-5": -8, "fast-swoosh": -8, "slow-woosh": -10,
       "cinematic-woosh": -8, "glitchy-woosh": -8, "alien-digital-glitch": -8, "radio-switch": -8, "night-vision": -9,
       "digital-text": -10, "counter": -14, "radio-beep": -13, "shine": -8, "build-up-1": -9, "riser": -10,
       "beat-slowing": -6, "slow-motion": -9}


def rms_db(x, a, b):
    seg = x[max(0, int(a * SR)):max(0, int(b * SR))]
    if len(seg) == 0:
        return -80.0
    return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)


def main():
    os.makedirs(OUT, exist_ok=True)
    song, sr = sf.read(os.path.join(OUT, "dna.wav"), always_2d=True)
    assert sr == SR
    music = np.zeros((N, 2))
    music[:min(N, len(song))] = song[:N]
    fx_lo = np.zeros((N, 2))
    fx_hi = np.zeros((N, 2))
    levels = []
    for c in CUES:
        t, sid, g = c[:3]
        length = c[3] if len(c) > 3 else None
        x, hit = sfx.load(sid, SR)
        seg = x[max(0, int((hit - 0.35) * SR)):int((hit + 0.3) * SR)].mean(1)
        w = int(0.05 * SR)
        if len(seg) > w:
            e = np.sqrt(np.convolve(seg ** 2, np.ones(w) / w, "valid"))
            own = max(-40.0, 20 * np.log10(e.max() + 1e-9))          # its loudest 50 ms
        else:
            own = -20.0
        here = max(rms_db(music, t - 0.05, t + 0.3), -45.0)       # the song's level where the effect lands
        adj = g + 15                                           # the cue's own gain, re-centred: -15 is neutral
        gain = min(6.0, here + REL.get(sid, -9) + adj * 0.5 - own)
        levels.append((t, sid, round(gain, 1)))
        sfx.place(fx_lo if sid in LOW_OK else fx_hi, sid, t, gain_db=gain, length=length)
    if "-v" in sys.argv:
        for row in levels:
            print(row)
    for clip, s0, land, peak_src, g, dur in ENGINES:
        x = clip_audio(clip, s0, dur + 0.6)
        x = x / (np.abs(x).max() + 1e-9)
        k = int(0.08 * SR)
        x[:k] *= np.linspace(0, 1, k)[:, None]
        x[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))[:, None]
        here = max(rms_db(music, land - 0.2, land + 0.3), -45.0)
        g = here - 8 + (g + 18) * 0.5 - 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
        i = int(round((land - (peak_src - s0)) * SR))
        j = min(N, i + len(x))
        if j > i:
            fx_hi[max(0, i):j] += x[max(0, -i):j - i] * 10 ** (g / 20)
    fx = hp(fx_lo, 70) + hp(fx_hi, 140)
    meter = pyln.Meter(SR)
    trim = (meter.integrated_loudness(music) - 11.0) - meter.integrated_loudness(fx)   # effects 11 LU under the song
    fx *= 10 ** (trim / 20)
    print(f"effects trimmed {trim:+.1f} dB")
    mix = music + fx
    # the picture goes black at END: the tail after the song's last word fades out quickly
    e = int(edl.END * SR)
    mix[e:] *= np.linspace(1, 0, len(mix) - e)[:, None] ** 2
    lufs = meter.integrated_loudness(mix)
    g = 10 ** ((-14.0 - lufs) / 20)
    out = limit(mix * g, -1.0)
    sf.write(os.path.join(OUT, "mix.wav"), out.astype(np.float32), SR, subtype="FLOAT")
    print(f"mix: song {meter.integrated_loudness(music):.1f} LUFS, effects {meter.integrated_loudness(fx):.1f} LUFS alone, "
          f"in {lufs:.1f} -> {meter.integrated_loudness(out):.1f} LUFS, peak {20 * np.log10(np.abs(out).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
