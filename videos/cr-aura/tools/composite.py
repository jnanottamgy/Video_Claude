"""The CR aura edit compositor: EDL -> frames -> effects -> titles -> captions (last) -> H.264.

  python3 tools/composite.py [--preview] [--range t0-t1] [--out renders/cr_aura_video.mp4] [--still t]

Frames come from the Real-ESRGAN pass (renders/src/enhanced.mp4) when it exists, else the source
upscaled with Lanczos (development). --preview renders at 540x960 for quick looks.
"""
import argparse
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402
import fx  # noqa: E402
import titles as TT  # noqa: E402

SRC = "renders/src/source.mp4"
ENH = "renders/src/enhanced.mp4"
MATTES = "renders/mattes"
FPS = edl.FPS
BARS = 0.072                    # letterbox bar height (each) as a fraction of frame height
GOLD_GLOW = (1.0, 0.80, 0.40)

# where the CR is (fractions of the frame) for the effects that need one person: blob seeds,
# zoom centres, title anchors
FACE = {"stare": (0.58, 0.40), "turn": (0.47, 0.30), "pose": (0.37, 0.55), "phone": (0.5, 0.30),
        "typing": (0.42, 0.30), "smile": (0.44, 0.30), "thumb": (0.5, 0.35), "smirk": (0.5, 0.36),
        "close": (0.46, 0.38), "wave": (0.45, 0.45), "walkoff": (0.5, 0.55), "turnback": (0.62, 0.62),
        "endcard": (0.62, 0.62)}


def need_frames():
    """Every source frame the EDL touches (with neighbours for interpolation)."""
    out = set()
    n = edl.frame_count()
    for i in range(n):
        t = i / FPS
        s = edl.segment_at(t)
        f = edl.src_frame(s, t)
        out.update({int(np.floor(f)), int(np.ceil(f))})
    # the double exposure fills and the strobe source
    for a, b in DBL_FILLS:
        out.update(range(a, a + 12))
    out.update({521, 561, 922})
    return sorted(x for x in out if 0 <= x < 926)


# the six clips seen inside the double-exposure silhouette, one per eighth note
DBL_FILLS = [(826, 0), (845, 0), (868, 0), (880, 0), (892, 0), (905, 0)]


class Frames:
    """Source frames as float32 RGB at the output size, loaded once (only the ones the edit uses)."""

    def __init__(self, w, h, frames):
        self.w, self.h = w, h
        src = ENH if os.path.exists(ENH) and os.path.getsize(ENH) > 10_000_000 and _complete(ENH) else SRC
        self.enhanced = src == ENH
        sw, sh = (1080, 1920) if src == ENH else (576, 1024)
        want = set(frames)
        self.cache = {}
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             stdout=subprocess.PIPE)
        size = sw * sh * 3
        i = 0
        while want:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            if i in want:
                im = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
                if (sw, sh) != (w, h):
                    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_LANCZOS4 if w > sw else cv2.INTER_AREA)
                self.cache[i] = im
                want.discard(i)
            i += 1
        p.kill()
        print(f"frames: {len(self.cache)} from {'enhanced' if self.enhanced else 'source (lanczos)'}", flush=True)

    def get(self, f):
        f = int(min(max(f, 0), 925))
        while f not in self.cache and f > 0:
            f -= 1
        return self.cache[f].astype(np.float32) / 255

    def at(self, ff, interp=True):
        a = int(np.floor(ff))
        u = ff - a
        if not interp or u < 0.04 or u > 0.96 or (a + 1) not in self.cache:
            return self.get(round(ff))
        return fx.flow_interp(self.get(a), self.get(a + 1), u)


