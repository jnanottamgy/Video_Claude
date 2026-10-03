"""Solve the handheld camera's motion through the clip, using the two walls.

Why not a free homography per wall: each wall's trackable points are few and
mostly collinear (pelmet / soffit edges), and an 8-DOF fit on them extrapolated
the sign area 87,000 px off-screen. Instead solve the CAMERA: 6 numbers per frame
(rotation + translation), constrained by every point on both walls at once.

Scene, in frame-0 camera coordinates, measured on frame 0 of the real clip:
  K          f = 1637 px (from the perpendicular walls' vanishing points), c = (540, 960)
  left wall  horizontals -> VP1 (1547, 1000); through the headboard edge, depth 1 (scale convention)
  back wall  horizontals -> VP2 (-2123, 1000); through the inner corner (x = 770), which is on the left wall

Tracked points are lifted to 3D on their wall. Per frame, robust least squares finds
(R_n, t_n) reprojecting them; lost tracks are re-seeded through the current pose.
A light temporal filter removes tracking jitter, then each wall's frame-0 -> frame-n
homography follows exactly:   H = K (R + t n^T / d) K^-1.

  python3 tools/solve_camera.py   ->  renders/real/camera.npz
"""
import subprocess

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation

SRC = "renders/real/source.MOV"
W, H = 1080, 1920
F, CX, CY = 1637.0, 540.0, 960.0
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.0]])
Ki = np.linalg.inv(K)
VP1, VP2, HORIZON = (1547.0, 1000.0), (-2123.0, 1000.0), 1000.0
CORNER_X = 770.0

ceil = lambda x: 0.4693 * x + 273.9        # left wall / ceiling junction
head = lambda x: -0.0711 * x + 1109.7      # headboard top edge
soffit = lambda x: -0.0354 * x + 591.6     # soffit underside, back-wall side

# Regions of each wall that are actually wall (frame-0 px). The fan, the legs, the person
# at the desk, the ceiling light and the soffit are not on either wall, so they're left out.
LEFT_POLY = [(0, ceil(0) + 18), (525, ceil(525) + 18), (560, 600), (CORNER_X - 8, 600),
             (CORNER_X - 8, 1080), (200, 1080), (200, head(200) + 6), (500, head(500) + 6), (500, 1110), (0, 1110)]
LEFT_CUT = [[(0, 940), (200, 940), (200, 1110), (0, 1110)]]                          # feet on the wall
BACK_POLY = [(CORNER_X + 8, soffit(CORNER_X) + 22), (1080, soffit(1080) + 22), (1080, 1040), (CORNER_X + 8, 1040)]
BACK_CUT = [[(840, 980), (1080, 980), (1080, 1040), (840, 1040)]]                    # top of the head


def wall(vp, through):
    h = Ki @ np.array([vp[0], vp[1], 1.0]); h /= np.linalg.norm(h)
    up = np.array([0.0, 1.0, 0.0]); v = up - h * (h @ up); v /= np.linalg.norm(v)
    n = np.cross(h, v); n /= np.linalg.norm(n)
    return n, float(n @ through)


def lift(px, n, d, R=np.eye(3), t=np.zeros(3)):
    """Back-project pixels seen by camera (R, t) onto plane n.X = d (frame-0 coords)."""
    c = -R.T @ t
    rays = (R.T @ (Ki @ np.c_[px, np.ones(len(px))].T)).T
    lam = (d - c @ n) / (rays @ n)
    return c + lam[:, None] * rays


headpt = Ki @ np.array([300.0, head(300.0), 1.0]); headpt /= headpt[2]
N_L, D_L = wall(VP1, headpt)
cornerpt = lift(np.array([[CORNER_X, 900.0]]), N_L, D_L)[0]
N_B, D_B = wall(VP2, cornerpt)
PLANES = {0: (N_L, D_L), 1: (N_B, D_B)}


def mask(poly, cuts, Hm=None):
    m = np.zeros((H, W), np.uint8)
    P = np.float32(poly).reshape(-1, 1, 2)
    if Hm is not None:
        P = cv2.perspectiveTransform(P, Hm)
    cv2.fillPoly(m, [np.int32(P)], 255)
    for c in cuts:
        C = np.float32(c).reshape(-1, 1, 2)
        if Hm is not None:
            C = cv2.perspectiveTransform(C, Hm)
        cv2.fillPoly(m, [np.int32(C)], 0)
    return m


def homography(R, t, plane):
    n, d = plane
    return K @ (R + np.outer(t, n) / d) @ Ki


def project(X, R, t):
    Y = (K @ (R @ X.T + t[:, None])).T
    return Y[:, :2] / Y[:, 2:3]


def frames():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(W * H)
        if len(buf) < W * H:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W)


