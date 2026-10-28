"""Jayashree D Jain event reel: the picture.

Each output frame: the shot's source frame (optical-flow interpolated in slow motion), the camera
(push, punch, whip, shake), the grade (look.py LUT), god rays, transitions (flash leaks, whips,
dissolves, the drop), golden dust, bloom and halation, vignette, the titles, grain.
  python3 tools/composite.py frame N OUT.jpg       # one frame (N = output frame number)
  python3 tools/composite.py sheet OUT.jpg N...    # a contact sheet of frames
  python3 tools/composite.py render [JOBS]         # the whole reel -> renders/video.mp4
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402
import fx  # noqa: E402
import look  # noqa: E402
import media  # noqa: E402
import titles as T  # noqa: E402

FPS, W, H = edl.FPS, edl.W, edl.H
SHOTS = edl.SHOTS
DISSOLVE = 1.0                   # s, the longest cross-dissolve (edl.DISSOLVES sets each one)
WHIP = 4 / FPS                   # each half of a whip pan
D, B, E = edl.DROP, edl.BASS, edl.END

# ---------------------------------------------------------------- the direction
# punches on cuts after the drop: (time, extra zoom, decay s)
PUNCH = [(s["t"], 0.06, 0.14) for s in SHOTS if s["t"] > D + 0.01 and s["x"] in ("cut", "whip", "flash")]
PUNCH.append((D, 0.12, 0.30))
# flashes of warm light at a cut: (time, peak, attack s, decay s, leak seed)
LEAKS = [(s["t"], 0.70, 0.10, 0.30, 100 + s["i"]) for s in SHOTS if s["x"] == "flash" and s["t"] < E - 0.01]
LEAKS += [(D, 0.8, 0.12, 0.30, 12), (E, 0.9, 0.10, 0.6, 13)]
# white flashes: (time, alpha, decay s)
WHITE = [(D, 0.80, 0.10), (B, 0.30, 0.08), (E, 0.50, 0.15)]
# shakes: (time, px, decay s, Hz)
SHAKE = [(D, 20, 0.30, 15), (B, 10, 0.20, 16), (E, 8, 0.25, 13)]
# zoom-blur bursts and chromatic kicks: (time, amount, decay s)
ZBLUR = [(D, 0.10, 0.16), (B, 0.05, 0.12)]
CHROMA = [(D, 9, 0.14), (B, 5, 0.12), (E, 5, 0.14)]
# a subtle exposure pulse on the song's accents (bar + 0, 1.5, 3 pulses) through the montage
PULSE = [(D + (4 * k + a) * edl.PULSE, 0.035) for k in range(0, 20) for a in edl.ACCENTS]
PULSE = [(t, v) for t, v in PULSE if D <= t < E - 0.01]
# golden dust: (time, level) keyframes, linear between
DUST = [(0.0, 0.9), (D - 0.2, 0.9), (D + 0.3, 0.3), (E - 0.1, 0.3), (E + 0.4, 1.0), (99, 1.0)]
# a slow drifting leak through the end card: (t0, t1, level, seed)
DRIFT = [(E, edl.DURATION + 1, 0.20, 22)]


def env(t, t0, attack, decay):
    if t < t0 - attack or t > t0 + decay * 6:
        return 0.0
    if t < t0:
        return ((t - (t0 - attack)) / attack) ** 2 if attack > 0 else 0.0
    return math.exp(-(t - t0) / decay)


def interp_keys(keys, t):
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
    return keys[-1][1]


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- source frames
class Reader:
    """Frames of one clip in order from a start time: the 1080x1920 proxy, or the 4K original (hires)."""

    def __init__(self, clip, t0, hires=False):
        self.clip, self.hires = clip, hires
        n = edl_stats(clip)
        self.count = n
        self.i0 = max(0, min(n - 1, int(math.floor(t0 * FPS)) - 1))
        if hires:
            name = [c for c in media.clips() if c.startswith(f"IMG_{clip}.")][0]
            path = os.path.join(media.SRC, name)
            self.w, self.h = 2160, 3840
            vf = media.vf(name, f"scale={self.w}:{self.h}")
        else:
            path = os.path.join(edl.ROOT, f"renders/proxy/IMG_{clip}.mp4")
            self.w, self.h = W, H
            vf = "null"
        ss = max(0.0, (self.i0 - 0.5) / FPS)
        self.p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-threads", "4" if hires else "2", "-ss", f"{ss:.4f}",
                                   "-i", path, "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, bufsize=self.w * self.h * 3 * 2)
        self.next = self.i0
        self.buf = {}
        self.flow = {}

    def get(self, i):
        i = max(self.i0, min(self.count - 1, i))
        size = self.w * self.h * 3
        while self.next <= i:
            raw = self.p.stdout.read(size)
            if len(raw) < size:                       # past the end: hold the last frame
                self.count = self.next
                return self.buf[max(self.buf)]
            self.buf[self.next] = np.frombuffer(raw, np.uint8).reshape(self.h, self.w, 3)
            self.next += 1
            for k in [k for k in self.buf if k < self.next - 4]:
                del self.buf[k]
        return self.buf[i] if i in self.buf else self.buf[min(self.buf)]

    def at(self, st, interpolate):
        f = st * FPS
        if not interpolate:
            return self.get(int(round(f)))
        i = int(math.floor(f))
        a = f - i
        if a < 0.04:
            return self.get(i)
        if a > 0.96:
            return self.get(i + 1)
        f0, f1 = self.get(i), self.get(i + 1)
        if i not in self.flow:
            self.flow = {i: flows(f0, f1, self.w, self.h)}
        fw, bw = self.flow[i]
        gx, gy = grid(self.w, self.h)
        w0 = cv2.remap(f0, gx - a * fw[..., 0], gy - a * fw[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        w1 = cv2.remap(f1, gx - (1 - a) * bw[..., 0], gy - (1 - a) * bw[..., 1], cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
        return cv2.addWeighted(w0, 1 - a, w1, a, 0)

    def close(self):
        try:
            self.p.stdout.close()
            self.p.kill()
            self.p.wait()
        except Exception:
            pass


_stats = None


def edl_stats(clip):
    global _stats
    if _stats is None:
        import json
        _stats = json.load(open(os.path.join(edl.ROOT, "renders/analysis/clipstats.json")))
    return _stats[f"IMG_{clip}.mp4"]["n"]


_dis = None
_grids = {}


def grid(w, h):
    if (w, h) not in _grids:
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        _grids[(w, h)] = (gx, gy)
    return _grids[(w, h)]


def flows(f0, f1, w, h):
    """Forward and backward DIS optical flow, computed at 540x960 and scaled to (w, h)."""
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    g0 = cv2.cvtColor(cv2.resize(f0, (540, 960), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    g1 = cv2.cvtColor(cv2.resize(f1, (540, 960), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    k = w / 540
    fw = cv2.resize(_dis.calc(g0, g1, None), (w, h), interpolation=cv2.INTER_LINEAR) * k
    bw = cv2.resize(_dis.calc(g1, g0, None), (w, h), interpolation=cv2.INTER_LINEAR) * k
    return fw, bw


# ---------------------------------------------------------------- the frame
class Comp:
    def __init__(self):
        self.luts = {k: look.lut(k) for k in look.LOOKS}
        self.readers = {}
        self.dust = fx.Dust()
        self.titles = T.Titles()

    def reader(self, s, st):
        r = self.readers.get(s["i"])
        need = int(math.floor(st * FPS))
        if r is None or need < r.i0:
            if r is not None:
                r.close()
            r = Reader(s["clip"], st, s["hires"])
            self.readers[s["i"]] = r
        return r

    def release(self, t):
        for i in [i for i in self.readers if SHOTS[i]["end"] + DISSOLVE < t]:
            self.readers.pop(i).close()

    # ---- one shot's picture at reel time t (graded, camera applied), float RGB
    def shot(self, s, t, whip_dx=0.0):
        st = max(0.0, edl.src_time(s, t))
        r = self.reader(s, st)
        img = r.at(st, s["speed"] < 1 or s["ramp"])
        dur = s["end"] - s["t"]
        u = (t - s["t"]) / dur
        z0, z1 = s["z"]
        uc = min(max(u, 0.0), 1.0)
        z = z0 + (z1 - z0) * (uc ** 1.8 if s["ramp"] else smooth(u) * 0.35 + u * 0.65)
        for (tp, amp, dec) in PUNCH:
            if s["t"] - 1e-6 <= tp <= t and abs(tp - s["t"]) < 1e-3:
                z *= 1 + amp * math.exp(-(t - tp) / dec)
        dx = dy = rot = 0.0
        for (ts, px, dec, hz) in SHAKE:
            if ts <= t < ts + dec * 5:
                e = math.exp(-(t - ts) / dec)
                dx += px * e * math.sin(2 * math.pi * hz * (t - ts))
                dy += px * 0.7 * e * math.sin(2 * math.pi * hz * 1.3 * (t - ts) + 1.1)
                rot += 0.35 * e * math.sin(2 * math.pi * hz * 0.8 * (t - ts) + 0.4)
        dx += whip_dx
        sc = z * W / r.w                               # source px -> output px
        cx, cy = s["c"]
        half_w, half_h = W / (2 * sc), H / (2 * sc)
        wx = min(max(cx * r.w, half_w), r.w - half_w)
        wy = min(max(cy * r.h, half_h), r.h - half_h)
        m = np.float32([[sc, 0, W / 2 - sc * wx + dx], [0, sc, H / 2 - sc * wy + dy]])
        if abs(rot) > 0.01:
            rm = cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.0)
            m = (np.vstack([rm, [0, 0, 1]]) @ np.vstack([m, [0, 0, 1]]))[:2].astype(np.float32)
        out = cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR if sc < 1.01 else cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REFLECT)
        x = look.apply(out, self.luts[s["look"]]).astype(np.float32) / 255
        if s["rays"]:
            px, py, k = s["rays"]
            x = fx.god_rays(x, px, py, k)
        if abs(whip_dx) > 2:
            x = fx.whip_blur(x, min(380, abs(whip_dx) * 0.55))
        return x

    def frame(self, n):
        t = n / FPS
        cur = edl.shot_at(t)
        i = cur["i"]
        nxt = SHOTS[i + 1] if i + 1 < len(SHOTS) else None
        prv = SHOTS[i - 1] if i > 0 else None
        # ---- the picture, with whips and dissolves
        dn = edl.DISSOLVES.get(nxt["i"], 0.8) if nxt else 0.0
        dc = edl.DISSOLVES.get(cur["i"], 0.8)
        if nxt and nxt["x"] == "dissolve" and t >= nxt["t"] - dn / 2:
            w = smooth((t - (nxt["t"] - dn / 2)) / dn)
            x = self.shot(cur, t) * (1 - w) + self.shot(nxt, t) * w
        elif cur["x"] == "dissolve" and prv and t < cur["t"] + dc / 2:
            w = smooth((t - (cur["t"] - dc / 2)) / dc)
            x = self.shot(prv, t) * (1 - w) + self.shot(cur, t) * w
        elif nxt and nxt["x"] == "whip" and t >= nxt["t"] - WHIP:
            u = (t - (nxt["t"] - WHIP)) / WHIP
            d = -1 if nxt["i"] % 2 else 1
            x = self.shot(cur, t, whip_dx=d * W * 0.85 * u ** 2)
        elif cur["x"] == "whip" and t < cur["t"] + WHIP:
            u = (t - cur["t"]) / WHIP
            d = -1 if cur["i"] % 2 else 1
            x = self.shot(cur, t, whip_dx=-d * W * 0.85 * (1 - u) ** 2)
        else:
            x = self.shot(cur, t)
        # ---- light
        x = look.clarity(x, 0.20)
        x = look.bloom(x, 0.32 if cur["look"] == "candle" else 0.26)
        x = look.halation(x, 0.16)
        pulse = sum(a * math.exp(-(t - b) / 0.14) for b, a in PULSE if b <= t < b + 0.6)
        if pulse:
            x = np.clip(x * (1 + pulse), 0, 1)
        dust = interp_keys(DUST, t)
        x = x + self.dust.layer(t, dust) * 0.85
        for (t0, t1, lvl, seed) in DRIFT:
            if t0 <= t < t1:
                fade = smooth((t - t0) / 1.0) * smooth((t1 - t) / 0.6)
                lk = fx.leak((t - t0) * 0.35, seed, lvl * fade, drift=0.5)
                if lk is not None:
                    x = fx.screen(x, lk)
        for (tl, peak, att, dec, seed) in LEAKS:
            e = env(t, tl, att, dec)
            if e > 0.01:
                x = fx.screen(x, fx.leak(t - tl + 0.5, seed, peak * e))
                x = x * (1 + 0.18 * e)
        for (tw, a, dec) in WHITE:
            if tw <= t < tw + dec * 6:
                e = a * math.exp(-(t - tw) / dec)
                x = x + (np.array([1.0, 0.95, 0.85], np.float32) - x) * e
        for (tz, amt, dec) in ZBLUR:
            if tz <= t < tz + dec * 4:
                x = fx.zoom_blur(x, amt * math.exp(-(t - tz) / dec))
        for (tc, px, dec) in CHROMA:
            if tc <= t < tc + dec * 4:
                x = fx.chroma(x, px * math.exp(-(t - tc) / dec))
        x = np.clip(x, 0, 1)
        x = look.vignette(x, 0.36)
        # ---- type, then grain over everything
        x = self.titles.draw(x, t, edl.TEXT)
        x = look.grain(x, 1000 + n, 0.022)
        self.release(t)
        return x


def to8(x):
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_range(a, b, out):
    cv2.setNumThreads(1)                              # one core per worker: the workers are the parallelism
    c = Comp()
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "11",
                            "-threads", "2", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709",
                            "-color_primaries", "bt709", "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    for n in range(a, b):
        enc.stdin.write(to8(c.frame(n)).tobytes())
        if (n - a) % 60 == 0:
            print(f"[{os.getpid()}] {n}/{b}", flush=True)
    enc.stdin.close()
    enc.wait()


def main():
    cmd = sys.argv[1]
    if cmd == "frame":
        c = Comp()
        n = int(sys.argv[2])
        cv2.imwrite(sys.argv[3], cv2.cvtColor(to8(c.frame(n)), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    elif cmd == "sheet":
        c = Comp()
        ims = []
        for a in sys.argv[3:]:
            n = int(a)
            im = cv2.resize(to8(c.frame(n)), (360, 640), interpolation=cv2.INTER_AREA)
            cv2.putText(im, f"{n} {n / FPS:.2f}s", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1,
                        cv2.LINE_AA)
            ims.append(im)
        cols = int(os.environ.get("COLS", 4))
        while len(ims) % cols:
            ims.append(np.zeros_like(ims[0]))
        sheet = np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)])
        cv2.imwrite(sys.argv[2], cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    elif cmd == "render":
        jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        parts = os.path.join(edl.ROOT, "renders/parts")
        os.makedirs(parts, exist_ok=True)
        cuts = [round(edl.TOTAL * k / jobs) for k in range(jobs + 1)]
        procs = []
        envv = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        for k in range(jobs):
            out = os.path.join(parts, f"part{k}.mp4")
            procs.append(subprocess.Popen([sys.executable, __file__, "range", str(cuts[k]), str(cuts[k + 1]), out],
                                          env=envv))
        codes = [p.wait() for p in procs]
        if any(codes):
            sys.exit(f"a render worker failed: {codes}")
        lst = os.path.join(parts, "list.txt")
        with open(lst, "w") as f:
            for k in range(jobs):
                f.write(f"file 'part{k}.mp4'\n")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        os.path.join(edl.ROOT, "renders/video.mp4")], check=True)
        print("renders/video.mp4")
    elif cmd == "range":
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])


if __name__ == "__main__":
    main()
