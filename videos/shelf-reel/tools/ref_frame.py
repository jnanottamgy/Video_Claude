"""Reference frames for slot authors: the footage frame shown at OUTPUT time t (old captions still burned in).

  python3 tools/ref_frame.py 54.5 renders/ref/out_54.50.png
"""
import subprocess, sys
import edl

t, dest = float(sys.argv[1]), sys.argv[2]
seg, f, _ = edl.src_frame(int(round(t * edl.FPS)))
f = int(round(f if f is not None else seg["a"]))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, f - 0.01) / edl.FPS:.6f}", "-i", "renders/source.mp4", "-vframes", "1", dest],
               check=True)   # a hair before frame f: lands exactly on f (see composite.Source._open)
print(f"out {t:.2f}s = {seg['id']} src frame {f} ({f / edl.FPS:.2f}s) -> {dest}")
