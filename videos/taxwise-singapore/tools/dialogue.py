"""HK Vinay's voice, kept as recorded: his original stereo audio from the team's reel with only gentle, transparent,
linear processing. No noise reduction, no dereverberation, no exciter, no gating: nothing that can make a voice
sound processed.

  1. a 75 Hz high-pass, 24 dB/oct: desk rumble and the air conditioning's lowest hum;
  2. a mild broadcast EQ: -2 dB at 250 Hz (a little less room box), +2.5 dB presence at 3.5 kHz, +2 dB air
     shelf from 8 kHz;
  3. the room's width narrowed a little (mid/side, side x 0.7): the voice sits centred, the room a touch
     further back. A linear change: in mono it is exactly the original mid.
Levels, a light compressor and the cut onto the timeline happen in tools/mix.py.

When the Adobe Podcast "Enhance Speech" version of his recording is present (renders/src/voice_enhanced.*, made by
the client from renders/deliver/TAXWISE_voice_for_Adobe_Enhance.wav: the room's echo removed), it is used instead:
aligned to the original by cross-correlation (to the sample), trimmed to the same length, and only high-passed at
70 Hz (Adobe has already EQ'd and cleaned it).

v5: when his re-recorded lines are present (renders/src/rerecord_*/take_*.m4a, recorded to the karaoke guide in a
dry room), they replace both. tools/adr.py fits every line onto the original's timing (lip sync, graphics cues).
The lines then get a light, broad EQ, the same for all six:
  - a 75 Hz high-pass;
  - +2.5 dB at 320 Hz: the body a phone mic loses;
  - -2.5 dB at 2.8 kHz: its honk;
  - +3 dB at 5.1 kHz: it fills a notch the phone's mic puts there.
They also get a gentle match to each other: 60% of each line's smoothed difference from the six's average,
at most +-4 dB, 100 Hz-10 kHz. The six lines were recorded minutes apart, with the phone held a little
differently each time. No compression, denoising or gating here; levels and dynamics are tools/mix.py's.

  python3 tools/dialogue.py   ->  renders/audio/dialogue_src.wav (float, stereo, source timeline)
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

SR = 48000
OUT = os.path.join(edl.ROOT, "renders/audio/dialogue_src.wav")


def load_src():
    """The team's reel audio, both channels, as float64 at 48 kHz."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", edl.SRC, "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)


# ---- RBJ biquads ----
def _peak(f0, gain_db, q):
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1, a[1] / a[0], a[2] / a[0]]])


def _shelf(f0, gain_db, high=True, s=0.7):
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    c, sq = np.cos(w), 2 * np.sqrt(A) * al
    if high:
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    else:
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1, a[1] / a[0], a[2] / a[0]]])


CHAIN = np.vstack([butter(4, 75, "highpass", fs=SR, output="sos"),
                   _peak(250, -2.0, 0.9), _peak(3500, 2.5, 0.8), _shelf(8000, 2.0, high=True)])
SIDE = 0.7


def process(x):
    y = sosfilt(CHAIN, x, axis=0)
    mid, side = 0.5 * (y[:, 0] + y[:, 1]), 0.5 * (y[:, 0] - y[:, 1])
    return np.stack([mid + SIDE * side, mid - SIDE * side], 1)


def enhanced_path():
    import glob
    c = sorted(glob.glob(os.path.join(edl.ROOT, "renders/src/voice_enhanced.*")))
    return c[0] if c else None


