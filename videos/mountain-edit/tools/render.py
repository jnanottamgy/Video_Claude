"""The compositor: every output frame of the reel from the edit (tools/edl.py), rendered in parallel chunks.

  python3 tools/render.py                      # the whole picture -> renders/picture/picture.mp4
  python3 tools/render.py --stills 1.2,15.3    # review stills -> renders/stills/
  python3 tools/render.py --sheet 15 28.5 4    # a contact sheet of a range at 4 fps -> renders/stills/

A frame: the shot's base image (its layout, with view moves: punches, shakes, whips) -> the shot's grade ->
words behind the subject (cut out by its matte) -> overlays (HUD, helix, code rain, glints, words in front) ->
global finishing (flashes, inverts, glitch, aberration, CRT, halation, vignette, grain, letterbox).
"""
import argparse
import functools
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402
import gfx  # noqa: E402
import look  # noqa: E402
import media  # noqa: E402

W, H, FPS = media.W, media.H, media.FPS
ROOT = media.ROOT
CACHE = os.path.join(ROOT, "renders/cache")
SHOTS = edl.SHOTS
NFRAMES = int(round(edl.DURATION * FPS))


def shot_at(f):
    for s in SHOTS:
        if s["F0"] <= f < s["F1"]:
            return s
    return None


# ----------------------------------------------------------------------------------------- sources

def _vt(v):
    v = tuple(v)
    return v + (0.0,) * (4 - len(v))


def view_of(spec, t):
    v = spec["view"]
    return _vt(v(t) if callable(v) else v)


def src_of(spec, t):
    s = spec["src"]
    if callable(s):
        return s(t)
    s0, speed = s
    return s0 + (t - spec["t0"]) * speed


@functools.lru_cache(maxsize=12)
def source(key):
    """A decoded source for a shot, panel or tile, sized from every time and view it will ask for."""
    spec = edl.SPECS[key]
    ts = np.arange(spec["F0"], spec["F1"] + 1) / FPS
    times = [src_of(spec, t) for t in ts]
    views = [view_of(spec, t) for t in ts]
    aspect = spec.get("aspect", W / H)
    zmax = spec.get("zmax", 1.0)
    vs = [(cx, cy, cw / zmax) for cx, cy, cw, _ in views]
    if abs(aspect - W / H) > 1e-3:          # panels: convert to a 16:9-equivalent window that covers the tall one
        vs = [(cx, cy, max(cw, cw / aspect * W / H)) for cx, cy, cw in vs]
    return media.Shot(spec["clip"], times, vs, margin=spec.get("margin", 1.3), max_scale=spec.get("max_scale", 1.0))


def render_view(key, spec, t, out=(W, H), zoom=1.0, dx=0.0, dy=0.0, droll=0.0):
    S = source(key)
    cx, cy, cw, roll = view_of(spec, t)
    return S.view(src_of(spec, t), cx, cy, cw / zoom, roll + droll, spec.get("blend", False), out, dx, dy)


# ----------------------------------------------------------------------------------------- view effects

def view_fx(spec, t, f):
    """Zoom (punches), offset (shakes) and roll for this frame from the shot's fx list."""
    zoom, dx, dy, dr = 1.0, 0.0, 0.0, 0.0
    for fx in spec.get("fx", []):
        k = fx[0]
        if k == "punch":                       # ("punch", t, amount, decay)
            zoom *= 1 + fx[2] * look.env_hit(t, fx[1], 0.0, fx[3] if len(fx) > 3 else 0.35, 2.2)
        elif k == "zoom":                       # ("zoom", t0, t1, z0, z1) eased continuous zoom
            u = np.clip((t - fx[1]) / (fx[2] - fx[1]), 0, 1)
            u = u * u * (3 - 2 * u)
            zoom *= fx[3] + (fx[4] - fx[3]) * u
        elif k == "shake":                      # ("shake", t, amp, dur[, seed])
            a, b, c = look.shake(f, fx[1], fx[2], fx[3], fx[4] if len(fx) > 4 else 0)
            dx += a; dy += b; dr += c
        elif k == "handheld":                   # ("handheld", amp) gentle continuous float
            dx += fx[1] * (math.sin(t * 1.3) + 0.5 * math.sin(t * 2.9 + 1))
            dy += fx[1] * 0.6 * (math.sin(t * 1.7 + 2) + 0.4 * math.sin(t * 3.3))
    return zoom, dx, dy, dr


