"""The client's event footage: listing, probing and decoding with HDR tone mapping.

Most clips are iPhone 4K HEVC in HLG HDR (BT.2020, arib-std-b67); a few are SDR H.264. Every clip is
portrait (rotation metadata; ffmpeg auto-rotates). Frames come out as SDR BT.709 RGB.
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "renders/src/drive")
# HLG -> linear light -> BT.709 primaries -> tone map (hable, keeps highlights soft) -> BT.709 gamma
TONEMAP_HLG = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
               "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def clips():
    return sorted(f for f in os.listdir(SRC) if f.lower().endswith(".mov"))


_probe = {}


def probe(name):
    if name not in _probe:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height,color_transfer,codec_name:format=duration", "-of", "json",
                              os.path.join(SRC, name)], capture_output=True, text=True, check=True).stdout
        j = json.loads(out)
        s = j["streams"][0]
        _probe[name] = dict(hdr=s.get("color_transfer") == "arib-std-b67", duration=float(j["format"]["duration"]),
                            w=s["width"], h=s["height"])
    return _probe[name]


def vf(name, extra=""):
    """The decode filter chain for a clip: tone map (if HDR), then `extra`."""
    chain = TONEMAP_HLG if probe(name)["hdr"] else "format=yuv420p"
    return chain + ("," + extra if extra else "")


def frame(name, t, w=1080):
    """One SDR RGB frame (uint8, portrait, `w` wide) at time t."""
    import numpy as np
    p = probe(name)
    h = int(round(w * max(p["w"], p["h"]) / min(p["w"], p["h"]) / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", os.path.join(SRC, name), "-frames:v", "1",
                          "-vf", vf(name, f"scale={w}:{h}:flags=lanczos"), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)
