"""TaxWise Singapore reel: the sound. HK Vinay's voice, "Timeless Instrumental", and sound design on every graphic cue.

  python3 tools/mix.py   ->  renders/audio/mix.wav           -14 LUFS, -1 dBTP (Instagram, Shorts, LinkedIn)
                             renders/audio/mix_nomusic.wav   voice + effects, same gain (if a platform mutes the song)
                             renders/audio/stem_{D,M,B}.wav  float stems, exactly as mixed
                             renders/audio/sfx_log.json      every effect placed: time, id, gain
Three stems:
  D  the voice: his lines cut from renders/audio/dialogue_src.wav (tools/dialogue.py) per edl.SEGMENTS with
     short fades, every line levelled to the same speech loudness, a slow fader ride, a 3:1 soft-knee
     compressor and a peak catcher. Mono, centre.
  M  the song per edl.MUSIC: in on the pickup beat, the 6-bar lift crossfaded on the bar line at 30.5, the
     held chord faded at the end, and half a beat of silence before the drop ("into... SINGAPORE"). Under the
     voice its 250 Hz-5 kHz band ducks; the kick, the bass and the shimmer stay.
  B  sound design on the picture's cues (the specs in slots/ and the builders' cue lists): the user's library
     (library/sfx: all 28 effects are used) plus synthesised glints, pops, ticks and sub hits, tuned to the
     song (B minor; the chord that rings out at the end is F#).
Master: 25 Hz high-pass, gain to -14 LUFS, a 4x-oversampled latency-compensated limiter at -1.2 dBFS.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/home/user/Video_Claude/library/tools")
import edl  # noqa: E402
import sfx  # noqa: E402

SR = 48000
N = int(round(edl.DURATION * SR))
OUT = os.path.join(edl.ROOT, "renders/audio")
DLG = os.path.join(OUT, "dialogue_src.wav")
rng = np.random.default_rng(7)

# B minor pentatonic (+ the F# of the last chord), for every tonal effect
NOTE = {"B5": 987.77, "D6": 1174.66, "E6": 1318.51, "F#6": 1479.98, "A6": 1760.0, "B6": 1975.53, "D7": 2349.32,
        "E7": 2637.02, "F#7": 2959.96, "A7": 3520.0, "B7": 3951.07, "B1": 61.74, "F#1": 46.25, "B2": 123.47,
        "D2": 73.42, "F#2": 92.5}
DROP, BREAK, LIFT, END = edl.DROP, edl.BREAK, edl.LIFT, edl.END
GAP = (DROP - 0.25, DROP)                # half a beat of silence before the drop


# ---------------- dsp helpers ----------------
def sos(kind, f, order=2):
    return butter(order, f, kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    return sosfiltfilt(sos(kind, f, order), x, axis=0)


def stereo(m):
    return np.stack([m, m], axis=1)


def fade(x, fin=0.0, fout=0.0):
    """Raised-cosine fade in / out (mono or stereo)."""
    x = x.copy()
    n = len(x)
    for dur, rising in ((fin, True), (fout, False)):
        k = min(n, int(dur * SR))
        if k <= 0:
            continue
        r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))
        r = r if rising else r[::-1]
        sl = slice(0, k) if rising else slice(n - k, n)
        x[sl] *= r[:, None] if x.ndim == 2 else r
    return x


def pan_gain(pan):
    th = (pan + 1) * np.pi / 4
    return np.array([np.cos(th), np.sin(th)]) * np.sqrt(2)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def resample(x, ratio):
    """Tape-style speed change (pitch and length): ratio > 1 is faster/higher."""
    n = int(len(x) / ratio)
    pos = np.arange(n) * ratio
    i = np.minimum(pos.astype(int), len(x) - 2)
    fr = (pos - i)[:, None] if x.ndim == 2 else pos - i
    return x[i] * (1 - fr) + x[i + 1] * fr


# ---------------- synthesised sounds (all deterministic) ----------------
def glint(f, dur=1.1, width=1.8):
    """A crystal 'tick of light': harmonic partials with a touch of inharmonic shimmer, detuned L/R for width."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ch, det in ((0, -width / 2), (1, width / 2)):
        ff = f + det
        x = (np.sin(2 * np.pi * ff * t) * np.exp(-t / (dur / 3.2))
             + 0.42 * np.sin(2 * np.pi * 2.0 * ff * t + 0.3) * np.exp(-t / (dur / 5.0))
             + 0.18 * np.sin(2 * np.pi * 3.01 * ff * t + 1.1) * np.exp(-t / (dur / 8.0))
             + 0.10 * np.sin(2 * np.pi * 4.23 * ff * t) * np.exp(-t / (dur / 12.0)))
        out[:, ch] = x * np.minimum(1, t / 0.0015)
    return out / np.abs(out).max()


def chord_glint(names, dur=1.6, spread=0.035):
    parts = [glint(NOTE[k], dur) for k in names]
    n = max(len(p) for p in parts) + int(spread * SR * len(parts))
    out = np.zeros((n, 2))
    for k, p in enumerate(parts):
        i = int(k * spread * SR)
        out[i:i + len(p)] += p * pan_gain((k - (len(parts) - 1) / 2) * 0.5)
    return out / np.abs(out).max()


