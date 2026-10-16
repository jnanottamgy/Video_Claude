"""Sound for the CR aura edit: the hook dialogue, the song from its first downbeat, and the SFX.

  python3 tools/mix.py   -> renders/mix.wav (with music), renders/mix_nomusic.wav (dialogue + SFX)

Dialogue: the four hook lines cut from the source (30 ms fades at every edge), lifted toward the
music's level, the last line tape-stopped into the strobe. Music: the source from 13.06 s laid
so its first downbeat lands on the drop (4.0 s), muffled under the double exposure and opened in
a sweep into the next hit, then the final downbeat re-struck with a reverb tail for the end card.
SFX: the media-use library (Pixabay licence) plus synthesised shutter clicks, sub booms, a
reverse swell and a riser. Master: two-pass loudnorm to -14 LUFS, -1 dBTP.
"""
import json
import os
import subprocess
import sys

import numpy as np
import scipy.signal as ss
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

SR = 48000
LIB = "/home/user/Video_Claude/.agents/skills/media-use/audio/assets/sfx"
SRC = "renders/src/source.mp4"
N = int(round(edl.END * SR)) + SR


def load(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def fade(x, a=0.03, b=0.03):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na:
        x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x


def place(buf, x, t, gain_db=0.0):
    i = int(round(t * SR))
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i] * 10 ** (gain_db / 20)


