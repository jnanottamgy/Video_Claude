"""The sound of the SHELF CAMPUS reel: studio dialogue, the song re-cut to the story, and dense sound design.

Stems, then a master:
  D  dialogue: lines cut from renders/audio/dialogue_src.wav (tools/dialogue.py: denoised, EQ'd, de-essed),
     30 ms fades at every edge, each line levelled to the same loudness (Kartik sits 12-20 dB under
     Jnanottam in the original), then a compressor (3:1, 6 ms / 110 ms), light saturation and a soft
     ceiling. The f-word is replaced by the library's radio beep over a matched 1.8 kHz tone.
  M  the song (edl.MUSIC): the muffled intro looped one bar, a tape stop into the freeze, drop 1 on the
     name, the bass stop on the cut to black, drop 2 on "SHELF". Ducked and speech-band carved under
     dialogue; dipped and low-passed for the payoff freeze.
  B  sound design: the SFX library (library/sfx: whooshes, impacts, slashes, risers, glitches, the tape
     stop) placed by their hit points on every cut, slam and pop, plus synthesised UI sounds (message
     sends/receives, notification chimes, typing, error dings, a police whoop, camera shutters).
Master: 30 Hz high-pass, gentle bus glue, two-pass loudnorm to -14 LUFS / -1 dBTP (Instagram).

  python3 tools/mix.py   ->  renders/audio/mix.wav, mix_nomusic.wav, stem_{D,M,B}.wav
"""
import json
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl  # noqa: E402
import sfx as LIB  # noqa: E402

SR = 48000
TOTAL = edl.DURATION
N = int(round(TOTAL * SR))
OUTDIR = "renders/audio"
rng = np.random.default_rng(1729)
METER = pyln.Meter(SR)


# ---------------- helpers ----------------
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def filt(x, kind, f, order=4):
    return sosfiltfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def stereo(m):
    return np.stack([m, m], axis=1)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = len(x)
    if fin > 0:
        k = min(n, int(fin * SR))
        x[:k] *= np.linspace(0, 1, k)[:, None] if x.ndim == 2 else np.linspace(0, 1, k)
    if fout > 0:
        k = min(n, int(fout * SR))
        x[n - k:] *= np.linspace(1, 0, k)[:, None] if x.ndim == 2 else np.linspace(1, 0, k)
    return x


def place(buf, x, t, align=0, gain_db=0.0, pan=0.0):
    """Mix x into buf so that sample `align` of x lands at time t (s)."""
    if len(x) == 0:
        return
    if x.ndim == 1:
        x = stereo(x)
    i = int(round(t * SR)) - align
    a, b = max(0, i), min(len(buf), i + len(x))
    if b <= a:
        return
    th = (pan + 1) * np.pi / 4
    g = np.array([np.cos(th), np.sin(th)]) * np.sqrt(2) * 10 ** (gain_db / 20)
    buf[a:b] += x[a - i:b - i] * g


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def lufs(x):
    try:
        return METER.integrated_loudness(stereo(x) if x.ndim == 1 else x)
    except ValueError:
        return -70.0


# ---------------- the library ----------------
_lib = {}


def lib(sfx_id, t, gain_db=0.0, length=None, hp=None, lp=None, pan=0.0, fade_out=0.06, semis=0.0, dip=False,
        pre=None, t_from=None):
    """A library effect with its hit point on t (optionally trimmed, filtered, pitched). dip: cut its
    350 Hz-3.5 kHz band by ~12 dB, for hits that land on a spoken word (the drops land on names).
    pre: keep only `pre` s before the hit (drops land out of a vacuum, not out of the effect's own
    wind-up). t_from: drop whatever would sound before that output time (with a 60 ms fade in)."""
    if sfx_id not in _lib:
        _lib[sfx_id] = LIB.load(sfx_id, SR)
    x, hit = _lib[sfx_id]
    if semis:
        r = 2 ** (semis / 12)
        x = resample_poly(x, int(round(1000 / r)), 1000, axis=0)
        hit = hit / r
    if pre is not None and hit > pre:
        x = fade(x[int((hit - pre) * SR):], 0.004, 0)
        hit = pre
    if length is not None:
        x = fade(x[: int((hit + length) * SR)], 0, fade_out)
    if t_from is not None and t - hit < t_from:
        k = int((t_from - (t - hit)) * SR)
        x = fade(x[k:], 0.06, 0)
        hit -= k / SR
    if hp:
        x = filt(x, "highpass", hp, 2)
    if lp:
        x = filt(x, "lowpass", lp, 2)
    if dip:
        x = x - filt(x, "bandpass", [350, 3500], 2) * 0.75
    place(B, x, t, int(round(hit * SR)), gain_db, pan)


