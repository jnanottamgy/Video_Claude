"""TaxWise Singapore reel: the soundtrack, rebuilt simply (v3).

  V  his voice: renders/audio/dialogue_src.wav (his original stereo recording, only gently EQ'd: tools/dialogue.py),
     cut onto the timeline per edl.SEGMENTS with short fades, every line at the same loudness (LUFS), a light 2:1 compressor
     (stereo-linked, smooth) and a peak catcher. Nothing else touches it.
  M  the song per edl.MUSIC: in on the pickup beat, the 6-bar lift crossfaded on the bar line at 30.5, half a beat of
     silence before the drop ("into... SINGAPORE"), the last chord fading out. A smooth broadband duck under his
     voice (-6 dB, 150 ms down, 500 ms back up) and lifts where he is silent.
  B  a curated set of effects on the big moments, from the user's library (library/sfx) plus a few glints tuned
     to the song (B minor): whooshes on the transitions and the type, the drop's bass hit, risers into the drop,
     the lift and the bloom, the logo's sting.
  Master: -14 LUFS, -1 dBTP (Instagram, Shorts, LinkedIn).

  python3 tools/mix.py   ->  renders/audio/mix.wav, mix_nomusic.wav (voice + effects, same gain),
                             stem_{V,M,B}.wav, sfx_log.json
"""
import json
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
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
DROP, BREAK, LIFT, END = edl.DROP, edl.BREAK, edl.LIFT, edl.END
GAP = (DROP - 0.25, DROP)                     # half a beat of silence before the drop
METER = pyln.Meter(SR)
NOTE = {"B5": 987.77, "D6": 1174.66, "F#6": 1479.98, "B6": 1975.53, "D7": 2349.32, "F#7": 2959.96}

VOICE_LEVEL = -16.5                           # every line at the same integrated loudness (LUFS, before the master)
MUSIC_DB = -14.0                              # the song file is mastered loud (-8.7 dB RMS)
DUCK_DB = -7.0                                # the song under his voice
NO_DUCK = [(12.45, 14.22)]                    # the drop hits at full level, "SINGAPORE" and all
MUSIC_UP = [(12.50, 14.22, 3.0), (24.97, 25.47, 3.0), (35.12, 35.82, 3.0), (42.37, 42.97, 3.0), (47.85, 52.0, 6.0)]


# ---------------- helpers ----------------
def sos(kind, f, order=2):
    return butter(order, f, kind, fs=SR, output="sos")


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


def smooth_env(on, att, rel, hop):
    """One-pole smoothing of a 0..1 control: `att` s to rise, `rel` s to fall."""
    a, r = 1 - np.exp(-hop / (att * SR)), 1 - np.exp(-hop / (rel * SR))
    e = np.zeros(len(on))
    for i in range(len(on)):
        p = e[i - 1] if i else 0.0
        e[i] = p + (a if on[i] > p else r) * (on[i] - p)
    return e


def band_db(m, lo=300, hi=3400, hop=SR // 100):
    b = sosfiltfilt(sos("bandpass", [lo, hi]), m)
    k = len(b) // hop
    return 20 * np.log10(np.sqrt((b[:k * hop].reshape(k, hop) ** 2).mean(1) + 1e-14))


# ---------------- V: the voice ----------------
def active_level(m):
    db = band_db(m)
    act = db[db > np.percentile(db, 95) - 20]
    return 10 * np.log10(np.mean(10 ** (act / 10)))


def compress(x, ratio=2.0, below_peak_db=8.0, knee=10.0, att=0.015, rel=0.200, hop=48):
    """A light, smooth, stereo-linked compressor: its threshold sits `below_peak_db` under the loud speech, so it
    only rounds off the loudest words (about 2-4 dB)."""
    m = 0.5 * (x[:, 0] + x[:, 1])
    k = len(m) // hop
    lvl = 10 * np.log10(np.convolve(m ** 2, np.ones(480) / 480, "same")[:k * hop].reshape(k, hop).mean(1) + 1e-14)
    thr = np.percentile(lvl[lvl > -70], 97) - below_peak_db
    over = lvl - thr
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 / ratio - 1), (1 / ratio - 1) * (over + knee / 2) ** 2 / (2 * knee)))
    a, r = 1 - np.exp(-hop / (att * SR)), 1 - np.exp(-hop / (rel * SR))
    g = np.zeros(k)
    for i in range(k):
        p = g[i - 1] if i else 0.0
        g[i] = p + (a if gr[i] < p else r) * (gr[i] - p)
    gain = np.interp(np.arange(len(m)), np.arange(k) * hop + hop / 2, 10 ** (g / 20))
    return x * gain[:, None], g


