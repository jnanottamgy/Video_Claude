"""The soundtrack: her own recording of the song's finale, untouched in its timing, with a few temple sounds.

  python3 tools/mix.py   ->  renders/audio/mix.wav   (-14 LUFS, -1 dBTP)

- **Song:** source 373.98-404.60 s, one continuous take: the last refrain, the chant and the song's own ending,
  then silence.
  - Processing: only a 35 Hz high-pass and +2.5 dB of air above 6 kHz. The YouTube copy is dark: its 5-10 kHz
    band sits ~15 dB under a balanced mix.
- **Temple sounds** (tools/sounds.py, tuned to Sa = G#):
  - a deep bell on the first frame;
  - a small bell as she first appears;
  - a shankh rising under "ಜೈ ಬೋಲೋ";
  - the deep bell again on the shouted "ಜೈ!", with a shimmer of ghungroo and a soft low whoosh from the library;
  - a tanpura drone under the end card, fading out so the loop restarts on the bell.
"""
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl  # noqa: E402
import sfx  # noqa: E402
import sounds as S  # noqa: E402

SR = 48000
OUT = os.path.join(edl.ROOT, "renders/audio")
N = int(round(edl.DURATION * SR))
SRC_AUDIO = os.path.join(OUT, "source.wav")


def shelf(f0, gain_db, s=0.7):
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    c, sq = np.cos(w), 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
    a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1, a[1] / a[0], a[2] / a[0]]])


def song():
    if not os.path.exists(SRC_AUDIO):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(edl.ROOT, "renders/src/drive/gommata_source.mp4"),
                        "-vn", "-ar", str(SR), "-c:a", "pcm_f32le", SRC_AUDIO], check=True)
    x, sr = sf.read(SRC_AUDIO, always_2d=True)
    assert sr == SR
    i0, n = int(round(edl.SRC0 * SR)), int(round(edl.MUSIC_END * SR))
    y = x[i0:i0 + n].astype(np.float64).copy()
    k = int(0.03 * SR)
    y[:k] *= np.linspace(0, 1, k)[:, None]
    k = int(0.35 * SR)
    y[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    eq = np.vstack([butter(2, 35, "highpass", fs=SR, output="sos"), shelf(6000, 2.5)])
    y = sosfilt(eq, y, axis=0)
    out = np.zeros((N, 2))
    out[:len(y)] = y
    return out


def put(buf, x, t, gain_db, fade_in=0.0, length=None, fade_out=0.0):
    x = x.copy()
    if length is not None:
        x = x[:int(length * SR)]
    if fade_in > 0:
        k = min(len(x), int(fade_in * SR))
        x[:k] *= np.linspace(0, 1, k)[:, None]
    if fade_out > 0:
        k = min(len(x), int(fade_out * SR))
        x[-k:] *= np.linspace(1, 0, k)[:, None]
    i = int(round(t * SR))
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[:j - i] * 10 ** (gain_db / 20)


def effects():
    b = np.zeros((N, 2))
    put(b, S.big_bell(seed=1), 0.0, -17)
    put(b, S.ting(seed=4), edl.S[2] - 0.02, -27)
    put(b, S.shankh(f0=edl.SA / 2, dur=2.4), 22.95, -21, fade_in=0.15)
    put(b, S.big_bell(seed=3), edl.JAI - 0.01, -14)
    put(b, S.ghungroo(seed=3), edl.JAI, -22)
    sfx.place(b, "lowpass-woosh", edl.JAI, gain_db=-20)
    t_dr = edl.MUSIC_END - 0.6
    put(b, S.tanpura(dur=edl.DURATION - t_dr + 0.5), t_dr, -21, fade_in=0.8, length=edl.DURATION - t_dr,
        fade_out=1.0)
    return b


def limit(x, ceiling_db=-1.0, look=0.002, rel=0.08):
    """A 4x-oversampled peak limiter (smooth gain, lookahead)."""
    from scipy.signal import resample_poly
    up = resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(1)
    c = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    L = int(look * SR * 4)
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, 2 * L + 1)
    a = np.exp(-1 / (rel * SR * 4))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
        out[i] = cur
    return resample_poly(up * out[:, None], 1, 4, axis=0)[:len(x)]


def main():
    os.makedirs(OUT, exist_ok=True)
    s, e = song(), effects()
    mix = s + e
    m = pyln.Meter(SR)
    lufs = m.integrated_loudness(mix)
    g = 10 ** ((-14.0 - lufs) / 20)
    mix = limit(mix * g, -1.0)
    sf.write(os.path.join(OUT, "mix.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    print(f"mix: in {lufs:.1f} LUFS, gain {20 * np.log10(g):+.2f} dB -> {m.integrated_loudness(mix):.1f} LUFS, "
          f"peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS; effects {m.integrated_loudness(e * g):.1f} LUFS alone")


if __name__ == "__main__":
    main()