# ---------------- synthesised sounds ----------------
def tone(f, dur, decay, harm=((1, 1.0),), attack=0.002):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in harm)
    return x * np.minimum(1, t / attack) * np.exp(-t / decay)


def wa_send():
    """Outgoing message: a soft falling 'pop'."""
    out = np.zeros(int(0.14 * SR))
    for k, f in enumerate((1180, 790)):
        x = tone(f, 0.06, 0.018, ((1, 1.0), (2, 0.15)))
        i = int(k * 0.045 * SR)
        out[i:i + len(x)] += x
    return out * 0.55


def wa_receive():
    """Incoming message: two rising rounded tones."""
    out = np.zeros(int(0.2 * SR))
    for k, f in enumerate((880, 1320)):
        x = tone(f, 0.09, 0.03, ((1, 1.0), (2, 0.2), (3, 0.05)))
        i = int(k * 0.06 * SR)
        out[i:i + len(x)] += x
    return out * 0.5


def chime(notes=(1046.5, 1318.5, 1568.0), step=0.075, decay=0.22, gain=0.45):
    """A generic notification chime (not any platform's real sound): bell partials, short arpeggio."""
    out = np.zeros(int((step * len(notes) + 0.8) * SR))
    for k, f in enumerate(notes):
        x = tone(f, 0.8, decay, ((1, 1.0), (2.0, 0.35), (3.01, 0.12), (4.2, 0.06)))
        i = int(k * step * SR)
        out[i:i + len(x)] += x
    return out * gain / max(1e-9, np.abs(out).max())


def ping():
    """The one WhatsApp-style ping in the dark (with a little room)."""
    x = chime((1318.5, 1760.0), 0.09, 0.35, 0.5)
    y = np.zeros(len(x) + int(0.9 * SR))
    y[:len(x)] += x
    for d, g in ((0.11, 0.25), (0.23, 0.13), (0.37, 0.07)):          # a few early reflections
        i = int(d * SR)
        y[i:i + len(x)] += filt(stereo(x), "lowpass", 4000, 2)[:, 0] * g
    return y


def typing(dur, rate=11.0):
    out = np.zeros(int(dur * SR))
    t = 0.0
    while t < dur - 0.03:
        n = int(0.02 * SR)
        c = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.0025 * SR))
        c = sosfilt(butter(2, [1800, 6500], "bandpass", fs=SR, output="sos"), c)
        i = int(t * SR)
        out[i:i + n] += c * rng.uniform(0.5, 1.0)
        t += 1 / rate * rng.uniform(0.7, 1.3)
    return out * 0.35


def error_ding(f=622.0):
    return tone(f, 0.5, 0.12, ((1, 1.0), (2, 0.3), (2.98, 0.15))) * 0.5


def whoop(dur=0.55):
    """A police-siren chirp ('whoop'): a saw sweep up then down."""
    n = int(dur * SR)
    u = np.arange(n) / n
    f = 520 + 900 * np.sin(np.pi * np.clip(u * 1.25, 0, 1)) ** 1.5
    ph = np.cumsum(f) / SR
    x = (2 * (ph % 1) - 1) * 0.6 + np.sin(2 * np.pi * ph) * 0.4
    x = sosfilt(butter(2, [400, 3500], "bandpass", fs=SR, output="sos"), x)
    return x * np.minimum(1, u / 0.05) * np.minimum(1, (1 - u) / 0.15) * 0.5


def shutter():
    out = np.zeros(int(0.12 * SR))
    for d in (0.0, 0.05):
        n = int(0.03 * SR)
        c = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.004 * SR))
        c = sosfilt(butter(2, [1200, 7000], "bandpass", fs=SR, output="sos"), c)
        i = int(d * SR)
        out[i:i + n] += c * (1.0 if d == 0 else 0.7)
    return out * 0.6