def peak_catch(x, ceil_db=-2.0, look=0.002, rel=0.080, hop=24):
    """A transparent lookahead peak limiter (stereo-linked) for the odd plosive."""
    from scipy.ndimage import minimum_filter1d
    pk = np.abs(x).max(1)
    need = minimum_filter1d(np.minimum(1.0, 10 ** (ceil_db / 20) / (pk + 1e-12)), size=2 * int(look * SR) + 1)
    red = -20 * np.log10(need)
    k = len(red) // hop
    rb = red[:k * hop].reshape(k, hop).max(1)
    out = np.zeros(k)
    dec = np.exp(-hop / (rel * SR))
    for i in range(k):
        out[i] = max(rb[i], (out[i - 1] if i else 0.0) * dec)
    g = 10 ** (-np.interp(np.arange(len(pk)), np.arange(k) * hop + hop / 2, out) / 20)
    return x * np.minimum(g, need)[:, None]


def voice():
    x, sr = sf.read(DLG, always_2d=True)
    assert sr == SR
    V = np.zeros((N + SR, 2))
    report = []
    for s in edl.SEGMENTS:
        a, b = int(round(s["src"] * SR)), int(round(s["src_end"] * SR))
        y = fade(x[a:b], 0.015, 0.040)
        lv = METER.integrated_loudness(y)                # perceived loudness (EBU R128) of the whole line
        g = VOICE_LEVEL - lv
        i = int(round(s["out"] * SR))
        V[i:i + len(y)] += y * 10 ** (g / 20)
        report.append(f"{s['id']} {g:+.1f} dB")
    V = V[:N]
    V, gr = compress(V)
    V = peak_catch(V)
    return V, report, gr


