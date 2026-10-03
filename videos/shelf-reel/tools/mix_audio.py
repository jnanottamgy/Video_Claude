"""Sound for the S.H.E.L.F reel recut.

Two stems, then a master:
  A  the source mix (dialogue + their music) re-cut to the EDL with 30 ms fades at every join;
     replaced by sound design in the compressed intro, tape-stopped into the freeze frames,
     rewound for the cold-open rewind.
  B  sound design: every camera hit / whip / glitch / flash in direction.py gets its sound on the
     same frame; notification pings and tile pops are placed where the overlay renders actually
     show a new card (alpha onsets), so the sound follows the picture exactly.
Master: 30 Hz high-pass, peak limiter, two-pass loudnorm to -14 LUFS / -1 dBTP (Instagram).

  python3 tools/mix_audio.py   ->  renders/mix.wav
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
import direction as D  # noqa: E402
import edl  # noqa: E402

SR = 48000
FPS = edl.FPS
TOTAL = edl.TOTAL / FPS
SFX = "assets/sfx"
OUT = "renders/mix.wav"
rng = np.random.default_rng(42)


# ---------------- io + dsp helpers ----------------
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


_cache = {}


def sfx(name):
    if name not in _cache:
        _cache[name] = load(f"{SFX}/{name}.mp3")
    return _cache[name]


def onset(x, db=-30):
    a = np.abs(x).max(axis=1)
    return int(np.argmax(a > a.max() * 10 ** (db / 20)))


def place(buf, x, t, align=0, gain=1.0, pan=0.0):
    """Mix x into buf so that sample `align` of x lands at time t (s). pan in [-1, 1]."""
    if gain == 0 or len(x) == 0:
        return
    i = int(round(t * SR)) - align
    a, b = max(0, i), min(len(buf), i + len(x))
    if b <= a:
        return
    th = (pan + 1) * np.pi / 4
    g = np.array([np.cos(th), np.sin(th)]) * np.sqrt(2) * gain
    buf[a:b] += x[a - i:b - i] * g


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = len(x)
    if fin > 0:
        k = min(n, int(fin * SR))
        x[:k] *= np.linspace(0, 1, k)[:, None]
    if fout > 0:
        k = min(n, int(fout * SR))
        x[n - k:] *= np.linspace(1, 0, k)[:, None]
    return x


def decay_after(x, start, tau):
    x = x.copy()
    n = np.arange(len(x)) - start
    x *= np.where(n > 0, np.exp(-n / (tau * SR)), 1.0)[:, None]
    return x


def pitch(x, semis):
    """Resample-pitch (changes duration too, like a tape)."""
    r = 2 ** (semis / 12)
    up, down = int(round(1000 / r)), 1000
    return resample_poly(x, up, down, axis=0)


def filt(x, kind, f, order=4):
    sos = butter(order, f, kind, fs=SR, output="sos")
    return sosfiltfilt(sos, x, axis=0)


def seg(x, t0, t1):
    return x[int(t0 * SR):int(t1 * SR)]


def stereo(m):
    return np.stack([m, m], axis=1)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


# ---------------- synthesised sounds ----------------
def sub_drop(dur=1.3, f0=95, f1=32, gain=1.0):
    n = int(dur * SR)
    f = f1 + (f0 - f1) * np.exp(-np.arange(n) / (0.25 * SR))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return stereo(np.sin(ph) * env_exp(n, dur / 3.5) * gain)


def thump(f=58, dur=0.35, click=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t * (1 - 0.35 * t / dur)) * np.exp(-t / (dur / 4))
    c = rng.standard_normal(n) * np.exp(-t / 0.004) * click
    return stereo(filt(stereo(body + c)[:, 0], "lowpass", 900, 2))


def heartbeat(t0, t1, bpm0, bpm1, gain=0.6):
    out, t = [], t0
    while t < t1:
        u = (t - t0) / max(t1 - t0, 1e-6)
        bpm = bpm0 + (bpm1 - bpm0) * u
        out.append((t, thump(52, 0.32), gain * (0.6 + 0.4 * u)))
        out.append((t + 60 / bpm * 0.28, thump(46, 0.30), gain * 0.7 * (0.6 + 0.4 * u)))
        t += 60 / bpm
    return out


def tick(freq=1900, dur=0.05):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2.7 * t)) * np.exp(-t / 0.006)
    x += rng.standard_normal(n) * np.exp(-t / 0.002) * 0.3
    return stereo(x * 0.5)


def beep(f, dur, gain=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6
    x = filt(stereo(x), "lowpass", 5000, 2)[:, 0]
    e = np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.01)
    return stereo(x * e * gain)


def alarm(t0, t1):
    """A generic digital alarm: bursts of four rising beeps."""
    out, t = [], t0
    while t < t1:
        for k, f in enumerate((1568, 1760, 1976, 2093)):
            out.append((t + k * 0.11, beep(f, 0.075, 0.22)))
        t += 0.62
    return out


def buzz(dur=0.42, gain=0.5):
    """Phone vibrating on a wooden surface."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * 172 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * t))
    x = filt(stereo(x), "bandpass", [120, 1800], 2)[:, 0]
    e = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.02)
    return stereo(x * e * gain)