def whip_state(spec, t):
    """('whip', t0, t1, dir, dist): slide by up to dist*W with directional blur, peak speed at the cut."""
    for fx in spec.get("fx", []):
        if fx[0] == "whip" and fx[1] <= t < fx[2]:
            u = (t - fx[1]) / (fx[2] - fx[1])
            return fx, u
    return None, 0.0


def base_full(key, spec, t, f, out=(W, H)):
    zoom, dx, dy, dr = view_fx(spec, t, f)
    wfx, u = whip_state(spec, t)
    zb = [fx for fx in spec.get("fx", []) if fx[0] == "zoomblur" and fx[1] <= t < fx[2]]
    if wfx is None and not zb:
        return render_view(key, spec, t, out, zoom, dx, dy, dr)
    if wfx is not None:
        _, a, b, d, dist = wfx[:5]
        out_side = wfx[5] if len(wfx) > 5 else "out"     # "out": leaves the frame at the end; "in": arrives
        # position along the whip: eased so the speed peaks at the cut
        p = u ** 2.2 if out_side == "out" else -((1 - u) ** 2.2)
        speed = (2.2 * u ** 1.2) if out_side == "out" else 2.2 * (1 - u) ** 1.2
        off = d * dist * W * p
        blur = d * dist * W * 0.18 * speed
        n = 9
        acc = None
        for i in range(n):
            o = off + blur * (i / (n - 1) - 0.5)
            img = render_view(key, spec, t, out, zoom, dx + o, dy, dr)
            acc = img if acc is None else acc + img
        return acc / n
    fx = zb[0]                                          # ("zoomblur", t0, t1, amount, direction +1 in / -1 out)
    u = (t - fx[1]) / (fx[2] - fx[1])
    amt = fx[3] * (u if fx[4] > 0 else 1 - u) ** 1.5
    n = 8
    acc = None
    for i in range(n):
        img = render_view(key, spec, t, out, zoom * (1 + amt * i / (n - 1)), dx, dy, dr)
        acc = img if acc is None else acc + img
    return acc / n


# ----------------------------------------------------------------------------------------- layouts

def base(spec, t, f):
    lay = spec.get("layout", "full")
    if lay == "full":
        return base_full(spec["id"], spec, t, f)
    if lay == "black":
        return np.zeros((H, W, 3), np.float32)
    if lay == "photo":
        return photo_frame(spec, t, f)
    if lay == "panels":
        return panels_frame(spec, t, f)
    if lay == "card":
        return card_frame(spec, t, f)
    if lay == "custom":
        return spec["draw"](spec, t, f, sys.modules[__name__])
    raise ValueError(lay)


def panels_frame(spec, t, f):
    """Split screens and grids: each panel is its own source in its own rect, sliding/popping in at its time."""
    img = np.zeros((H, W, 3), np.float32) + np.array(spec.get("bg", (0, 0, 0)), np.float32)
    if spec.get("bg_key"):
        bg = base_full(spec["bg_key"], edl.SPECS[spec["bg_key"]], t, f)
        img = cv2.GaussianBlur(bg, (0, 0), 25) * 0.35
    for pk in spec["panels"]:
        p = edl.SPECS[pk]
        if t < p["appear"]:
            continue
        x0, y0, x1, y1 = p["rect"]
        pw, ph = x1 - x0, y1 - y0
        u = min(1.0, (t - p["appear"]) / p.get("anim", 0.12))
        e = 1 - (1 - u) ** 3
        style = p.get("style", "slide_up")
        ox, oy, sc = 0, 0, 1.0
        if style == "slide_up":
            oy = (1 - e) * ph * 0.6
        elif style == "slide_down":
            oy = -(1 - e) * ph * 0.6
        elif style == "pop":
            sc = 1.25 - 0.25 * e
        tile = base_full(pk, p, t, f, out=(pw, ph))
        if style == "pop" and sc != 1.0:
            m = cv2.getRotationMatrix2D((pw / 2, ph / 2), 0, sc)
            tile = cv2.warpAffine(tile, m, (pw, ph), borderMode=cv2.BORDER_REFLECT101)
        fl = look.env_hit(t, p["appear"], 0, 0.18, 2)          # each panel lands with its own flash
        if fl > 0:
            tile = look.flash(tile, 0.7 * fl)
        X0, Y0 = int(x0 + ox), int(y0 + oy)
        xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X0 + pw), min(H, Y0 + ph)
        if xb > xa and yb > ya:
            img[ya:yb, xa:xb] = tile[ya - Y0:yb - Y0, xa - X0:xb - X0]
    return img


