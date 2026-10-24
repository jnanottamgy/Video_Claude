"""Objective checks of the mix (renders/audio): speech-to-music ratio per line, drop punch, loudness.

  python3 tools/audio_check.py
Per line: the median, over the frames where the voice is active, of (dialogue - music) in the
300 Hz-4 kHz band that carries intelligibility. Broadcast practice wants >= 8-10 dB there.
"""
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

os.chdir(edl.ROOT)
SR = 48000
D, _ = sf.read("renders/audio/stem_D.wav")
M, _ = sf.read("renders/audio/stem_M.wav")
B, _ = sf.read("renders/audio/stem_B.wav")
sos = butter(4, [300, 4000], "bandpass", fs=SR, output="sos")
band = lambda x: sosfiltfilt(sos, x.mean(axis=1))
d, m, b = band(D), band(M), band(B)
hop = SR // 50
def lv(x):
    k = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-12)
ld, lm, lb = lv(d), lv(m), lv(b + m)
active = ld > np.percentile(ld[ld > -80], 70) - 18
print("line   speech-to-music  speech-to-(music+sfx)   (median over active voice, dB)")
pieces = [(s["out0"], s["out1"], s["id"]) for s in edl.SEGMENTS if s["kind"] == "talk"]
pieces += [(v["out0"], v["out0"] + v["src1"] - v["src0"], s["id"] + "vo") for s in edl.SEGMENTS for v in s.get("vo", [])]
for a, e, sid in sorted(pieces):
    i, j = int(a * 50), int(e * 50)
    sel = active[i:j]
    if sel.sum() < 3:
        continue
    smr = np.median((ld[i:j] - lm[i:j])[sel])
    sbr = np.median((ld[i:j] - lb[i:j])[sel])
    flag = "  LOW" if smr < 8 else ""
    print(f"{sid:6s} {a:6.2f}  {smr:6.1f}  {sbr:6.1f}{flag}")
mix, _ = sf.read("renders/audio/mix.wav")
meter = pyln.Meter(SR)
print(f"mix integrated {meter.integrated_loudness(mix):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS")
sub = sosfiltfilt(butter(4, 150, "lowpass", fs=SR, output="sos"), mix.mean(axis=1))
air = sosfiltfilt(butter(4, 5000, "highpass", fs=SR, output="sos"), mix.mean(axis=1))
rms = lambda x, i, j: 20 * np.log10(np.sqrt((x[i:j] ** 2).mean()) + 1e-12)
for name, t in (("drop 1", edl.D), ("drop 2", edl.D2)):
    i, w = int(t * SR), int(0.4 * SR)
    print(f"{name} at {t:.3f}: jump over 400 ms  sub(<150 Hz) {rms(sub, i, i + w) - rms(sub, i - w, i):+.1f} dB, "
          f"air(>5 kHz) {rms(air, i, i + w) - rms(air, i - w, i):+.1f} dB, full {rms(mix.mean(axis=1), i, i + w) - rms(mix.mean(axis=1), i - w, i):+.1f} dB")
