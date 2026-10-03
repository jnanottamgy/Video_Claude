"""Sound design for the S.H.E.L.F wall reveal + LAUNCHING SOON, as one 10s stem.

Every cue is placed by the *measured* transient of its file (onset or peak), not
by the file's start, so the sound lands on the frame where its visual happens.
The impact time and the typing rhythm are parsed from the two compositions, so
retiming the animation retimes the sound.

Sources: the bundled media-use SFX library (assets/sfx/, offline).

Placement follows the picture: S.H.E.L.F sits on the left of frame, LAUNCHING
SOON on the right, so their sounds are panned that way — and each letter tick
or keystroke pans with that letter's position. Pans stay moderate: phone
speakers are near-mono, and low end stays centred.

  python3 tools/mix_sfx.py   ->  renders/out/SHELF_sfx.wav  (48 kHz / 24-bit, -16 LUFS, -1.5 dBTP)
"""
import json
import os
import re
import subprocess

import numpy as np
from scipy.signal import resample

SR = 48000
DUR = 10.0
SFX = "assets/sfx"
OUT = "renders/out/SHELF_sfx.wav"
TARGET_LUFS, TARGET_TP = -16.0, -1.5


def parse(path, name):
    m = re.search(r"var\s+%s\s*=\s*([^;]+);" % name, open(path).read())
    return json.loads(m.group(1))


HIT = parse("index.html", "HIT")                                   # mark hits the wall
T1 = parse("../shelf-launch-soon/index.html", "T1")                # L-A-U-N-C-H-I-N-G
ENTER = parse("../shelf-launch-soon/index.html", "ENTER")
T2 = parse("../shelf-launch-soon/index.html", "T2")                # S-O-O-N
# These mirror literal times in index.html (see the matching tl calls there):
SPEC = 1.55                                     # specular sweep starts
GLYPH0, GLYPH_STEP = 1.75, 0.065                # S . H . E . L . F, one glyph per step
RULE = 2.55
DECODE0, DECODE_STEP, FLASH = 3.0, 0.24, 0.05   # word k lands at DECODE0+k*STEP, its letter flashes +FLASH
CURSOR_IN = 4.55                                # from shelf-launch-soon: the cursor appears
BAR = 6.6                                       # launch bar fills 6.6 -> 7.5
SHINES = (7.6, 9.0)


def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SFX, name + ".mp3"),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def onset(x, db=-30):
    a = np.abs(x).max(axis=1)
    return int(np.argmax(a > a.max() * 10 ** (db / 20)))


def crest(x, win=0.05):
    """Time of maximum short-term energy (a peak *region*, not a single spiky sample)."""
    n = int(win * SR)
    e = np.convolve((x ** 2).mean(axis=1), np.ones(n) / n, mode="same")
    return int(np.argmax(e))


def pitch(x, semis):
    if semis == 0:
        return x
    n = int(round(len(x) / 2 ** (semis / 12)))
    return np.stack([resample(x[:, 0], n), resample(x[:, 1], n)], axis=1)


def pan_mono(x, p):
    m = x.mean(axis=1)
    th = (p + 1) * np.pi / 4
    return np.stack([m * np.cos(th), m * np.sin(th)], axis=1) * np.sqrt(2)


def balance(x, p):
    return x * np.array([min(1.0, 1 - p), min(1.0, 1 + p)])


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    for n, sl in ((int(fin * SR), slice(None)), (int(fout * SR), None)):
        if n <= 0:
            continue
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
        if sl is None:
            x[-n:] *= ramp[::-1, None]
        else:
            x[:n] *= ramp[:, None]
    return x


def decay_after(x, at, tau):
    t = np.arange(len(x)) / SR
    env = np.where(t < at / SR, 1.0, np.exp(-(t - at / SR) / tau))
    return x * env[:, None]


mix = np.zeros((int(DUR * SR), 2))
log = []


def place(x, t_event, ref, gain, label):
    """Put sample `ref` of x (its transient) at timeline time t_event."""
    start = int(round(t_event * SR)) - ref
    a, b = max(0, start), min(len(mix), start + len(x))
    if b > a:
        mix[a:b] += gain * x[a - start:b - start]
    log.append((t_event, label))


# 1 ── riser crests into the hit. The library manifest says this file peaks at its
#      end (~10s); measured, its crest is ~4s in and it's silent after ~5s.
riser = load("riser")
rc = crest(riser)
seg = riser[max(0, rc - int(HIT * SR)): rc + int(0.04 * SR)]          # timeline 0 -> just past the hit
place(fade(balance(seg, -0.15), fin=0.35, fout=0.06), HIT, int(HIT * SR), 0.5,
      f"riser (crest {rc / SR:.2f}s into file)")

