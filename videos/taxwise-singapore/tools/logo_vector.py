"""The TaxWise TW shield as clean, symmetric vector geometry (design/tw-mark.svg).

The client's logo files are small (180-416 px), so the mark is rebuilt: corners read off a 16x trace of the
white-on-navy file, straight edges kept straight, every curved edge a cubic Bezier fitted (least squares, fixed
ends) to the traced outline, then mirrored about x = 500 so the mark is exactly symmetric. Three parts, so they
can animate on their own: the arched T (with its notched stem), the W shield, the diamond.
viewBox 0 0 1000 1114.
  python3 tools/logo_vector.py   ->  design/tw-mark.svg, renders/analysis/logo_check.png (overlay on the original)
"""
import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "renders/src/brand/logo_white_on_navy.png")
K = 16


def traced():
    """Contour points of the three shapes, in viewBox units (x 0..1000)."""
    im = np.array(Image.open(SRC).convert("L")).astype(np.float32)
    big = cv2.GaussianBlur(cv2.resize(im, (180 * K, 180 * K), interpolation=cv2.INTER_CUBIC), (0, 0), K * 0.35)
    _, th = cv2.threshold(big.astype(np.uint8), 140, 255, cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnts = sorted([c[:, 0, :].astype(np.float64) for c in cnts if cv2.contourArea(c) > 2000], key=lambda c: c[:, 1].min())
    allp = np.vstack(cnts)
    x0, y0, x1 = allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max()
    s = 1000.0 / (x1 - x0)
    return [(c - [x0, y0]) * s for c in cnts], s, (x0, y0)


def fit_cubic(pts, p0, p3):
    """Least-squares cubic Bezier through fixed ends p0, p3 for points ordered along the edge."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = d / d[-1]
    b0, b1, b2, b3 = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t ** 2 * (1 - t), t ** 3
    rhs = pts - np.outer(b0, p0) - np.outer(b3, p3)
    A = np.stack([b1, b2], 1)
    sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    return sol[0], sol[1]


def edge_points(contour, a, b):
    """Contour points between the points nearest a and b (the shorter way round), trimmed off the corners."""
    ia = np.argmin(np.linalg.norm(contour - a, axis=1))
    ib = np.argmin(np.linalg.norm(contour - b, axis=1))
    n = len(contour)
    fwd = [(ia + k) % n for k in range((ib - ia) % n + 1)]
    bwd = [(ia - k) % n for k in range((ia - ib) % n + 1)]
    idx = fwd if len(fwd) <= len(bwd) else bwd
    p = contour[idx]
    m = max(1, len(p) // 12)
    return p[m:-m]


def mirror(p):
    return np.array([1000.0 - p[0], p[1]])


def build():
    (t_c, w_c, d_c), _, _ = traced()
    P = lambda x, y: np.array([x, y], float)
    # corners (left half; the right half mirrors them)
    T_TOP_L, T_BAR_BL, T_STEM_TL, T_STEM_BL, T_NOTCH = P(0, 87.5), P(0, 285), P(421, 162), P(421, 431), P(500, 388)
    W_OUT_TL, W_ARM_TL, W_VALLEY_L, W_PEAK, W_BOT_L, W_BOT_C = (P(25, 432), P(147, 358), P(281, 725), P(500, 501),
                                                                 P(231, 931), P(500, 718))
    D_TOP, D_LEFT, D_BOT = P(500, 877), P(384, 981), P(500, 1113)

    def sym_fit(contour, a, b):
        """Fit the left edge a->b and the mirrored right edge together, return left-half control points."""
        pl = edge_points(contour, a, b)
        pr = edge_points(contour, mirror(a), mirror(b))
        pr = np.c_[1000.0 - pr[:, 0], pr[:, 1]]
        # orient both a -> b
        if np.linalg.norm(pl[0] - a) > np.linalg.norm(pl[-1] - a):
            pl = pl[::-1]
        if np.linalg.norm(pr[0] - a) > np.linalg.norm(pr[-1] - a):
            pr = pr[::-1]
        c1l, c2l = fit_cubic(pl, a, b)
        c1r, c2r = fit_cubic(pr, a, b)
        return (c1l + c1r) / 2, (c2l + c2r) / 2

    f = lambda p: f"{p[0]:.2f},{p[1]:.2f}"
    # the T: top arc (one symmetric cubic across), the bar's lower arcs, the stem with its notch
    top_pts = edge_points(t_c, T_TOP_L, mirror(T_TOP_L))
    if top_pts[0][0] > top_pts[-1][0]:
        top_pts = top_pts[::-1]
    tc1, tc2 = fit_cubic(top_pts, T_TOP_L, mirror(T_TOP_L))
    tc1, tc2 = (tc1 + mirror(tc2)) / 2, (tc2 + mirror(tc1)) / 2
    lo1, lo2 = sym_fit(t_c, T_BAR_BL, T_STEM_TL)
    t_path = (f"M{f(T_TOP_L)} C{f(tc1)} {f(tc2)} {f(mirror(T_TOP_L))} L{f(mirror(T_BAR_BL))} "
              f"C{f(mirror(lo1))} {f(mirror(lo2))} {f(mirror(T_STEM_TL))} L{f(mirror(T_STEM_BL))} L{f(T_NOTCH)} "
              f"L{f(T_STEM_BL)} L{f(T_STEM_TL)} C{f(lo2)} {f(lo1)} {f(T_BAR_BL)} Z")
    # the W
    in1, in2 = sym_fit(w_c, W_ARM_TL, W_VALLEY_L)
    out1, out2 = sym_fit(w_c, W_OUT_TL, W_BOT_L)
    bt1, bt2 = sym_fit(w_c, W_BOT_L, W_BOT_C)
    w_path = (f"M{f(W_OUT_TL)} L{f(W_ARM_TL)} C{f(in1)} {f(in2)} {f(W_VALLEY_L)} L{f(W_PEAK)} "
              f"L{f(mirror(W_VALLEY_L))} C{f(mirror(in2))} {f(mirror(in1))} {f(mirror(W_ARM_TL))} "
              f"L{f(mirror(W_OUT_TL))} C{f(mirror(out1))} {f(mirror(out2))} {f(mirror(W_BOT_L))} "
              f"C{f(mirror(bt1))} {f(mirror(bt2))} {f(W_BOT_C)} C{f(bt2)} {f(bt1)} {f(W_BOT_L)} "
              f"C{f(out2)} {f(out1)} {f(W_OUT_TL)} Z")
    d_path = f"M{f(D_TOP)} L{f(mirror(D_LEFT))} L{f(D_BOT)} L{f(D_LEFT)} Z"
    return t_path, w_path, d_path


def render(paths, scale, size=None):
    """Rasterise the SVG paths (cubic + line commands) to a float mask with 4x supersampling."""
    ss = 4
    Wd, Hd = size or (int(1000 * scale) + 2, int(1114.1 * scale) + 2)
    img = np.zeros((Hd * ss, Wd * ss), np.uint8)
    for d in paths:
        pts, cur = [], None
        toks = d.replace("M", " M ").replace("L", " L ").replace("C", " C ").replace("Z", " Z ").split()
        i = 0
        while i < len(toks):
            c = toks[i]
            if c in ("M", "L"):
                cur = np.array([float(v) for v in toks[i + 1].split(",")])
                pts.append(cur)
                i += 2
            elif c == "C":
                c1, c2, p3 = (np.array([float(v) for v in toks[i + k].split(",")]) for k in (1, 2, 3))
                for t in np.linspace(0, 1, 40)[1:]:
                    pts.append((1 - t) ** 3 * cur + 3 * t * (1 - t) ** 2 * c1 + 3 * t ** 2 * (1 - t) * c2 + t ** 3 * p3)
                cur = p3
                i += 4
            else:
                i += 1
        poly = np.round(np.array(pts) * scale * ss).astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(img, [poly], 255, cv2.LINE_AA)
    return cv2.resize(img, (Wd, Hd), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


def main():
    paths = build()
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1114.1" width="1000" height="1114">']
    for n, d in zip(("tw-t", "tw-w", "tw-diamond"), paths):
        svg.append(f'  <path id="{n}" d="{d}" fill="currentColor"/>')
    svg.append("</svg>")
    os.makedirs(os.path.join(ROOT, "design"), exist_ok=True)
    open(os.path.join(ROOT, "design/tw-mark.svg"), "w").write("\n".join(svg) + "\n")
    # check: the new mark (gold) over the original's trace (white), at 1.2 px per unit
    (t_c, w_c, d_c), s, (x0, y0) = traced()
    m = render(paths, 1.2)
    orig = np.zeros_like(m, np.uint8)
    for c in (t_c, w_c, d_c):
        cv2.fillPoly(orig, [np.round(c * 1.2).astype(np.int32).reshape(-1, 1, 2)], 255)
    vis = np.zeros((*m.shape, 3), np.uint8)
    vis[..., 2] = orig                                  # original in red
    vis[..., 1] = (m * 255).astype(np.uint8)            # new in green -> overlap reads yellow
    os.makedirs(os.path.join(ROOT, "renders/analysis"), exist_ok=True)
    cv2.imwrite(os.path.join(ROOT, "renders/analysis/logo_check.png"), vis)
    diff = np.abs((orig > 127).astype(float) - (m > 0.5).astype(float)).mean()
    print(f"design/tw-mark.svg written; pixel disagreement with the trace {diff * 100:.2f}%")


if __name__ == "__main__":
    main()
