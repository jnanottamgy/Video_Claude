"""ADR: lay HK Vinay's re-recorded lines onto the reel's timing (classical DSP, offline).

He re-recorded his six lines to the karaoke guide (tools/karaoke.py): renders/src/rerecord_*/take_*.m4a, one file
per line, named by recording time, in script order. Each take is fitted to the original performance the way
dialogue-replacement tools do it.

1. **The guide.** It is the echo-free Adobe version of the original: sample-aligned to it, so it keeps the
   original's exact timing, without the room tails that would blur the match. Without it, the original itself.
2. **The match.** Both recordings become 10 ms frames: MFCCs, deltas and loudness. Dynamic time warping finds the
   frame-to-frame correspondence.
3. **The anchors** are the points that must line up:
   - every onset after a pause in the guide (exact, from its speech detector);
   - on camera (A lines), also his word onsets inside phrases, at least 0.2 s apart.
   Each anchor's place in the take comes from the match, snapped to the take's own onset when one is close.
4. **The fit,** anchor to anchor:
   - his pauses absorb the timing difference first. Each pause keeps 80 ms of natural decay after a word and
     40 ms before the next word; only its middle is shortened or lengthened.
   - only then do the words themselves speed up or slow down, within limits:
       - on camera: 0.82-1.22x, so the words land where his lips move;
       - voice-over: 0.92-1.09x, so the take keeps its own rhythm. The graphics are cued on phrase starts, and
         those are anchored.
   - what can't be absorbed is carried to the next anchor.
5. **The render.** WSOLA (waveform-similarity overlap-add) plays the take along this time map with its pitch
   untouched. Where the map runs at 1:1, the take comes out sample-exact.
   - Each line fades in 0.06-0.10 s before its first word: some takes begin with the phone's gain-pumped room noise.
   - Each line ends 0.25 s after its last.

  python3 tools/adr.py [--plots]  ->  renders/audio/adr/<line>.wav (mono float, on the line's source window),
                                      adr.json (anchors, residuals, speeds), renders/verify/adr_<line>.png
"""
import glob
import json
import os
import subprocess
import sys

import librosa
import numba
import numpy as np
import soundfile as sf
from scipy.fft import dct
from scipy.ndimage import binary_closing, minimum_filter1d
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
import dialogue as Dg  # noqa: E402
import edl  # noqa: E402

SR = 48000
HOP = 480                                   # 10 ms analysis frames
TAKES = os.path.join(edl.ROOT, "renders/src/rerecord_*/take_*.m4a")
OUT = os.path.join(edl.ROOT, "renders/audio/adr")
MARGIN = 0.25                               # s of source timeline rendered on each side of a line's window
DTW_PEN, DTW_PEN_PAUSE = 1.0, 0.05          # DTW: cost of holding/skipping a 10 ms frame of his speech / pauses
RATE = {"A": (0.80, 1.22), "G": (0.84, 1.20)}   # how much faster (>1) or slower his words may play
WEIGHT = {"A": dict(onset=2.0, word=1.0, early=3.0),   # how much a missed anchor costs (per frame squared);
          "G": dict(onset=1.0, word=0.15, early=1.0)}  # on camera, audio ahead of the lips costs three times more
CUES = {"G1": "team thirty in-house expertise finance taxation payroll compliance advisory",  # words the graphics
        "G2": "India helping Singapore's financial we connections across borders"}            # hit (slots/SPEC_*.md)
CUE_WEIGHT = 2.0
LAM, MU = 30.0, 2.0                         # cost of a speed change (x speech frames x ln(speed)^2), of squeezing
SEARCH = 40                                 # a pause's natural ends (per frame); anchors may move +-0.4 s
V_COST, V_MIN = 12.0, 4                     # opening a virtual pause: its cost, and at least 40 ms of silence
V_RAMP = 1.5                                # frames: the fade into and out of a virtual pause
END_RATE = (0.92, 1.10)                     # a line's last stretch, to the end of his last word
DECAY, PRE = 8, 4                           # frames of natural sound kept after a word / before an onset
WORD_GAP = 15                               # word anchors at least 0.15 s apart
REFINE = 12                                 # anchors refined +-0.12 s by matching the syllable's loudness contour
LEAD, LEAD_RAMP, TAIL, TAIL_RAMP = 6, 4, 15, 10     # frames: the line's fade-in before the first word, fade-out
N_WIN, HS, TOL = 1024, 512, 384             # WSOLA: 21 ms Hann frames, 50% overlap, +-8 ms similarity search


