"""Measure a reference edit frame by frame and its soundtrack beat by beat, so its cutting, effects
and music sync can be described in numbers instead of by eye.

  python3 tools/analyze_ref.py renders/ref/reference.mp4 renders/analysis

Writes into the output dir:
  frames.json   per frame: luma, contrast, saturation, sharpness, cut score, letterbox rows,
                global motion (zoom / rotation / pan fitted to dense optical flow), residual (subject)
                motion, R-vs-B channel offset (RGB split), mean colour of shadows / mids / highlights
  audio.json    tempo, beat times, onset times, band energies at 100 Hz, RMS
"""
import json
import os
import sys

import cv2
import numpy as np


def letterbox(gray, thresh=18):
    """Rows of black bar at the top and bottom (a row counts as bar when 98% of it is near black)."""
    dark = (gray < thresh).mean(axis=1) > 0.98
    top = 0
    while top < len(dark) and dark[top]:
        top += 1
    bot = 0
    while bot < len(dark) and dark[len(dark) - 1 - bot]:
        bot += 1
    return top, bot


def fit_similarity(flow, mask=None):
    """Global camera motion from a dense flow field: u = a*x - b*y + tx, v = b*x + a*y + ty
    (x, y centred, in pixels). Robust: two passes, the second drops the worst 40% (the subject)."""
    h, w = flow.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    xs -= w / 2
    ys -= h / 2
    sel = np.ones((h, w), bool) if mask is None else mask
    x, y = xs[sel], ys[sel]
    u, v = flow[..., 0][sel].astype(np.float64), flow[..., 1][sel].astype(np.float64)
    keep = np.ones(len(x), bool)
    for _ in range(2):
        A = np.zeros((2 * keep.sum(), 4))
        A[0::2, 0], A[0::2, 1], A[0::2, 2] = x[keep], -y[keep], 1
        A[1::2, 0], A[1::2, 1], A[1::2, 3] = y[keep], x[keep], 1
        rhs = np.empty(2 * keep.sum())
        rhs[0::2], rhs[1::2] = u[keep], v[keep]
        p, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        ru = u - (p[0] * x - p[1] * y + p[2])
        rv = v - (p[1] * x + p[0] * y + p[3])
        r = np.hypot(ru, rv)
        keep = r <= np.quantile(r, 0.6)
    return p, float(np.median(r)), float(np.quantile(r, 0.9))


def rb_offset(img):
    """Shift of the red channel against the blue (phase correlation), px: an RGB-split detector."""
    r = img[..., 2].astype(np.float32)
    b = img[..., 0].astype(np.float32)
    win = cv2.createHanningWindow(r.shape[::-1], cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(b, r, win)
    return float(dx), float(dy), float(resp)


def video_metrics(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    out, prev_small, prev_hist = [], None, None
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        top, bot = letterbox(gray)
        H = gray.shape[0]
        act = slice(top, H - bot) if top + bot < H - 8 else slice(0, H)
        g = gray[act]
        frc = fr[act]
        hsv = cv2.cvtColor(frc, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(frc, cv2.COLOR_BGR2LAB).astype(np.float32)
        L = lab[..., 0] * 100 / 255
        tones = {}
        for name, lo, hi in (("shadows", 0, 25), ("mids", 35, 65), ("highs", 75, 101)):
            m = (L >= lo) & (L < hi)
            tones[name] = [round(float(lab[..., 1][m].mean() - 128), 2), round(float(lab[..., 2][m].mean() - 128), 2),
                           round(float(m.mean()), 3)] if m.sum() > 50 else None
        small = cv2.resize(g, (int(g.shape[1] * 240 / g.shape[0]) if g.shape[0] < g.shape[1] else 240,
                               240 if g.shape[0] < g.shape[1] else int(g.shape[0] * 240 / g.shape[1])),
                           interpolation=cv2.INTER_AREA)
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        rec = dict(f=i, t=round(i / fps, 4), luma=round(float(g.mean()), 2), contrast=round(float(g.std()), 2),
                   sat=round(float(hsv[..., 1].mean()), 2), sharp=round(float(cv2.Laplacian(g, cv2.CV_64F).var()), 1),
                   bars=[top, bot], tones=tones, p01=int(np.percentile(g, 1)), p99=int(np.percentile(g, 99)))
        dx, dy, resp = rb_offset(frc)
        rec["rb"] = [round(dx, 2), round(dy, 2), round(resp, 3)]
        if prev_small is not None and prev_small.shape == small.shape:
            rec["diff"] = round(float(np.abs(small.astype(np.int16) - prev_small.astype(np.int16)).mean()), 2)
            rec["hist"] = round(float(1 - cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)), 4)
            flow = dis.calc(prev_small, small, None)
            p, med, q90 = fit_similarity(flow)
            sc = 240 / g.shape[0] if g.shape[0] < g.shape[1] else 240 / g.shape[1]
            rec["zoom"] = round(float(p[0]), 5)          # per-frame scale change (+ = zooming in)
            rec["rot"] = round(float(np.degrees(p[1])), 4)
            rec["pan"] = [round(float(p[2] / sc), 2), round(float(p[3] / sc), 2)]   # px of the source frame
            rec["local"] = [round(med / sc, 2), round(q90 / sc, 2)]
            rec["flow"] = round(float(np.hypot(flow[..., 0], flow[..., 1]).mean() / sc), 2)
        else:
            rec.update(diff=None, hist=None)
        out.append(rec)
        prev_small, prev_hist = small, hist
        i += 1
    return fps, out


def audio_metrics(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = 220                                    # ~100 Hz frames
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, units="time")
    onsets = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, units="time", backtrack=False)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    bands = {"sub": (20, 60), "bass": (60, 160), "lowmid": (160, 600), "mid": (600, 2500), "high": (2500, 6000), "air": (6000, 11025)}
    be = {k: (10 * np.log10(S[(freqs >= lo) & (freqs < hi)].sum(axis=0) + 1e-10)).round(2).tolist() for k, (lo, hi) in bands.items()}
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    flat = librosa.feature.spectral_flatness(S=S)[0]
    cent = librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr)[0]
    return dict(sr=sr, hop=hop, tempo=float(np.atleast_1d(tempo)[0]), beats=[round(float(b), 3) for b in beats],
                onsets=[round(float(o), 3) for o in onsets], onset_env=np.round(oenv, 3).tolist(),
                bands=be, rms_db=(20 * np.log10(rms + 1e-9)).round(2).tolist(), flatness=np.round(flat, 4).tolist(),
                centroid=np.round(cent, 1).tolist())


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    fps, frames = video_metrics(src)
    json.dump(dict(fps=fps, frames=frames), open(os.path.join(outdir, "frames.json"), "w"))
    wav = os.path.join(outdir, "audio.wav")
    if not os.path.exists(wav):
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "2", "-ar", "44100", wav], check=True)
    json.dump(audio_metrics(wav), open(os.path.join(outdir, "audio.json"), "w"))
    print(f"{len(frames)} frames at {fps} fps -> {outdir}")


if __name__ == "__main__":
    main()