def thunk(f=70, dur=0.25):
    """A pin / stamp body: low thump plus a paper slap."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t * (1 - 0.3 * t / dur)) * np.exp(-t / 0.05)
    slap = sosfilt(butter(2, [700, 5000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.012)
    return body * 0.8 + slap * 0.7


def zip_(dur=0.28, f0=900, f1=4200):
    """A string pulled taut / a line drawing: a band-passed noise sweep."""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 512):
        fc = f0 * (f1 / f0) ** (i / n)
        out[i:i + 512] = sosfilt(butter(2, [fc * 0.7, min(fc * 1.4, 20000)], "bandpass", fs=SR, output="sos"), x[i:i + 512])
    return out * np.sin(np.pi * np.arange(n) / n) * 0.5


def ticks(t0, t1, rate0, rate1, f=2400):
    out = []
    t = t0
    while t < t1:
        u = (t - t0) / max(1e-6, t1 - t0)
        out.append(t)
        t += 1 / (rate0 + (rate1 - rate0) * u)
    x = tone(f, 0.02, 0.004, ((1, 1.0), (2.7, 0.4)))
    return [(tt, x) for tt in out]


def bell_alarm(dur=0.7):
    """A small mechanical alarm-clock ring (hammer on two bells)."""
    out = np.zeros(int(dur * SR))
    t = 0.0
    while t < dur - 0.05:
        x = tone(2350, 0.06, 0.02, ((1, 1.0), (1.47, 0.6), (2.7, 0.3))) + tone(2100, 0.06, 0.02, ((1, 0.6),))
        i = int(t * SR)
        out[i:i + len(x)] += x
        t += 0.035
    return out * 0.3


def power_down(dur=0.35):
    n = int(dur * SR)
    u = np.arange(n) / n
    f = 600 * (1 - u) ** 2 + 40
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - u) ** 1.5 * 0.5


def data_sweep(dur=0.5, f0=300, f1=5000):
    n = int(dur * SR)
    u = np.arange(n) / n
    f = f0 * (f1 / f0) ** u
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * 0.3
    return sosfilt(butter(2, 7000, "lowpass", fs=SR, output="sos"), x) * np.sin(np.pi * u) ** 0.7 * 0.35


def sub_boom(dur=0.9, f0=90, f1=34):
    n = int(dur * SR)
    f = f1 + (f0 - f1) * np.exp(-np.arange(n) / (0.12 * SR))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, dur / 3.5) * 0.9


def reverse_swell(dur=0.6):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 512):
        fc = 500 * (9000 / 500) ** (i / n)
        out[i:i + 512] = sosfilt(butter(2, fc, "highpass", fs=SR, output="sos"), x[i:i + 512])
    return out * (np.arange(n) / n) ** 2.5 * 0.5


def tape_stop(x, dur=0.45):
    """Slow the end of x to a halt over `dur` seconds (time-varying resample, like a turntable)."""
    n = int(dur * SR)
    head, tail = x[:-n], x[-n:]
    rate = np.linspace(1, 0.02, n) ** 1.6
    pos = np.cumsum(rate)
    pos = pos[pos < n - 1]
    i = pos.astype(int)
    fr = (pos - i)[:, None]
    slow = tail[i] * (1 - fr) + tail[i + 1] * fr
    slow *= np.linspace(1, 0.0, len(slow))[:, None] ** 0.5
    return np.concatenate([head, slow, np.zeros((n - len(slow), 2))])


# ---------------- dynamics ----------------
def compressor(x, thr_db=-24.0, ratio=3.0, att=0.006, rel=0.110, knee=6.0, makeup_db=0.0):
    m = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    lvl = 20 * np.log10(m + 1e-9)
    over = lvl - thr_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, -over * (1 - 1 / ratio), -((over + knee / 2) ** 2) / (2 * knee) * (1 - 1 / ratio)))
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    g = np.zeros_like(gr)
    prev = 0.0
    for i in range(len(gr)):                       # gain computer smoothing (attack when reducing more)
        c = a if gr[i] < prev else r
        prev = c * prev + (1 - c) * gr[i]
        g[i] = prev
    gain = 10 ** ((g + makeup_db) / 20)
    return x * (gain[:, None] if x.ndim == 2 else gain)


def soft_clip(x, ceiling=0.89):
    return np.tanh(x / ceiling) * ceiling


def speech_env(d):
    """0..1 dialogue presence: 300-3400 Hz RMS in 10 ms hops, fast attack, 300 ms release."""
    band = filt(d.mean(axis=1), "bandpass", [300, 3400], 2)
    hop = SR // 100
    k = len(band) // hop
    db = 20 * np.log10(np.sqrt((band[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-12))
    ref = np.percentile(db[db > -70], 90)
    on = np.clip((db - (ref - 34)) / 10, 0, 1)
    env, a, r = np.zeros(k), 1 - np.exp(-1 / 2.0), 1 - np.exp(-1 / 30.0)
    for i in range(k):
        prev = env[i - 1] if i else 0.0
        env[i] = prev + (a if on[i] > prev else r) * (on[i] - prev)
    e = np.repeat(env, hop)
    return np.concatenate([e, np.full(max(0, len(d) - len(e)), 0.0)])[:len(d)]


# ---------------- stems ----------------
LINE_TARGET = -19.0          # LUFS per line before the stem compressor


def stem_D():
    src, _ = sf.read(os.path.join(OUTDIR, "dialogue_src.wav"))
    D = np.zeros((N + SR, 2))
    pieces = []
    for s in edl.SEGMENTS:
        if s["kind"] == "talk":
            pieces.append((s["src"], s["src"] + s["out1"] - s["out0"], s["out0"], s["id"]))
        for v in s.get("vo", []):
            pieces.append((v["src0"], v["src1"], v["out0"], s["id"] + "vo"))
    report = []
    b0, b1 = edl.BLEEP_SRC
    loud = {sid: lufs(src[int(round(a * SR)):int(round(b * SR))]) for a, b, o, sid in pieces}
    who = {s["id"]: s["who"] for s in edl.SEGMENTS}
    spk = {}
    for sid, L in loud.items():
        spk.setdefault(who.get(sid.replace("vo", ""), "VO"), []).append(L)
    spk = {k: float(np.median(v)) for k, v in spk.items()}
    for a, b, o, sid in pieces:
        x = src[int(round(a * SR)):int(round(b * SR))].copy()
        if a <= b0 < b:                                   # the bleep: silence the word under the beep
            i, j = int((b0 - a) * SR), int((b1 - a) * SR)
            r = int(0.006 * SR)
            g = np.ones(len(x))
            g[i:j] = 0
            g[i - r:i] = np.linspace(1, 0, r)
            g[j:j + r] = np.linspace(0, 1, r)
            x = x * g
        L = lufs(x)
        Ls = spk.get(who.get(sid.replace("vo", ""), "VO"), L)
        gain = np.clip(LINE_TARGET - (0.8 * L + 0.2 * Ls), -6, 20)    # 80% line-levelled, 20% speaker-levelled
        x = fade(x * 10 ** (gain / 20), 0.03, 0.03)       # 30 ms fades at every edge
        place(D, x, o, 0, 0.0)
        report.append((sid, round(L, 1), round(gain, 1)))
    D = D[:N]
    D = compressor(D, thr_db=-26, ratio=3.0, att=0.006, rel=0.11, makeup_db=3.0)
    D = D * 0.75 + soft_clip(D * 1.6, 0.9) / 1.6 * 0.25   # a little density
    return D, report


def bleep_sound():
    """The radio beep's attack over a steady 1.8 kHz tone, exactly the length of the word."""
    b0, b1 = edl.BLEEP_SRC
    t = edl.out_of_src(b0, "A2")
    dur = b1 - b0
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1800 * tt) * 0.30 * np.minimum(1, tt / 0.004) * np.minimum(1, (dur - tt) / 0.008)
    place(B, x, t, 0, -2.0)
    lib("radio-beep", t, -9.0, length=dur - 0.02, fade_out=0.02)