def speech_presence(V, hop=SR // 100, hold=0.5):
    """0..1: is he speaking (the voice's speech band within 30 dB of its loud level). Held for 0.5 s, so the
    song doesn't swell up in the short pauses between his words (no pumping); off in the NO_DUCK windows."""
    from numpy.lib.stride_tricks import sliding_window_view
    db = band_db(0.5 * (V[:, 0] + V[:, 1]), hop=hop)
    on = np.clip((db - (np.percentile(db[db > -80], 90) - 30)) / 8, 0, 1)
    h = int(hold * SR / hop)
    on = sliding_window_view(np.pad(on, (h, 0)), h + 1).max(1)
    t = (np.arange(len(on)) * hop + hop / 2) / SR
    for a, b in NO_DUCK:
        on[(t >= a) & (t < b)] = 0.0
    e = smooth_env(on, 0.15, 0.50, hop)
    return np.interp(np.arange(len(V)), np.arange(len(e)) * hop + hop / 2, e)


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
    a, b = int(GAP[0] * SR), int(GAP[1] * SR)            # half a beat of silence before the drop
    k = int(0.025 * SR)
    M[a - k:a] *= np.cos(np.linspace(0, np.pi / 2, k))[:, None]
    M[a:b] = 0
    k = int(0.9 * SR)                                    # the last chord fades out
    M[-k:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
    return M


def music_gain(presence):
    """The song's level: MUSIC_DB, ducked under his voice, lifted in the windows where he is silent."""
    t = np.arange(N) / SR
    up = np.zeros(N)
    for a, b, db in MUSIC_UP:
        w = np.clip(np.minimum((t - a) / 0.25, (b - t) / 0.25 + (9 if b >= edl.DURATION else 0)), 0, 1)
        up = np.maximum(up, db * (0.5 - 0.5 * np.cos(np.pi * w)))
    return 10 ** ((MUSIC_DB + DUCK_DB * presence[:N] + up) / 20)


# ---------------- B: the effects ----------------
def glint(f, dur=1.2, width=1.8):
    """A soft crystal 'tick of light', tuned: harmonic partials, detuned L/R for width."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ch, det in ((0, -width / 2), (1, width / 2)):
        ff = f + det
        x = (np.sin(2 * np.pi * ff * t) * np.exp(-t / (dur / 3.2))
             + 0.40 * np.sin(2 * np.pi * 2.0 * ff * t + 0.3) * np.exp(-t / (dur / 5.0))
             + 0.15 * np.sin(2 * np.pi * 3.01 * ff * t + 1.1) * np.exp(-t / (dur / 8.0)))
        out[:, ch] = x * np.minimum(1, t / 0.002)
    return out / np.abs(out).max()


def chord(names, dur=1.6, spread=0.04):
    parts = [glint(NOTE[k], dur) for k in names]
    out = np.zeros((max(len(p) for p in parts) + int(spread * SR * len(parts)), 2))
    for k, p in enumerate(parts):
        i = int(k * spread * SR)
        out[i:i + len(p)] += p
    return out / np.abs(out).max()


def sub_hit(dur=1.4, f0=80, f1=34):
    n = int(dur * SR)
    f = f1 + (f0 - f1) * np.exp(-np.arange(n) / (0.2 * SR))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-np.arange(n) / (dur / 3.2 * SR)) * np.minimum(1, np.arange(n) / 96)
    return np.stack([x, x], 1) / np.abs(x).max()


class Bus:
    def __init__(self):
        self.x = np.zeros((N + SR, 2))
        self.log = []

    def put(self, x, t, gain_db, hit=0.0, hp=None, name="synth"):
        if hp:
            x = sosfilt(sos("highpass", hp), x, axis=0)
        i = int(round((t - hit) * SR))
        if i < 0:
            x, i = x[-i:], 0
        j = min(len(self.x), i + len(x))
        if j > i:
            self.x[i:j] += x[:j - i] * 10 ** (gain_db / 20)
        self.log.append(dict(t=round(t, 3), sfx=name, gain_db=gain_db))

    def lib(self, sfx_id, t, gain_db, hp=None, length=None, start=None, at=None, fade_in=0.0):
        """A library effect with its hit point on t. at: another alignment point in the file (the build-ups peak
        well before their end); start: keep only this much lead-in; length: keep this much after the hit."""
        x, hit = sfx.load(sfx_id, SR)
        if at is not None:
            hit = at
        if start is not None and hit > start:
            x, hit = x[int((hit - start) * SR):], start
        if length is not None:
            x = fade(x[:int((hit + length) * SR)], 0, min(0.3, length / 2))
        if fade_in:
            x = fade(x, fade_in, 0)
        self.put(x, t, gain_db, hit=hit, hp=hp, name=sfx_id)


def effects():
    B = Bus()
    L, P = B.lib, B.put
    # the hook: a horizon line ignites, the skyline rises, A NEW HORIZON, a globe spins up
    L("fast-swoosh", 0.30, -22, hp=300)
    P(glint(NOTE["B6"], 1.4), 0.02, -26, name="glint (the spark)")
    L("slow-woosh", 2.60, -24, hp=150)
    P(chord(["B6", "D7", "F#7"]), 3.07, -26, name="glint chord (the skyline completes)")
    L("woosh-1", 4.40, -25, hp=150)
    L("bass-woosh-2", 5.31, -24, hp=60, length=0.6)
    # the intro: the aura pull-out reveals his name; the music drops out on "TaxWise"; the build
    L("slow-motion", 6.10, -20, hp=90)
    L("cinematic-electric-hit", 6.10, -21, hp=60, length=2.5, start=0.3)
    L("woosh-3", 6.66, -24, hp=250)
    L("fast-swoosh", 7.72, -27, hp=400)
    L("lowpass-woosh", BREAK + 0.25, -26, hp=80)
    P(glint(NOTE["B6"], 1.5), 9.12, -27, name="glint (the TW mark's shine)")
    L("woosh-4", 11.65, -25, hp=150)
    L("build-up-2", GAP[0], -23, hp=100, at=2.85)
    # THE DROP on "SINGAPORE"
    L("bass-woosh-1", DROP, -12, hp=35, start=0.0)
    L("cinematic-electric-hit", DROP, -21, hp=80, length=2.0, start=0.0)
    P(sub_hit(1.6), DROP, -17, name="sub hit (the drop)")
    P(chord(["B6", "D7", "F#7"]), 12.86, -25, name="glint chord (the mark completes)")
    L("woosh-3", 13.00, -25, hp=300)
    L("glitchy-woosh", 14.17, -19, hp=80)
    # the team and the services
    L("fast-swoosh", 14.50, -25, hp=300)
    L("sword-impact", 16.34, -25, hp=200, length=1.0)
    L("bass-woosh-2", 16.34, -20, hp=60, length=0.8)
    L("woosh-3", 16.84, -26, hp=300)
    L("slow-woosh", 18.50, -22, hp=120)
    L("bass-woosh-2", 18.74, -22, hp=60, length=0.8)
    P(glint(NOTE["D7"], 1.3), 18.76, -26, name="glint (the TW mark condenses)")
    for k, t in enumerate((20.66, 21.38, 22.50, 23.38, 24.18)):        # the five services fly out on their words
        L("woosh-3" if k % 2 == 0 else "fast-swoosh", t + 0.12, -26, hp=300)
        P(glint(NOTE[["B6", "D7", "F#7", "B6", "D7"][k]], 0.9), t + 0.25, -29, name="glint (a service lands)")
    L("build-up-1", LIFT, -24, hp=150, at=1.55)
    L("cinematic-electric-hit", LIFT, -21, hp=60, length=3.0, start=0.5)
    L("woosh-1", 25.10, -22, hp=120)
    # the globe
    L("lowpass-woosh", 25.75, -26, hp=80)
    L("woosh-1", 26.15, -24, hp=120)
    P(glint(NOTE["B6"], 1.0), 27.52, -28, name="glint (BANGALORE)")
    P(glint(NOTE["D7"], 1.0), 27.64, -29, name="glint (CHENNAI)")
    L("slow-woosh", 29.40, -24, hp=150)                                 # the arc travels to Singapore
    L("bass-woosh-2", 29.92, -21, hp=60, length=0.8)
    P(chord(["F#6", "B6", "D7"]), 29.94, -25, name="glint chord (SINGAPORE)")
    L("woosh-3", 33.74, -25, hp=300)
    L("fast-swoosh", 34.38, -27, hp=400)
    L("wind-impact", 35.57, -22, hp=90, start=1.6, fade_in=1.2)        # into the gold pulse
    # the values
    L("slow-motion", 35.57, -21, hp=90)
    L("fast-swoosh", 36.30, -28, hp=400)
    for t, note in ((38.24, "B6"), (39.20, "D7"), (40.96, "F#7")):
        L("woosh-3", t, -27, hp=350)
        P(glint(NOTE[note], 1.0), t + 0.12, -29, name="glint (a value lands)")
    P(chord(["B6", "D7", "F#7"]), 41.92, -28, name="glint chord (all three glow)")
    # the finale
    L("woosh-2", 42.40, -24, hp=100)
    L("bass-woosh-2", 43.07, -23, hp=60, length=0.8)
    P(glint(NOTE["F#7"], 1.3), 43.42, -27, name="glint (the mark's diamond)")
    L("fast-swoosh", 44.16, -28, hp=400)
    P(glint(NOTE["D7"], 1.2), 44.59, -27, name="glint (the pin lands)")
    L("build-up-3", 48.25, -24, hp=120, fade_in=1.0)
    L("woosh-1", 48.30, -22, hp=100)
    # the logo end card
    P(sub_hit(2.2, 70, 30), END, -17, name="sub hit (the logo)")
    L("cinematic-electric-hit", END, -22, hp=60, length=3.0, start=0.15)
    L("sword-impact", 49.00, -26, hp=300, length=2.4)                   # the shield locks
    P(glint(NOTE["F#7"], 2.2), 49.02, -23, name="glint (the diamond)")
    L("fast-swoosh", 50.62, -30, hp=500)
    x = B.x[:N]
    k = int(0.4 * SR)
    x[-k:] *= np.linspace(1, 0, k)[:, None]
    a, b = int(GAP[0] * SR), int(DROP * SR) - 96                          # the silence before the drop stays silent
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
    V, report, gr = voice()
    M = song() * music_gain(speech_presence(V))[:, None]
    Bx, log = effects()
    for name, x in (("V", V), ("M", M), ("B", Bx)):
        sf.write(os.path.join(OUT, f"stem_{name}.wav"), x.astype(np.float32), SR, subtype="FLOAT")
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, (V + M + Bx).astype(np.float32), SR, subtype="FLOAT")
    i_in, g = master(raw, os.path.join(OUT, "mix.wav"))
    raw2 = os.path.join(OUT, "mix_nomusic_raw.wav")
    sf.write(raw2, (V + Bx).astype(np.float32), SR, subtype="FLOAT")
    master(raw2, os.path.join(OUT, "mix_nomusic.wav"), gain=g)
    json.dump(log, open(os.path.join(OUT, "sfx_log.json"), "w"), indent=1)
    i_out, p_out = lufs(os.path.join(OUT, "mix.wav"))
    print("line gains:", ", ".join(report))
    print(f"voice compressor: max {gr.min():.1f} dB, while talking median {np.median(gr[gr < -0.05]):.1f} dB")
    print(f"mix: in {i_in:.1f} LUFS, gain {g:+.2f} dB -> {i_out:.1f} LUFS, peak {p_out:.1f} dBFS; {len(log)} effects")


if __name__ == "__main__":
    main()
