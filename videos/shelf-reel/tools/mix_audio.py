"""Sound for the S.H.E.L.F reel, v2: the dialogue, the song, and sound design on the song's grid.

Three stems, then a master:
  D  dialogue: renders/dialogue.wav (the team's mix minus the song, see dialogue.py) re-cut to the
     EDL with 30 ms fades at every join; the cold-open rewind is tape chatter of the original mix.
  M  the song, laid out by music.py (hook / story / drop 2), with a speech-band carve: under
     dialogue its 250 Hz-5 kHz band ducks ~9 dB while the kick and 808 stay, so the drops keep
     their weight and every line stays clear.
  B  sound design: every camera hit / whip / glitch / flash in direction.py gets its sound on the
     same frame; message pops are placed where the overlay renders actually show a new card or
     bubble (alpha onsets). Nothing tonal that could fight the song's key; the silence before
     drop 2 stays silent.
Master: 30 Hz high-pass, peak limiter, two-pass loudnorm to -14 LUFS / -1 dBTP (Instagram).

  python3 tools/mix_audio.py   ->  renders/mix.wav (+ renders/mix_nomusic.wav: D + B only)
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
import music as MU  # noqa: E402

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


def wa_pop(gain=0.3, up=True):
    """A chat-app message pop: two short rounded tones (rising for incoming, falling for sent)."""
    out = np.zeros((int(0.16 * SR), 2))
    for k, f in enumerate((990, 1480) if up else (1320, 880)):
        n = int(0.055 * SR)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * f * t * (1 + 0.06 * t / 0.055)) * np.minimum(1, t / 0.002) * np.exp(-t / 0.016)
        i = int(k * 0.052 * SR)
        out[i:i + n] += stereo(x)
    return out * gain


def speech_env(d):
    """0..1 dialogue presence (any level, quiet words included): 300-3400 Hz RMS in 10 ms hops,
    fast attack, 350 ms release."""
    band = filt(d.mean(axis=1), "bandpass", [300, 3400], 2)
    hop = SR // 100
    k = len(band) // hop
    rms = np.sqrt((band[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    ref = np.percentile(db[db > -70], 90)                     # loud speech
    on = np.clip((db - (ref - 36)) / 10, 0, 1)                # -36 dB under loud speech -> 0, -26 -> 1
    env, a, r = np.zeros(k), 1 - np.exp(-1 / 2.0), 1 - np.exp(-1 / 35.0)
    for i in range(k):
        prev = env[i - 1] if i else 0.0
        env[i] = prev + (a if on[i] > prev else r) * (on[i] - prev)
    return np.repeat(env, hop)[:len(d)] if len(env) else np.zeros(len(d))


def level_dialogue(d, target=-23.0, lo=-4.0, hi=7.0):
    """Ride the dialogue fader: pull quiet words up and loud ones down toward `target` (speech-band
    dB), 60% of the way, only where somebody is speaking."""
    band = filt(d.mean(axis=1), "bandpass", [300, 3400], 2)
    hop = SR // 100
    k = len(band) // hop
    db = 20 * np.log10(np.sqrt((band[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-12))
    ref = np.percentile(db[db > -70], 90)
    talk = db > ref - 30
    want = np.where(talk, np.clip((target - db) * 0.6, lo, hi), 0.0)
    g, a, r = np.zeros(k), 1 - np.exp(-1 / 3.0), 1 - np.exp(-1 / 20.0)
    for i in range(k):
        prev = g[i - 1] if i else 0.0
        g[i] = prev + (a if want[i] < prev else r) * (want[i] - prev)    # quick to duck, slower to lift
    gain = 10 ** (np.repeat(g, hop) / 20)
    out = d.copy()
    out[:len(gain)] *= gain[:, None]
    return out


def censor_spans():
    """Output-time spans of the f-word (from words.json). Strong language keeps a reel out of
    teen recommendations, so it is muted under a WhatsApp ping; the captions already star it."""
    out = []
    for c in json.load(open("renders/words.json")):
        for w in c["words"]:
            if "*" in w["w"] and w["w"].lower().strip(".,!?").endswith("ck"):
                out.append((w["t0"] - 0.012, w["t1"] + 0.02))
    return out


def mute(x, spans, ramp=0.008):
    x = x.copy()
    g = np.ones(len(x))
    r = int(ramp * SR)
    for a, b in spans:
        i, j = int(a * SR), int(b * SR)
        g[i:j] = 0
        g[max(0, i - r):i] = np.minimum(g[max(0, i - r):i], np.linspace(1, 0, i - max(0, i - r)))
        g[j:j + r] = np.minimum(g[j:j + r], np.linspace(0, 1, len(g[j:j + r])))
    return x * g[:, None]


def carve(m, env, mid_db=-11.0, edge_db=-4.5):
    """Duck the music's speech band under the dialogue, keep its lows and highs mostly intact."""
    low = filt(m, "lowpass", 250, 4)
    high = filt(m, "highpass", 5000, 4)
    mid = m - low - high
    e = env[:len(m), None]
    g_mid = 10 ** (mid_db * e / 20)
    g_edge = 10 ** (edge_db * e / 20)
    return (low + high) * g_edge + mid * g_mid


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
    out, last = [], -10 ** 9
    for k in range(1, len(cov)):
        if cov[k] - cov[k - 1] > thresh and (k - last) / FPS > min_gap:
            out.append((t0 + k / FPS, cov[k] - cov[k - 1]))
            last = k
    return out


