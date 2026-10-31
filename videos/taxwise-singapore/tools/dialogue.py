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


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ref = load_src()
    p = enhanced_path()
    if p:
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
