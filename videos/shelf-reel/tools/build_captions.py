"""Generate the captions overlay (HyperFrames projects) from renders/words.json.

Style: Sora 800, white with a crisp dark outline, one chunk at a time at y = 1375 (where the old
burned-in captions were, so the new ones also sit over the inpainted area). The word being
spoken lights up: amber while the student panics, S.H.E.L.F blue once the founders take over;
"SHELF" itself is always brand blue.

HyperFrames reserves ~8.3 MB of capture scratch per PNG frame, so the captions are split into
short windows around the speech (<= ~11 s each), one project per window:
  renders/captions/w00 ... wNN   (gitignored: they carry the dialogue)
  renders/captions/manifest.json [{dir, start_frame, frames}] -> read by the compositor

  python3 tools/build_captions.py && python3 tools/build_captions.py --render
"""
import html
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

ROOT = "renders/captions"
FPS = edl.FPS
FOUNDERS_AT = edl.BY_ID["P6a"]["o"] / FPS          # the turn: amber -> blue
TOTAL = edl.TOTAL / FPS
MAX_WIN, SPLIT_GAP = 11.0, 1.2

PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="./vendor/gsap.min.js"></script>
    <link rel="stylesheet" href="./design/shelf.css" />
    <style>
      #stage { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: transparent; }
      .scene { position: absolute; inset: 0; }
      .cap {
        position: absolute;
        left: 540px;
        top: 1375px;
        white-space: nowrap;
        font: 800 74px/1.1 var(--font-brand);
        letter-spacing: -0.01em;
        color: #ffffff;
        visibility: hidden;
        /* crisp outline (8 taps) + a soft lift off the footage */
        text-shadow:
          3px 0 0 #0b0d12, -3px 0 0 #0b0d12, 0 3px 0 #0b0d12, 0 -3px 0 #0b0d12,
          2px 2px 0 #0b0d12, -2px 2px 0 #0b0d12, 2px -2px 0 #0b0d12, -2px -2px 0 #0b0d12,
          0 8px 26px rgba(0, 0, 0, 0.55);
      }
      .w { display: inline-block; }
      .w.brand {
        color: #8fc7ff;
        text-shadow:
          3px 0 0 #07142b, -3px 0 0 #07142b, 0 3px 0 #07142b, 0 -3px 0 #07142b,
          2px 2px 0 #07142b, -2px 2px 0 #07142b, 2px -2px 0 #07142b, -2px -2px 0 #07142b,
          0 0 26px rgba(var(--glow), 0.85);
      }
    </style>
  </head>
  <body>
    <div id="stage" data-composition-id="main" data-start="0" data-duration="%(dur)s" data-width="1080" data-height="1920">
      <div id="scene" class="clip scene" data-start="0" data-duration="%(dur)s" data-track-index="0">
%(spans)s
      </div>
    </div>
    <script>
      var tl = gsap.timeline({ paused: true });
      gsap.set(".cap", { xPercent: -50, yPercent: -50 });
      // a chunk pops in (small rise + overshoot) and cuts out
      function chunk(sel, show, hide) {
        tl.set(sel, { visibility: "visible" }, show);
        tl.fromTo(sel, { scale: 0.82, y: 14 }, { scale: 1, y: 0, duration: 0.17, ease: "back.out(2.2)", immediateRender: false }, show);
        tl.set(sel, { visibility: "hidden" }, hide);
      }
      // the spoken word lights up and bumps, then hands the colour on
      function hl(sel, t0, t1, color) {
        tl.to(sel, { color: color, scale: 1.1, duration: 0.07, ease: "power2.out" }, t0);
        tl.to(sel, { scale: 1, duration: 0.2, ease: "power2.out" }, t0 + 0.07);
        tl.to(sel, { color: "#ffffff", duration: 0.08, ease: "power1.out" }, Math.max(t0 + 0.1, t1));
      }
      function pop(sel, t0) {
        tl.fromTo(sel, { scale: 1 }, { scale: 1.16, duration: 0.08, ease: "power2.out", immediateRender: false }, t0);
        tl.to(sel, { scale: 1, duration: 0.26, ease: "power2.out" }, t0 + 0.08);
      }
