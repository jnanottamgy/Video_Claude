"""Studio dialogue from the reel's phone-mic track: classical DSP only (no ML separation).

The whole source track is processed once, on the SOURCE timeline; tools/mix.py then cuts the lines out of
it, levels each line and compresses the assembled stem.
  1. mono at 48 kHz (the two channels are the same voice, 0.81 correlated)
  2. high-pass 70 Hz (rumble, desk bumps)
  3. spectral noise reduction per recorded clip (the original edit's clips sit between runs of digital
     silence): noise PSD = each bin's 12th-percentile power over the clip; Wiener-style gain with 2x
     over-subtraction, a -13 dB floor (natural, no "underwater" sound), smoothed across 3 bins and with a
     slow release over time so no musical noise
  3b. late-reverb suppression (the room tail decayed by an estimated T60, subtracted with a floor)
  4. EQ toward a broadcast voice: the phone track is dark and boomy (1.6-3.2 kHz sits 19 dB under the
     100-200 Hz band): -2.5 dB low shelf at 160 Hz (phone proximity boom), -2 dB mud at 230 Hz, -1.5 dB box
     at 600 Hz, +2 dB at 1.4 kHz, +4.5 dB presence at 3.2 kHz, +4 dB air shelf from 8 kHz
  5. de-esser on 5-10 kHz (only where that band jumps above the voice)
  python3 tools/dialogue.py   ->  renders/audio/dialogue_src.wav (float, mono, source timeline)
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, istft, sosfilt, sosfiltfilt, stft

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

SR = 48000
OUT = "renders/audio/dialogue_src.wav"


def load_src():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(edl.ROOT, edl.SRC), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def clips(x):
    """(start, end) samples of each recorded clip: the original edit joined clips with digital silence."""
    hop = SR // 100
    k = len(x) // hop
    rms = np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1))
    dead = rms < 1e-6
    out, start, i = [], None, 0
    while i < k:
        if not dead[i] and start is None:
            start = i
        if dead[i] and start is not None:
            j = i
            while j < k and dead[j]:
                j += 1
            if j - i >= 3 or j == k:                      # >= 30 ms of digital silence ends a clip
                out.append((start * hop, i * hop))
                start = None
            i = j
            continue
        i += 1
    if start is not None:
        out.append((start * hop, len(x)))
    return out


def denoise(x, over=1.6, floor_db=-14.0, pct=12):
    n_fft, hop = 2048, 512
    if len(x) < n_fft * 2:
        return x
    f, t, Z = stft(x, SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary="even", padded=True)
    P = np.abs(Z) ** 2
    N = np.percentile(P, pct, axis=1, keepdims=True) / -np.log(1 - pct / 100)    # a noise bin's power is exponential: unbias
    g = np.clip(1 - over * N / (P + 1e-20), (10 ** (floor_db / 20)) ** 2, 1.0) ** 0.5
    g = (np.roll(g, 1, 0) + g + np.roll(g, -1, 0)) / 3                       # across frequency
    rel = np.exp(-hop / (0.060 * SR))                                         # 60 ms release over time
    for i in range(1, g.shape[1]):
        g[:, i] = np.maximum(g[:, i], g[:, i - 1] * rel)
    _, y = istft(Z * g, SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary=True)
    return y[:len(x)]


def dereverb(x, t60=0.45, delay=0.064, over=1.2, floor_db=-7.0):
    """Late-reverb suppression (Lebart et al.): the late tail at frame t is the power of frame t - delay,
    decayed by the room's T60; subtract it with a gain floor. Makes the phone in a hard-walled office
    sound closer, like a mic on a boom."""
    n_fft, hop = 1024, 256
    if len(x) < n_fft * 4:
        return x
    f, t, Z = stft(x, SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary="even", padded=True)
    P = np.abs(Z) ** 2
    d = max(1, int(round(delay * SR / hop)))
    alpha = 10 ** (-6.0 * delay / t60)                                          # energy decay over `delay`
    Ps = P.copy()
    for i in range(1, P.shape[1]):                                              # a little temporal smoothing
        Ps[:, i] = 0.6 * Ps[:, i - 1] + 0.4 * P[:, i]
    late = np.zeros_like(P)
    late[:, d:] = alpha * Ps[:, :-d]
    g = np.clip(1 - over * late / (P + 1e-20), 10 ** (floor_db / 10), 1.0) ** 0.5
    g = (np.roll(g, 1, 0) + g + np.roll(g, -1, 0)) / 3
    _, y = istft(Z * g, SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary=True)
    return y[:len(x)]


# ---- RBJ biquads ----
def _peak(f0, gain_db, q):
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1, a[1] / a[0], a[2] / a[0]]])


def _shelf(f0, gain_db, high=True, s=0.8):
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


EQ = np.vstack([_shelf(160, -2.5, high=False), _peak(230, -2.0, 0.9), _peak(600, -1.5, 1.3), _peak(1400, 2.0, 0.9),
                _peak(3200, 4.5, 0.8), _shelf(8000, 4.0, high=True)])


def deess(x, lo=5000, hi=10000, thr_db=-9.0, max_red_db=-7.0):
    band = sosfiltfilt(butter(4, [lo, hi], "bandpass", fs=SR, output="sos"), x)
    hop = SR // 200                                                            # 5 ms
    k = len(x) // hop
    eb = np.sqrt((band[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-14)
    ef = np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-14)
    over = 20 * np.log10(eb / ef) - thr_db                                     # band above its usual share
    red = np.clip(-over * 0.7, max_red_db, 0.0)
    g = np.repeat(10 ** (red / 20), hop)
    g = np.concatenate([g, np.ones(len(x) - len(g))])
    g = np.convolve(g, np.ones(96) / 96, "same")                               # 2 ms smoothing
    return x - band + band * g


def bands_report(x, label):
    seg = x[int(20.5 * SR):int(23.3 * SR)]
    f = np.fft.rfftfreq(8192, 1 / SR)
    S = np.mean([np.abs(np.fft.rfft(seg[i:i + 8192] * np.hanning(8192))) ** 2 for i in range(0, len(seg) - 8192, 4096)], axis=0)
    db = 10 * np.log10(S + 1e-20)
    ref = db[(f >= 100) & (f < 200)].mean()
    edges = [100, 200, 400, 800, 1600, 3200, 6400, 10000, 14000]
    print(label, " ".join(f"{a}-{b}:{db[(f >= a) & (f < b)].mean() - ref:+.1f}" for a, b in zip(edges, edges[1:])))


def main():
    os.chdir(edl.ROOT)
    os.makedirs("renders/audio", exist_ok=True)
    x = load_src()
    bands_report(x, "before")
    x = sosfiltfilt(butter(2, 70, "highpass", fs=SR, output="sos"), x)
    y = np.zeros_like(x)
    for a, b in clips(x):
        y[a:b] = dereverb(denoise(x[a:b]))
    y = sosfilt(EQ, y)
    y = deess(y)
    bands_report(y, "after ")
    sf.write(OUT, y.astype(np.float32), SR, subtype="FLOAT")
    print("->", OUT, f"({len(clips(x))} clips denoised)")


if __name__ == "__main__":
    main()
