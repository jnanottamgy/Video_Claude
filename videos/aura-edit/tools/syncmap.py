"""Spectrogram of the reference's soundtrack with the beat grid and the edit's events on top.

  python3 tools/syncmap.py renders/analysis OUT.png t0 t1
"""
import json
import sys

import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

EVENTS = [  # (time s, label, kind)  kind: cut | flash | fx | text
    (0.000, "cutout strobe", "fx"), (0.458, "CUT", "cut"), (2.167, "hand wipe", "fx"), (2.583, "wipe lands", "cut"),
    (4.667, "echo", "fx"), (4.958, "echo dissolve", "cut"), (5.125, "shake", "fx"), (6.375, "white sil", "flash"),
    (6.667, "white sil", "flash"), (6.958, "white sil", "flash"), (7.667, "CUT dbl-exp", "cut"),
    (7.917, "", "fx"), (8.167, "", "fx"), (8.417, "", "fx"), (8.667, "", "fx"), (8.875, "", "fx"), (9.125, "", "fx"),
    (9.375, "", "fx"), (9.625, "", "fx"), (9.875, "threshold", "flash"), (10.167, "CUT", "cut"), (10.833, "CUT", "cut"),
    (11.125, "+1", "cut"), (11.458, "+1", "cut"), (12.708, "CUT", "cut"), (13.250, "CRAZY", "text"), (13.750, "", "text"),
    (13.917, "+1", "cut"), (14.250, "+1", "cut"), (14.500, "+1", "cut"), (15.000, "pose", "cut"), (15.208, "CUT", "cut"),
    (15.625, "white mask", "flash"), (15.792, "white mask", "flash"), (16.458, "CUT spin", "cut"), (16.792, "CUT", "cut"),
    (17.125, "CUT", "cut"), (17.750, "CUT", "cut"), (18.208, "mask", "flash"), (18.292, "mask", "flash"),
    (18.375, "mask", "flash"), (18.958, "line", "fx"), (19.167, "cross", "fx"), (19.708, "blocks", "fx"),
    (19.917, "B&W full", "cut"), (20.208, "CUT", "cut"), (21.000, "logo walk-by", "text"), (24.167, "fade", "fx"),
]
COL = {"cut": "#ff3b30", "flash": "#ffffff", "fx": "#35c8ff", "text": "#ffcc00"}


def main():
    d, out, t0, t1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    au = json.load(open(f"{d}/audio.json"))
    y, sr = librosa.load(f"{d}/audio.wav", sr=22050, mono=True, offset=t0, duration=t1 - t0)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=128)), ref=np.max)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(26, 9), sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
    librosa.display.specshow(S, sr=sr, hop_length=128, x_axis="time", y_axis="log", ax=a1, cmap="magma", vmin=-75)
    hop = au["hop"]
    env = np.array(au["onset_env"])
    te = np.arange(len(env)) * hop / au["sr"]
    m = (te >= t0) & (te <= t1)
    a2.plot(te[m] - t0, env[m], color="#444")
    bands = au["bands"]
    tb = np.arange(len(bands["sub"])) * hop / au["sr"]
    mb = (tb >= t0) & (tb <= t1)
    a2b = a2.twinx()
    for k, c in (("sub", "#7a3cff"), ("bass", "#c03cff"), ("high", "#00a0a0"), ("air", "#a0a000")):
        a2b.plot(tb[mb] - t0, np.array(bands[k])[mb], color=c, lw=1, label=k)
    a2b.legend(loc="upper right", fontsize=8)
    for b in au["beats"]:
        if t0 <= b <= t1:
            a1.axvline(b - t0, color="#00ff88", lw=0.8, alpha=0.6)
            a2.axvline(b - t0, color="#00aa55", lw=0.8, alpha=0.6)
    for t, lab, kind in EVENTS:
        if t0 <= t <= t1:
            a1.axvline(t - t0, color=COL[kind], lw=1.6, ls="--", alpha=0.95)
            a1.text(t - t0 + 0.01, 9000, lab, color=COL[kind], fontsize=9, rotation=90, va="top")
    a1.set_title(f"{t0:.1f}-{t1:.1f} s  (green = detected beats; red = cuts, white = flashes, blue = effects, yellow = text)")
    ticks = np.arange(0, t1 - t0 + 1e-6, 0.25)
    a2.set_xticks(ticks)
    a2.set_xticklabels([f"{t0 + x:.2f}" if abs((t0 + x) * 2 - round((t0 + x) * 2)) < 1e-6 else "" for x in ticks], fontsize=8)
    plt.tight_layout()
    plt.savefig(out, dpi=70)
    print(out)


if __name__ == "__main__":
    main()