def pop(f, dur=0.07):
    """A rounded UI pop: a sine that drops a fifth, with a soft click."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ff = f * (1 + 0.5 * np.exp(-t / 0.008))
    x = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.minimum(1, t / 0.0012) * np.exp(-t / (dur / 4))
    return stereo(x / np.abs(x).max())


def tick(f=2200, dur=0.045):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t / 0.005)
    x += rng.standard_normal(n) * np.exp(-t / 0.0015) * 0.35
    return stereo(x / np.abs(x).max())


def sub_drop(dur=1.3, f0=90, f1=34):
    n = int(dur * SR)
    f = f1 + (f0 - f1) * np.exp(-np.arange(n) / (0.22 * SR))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, dur / 3.2) * np.minimum(1, np.arange(n) / (0.002 * SR))
    return stereo(x / np.abs(x).max())


def thump(f=60, dur=0.4, click=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t * (1 - 0.3 * t / dur)) * np.exp(-t / (dur / 4))
    c = rng.standard_normal(n) * np.exp(-t / 0.004) * click
    x = sosfilt(sos("lowpass", 1200), body + c)
    return stereo(x / np.abs(x).max())


def swell(dur, f0=500, f1=9000, power=2.4):
    """Filtered noise rising into its end (a reverse cymbal / short riser), stereo-decorrelated."""
    n = int(dur * SR)
    out = np.zeros((n, 2))
    blk = 512
    for ch in range(2):
        x = rng.standard_normal(n)
        zi = None
        for i in range(0, n, blk):
            u = i / n
            fc = min(f0 * (f1 / f0) ** u, SR / 2.3)
            s = sos("highpass", fc)
            if zi is None:
                zi = np.zeros((s.shape[0], 2))
            out[i:i + blk, ch], zi = sosfilt(s, x[i:i + blk], zi=zi)
    e = (np.arange(n) / n) ** power
    out *= e[:, None]
    return out / np.abs(out).max()


def sheen(dur=0.55, f0=2500, f1=11000):
    """A light sweep across gold: a bright band of noise sweeping up, bell-shaped."""
    n = int(dur * SR)
    out = np.zeros((n, 2))
    blk = 256
    for ch in range(2):
        x = rng.standard_normal(n)
        zi = None
        for i in range(0, n, blk):
            u = i / n
            fc = f0 * (f1 / f0) ** u
            s = sos("bandpass", [fc / 1.25, min(fc * 1.25, SR / 2.2)])
            if zi is None:
                zi = np.zeros((s.shape[0], 2))
            out[i:i + blk, ch], zi = sosfilt(s, x[i:i + blk], zi=zi)
    u = np.arange(n) / n
    out *= (np.sin(np.pi * u) ** 1.5)[:, None] * np.stack([1.2 - 0.7 * u, 0.5 + 0.7 * u], 1)   # sweeps left to right
    return out / np.abs(out).max()


def comet(dur, f0=320, f1=3800):
    """The arc travelling India -> Singapore: a rising airy whistle with noise, panned left to right."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    f = f0 * (f1 / f0) ** (u ** 1.6)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    air = np.zeros(n)
    x = rng.standard_normal(n)
    zi = None
    for i in range(0, n, 256):
        fc = f[i]
        s = sos("bandpass", [fc / 1.5, min(fc * 1.5, SR / 2.2)])
        if zi is None:
            zi = np.zeros((s.shape[0], 2))
        air[i:i + 256], zi = sosfilt(s, x[i:i + 256], zi=zi)
    air /= np.abs(air).max()
    m = (tone + air) * (0.15 + 0.85 * u ** 1.8) * np.minimum(1, (dur - t) / 0.02)
    p = -0.6 + 1.2 * u
    th = (p + 1) * np.pi / 4
    out = np.stack([m * np.cos(th), m * np.sin(th)], 1)
    return out / np.abs(out).max()


def spark(f=1800, dur=0.16):
    """An electric spark: a crackle of filtered noise bursts with a bright pitched snap."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / 0.018)
    x = sosfilt(sos("bandpass", [f * 0.7, min(f * 4.5, SR / 2.3)]), x)
    crack = np.zeros(n)
    for k in range(5):                                   # a few micro-crackles after the snap
        i = int((0.012 + 0.017 * k + 0.004 * (k % 2)) * SR)
        m = int(0.003 * SR)
        crack[i:i + m] += rng.standard_normal(m) * (0.6 - 0.1 * k)
    snap = np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / 0.010)
    y = x / (np.abs(x).max() + 1e-9) + crack * 0.6 + snap * 0.5
    out = np.stack([y * 0.9, np.roll(y, int(0.0007 * SR))], 1)
    return out / np.abs(out).max()


def fall(dur=0.2, f0=2600, f1=700):
    """A short falling whistle: something dropping into place."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.01) * (0.4 + 0.6 * t / dur)
    return stereo(x / np.abs(x).max())


def counter_ticks(t0, t1, n, ease_pow=3.0):
    """Times at which a counter easing (power-out) from 0 to n crosses each integer."""
    out = []
    for k in range(1, n + 1):
        v = k / n                                       # value fraction; u = 1 - (1 - v) ** (1 / p) inverts power-out
        u = 1 - (1 - v) ** (1 / ease_pow) if v < 1 else 1.0
        out.append(t0 + u * (t1 - t0))
    return out