def card_frame(spec, t, f):
    """A clip inside a rounded "window" over a darkened, blurred copy of itself; the card grows to full frame."""
    full = base_full(spec["id"], spec, t, f)
    bg = cv2.GaussianBlur(cv2.resize(full, (W // 4, H // 4)), (0, 0), 6)
    bg = cv2.resize(bg, (W, H)) * 0.32
    u = np.clip((t - spec["grow"][0]) / (spec["grow"][1] - spec["grow"][0]), 0, 1)
    u = u * u * (3 - 2 * u)
    cw0, ch0 = spec["card"]
    cw, ch = cw0 + (W - cw0) * u, ch0 + (H - ch0) * u
    r = int(spec.get("radius", 48) * (1 - u))
    x0, y0 = int((W - cw) / 2), int((H - ch) / 2)
    mask = np.zeros((H, W), np.uint8)
    cv2.rectangle(mask, (x0 + r, y0), (int(x0 + cw) - r, int(y0 + ch)), 255, -1)
    cv2.rectangle(mask, (x0, y0 + r), (int(x0 + cw), int(y0 + ch) - r), 255, -1)
    for cx, cy in ((x0 + r, y0 + r), (int(x0 + cw) - r, y0 + r), (x0 + r, int(y0 + ch) - r), (int(x0 + cw) - r, int(y0 + ch) - r)):
        cv2.circle(mask, (cx, cy), r, 255, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 1.0)[..., None]
    # the card shows the full frame shrunk into it (a window onto the shot)
    small = cv2.resize(full, (max(2, int(cw)), max(2, int(ch))), interpolation=cv2.INTER_AREA)
    inner = bg.copy()
    inner[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = small[:min(small.shape[0], H - y0), :min(small.shape[1], W - x0)]
    out = bg * (1 - m) + inner * m
    if u < 1:                                         # a thin bright rim
        edge = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32) / 255
        out = out + edge[..., None] * 0.6 * (1 - u)
    return out


# ----------------------------------------------------------------------------------------- photos (2.5D)

@functools.lru_cache(maxsize=4)
def photo_layers(key):
    """A photo split into background (person removed, filled) and foreground (person + alpha), at 2x output."""
    p = edl.SPECS[key]
    img = media.photo(p["clip"], p.get("rotate", 0))
    cache = os.path.join(CACHE, "photo", f"{p['clip']}_{p.get('rotate', 0)}.png")
    if os.path.exists(cache):
        m = cv2.imread(cache, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    else:
        from rembg import new_session, remove
        from PIL import Image
        m = np.asarray(remove(Image.fromarray((img * 255).astype(np.uint8)), session=new_session("isnet-general-use"),
                              only_mask=True)).astype(np.float32) / 255
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        cv2.imwrite(cache, (m * 255).astype(np.uint8))
    # background: inpaint the person (dilated) at low res, then blur the fill
    hole = cv2.dilate((m > 0.2).astype(np.uint8), np.ones((25, 25), np.uint8))
    s = 0.25
    small = cv2.resize((img * 255).astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    hs = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(filled, (0, 0), 3)
    fill_big = cv2.resize(filled, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    hb = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 6)[..., None]
    bg = img * (1 - hb) + fill_big * hb
    return img, bg, m


def photo_frame(spec, t, f):
    """Two layers moving at different speeds (parallax), the person nearer: a still that moves like video."""
    img, bg, m = photo_layers(spec["id"])
    ih, iw = img.shape[:2]
    u = np.clip((t - spec["t0"]) / max(1e-3, spec["t1"] - spec["t0"]), 0, 1)
    cx, cy, cw = spec["view"](t) if callable(spec["view"]) else spec["view"]
    zoom, dx, dy, dr = view_fx(spec, t, f)
    bgz = spec.get("bg_zoom", (1.0, 1.06))
    fgz = spec.get("fg_zoom", (1.0, 1.14))
    sb = bgz[0] + (bgz[1] - bgz[0]) * u
    sf = fgz[0] + (fgz[1] - fgz[0]) * u
    pan = spec.get("pan", (0.0, 0.0))

    def warp(layer, s, par):
        k = W / (cw / s) * zoom
        m_ = np.float32([[k, 0, W / 2 + dx + pan[0] * par * u * W - k * cx],
                         [0, k, H / 2 + dy + pan[1] * par * u * H - k * cy]])
        return cv2.warpAffine(layer, m_, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT101)
    b = warp(bg, sb, 0.4)
    fimg = warp(img, sf, 1.0)
    fa = warp(m, sf, 1.0)
    spec["_alpha"] = (f, fa)                      # the person's matte for this frame (HUD, cut-outs)
    fa = fa[..., None]
    return np.clip(b * (1 - fa) + fimg * fa, 0, 1)


# ----------------------------------------------------------------------------------------- mattes and tracks

def fill_holes(m):
    """Fill holes inside a silhouette (mirrored lenses, bright patches read as background) with a flood fill."""
    b = (m > 0.5).astype(np.uint8) * 255
    ff = b.copy()
    mask = np.zeros((H + 2, W + 2), np.uint8)
    for seed in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        if ff[seed[1], seed[0]] == 0:
            cv2.floodFill(ff, mask, seed, 255)
    holes = cv2.bitwise_not(ff)                       # what the outside flood never reached, inside the subject
    holes = cv2.GaussianBlur(holes.astype(np.float32) / 255, (0, 0), 1.5)
    return np.maximum(m, holes)


def matte(spec, f):
    p = os.path.join(CACHE, "matte", spec["id"], f"{f:05d}.png")
    if not os.path.exists(p):
        return None
    m = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    return fill_holes(m) if spec.get("fill", True) else m


@functools.lru_cache(maxsize=16)
def track(sid):
    p = os.path.join(CACHE, "track", f"{sid}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def matte_box(m, top_frac=None):
    ys, xs = np.nonzero(m > 0.5)
    if len(ys) < 50:
        return None
    x0, x1 = np.percentile(xs, 1), np.percentile(xs, 99)
    y0, y1 = np.percentile(ys, 0.5), np.percentile(ys, 99.5)
    if top_frac:                                  # the head: the top part of the silhouette
        y1 = y0 + (x1 - x0) * top_frac
    return float(x0), float(y0), float(x1), float(y1)


# ----------------------------------------------------------------------------------------- words

def draw_words(ov_behind, ov_front, spec, t):
    for w in spec.get("words", []):
        t_in, t_out = w["t"], w.get("until", spec["t1"])
        if not (t_in <= t < t_out):
            continue
        sl = gfx.slam(t, t_in, w.get("dur", 0.11), w.get("from", 1.35))
        if sl is None:
            continue
        sc, a = sl
        if t_out - t < 0.05 and w.get("fade_out", False):
            a *= (t_out - t) / 0.05
        spr = gfx.text(w["text"], w.get("font", gfx.F_BIG), w.get("size", 300), tuple(w.get("color", gfx.WHITE)),
                       w.get("tracking", 0.0), w.get("stroke", 0), w.get("outline", False))
        x, y = w["pos"](t) if callable(w["pos"]) else w["pos"]
        blur = 2.5 * max(0.0, sc - 1.0) * 6
        target = ov_behind if w.get("behind", False) else ov_front
        if w.get("shadow", True) and not w.get("behind", False):
            sh = np.zeros_like(spr)
            sh[..., 3] = spr[..., 3] * 0.55
            gfx.place(target, sh, x + 4, y + 6, sc, a, 6 + blur)
        gfx.place(target, spr, x, y, sc * w.get("scale", 1.0), a * w.get("alpha", 1.0), blur)


# ----------------------------------------------------------------------------------------- one frame

def frame(f):
    t = f / FPS
    spec = shot_at(f)
    if spec is None:
        img = np.zeros((H, W, 3), np.float32)
        return finish(img, t, f, None)
    raw = base(spec, t, f)
    g = raw
    for pre in spec.get("pre", []):
        if pre[0] == "sky":
            g = look.sky_grad(g, pre[1], 0.0, pre[2] if len(pre) > 2 else 0.6)
        elif pre[0] == "exposure":
            g = g * pre[1]
    g = look.grade(g, spec.get("look", "summit"))
    m = matte(spec, f) if spec.get("matte") else None
    if spec.get("layout") == "photo" and spec.get("_alpha") and spec["_alpha"][0] == f:
        m = spec["_alpha"][1]
    img = g
    ov_b, ov_f = gfx.blank(), gfx.blank()
    draw_words(ov_b, ov_f, spec, t)
    if ov_b[..., 3].max() > 0:
        img = gfx.over(img, ov_b)
        if m is not None:
            mm = m[..., None]
            img = img * (1 - mm) + g * mm
    for fx in spec.get("fx", []):
        k = fx[0]
        if k == "cutout" and m is not None and fx[1] <= t < fx[2]:          # ("cutout", t0, t1, color)
            col = np.array(fx[3] if len(fx) > 3 else (1, 1, 1), np.float32)
            img = img * (1 - m[..., None]) + col * m[..., None]
        elif k == "glow" and m is not None and fx[1] <= t < fx[2]:          # ("glow", t0, t1, color, strength)
            edge = cv2.GaussianBlur(m, (0, 0), 9) - cv2.GaussianBlur(m, (0, 0), 2)
            edge = np.clip(np.abs(edge) * 4, 0, 1)
            rim = np.clip(cv2.GaussianBlur(m, (0, 0), 14) - m, 0, 1) * 2.2
            a = fx[4] if len(fx) > 4 else 1.0
            pul = 0.75 + 0.25 * math.sin(t * 14)
            col = np.array(fx[3] if len(fx) > 3 else (1, 1, 1), np.float32)
            img = 1 - (1 - img) * (1 - np.clip((edge + rim)[..., None] * col * a * pul, 0, 1))
    img = gfx.over(img, ov_f)
    for fx in spec.get("overlays", []):
        img = fx(img, spec, t, f, m, sys.modules[__name__])
    return finish(img, t, f, spec)


def finish(img, t, f, spec):
    G = edl.GLOBAL
    # flashes (white and coloured), inverts, glitches, aberration
    a = 0.0
    col = (1, 1, 1)
    for fl in G["flashes"]:
        e = fl[2] * look.env_hit(t, fl[0], fl[4] if len(fl) > 4 else 0.0, fl[1], 2.0)
        if e > a:
            a, col = e, fl[3] if len(fl) > 3 else (1, 1, 1)
    for iv in G["inverts"]:
        if iv[0] <= t < iv[1]:
            img = look.invert(img, 1.0, iv[2] if len(iv) > 2 else (1.0, 0.9, 0.9))
    for gl in G["glitches"]:
        if gl[0] <= t < gl[1]:
            img = look.glitch_blocks(img, f, gl[2], int(gl[0] * 100))
            img = look.rgb_split(img, 14 * gl[2] * (1 if f % 2 else -1))
    ab = 0.0
    for h in G["hits"]:                              # aberration and a little split on every hit
        ab = max(ab, h[1] * look.env_hit(t, h[0], 0.0, h[2] if len(h) > 2 else 0.25, 2))
    if ab > 0:
        img = look.aberration(img, 0.012 * ab)
    crt = any(c[0] <= t < c[1] for c in G["crt"])
    if crt:
        img = crt_look(img, t, f)
    hal = G["halation"](t)
    if hal > 0:
        img = look.halation(img, 0.8, hal)
    img = look.vignette(img, G["vignette"](t))
    img = look.flash(img, a, col)
    img = look.grain(img, f, G["grain"](t))
    img = look.bars(img, G["bars"](t))
    fade = G["fade"](t)
    if fade < 1:
        img = img * fade
    return np.clip(img, 0, 1)


def crt_look(img, t, f):
    """A broadcast monitor: B&W, scanlines, a rolling bar, slight tearing, LIVE bug and timecode."""
    g = look.bw(img, (0.95, 1.0, 1.02), 1.7)
    yy = np.arange(H)
    scan = (0.78 + 0.22 * (np.sin(yy * math.pi / 2) ** 2)).astype(np.float32)
    g = g * scan[:, None, None]
    roll = ((t * 0.35) % 1.2 - 0.1) * H
    band = np.exp(-((yy - roll) / 60.0) ** 2).astype(np.float32) * 0.12
    g = g + band[:, None, None]
    rng = np.random.default_rng(f)
    if rng.random() < 0.35:                       # a tear
        y0 = int(rng.integers(0, H - 40)); hgt = int(rng.integers(4, 22))
        g[y0:y0 + hgt] = np.roll(g[y0:y0 + hgt], int(rng.integers(-40, 40)), axis=1)
    g = look.rgb_split(g, 2.5)
    h = gfx.Hud()
    if (f // 12) % 2 == 0:
        cv2.circle(h.c, (92, 92), 11, (237, 18, 23, 255), -1, cv2.LINE_AA)
    h.text("LIVE", 112, 76, 30, (1, 1, 1), 0.95, gfx.F_MONOB)
    h.text("CH 04", W - 92, 76, 26, (1, 1, 1), 0.85, gfx.F_MONO, anchor="ra")
    tc = f"{int(t // 60):02d}:{int(t) % 60:02d}:{f % 30:02d}"
    h.text(tc, W - 92, H - 118, 26, (1, 1, 1), 0.85, gfx.F_MONO, anchor="ra")
    return gfx.over(np.clip(g, 0, 1), h.overlay())


# ----------------------------------------------------------------------------------------- drivers

def write_still(f, path):
    img = frame(f)
    cv2.imwrite(path, cv2.cvtColor((img * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])


def render_chunk(args):
    k, f0, f1, out = args
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        img = frame(f)
        p.stdin.write((img * 255 + 0.5).astype(np.uint8).tobytes())
        if (f - f0) % 30 == 0:
            print(f"[chunk {k}] frame {f}/{f1}", flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default="")
    ap.add_argument("--sheet", nargs=3, type=float)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--range", nargs=2, type=float)
    a = ap.parse_args()
    sd = os.path.join(ROOT, "renders/stills")
    os.makedirs(sd, exist_ok=True)
    if a.stills:
        for s in a.stills.split(","):
            f = media.frame_of(float(s))
            write_still(f, os.path.join(sd, f"still_{f:05d}.jpg"))
            print(os.path.join(sd, f"still_{f:05d}.jpg"))
        return
    if a.sheet:
        t0, t1, fps = a.sheet
        fs = [media.frame_of(t) for t in np.arange(t0, t1, 1 / fps)]
        tiles = []
        for f in fs:
            im = cv2.resize(frame(f), (384, 216), interpolation=cv2.INTER_AREA)
            im = (im * 255).astype(np.uint8)
            cv2.putText(im, f"{f / FPS:.2f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
            tiles.append(im)
        cols = 6
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        p = os.path.join(sd, f"sheet_{t0:05.2f}_{t1:05.2f}.jpg")
        cv2.imwrite(p, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(p)
        return
    out_dir = os.path.join(ROOT, "renders/picture")
    os.makedirs(out_dir, exist_ok=True)
    f_start, f_end = 0, NFRAMES
    if a.range:
        f_start, f_end = media.frame_of(a.range[0]), media.frame_of(a.range[1])
    n = a.workers
    # split on shot boundaries near equal sizes so each source decodes in one worker
    bounds = [f_start]
    for k in range(1, n):
        target = f_start + (f_end - f_start) * k // n
        cands = [s["F0"] for s in SHOTS if f_start < s["F0"] < f_end]
        bounds.append(min(cands, key=lambda c: abs(c - target)) if cands else target)
    bounds.append(f_end)
    bounds = sorted(set(bounds))
    jobs = [(k, bounds[k], bounds[k + 1], os.path.join(out_dir, f"seg_{k:02d}.mp4")) for k in range(len(bounds) - 1)]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(len(jobs)) as pool:
        outs = pool.map(render_chunk, jobs)
    lst = os.path.join(out_dir, "segs.txt")
    with open(lst, "w") as fh:
        for o in outs:
            fh.write(f"file '{o}'\n")
    final = os.path.join(out_dir, "picture.mp4" if not a.range else "picture_range.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", final], check=True)
    print(final)


if __name__ == "__main__":
    main()
