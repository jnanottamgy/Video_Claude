"""Build assets/globe-data.js for the globe slot (run from slots/globe/tools: python3 build_geo.py [preview_dir]).

- Land dot matrix: rows of equal angular spacing on the sphere (STEP deg), each dot keeps its land coverage
  (fraction of its cell that is land, from a 20 px/deg equirectangular raster of Natural Earth land-50m).
- India: the official outline (Survey of India view), i.e. the de facto India polygon plus Siachen, plus the
  parts of Jammu & Kashmir and Ladakh held by Pakistan (Gilgit-Baltistan, AJK) and by China (Aksai Chin and
  the Shaksgam tract). The world-atlas data is de facto, so these are added with two hand-made envelopes:
    W: Pakistan-held J&K, bounded on the west by the old J&K / Punjab / KPK boundary;
    E: China-held areas, bounded by India's claim line (Shaksgam north edge, the Kunlun line round Aksai Chin).
  official = India | Siachen | (Pakistan & W) | (China & E)
"""
import base64
import json
import sys
import numpy as np
import cv2
import topo

STEP = 0.55

land_topo = topo.load("../assets/land-50m.json")
la = topo.decode_arcs(land_topo)
land_polys = topo.polygons(land_topo["objects"]["land"], la)

ctopo = topo.load("../assets/countries-50m.json")
ca = topo.decode_arcs(ctopo)
G = {g.get("properties", {}).get("name"): g for g in ctopo["objects"]["countries"]["geometries"]}

# ---------------------------------------------------------------- land raster + dots
S = 20
W, H = 360 * S, 180 * S
landm = topo.raster(land_polys, -180, 90, S, W, H)
ii = cv2.integral((landm > 0).astype(np.uint8))  # (H+1, W+1)


def cover(lon, lat, dlon, dlat):
    x0 = int(np.clip(np.floor((lon - dlon / 2 + 180) * S), 0, W - 1))
    x1 = int(np.clip(np.ceil((lon + dlon / 2 + 180) * S), x0 + 1, W))
    y0 = int(np.clip(np.floor((90 - lat - dlat / 2) * S), 0, H - 1))
    y1 = int(np.clip(np.ceil((90 - lat + dlat / 2) * S), y0 + 1, H))
    s = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
    return s / float((x1 - x0) * (y1 - y0))


dots = []
nrows = int(round(180 / STEP))
for i in range(nrows):
    lat = -90 + (i + 0.5) * 180 / nrows
    n = max(1, int(round(360 * np.cos(np.radians(lat)) / STEP)))
    dl = 360.0 / n
    off = 0.5 * dl * (i % 2)  # alternate rows offset: halftone packing
    for j in range(n):
        lon = -180 + (j + 0.5) * dl + off
        if lon > 180:
            lon -= 360
        c = cover(lon, lat, dl, 180 / nrows)
        if c >= 0.22:
            dots.append((lon, lat, c))

# ---------------------------------------------------------------- official India mask (lon 60-100, lat 0-40)
SI = 40
LON0, LAT1 = 60.0, 40.0
WI, HI = 40 * SI, 40 * SI


def mask(name):
    return topo.raster(topo.polygons(G[name], ca), LON0, LAT1, SI, WI, HI) > 0


def poly_mask(pts):
    a = np.array(pts, dtype=np.float64)
    return topo.raster([[a]], LON0, LAT1, SI, WI, HI) > 0


