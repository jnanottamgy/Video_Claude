"""Minimal TopoJSON decoding + equirectangular rasterising (numpy/cv2), for build_geo.py."""
import json
import numpy as np
import cv2


def load(path):
    with open(path) as f:
        return json.load(f)


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        a = np.cumsum(np.array(arc, dtype=np.float64), axis=0)
        a[:, 0] = a[:, 0] * sx + tx
        a[:, 1] = a[:, 1] * sy + ty
        out.append(a)
    return out


def ring(ids, arcs):
    pts = []
    for i in ids:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.append(a if not pts else a[1:])
    return np.concatenate(pts, axis=0)


def polygons(geom, arcs):
    """-> list of polygons, each a list of rings (lon/lat arrays)."""
    t = geom["type"]
    if t == "Polygon":
        return [[ring(r, arcs) for r in geom["arcs"]]]
    if t == "MultiPolygon":
        return [[ring(r, arcs) for r in p] for p in geom["arcs"]]
    if t == "GeometryCollection":
        out = []
        for g in geom["geometries"]:
            out += polygons(g, arcs)
        return out
    return []


def unwrap(r):
    """Make a ring continuous in longitude (rings crossing the antimeridian jump by ~360).
    A ring that winds round a pole (Antarctica) is closed down to that pole."""
    lon = np.degrees(np.unwrap(np.radians(r[:, 0])))
    out = np.c_[lon, r[:, 1]]
    d = lon[-1] - lon[0]
    if abs(d) > 180:  # encircles a pole
        pole = -90.0 if r[:, 1].mean() < 0 else 90.0
        out = np.vstack([out, [[lon[-1], pole], [lon[0], pole]]])
    return out


def raster(polys, lon0, lat1, ppd, w, h):
    """Fill polygons (even-odd per polygon) into a uint8 mask. Window: x=(lon-lon0)*ppd, y=(lat1-lat)*ppd."""
    m = np.zeros((h, w), np.uint8)
    for p in polys:
        tmp = np.zeros((h, w), np.uint8)
        rings = [unwrap(r) for r in p]
        for shift in (-360.0, 0.0, 360.0):
            cs = []
            for r in rings:
                xy = np.empty_like(r)
                xy[:, 0] = (r[:, 0] + shift - lon0) * ppd
                xy[:, 1] = (lat1 - r[:, 1]) * ppd
                cs.append(np.round(xy * 16).astype(np.int32))
            if any((c[:, 0].max() >= 0 and c[:, 0].min() < w * 16) for c in cs):
                cv2.fillPoly(tmp, cs, 255, lineType=cv2.LINE_8, shift=4)
        m |= tmp
    return m