def _complete(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return int(r.stdout.strip()) >= 926
    except ValueError:
        return False


class Mattes:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cache = {}

    def raw(self, f):
        f = int(round(f))
        if f not in self.cache:
            m = cv2.imread(f"{MATTES}/raw_{f:05d}.png", cv2.IMREAD_GRAYSCALE)
            self.cache[f] = None if m is None else m.astype(np.float32) / 255
        return self.cache[f]

    def person(self, f, guide, seg_id=None, only_cr=False):
        """Matte at output size snapped to the guide frame. only_cr keeps the CR's blob only."""
        m = self.raw(f)
        if m is None:
            return np.zeros(guide.shape[:2], np.float32)
        h, w = m.shape
        m = m.copy()
        if seg_id in ("wave", "walkoff", "turnback", "endcard"):
            # the lab ceiling beam fools the model: drop anything in the top 45% of the frame
            m[: int(0.45 * h)] *= 0
        if only_cr:
            sx, sy = FACE.get(seg_id, (0.5, 0.5))
            m = fx.keep_blob(m, seed=(sx * w, sy * h))
        return fx.matte_up(m, guide, r=max(4, guide.shape[1] // 120))


class Comp:
    def __init__(self, preview=False):
        self.w, self.h = (540, 960) if preview else (1080, 1920)
        self.frames = Frames(self.w, self.h, need_frames())
        self.mattes = Mattes(self.w, self.h)
        self.hist = {}            # per-segment history of base frames (echo)
        self.track = None         # walk-off wall track
        self.title_goat = TT.text_rgba("THE G.O.A.T.", "Cinzel-900.ttf", int(self.w * 0.112), "gold", 0.04, 0.55)
        self.title_cls = TT.with_shadow(TT.text_rgba("CLASS", "Cinzel-700.ttf", int(self.w * 0.16), "white", 0.18, 0.3), 0.07, 0.6)
        self.title_rep = TT.with_shadow(TT.text_rgba("REPRESENTATIVE", "Cinzel-700.ttf", int(self.w * 0.068), "gold", 0.10, 0.3), 0.09, 0.6)
        self.plus = TT.text_rgba("+1000 AURA", "Cinzel-900.ttf", int(self.w * 0.085), "gold", 0.03, 0.6)
        self.end_goat = TT.text_rgba("THE G.O.A.T.", "Cinzel-900.ttf", int(self.w * 0.115), "gold", 0.04, 0.7)
        self.end_sub = TT.text_rgba("CLASS REPRESENTATIVE", "Cinzel-700.ttf", int(self.w * 0.047), "white", 0.16, 0.35)
        self.subs = [(0.05, 2.03, "I can imitate goats."), (2.08, 2.66, "Please do."), (2.70, 3.24, "MAAA!"),
                     (3.26, 3.70, "Take two.")]
        self.sub_rgba = {s: TT.subtitle_rgba(s, int(self.w * 0.052)) for _, _, s in self.subs}

    # ---------- helpers ----------
    def S(self, x):
        return x * self.w

    def base(self, seg, t):
        f = edl.src_frame(seg, t)
        slow = seg["id"] in ("stare", "turn", "pose", "turnback", "wave", "smirk")
        return self.frames.at(f, interp=slow), f

    def cam(self, img, seg, t):
        """The segment's own move plus the 808 punches and shakes."""
        h, w = img.shape[:2]
        scale, cx, cy, dx, dy, rot = 1.0, w / 2, h / 2, 0.0, 0.0, 0.0
        if "cam" in seg:
            s0, s1, fx_, fy_ = seg["cam"]
            u = fx.ease_in_out_cubic((t - seg["t0"]) / (seg["t1"] - seg["t0"]))
            scale = s0 + (s1 - s0) * u
            cx, cy = fx_ * w, fy_ * h
        # 808 punches: a small scale kick on every hit, bigger on cuts
        for n in edl.K808:
            th = edl.tq(n)
            u = t - th
            if 0 <= u < 0.25:
                big = abs(th - seg["t0"]) < 0.02
                scale *= 1 + (0.06 if big else 0.025) * (1 - fx.ease_out_cubic(u / 0.25))
                ddx, ddy, dr = fx.shake_offset(u, (0.012 if big else 0.005) * w, 0.09, seed=int(n * 3))
                dx, dy, rot = dx + ddx, dy + ddy, rot + dr
        return fx.camera(img, scale, cx, cy, dx, dy, rot)

    def cine(self, img, n, t, seg_id):
        img = fx.tame_reds(img, 0.28)
        img = fx.grade(img, warmth=1.0, sat=0.9, contrast=1.05, lift=0.02, teal=1.1)
        img = fx.bloom(img, 0.70, 0.32)
        img = fx.vignette(img, 0.24)
        img = fx.sharpen(img, 0.35, 1.0 * self.w / 1080)
        return img

    # ---------- the frame ----------
    def frame(self, i):
        t = i / FPS
        seg = edl.segment_at(t)
        sid = seg["id"]
        w, h = self.w, self.h
        if sid == "strobe":
            img = self.strobe(t)
        elif sid == "dblexp":
            img = self.dblexp(t, seg)
        else:
            img, f = self.base(seg, t)
            m_person = None
            if "echo" in seg["fx"] or "echo_light" in seg["fx"]:
                hist = self.hist.setdefault(sid, [])
                hist.append(img)
                del hist[:-6]
                if "echo" in seg["fx"] or t < edl.tq(45):
                    img = fx.echo(hist, 0.62 if "echo" in seg["fx"] else 0.45, 0.42 if "echo" in seg["fx"] else 0.6)
            if any(k in seg["fx"] for k in ("title_goat", "aura", "aura_small", "hero_hit", "smirk_hits", "title_cr", "curtain_flash")):
                m_person = self.mattes.person(f, img, sid, only_cr=sid not in ("walkoff",))
            # titles that sit BEHIND him are composited before the camera move (they live in the scene)
            if "title_goat" in seg["fx"]:
                img = self.goat_behind(img, m_person, t)
            if "title_cr" in seg["fx"]:
                img = self.cr_behind(img, m_person, t, f)
            if "curtain_flash" in seg["fx"]:
                for tn in (edl.tq(26), edl.tq(27), edl.tq(28)):
                    if 0 <= t - tn < 1 / FPS - 1e-6:
                        img = fx.region_flash(img, fx.red_mask(img, m_person), 0.95)
            if "aura" in seg["fx"]:
                img = self.aura(img, m_person, t, seg)
            if "aura_small" in seg["fx"]:
                k = fx.ease_out_cubic((t - edl.tq(61)) / 0.4) if t >= edl.tq(61) else 0.0
                img = fx.aura_glow(img, m_person, t, 1.1 * k, GOLD_GLOW, size_frac=0.02)
            if "hero_hit" in seg["fx"] or "smirk_hits" in seg["fx"]:
                img = self.silhouette_flash(img, m_person, t, seg)
            if seg["fx"][0] == "podcast":
                img = self.podcast_look(img, t, seg)
            img = self.cam(img, seg, t) if seg["fx"][0] != "podcast" else img
            if "finale_zoom" in seg["fx"]:
                img = self.finale_zoom(img, t)
            if "cine" in seg["fx"]:
                img = self.cine(img, i, t, sid)
            img = self.transitions(img, t, seg)
            if "plus1000" in seg["fx"]:
                img = self.plus1000(img, t, seg)
            if "endcard" in seg["fx"]:
                img = self.endcard(img, t)
        img = self.hits(img, t, seg)
        # bars slam in on the drop
        if t >= edl.DROP - 1e-6:
            k = fx.ease_out_cubic((t - edl.DROP) / 0.1)
            img = fx.letterbox(img, BARS * k)
        img = fx.grain(img, i, 0.028 if t >= edl.DROP else 0.012)
        img = self.end_fade(img, t)
        img = self.captions(img, t)                  # captions LAST
        return np.clip(img, 0, 1)

    # ---------- the hook ----------
    def podcast_look(self, img, t, seg):
        img = fx.grade(img, warmth=0.6, sat=0.97, contrast=0.85, lift=0.012, teal=0.5)
        img = fx.sharpen(img, 0.3, 1.0 * self.w / 1080)
        if seg["id"] == "her_maaa":
            u = t - (seg["t0"] + 0.017)
            if u >= 0:
                k = fx.ease_out_cubic(min(u / 0.1, 1))
                dx, dy, dr = fx.shake_offset(u, 0.01 * self.w, 0.12, seed=4)
                img = fx.camera(img, 1 + 0.16 * k, 0.56 * self.w, 0.30 * self.h, dx, dy, dr)
        if seg["id"] == "host_take2":
            u = (t - seg["t0"]) / (seg["t1"] - seg["t0"])
            k = np.clip((u - 0.6) / 0.4, 0, 1)
            img = fx.desat(img, 0.9 * k)
            img = fx.camera(img, 1 + 0.10 * fx.ease_in_cubic(k), 0.52 * self.w, 0.30 * self.h)
            img = fx.tunnel(img, 0.8 * k)
        return img

    def strobe(self, t):
        """9 frames on black: head, shoulders, the whole him; each as a white matte then a red cut-out."""
        w, h = self.w, self.h
        k = int(round((t - 3.70) * FPS))
        src = self.frames.get(521)
        m = self.mattes.person(521, src, "stare", only_cr=True)
        ys = np.nonzero(m.max(axis=1) > 0.5)[0]
        top = ys.min() if len(ys) else int(0.3 * h)
        neck = int(top + 0.17 * h)
        head = m.copy(); head[neck:] = 0
        body = m.copy(); body[:neck] = 0
        seq = [("w", head), ("r", head), ("w", body), ("r", body), ("w", m), ("r", m), ("rim", m), ("w", m), ("flash", m)]
        mode, part = seq[min(k, len(seq) - 1)]
        out = np.zeros((h, w, 3), np.float32)
        if mode == "w":
            out = fx.region_flash(out, part, 1.0, (0.97, 0.96, 0.92))
        elif mode == "r":
            red = np.clip(fx.luma(src)[..., None] * np.array([1.35, 0.18, 0.12], np.float32) + np.array([0.12, 0.0, 0.0], np.float32), 0, 1)
            out = red * part[..., None]
        elif mode == "rim":
            r = fx.rim(part, 0.006)
            out = fx.region_flash(out, r, 1.0, (1.0, 1.0, 1.0))
        else:
            out = np.ones((h, w, 3), np.float32) * 0.92
        return fx.camera(out, 1.0 + 0.012 * k, 0.58 * w, 0.4 * h)

    # ---------- phrase 1 ----------
    def goat_behind(self, img, m, t):
        """THE G.O.A.T. on the board behind his head: slams in on the drop, glows on the 808s, fades by the cut."""
        u = t - edl.DROP
        if u < 0:
            return img
        scale = 1.0 + 0.18 * (1 - fx.ease_out_cubic(min(u / 0.22, 1)))
        a = min(u / 0.05, 1.0)
        end = edl.tq(6)
        if t > end - 0.2:
            a *= max(0.0, (end - t) / 0.2)
        layer = TT.place((self.h, self.w), self.title_goat, self.w * 0.5, self.h * 0.322, scale, a)
        out = fx.over(img, layer)
        out = out * (1 - m[..., None]) + img * m[..., None]          # him in front of the title
        return out

    def silhouette_flash(self, img, m, t, seg):
        hits = [edl.tq(4)] if seg["id"] == "stare" else [edl.tq(35)]
        for th in hits:
            if 0 <= t - th < 1.5 / FPS:
                img = fx.region_flash(img, m, 1.0, (0.98, 0.97, 0.93))
        return img

    def aura(self, img, m, t, seg):
        u = t - seg["t0"]
        k = fx.ease_out_cubic(min(u / 0.15, 1))
        bg = fx.desat(img, 0.55 * k) * (1 - 0.32 * k)
        img = bg * (1 - m[..., None]) + img * m[..., None]
        img = fx.aura_glow(img, m, t, 1.25 * k, GOLD_GLOW, size_frac=0.04)
        r = fx.rim(m, 0.0035)
        img = fx.region_flash(img, r, 0.8 * k, (1.0, 0.95, 0.8))
        return img

    def plus1000(self, img, t, seg):
        u = t - (seg["t0"] + 0.12)
        if u < 0:
            return img
        s = 1.0 + 0.6 * (1 - fx.ease_out_cubic(min(u / 0.16, 1)))
        a = min(u / 0.04, 1.0) * (1 - max(0.0, (u - 0.55) / 0.15))
        layer = TT.place((self.h, self.w), self.plus, self.w * 0.68, self.h * (0.40 - 0.02 * fx.ease_out_cubic(min(u / 0.6, 1))), s, max(a, 0))
        return fx.over(img, layer)

    # ---------- phrase 2: the double exposure ----------
    def dblexp(self, t, seg):
        w, h = self.w, self.h
        u = t - seg["t0"]
        src = self.frames.get(521)
        m = self.mattes.person(521, src, "stare", only_cr=True)
        # place the silhouette: centred, bigger, pushing in
        push = 1.04 + 0.14 * fx.ease_in_out_cubic(u / (seg["t1"] - seg["t0"]))
        M = fx.camera_matrix(w, h, push, 0.58 * w, 0.45 * h, (0.5 - 0.58) * w, (0.47 - 0.45) * h)
        mm = cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_LINEAR)
        subj = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
        # feather the bottom into white
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        mm = mm * np.clip((0.97 - yy) / 0.22, 0, 1)
        k = min(int(u / edl.EIGHTH), len(DBL_FILLS) - 1)
        f0 = DBL_FILLS[k][0] + int((u - k * edl.EIGHTH) * FPS)
        fill = self.frames.get(f0)
        fill = fx.camera(fill, 1.15, w / 2, h / 2)
        fill = fx.grade(fill, warmth=1.1, sat=1.05, contrast=1.1, lift=0.0)
        sl = fx.luma(subj)[..., None]
        inside = 1 - (1 - fill) * (1 - 0.30 * sl)               # screen a little of his own face in
        inside = inside * (0.72 + 0.28 * sl)
        white = np.ones((h, w, 3), np.float32) * np.array([0.985, 0.98, 0.97], np.float32)
        out = white * (1 - mm[..., None]) + inside * mm[..., None]
        # the last two frames before the filter opens: solid black silhouette (threshold)
        if seg["t1"] - t <= 2.0 / FPS + 1e-6:
            out = white * (1 - mm[..., None])
        return out

    # ---------- transitions ----------
    def transitions(self, img, t, seg):
        w = self.w
        sid = seg["id"]
        # suck out of the phone shot into the white double exposure
        if sid == "phone":
            d = seg["t1"] - t
            if d < 0.18:
                k = 1 - d / 0.18
                img = fx.zoom_blur(fx.camera(img, 1 + 0.35 * k * k), k)
                img = fx.flash(img, (0.985, 0.98, 0.97), k ** 1.5)
        # whip out of the thumbs-up (he turns away) and whip into the smirk
        if sid == "thumb":
            d = seg["t1"] - t
            if d < 0.2:
                k = fx.ease_in_cubic(1 - d / 0.2)
                img = fx.motion_blur(fx.camera(img, 1.0, None, None, -0.45 * w * k, 0), k, 0, 0.12)
        if sid == "smirk":
            u = t - seg["t0"]
            if u < 0.17:
                k = 1 - fx.ease_out_cubic(u / 0.17)
                img = fx.motion_blur(fx.camera(img, 1.0, None, None, 0.45 * w * k, 0), k, 0, 0.12)
        if sid == "typing" and t - seg["t0"] < 0.08:          # the filter opens: hit
            img = fx.flash(img, (1, 1, 1), 0.85 * (1 - (t - seg["t0"]) / 0.08))
        if sid == "close":
            u = t - seg["t0"]
            if u < 0.2:
                img = fx.rgb_split(img, 0.02 * w * (1 - fx.ease_out_cubic(u / 0.2)))
            img = fx.light_leak(img, t, 0.35 * np.clip(1 - abs(u - 0.6) / 0.6, 0, 1), True, 1)
        if sid == "wave":
            u = t - edl.tq(45)
            if u >= 0:
                img = fx.motion_blur(img, 0.35, 0, 0.05)
        return img

    def hits(self, img, t, seg):
        """Flashes, shockwaves and chroma on the big hits (after the grade)."""
        w, h = self.w, self.h
        # the drop
        u = t - edl.DROP
        if 0 <= u < 0.6:
            img = fx.shockwave(img, u, 0.58 * w, 0.40 * h, 0.03, 0.08)
            img = fx.chroma(img, 0.016 * w * max(0.0, 1 - u / 0.3))
            img = fx.flash(img, (1, 1, 1), max(0.0, 1 - u / 0.14) ** 1.5)
        # pose freeze and phrase downbeats
        for th, col, dur, amp in ((edl.tq(10), (1, 0.97, 0.9), 0.12, 0.7), (edl.tq(32), (1, 1, 1), 0.1, 0.8),
                                  (edl.tq(48), (1, 0.97, 0.9), 0.14, 0.6), (edl.tq(38), (1, 1, 1), 0.06, 0.5)):
            u = t - th
            if 0 <= u < dur:
                img = fx.flash(img, col, amp * (1 - u / dur))
        u = t - edl.tq(32)
        if 0 <= u < 0.5:
            img = fx.shockwave(img, u, 0.5 * w, 0.4 * h, 0.022, 0.07)
        # glitch hits in the montage
        for th in (edl.tq(19), edl.tq(31)):
            u = t - th
            if 0 <= u < 2.5 / FPS:
                img = fx.glitch(img, int(th * 100), 0.7)
                img = fx.rgb_split(img, 0.012 * w)
        return img

    # ---------- phrase 4 ----------
    def cr_behind(self, img, m, t, f):
        """CLASS / REPRESENTATIVE on the far wall above the curtains, tracked with the camera pan, people in front."""
        u = t - edl.tq(48)
        if u < 0:
            return img
        # the wall's drift: integrate the measured global pan from the walk-off's first frame
        if self.track is None:
            import json
            F = json.load(open("renders/analysis/frames.json"))["frames"]
            acc, tr = np.zeros(2), {}
            for k in range(806, 926):
                p = F[k].get("pan", [0, 0])
                acc = acc + np.array(p) * (self.w / 576)
                tr[k] = acc.copy()
            self.track = tr
        ks = sorted(self.track)
        tx = np.array([self.track[k][0] for k in ks]); ty = np.array([self.track[k][1] for k in ks])
        mid = 0.5 * (np.interp(806, ks, tx) + np.interp(905, ks, tx)), 0.5 * (np.interp(806, ks, ty) + np.interp(905, ks, ty))
        dxy = 0.45 * (np.interp(f, ks, tx) - mid[0]), 0.45 * (np.interp(f, ks, ty) - mid[1])
        a = fx.ease_out_cubic(min(u / 0.35, 1))
        end = edl.tq(56.5)
        if t > end - 0.25:
            a *= max(0.0, (end - t) / 0.25)
        spread = 1.0 + 0.08 * (1 - fx.ease_out_cubic(min(u / 0.8, 1)))
        cx, cy = self.w * 0.5 + dxy[0], self.h * 0.475 + dxy[1]
        l1 = TT.place((self.h, self.w), self.title_cls, cx, cy - self.h * 0.045, spread, a)
        l2 = TT.place((self.h, self.w), self.title_rep, cx, cy + self.h * 0.022, spread, a)
        out = fx.over(fx.over(img, l1), l2)
        return out * (1 - m[..., None]) + img * m[..., None]

    def finale_zoom(self, img, t):
        t0, t1 = edl.tq(56.5), edl.tq(64) + 0.6
        k = fx.ease_in_out_cubic((t - t0) / (t1 - t0))
        return fx.camera(img, 1 + 0.85 * k, 0.62 * self.w, 0.60 * self.h, (0.5 - 0.62) * self.w * k, (0.47 - 0.60) * self.h * k)

    def endcard(self, img, t):
        u = t - edl.SONG_END
        if u < 0:
            return img
        if u < 0.5:
            img = fx.shockwave(img, u, 0.5 * self.w, 0.45 * self.h, 0.025, 0.08)
        img = fx.flash(img, (1, 1, 1), max(0.0, 1 - u / 0.12))
        img = img * (1 - 0.35 * fx.ease_out_cubic(min(u / 0.3, 1)))
        s = 1.0 + 0.25 * (1 - fx.ease_out_cubic(min(u / 0.25, 1)))
        a = min(u / 0.05, 1)
        img = fx.over(img, TT.place((self.h, self.w), self.end_goat, self.w * 0.5, self.h * 0.30, s, a))
        a2 = fx.ease_out_cubic(min(max(u - 0.25, 0) / 0.3, 1))
        img = fx.over(img, TT.place((self.h, self.w), self.end_sub, self.w * 0.5, self.h * 0.365, 1.0, a2))
        return img

    def end_fade(self, img, t):
        d = edl.END - t
        if d < 0.6:
            img = img * max(0.0, d / 0.6) ** 1.4
        return img

    def captions(self, img, t):
        for a, b, s in self.subs:
            if a <= t < b:
                rgba = self.sub_rgba[s]
                pop = 1.0 + (0.18 if s == "MAAA!" else 0.06) * (1 - fx.ease_out_cubic(min((t - a) / 0.08, 1)))
                img = fx.over(img, TT.place((self.h, self.w), rgba, self.w * 0.5, self.h * 0.735, pop, 1.0))
        return img


def render(out, preview=False, rng=None):
    c = Comp(preview)
    n = edl.frame_count()
    a, b = (0, n) if rng is None else (int(round(rng[0] * FPS)), min(n, int(round(rng[1] * FPS))))
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{c.w}x{c.h}",
                            "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow" if not preview else "veryfast",
                            "-crf", "16" if not preview else "22", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(a, b):
        im = c.frame(i)
        enc.stdin.write((im * 255 + 0.5).astype(np.uint8).tobytes())
        if (i - a) % 60 == 0:
            print(f"frame {i}/{b}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("->", out)


def still(t, out, preview=False):
    c = Comp(preview)
    im = c.frame(int(round(t * FPS)))
    cv2.imwrite(out, cv2.cvtColor((im * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--range", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--stills", default=None, help="comma-separated output times -> renders/analysis/still_<t>.jpg")
    a = ap.parse_args()
    if a.stills:
        c = Comp(a.preview)
        for s in a.stills.split(","):
            im = c.frame(int(round(float(s) * FPS)))
            cv2.imwrite(f"renders/analysis/still_{float(s):06.3f}.jpg", cv2.cvtColor((im * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
        print("stills done")
    else:
        rng = tuple(float(v) for v in a.range.split("-")) if a.range else None
        render(a.out or ("renders/cr_aura_preview.mp4" if a.preview else "renders/cr_aura_video.mp4"), a.preview, rng)