%(js)s
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def items():
    """(chunk, show, hide): each chunk shows from its first word until the next one appears or it ends,
    and stays inside its shot: no caption is carried across a cut unless the speech itself is."""
    import direction
    words = json.load(open("renders/words.json"))
    out = []
    for i, c in enumerate(words):
        nxt = words[i + 1]["t0"] if i + 1 < len(words) else TOTAL
        show, nxt_show = c["t0"] - 0.04, nxt - 0.04
        hide = nxt_show if nxt - c["t1"] < 0.35 else c["t1"] + 0.12
        hide = min(hide, nxt_show)                                          # never two chunks at once
        s0, s1 = next(((a, b) for a, b, *_ in direction.SHOTS if a <= c["t0"] + 0.01 < b), (0, TOTAL))
        show = max(show, s0)
        if c["t1"] <= s1 + 0.05:
            hide = min(hide, s1)
        out.append((c, round(show, 3), round(hide, 3)))
    return out


def windows(its):
    """Group chunks into windows split at pauses, none longer than MAX_WIN."""
    wins, cur = [], []
    for it in its:
        if cur and (it[1] - cur[-1][2] > SPLIT_GAP or it[2] - cur[0][1] > MAX_WIN):
            wins.append(cur)
            cur = []
        cur.append(it)
    return wins + [cur]


def write_project(d, its, w0, w1):
    os.makedirs(f"{d}/vendor", exist_ok=True)
    shutil.copy("slots/_template/vendor/gsap.min.js", f"{d}/vendor/gsap.min.js")
    for f in ("hyperframes.json", "meta.json", "package.json"):
        shutil.copy(f"slots/_template/{f}", f"{d}/{f}")
    if not os.path.islink(f"{d}/design"):
        os.symlink("../../../design", f"{d}/design")
    spans, js = [], []
    for k, (c, show, hide) in enumerate(its):
        accent = "var(--amber)" if c["t0"] < FOUNDERS_AT else "#62b4ff"
        js.append(f'chunk("#c{k}", {show - w0:.3f}, {hide - w0:.3f});')
        ws = []
        for j, w in enumerate(c["words"]):
            brand = "SHELF" in w["w"] or "S.H.E.L.F" in w["w"]
            ws.append(f'<span class="w{" brand" if brand else ""}" id="w{k}_{j}">{html.escape(w["w"])}</span>')
            if brand:
                js.append(f'pop("#w{k}_{j}", {w["t0"] - w0:.3f});')
            else:
                t1 = c["words"][j + 1]["t0"] if j + 1 < len(c["words"]) else hide
                js.append(f'hl("#w{k}_{j}", {w["t0"] - w0:.3f}, {t1 - w0:.3f}, "{accent}");')
        spans.append(f'        <div class="cap" id="c{k}">{" ".join(ws)}</div>')
    dur = f"{(w1 - w0):.4f}"
    page = PAGE % {"dur": dur, "spans": "\n".join(spans), "js": "\n".join("      " + j for j in js)}
    old = open(f"{d}/index.html").read() if os.path.exists(f"{d}/index.html") else None
    if page != old:                                    # changed: its old render is stale
        shutil.rmtree(f"{d}/renders/png", ignore_errors=True)
        open(f"{d}/index.html", "w").write(page)


def build():
    its = items()
    manifest = []
    for k, win in enumerate(windows(its)):
        f0 = int(win[0][1] * FPS) - 2                      # frame-aligned window with a little slack
        f1 = int(win[-1][2] * FPS + 0.999) + 2
        d = f"{ROOT}/w{k:02d}"
        write_project(d, win, f0 / FPS, f1 / FPS)
        manifest.append({"dir": d, "start_frame": f0, "frames": f1 - f0})
        print(f"{d}: frames {f0}-{f1} ({(f1 - f0) / FPS:.2f}s), {len(win)} chunks")
    json.dump(manifest, open(f"{ROOT}/manifest.json", "w"), indent=1)


def render():
    for m in json.load(open(f"{ROOT}/manifest.json")):
        png = f"{m['dir']}/renders/png"
        if os.path.isdir(png) and len(os.listdir(png)) == m["frames"]:
            continue
        shutil.rmtree(png, ignore_errors=True)
        subprocess.run(["npx", "--yes", "hyperframes@0.8.114", "render", ".", "--format", "png-sequence", "-q", "high",
                        "-o", "./renders/png", "--quiet"], cwd=m["dir"], check=True)
        n = len(os.listdir(png))
        print(f"{m['dir']}: {n} frames (want {m['frames']})", flush=True)
        for w in os.listdir(f"{m['dir']}/renders"):
            if w.startswith("work-"):
                shutil.rmtree(f"{m['dir']}/renders/{w}", ignore_errors=True)


if __name__ == "__main__":
    render() if "--render" in sys.argv else build()