def stem_M(song):
    M = np.zeros((N + SR, 2))
    for k, (a, b, s0) in enumerate(edl.MUSIC):
        pre = 0.004 if k == 2 else 0.0                    # keep drop 1's first transient whole
        post = 0.010 if k == 0 else 0.0                   # the intro loop point: a 10 ms crossfade into bar 2 again
        x = song[int((s0 - pre) * SR):int((s0 + (b - a) + post) * SR)].copy()
        if k == 1:
            x = tape_stop(fade(x, 0.010, 0.0), 0.42)      # the record stops on the freeze
            x = fade(x, 0.0, 0.01)
        elif k == 0:
            x = fade(x, 0.003, 0.010)
        elif k == 3:
            x = fade(x, 0.002, 0.012)                     # ends on a bar line: the loop restarts the intro
        else:
            x = fade(x, 0.002, 0.006)
        place(M, x, a - pre)
    return M[:N]


SECTION_GAIN = [            # (from, music gain dB before ducking, duck depth dB under speech)
    (0.000, -3.0, 9.0),     # hook: the muffled intro under the problem (already dark: masks little)
    (edl.B_START, -5.0, 11.0),   # founders: drop 1 is 9 dB hotter than the intro
    (edl.R, -1.0, 9.0),     # the reveal: the breakdown, drop 2 under "SHELF"
    (27.433, -5.0, 11.0),   # "your AI-powered academic memory... that lives on WhatsApp"
    (32.10, -4.0, 11.0),    # the demo voice-over
    (45.50, -3.0, 10.0),    # payoff + CTA
    (56.967, 0.0, 0.0),     # end card
]
DROP_GUARD = 0.40           # each drop plays unducked for 400 ms (the name / "SHELF" rides on top), then ducks


