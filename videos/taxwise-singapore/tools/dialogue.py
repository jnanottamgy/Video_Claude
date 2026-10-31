"""Studio dialogue for HK Vinay from the reel's two phone-mic channels: classical DSP only (no ML separation).

The whole source track is processed once, on the SOURCE timeline; tools/mix.py cuts the lines out of it,
levels each line and compresses the assembled stem.
  1. a band-split mono:
     - below 1.5 kHz, the average of both channels after aligning R to L (4 samples), for +3 dB SNR;
     - above 1.5 kHz, the left channel only. The two capsules are only ~0.7 correlated up there, and summing
       them comb-filters the presence away.
  2. high-pass 80 Hz, 24 dB/oct: the air conditioning hums at 58-94 Hz.
  3. spectral noise reduction per recorded take (the original edit's shots): noise PSD = each bin's
     12th-percentile power over the take; Wiener-style gain with over-subtraction, a -14 dB floor (natural, no
     "underwater" sound), smoothed across 3 bins and with a 60 ms release so no musical noise.
  4. late-reverb suppression: the office tail decayed by an estimated T60, subtracted with a floor.
  5. EQ toward a broadcast voice (below), then a de-esser on 5-10 kHz (only where that band jumps above the
     voice).
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
OUT = os.path.join(edl.ROOT, "renders/audio/dialogue_src.wav")
TAKES = [0.0, 7.87, 17.30, 30.23, 40.83, 48.93]          # the original edit's shot changes (source seconds)


def load_src():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", edl.SRC, "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)
    L, R = x[:, 0], np.roll(x[:, 1], -4)
    lp = butter(4, 1500, "lowpass", fs=SR, output="sos")
    low = sosfiltfilt(lp, 0.5 * (L + R))
    high = L - sosfiltfilt(lp, L)
    return low + high


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


# toward a broadcast voice: this track is dark and a little boxy (1.6-3.2 kHz sits 8 dB, 3.2-6.4 kHz 24 dB under
# the 100-200 Hz band; 200-800 Hz is +1 to +3 dB): trim the box, open the presence and the air
EQ = np.vstack([_peak(120, 1.0, 0.9), _peak(380, -3.0, 1.0), _peak(900, -1.0, 1.2), _peak(2800, 5.0, 0.8),
                _shelf(5200, 8.0, high=True), _shelf(11000, 3.5, high=True)])


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
    seg = x[int(19.2 * SR):int(29.5 * SR)]
    f = np.fft.rfftfreq(8192, 1 / SR)
    S = np.mean([np.abs(np.fft.rfft(seg[i:i + 8192] * np.hanning(8192))) ** 2 for i in range(0, len(seg) - 8192, 4096)], axis=0)
    db = 10 * np.log10(S + 1e-20)
    ref = db[(f >= 100) & (f < 200)].mean()
    edges = [60, 100, 200, 400, 800, 1600, 3200, 6400, 10000, 14000]
    print(label, " ".join(f"{a}-{b}:{db[(f >= a) & (f < b)].mean() - ref:+.1f}" for a, b in zip(edges, edges[1:])))


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    x = load_src()
    bands_report(x, "before")
    x = sosfiltfilt(butter(4, 80, "highpass", fs=SR, output="sos"), x)
    y = np.zeros_like(x)
    bounds = [int(t * SR) for t in TAKES] + [len(x)]
    for a, b in zip(bounds, bounds[1:]):
        y[a:b] = dereverb(denoise(x[a:b]))
    y = sosfilt(EQ, y)
    y = deess(y)
    bands_report(y, "after ")
    sf.write(OUT, y.astype(np.float32), SR, subtype="FLOAT")
    print("->", OUT)


if __name__ == "__main__":
    main()
