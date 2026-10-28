"""Synthesised temple sounds, tuned to the song's Sa (edl.SA): brass bells, the aarti hand bell,
ghungroo, and a shankh. All return stereo float64 (N, 2) at 48 kHz, peak-normalised to 1.

  python3 tools/sounds.py OUT_DIR      # write each sound as a wav, plus a spectrogram sheet
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

SR = 48000
SA = edl.SA                       # the song's tonic, in the 4th octave
PA = SA * 1.5

# a brass temple bell's modes: (ratio to the prime, amplitude, decay multiplier)
BELL_MODES = [(0.50, 0.55, 1.6), (1.00, 1.00, 1.0), (1.19, 0.55, 0.85), (1.50, 0.30, 0.70), (2.00, 0.65, 0.60),
              (2.52, 0.30, 0.45), (2.66, 0.25, 0.42), (3.01, 0.22, 0.35), (4.07, 0.16, 0.25), (5.40, 0.10, 0.18),
              (6.72, 0.06, 0.12), (8.18, 0.035, 0.09)]


def _norm(x):
    return x / (np.abs(x).max() + 1e-12)


def bell(f, dur, decay, seed=0, strike=0.22, detune=0.0018, bright=1.0):
    """A struck brass bell: detuned mode pairs (the slow 'wah' of temple bells), a strike transient."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ratio, amp, dm in BELL_MODES:
        fr = f * ratio
        if fr > 15000:
            continue
        env = np.exp(-t / (decay * dm))
        a = amp * (bright if ratio > 2.2 else 1.0)
        split = fr * detune * rng.uniform(0.6, 1.4)
        p1, p2 = rng.uniform(0, 2 * np.pi, 2)
        s1 = np.sin(2 * np.pi * (fr - split / 2) * t + p1)
        s2 = np.sin(2 * np.pi * (fr + split / 2) * t + p2)
        out[:, 0] += a * env * (s1 + 0.8 * s2)
        out[:, 1] += a * env * (0.8 * s1 + s2)
    # strike: a few ms of bright noise
    k = int(0.006 * SR)
    noise = rng.standard_normal((k, 2)) * np.exp(-np.arange(k) / (0.0015 * SR))[:, None]
    noise = np.diff(np.vstack([np.zeros((1, 2)), noise]), axis=0)          # tilt it bright
    out[:k] += noise * strike * np.abs(out).max() * 2
    att = int(0.0015 * SR)
    out[:att] *= np.linspace(0, 1, att)[:, None]
    return _norm(out)


def aarti(dur=2.6, rate=6.0, f=SA * 4, seed=11):
    """The aarti hand bell rung steadily: a small bright bell struck ~6 times a second, swelling and fading."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n + SR, 2))
    voices = [bell(f, 1.0, 0.55, seed=seed + v, strike=0.35, detune=0.003) for v in range(3)]
    t = 0.0
    while t < dur:
        e = np.sin(np.pi * min(1.0, t / dur)) ** 0.6
        v = voices[rng.integers(0, 3)] * rng.uniform(0.55, 1.0) * e
        i = int(t * SR)
        out[i:i + len(v)] += v
        t += 1 / rate * rng.uniform(0.82, 1.18)
    return _norm(out[:n + SR // 2])


def ghungroo(dur=0.5, count=42, spread=0.24, seed=3):
    """A shake of ankle bells: dozens of tiny high jingles, front-loaded, scattered across the stereo field."""
    rng = np.random.default_rng(seed)
    n = int(max(dur, spread + 0.6) * SR)
    out = np.zeros((n, 2))
    for _ in range(count):
        t0 = spread * rng.beta(1.4, 3.0)
        f = rng.uniform(3600, 8800)
        dk = rng.uniform(0.025, 0.085)
        m = int(dk * 6 * SR)
        t = np.arange(m) / SR
        s = np.zeros(m)
        for r, a in ((1.0, 1.0), (1.47 * rng.uniform(0.97, 1.03), 0.5), (2.31 * rng.uniform(0.97, 1.03), 0.3)):
            if f * r < 20000:
                s += a * np.sin(2 * np.pi * f * r * t + rng.uniform(0, 6.28)) * np.exp(-t / (dk / r ** 0.5))
        c = int(0.0006 * SR)
        s[:c] += rng.standard_normal(c) * 0.8
        amp = rng.uniform(0.25, 1.0)
        pan = rng.uniform(-0.8, 0.8)
        i = int(t0 * SR)
        out[i:i + m, 0] += s * amp * (1 - pan) / 2
        out[i:i + m, 1] += s * amp * (1 + pan) / 2
    return _norm(out)


def shankh(f0=SA, dur=2.4, seed=5):
    """A conch call: a scoop up to pitch, a held breathy horn tone with a wavering vibrato, a falling tail."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    cents = -120 * np.exp(-t / 0.09)                                       # the scoop up
    cents += 9 * np.sin(2 * np.pi * 5.1 * t + 0.3) * np.clip((t - 0.35) / 0.4, 0, 1)
    walk = np.cumsum(rng.standard_normal(n)) / np.sqrt(SR) * 6
    cents += walk - np.linspace(0, walk[-1], n)
    cents += -45 * np.clip((t - (dur - 0.45)) / 0.45, 0, 1) ** 2            # the fall at the end
    f = f0 * 2 ** (cents / 1200)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi / 2 * np.clip(t / 0.22, 0, 1)) ** 2
    env *= 1 + 0.12 * np.clip((t - 0.2) / 1.2, 0, 1)
    env *= np.clip((dur - t) / 0.42, 0, 1) ** 1.5
    out = np.zeros(n)
    for h in range(1, 18):
        fh = f0 * h
        if fh > 9000:
            break
        formant = 1 + 2.4 * np.exp(-((fh - 900) / 330) ** 2) + 1.3 * np.exp(-((fh - 2200) / 520) ** 2)
        a = h ** -0.95 * formant
        out += a * env ** (1 + 0.09 * h) * np.sin(h * ph + rng.uniform(0, 6.28))
    # breath: band-passed noise riding the envelope
    from scipy.signal import butter, sosfilt
    sos = butter(2, [700, 3800], btype="band", fs=SR, output="sos")
    out += sosfilt(sos, rng.standard_normal(n)) * env * 0.05 * np.abs(out).max()
    st = np.stack([out, np.roll(out, int(0.0004 * SR))], 1)                # a touch of width
    return _norm(st)


def big_bell(seed=1):
    """The deep temple bell on Sa, ringing ~6 s."""
    return bell(SA, 7.0, 3.2, seed=seed, strike=0.18)


def mid_bell(seed=2):
    return bell(SA * 2, 4.0, 1.8, seed=seed, strike=0.25)


def ting(seed=4):
    return bell(SA * 4, 2.2, 0.8, seed=seed, strike=0.3, detune=0.003)


if __name__ == "__main__":
    import os
    import sys

    import soundfile as sf
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, x in [("big_bell", big_bell()), ("mid_bell", mid_bell()), ("ting", ting()), ("aarti", aarti()),
                    ("ghungroo", ghungroo()), ("shankh", shankh())]:
        sf.write(os.path.join(out, f"{name}.wav"), (x * 0.9).astype(np.float32), SR)
        print(name, f"{len(x) / SR:.2f}s")