def automate_music(M, env):
    t = np.arange(len(M)) / SR
    g_db = np.zeros(len(M))
    depth = np.zeros(len(M))
    for k, (t0, gdb, dd) in enumerate(SECTION_GAIN):
        t1 = SECTION_GAIN[k + 1][0] if k + 1 < len(SECTION_GAIN) else TOTAL + 1
        m = (t >= t0) & (t < t1)
        g_db[m], depth[m] = gdb, dd
    g_db = np.convolve(g_db, np.ones(2400) / 2400, "same")          # 50 ms crossfades between sections
    e = env[:len(M)].copy()
    for td in (edl.D, edl.D2):                                     # let each drop's transient through
        i, j = int(td * SR), int((td + DROP_GUARD) * SR)
        e[i:j] *= np.linspace(0, 1, j - i) ** 2
    duck = -depth * e
    # the payoff freeze: the music drops away (low-pass + dip) and snaps back on the beat
    f0, f1 = edl.out_of_src(61.74, "E4"), next(s for s in edl.SEGMENTS if s["id"] == "F1")["out0"]
    fz = (t >= f0) & (t < f1)
    g = 10 ** ((g_db + duck) / 20)
    out = M * g[:, None]
    low = filt(M, "lowpass", 260, 2) * g[:, None]
    w = np.zeros(len(M))
    w[fz] = np.minimum(1, (t[fz] - f0) / 0.05)
    out = out * (1 - w[:, None]) + low * 0.55 * w[:, None]
    return out


def carve(m, env, mid_db=-8.0, edge_db=-3.0):
    low = filt(m, "lowpass", 250, 4)
    high = filt(m, "highpass", 5000, 4)
    mid = m - low - high
    e = env[:len(m), None]
    return (low + high) * 10 ** (edge_db * e / 20) + mid * 10 ** (mid_db * e / 20)


# ---------------- the sound design ----------------
B = None


def syn(x, t, gain_db=0.0, pan=0.0, align=0):
    place(B, x, t, align, gain_db, pan)


