"""One strip per reel: log-frequency spectrogram, loudness, cuts (cyan) and flashes (white).
  python3 tools/spectro_inspo.py OUT.png r1 r2 ...   (reads renders/analysis/<r>.json and renders/src/inspo/<r>.mp4)"""
import json, subprocess, sys
import numpy as np, librosa, librosa.display
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
out, names = sys.argv[1], sys.argv[2:]
fig, axes = plt.subplots(len(names), 1, figsize=(18, 2.6 * len(names)))
for ax, n in zip(np.atleast_1d(axes), names):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"renders/src/inspo/{n}.mp4", "-vn", "-ac", "1", "-ar", "22050", "-f", "f32le", "-"], capture_output=True).stdout
    y = np.frombuffer(raw, np.float32)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=256)), ref=np.max)
    librosa.display.specshow(S, sr=22050, hop_length=256, x_axis="time", y_axis="log", ax=ax, cmap="magma", vmin=-70)
    d = json.load(open(f"renders/analysis/{n}.json"))
    fps = d["video"]["fps"]
    for c in d["video"]["cuts"]:
        ax.axvline(c / fps, color="cyan", lw=0.8, alpha=0.8)
    for f in d["video"]["flashes"]:
        ax.axvline(f / fps, color="white", lw=1.5, ls=":")
    ax.set_xticks(np.arange(0, len(y) / 22050, 0.5)); ax.tick_params(labelsize=6)
    ax.set_title(n, fontsize=9, loc="left"); ax.set_ylabel(""); ax.set_xlabel("")
plt.tight_layout(); plt.savefig(out, dpi=80)
