"""Sound for the 3s STAY TUNED IN / TO KNOW card, placed by measured transients.

Same method as the S.H.E.L.F wall reveal (../shelf-wall-reveal/tools/mix_sfx.py), whose
measurements of the bundled media-use library hold here too:
  - riser.mp3 builds 2.0-3.0s, plateaus, cuts at 4.15s: its ENERGY CREST anchors the hit
    (its manifest's "peak at end, trigger at climax - 10.03s" is wrong for this file)
  - impact-bass-1/2 reach full level within ~40ms then sustain near 0 dBFS for 2s+:
    anchor the ATTACK, and shape each into a decaying hit
HIT is parsed from index.html, so retiming the lock retimes the boom.

  python3 tools/mix_sfx.py  ->  renders/sfx.wav   (48 kHz / 24-bit, 3.0s, -16 LUFS, -1.5 dBTP)
"""
import json, os, re, subprocess, wave
import numpy as np
from scipy.signal import butter, resample, sosfiltfilt

SR, DUR, SFX, OUT = 48000, 3.0, "assets/sfx", "renders/sfx.wav"
HIT = json.loads(re.search(r"var\s+HIT\s*=\s*([^;]+);", open("index.html").read()).group(1))
TOKNOW, SWEEP, FADE = 1.08, 1.45, 2.56          # mirror the tl calls in index.html


def load(n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{SFX}/{n}.mp3", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def onset(x, db=-30):
    a = np.abs(x).max(axis=1); return int(np.argmax(a > a.max() * 10 ** (db / 20)))


def crest(x, win=0.05):
    k = int(win * SR); return int(np.argmax(np.convolve((x ** 2).mean(axis=1), np.ones(k) / k, mode="same")))


def pitch(x, s):
    if s == 0: return x
    n = int(round(len(x) / 2 ** (s / 12))); return np.stack([resample(x[:, 0], n), resample(x[:, 1], n)], axis=1)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin > 0: n = int(fin * SR); x[:n] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
    if fout > 0: n = int(fout * SR); x[-n:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
    return x


def decay_after(x, at, tau):
    t = np.arange(len(x)) / SR; return x * np.where(t < at / SR, 1.0, np.exp(-(t - at / SR) / tau))[:, None]


mix = np.zeros((int(DUR * SR), 2))


def place(x, t, ref, gain):
    s = int(round(t * SR)) - ref; a, b = max(0, s), min(len(mix), s + len(x))
    if b > a: mix[a:b] += gain * x[a - s:b - s]


# 1 riser crests into the lock
r = load("riser"); rc = crest(r)
seg = r[max(0, rc - int(HIT * SR)): rc + int(0.03 * SR)]
place(fade(seg, fin=0.25, fout=0.05), HIT, int(HIT * SR), 0.5)
# 2 the hit: deep boom + punchy thud, attack-aligned, shaped into decaying hits
b2 = load("impact-bass-2"); o2 = onset(b2); place(decay_after(b2, o2 + int(0.04 * SR), 0.5), HIT, o2, 0.65)
b1 = load("impact-bass-1"); o1 = onset(b1); place(decay_after(b1, o1 + int(0.03 * SR), 0.3), HIT, o1, 0.5)
# 3 TO KNOW rises: a soft swipe
w = load("whoosh-short"); place(w, TOKNOW + 0.12, crest(w, 0.02), 0.32)
# 4 the light sweep: shimmer travelling left -> right with the band
sp = load("sparkle"); m = sp.mean(axis=1); th = (np.linspace(-0.45, 0.45, len(m)) + 1) * np.pi / 4
place(np.stack([m * np.cos(th), m * np.sin(th)], axis=1) * np.sqrt(2), SWEEP + 0.05, onset(sp), 0.45)
# 5 out: a low, soft swipe as it fades
wl = pitch(w, -5); place(wl, FADE + 0.15, crest(wl, 0.02), 0.22)

mix = sosfiltfilt(butter(4, 35, "highpass", fs=SR, output="sos"), mix, axis=0)
mix[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))[:, None]
os.makedirs("renders", exist_ok=True); tmp = OUT + ".raw.wav"
with wave.open(tmp, "wb") as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
                f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
                f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.8414:level=disabled",
                "-ar", str(SR), "-c:a", "pcm_s24le", OUT], check=True)
os.remove(tmp); print(f"HIT={HIT}s  riser crest {rc / SR:.2f}s into file  ->  {OUT}")