def load_cues():
    p = os.path.join(edl.ROOT, "renders", "cues.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def design():
    """Every cue is (time, sound). Times are output seconds; most come from the slot builders' reports."""
    S = lambda sid: next(s for s in edl.SEGMENTS if s["id"] == sid)
    D, R, D2 = edl.D, edl.R, edl.D2

    # ---- HOOK: frame 1 is loud ----
    syn(sub_boom(0.8), 0.0, -6.0)
    lib("cinematic-electric-hit", 0.02, -15.0, length=0.9, hp=60)
    syn(whoop(0.5), 0.03, -12.0, 0.25)
    syn(whoop(0.45), 0.62, -17.0, -0.25)
    for tt, x in ticks(0.54, 1.40, 18, 34):                       # the storage counter rolls
        syn(x, tt, -24.0)
    syn(error_ding(415), 1.90, -12.0)                              # STORAGE FULL
    lib("alien-digital-glitch", 1.90, -19.0, length=0.30)
    lib("fast-swoosh", 2.46, -9.0, pan=-0.3)                       # the tape whips off
    lib("woosh-3", 2.50, -12.0, pan=0.3)
    bleep_sound()
    syn(error_ding(330), edl.out_of_src(5.62, "A2"), -12.0)        # "No results found"
    syn(thunk(55, 0.3), edl.out_of_src(5.62, "A2"), -10.0)
    # evidence board: a camera shutter + pin per exhibit, string draws
    for t in (4.37, 5.57, 7.27):
        syn(shutter(), t - 0.03, -8.0, 0.2)
        syn(thunk(90, 0.18), t, -11.0)
    syn(zip_(0.3), 5.65, -13.0, 0.1)
    syn(zip_(0.25, 1100, 5000), 7.65, -14.0, -0.1)
    syn(zip_(0.25, 1100, 5000), 8.23, -14.0, 0.2)
    lib("woosh-2", S("A3b")["out0"], -14.0, length=0.6)            # the punch-in
    syn(bell_alarm(0.75), 7.83, -10.0, 0.3)                        # the deadline clock rings
    lib("sword-slash-3", 8.49, -17.0)                              # "Bro"
    lib("cinematic-electric-hit", 9.42, -15.0, length=0.45, hp=80, dip=True)   # "assignment!": UNSOLVED slap
    # the record stops, the freeze, two stamps in silence
    lib("beat-slowing", edl.A_FREEZE - 0.42, -12.0, length=0.9)
    for t, g in ((9.95, -4.0), (10.53, -3.0)):
        syn(thunk(48, 0.45), t, g)
        lib("sword-impact", t, -15.0, length=0.35, hp=90)
        syn(sub_boom(0.5, 70, 32), t, -10.0)
    lib("gun-reload", 10.88, -14.0, length=0.5)                    # loading up before the name
    syn(reverse_swell(0.42), D - 0.52, -13.0)                       # "I'm..." into the drop, then 100 ms of vacuum

    # ---- FOUNDERS ----
    lib("bass-woosh-1", D, -7.0, hp=70, dip=True, pre=0.04)
    lib("cinematic-electric-hit", D, -11.0, hp=70, length=1.6, dip=True, pre=0.02)
    lib("woosh-3", D + 0.584, -16.0)                               # the light sweep
    syn(shutter(), S("B1f")["out0"], -10.0)                        # the micro freeze
    lib("sword-impact", 14.033, -10.0, hp=90, length=0.9, dip=True)   # KARTIK
    lib("fast-swoosh", 14.033, -13.0, dip=True)
    for t in (15.199, 15.782):
        lib("sword-slash-3", t, -10.0)
    lib("sword-impact", 16.366, -10.0, hp=90, length=0.8)
    lib("sword-slash-1", 16.949, -16.0)
    lib("woosh-4", 18.10, -13.0)
    for k, t in enumerate((19.67, 19.83, 19.98, 20.12)):           # "students": stressed messages
        syn(wa_receive(), t, -12.0, (-0.4, 0.3, -0.1, 0.4)[k])
    syn(error_ding(520), 20.15, -7.0)                              # brain.exe
    for k in range(5):
        syn(error_ding(520 * 1.06 ** k), 20.63 + k * 0.07, -12.0 - k, 0.2 * (-1) ** k)
    lib("alien-digital-glitch", 20.63, -15.0, length=0.45)
    syn(data_sweep(0.55), 21.57, -14.0)                            # the blueprint draws
    lib("radio-switch", 22.13, -14.0, length=0.3)
    syn(power_down(0.3), R - 0.20, -9.0)

    # ---- REVEAL ----
    syn(ping(), R + 0.13, -4.0)                                    # one ping in the dark
    lib("build-up-2", D2 - 0.10, -12.0, t_from=R + 0.05, fade_out=0.03)   # builds through the dark, stops 100 ms before drop 2
    lib("slow-woosh", 24.2, -15.0)
    lib("lightning-strike", D2, -9.0, hp=60, dip=True, pre=0.03)
    lib("bass-woosh-2", D2, -8.0, hp=70, dip=True, pre=0.05)
    lib("cinematic-electric-hit", D2, -12.0, hp=70, length=1.8, dip=True, pre=0.02)
    lib("sword-slash-1", 26.01, -15.0)                             # CAMPUS
    lib("woosh-1", S("C2")["out0"], -16.0, length=0.8)
    syn(data_sweep(0.4, 800, 6000), 28.05, -15.0)                  # AI-powered
    lib("glitchy-woosh", 29.49, -16.0)                             # memory
    syn(wa_receive(), 31.08, -6.0)                                 # the WhatsApp badge
    lib("woosh-3", 31.0, -14.0)
    lib("fast-swoosh", 32.05, -11.0)

    # ---- DEMO ----
    lib("sword-impact", 32.10, -12.0, hp=90, length=0.7)           # NO NEW APP.
    lib("glitchy-woosh", 32.25, -16.0)
    lib("bass-woosh-1", 32.68, -13.0, hp=80, length=0.9)           # JUST WHATSAPP.
    syn(wa_receive(), 32.70, -9.0)
    lib("slow-woosh", 33.35, -14.0)                                # the phone flies in
    for t in (34.430, 36.762, 38.512, 40.844):
        syn(wa_send(), t, -6.0, 0.15)
    for t in (35.596, 37.929, 39.678, 41.428):
        syn(wa_receive(), t, -6.0, -0.15)
    syn(typing(0.55), 36.19, -12.0)
    lib("woosh-2", 39.68, -16.0, length=0.6)                       # the deadline card pops out
    syn(chime((1046.5, 1318.5, 1568.0, 2093.0), 0.07, 0.3, 0.5), 42.011, -6.0)   # the reminder fires
    for k, t in enumerate((43.177, 43.760, 44.343, 44.926)):       # SAVE / FIND / TRACK / ACTUALLY SUBMIT
        syn(chime(((1046.5, 1318.5), (1174.7, 1568.0), (1318.5, 1760.0), (1568.0, 2093.0, 2637.0))[k], 0.06, 0.25, 0.5),
            t, -7.0 + (2.0 if k == 3 else 0.0))
        lib("sword-slash-3", t, -13.0, pan=(-0.3, 0.3, -0.3, 0.0)[k])
    lib("sword-impact", 44.926, -12.0, hp=100, length=0.6)
    lib("woosh-4", 45.48, -14.0)

    # ---- PAYOFF (times from the payoff builder's report) ----
    lib("woosh-3", 45.70, -17.0)
    syn(wa_receive(), 45.733, -10.0)                               # the found-file card
    syn(thunk(80, 0.2), 46.533, -11.0)                             # FOUND stamps on
    syn(chime((1568.0, 2093.0), 0.06, 0.2, 0.5), 46.533, -9.0)
    lib("fast-swoosh", 47.133, -17.0, pan=-0.3)                    # file card out, calendar in
    lib("woosh-3", 47.20, -16.0, pan=0.3)
    syn(bell_alarm(0.62), 47.33, -18.0, 0.3)                       # the deadline alarm rings...
    syn(chime((1318.5, 1568.0), 0.06, 0.2, 0.5), 47.967, -10.0)   # ...goes quiet: on track
    lib("fast-swoosh", 49.20, -16.0, pan=-0.5)                     # calendar whips out
    lib("woosh-3", 49.30, -15.0)                                   # the WhatsApp icon bounces in
    syn(thunk(95, 0.15), 49.66, -15.0)
    for k in range(9):                                             # 999+ chaos
        syn(wa_receive(), 49.433 + k * 0.045, -14.0 - k * 0.5, rng.uniform(-0.6, 0.6))
    for t in (49.733, 50.000):
        syn(error_ding(700), t, -16.0, rng.uniform(-0.4, 0.4))
    for tt, x in ticks(50.067, 51.30, 12, 40, 1900):               # the badge counts down
        syn(x, tt, -19.0)
    syn(chime((1568.0, 2093.0, 2637.0), 0.05, 0.3, 0.5), 51.333, -8.0)
    syn(chime((2093.0, 2637.0), 0.05, 0.25, 0.4), 51.533, -16.0)
    f0 = S("E4f")["out0"]
    lib("cinematic-electric-hit", f0, -8.0, hp=50, length=1.0, pre=0.02)    # the bass hit on the freeze
    syn(sub_boom(0.8, 80, 30), f0, -5.0)
    syn(thunk(55, 0.35), f0, -8.0)                                 # FINALLY USEFUL. slams
    lib("alien-digital-glitch", f0 + 0.02, -14.0, length=0.6)
    lib("glitchy-woosh", S("F1")["out0"], -12.0)                  # glitch transition back
    # ---- CTA (times from the cta builder's report) ----
    lib("woosh-2", 52.60, -16.0, length=0.6)                       # the student ID card swings in
    lib("sword-slash-3", 53.20, -12.0)                             # STUDENTS.
    syn(thunk(90, 0.2), 53.20, -14.0)
    lib("fast-swoosh", 53.633, -18.0)                              # BUILT BY whips out
    lib("sword-slash-3", 54.167, -13.0)                            # STUDENTS. again
    lib("woosh-3", 54.433, -17.0)                                  # card out
    syn(wa_receive(), 55.067, -11.0)                               # Semester 2.0: update available
    syn(tone(1500, 0.05, 0.012), 55.267, -16.0)                    # the button folds into the bar
    syn(data_sweep(0.87, 300, 3000), 55.30, -16.0)                 # installing...
    syn(chime((1318.5, 1760.0, 2093.0, 2637.0), 0.06, 0.35, 0.5), 56.20, -6.0)    # upgrade complete
    lib("bass-woosh-2", 56.20, -15.0, hp=90, length=0.7, pre=0.2)
    syn(chime((3135.9, 3951.1), 0.09, 0.15, 0.3), 56.27, -20.0)   # sparkles
    # ---- END CARD (times from the end-card builder's report) ----
    lib("cinematic-electric-hit", 56.967, -9.0, hp=60, length=2.2, pre=0.02)
    lib("bass-woosh-1", 56.967, -11.0, hp=70, pre=0.25)
    lib("woosh-3", 57.10, -19.0)                                   # light sweep over the mark
    lib("sword-slash-1", 57.167, -16.0)                            # CAMPUS
    lib("woosh-2", 57.767, -16.0, length=0.6)                      # YOUR BRAIN HAS A BACKUP NOW.
    lib("sword-impact", 58.333, -11.0, hp=90, length=1.0)          # COMING SOON.
    syn(wa_send(), 58.933, -6.0)                                   # the tag-a-friend bubble
    syn(tone(2600, 0.04, 0.01), 59.50, -22.0)                      # its ticks turn blue

    # ---- overlay-driven pops (from the builders' reports, renders/cues.json) ----
    for c in load_cues().get("pops", []):
        syn(wa_receive() if c.get("kind") == "in" else wa_send(), c["t"], c.get("db", -14.0), c.get("pan", 0.0))


# ---------------- master ----------------
def write(path, x):
    sf.write(path, x.astype(np.float32), SR, subtype="FLOAT")


def master(mix, out):
    mix = filt(mix, "highpass", 30, 2)
    mix = compressor(mix, thr_db=-14, ratio=1.6, att=0.02, rel=0.25)       # bus glue, ~1-2 dB
    tmp = out + ".raw.wav"
    write(tmp, mix / max(1.0, np.abs(mix).max() / 0.98))
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
                    f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
                    f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.891:level=disabled",
                    "-ar", str(SR), "-c:a", "pcm_s24le", out], check=True)
    os.remove(tmp)
    return j


def main():
    global B
    os.chdir(edl.ROOT)
    song = load(edl.SONG)
    Dl, rep = stem_D()
    B = np.zeros((N + SR * 3, 2))
    design()
    B = B[:N]
    env = speech_env(Dl)
    M = carve(automate_music(stem_M(song), env), env)
    Bc = carve(B, env, -8.0, -2.0)
    for name, x in (("D", Dl), ("M", M), ("B", Bc)):
        write(os.path.join(OUTDIR, f"stem_{name}.wav"), x)
    j = master(Dl + M + Bc, os.path.join(OUTDIR, "mix.wav"))
    master(Dl + Bc, os.path.join(OUTDIR, "mix_nomusic.wav"))
    for sid, L, g in rep:
        print(f"  {sid:6s} line {L:6.1f} LUFS  gain {g:+5.1f} dB")
    print(f"mix: input {j['input_i']} LUFS -> -14 LUFS, true peak -1 dBTP;  {N / SR:.3f} s")


if __name__ == "__main__":
    main()
