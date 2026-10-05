"""Clean dialogue: the team's mix minus the song, which we have as a clean file.

Their edit plays renders/song.mp3 from its first sample at source t=0, unprocessed, at a constant
-17.5 dB (measured: zero offset and zero drift across the whole reel; the last 3 s fade out). So
the music is removed by subtraction, not separation: in the STFT domain, per channel,
    D = X - g(t) * H(f) * S
H(f) is the least-squares transfer function fitted on the dialogue-free wake-up section (src 1-16 s),
g(t) a smooth broadband gain that follows their fade-out. What remains is the dialogue plus
whatever else was in their mix (the wall-reveal SFX), minus AAC coding noise.

  python3 tools/dialogue.py        # -> renders/dialogue.wav (48 kHz stereo, source timeline)
"""
import subprocess

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import istft, stft

SR = 48000
NFFT, HOP = 2048, 512
FIT = [(1.0, 16.0)]                # dialogue-free: the alarm and wake-up (source seconds)


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def main():
    x = load("renders/source.mp4")
    s = load("renders/song.mp3")[: len(x)]
    out = np.zeros_like(x)
    for ch in range(2):
        _, t, X = stft(x[:, ch], SR, nperseg=NFFT, noverlap=NFFT - HOP)
        _, _, S = stft(s[:, ch], SR, nperseg=NFFT, noverlap=NFFT - HOP)
        fit = np.zeros(len(t), bool)
        for a, b in FIT:
            fit |= (t >= a) & (t < b)
        H = (X[:, fit] * S[:, fit].conj()).sum(1) / ((np.abs(S[:, fit]) ** 2).sum(1) + 1e-12)
        M = H[:, None] * S
        # broadband gain per frame, relative to H: speech is uncorrelated with the song, so this is
        # unbiased; smoothed over ~0.5 s, and held at 1 wherever the song is too quiet to measure
        num = np.real((X * M.conj()).sum(0))
        den = (np.abs(M) ** 2).sum(0)
        w = int(0.5 * SR / HOP)
        g = uniform_filter1d(num, w) / (uniform_filter1d(den, w) + 1e-12)
        quiet = uniform_filter1d(den, w) < 1e-6 * den.max()
        g = np.clip(np.where(quiet, 1.0, g), 0.0, 1.2)
        D = X - g[None, :] * M
        _, d = istft(D, SR, nperseg=NFFT, noverlap=NFFT - HOP)
        out[:, ch] = d[: len(x)]
        sup = 10 * np.log10((np.abs(D[:, fit]) ** 2).sum() / (np.abs(X[:, fit]) ** 2).sum())
        print(f"ch{ch}: |H| median {np.median(np.abs(H[10:700])):.4f}  music suppression on the fit range {sup:.1f} dB  "
              f"gain range {g[~quiet].min():.3f}-{g[~quiet].max():.3f}")
    sf.write("renders/dialogue.wav", out, SR, subtype="FLOAT")
    print("renders/dialogue.wav", len(out) / SR, "s")


if __name__ == "__main__":
    main()