ENV_W = [  # Pakistan-held J&K (AJK + Gilgit-Baltistan). West edge = old J&K boundary, south -> north.
    (74.68, 32.66), (74.40, 32.70), (74.15, 32.75), (73.95, 32.88), (73.75, 33.02), (73.63, 33.13),
    (73.62, 33.35), (73.58, 33.55), (73.52, 33.78), (73.47, 34.02), (73.42, 34.25), (73.42, 34.40),
    (73.50, 34.55), (73.62, 34.70), (73.80, 34.85), (73.95, 35.00), (74.02, 35.12), (73.85, 35.25),
    (73.60, 35.33), (73.35, 35.45), (73.12, 35.62), (72.90, 35.82), (72.60, 35.98), (72.53, 36.08),
    (72.62, 36.30), (72.90, 36.52), (73.20, 36.70), (73.50, 36.85), (73.70, 36.92),
    (73.70, 37.90), (79.50, 37.90), (79.50, 32.66),
]
ENV_E = [  # China-held: Shaksgam tract + Aksai Chin. Claim line west -> east, then back through India.
    (75.30, 36.30), (75.70, 36.71), (76.10, 36.62), (76.50, 36.45), (76.90, 36.25), (77.30, 36.05),
    (77.70, 35.92), (78.10, 35.98), (78.60, 36.05), (79.20, 36.00), (79.70, 35.90), (80.15, 35.70),
    (80.30, 35.35), (80.25, 35.00), (80.10, 34.70), (79.80, 34.50), (79.45, 34.35), (78.95, 34.35),
    (78.20, 34.40), (77.20, 34.80), (76.00, 35.40),
]
official = mask("India") | mask("Siachen Glacier") | (mask("Pakistan") & poly_mask(ENV_W)) | (mask("China") & poly_mask(ENV_E))
om = official.astype(np.uint8) * 255
om = cv2.morphologyEx(om, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

cs, _ = cv2.findContours(om, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
rings = []
for c in cs:
    area = cv2.contourArea(c) / (SI * SI)  # deg^2
    if area < 0.012:
        continue
    eps = 0.035 * SI if area > 50 else 0.02 * SI
    a = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(np.float64)
    lon = LON0 + (a[:, 0] + 0.5) / SI
    lat = LAT1 - (a[:, 1] + 0.5) / SI
    rings.append((area, [round(float(v), 3) for p in zip(lon, lat) for v in p]))
rings.sort(key=lambda r: -r[0])


def in_official(lon, lat):
    x = int((lon - LON0) * SI)
    y = int((LAT1 - lat) * SI)
    return 1 if (0 <= x < WI and 0 <= y < HI and official[y, x]) else 0


# ---------------------------------------------------------------- write
arr = np.array([(round(d[0] * 100), round(d[1] * 100)) for d in dots], dtype=np.int16).ravel()
cov = np.array([min(255, int(round(d[2] * 255))) for d in dots], dtype=np.uint8)
ind = np.array([in_official(d[0], d[1]) for d in dots], dtype=np.uint8)
b64 = lambda a: base64.b64encode(a.tobytes()).decode()
data = {
    "step": STEP,
    "n": len(dots),
    "ll": b64(arr),
    "cov": b64(cov),
    "ind": b64(ind),
    "india": [r[1] for r in rings],
}
with open("../assets/globe-data.js", "w") as f:
    f.write("/* generated by tools/build_geo.py from Natural Earth (world-atlas, see LICENSE-world-atlas) */\n")
    f.write("window.GLOBE_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
print("dots", len(dots), "india dots", int(ind.sum()), "rings", [(round(r[0], 3), len(r[1]) // 2) for r in rings])

# ---------------------------------------------------------------- previews
if len(sys.argv) > 1:
    out = sys.argv[1]
    small = cv2.resize(landm, (1440, 720), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out + "/land_world.png", small)
    prev = np.zeros((HI, WI, 3), np.uint8)
    prev[mask("India")] = (60, 120, 200)
    prev[official & ~mask("India")] = (40, 200, 240)
    for c in cs:
        if cv2.contourArea(c) / (SI * SI) >= 0.012:
            cv2.drawContours(prev, [c], -1, (255, 255, 255), 2)
    for (lon, lat) in [(77.59, 12.97), (80.27, 13.08)]:
        cv2.circle(prev, (int((lon - LON0) * SI), int((LAT1 - lat) * SI)), 8, (0, 0, 255), -1)
    cv2.imwrite(out + "/india_official.png", cv2.resize(prev, (800, 800), interpolation=cv2.INTER_AREA))