def noise_swell(dur, f0=400, f1=6000, gain=0.5, reverse_cymbal=True):
    """Filtered-noise swell that rises into its end (reverse-cymbal / short riser)."""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        u = i / n
        fc = f0 * (f1 / f0) ** u
        sos = butter(2, min(fc, SR / 2.2), "highpass" if reverse_cymbal else "lowpass", fs=SR, output="sos")
        out[i:i + blk] = sosfilt(sos, x[i:i + blk])
    e = (np.arange(n) / n) ** 2.4
    return stereo(out * e * gain / (np.abs(out).max() + 1e-9))


def drone(dur, f0, f1, gain=0.25):
    """Detuned saw cluster sweeping up: tension under the storm / the tangle."""
    n = int(dur * SR)
    u = np.arange(n) / n
    acc = np.zeros(n)
    for det in (-0.7, 0, 0.6, 12.1, 7.02):
        f = f0 * (f1 / f0) ** u * 2 ** (det / 12)
        ph = np.cumsum(f) / SR
        acc += 2 * (ph % 1) - 1
    acc = filt(stereo(acc), "lowpass", 2400, 2)[:, 0]
    e = np.minimum(1, u / 0.15) * (0.4 + 0.6 * u)
    return stereo(acc / 5 * e * gain)


def ting(f=3300, dur=0.9, gain=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) + 0.2 * np.sin(2 * np.pi * f * 5.4 * t)) * np.exp(-t / 0.18)
    return stereo(x * gain)


def shutter(gain=0.6):
    out = np.zeros((int(0.12 * SR), 2))
    for d in (0.0, 0.055):
        n = int(0.03 * SR)
        t = np.arange(n) / SR
        c = filt(stereo(rng.standard_normal(n) * np.exp(-t / 0.004)), "bandpass", [1200, 7000], 2)
        i = int(d * SR)
        out[i:i + n] += c * gain
    return out


def blip(f0, f1, gain=0.25):
    return np.concatenate([beep(f0, 0.07, gain), np.zeros((int(0.02 * SR), 2)), beep(f1, 0.09, gain)])


def tape_stop(x, dur=0.32):
    """Slow the end of x to a halt over `dur` s (time-varying resample)."""
    n = int(dur * SR)
    if len(x) < n + 10:
        return x
    head, tail = x[:-n], x[-n:]
    rate = np.linspace(1, 0.02, n) ** 1.5
    pos = np.cumsum(rate)
    pos = pos[pos < n - 1]
    i = pos.astype(int)
    fr = (pos - i)[:, None]
    slow = tail[i] * (1 - fr) + tail[i + 1] * fr
    slow *= np.linspace(1, 0.0, len(slow))[:, None] ** 0.6
    return np.concatenate([head, slow, np.zeros((n - len(slow), 2))])


def rewind_audio(orig, dur):
    """The story so far, backwards and fast: tape chatter + motor whine + a final clunk."""
    src = seg(orig, 0.8, 56.0)[::-1]
    fast = resample_poly(src, 1, 46, axis=0)            # 46x speed (and pitch) — chatter
    n = int(dur * SR)
    fast = np.resize(fast, (n, 2)) if len(fast) < n else fast[:n]
    fast = filt(fast, "bandpass", [300, 7000], 2) * 0.55
    t = np.arange(n) / SR
    f = 260 + 900 * (t / dur) ** 1.4
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.12
    x = fast + stereo(whine)
    x *= np.minimum(1, t / 0.03)[:, None]
    return x