# ---------------- placing ----------------
class Bus:
    def __init__(self):
        self.x = np.zeros((N + SR, 2))
        self.log = []

    def put(self, x, t, gain_db, hit=0.0, pan=0.0, hp=None, lp=None, name="synth"):
        if hp:
            x = sosfilt(sos("highpass", hp, 2), x, axis=0)
        if lp:
            x = sosfilt(sos("lowpass", lp, 2), x, axis=0)
        if pan:
            x = x * pan_gain(pan)[None, :]
        i = int(round((t - hit) * SR))
        if i < 0:
            x, i = x[-i:], 0
        j = min(len(self.x), i + len(x))
        if j > i:
            self.x[i:j] += x[:j - i] * 10 ** (gain_db / 20)
        self.log.append(dict(t=round(t, 3), sfx=name, gain_db=gain_db))

    def lib(self, sfx_id, t, gain_db, length=None, hp=None, lp=None, pan=0.0, fade_in=0.0, rate=1.0, start=None,
            at=None):
        """A library effect, its hit point on t. length: seconds kept after the hit; start: seconds before the
        hit to begin at (the rest of the lead-in is dropped); rate: tape speed (pitch); at: a different
        alignment point in the file (s), e.g. a riser's climax: the manifest's "end" is where the file stops,
        and the build-ups peak well before that."""
        x, hit = sfx.load(sfx_id, SR)
        if at is not None:
            hit = at
        if rate != 1.0:
            x, hit = resample(x, rate), hit / rate
        if start is not None and hit > start:
            cut = int((hit - start) * SR)
            x, hit = x[cut:], start
        if length is not None:
            x = fade(x[:int((hit + length) * SR)], 0, min(0.25, length / 2))
        if fade_in:
            x = fade(x, fade_in, 0)
        self.put(x, t, gain_db, hit=hit, pan=pan, hp=hp, lp=lp, name=sfx_id + (f" x{rate:g}" if rate != 1 else ""))


# ---------------- D: the voice ----------------
def band_db(x, lo=300, hi=3400, hop=SR // 100):
    b = sosfiltfilt(sos("bandpass", [lo, hi], 2), x)
    k = len(b) // hop
    return 20 * np.log10(np.sqrt((b[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-14))


def active_level(x):
    db = band_db(x)
    ref = np.percentile(db, 95)
    act = db[db > ref - 22]
    return 10 * np.log10(np.mean(10 ** (act / 10)))


def ride(d, target, lo=-4.0, hi=6.0, amount=0.55):
    """A slow fader ride toward `target` (speech-band dB), only where he speaks: quick down, slower up."""
    hop = SR // 100
    db = band_db(d, hop=hop)
    talk = db > target - 24
    want = np.where(talk, np.clip((target - db) * amount, lo, hi), 0.0)
    want = np.convolve(want, np.ones(15) / 15, "same")
    g, a, r = np.zeros(len(want)), 1 - np.exp(-1 / 4.0), 1 - np.exp(-1 / 25.0)
    for i in range(len(want)):
        p = g[i - 1] if i else 0.0
        g[i] = p + (a if want[i] < p else r) * (want[i] - p)
    gain = np.interp(np.arange(len(d)), np.arange(len(g)) * hop + hop / 2, 10 ** (g / 20))
    return d * gain


def compress(x, thr_db=-24.0, ratio=3.0, knee=8.0, att=0.006, rel=0.140, hop=48):
    """Feed-forward soft-knee compressor: RMS detector (3 ms), gain smoothed with attack/release, applied per sample."""
    k = len(x) // hop
    e = np.sqrt(np.convolve(x ** 2, np.ones(144) / 144, "same")[:k * hop].reshape(k, hop).max(1) + 1e-14)
    lvl = 20 * np.log10(e)
    over = lvl - thr_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 / ratio - 1), (1 / ratio - 1) * (over + knee / 2) ** 2 / (2 * knee)))
    a, r = 1 - np.exp(-hop / (att * SR)), 1 - np.exp(-hop / (rel * SR))
    g = np.zeros(k)
    for i in range(k):
        p = g[i - 1] if i else 0.0
        g[i] = p + (a if gr[i] < p else r) * (gr[i] - p)
    gain = np.interp(np.arange(len(x)), np.arange(k) * hop + hop / 2, 10 ** (g / 20))
    return x * gain, g


def peak_catch(x, ceil_db=-3.0, look=0.0015, rel=0.060, hop=24):
    """A lookahead peak limiter for the voice stem: the gain each window needs, held, released over `rel`."""
    from scipy.ndimage import minimum_filter1d
    need = np.minimum(1.0, 10 ** (ceil_db / 20) / (np.abs(x) + 1e-12))
    need = minimum_filter1d(need, size=2 * int(look * SR) + 1)
    red = -20 * np.log10(need)
    k = len(red) // hop
    rb = red[:k * hop].reshape(k, hop).max(1)
    out = np.zeros(k)
    dec = np.exp(-hop / (rel * SR))
    for i in range(k):
        out[i] = max(rb[i], (out[i - 1] if i else 0.0) * dec)
    g = 10 ** (-np.interp(np.arange(len(x)), np.arange(k) * hop + hop / 2, out) / 20)
    return x * np.minimum(g, need)


def voice():
    x, sr = sf.read(DLG)
    assert sr == SR
    target = -22.0                                       # speech-band level of every line
    D = np.zeros(N + SR)
    report = []
    for s in edl.SEGMENTS:
        a, b = int(round(s["src"] * SR)), int(round(s["src_end"] * SR))
        y = fade(x[a:b], 0.025, 0.045)
        lv = active_level(y)
        g = target - lv
        y = y * 10 ** (g / 20)
        i = int(round(s["out"] * SR))
        D[i:i + len(y)] += y
        report.append((s["id"], round(lv, 1), round(g, 1)))
    D = D[:N]
    D = ride(D, target)
    D, gr = compress(D)
    D = peak_catch(D, -2.5)
    return D, report, gr