# 2 ── the hit: a deep boom + a punchier mid thud, both ATTACK-aligned to the hit.
#      Measured, neither file has a swell to anchor to: each reaches full level within
#      ~40 ms and then sustains at ~0 dBFS RMS for 2s+ (a sub drone, not a hit). The
#      manifest describes impact-bass-2 as "short swell, then a deep hit" — its level is
#      flat from 40 ms. So: anchor the attack, and shape each into a decaying hit.
#      (Anchoring b2's loudest 20 ms instead landed deep in that plateau and started the
#      boom before t=0, burying the riser — caught on the stem's envelope plot.)
b2 = load("impact-bass-2"); o2 = onset(b2)
place(decay_after(balance(b2, -0.2), o2 + int(0.04 * SR), 0.45), HIT, o2, 0.6, "impact boom")
b1 = load("impact-bass-1"); o1 = onset(b1)
place(decay_after(balance(b1, -0.3), o1 + int(0.03 * SR), 0.3), HIT, o1, 0.5, "impact thud")

# 3 ── glass shimmer riding the specular sweep, panning across the mark as it moves
sp = load("sparkle"); os_ = onset(sp)
m = sp.mean(axis=1)
pans = np.linspace(-0.65, -0.25, len(m))
th = (pans + 1) * np.pi / 4
sweep = np.stack([m * np.cos(th), m * np.sin(th)], axis=1) * np.sqrt(2)
place(sweep, SPEC + 0.07, os_, 0.5, "shimmer on specular sweep")

# 4 ── a soft, low tick per letter of S.H.E.L.F (dots silent), rising in pitch, panned per letter
ck = load("click")
for j, (semis, p) in enumerate(zip((-6, -5, -4, -3, -2), np.linspace(-0.7, -0.25, 5))):
    x = pitch(ck, semis)
    place(pan_mono(x, p), GLYPH0 + 2 * j * GLYPH_STEP + 0.06, onset(x), 0.25, f"tick {'SHELF'[j]}")

# 5 ── the accent rule swipes out
wh = load("whoosh-short")
place(balance(wh, -0.45), RULE + 0.2, crest(wh, 0.02), 0.35, "rule swipe")

# 6 ── decode: each word lights its letter with a ping, climbing a pentatonic scale
pg = load("ping")
for k, (semis, p) in enumerate(zip((-4, -2, 0, 3, 5), np.linspace(-0.7, -0.25, 5))):
    x = pitch(pg, semis)
    place(pan_mono(x, p), DECODE0 + k * DECODE_STEP + FLASH, onset(x), 0.32, f"decode ping {'SHELF'[k]}")

# 7 ── over to the other wall: the cursor arrives
place(pan_mono(pitch(ck, 4), 0.6), CURSOR_IN, onset(pitch(ck, 4)), 0.12, "cursor appears")

# 8 ── typing. Each keystroke a little different (fixed seed: renders are identical),
#      panned to where its letter lands on the back wall. SOON is typed heavier.
kp = load("key-press")
rng = np.random.default_rng(7)
for i, t in enumerate(T1):
    x = pitch(kp, rng.uniform(-0.6, 0.6))
    place(pan_mono(x, np.linspace(0.45, 0.75, len(T1))[i]), t, onset(x), 0.4 * 10 ** (rng.uniform(-1.5, 1.5) / 20), f"key {'LAUNCHING'[i]}")
x = pitch(kp, -4)
place(pan_mono(x, 0.55), ENTER, onset(x), 0.55, "enter")
for i, t in enumerate(T2):
    x = pitch(kp, -1.5 + rng.uniform(-0.4, 0.4))
    place(pan_mono(x, np.linspace(0.5, 0.72, len(T2))[i]), t, onset(x), 0.5 * 10 ** (rng.uniform(-1, 1) / 20), f"key {'SOON'[i]}")

# 9 ── launch bar fills, and a soft chime as it settles
place(balance(wh, 0.6), BAR + 0.1, crest(wh, 0.02), 0.14, "bar fill swipe")
cm = load("chime")
place(pan_mono(cm, 0.55), BAR + 0.85, onset(cm), 0.28, "chime as bar settles")

# 10 ── the shine passing along the bar
for t in SHINES:
    place(pan_mono(sp, 0.6), t + 0.15, onset(sp), 0.18, "bar shine")


# ── clean up: 35 Hz high-pass (sub-audible rumble only eats headroom; phones can't
#    play it anyway) and a short fade so the last shimmer tail doesn't cut off at 10s
from scipy.signal import butter, sosfiltfilt
mix = sosfiltfilt(butter(4, 35, "highpass", fs=SR, output="sos"), mix, axis=0)
mix[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))[:, None]

# ── loudness: measure, set static gain to target, then true-peak limit
os.makedirs(os.path.dirname(OUT), exist_ok=True)
tmp = OUT + ".raw.wav"
import wave
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(tmp, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af",
                       f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"],
                      capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
                f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}"
                f":measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
                f"alimiter=limit={10 ** (TARGET_TP / 20):.4f}:level=disabled",
                "-ar", str(SR), "-c:a", "pcm_s24le", OUT], check=True)
os.remove(tmp)

print(f"cues: {len(log)}   (HIT={HIT}s, {len(T1)}+{len(T2)} keystrokes parsed from the compositions)")
for t, label in sorted(log):
    print(f"  {t:6.3f}s  {label}")
print("->", OUT)