# ---------------- overlay-driven cues ----------------
def alpha_onsets(png_dir, t0, thresh=0.004, min_gap=0.05):
    """Times (output s) where an overlay's coverage jumps: a new card / tile arriving."""
    import cv2
    files = sorted(f for f in os.listdir(png_dir) if f.endswith(".png")) if os.path.isdir(png_dir) else []
    cov = []
    for f in files:
        a = cv2.imread(f"{png_dir}/{f}", cv2.IMREAD_UNCHANGED)
        cov.append(0.0 if a is None or a.shape[2] < 4 else float((a[::4, ::4, 3] > 128).mean()))
    cov = np.array(cov)
    out, last = [], -1
    for k in range(1, len(cov)):
        if cov[k] - cov[k - 1] > thresh and (k - last) / FPS > min_gap:
            out.append((t0 + k / FPS, cov[k] - cov[k - 1]))
            last = k
    return out


# ---------------- build ----------------
def stem_A(orig):
    """The source mix laid out on the output timeline."""
    A = np.zeros((int(TOTAL * SR) + SR, 2))
    for s in edl.LAYOUT:
        o = s["o"] / FPS
        n = s["n"] / FPS
        if s["audio"] == "orig":
            a, b = s.get("src_audio", (s["a"], s.get("b", s["a"])))
            x = seg(orig, a / FPS, b / FPS)
            if s["id"] in ("P6c_f", "P6d_f"):
                x = tape_stop(x, 0.30)                     # the music winds down into the name card
            x = fade(x, s.get("fade_in", 0.03), 0.03)
            place(A, x, o)
        elif s["audio"] == "rewind":
            place(A, fade(rewind_audio(orig, n), 0.02, 0.02), o, gain=0.9)
        elif s["audio"] == "tail":
            a, b = s["src_audio"]
            place(A, fade(seg(orig, a / FPS, b / FPS), 0.03, 1.4), o)
    return A