def take_paths():
    p = sorted(glob.glob(TAKES))
    return p if len(p) == len(edl.SEGMENTS) else None


def load_mono(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def guide_track():
    """The original performance, mono, on the source timeline: the echo-free Adobe version when present."""
    ref = Dg.load_src()
    p = Dg.enhanced_path()
    return (Dg.load_enhanced(p, ref)[0] if p else ref).mean(1)


def window(seg):
    return seg["src"] - MARGIN, seg["src_end"] + MARGIN


# ---------------- analysis ----------------
def band_level(x, lo=300, hi=4000):
    """Speech-band level (dB) per 10 ms frame, frame i centred on sample i * HOP (as librosa's frames)."""
    f = sosfiltfilt(butter(4, [lo, hi], "bandpass", fs=SR, output="sos"), x)
    k = len(x) // HOP + 1
    f = np.pad(f, (HOP // 2, k * HOP))[:k * HOP].reshape(k, HOP)
    return 10 * np.log10((f ** 2).mean(1) + 1e-14)


def vad(e):
    """Speech frames: within 32 dB of the loud speech, and 12 dB over the local floor (a 1 s running minimum), so a
    phone's gain-pumped room noise before he starts doesn't count."""
    return e > np.maximum(np.percentile(e, 95) - 32, minimum_filter1d(e, 101) + 12)


def islands(v, close=9, min_len=6):
    """Runs of speech frames (gaps under 90 ms bridged) -> [(start, end)] in frames."""
    v = binary_closing(v, np.ones(close, bool)) | v
    d = np.diff(np.concatenate([[0], v.astype(int), [0]]))
    return [(int(a), int(b)) for a, b in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]) if b - a >= min_len]


def features(x, speech):
    """10 ms frames: [12 MFCC, 12 deltas, loudness], normalised over the speech frames."""
    S = librosa.feature.melspectrogram(y=x.astype(np.float32), sr=SR, n_fft=2048, hop_length=HOP, win_length=1200,
                                       n_mels=40, fmin=100, fmax=7000)
    n = min(S.shape[1], len(speech))
    S, speech = S[:, :n], speech[:n]
    L = 10 * np.log10(S + 1e-10)
    e = 10 * np.log10(S.mean(0) + 1e-10)
    c = dct(L, axis=0, norm="ortho")[1:13]
    c = (c - c[:, speech].mean(1, keepdims=True)) / (c[:, speech].std(1, keepdims=True) + 1e-6)
    d = librosa.feature.delta(c, width=5)
    loud = np.clip((e - np.percentile(e[speech], 95)) / 8.0, -4, 1)[None, :] * 1.5
    return np.vstack([c, d, loud]).T.astype(np.float64)


@numba.njit(cache=True)
def _dtw(C, pen):
    """Monotonic alignment of guide frames (rows) to take frames (cols). Steps: both advance (cost C); the guide
    advances while the take holds frame j, or the take advances (frame j squeezed out) while the guide holds:
    cost C + pen[j]. Returns the path as two index arrays."""
    n, m = C.shape
    D = np.full((n, m), np.inf)
    B = np.zeros((n, m), np.int8)
    D[0, 0] = C[0, 0]
    for i in range(n):
        for j in range(m):
            if i == 0 and j == 0:
                continue
            best, b = np.inf, 0
            if i > 0 and j > 0:
                best = D[i - 1, j - 1]
            if i > 0 and D[i - 1, j] + pen[j] < best:
                best, b = D[i - 1, j] + pen[j], 1
            if j > 0 and D[i, j - 1] + pen[j] < best:
                best, b = D[i, j - 1] + pen[j], 2
            D[i, j] = best + C[i, j]
            B[i, j] = b
    pi, pj = np.empty(n + m, np.int64), np.empty(n + m, np.int64)
    i, j, k = n - 1, m - 1, 0
    while True:
        pi[k], pj[k] = i, j
        k += 1
        if i == 0 and j == 0:
            break
        b = B[i, j]
        if b == 0:
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        else:
            j -= 1
    return pi[:k][::-1], pj[:k][::-1]


def dtw_maps(g, d, vg, vd):
    """-> fwd[i]: the take frame matching guide frame i; inv[j]: the guide frame matching take frame j."""
    Fg, Fd = features(g, vg), features(d, vd)
    n, m = len(Fg), len(Fd)
    vg, vd = vg[:n], vd[:m]
    C = np.sqrt(np.maximum((Fg ** 2).sum(1)[:, None] + (Fd ** 2).sum(1)[None, :] - 2 * Fg @ Fd.T, 0))
    C[np.ix_(~vg, ~vd)] = np.minimum(C[np.ix_(~vg, ~vd)], 0.5)      # pause matches pause: cheap
    pi, pj = _dtw(C, np.where(vd, DTW_PEN, DTW_PEN_PAUSE))
    fwd = np.bincount(pi, pj, n) / np.maximum(np.bincount(pi, None, n), 1)
    inv = np.bincount(pj, pi, m) / np.maximum(np.bincount(pj, None, m), 1)
    return fwd, inv


# ---------------- the time map ----------------
def runs_between(isl, a, b, splits=()):
    """Speech/pause runs of the take covering frames [a, b): [(start, end, kind)], kind s = speech, p = pause,
    v = a virtual pause (zero length) at a split point inside his speech."""
    out, t = [], a
    for s, e in isl:
        s, e = max(s, a), min(e, b)
        if e <= s:
            continue
        if s > t:
            out.append((t, s, "p"))
        cuts = [v for v in splits if s < v < e]
        for v in cuts:
            out += [(s, v, "s"), (v, v, "v")]
            s = v
        out.append((s, e, "s"))
        t = e
    if t < b:
        out.append((t, b, "p"))
    return out


def pieces_of(runs):
    """Take runs -> [(take_len, kind)]: s = speech; r = a pause's natural end (DECAY after a word, PRE before the
    next), kept 1:1; m = a pause's elastic middle; v = a virtual pause (silence that can be opened in his speech)."""
    pieces = []
    for k, (s, e, kind) in enumerate(runs):
        n = e - s
        if kind in "sv":
            pieces.append((n, kind))
            continue
        after = k > 0 and runs[k - 1][2] == "s"
        before = (k + 1 < len(runs) and runs[k + 1][2] == "s") or k + 1 == len(runs)
        dec = min(DECAY, int(0.4 * n)) if after else 0
        pre = min(PRE, int(0.25 * n)) if before else 0
        pieces += [(dec, "r"), (n - dec - pre, "m"), (pre, "r")]
    return pieces


def seg_stats(runs):
    pc = pieces_of(runs)
    return (sum(n for n, k in pc if k == "s"), sum(n for n, k in pc if k == "r"), sum(n for n, k in pc if k == "m"),
            any(k == "m" for n, k in pc), any(k == "v" for n, k in pc))


def seg_cost(st, G, lo, hi):
    """Cost of fitting a take segment (stats st) into G guide frames (array), inf where impossible."""
    S, R, E, has_pause, has_v = st
    G = np.asarray(G, float)
    c = np.full(G.shape, np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = S / G
        speed = LAM * S * np.log(r) ** 2
    if has_pause:
        c = np.where(G >= S + R, 0.0, c)
        c = np.where((G >= S) & (G < S + R), MU * (S + R - G), c)
        c = np.where((G > 0) & (G < S) & (r <= hi), speed + MU * R, c)
    else:
        c = np.where((G > 0) & (r >= lo) & (r <= hi), speed, c)
        if has_v:                                       # or open the virtual pause(s): silence where he ran on
            c = np.minimum(c, np.where(G >= S + V_MIN, V_COST, np.inf))
    return c


def fit(runs, G, lo, hi):
    """Lay the take runs onto G guide frames: pauses absorb first (keeping DECAY frames after speech and PRE before
    it at 1:1), else a virtual pause opens, then the speech rate moves within [lo, hi].
    -> ([(take_len, guide_len, kind)], guide frames used, speech rate)."""
    pieces = pieces_of(runs)
    S = sum(n for n, k in pieces if k == "s")
    R = sum(n for n, k in pieces if k == "r")
    E = sum(n for n, k in pieces if k == "m")
    has_pause = any(k == "m" for n, k in pieces)
    nv = sum(1 for n, k in pieces if k == "v")
    r, kr, km, gv = 1.0, 1.0, 1.0, 0.0
    if G >= S + R:
        if has_pause:
            km = (G - S - R) / E if E > 0 else 0.0
            if E == 0:                                # pauses too short to have a middle: let the reserve grow
                kr = (G - S) / max(R, 1e-9)
        elif nv and G >= S + V_MIN and LAM * S * np.log(S / G) ** 2 >= V_COST or (nv and S / G < lo):
            gv = (G - S) / nv                         # open the virtual pause(s)
        else:
            r = min(max(S / max(G, 1e-9), lo), hi) if S else 1.0
    else:
        km = 0.0
        if G >= S:
            kr = (G - S) / max(R, 1e-9)
        else:
            kr = 0.0
            r = min(max(S / max(G, 1e-9), lo), hi)
    out = []
    for n, k in pieces:
        gl = {"s": n / r, "r": n * kr, "m": n * km, "v": gv}[k]
        if n > 0 or gl > 0:
            out.append((n, gl, k))
    return out, sum(gl for _, gl, _ in out), r


def virtual_splits(gis, tis, fwd, ld):
    """Where the original paused (>= 0.1 s) but the take runs on: split points at the take's quietest frame there."""
    gaps = [(e0, s1) for (s0, e0), (s1, e1) in zip(gis, gis[1:]) if s1 - e0 >= 10]
    tgaps = [(e0, s1) for (s0, e0), (s1, e1) in zip(tis, tis[1:])]
    sm = np.convolve(ld, np.ones(3) / 3, "same")
    out = []
    for e0, s1 in gaps:
        ta, tb = int(round(fwd[e0])) - 8, int(round(fwd[s1]))
        if any(y > ta and x < tb + 6 for x, y in tgaps) or tb - ta < 3:
            continue
        out.append((int(ta + np.argmin(sm[ta:tb])), s1))   # (take frame of the split, the guide onset after it)
    return out


def refine(o, t, eg, ed):
    """Move a take anchor (+-REFINE frames) to where the take's loudness contour over the syllable (80 ms before to
    220 ms after) best matches the guide's at o. Kept only if it matches clearly better."""
    o = int(o)
    A = eg[o - 8:o + 22]
    if o < 8 or len(A) < 30:
        return t

    def corr(tt):
        B = ed[tt - 8:tt + 22]
        if tt < 8 or len(B) < 30:
            return -1.0
        return float(np.mean((A - A.mean()) / (A.std() + 1e-9) * (B - B.mean()) / (B.std() + 1e-9)))

    t0 = int(round(t))
    c0 = corr(t0)
    cs = [(corr(t0 + L), t0 + L) for L in range(-REFINE, REFINE + 1)]
    c, tb = max(cs)
    return float(tb) if c > 0.6 and c > c0 + 0.05 else t


def norm(w):
    return w.lower().strip(".,:;!?")


def place_anchors(pts, stats, kind, lo, hi):
    """Dynamic programming over every anchor's guide frame (its target +-SEARCH): the placements that minimise the
    missed anchors (weighted; on camera, audio early costs more) plus the speed changes and squeezed pauses needed
    to fit the take between them. -> placements (guide frames)."""
    W = WEIGHT[kind]
    offs = np.arange(-SEARCH, SEARCH + 1)
    e = offs.astype(float)

    def err(k):
        w = CUE_WEIGHT if pts[k][2] == "cue" else W[pts[k][2]]
        return w * np.where(e < 0, W["early"], 1.0) * e ** 2

    cost, back = err(0), []
    for k in range(1, len(pts)):
        G = (pts[k][0] + offs)[None, :] - (pts[k - 1][0] + offs)[:, None]
        tot = cost[:, None] + seg_cost(stats[k - 1], G, lo, hi)
        b = np.argmin(tot, 0)
        cost = tot[b, np.arange(len(offs))] + err(k)
        back.append(b)
    if not np.isfinite(cost.min()):
        return None
    idx = [int(np.argmin(cost))]
    for b in reversed(back):
        idx.append(int(b[idx[-1]]))
    idx = idx[::-1]
    return [float(pts[k][0] + offs[idx[k]]) for k in range(len(pts))]


def time_map(seg, g, d, words_o, words):
    """Guide window g, take d, the line's word onsets in guide frames -> knots (o, t) in frames, the gain envelope,
    and a report."""
    lg, ld = band_level(g), band_level(d)
    vg, vd = vad(lg), vad(ld)
    fwd, inv = dtw_maps(g, d, vg, vd)
    eg = np.maximum(lg - np.percentile(lg, 95), -40)
    ed = np.maximum(ld - np.percentile(ld, 95), -40)
    n, m = len(fwd), len(inv)
    gis = [s for s, e in islands(vg[:n]) if min(abs(s - w) for w in words_o) <= 25]   # onsets of real words
    tis = islands(vd[:m])
    lo, hi = RATE[seg["kind"]]
    # anchors: the guide's onsets after pauses, plus word onsets at least WORD_GAP apart, placed in the take
    anchors = [(s, "onset") for s in gis]
    cue = [o for o, w in zip(words_o, words) if norm(w) in CUES.get(seg["id"], "").lower().split()]
    for w in sorted(words_o, key=lambda x: x not in cue):          # graphics cues first
        if all(abs(w - o) >= WORD_GAP for o, _ in anchors) and vg[w:w + 10].any():
            anchors.append((w, "word"))
    anchors.sort()
    pts = []
    for o, kind in anchors:
        t = refine(o, fwd[min(o, n - 1)], eg, ed)
        if pts and (t <= pts[-1][1] + 3 or o <= pts[-1][0] + 3):
            continue
        w = words[int(np.argmin([abs(o - x) for x in words_o]))]
        if norm(w) in CUES.get(seg["id"], "").lower().split() and abs(o - words_o[words.index(w)]) <= 10:
            kind = "cue"
        pts.append((o, t, kind))
    # the take's speech starts at the first anchor; drop whatever comes before (lead-in noise, stray sounds)
    tis = [(max(s, int(pts[0][1])), e) for s, e in tis if e > pts[0][1]]
    last_end = max(e for s, e in tis if s <= fwd[min(words_o[-1], n - 1)] + 30)
    # a split belongs before the onset that follows the original's pause: that anchor starts after it
    vs = virtual_splits(islands(vg[:n]), tis, fwd, ld)
    splits = []
    for v, s1 in vs:
        k = next((k for k, p in enumerate(pts) if abs(p[0] - s1) <= 3), None)
        if k is None:
            continue
        if pts[k][1] <= v:
            pts[k] = (pts[k][0], float(v + 2), pts[k][2])
        if (k == 0 or pts[k - 1][1] < v) and (k + 1 == len(pts) or pts[k + 1][1] > v + 2):
            splits.append(v)
    stats = [seg_stats(runs_between(tis, int(round(pts[k][1])), int(round(pts[k + 1][1])), splits))
             for k in range(len(pts) - 1)]
    place = place_anchors(pts, stats, seg["kind"], lo, hi)
    if place is None:                                   # nothing fits: widen the speed limits a little
        place = place_anchors(pts, stats, seg["kind"], lo * 0.9, hi * 1.1)
        lo, hi = lo * 0.9, hi * 1.1
    knots = [(place[0] - LEAD - 30, pts[0][1] - LEAD - 30), (place[0], pts[0][1])]
    report, dips = [], []
    O, T = place[0], float(pts[0][1])
    for k, (o, t, kind) in enumerate(pts):
        word = words[int(np.argmin([abs(o - w) for w in words_o]))]
        report.append(dict(word=word, kind=kind, target_ms=round(o * 10), off_ms=round((place[k] - o) * 10)))
        O, T = place[k], float(t)
        if k + 1 < len(pts):
            pieces, used, r = fit(runs_between(tis, int(round(t)), int(round(pts[k + 1][1])), splits),
                                  place[k + 1] - O, lo, hi)
        else:                                           # the last stretch: to the end of his last word
            seg_runs = runs_between(tis, int(round(t)), last_end)
            S = sum(e - s for s, e, kind in seg_runs)
            G_soft = inv[min(last_end, m - 1)] - O
            r = min(max(S / max(G_soft, 1e-9), END_RATE[0]), END_RATE[1])
            pieces = [(e - s, (e - s) / r, kind) for s, e, kind in seg_runs]
        report[-1]["speed"] = round(float(r), 3)
        for tl, gl, kind in pieces:
            if kind == "v" and gl >= 2:
                dips.append((O, gl))
                report[-1]["opened_pause_ms"] = round(gl * 10)
            T, O = T + tl, O + gl
            knots.append((O, T))
    end_o, end_t = O, T
    knots.append((end_o + TAIL + 40, end_t + TAIL + 40))
    ko, kt = [knots[0][0]], [knots[0][1]]
    for o, t in knots[1:]:                              # strictly increasing guide times (jumps = splices)
        o = max(o, ko[-1] + 0.01)
        ko.append(o)
        kt.append(max(t, kt[-1]))
    gain = [(place[0] - LEAD - LEAD_RAMP, 0.0), (place[0] - LEAD, 1.0), (end_o + TAIL, 1.0),
            (end_o + TAIL + TAIL_RAMP, 0.0)]
    for o, gl in dips:                                  # silence in the opened pauses, with short fades
        gain += [(o - V_RAMP, 1.0), (o, 0.0), (o + gl, 0.0), (o + gl + V_RAMP, 1.0)]
    gain.sort()
    return np.array(ko), np.array(kt), gain, report, (fwd, vg, vd)


# ---------------- rendering ----------------
@numba.njit(cache=True)
def _wsola(x, starts, N, Hs, tol):
    K = len(starts)
    y = np.zeros(K * Hs + N)
    ws = np.zeros(K * Hs + N)
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / N)
    P = N + tol + Hs
    xp = np.zeros(len(x) + 2 * P + N)
    xp[P:P + len(x)] = x
    lo, hi = tol, len(xp) - N - tol - Hs - 1
    prev = -1
    for k in range(K):
        p = int(np.round(starts[k])) + P
        p = min(max(p, lo), hi)
        best = p
        if prev >= 0:
            nat = prev + Hs
            bestc = -1e300
            for dd in range(-tol, tol + 1):
                q = p + dd
                s, ee = 0.0, 1e-12
                for t in range(0, N, 2):
                    s += xp[q + t] * xp[nat + t]
                    ee += xp[q + t] * xp[q + t]
                c = s / np.sqrt(ee)
                if c > bestc:
                    bestc, best = c, q
        for t in range(N):
            y[k * Hs + t] += w[t] * xp[best + t]
            ws[k * Hs + t] += w[t]
        prev = best
    for t in range(len(y)):
        if ws[t] > 1e-6:
            y[t] /= max(ws[t], 0.5)
    return y


def render(d, ko, kt, gain, n_out):
    """The take `d` on the guide's timeline (n_out samples) along the knots (guide frame -> take frame)."""
    K = int(np.ceil(n_out / HS)) + 1
    centres = np.arange(K) * HS + N_WIN / 2
    ko = np.concatenate([[ko[0] - 1e4], ko, [ko[-1] + 1e4]])          # 1:1 beyond the knots
    kt = np.concatenate([[kt[0] - 1e4], kt, [kt[-1] + 1e4]])
    src = np.interp(centres / HOP, ko, kt) * HOP
    y = _wsola(d, src - N_WIN / 2, N_WIN, HS, TOL)[:n_out]
    go, gv = zip(*gain)
    return y * np.interp(np.arange(n_out) / HOP, go, gv)


def line_words(seg):
    import karaoke_timing as KT
    a, _ = window(seg)
    ln = next(ln for ln in KT.lines() if ln["id"] == seg["id"])
    return [int(round((w["s"] + seg["offset"] - a) * 100)) for w in ln["words"]], [w["w"] for w in ln["words"]]


def align_line(seg, take, guide):
    """-> (the take on the line's source window, report, extras)."""
    a, b = window(seg)
    g = guide[int(round(a * SR)):int(round(b * SR))]
    words_o, words = line_words(seg)
    ko, kt, gain, report, extra = time_map(seg, g, take, words_o, words)
    y = render(take, ko, kt, gain, len(g))
    rate = np.diff(kt) / np.diff(ko)
    dur = np.diff(ko)
    vd = extra[2]
    # the speed of his speech wherever it plays (knot segments that cover take speech frames)
    sp = np.array([vd[min(int(t), len(vd) - 1)] for t in kt[:-1]])
    talk = sp & (dur > 0.5) & (np.diff(kt) > 0.05)
    w_rates = rate[talk]
    w_dur = dur[talk]
    rep = dict(id=seg["id"], kind=seg["kind"], window=[round(a, 3), round(b, 3)], anchors=report,
               speech_speed_range=[round(float(w_rates.min()), 3), round(float(w_rates.max()), 3)],
               speech_unchanged_pct=round(float(w_dur[np.abs(w_rates - 1) < 0.005].sum() / w_dur.sum() * 100), 1))
    return y, rep, (g, ko, kt, gain, words_o, words, extra)


def plot(seg, y, extras, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g, ko, kt, gain, words_o, words, (fwd, vg, vd) = extras
    a, _ = window(seg)
    eg, ey = band_level(g), band_level(y)
    tt = a - seg["offset"] + np.arange(len(eg)) / 100
    fig, ax = plt.subplots(figsize=(16, 4.2))
    ax.plot(tt, eg - np.percentile(eg, 95), lw=1.0, color="#1f5fbf", label="original (guide)")
    ax.plot(tt[:len(ey)], ey - np.percentile(ey, 95), lw=1.0, color="#d08000", label="new take, fitted")
    for o, w in zip(words_o, words):
        ax.axvline(a - seg["offset"] + o / 100, color="#999", lw=0.6)
        ax.text(a - seg["offset"] + o / 100, 3, w, fontsize=7, rotation=45)
    ax.set_ylim(-50, 12)
    ax.set_xlabel("reel time (s)")
    ax.set_ylabel("speech band, dB re p95")
    ax.set_title(f"{seg['id']}: original vs the re-recorded take after fitting")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def main():
    paths = take_paths()
    if not paths:
        sys.exit(f"need {len(edl.SEGMENTS)} takes at {TAKES}")
    os.makedirs(OUT, exist_ok=True)
    guide = guide_track()
    reports = []
    for seg, p in zip(edl.SEGMENTS, paths):
        take = load_mono(p)
        y, rep, extras = align_line(seg, take, guide)
        rep["take"] = os.path.basename(p)
        sf.write(os.path.join(OUT, f"{seg['id']}.wav"), y.astype(np.float32), SR, subtype="FLOAT")
        if "--plots" in sys.argv:
            os.makedirs(os.path.join(edl.ROOT, "renders/verify"), exist_ok=True)
            plot(seg, y, extras, os.path.join(edl.ROOT, f"renders/verify/adr_{seg['id']}.png"))
        reports.append(rep)
        print(f"{seg['id']} ({seg['kind']}) {rep['take']}: speech speed {rep['speech_speed_range']}, untouched "
              f"{rep['speech_unchanged_pct']}%; anchors (word, ms off: + late / - early):")
        print("    " + "  ".join(f"{r['word']}{dict(onset='*', cue='!').get(r['kind'], '')} {r['off_ms']:+d}"
                                  + (f" [+{r['opened_pause_ms']} ms pause]" if r.get("opened_pause_ms") else "")
                                  for r in rep["anchors"]))
    json.dump(reports, open(os.path.join(OUT, "adr.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