def speech_env(d, release=0.30):
    """0..1 voice presence: speech-band level in 10 ms hops, fast attack, `release` s release."""
    hop = SR // 100
    db = band_db(d, hop=hop)
    ref = np.percentile(db[db > -80], 90)
    on = np.clip((db - (ref - 34)) / 10, 0, 1)
    e, a, r = np.zeros(len(on)), 1 - np.exp(-1 / 1.5), 1 - np.exp(-1 / (release * 100))
    for i in range(len(on)):
        p = e[i - 1] if i else 0.0
        e[i] = p + (a if on[i] > p else r) * (on[i] - p)
    return np.interp(np.arange(len(d)), np.arange(len(e)) * hop + hop / 2, e)


# ---------------- M: the song ----------------
def song():
    x, sr = sf.read(edl.SONG, always_2d=True)
    assert sr == SR
    M = np.zeros((N + SR, 2))
    xf = int(0.012 * SR)                                 # the seam's crossfade, centred on the bar line
    for k, (o, s0, ln) in enumerate(edl.MUSIC):
        i0 = int(round(o * SR)) - (xf // 2 if k else 0)
        a = int(round(s0 * SR)) - (xf // 2 if k else 0)
        n = int(round(ln * SR)) + (xf // 2 if k else 0) + (xf // 2 if k < len(edl.MUSIC) - 1 else 0)
        y = x[a:a + n].astype(np.float64)
        if k:
            y[:xf] *= np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
        else:
            y = fade(y, 0.006, 0)
        if k < len(edl.MUSIC) - 1:
            y[-xf:] *= np.cos(np.linspace(0, np.pi / 2, xf))[:, None]
        j = min(len(M), i0 + len(y))
        M[i0:j] += y[:j - i0]
    M = M[:N]
    # half a beat of silence before the drop: out with a 25 ms fade, back in hard on the downbeat
    a, b = int(GAP[0] * SR), int(GAP[1] * SR)
    k = int(0.025 * SR)
    M[a - k:a] *= np.cos(np.linspace(0, np.pi / 2, k))[:, None]
    M[a:b] = 0
    # the last chord: fade over the final 0.9 s
    k = int(0.9 * SR)
    M[-k:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
    return M


# where he is silent the song comes up: (start, end, dB), 0.2 s ramps
MUSIC_UP = [(13.30, 14.22, 4.0), (24.97, 25.47, 2.0), (35.12, 35.82, 2.0), (42.37, 42.97, 2.0), (47.85, 52.0, 3.0)]


def music_up(m):
    g = np.zeros(len(m))
    t = np.arange(len(m)) / SR
    for a, b, db in MUSIC_UP:
        r = 0.2
        w = np.clip(np.minimum((t - a) / r, (b - t) / r + (1.0 if b >= edl.DURATION else 0.0) * 9), 0, 1)
        g = np.maximum(g, db * (0.5 - 0.5 * np.cos(np.pi * w)))
    return m * 10 ** (g / 20)[:, None]


def carve(m, env, mid_db=-11.0, edge_db=-4.5, lo=250, hi=5000):
    """Duck the music's speech band under the voice; its lows and highs mostly stay."""
    low = filt(m, "lowpass", lo, 4)
    high = filt(m, "highpass", hi, 4)
    mid = m - low - high
    e = env[:len(m), None]
    return (low + high) * 10 ** (edge_db * e / 20) + mid * 10 ** (mid_db * e / 20)


# ---------------- B: the sound design ----------------
def effects():
    B = Bus()
    L = B.lib
    P = B.put

    # ===== HOOK 0.00-6.10: a horizon line ignites, the skyline draws on, A NEW HORIZON, a globe spins up =====
    P(sub_drop(1.1, 70, 32), 0.0, -14, name="sub drop")
    P(glint(NOTE["B6"], 1.4), 0.02, -21, name="glint B6 (the point of light)")
    L("fast-swoosh", 0.28, -19, hp=300, pan=-0.45)                     # the line races out left...
    L("fast-swoosh", 0.32, -19, hp=300, pan=0.45, rate=1.06)            # ...and right
    L("woosh-4", 1.20, -21, hp=120)                                     # the camera eases out
    P(thump(58, 0.45), 0.50, -15, name="thump (the line lands)")
    P(glint(NOTE["F#6"], 1.0), 0.51, -25, name="glint (the line flashes)")
    P(sheen(1.0), 0.89, -27, name="sheen (a pulse runs along the line)")
    for k, t in enumerate((2.03, 2.07, 2.13, 2.19, 2.25)):             # MBS, Supertrees, ArtScience, Flyer, CBD rise
        P(pop(NOTE[["B5", "D6", "E6", "F#6", "A6"][k]], 0.05), t, -29, pan=-0.5 + 0.25 * k, name="pop (a landmark rises)")
    L("fast-swoosh", 2.85, -24, hp=400, pan=0.3)                        # the SkyPark ship slides across
    for k in range(18):                                                 # the Flyer's capsules tick on
        P(tick(3400 + 40 * k, 0.02), 2.60 + k * 0.022, -32, pan=0.15, name="tick (a Flyer capsule)")
    P(swell(1.0, 700, 10000), 3.07, -22, hit=1.0, name="swell (skyline draws on)")
    L("woosh-3", 3.00, -16, hp=200)                                     # A NEW HORIZON rises
    L("sword-impact", 3.07, -26, hp=600, length=1.6)                    # the skyline's glint rings
    P(glint(NOTE["F#7"], 1.6), 3.08, -20, pan=-0.2, name="glint F#7 (skyline complete)")
    L("slow-woosh", 3.20, -21, hp=150)                                  # the sunrise glow swells
    L("woosh-1", 4.40, -23, hp=150, pan=0.15)                           # the globe spins up
    P(pop(NOTE["B6"], 0.06), 4.50, -27, name="pop (equator pulse)")
    P(comet(0.69, 600, 3200), 5.31, -26, hit=0.69, pan=-0.2, name="comet (the equator draws round)")
    P(pop(NOTE["D6"], 0.08), 5.43, -25, name="pop (second ring)")
    P(thump(52, 0.5), 5.31, -16, name="thump (global)")
    P(sub_drop(1.0, 80, 36), 5.31, -16, name="sub drop (global pulse ring)")
    P(glint(NOTE["D7"], 1.3), 5.33, -21, pan=-0.3, name="glint D7 (globe complete)")

    # ===== INTRO 6.10-12.50: the aura pull-out reveals HK VINAY; the music drops out on "TaxWise" =====
    L("cinematic-electric-hit", 6.10, -14, hp=45, length=3.0, start=0.9)  # the cut: the aura
    L("slow-motion", 6.10, -16, hp=90)
    L("woosh-4", 6.55, -18, hp=100)                                     # the pull-out (1.45x -> 1.00x)
    L("sword-slash-1", 6.66, -25, hp=500, lp=7000, pan=-0.35)           # HK rises (the swish only, no metal)
    L("sword-slash-3", 7.12, -24, hp=500, lp=7000, pan=-0.2)            # VINAY
    P(thump(55, 0.4), 7.12, -19, name="thump (VINAY lands)")
    L("woosh-3", 7.70, -17, hp=300, pan=-0.3)                           # MANAGING PARTNER slides in
    P(sheen(0.6), 7.50, -25, hit=0.25, name="sheen (light sweep across HK)")
    P(tick(2400), 7.74, -22, pan=-0.3, name="tick (MANAGING PARTNER drops in)")
    # the drums leave on "TaxWise": the beat slows into the break, a muffled swell opens it
    L("beat-slowing", BREAK, -26, hp=120, length=0.55, start=0.12)
    L("lowpass-woosh", BREAK + 0.25, -24)
    for t, note in ((8.56, "B6"), (8.62, "D7"), (8.80, "F#7")):        # T, W, diamond draw on
        P(pop(NOTE[note], 0.05), t, -27, pan=0.35, name="pop (the TW mark draws on)")
    P(swell(0.42, 1500, 12000, 1.6), 8.98, -27, hit=0.42, name="swell (gold floods the mark)")
    P(glint(NOTE["B6"], 1.5), 9.12, -24, pan=0.35, name="glint B6 (the mark's shine)")
    for k, t in enumerate((9.49, 9.81, 10.13, 10.61, 10.77, 11.33, 11.65, 12.37)):   # the loading line steps, a spark each
        P(spark(1500 + 260 * k), t, -27 + 0.6 * k, pan=-0.6 + 0.17 * k, name="spark (the loading line steps)")
    # the build: a loading line burns across the wall like a fuse, a reload, the riser
    L("fire", 9.49, -10, hp=1800, lp=9000, length=2.76, fade_in=2.4, start=0.21)   # the fuse crackles, growing
    L("build-up-2", GAP[0], -22, hp=90, at=2.85)                        # climaxes where the silence begins
    L("sword-slash-3", 11.65, -23, hp=400, lp=7000)                     # EXPANSION cut in outline
    P(thump(62, 0.35), 11.65, -21, name="thump (EXPANSION)")
    L("bass-woosh-2", GAP[0], -23, hp=60, length=0.02)                  # its sweep rises into the silence

    # ===== THE DROP 12.50 on "SINGAPORE" =====
    L("bass-woosh-1", DROP, -11, hp=35, start=0.0)               # the burst only: the silence stays silent
    L("lightning-strike", DROP, -27, hp=500, length=1.2)                # the white-gold flash: a touch of crack
    L("sword-impact", DROP + 0.01, -24, hp=220, length=1.4)              # gold metal rings
    P(sub_drop(1.8, 85, 30), DROP, -15, name="sub drop (the drop)")
    L("sword-slash-2", DROP + 0.03, -26, hp=600, lp=7000)               # SINGAPORE slams in, letter by letter
    P(chord_glint(["B6", "D7", "F#7"], 1.8), DROP + 0.36, -21, name="glint chord (all letters landed)")
    L("woosh-3", 13.00, -19, hp=300, pan=0.2)                           # NOW IN snaps in
    P(tick(2600), 13.02, -20, name="tick (NOW IN)")
    P(sheen(0.6), 13.50, -21, hit=0.25, name="sheen (light sweep across the type)")
    L("glitchy-woosh", 14.22, -16, hp=80)                               # everything rushes into the lens (RGB split)
    L("alien-digital-glitch", 14.20, -23, hp=400, length=0.22, start=0.0)
    P(swell(0.5, 900, 12000), 14.22, -20, hit=0.5, name="swell (into the lens)")

    # ===== THE TEAM 14.22-25.47 =====
    L("rain", 14.25, -15, hp=4500, lp=12000, length=1.25, fade_in=0.3, start=0.21)   # gold points stream in (fizz)
    pent = ["B5", "D6", "E6", "F#6", "A6", "B6", "D7", "E7", "F#7", "A7"]
    for k in range(30):                                                 # 30 people pop into formation
        u = k / 29
        t = 14.55 + 0.90 * (1 - (1 - u) ** 1.6)
        P(pop(NOTE[pent[k % len(pent)]] * (0.5 if k % 3 == 0 else 1.0), 0.06), t, -31 + 4 * u,
          pan=float(np.sin(k * 2.4)) * 0.6, name="pop (a person)")
    P(glint(NOTE["B6"], 1.0), 15.46, -22, name="glint (the team complete)")
    for t in counter_ticks(15.46, 16.34, 30):                          # the counter runs 0 -> 30
        P(tick(2300, 0.03), t, -23, name="tick (counter)")
    L("sword-impact", 16.34, -21, hp=150, length=1.2)                   # 30+ slams
    P(thump(56, 0.5), 16.34, -14, name="thump (30+)")
    P(sub_drop(1.2, 90, 36), 16.34, -15, name="sub drop (30+ ring pulse)")
    L("woosh-3", 16.84, -17, hp=300)                                    # IN-HOUSE SPECIALISTS
    P(tick(2500), 16.90, -21, name="tick (hairline)")
    L("slow-woosh", 18.75, -18, hp=120)                                 # the people swirl into the hub
    L("woosh-4", 19.05, -21, hp=150, rate=1.12)
    P(thump(60, 0.4), 19.22, -18, name="thump (the TW mark condenses)")
    P(glint(NOTE["D7"], 1.3), 19.24, -20, name="glint D7 (the hub)")
    L("fast-swoosh", 19.22, -23, hp=400)                                # EXPERTISE ACROSS
    services = [(20.66, "FINANCE", "B6", -0.55), (21.38, "TAXATION", "D7", 0.55), (22.50, "PAYROLL", "E7", -0.45),
                (23.38, "COMPLIANCE", "F#7", 0.45), (24.18, "ADVISORY", "B7", 0.0)]
    for k, (t, name, note, pan) in enumerate(services):
        L("woosh-3" if k % 2 == 0 else "fast-swoosh", t - 0.05, -22, hp=250, pan=pan)
        P(thump(64, 0.3, 0.5), t, -22, pan=pan * 0.5, name=f"thump ({name})")
        P(glint(NOTE[note], 0.9), t + 0.04, -24, pan=pan, name=f"glint {note} ({name})")
        P(tick(2800, 0.035), t + 0.20, -22, pan=pan, name=f"tick ({name} icon draws)")
    L("build-up-1", LIFT, -21, hp=150, at=1.55)                         # climaxes on the lift
    L("cinematic-electric-hit", LIFT, -18, hp=55, length=3.5, start=0.6)  # the network glows
    P(chord_glint(["B6", "D7", "F#7", "B7"], 2.2, 0.05), LIFT + 0.02, -21, name="glint chord (ONE CONNECTED...)")
    L("woosh-1", 25.25, -19, hp=120)                                    # the network folds into a sphere

    # ===== THE GLOBE 25.47-35.57 =====
    P(sub_drop(1.4, 70, 30), 25.47, -19, name="sub drop (the sphere fills with Earth)")
    L("lowpass-woosh", 25.70, -21, hp=70)
    L("rain", 25.50, -17, hp=5000, lp=13000, length=0.75, fade_in=0.2, start=0.21)  # the Earth blooms in gold dots
    L("woosh-1", 26.15, -20, hp=120, pan=-0.2)                          # the spin to India (peaks 26.1-26.25)
    P(thump(54, 0.45), 27.52, -18, name="thump (settles on India)")
    P(pop(NOTE["B6"]), 27.52, -25, pan=-0.3, name="pop (BANGALORE)")
    P(glint(NOTE["B6"], 1.0), 27.53, -22, pan=-0.3, name="glint (BANGALORE)")
    P(pop(NOTE["D7"]), 27.64, -25, pan=-0.15, name="pop (CHENNAI)")
    P(glint(NOTE["D7"], 1.0), 27.65, -22, pan=-0.15, name="glint (CHENNAI)")
    P(sheen(0.7), 27.67, -23, hit=0.35, name="sheen (India's outline glows)")
    L("slow-woosh", 28.60, -23, hp=150, pan=0.2)                         # the camera swings east
    P(comet(1.52), 29.92, -23, hit=1.52, name="comet (Bangalore -> Singapore)")
    P(comet(1.44, 360, 4200), 29.92, -27, hit=1.44, pan=0.15, name="comet (Chennai -> Singapore)")
    L("bass-woosh-2", 29.92, -19, hp=60, length=1.0)
    P(thump(50, 0.6), 29.92, -15, name="thump (Singapore pin)")
    P(chord_glint(["F#6", "B6", "D7"], 1.6), 29.94, -23, pan=0.3, name="glint chord (SINGAPORE)")
    P(pop(NOTE["B6"], 0.08), 30.04, -25, pan=0.3, name="pop (second pulse ring)")
    L("radio-beep", 30.19, -30, hp=600, lp=7000, pan=0.35)               # NEW OFFICE: a message in
    P(tick(3000, 0.03), 30.33, -24, pan=0.35, name="tick (the tick draws)")
    L("fast-swoosh", 30.62, -27, hp=500, pan=-0.4, rate=0.9)             # the India labels exit
    for t in (28.77, 28.89, 30.27, 30.39, 31.17, 31.77, 31.89, 32.67, 33.27, 33.39):   # soft pin pings
        P(pop(NOTE["F#7"], 0.05), t, -33, pan=float(np.sin(t * 7)) * 0.5, name="pop (pin ping)")
    L("slow-woosh", 31.05, -21, hp=150)                                 # the slow push
    L("rain", 30.50, -16, hp=6000, lp=13000, length=2.6, fade_in=0.5, start=0.21)  # light rising off the arcs
    for k, (t, land, pan) in enumerate(((32.0, 32.5, -0.3), (32.5, 33.0, 0.35), (33.0, 33.25, -0.1))):  # the bridge
        P(comet(land - t + 0.02, 500, 4200), land, -24, hit=land - t + 0.02, pan=pan * 0.5, name="comet (an arc)")
        P(tick(3000 + 300 * k, 0.04), t, -21, pan=pan, name="tick (an arc fires)")
    P(chord_glint(["B6", "D7", "F#7"], 1.6), 33.25, -20, name="glint chord (all arcs glow)")
    P(thump(56, 0.35), 33.25, -20, name="thump (the bloom and zoom punch)")
    L("woosh-4", 33.85, -22, hp=150)                                    # the camera pulls back
    L("sword-slash-1", 33.74, -26, hp=400, lp=7000)                     # INDIA x SINGAPORE
    P(thump(58, 0.4), 33.74, -18, name="thump (INDIA x SINGAPORE)")
    L("woosh-3", 34.38, -17, hp=300)                                    # CROSS-BORDER FINANCE
    for k, t in enumerate((34.60, 34.72, 34.84)):                       # TAX . COMPLIANCE . ADVISORY
        P(tick(2600 + 250 * k, 0.035), t, -21, name="tick (TAX / COMPLIANCE / ADVISORY)")
    P(sheen(0.6), 34.90, -26, hit=0.3, name="sheen (sweep across CROSS-BORDER FINANCE)")
    P(swell(0.30, 600, 6000, 1.4), 35.20, -24, hit=0.30, name="swell (the Singapore pin charges)")
    P(thump(52, 0.4), 35.20, -19, name="thump (the gold pulse bursts)")
    P(swell(0.35, 800, 12000), 35.52, -18, hit=0.35, name="swell (the gold pulse fills the frame)")
    L("wind-impact", 35.57, -18, hp=90, fade_in=2.0, start=2.2)        # the gust into the cut back to him

    # ===== THE VALUES 35.57-42.37: the aura pull-out, three values on the wall =====
    L("slow-motion", 35.57, -16, hp=90)
    L("woosh-4", 35.95, -19, hp=110)
    P(sub_drop(1.2, 75, 32), 35.57, -14, name="sub drop (aura)")
    L("fast-swoosh", 36.30, -22, hp=350, pan=-0.4)                      # OUR COMMITMENT
    P(tick(2400), 36.40, -22, pan=-0.4, name="tick (hairline)")
    for t, sid, note in ((38.24, "sword-slash-1", "B6"), (39.20, "sword-slash-3", "D7"), (40.96, "sword-slash-1", "F#7")):
        L(sid, t, -26, hp=450, lp=7000, pan=-0.35)
        P(thump(60, 0.35), t, -19, name="thump (a value lands)")
        P(glint(NOTE[note], 1.0), t + 0.05, -25, pan=-0.35, name=f"glint {note} (the diamond bullet)")
    P(thump(52, 0.45), 41.52, -18, name="thump (relationships: the punch-in)")
    P(sheen(0.8), 41.90, -22, hit=0.35, name="sheen (all three glow)")
    P(chord_glint(["B6", "D7", "F#7"], 1.8), 41.62, -25, name="glint chord (all three glow)")

    # ===== THE FINALE 42.37-48.25 =====
    L("radio-switch", 42.37, -17, hp=400, length=0.30)                  # cut to the last shot
    L("woosh-2", 42.40, -21, hp=100)
    P(swell(0.55, 400, 5000, 1.8), 43.05, -27, hit=0.55, name="swell (light gathers where the mark lands)")
    L("woosh-3", 42.95, -17, hp=300, rate=0.9)                          # the T drops
    P(thump(50, 0.5), 43.07, -17, name="thump (the TW mark assembles)")
    L("fast-swoosh", 43.14, -22, hp=300, rate=1.1)                      # the W rises
    P(pop(NOTE["B6"]), 43.34, -22, name="pop (the diamond)")
    P(glint(NOTE["F#7"], 1.3), 43.42, -21, name="glint F#7 (the diamond's glint)")
    P(sheen(0.6), 43.50, -21, hit=0.25, name="sheen (the mark's shine)")
    L("fast-swoosh", 44.16, -25, hp=400, pan=-0.4)                      # the horizon line draws out both ways
    L("fast-swoosh", 44.18, -25, hp=400, pan=0.4, rate=1.05)
    P(swell(0.63, 900, 9000), 44.85, -24, hit=0.63, name="swell (the skyline draws on again)")
    L("woosh-3", 44.25, -17, hp=300)                                    # NOW IN SINGAPORE drop from the line
    for t, note in ((44.27, "B6"), (44.43, "D7")):
        P(pop(NOTE[note], 0.06), t, -25, name="pop (a word drops)")
    P(fall(0.20), 44.59, -24, hit=0.20, name="fall (the pin drops)")
    P(thump(56, 0.4), 44.59, -18, name="thump (the pin lands on the SkyPark)")
    P(pop(NOTE["D7"]), 44.59, -21, name="pop (the pin)")
    P(chord_glint(["D7", "F#7"], 1.4), 44.62, -22, name="glint (the pin's pulse ring)")
    P(pop(NOTE["F#7"], 0.07), 44.71, -26, name="pop (second ring)")
    P(sheen(0.7), 46.50, -27, hit=0.3, name="sheen (sweep across NOW IN SINGAPORE)")
    P(glint(NOTE["B6"], 1.2), 47.15, -28, name="glint (a second shine on the mark)")
    L("fire", 45.63, -11, hp=1500, lp=8000, length=2.55, fade_in=2.0, start=0.21)  # the sunrise grows warmer
    L("build-up-3", 48.25, -21, hp=120, fade_in=1.0)                     # accelerating pulses into the bloom
    P(swell(1.2, 400, 11000), 48.25, -18, hit=1.2, name="swell (the wall blooms gold)")
    L("woosh-1", 48.30, -19, hp=100)

    # ===== THE END CARD 48.25-52.00: the drums stop, one chord rings =====
    P(sub_drop(2.4, 70, 30), END, -14, name="sub drop (the mark assembles)")
    L("cinematic-electric-hit", END, -20, hp=60, length=3.2, start=0.15)
    L("sword-impact", END + 0.30, -23, hp=300, length=2.6)               # the shield locks
    P(glint(NOTE["F#7"], 2.2), END + 0.45, -19, name="glint F#7 (the diamond's glint)")
    P(sheen(0.8), 49.30, -21, hit=0.35, name="sheen (shine across the mark)")
    L("slow-woosh", 49.25, -23, hp=200)                                  # TAXWISE / CONSULTANTS
    for k, t in enumerate((49.85, 50.00, 50.15)):                        # BANGALORE | CHENNAI | SINGAPORE
        P(tick(2400 + 200 * k, 0.035), t, -22, name="tick (an office)")
    P(pop(NOTE["F#6"]), 50.15, -24, name="pop (the Singapore pin)")
    P(glint(NOTE["B6"], 1.5), 50.52, -23, name="glint (TWCHARTERED.COM)")
    P(sheen(1.6), 51.0, -30, hit=0.8, name="sheen (gold dust)")
    x = B.x[:N]
    k = int(0.4 * SR)
    x[-k:] *= np.linspace(1, 0, k)[:, None]
    # the gap before the drop stays silent: nothing from the effects either
    a, b = int(GAP[0] * SR), int(DROP * SR) - int(0.002 * SR)
    kk = int(0.015 * SR)
    x[a - kk:a] *= np.cos(np.linspace(0, np.pi / 2, kk))[:, None]
    x[a:b] = 0
    return x, B.log


# ---------------- master ----------------
def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr.rsplit("Summary:", 1)[1]
    return float(s.split("I:", 1)[1].split("LUFS")[0]), float(s.split("Peak:", 1)[1].split("dBFS")[0])


def master(src, dst, target=-14.0, ceiling_db=-1.2, gain=None):
    i_in, _ = lufs(src)
    g = target - i_in if gain is None else gain
    lim = 10 ** (ceiling_db / 20)
    af = (f"highpass=f=25:poles=2,volume={g:.2f}dB,aresample=192000,"
          f"alimiter=limit={lim:.4f}:attack=3:release=80:level=false:latency=true,aresample={SR}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-c:a", "pcm_s24le", dst], check=True)
    return i_in, g


def main():
    os.makedirs(OUT, exist_ok=True)
    D, report, gr = voice()
    M = song()
    Bx, log = effects()
    env = speech_env(D)
    Mc = music_up(carve(M, env)) * 10 ** (MUSIC_DB / 20)
    Bc = carve(Bx, env, -8.0, -2.5) * 10 ** (FX_DB / 20)
    Ds = stereo(D)
    for name, x in (("D", Ds), ("M", Mc), ("B", Bc)):
        sf.write(os.path.join(OUT, f"stem_{name}.wav"), x.astype(np.float32), SR, subtype="FLOAT")
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, (Ds + Mc + Bc).astype(np.float32), SR, subtype="FLOAT")
    i_in, g = master(raw, os.path.join(OUT, "mix.wav"))
    raw2 = os.path.join(OUT, "mix_nomusic_raw.wav")
    sf.write(raw2, (Ds + Bc).astype(np.float32), SR, subtype="FLOAT")
    master(raw2, os.path.join(OUT, "mix_nomusic.wav"), gain=g)
    json.dump(log, open(os.path.join(OUT, "sfx_log.json"), "w"), indent=1)
    i_out, p_out = lufs(os.path.join(OUT, "mix.wav"))
    used = sorted({e["sfx"].split(" x")[0] for e in log if not e["sfx"].split(" ")[0] in
                   ("glint", "pop", "tick", "thump", "sub", "swell", "sheen", "comet", "spark", "fall")})
    print("lines (id, level, gain):", report)
    print(f"voice compressor: max {gr.min():.1f} dB, median while talking {np.median(gr[gr < -0.1]):.1f} dB")
    print(f"mix: in {i_in:.1f} LUFS, gain {g:+.2f} dB -> {i_out:.1f} LUFS, peak {p_out:.1f} dBFS; {len(log)} effects")
    print(f"library effects used: {len(used)}/28", used)


FX_DB = -1.5                                              # the sound design supports; voice and song lead
MUSIC_DB = -12.0                                          # the song is mastered at -8.7 dB RMS

if __name__ == "__main__":
    main()