def seed(img, lab, Hm, R, t, existing):
    poly, cuts = (LEFT_POLY, LEFT_CUT) if lab == 0 else (BACK_POLY, BACK_CUT)
    m = mask(poly, cuts, Hm)
    for p in existing:  # don't re-detect where we already track
        cv2.circle(m, (int(p[0]), int(p[1])), 12, 0, -1)
    pts = cv2.goodFeaturesToTrack(img, maxCorners=200, qualityLevel=0.004, minDistance=10, mask=m, blockSize=7)
    if pts is None:
        return np.zeros((0, 2), np.float32), np.zeros((0, 3))
    pts = cv2.cornerSubPix(img, pts, (5, 5), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.01)).reshape(-1, 2)
    return pts.astype(np.float32), lift(pts.astype(np.float64), *PLANES[lab], R, t)


def solve(X, x, p_init, lam_t=100.0):
    def res(p):
        R = Rotation.from_rotvec(p[:3]).as_matrix()
        return np.concatenate([(project(X, R, p[3:]) - x).ravel(), lam_t * p[3:]])
    return least_squares(res, p_init, loss="soft_l1", f_scale=1.5, x_scale=[1e-3] * 3 + [1e-3] * 3).x


def main():
    it = frames()
    prev = next(it)
    R0, t0 = np.eye(3), np.zeros(3)
    cur, X, lab = [], [], []
    for l in (0, 1):
        p, Xi = seed(prev, l, None, R0, t0, [])
        cur.append(p); X.append(Xi); lab += [l] * len(p)
    cur, X, lab = np.concatenate(cur), np.concatenate(X), np.array(lab)
    print(f"frame 0: seeded {np.sum(lab == 0)} left-wall + {np.sum(lab == 1)} back-wall points")
    poses, stats = [np.zeros(6)], [(0, int(np.sum(lab == 0)), int(np.sum(lab == 1)), 0.0, 0.0)]
    lk = dict(winSize=(25, 25), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    p_prev = np.zeros(6)
    for n, img in enumerate(it, start=1):
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, img, cur, None, **lk)
        bck, st2, _ = cv2.calcOpticalFlowPyrLK(img, prev, nxt, None, **lk)
        ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm(bck - cur, axis=1) < 1.0)
        cur, X, lab = nxt[ok], X[ok], lab[ok]
        p = solve(X, cur.astype(np.float64), p_prev)
        R, t = Rotation.from_rotvec(p[:3]).as_matrix(), p[3:]
        err = np.linalg.norm(project(X, R, t) - cur, axis=1)
        keep = err < 3.0                                  # drop tracks that slid off their feature
        cur, X, lab = cur[keep], X[keep], lab[keep]
        for l in (0, 1):                                   # top up thin walls through the current pose
            if np.sum(lab == l) < 30:
                pn, Xn = seed(img, l, homography(R, t, PLANES[l]), R, t, cur)
                cur = np.concatenate([cur, pn]); X = np.concatenate([X, Xn]); lab = np.concatenate([lab, [l] * len(pn)])
        rms = [float(np.sqrt(np.mean(err[keep][lab[:keep.sum()] == l] ** 2))) if np.any(lab[:keep.sum()] == l) else np.nan for l in (0, 1)]
        poses.append(p); stats.append((n, int(np.sum(lab == 0)), int(np.sum(lab == 1)), *rms))
        p_prev, prev = p, img
    poses, stats = np.array(poses), np.array(stats)
    smooth = savgol_filter(poses, window_length=7, polyorder=2, axis=0, mode="interp")
    HL = np.array([homography(Rotation.from_rotvec(s[:3]).as_matrix(), s[3:], PLANES[0]) for s in smooth])
    HB = np.array([homography(Rotation.from_rotvec(s[:3]).as_matrix(), s[3:], PLANES[1]) for s in smooth])
    np.savez("renders/real/camera.npz", poses=poses, smooth=smooth, H_left=HL, H_back=HB, stats=stats,
             K=K, N_L=N_L, D_L=D_L, N_B=N_B, D_B=D_B)
    ang = np.degrees(np.linalg.norm(smooth[:, :3], axis=1))
    print(f"frames solved: {len(poses)};  camera rotation up to {ang.max():.2f} deg;  "
          f"translation up to {np.linalg.norm(smooth[:, 3:], axis=1).max():.4f} (headboard-depth units)")
    for l, name in ((1, "left wall"), (2, "back wall")):
        print(f"  {name}: tracked points {int(stats[1:, l].min())}-{int(stats[1:, l].max())},  "
              f"reprojection RMS mean {np.nanmean(stats[1:, l + 2]):.2f}px  worst {np.nanmax(stats[1:, l + 2]):.2f}px")


if __name__ == "__main__":
    main()