def db_rms(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


# ---------- synthesis ----------
def shutter():
    rng = np.random.default_rng(3)
    def click(n, amp):
        noise = rng.standard_normal(n)
        sos = ss.butter(4, [2500, 9000], "band", fs=SR, output="sos")
        b = ss.sosfilt(sos, noise) * np.exp(-np.arange(n) / (0.004 * SR))
        thunk = np.sin(2 * np.pi * 190 * np.arange(n) / SR) * np.exp(-np.arange(n) / (0.012 * SR)) * 0.6
        return (b + thunk) * amp
    n = int(0.12 * SR)
    y = np.zeros(n)
    y[: int(0.05 * SR)] += click(int(0.05 * SR), 1.0)
    k = int(0.055 * SR)
    y[k:k + int(0.05 * SR)] += click(int(0.05 * SR), 0.6)
    y /= np.abs(y).max()
    return np.stack([y, y * 0.92], 1)


def subboom(f0=62, f1=31, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.22) * np.minimum(t / 0.004, 1)
    y = np.tanh(y * 1.8) / np.tanh(1.8)
    return np.stack([y, y], 1)


def revswell(dur=0.9):
    rng = np.random.default_rng(11)
    n = int(dur * SR)
    noise = rng.standard_normal((n, 2))
    sos = ss.butter(3, 1800, "high", fs=SR, output="sos")
    x = ss.sosfilt(sos, noise, axis=0) * np.exp(-np.arange(n) / (0.25 * SR))[:, None]
    x = x[::-1]                                  # reversed cymbal: swells up to the end
    return x / np.abs(x).max()


def riser(dur=2.0):
    rng = np.random.default_rng(5)
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal((n, 2))
    out = np.zeros((n, 2))
    blk = 1024
    for i in range(0, n, blk):
        u = (i + blk / 2) / n
        fc = 300 * (6000 / 300) ** u
        sos = ss.butter(2, [fc * 0.7, min(fc * 1.4, 20000)], "band", fs=SR, output="sos")
        out[i:i + blk] = ss.sosfilt(sos, noise[i:i + blk], axis=0)
    tone = np.sin(2 * np.pi * np.cumsum(220 * (5.0 ** (t / dur))) / SR) * 0.15
    out = out / np.abs(out).max() + tone[:, None]
    return out * ((t / dur) ** 2.2)[:, None]


def tape_stop(x, dur):
    """Slow the last dur seconds of x down to a stop (pitch falls with it)."""
    n = int(dur * SR)
    head, tail = x[:-n], x[-n:]
    rate = np.linspace(1.0, 0.0, n) ** 1.3
    pos = np.cumsum(rate)
    pos = pos[pos < len(tail) - 1]
    i0 = np.floor(pos).astype(int)
    u = (pos - i0)[:, None]
    slowed = tail[i0] * (1 - u) + tail[i0 + 1] * u
    slowed *= np.linspace(1, 0.2, len(slowed))[:, None]
    return np.concatenate([head, slowed])


def reverb(x, t60=2.2, wet=0.5):
    rng = np.random.default_rng(21)
    n = int(t60 * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * np.arange(n) / n)[:, None]
    ir = ss.sosfilt(ss.butter(2, 6000, "low", fs=SR, output="sos"), ir, axis=0)
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([ss.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)
    out = np.zeros_like(y)
    out[: len(x)] += x * (1 - wet)
    return out + y * wet


def lib(name, start=None, length=None):
    x = load(f"{LIB}/{name}.mp3")
    if start is not None:
        a = int(start * SR)
        x = x[a: a + (int(length * SR) if length else None)]
    return x


def muffle(x, t_in, t_hold_end, t_open, cut=850.0):
    """Low-pass from t_in, holding `cut` Hz until t_hold_end, sweeping back open by t_open."""
    f, tt, Z = ss.stft(x.T, fs=SR, nperseg=2048, noverlap=1536)
    T = tt
    fc = np.full(len(T), 24000.0)
    m1 = (T >= t_in) & (T < t_hold_end)
    fc[m1] = cut
    m2 = (T >= t_hold_end) & (T < t_open)
    u = (T[m2] - t_hold_end) / (t_open - t_hold_end)
    fc[m2] = cut * (20000 / cut) ** (u ** 1.6)
    ramp_in = (T >= t_in - 0.05) & (T < t_in)
    fc[ramp_in] = 24000 * (cut / 24000) ** ((T[ramp_in] - (t_in - 0.05)) / 0.05)
    g = 1 / np.sqrt(1 + (f[:, None] / fc[None, :]) ** 6)
    _, y = ss.istft(Z * g[None], fs=SR, nperseg=2048, noverlap=1536)
    y = y.T[: len(x)]
    if len(y) < len(x):
        y = np.pad(y, ((0, len(x) - len(y)), (0, 0)))
    return y


# ---------- the mix ----------
HOOK = [("her_claim", 0.20, 2.26, 0.0), ("host_please", 4.00, 4.62, 2.06), ("her_maaa", 4.933, 5.50, 2.68),
        ("host_take2", 7.25, 7.70, 3.2467)]


def build():
    src = load(SRC)
    D = np.zeros((N, 2))
    for name, a, b, t_out in HOOK:
        seg = src[int(a * SR):int(b * SR)]
        seg = ss.sosfilt(ss.butter(2, 85, "high", fs=SR, output="sos"), seg, axis=0)
        if name == "host_take2":
            seg = tape_stop(seg, 0.10)
        place(D, fade(seg, 0.03, 0.03), t_out)
    # lift the dialogue to sit ~6 dB under the music
    speech = D[: int(3.75 * SR)]
    gain = -17.0 - db_rms(speech[np.abs(speech).max(1) > 1e-4])
    D *= 10 ** (gain / 20)
    D = np.tanh(D * 1.4) / 1.4                       # gentle peak control

    M = np.zeros((N, 2))
    s0 = 13.06
    song = src[int(s0 * SR):]
    song = fade(song, 0.004, 0.02)
    place(M, song, edl.DROP - (edl.SONG_T0 - s0))
    M = muffle(M, edl.tq(16), edl.tq(21) + 0.05, edl.tq(22) - 0.01)
    # the final downbeat: the drop's first half-beat, re-struck with a long tail
    hit = src[int(s0 * SR):int((edl.SONG_T0 + edl.EIGHTH * 2) * SR)]
    hit = fade(hit, 0.004, 0.08)
    place(M, reverb(hit, 2.6, 0.45), edl.SONG_END - (edl.SONG_T0 - s0))
    tail = int((edl.END - 0.05) * SR)
    M[tail:] *= 0
    fo = int(0.9 * SR)
    M[tail - fo:tail] *= np.linspace(1, 0, fo)[:, None] ** 1.5

    X = np.zeros((N, 2))
    sh, boom, swell = shutter(), subboom(), revswell(0.55)
    # the library impacts ring for 2 s at full level; the song's 808 already carries the low end, so keep
    # only their attack (0.45 s, faded) and thin their sub
    hp = ss.butter(2, 70, "high", fs=SR, output="sos")
    ib1 = fade(ss.sosfilt(hp, lib("impact-bass-1", 0.0, 0.45), axis=0), 0.0, 0.3)
    ib2 = fade(ss.sosfilt(hp, lib("impact-bass-2", 1.98, 0.45), axis=0), 0.004, 0.3)
    wsh, wcin = lib("whoosh-short"), lib("whoosh-cinematic")
    gl1, spark = lib("glitch-1", 0.12, 0.45), lib("sparkle")
    tq = edl.tq
    ev = [
        # hook
        (2.697 - 0.02, lib("pop"), -14),                              # the MAAA zoom
        (3.70 - 0.55, swell, -15),                                    # swell into the strobe
        (3.70, gl1, -12),                                             # strobe glitches
        # the drop
        (edl.DROP - 0.06, ib1, -9), (edl.DROP, boom, -15), (edl.DROP - 0.06, sh, -12),
        (tq(4) - 0.01, sh, -12),                                       # white silhouette flash
        (tq(6) - 0.17, wsh, -12),                                      # into the slow turn
        (tq(10) - 0.06, ib2, -12), (tq(10) + 0.10, spark, -11),         # pose freeze + +1000 AURA
        (tq(16) - 0.17, wsh, -11), (tq(16) - 0.45, swell, -18),        # suck into the double exposure
        (tq(22) - 1.2, riser(1.2), -17), (tq(22) - 0.06, ib1, -11), (tq(22), boom, -17),   # filter opens
        (tq(26) - 0.01, sh, -13), (tq(27) - 0.01, sh, -14), (tq(28) - 0.01, sh, -13),    # curtain flashes
        (tq(32) - 2.54, wcin, -17), (tq(32) - 0.06, ib1, -12),          # whip into the smirk
        (tq(35) - 0.01, sh, -12),                                      # smirk silhouette flash
        (tq(38) - 0.02, lib("glitch-3", 0.2, 0.5), -4),               # chroma hit
        (tq(42) - 0.17, wsh, -13),                                     # into the slow wave
        (tq(45) - 0.17, wsh, -14),                                    # the walk speeds up
        (tq(48) - 0.06, ib1, -12), (tq(48) + 0.05, spark, -13),        # CLASS REPRESENTATIVE
        (edl.SONG_END - 2.0, riser(2.0), -16),                        # build to the end card
        (edl.SONG_END - 0.06, ib1, -6), (edl.SONG_END, boom, -12), (edl.SONG_END - 0.01, sh, -12),
        (edl.SONG_END + 0.25, spark, -12),
    ]
    for t, x, g in ev:
        place(X, x, t, g)
    return D, M, X


def master(x, out):
    tmp = out + ".pre.wav"
    sf.write(tmp, x.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    js = r.stderr[r.stderr.rfind("{"): r.stderr.rfind("}") + 1]
    m = json.loads(js)
    af = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", out], check=True)
    os.remove(tmp)
    print(out, "input I", m["input_i"], "-> -14")


def main():
    D, M, X = build()
    n = int(round(edl.END * SR))
    master((D + M + X)[:n], "renders/mix.wav")
    master((D + X * 1.2)[:n], "renders/mix_nomusic.wav")


if __name__ == "__main__":
    main()