def load_enhanced(path, ref):
    """The Adobe-enhanced voice at 48 kHz stereo, aligned to the original recording `ref` (N, 2) and trimmed to
    its length. Returns (audio, lag in samples, correlation)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    e = np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)
    a, b = e.mean(1), ref.mean(1)
    n = min(len(a), len(b))
    bp = butter(4, [300, 3400], "bandpass", fs=SR, output="sos")
    fa, fb = sosfilt(bp, a[:n]), sosfilt(bp, b[:n])
    F = np.fft.rfft(fa, 2 * n) * np.conj(np.fft.rfft(fb, 2 * n))
    cc = np.fft.irfft(F)
    lags = np.concatenate([np.arange(0, n), np.arange(-n, 0)])
    win = np.abs(lags) <= int(2.0 * SR)                  # Adobe keeps timing: search +-2 s
    lag = int(lags[win][np.argmax(cc[win])])             # e[t + lag] lines up with ref[t]
    out = np.zeros_like(ref)
    src = e[max(0, lag):]
    dst0 = max(0, -lag)
    m = min(len(src), len(ref) - dst0)
    out[dst0:dst0 + m] = src[:m]
    corr = np.corrcoef(sosfilt(bp, out.mean(1)), sosfilt(bp, ref.mean(1)))[0, 1]
    return out, lag, corr


TAKE_EQ = np.vstack([butter(4, 75, "highpass", fs=SR, output="sos"),
                     _peak(320, 2.5, 0.8), _peak(2800, -2.5, 1.0), _peak(5100, 3.0, 2.0)])
MATCH, MATCH_MAX = 0.6, 4.0
THIRDS = 1000 * 2 ** (np.arange(-10, 11) / 3)            # 100 Hz .. 10 kHz


def third_octaves(x):
    """Third-octave band power (dB) over the speech frames of a line, re its 300-3000 Hz average."""
    import adr
    act = adr.vad(adr.band_level(x))
    f = np.fft.rfftfreq(4096, 1 / SR)
    S, n = np.zeros(len(f)), 0
    for i in range(0, len(x) - 4096, 1024):
        c = (i + 2048) // 480
        if c < len(act) and act[c]:
            S += np.abs(np.fft.rfft(x[i:i + 4096] * np.hanning(4096))) ** 2
            n += 1
    S /= max(n, 1)
    L = np.array([10 * np.log10(S[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-20) for c in THIRDS])
    return L - L[(THIRDS >= 300) & (THIRDS <= 3000)].mean()


def eq_fir(gain_db, taps=4095):
    """Zero-phase FIR from a gain curve at the third-octave centres (log-interpolated, 0 dB outside)."""
    f = np.fft.rfftfreq(taps, 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    g = np.interp(lf, np.log2(THIRDS), gain_db, left=0.0, right=0.0)
    h = np.roll(np.fft.irfft(10 ** (g / 20), n=taps), taps // 2) * np.hanning(taps)
    return h


def rerecorded(ref):
    """His re-recorded lines, fitted to the original's timing (tools/adr.py) and EQ'd, on the source timeline
    (dual mono, same length as `ref`). None when the takes aren't there."""
    import adr
    from scipy.signal import fftconvolve
    paths = adr.take_paths()
    if not paths:
        return None
    guide = adr.guide_track()
    lines = []
    for seg, p in zip(edl.SEGMENTS, paths):
        y, rep, _ = adr.align_line(seg, adr.load_mono(p), guide)
        lines.append((seg, sosfilt(TAKE_EQ, y)))
        offs = [r["off_ms"] for r in rep["anchors"]]
        print(f"  {seg['id']} {os.path.basename(p)}: {len(offs)} anchors, |off| max {max(map(abs, offs))} ms, "
              f"speech untouched {rep['speech_unchanged_pct']}%")
    spec = [third_octaves(y) for _, y in lines]
    mean = np.mean(spec, 0)
    out = np.zeros(len(ref))
    for (seg, y), L in zip(lines, spec):
        dev = np.convolve(np.pad(L - mean, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
        corr = np.clip(-MATCH * dev, -MATCH_MAX, MATCH_MAX)
        corr[[0, -1]] *= 0.5                                  # taper at the band edges
        y = fftconvolve(y, eq_fir(corr), mode="same")
        a = int(round(adr.window(seg)[0] * SR))
        out[a:a + len(y)] += y[:len(out) - a]
        print(f"  {seg['id']} match EQ (dB, 100 Hz-10 kHz in thirds): " + " ".join(f"{v:+.1f}" for v in corr))
    return np.stack([out, out], 1)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ref = load_src()
    p = enhanced_path()
    rr = rerecorded(ref)
    if rr is not None:
        y = rr
        print("using his re-recorded lines (renders/src/rerecord_*), fitted to the reel's timing")
    elif p:
        y, lag, corr = load_enhanced(p, ref)
        y = sosfilt(butter(4, 70, "highpass", fs=SR, output="sos"), y, axis=0)
        print(f"using the Adobe-enhanced voice {os.path.basename(p)}: offset {lag} samples ({lag / SR * 1000:.1f} ms) "
              f"corrected, correlation with the original {corr:.2f}")
    else:
        y = process(ref)
        print("using the original recording (gentle EQ)")
    sf.write(OUT, y.astype(np.float32), SR, subtype="FLOAT")
    print("->", OUT, f"{len(y) / SR:.2f} s, stereo")


if __name__ == "__main__":
    main()
