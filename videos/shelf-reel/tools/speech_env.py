"""Speech envelope of the source mix: 1-4 kHz RMS in 10 ms hops, in dB.

Their music bed is bass-heavy, so consonant/vowel onsets stand out in this band; beats.py snaps
caption times to them.

  python3 tools/speech_env.py   ->  renders/speech_env_db.npy
"""
import wave

import numpy as np
from scipy.signal import butter, sosfiltfilt

w = wave.open("renders/source_audio.wav")
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).mean(axis=1) / 32768
sp = sosfiltfilt(butter(4, [900, 4000], "bandpass", fs=sr, output="sos"), x)
hop = int(0.01 * sr)
env = np.array([np.sqrt(np.mean(sp[i:i + hop] ** 2)) for i in range(0, len(sp) - hop, hop)])
np.save("renders/speech_env_db.npy", 20 * np.log10(env + 1e-9))
print(f"{len(env)} hops -> renders/speech_env_db.npy")
