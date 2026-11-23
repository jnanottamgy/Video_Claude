"""Measure the inspiration reels: cuts, camera motion, speed, flashes, grade, letterbox, beats and sound hits.

  python3 tools/analyze_inspo.py renders/src/inspo/r1.mp4 [...]  ->  renders/analysis/<name>.json + a printed report

Per frame (on a 256-px-wide copy):
- the cut score (colour-histogram distance to the previous frame), with a threshold relative to the reel;
- global camera motion from dense optical flow: pan (dx, dy, px/frame at 256 px), zoom (radial divergence) and
  roll, so push-ins, pull-outs, whips and speed ramps show up;
- the luma mean, contrast (std), saturation, warmth (R-B) and black bars.
Audio: the beat grid (librosa), onsets with their band (sub < 150 Hz, mid, air > 5 kHz), loud transient hits,
and silences (where an edit cuts the music for impact).
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

W = 256


def frames(path):
    w, h, fps = probe(path)
    hh = int(round(h * W / w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{hh}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (W * hh * 3)
    fr = np.frombuffer(raw[:n * W * hh * 3], np.uint8).reshape(n, hh, W, 3)
    # the picture area: rows/columns that are ever brighter than letterbox black (titles in the bars are ignored by
    # needing 20% of the frames to light them)
    lit = fr.max(axis=3) > 24
    rows = np.nonzero((lit.mean(axis=2) > 0.02).mean(0) > 0.2)[0]
    cols = np.nonzero((lit.mean(axis=1) > 0.02).mean(0) > 0.2)[0]
    y0, y1 = (rows[0], rows[-1] + 1) if len(rows) else (0, hh)
    x0, x1 = (cols[0], cols[-1] + 1) if len(cols) else (0, W)
    return np.ascontiguousarray(fr[:, y0:y1, x0:x1]), fps, (w, h), (int(x0), int(y0), int(x1), int(y1), W, hh)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True,
                         check=True).stdout.strip().split(",")
    a, b = out[2].split("/")
    return int(out[0]), int(out[1]), float(a) / float(b)


def bars(img):
    """Rows of near-black letterbox at the top and bottom (fraction of the height)."""
    rowmax = img.max(axis=(1, 2))
    h = len(rowmax)
    top = 0
    while top < h // 2 and rowmax[top] < 18:
        top += 1
    bot = 0
    while bot < h // 2 and rowmax[h - 1 - bot] < 18:
        bot += 1
    return top / h, bot / h


def motion(prev, cur):
    g0 = cv2.cvtColor(prev, cv2.COLOR_RGB2GRAY)
    g1 = cv2.cvtColor(cur, cv2.COLOR_RGB2GRAY)
    f = cv2.calcOpticalFlowFarneback(g0, g1, None, 0.5, 3, 21, 3, 5, 1.1, 0)
    h, w = g0.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2, (h - 1) / 2
    rx, ry = xx - cx, yy - cy
    m = np.ones((h, w), bool)
    m[: h // 12] = m[-h // 12:] = False                       # ignore edges (text, bars)
    dx, dy = f[..., 0], f[..., 1]
    tx, ty = float(np.median(dx[m])), float(np.median(dy[m]))
    ex, ey = dx - tx, dy - ty
    r2 = rx ** 2 + ry ** 2 + 1e-6
    zoom = float(np.median(((ex * rx + ey * ry) / r2)[m & (r2 > 400)]))       # per-frame scale change
    roll = float(np.median(((ey * rx - ex * ry) / r2)[m & (r2 > 400)]))
    mag = float(np.median(np.hypot(dx, dy)[m]))
    resid = float(np.median(np.hypot(ex - zoom * rx, ey - zoom * ry)[m]))       # subject / parallax motion
    return tx, ty, zoom, roll, mag, resid


def hist(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    h = cv2.calcHist([hsv], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(h, h).flatten()


def video_metrics(path):
    fr, fps, (w, h), box = frames(path)
    n = len(fr)
    rows = []
    hp = hist(fr[0])
    for i in range(n):
        img = fr[i]
        hc = hist(img)
        cut = float(cv2.compareHist(hp, hc, cv2.HISTCMP_BHATTACHARYYA)) if i else 0.0
        hp = hc
        f = img.astype(np.float32) / 255
        L = f.mean(2)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        mo = motion(fr[i - 1], img) if i else (0, 0, 0, 0, 0, 0)
        tb = bars(img)
        rows.append(dict(t=round(i / fps, 3), cut=round(cut, 3), luma=round(float(L.mean()), 3),
                         contrast=round(float(L.std()), 3), sat=round(float(hsv[..., 1].mean() / 255), 3),
                         warm=round(float((f[..., 0] - f[..., 2]).mean()), 3), bars=[round(tb[0], 3), round(tb[1], 3)],
                         dx=round(mo[0], 2), dy=round(mo[1], 2), zoom=round(mo[2] * 1000, 2), roll=round(mo[3] * 1000, 2),
                         mag=round(mo[4], 2), resid=round(mo[5], 2)))
    # cuts: a histogram jump well above the reel's typical frame-to-frame change, or a big flow failure
    c = np.array([r["cut"] for r in rows])
    thr = max(0.28, float(np.median(c) + 6 * np.median(np.abs(c - np.median(c)))))
    cuts = [i for i in range(1, n) if c[i] > thr and c[i] >= c[max(0, i - 1)] and c[i] >= c[min(n - 1, i + 1)]]
    # flashes: luma well above both neighbours' level
    lum = np.array([r["luma"] for r in rows])
    flashes = [i for i in range(2, n - 2) if lum[i] > 0.6 and lum[i] - min(lum[i - 2], lum[i + 2]) > 0.18]
    return dict(fps=fps, size=[w, h], box=box, n=n, rows=rows, cuts=cuts, cut_thr=round(thr, 3), flashes=flashes)


def audio_metrics(path):
    import librosa
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "22050", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32).astype(np.float32)
    sr = 22050
    if len(y) < sr:
        return {}
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
    band = lambda lo, hi: librosa.amplitude_to_db(S[(f >= lo) & (f < hi)].mean(0) + 1e-9)
    sub, mid, air = band(20, 150), band(150, 5000), band(5000, 11000)
    rms = librosa.amplitude_to_db(librosa.feature.rms(S=S)[0] + 1e-9)
    on = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S), sr=sr)
    peaks = librosa.util.peak_pick(on, pre_max=6, post_max=6, pre_avg=12, post_avg=12, delta=on.std() * 1.2, wait=6)
    hits = []
    for p in peaks:
        a, b = max(0, p - 4), p
        d = lambda x: float(x[p:p + 3].max() - x[a:b + 1].min()) if b > a else 0.0
        jumps = dict(sub=d(sub), mid=d(mid), air=d(air))
        hits.append(dict(t=round(float(t[p]), 2), strength=round(float(on[p] / on.max()), 2),
                         band=max(jumps, key=jumps.get), rise_db={k: round(v, 1) for k, v in jumps.items()}))
    # silences / drop-outs: rms 18 dB under the reel's median for >= 0.15 s
    med = float(np.median(rms))
    quiet = rms < med - 18
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if t[min(j, len(t) - 1)] - t[i] >= 0.15:
                gaps.append([round(float(t[i]), 2), round(float(t[min(j, len(t) - 1)]), 2)])
            i = j
        else:
            i += 1
    # a 4-per-second loudness curve
    k = int(sr / 512 / 4)
    curve = [round(float(rms[i:i + k].mean()), 1) for i in range(0, len(rms), k)]
    return dict(tempo=round(float(np.atleast_1d(tempo)[0]), 1), beats=[round(float(b), 2) for b in beats], hits=hits,
                silences=gaps, rms_4hz=curve, rms_median=round(med, 1))


def report(name, v, a):
    rows = v["rows"]
    fps = v["fps"]
    print(f"\n===== {name}: {v['size'][0]}x{v['size'][1]} {fps:g} fps, {v['n'] / fps:.2f} s, cut threshold {v['cut_thr']}")
    cuts = [0] + v["cuts"] + [v["n"]]
    print(f"picture area (x0,y0,x1,y1 of {v['box'][4]}x{v['box'][5]}): {v['box'][:4]}")
    print(f"{len(v['cuts'])} cuts, average shot {v['n'] / fps / (len(v['cuts']) + 1):.2f} s")
    for s, e in zip(cuts, cuts[1:]):
        seg = rows[s + 1:e] or rows[s:e]
        dx = np.array([r["dx"] for r in seg]); dy = np.array([r["dy"] for r in seg])
        z = np.array([r["zoom"] for r in seg]); mag = np.array([r["mag"] for r in seg])
        ro = np.array([r["roll"] for r in seg]); res = np.array([r["resid"] for r in seg])
        lum = np.mean([r["luma"] for r in rows[s:e]]); sat = np.mean([r["sat"] for r in rows[s:e]])
        warm = np.mean([r["warm"] for r in rows[s:e]]); bt = rows[s]["bars"]
        # speed profile: thirds of the shot
        th = np.array_split(mag, 3) if len(mag) >= 3 else [mag]
        prof = "/".join(f"{x.mean():.1f}" for x in th)
        print(f"  {s / fps:6.2f}-{e / fps:6.2f} ({(e - s) / fps:4.2f}s)  pan {dx.sum():+6.0f},{dy.sum():+6.0f}px  "
              f"zoom {z.sum():+6.0f}‰  roll {ro.sum():+5.0f}‰  speed(px/f) {prof}  subj {res.mean():.2f}  "
              f"luma {lum:.2f} sat {sat:.2f} warm {warm:+.3f} bars {bt}")
    if v["flashes"]:
        print("  flashes at", [round(i / fps, 2) for i in v["flashes"]])
    if a:
        print(f"  audio: tempo ~{a['tempo']} BPM, {len(a['beats'])} beats; silences {a['silences']}")
        print("  hits:", "  ".join(f"{h['t']:.2f}({h['band']},{h['strength']:.2f})" for h in a["hits"] if h["strength"] > 0.25))
        cut_t = [c / fps for c in v["cuts"]]
        if a["beats"] and cut_t:
            b = np.array(a["beats"])
            hb = np.array([h["t"] for h in a["hits"]]) if a["hits"] else b
            on_beat = np.mean([np.min(np.abs(b - c)) < 0.07 for c in cut_t])
            on_hit = np.mean([np.min(np.abs(hb - c)) < 0.07 for c in cut_t])
            print(f"  cuts within 70 ms of a beat: {on_beat:.0%}, of an audio hit: {on_hit:.0%}")


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "renders/analysis")
    os.makedirs(out_dir, exist_ok=True)
    for p in sys.argv[1:]:
        name = os.path.splitext(os.path.basename(p))[0]
        v = video_metrics(p)
        a = audio_metrics(p)
        json.dump(dict(video=v, audio=a), open(os.path.join(out_dir, f"{name}.json"), "w"))
        report(name, v, a)


if __name__ == "__main__":
    main()
