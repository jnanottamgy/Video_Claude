"""Reference stills of the OUTPUT timeline (ungraded source frames; black where a full-frame graphic plays).

  python3 tools/ref_frame.py T OUT.png          # one frame at output time T
  python3 tools/ref_frame.py --set              # the builders' set: renders/ref/out_<t>.png
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

os.chdir(edl.ROOT)


def frame(t, out):
    n = int(round(t * edl.FPS))
    f = edl.src_frame(n)
    if f is None:
        from PIL import Image
        Image.fromarray(np.zeros((edl.H, edl.W, 3), np.uint8)).save(out)
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(f + 0.25) / edl.FPS:.4f}", "-i", edl.SRC, "-frames:v", "1", out],
                   check=True)


if __name__ == "__main__":
    if sys.argv[1] == "--set":
        os.makedirs("renders/ref", exist_ok=True)
        ts = []
        for s in edl.SEGMENTS:
            if s["kind"] in ("talk", "freeze"):
                a, b = s["out0"], s["out1"]
                ts += [a + 0.05, (a + b) / 2, b - 0.06]
        for t in sorted(set(round(x, 2) for x in ts)):
            frame(t, f"renders/ref/out_{t:06.2f}.png")
        print(len(ts), "refs in renders/ref/")
    else:
        frame(float(sys.argv[1]), sys.argv[2])
