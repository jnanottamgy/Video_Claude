"""Studio dialogue for HK Vinay from the reel's two phone-mic channels: classical DSP only (no ML).

The recording is a phone about a metre away in a hard-walled office: roomy (the voice only ~10 dB down
100 ms after a phrase ends) and dark (almost nothing above 5 kHz). The whole source track is processed once,
on the SOURCE timeline; tools/mix.py cuts the lines out of it and levels them.
  1. both channels high-passed at 80 Hz, 24 dB/oct (the air conditioning hums at 58-94 Hz), R aligned to L.
  2. dereverberation by WPE (weighted prediction error: multichannel linear prediction in the STFT domain,
     the standard classical method, no trained model), per recorded take. For every frequency, the room's
     reverberation is predicted from the past 16-304 ms of BOTH mics' signal, weighted by the inverse power
     of the dry voice (re-estimated over 5 iterations), and subtracted. The direct sound and the first 16 ms
     stay, so the voice keeps its body.
  3. a band-split mono: below 1.5 kHz the average of both (dereverberated) channels; above, the left only
     (the capsules are ~0.7 correlated up there and summing them comb-filters the presence away).
  4. spectral noise reduction per take (12th-percentile noise floor, Wiener gain with a -14 dB floor, 3-bin
     smoothing, a short 40 ms release), then a residual late-reverb suppression (T60 0.7 s, -11 dB floor).
  5. EQ toward a broadcast voice, a harmonic exciter (the 1.8-4.5 kHz band, envelope-normalised, soft-clipped:
     its new 5-12 kHz harmonics restore the air the phone never captured), and a de-esser on 5-10 kHz.
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
    """(N, 2): both phone capsules, high-passed at 80 Hz, R aligned to L (4 samples)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", edl.SRC, "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)
    x = np.stack([x[:, 0], np.roll(x[:, 1], -4)], 1)
    return sosfiltfilt(butter(4, 80, "highpass", fs=SR, output="sos"), x, axis=0)


def band_mono(x2):
    lp = butter(4, 1500, "lowpass", fs=SR, output="sos")
    L, R = x2[:, 0], x2[:, 1]
    return sosfiltfilt(lp, 0.5 * (L + R)) + (L - sosfiltfilt(lp, L))


def wpe(x2, n_fft=2048, hop=512, taps=18, delay=2, iters=3):
    """Weighted prediction error dereverberation of a (N, D) multichannel take -> (N, D).
    Per frequency f: X_t = Y_t - G^H Ytil_t, where Ytil_t stacks the D channels' STFT at t-delay ... t-delay-taps+1
    and G minimises sum_t |X_t|^2 / lambda_t (lambda = the dry signal's power, from the previous iteration)."""
    N, D = x2.shape
    if N < n_fft * 8:
        return x2
    Y = np.stack([stft(x2[:, d], SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary="even",
                       padded=True)[2] for d in range(D)], 1).astype(np.complex64)          # (F, D, T)
    F, _, T = Y.shape
    K = taps
    Yt = np.zeros((F, D * K, T), np.complex64)
    for k in range(K):
        s = delay + k
        Yt[:, k * D:(k + 1) * D, s:] = Y[:, :, :T - s]
    YtH = np.conj(Yt).transpose(0, 2, 1)                                                     # (F, T, DK)
    X = Y
    eye = np.eye(D * K, dtype=np.complex64)[None]
    for _ in range(iters):
        lam = np.mean(np.abs(X) ** 2, axis=1)                                                # (F, T)
        lam = np.maximum(lam, 1e-3 * lam.mean(axis=1, keepdims=True) + 1e-12)
        Ytw = Yt / lam[:, None, :].astype(np.float32)
        R = Ytw @ YtH                                                                        # (F, DK, DK)
        P = Ytw @ np.conj(Y).transpose(0, 2, 1)                                              # (F, DK, D)
        tr = np.real(np.trace(R, axis1=1, axis2=2))[:, None, None] / (D * K)
        G = np.linalg.solve(R + 1e-4 * tr * eye, P)                                          # (F, DK, D)
        X = Y - np.conj(G).transpose(0, 2, 1) @ Yt                                           # (F, D, T)
    out = np.zeros_like(x2)
    for d in range(D):
        _, y = istft(X[:, d, :], SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary=True)
        out[:, d] = y[:N]
    return out