# ---------------- build ----------------
# The picture shows exactly EDL frame f (composite.Source seeks half a frame early), so the source
# audio is read at the same source times. Kept as a named constant: if the decode ever changes, this
# is the one place the audio must follow it.
PICTURE_OFFSET = 0.0


def stem_D(dlg, orig):
    """The dialogue laid out on the output timeline, in sync with the picture."""
    A = np.zeros((int(TOTAL * SR) + SR, 2))
    for s in edl.LAYOUT:
        o = s["o"] / FPS
        n = s["n"] / FPS
        if s["audio"] == "orig":
            a, b = s.get("src_audio", (s["a"], s.get("b", s["a"])))
            x = seg(dlg, a / FPS + PICTURE_OFFSET, b / FPS + PICTURE_OFFSET)
            place(A, fade(x, s.get("fade_in", 0.03), 0.03), o)
        elif s["audio"] == "rewind":
            place(A, fade(rewind_audio(orig, n), 0.02, 0.02), o, gain=0.9)
        elif s["audio"] == "tail":
            a, b = s["src_audio"]
            place(A, fade(seg(dlg, a / FPS + PICTURE_OFFSET, b / FPS + PICTURE_OFFSET), 0.03, 1.4), o)
    return A


MUSIC_GAIN = {"hook": 0.24, "story": 0.20, "drop2": 0.22}     # the song file is mastered loud; their edit sat it at 0.133


def stem_M(song):
    """The song laid out by music.py. Each section starts on its own fade; the story section
    tape-stops into the turn, where the breakdown takes over."""
    M = np.zeros((int(TOTAL * SR) + SR, 2))
    for name, a, b, s0 in MU.MAP:
        if s0 is None:
            continue
        x = seg(song, s0, s0 + (b - a))
        if name == "story":
            x = fade(tape_stop(x, 0.24), 0.25, 0.0)            # in after the rewind; winds down into the turn
        elif name == "hook":
            x = fade(x, 0.005, 0.015)
        else:
            x = fade(x, 0.010, 0.04)                             # the reel loops into the hook on the beat
        place(M, x, a, 0, MUSIC_GAIN[name])
    return M