def stem_B(A):
    B = np.zeros_like(A)
    O = lambda sid: edl.BY_ID[sid]["o"] / FPS

    def impact(t, gain, name="impact-bass-2", tau=0.45):
        x = sfx(name)
        o = onset(x)
        place(B, decay_after(x, o + int(0.03 * SR), tau), t, o, gain)

    def whoosh(t, gain=0.35, pan=0.0, semis=0):
        x = pitch(sfx("whoosh"), semis) if semis else sfx("whoosh")
        place(B, x, t, int(0.16 * SR * 2 ** (-semis / 12)), gain, pan)     # peak on t

    def glitch(t, name="glitch-1", dur=0.35, gain=0.35):
        x = sfx(name)
        o = onset(x)
        place(B, fade(x[o:o + int(dur * SR)], 0.003, 0.06), t, 0, gain)

    def ping(t, gain=0.3, semis=0.0, name="notification", pan=0.0):
        x = pitch(sfx(name), semis) if semis else sfx(name)
        o = onset(x)
        place(B, fade(x[o:], 0, 0.3), t, 0, gain, pan)

    # ---- hook ----
    impact(0.25, 0.45, "impact-bass-1", 0.30)
    whoosh(0.22, 0.25)
    impact(0.80, 0.55, "impact-bass-2", 0.40)
    glitch(0.80, "glitch-1", 0.30, 0.30)
    place(B, sub_drop(1.0, 80, 30, 0.5), 0.80)
    glitch(3.36, "glitch-3", 0.11, 0.35)
    # ---- rewind lands on the alarm ----
    place(B, thump(70, 0.25, 0.6), O("P1a"), 0, 0.8)
    impact(O("P1a"), 0.55, "impact-bass-2", 0.6)
    for t, b in alarm(O("P1a") + 0.10, O("P1b")):
        place(B, b, t)
    for t, b in alarm(O("P1b"), O("P1b") + 0.95):                     # muffled: he's asleep
        place(B, filt(b, "lowpass", 900, 2) * 0.6, t)
    place(B, buzz(0.42, 0.35), O("P1a") + 0.18)
    place(B, buzz(0.42, 0.30), O("P1a") + 0.80)
    whoosh(O("P1a") + 0.30, 0.30, 0, -3)                               # crash zoom
    whoosh(O("P1b") + 0.95, 0.25, 0, 2)                                # eyes open
    # a bed under the wordless intro, so it never drops to digital silence: room tone + a low tension drone
    n_bed = int((O("P1e") + 0.6 - O("P1a")) * SR)
    room = filt(stereo(rng.standard_normal(n_bed)), "bandpass", [70, 2200], 2)
    place(B, fade(room / np.abs(room).max(), 0.4, 0.6), O("P1a"), 0, 0.022)
    place(B, fade(drone(n_bed / SR, 55, 78, 0.20), 1.2, 0.6), O("P1a"))
    for k in range(int((O("P1e") - O("P1b")) / 0.5)):                  # the clock is running
        place(B, tick(1900 if k % 2 == 0 else 1500), O("P1b") + k * 0.5, 0, 0.18 + 0.02 * k)
    whoosh(O("P1c") + 0.05, 0.40, -0.3, -2)
    whoosh(O("P1c") + 0.70, 0.30, 0.3, 1)
    whoosh(O("P1d") + 0.05, 0.30, 0.2, 0)
    for t, x, g in heartbeat(O("P1e"), 15.0, 72, 104, 0.55):
        place(B, x, t, 0, g)
    r = sfx("riser")
    place(B, fade(r, 0.6, 0.05)[: int(3.04 * SR) + 200], 13.21, int(3.04 * SR), 0.35)   # crest on "F*ck"
    # ---- panic ----
    impact(13.21, 0.75, "impact-bass-2", 0.55)
    impact(13.21, 0.45, "impact-bass-1", 0.30)
    place(B, sub_drop(1.4, 90, 30, 0.6), 13.21)
    glitch(13.21, "glitch-3", 0.20, 0.25)
    impact(14.80, 0.40, "impact-bass-1", 0.25)                         # 08:00:00 slams in
    place(B, beep(1000, 0.08, 0.12), 14.80)
    for k in range(1, int((O("P4") - 15.07))):                         # HUD ticking until the call connects
        place(B, tick(2100), 15.07 + k, 0, 0.08)
    whoosh(O("P3"), 0.30, 0.3)
    ping(15.90, 0.18, 4, "pop")                                        # calling card slides in
    place(B, sfx("click-soft"), 21.26, onset(sfx("click-soft")), 0.14)  # connected: a soft click on the green pulse, under the voice
    place(B, tick(1200, 0.04), 22.0, 0, 0.25)
    impact(25.01, 0.35, "impact-bass-1", 0.22)                         # "today"
    ping(26.20, 0.20, 0, "pop")                                        # "notes?"
    place(B, blip(660, 440, 0.16), 44.40)                              # call ended
    # ---- breakdown + storm ----
    impact(44.65, 0.55, "impact-bass-1", 0.30)
    x = sfx("whoosh-cinematic")
    place(B, fade(x, 0, 0.4), 44.66, int(2.55 * SR), 0.35)             # cards blow apart
    impact(45.20, 0.80, "impact-bass-2", 0.55)
    glitch(45.20, "glitch-2", 0.40, 0.35)
    place(B, sub_drop(1.6, 85, 28, 0.7), 45.20)
    glitch(46.36, "glitch-1", 0.18, 0.25)
    place(B, drone(51.80 - 45.5, 55, 220, 0.22), 45.5)
    for t, x, g in heartbeat(46.0, 51.8, 96, 168, 0.65):
        place(B, x, t, 0, g)
    t, k = 44.65, 0                                                     # the HUD clock racing
    while t < 51.45:
        place(B, tick(2300 - (k % 3) * 300, 0.035), t, 0, 0.13)
        t += max(0.045, 0.32 * 0.93 ** k)
        k += 1
    for th in (49.83, 50.94):                                          # an hour falls off the racing clock
        place(B, thump(64, 0.4, 0.5), th, 0, 0.55)
        place(B, tick(900, 0.06), th, 0, 0.30)
    glitch(51.45, "glitch-2", 0.38, 0.55)
    xr = sfx("whoosh")[::-1]
    place(B, xr, O("P6a"), len(xr) - int(0.16 * SR), 0.5)              # sucked out...
    # ---- the founders: calm, cool ----
    place(B, sub_drop(2.2, 70, 26, 0.9), O("P6a"))                    # ...into a deep, clean boom
    impact(O("P6a"), 0.55, "impact-bass-2", 0.9)
    for tg, gx, gy, size, dur in D.GLINT:
        place(B, ting(3300, 0.9, 0.22), tg + 0.05)
        x = sfx("sparkle")
        place(B, x, tg, onset(x), 0.35, 0.1)
    impact(54.88, 0.40, "impact-bass-1", 0.30)                         # "SHELF." lands
    place(B, sfx("sparkle"), 54.95, 0, 0.20)
    whoosh(57.60, 0.22, 0, 3)                                          # "y'all"
    for tn in (60.83, 66.30):                                          # giant names rise
        place(B, noise_swell(0.55, 600, 9000, 0.25), tn - 0.55)
        impact(tn, 0.40, "impact-bass-1", 0.35)
    for fz, nxt in ((O("P6c_f"), O("P6d")), (O("P6d_f"), O("P7"))):    # freeze-frame name cards
        place(B, shutter(0.55), fz)
        impact(fz, 0.55, "impact-bass-2", 0.6)
        place(B, noise_swell(0.7, 500, 8000, 0.30), nxt - 0.7)         # reverse swell back into the music
        impact(nxt, 0.35, "impact-bass-1", 0.25)
    # ---- the problem ----
    impact(79.45, 0.40, "impact-bass-1", 0.25)                         # "all of it"
    place(B, drone(2.3, 110, 160, 0.16), 80.6)                         # the tangle tightens
    glitch(82.18, "glitch-1", 0.30, 0.35)
    impact(82.18, 0.45, "impact-bass-2", 0.35)
    xr = pitch(sfx("whoosh"), 3)[::-1]
    place(B, xr, O("P8"), len(xr), 0.45)                               # everything vanishes
    x = sfx("chime")
    place(B, x, O("P8") + 0.05, onset(x), 0.16)                        # calm
    place(B, x, 85.75, onset(x), 0.22)                                 # "simple"
    # ---- the payoff ----
    place(B, noise_swell(0.9, 300, 10000, 0.40), 88.13 - 0.9)
    impact(88.13, 0.85, "impact-bass-2", 0.7)
    impact(88.13, 0.50, "impact-bass-1", 0.4)
    place(B, sub_drop(2.0, 90, 28, 0.8), 88.13)
    place(B, sfx("sparkle"), 88.40, 0, 0.28)
    x = sfx("whoosh-cinematic")
    place(B, fade(x[int(2.55 * SR):], 0, 0.8), 88.13, 0, 0.30)
    # "in one place": the tiles fly in, stack, dock
    for k in range(6):
        whoosh(89.50 + k * 0.07, 0.18, (-1) ** k * 0.6, k - 2)
    for k in range(6):
        place(B, sfx("click-soft"), 90.71 + k * 0.11, onset(sfx("click-soft")), 0.18, (k - 2.5) / 4)
    place(B, sfx("click"), 91.50, onset(sfx("click")), 0.22)
    x = sfx("chime")
    place(B, x, 92.19, onset(x), 0.30)
    place(B, sfx("sparkle"), 92.19, 0, 0.30)
    # ---- tease into STAY TUNED (the card brings its own riser + boom) ----
    place(B, noise_swell(1.2, 300, 8000, 0.30), 95.70 - 1.2)
    glitch(95.70, "glitch-3", 0.30, 0.40)
    # ---- whips ----
    for tw, dxn in D.WHIP:
        whoosh(tw, 0.30, 0.5 * dxn, rng.uniform(-2, 2))

    # ---- cues from the overlays themselves ----
    import composite
    cues = {d.split("/")[2]: alpha_onsets(d, t0) for d, t0, _ in composite.OVERLAYS}   # e.g. "cards", "storm"
    for t, dcov in cues.get("cards", []):
        if t < 44.4:
            ping(t, 0.32, 0, "notification", rng.uniform(-0.3, 0.3))
    for name, lo, hi in (("storm_hook", 0, 3.4), ("storm", 44.6, 51.45)):
        for t, dcov in cues.get(name, []):
            if lo <= t < hi:
                u = (t - lo) / (hi - lo)
                ping(t, 0.16 + 0.10 * u, rng.uniform(-3, 5), "notification" if rng.random() < 0.6 else "ping", rng.uniform(-0.7, 0.7))
    for t, dcov in cues.get("problem", []):
        if t < 83.3:
            x = sfx("pop")
            place(B, x, t, onset(x), 0.18 + min(0.2, dcov * 4), rng.uniform(-0.6, 0.6))
    return B, cues


def master(mix):
    mix = filt(mix, "highpass", 30, 2)
    tmp = OUT + ".raw.wav"
    write(tmp, mix / max(1.0, np.abs(mix).max() / 0.98))
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
                    f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
                    f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.891:level=disabled",
                    "-ar", str(SR), "-c:a", "pcm_s24le", OUT], check=True)
    os.remove(tmp)


def write(path, x):
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    orig = load("renders/source_audio.wav")
    A = stem_A(orig)
    B, cues = stem_B(A)
    n = int(TOTAL * SR)
    A, B = A[:n], B[:n]
    write("renders/stem_A.wav", A)
    write("renders/stem_B.wav", B / max(1.0, np.abs(B).max()))
    mix = A * 1.0 + B * 0.9
    master(mix)
    print("cues:", {k: len(v) for k, v in cues.items()})
    print("->", OUT)


if __name__ == "__main__":
    main()