def denoise(x, over=1.6, floor_db=-14.0, pct=12, release=0.040):
    n_fft, hop = 2048, 512
    if len(x) < n_fft * 2:
        return x
    f, t, Z = stft(x, SR, nperseg=n_fft, noverlap=n_fft - hop, window="hann", boundary="even", padded=True)
    P = np.abs(Z) ** 2
    N = np.percentile(P, pct, axis=1, keepdims=True) / -np.log(1 - pct / 100)    # a noise bin's power is exponential: unbias
    g = np.clip(1 - over * N / (P + 1e-20), (10 ** (floor_db / 20)) ** 2, 1.0) ** 0.5
    g = (np.roll(g, 1, 0) + g + np.roll(g, -1, 0)) / 3                       # across frequency
    rel = np.exp(-hop / (release * SR))                                      # a short release over time
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


# toward a broadcast voice: trim the room's low-mid box, open the presence and the air
EQ = np.vstack([_peak(110, 1.5, 0.9), _peak(320, -3.5, 1.0), _peak(850, -1.0, 1.2), _peak(3000, 5.0, 0.9),
                _shelf(5000, 8.0, high=True), _shelf(10000, 4.0, high=True)])


def exciter(x, lo=1800, hi=4500, drive=3.5, mix_db=-4.0):
    """Harmonic exciter: the 1.8-4.5 kHz band, normalised by its own envelope so the effect doesn't depend on
    level, soft-clipped (odd harmonics) and rectified (even ones); only the new content above 4.5 kHz is kept
    and mixed in under the voice, scaled back by the band's envelope."""
    band = sosfiltfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)
    env = np.sqrt(np.convolve(band ** 2, np.ones(240) / 240, "same")) + 1e-6                 # 5 ms
    u = band / env
    gen = np.tanh(drive * u) / np.tanh(drive) + 0.35 * (np.abs(u) - np.abs(u).mean())
    gen = sosfiltfilt(butter(4, 4500, "highpass", fs=SR, output="sos"), gen) * env
    return x + gen * 10 ** (mix_db / 20)


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


def decay_report(x, label):
    """How fast the voice falls after a phrase ends (dB re the phrase's peak), at 50/100/200 ms."""
    import json
    hop = SR // 100
    k = len(x) // hop
    e = 10 * np.log10((x[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-14)
    ws = [w for r in json.load(open(os.path.join(edl.ROOT, "renders/analysis/words.json"))) for w in r["words"]]
    ends = [ws[i]["e"] for i in range(len(ws) - 1) if ws[i + 1]["s"] - ws[i]["e"] > 0.35]
    c = []
    for t in ends:
        i = int(t * 100)
        if 30 <= i < len(e) - 25:
            c.append(e[i:i + 25] - e[i - 30:i].max())
    c = np.median(np.array(c), 0)
    print(f"{label} decay after a phrase: +50ms {c[5]:.1f}  +100ms {c[10]:.1f}  +200ms {c[20]:.1f} dB")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    x2 = load_src()
    decay_report(x2[:, 0], "before")
    bounds = [int(t * SR) for t in TAKES] + [len(x2)]
    w2 = np.zeros_like(x2)
    for a, b in zip(bounds, bounds[1:]):
        w2[a:b] = wpe(x2[a:b], n_fft=1536, hop=384, taps=36, delay=2, iters=5)
    x = band_mono(w2)
    bands_report(band_mono(x2), "before")
    y = np.zeros_like(x)
    for a, b in zip(bounds, bounds[1:]):
        y[a:b] = dereverb(denoise(x[a:b]), t60=0.7, delay=0.048, over=1.4, floor_db=-11.0)
    y = sosfilt(EQ, y)
    y = exciter(y)
    y = deess(y)
    bands_report(y, "after ")
    decay_report(y, "after ")
    sf.write(OUT, y.astype(np.float32), SR, subtype="FLOAT")
    print("->", OUT)


if __name__ == "__main__":
    main()