def stem_B(A):
    B = np.zeros_like(A)
    O = lambda sid: edl.BY_ID[sid]["o"] / FPS
    V = edl.from_v1

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

    # ---- hook: the song's pickup bar, drop 1 lands on "f*ck" ----
    place(B, wa_pop(0.34), 0.0)                                        # frame 1 pings (so does the last: the loop)
    whoosh(1.967, 0.26, 0.4, 2)                                        # "scattered": the pile is flung
    impact(0.25, 0.40, "impact-bass-1", 0.30)
    whoosh(0.22, 0.22)
    impact(0.80, 0.50, "impact-bass-2", 0.40)
    glitch(0.80, "glitch-1", 0.30, 0.28)
    glitch(3.36, "glitch-3", 0.11, 0.35)
    # ---- rewind lands on the alarm (the real alarm is in the dialogue) ----
    place(B, thump(70, 0.25, 0.6), O("P1a"), 0, 0.7)
    impact(O("P1a"), 0.50, "impact-bass-2", 0.6)
    place(B, buzz(0.42, 0.30), O("P1a") + 0.18)
    place(B, buzz(0.42, 0.26), O("P1a") + 0.80)
    whoosh(O("P1a") + 0.30, 0.28, 0, -3)                               # crash zoom
    whoosh(O("P1b") + 0.95, 0.22, 0, 2)                                # eyes open
    for k in range(int((O("P1e") - O("P1b")) / 0.5)):                  # the clock is running
        place(B, tick(1900 if k % 2 == 0 else 1500), O("P1b") + k * 0.5, 0, 0.12 + 0.015 * k)
    whoosh(O("P1c") + 0.05, 0.36, -0.3, -2)
    whoosh(O("P1c") + 0.70, 0.26, 0.3, 1)
    whoosh(O("P1d") + 0.05, 0.26, 0.2, 0)
    for t, x, g in heartbeat(O("P1e"), 13.0, 72, 104, 0.45):
        place(B, x, t, 0, g)
    r = sfx("riser")
    place(B, fade(r, 0.6, 0.05)[: int(3.04 * SR) + 200], 13.21, int(3.04 * SR), 0.30)   # crest on "F*ck"
    # ---- panic ----
    impact(13.21, 0.70, "impact-bass-2", 0.55)
    impact(13.21, 0.40, "impact-bass-1", 0.30)
    place(B, sub_drop(1.4, 90, 30, 0.35), 13.21)
    glitch(13.21, "glitch-3", 0.20, 0.25)
    impact(14.80, 0.38, "impact-bass-1", 0.25)                         # 08:00:00 slams in
    for k in range(1, int((O("P4") - 15.07))):                         # HUD ticking until the call connects
        place(B, tick(2100), 15.07 + k, 0, 0.07)
    whoosh(O("P3"), 0.28, 0.3)
    place(B, wa_pop(0.16), 15.90)                                      # call screen slides in
    place(B, sfx("click-soft"), 21.26, onset(sfx("click-soft")), 0.14)  # connected
    impact(25.01, 0.32, "impact-bass-1", 0.22)                         # "today"
    place(B, blip(660, 440, 0.15), 44.40)                              # call ended
    # ---- breakdown: the song's hi-hat build, then the bass drops out ----
    impact(44.65, 0.50, "impact-bass-1", 0.30)
    x = sfx("whoosh-cinematic")
    place(B, fade(x, 0, 0.4), 44.66, int(2.55 * SR), 0.30)
    impact(45.20, 0.75, "impact-bass-2", 0.55)
    glitch(45.20, "glitch-2", 0.40, 0.32)
    glitch(46.36, "glitch-1", 0.18, 0.22)
    gap = MU.GAP1 - MU.MAP[2][3] + MU.MAP[2][1]                       # the bass leaves (output s)
    for t, k in MU.grid(44.65, 51.45, sub=2):                         # the racing clock ticks on the song's 8ths,
        place(B, tick(2300 - int(k * 2) % 3 * 300, 0.035), t, 0, 0.10)
    for t, k in MU.grid(gap, 51.45, sub=4):                           # then 16ths once the bass is gone
        if abs(k * 2 - round(k * 2)) > 1e-6:
            place(B, tick(2600, 0.03), t, 0, 0.07)
    for t, k in MU.grid(gap, 50.45):                                  # a heartbeat fills the bass's absence
        place(B, thump(52, 0.32), t, 0, 0.55)
        place(B, thump(46, 0.30), t + 0.12, 0, 0.38)
    glitch(51.45, "glitch-2", 0.38, 0.50)
    xr = sfx("whoosh")[::-1]
    place(B, xr, O("P6a"), len(xr) - int(0.16 * SR), 0.45)             # sucked out...
    # ---- drop 1: the founders ----
    impact(O("P6a"), 0.60, "impact-bass-2", 0.9)                      # ...into the drop
    place(B, sub_drop(1.6, 70, 26, 0.35), O("P6a"))
    for tg, gx, gy, size, dur in D.GLINT:
        place(B, ting(3300, 0.9, 0.18), tg + 0.05)
        x = sfx("sparkle")
        place(B, x, tg, onset(x), 0.30, 0.1)
    impact(54.88, 0.36, "impact-bass-1", 0.30)                         # "SHELF." lands
    place(B, sfx("sparkle"), 54.95, 0, 0.18)
    whoosh(57.60, 0.20, 0, 3)                                          # "y'all"
    for tn in (60.83, V(66.30)):                                       # giant names rise
        place(B, noise_swell(0.55, 600, 9000, 0.20), tn - 0.55)
        impact(tn, 0.36, "impact-bass-1", 0.35)
    for fz, nxt in ((O("P6c_f"), O("P6d")), (O("P6d_f"), O("P7"))):    # freeze-frame name cards, on the beat
        place(B, shutter(0.50), fz)
        impact(fz, 0.55, "impact-bass-2", 0.6)
        place(B, noise_swell(0.6, 500, 8000, 0.18), nxt - 0.6)
        whoosh(nxt, 0.22, 0, -1)
    # ---- the problem ----
    impact(V(79.45), 0.36, "impact-bass-1", 0.25)                      # "all of it"
    glitch(V(82.18), "glitch-1", 0.30, 0.32)
    impact(V(82.18), 0.42, "impact-bass-2", 0.35)
    xr = pitch(sfx("whoosh"), 3)[::-1]
    place(B, xr, O("P8"), len(xr), 0.40)                               # everything vanishes; the song resets
    impact(O("P8"), 0.30, "impact-bass-1", 0.35)
    # ---- the payoff: the song's own silence on "so we built", drop 2 on "S.H.E.L.F" ----
    impact(MU.SHELF_WORD, 0.80, "impact-bass-2", 0.7)
    impact(MU.SHELF_WORD, 0.45, "impact-bass-1", 0.4)
    place(B, sfx("sparkle"), MU.SHELF_WORD + 0.27, 0, 0.26)
    x = sfx("whoosh-cinematic")
    place(B, fade(x[int(2.55 * SR):], 0, 0.8), MU.SHELF_WORD, 0, 0.26)
    # "in one place": the S.H.E.L.F chat (its message pops come from the overlay, below)
    x = sfx("chime")
    place(B, x, V(92.19), onset(x), 0.22)
    # ---- tease into STAY TUNED (the card brings its own riser + boom) ----
    place(B, noise_swell(1.2, 300, 8000, 0.24), V(95.70) - 1.2)
    glitch(V(95.70), "glitch-3", 0.30, 0.38)
    # ---- whips ----
    for tw, dxn in D.WHIP:
        whoosh(tw, 0.28, 0.5 * dxn, rng.uniform(-2, 2))

    # ---- the f-word, bleeped by a WhatsApp ping ----
    for a_, b_ in censor_spans():
        place(B, wa_pop(0.55), a_ + 0.01)
        place(B, pitch(wa_pop(0.30), 7), a_ + 0.09)
    # ---- the racing clock loses whole hours on the 808 pickups ----
    for th in (49.385, 50.609, 51.221):
        place(B, thump(110, 0.18, 0.8), th, 0, 0.45)
        place(B, tick(900, 0.06), th, 0, 0.32)
    # ---- the loop: the last frame pings like the first ----
    place(B, wa_pop(0.34), TOTAL - 0.20)

    # ---- cues from the overlays themselves ----
    import composite
    gaps = {"cards": 0.4, "problem": 0.08, "oneplace": 0.10}  # a sliding card can register on consecutive frames: one pop each
    cues = {d.split("/")[2]: alpha_onsets(d, t0, min_gap=gaps.get(d.split("/")[2], 0.05)) for d, t0, *_ in composite.OVERLAYS}
    for t, dcov in cues.get("cards", []):
        if t < 44.3:                                   # the 44.4 tremble is not an arrival
            place(B, wa_pop(0.30), t, 0, 1.0, rng.uniform(-0.3, 0.3))
    for name, lo, hi in (("storm_hook", 0, 3.4), ("storm", 44.6, 51.45)):
        for t, dcov in cues.get(name, []):
            if lo <= t < hi:
                u = (t - lo) / (hi - lo)
                place(B, pitch(wa_pop(0.14 + 0.08 * u), rng.uniform(-2, 4)), t, 0, 1.0, rng.uniform(-0.7, 0.7))
    burst = edl.out_time(89.967, "P7")                    # the orbit bursts on this cut: the whip whoosh covers it
    for t, dcov in cues.get("problem", []):
        if t < O("P8") - 0.05 and abs(t - burst) > 0.05:
            place(B, wa_pop(0.14 + min(0.14, dcov * 3)), t, 0, 1.0, rng.uniform(-0.6, 0.6))
    for t, dcov in cues.get("oneplace", []):
        place(B, wa_pop(0.20, up=True), t, 0, 1.0, rng.uniform(-0.3, 0.3))
    for t, dcov in cues.get("cta_end", [])[:1]:          # the "send this to..." bubble arrives
        whoosh(t - 0.02, 0.22, 0, 3)
        place(B, wa_pop(0.34, up=True), t)
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
    import soundfile as sf
    orig = load("renders/source_audio.wav")
    dlg = load("renders/dialogue.wav")
    song = load("renders/song.mp3")
    Dl = stem_D(dlg, orig)
    M = stem_M(song)
    B, cues = stem_B(Dl)
    n = int(TOTAL * SR)
    Dl, M, B = Dl[:n], M[:n], B[:n]
    Dl = mute(level_dialogue(Dl), censor_spans())
    env = speech_env(Dl)
    Mc = carve(M, env)
    Bc = carve(B, env, -6.0, -2.0) * 0.70
    for name, x in (("D", Dl), ("M", Mc), ("B", Bc)):               # float stems, exactly as mixed
        sf.write(f"renders/stem_{name}.wav", x.astype(np.float32), SR, subtype="FLOAT")
    master(Dl + Mc + Bc)
    global OUT
    full, OUT = OUT, "renders/mix_nomusic.wav"             # for posting without the song (if it gets muted)
    master(Dl + Bc)
    OUT = full
    print("cues:", {k: len(v) for k, v in cues.items()})
    print("->", full, "and renders/mix_nomusic.wav")


if __name__ == "__main__":
    main()
