"""The editing SFX library: look effects up, load them, and place them by their hit point.

  python3 library/tools/sfx.py list [category]     # what is in the library
  python3 library/tools/sfx.py check               # which audio files are missing (after a fresh container)
  python3 library/tools/sfx.py restore DIR         # copy files fetched from the backup artifact into place

In a mix script:

  sys.path.insert(0, "/home/user/Video_Claude/library/tools"); import sfx
  sfx.place(buf, "bass-woosh-1", t_drop, gain_db=-10)      # its burst lands exactly on t_drop
  sfx.place(buf, "build-up-3", t_drop, gain_db=-14)        # its climax lands on t_drop

Every entry in library/sfx/manifest.json has hit_s: the moment inside the file that belongs on
the event (an impact's transient, a whoosh's peak, a riser's end). place() starts the file at
event_time - hit_s. The audio is gitignored (a third-party pack in a public repo); the backup is the
private artifact in BACKUP below, restored with the Artifact tool (see library/README.md).
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np

LIB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "sfx"))
SR = 48000
BACKUP = "https://claude.ai/artifact/PQbmuZcLGS5irz7F8AVH9n"     # private page holding sfx/<id>.wav copies


def manifest():
    return json.load(open(os.path.join(LIB, "manifest.json")))["sfx"]


def entry(sfx_id):
    for s in manifest():
        if s["id"] == sfx_id:
            return s
    raise KeyError(f"no effect '{sfx_id}' in the library (python3 library/tools/sfx.py list)")


def find(category=None, text=None):
    out = manifest()
    if category:
        out = [s for s in out if s["category"] == category]
    if text:
        t = text.lower()
        out = [s for s in out if t in s["id"] or t in s["description"].lower()]
    return out


def path(sfx_id):
    return os.path.join(LIB, entry(sfx_id)["file"])


def load(sfx_id, sr=SR):
    """(stereo float64 array, hit_s) at sample rate sr."""
    p = path(sfx_id)
    if not os.path.exists(p):
        raise FileNotFoundError(f"{p} is missing: restore the library from {BACKUP} (library/README.md)")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64), entry(sfx_id)["hit_s"]


def place(buf, sfx_id, event_time, gain_db=0.0, sr=SR, length=None, fade_out=0.05):
    """Mix an effect into buf (N x 2) so its hit point lands on event_time.
    length trims the effect to that many seconds after its start (with a fade_out)."""
    x, hit = load(sfx_id, sr)
    if length is not None:
        x = x[: int(length * sr)].copy()
        n = min(len(x), int(fade_out * sr))
        if n:
            x[-n:] *= np.linspace(1, 0, n)[:, None]
    i = int(round((event_time - hit) * sr))
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[: j - i] * 10 ** (gain_db / 20)
    return buf


def missing():
    return [s["id"] for s in manifest() if not os.path.exists(os.path.join(LIB, s["file"]))]


def restore(src_dir):
    """Copy <src_dir>/sfx/<id>.wav (as fetched from the backup artifact) into the library."""
    n = 0
    for s in manifest():
        src = os.path.join(src_dir, "sfx", f"{s['id']}.wav")
        if os.path.exists(src):
            dst = os.path.join(LIB, s["file"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            n += 1
    return n


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for s in find(sys.argv[2] if len(sys.argv) > 2 else None):
            ok = "" if os.path.exists(os.path.join(LIB, s["file"])) else "  (missing)"
            print(f"{s['id']:24s} {s['category']:10s} {s['duration']:5.2f}s  hit {s['hit_s']:5.2f} ({s['align']})  {s['description']}{ok}")
    elif cmd == "check":
        m = missing()
        print("all present" if not m else f"{len(m)} missing; fetch with the Artifact tool: read url={BACKUP} paths=" +
              json.dumps([f"sfx/{i}.wav" for i in m]) + ", then: python3 library/tools/sfx.py restore <out_dir>")
    elif cmd == "restore":
        print(restore(sys.argv[2]), "files restored into", LIB)
    else:
        sys.exit(__doc__)
