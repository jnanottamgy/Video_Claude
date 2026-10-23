"""Build the private SFX library page (audition + backup) from library/sfx/manifest.json.

  python3 library/tools/build_sfx_page.py OUT_DIR

Writes OUT_DIR/index.html and OUT_DIR/sfx/<id>.wav (16-bit 48 kHz copies: they play in every
browser and restore with sample-exact timing, unlike MP3's encoder delay). Publish OUT_DIR/index.html
as an Artifact with files {"sfx/<id>.wav": ...} and {"manifest.json": ...}.
"""
import html
import json
import os
import subprocess
import sys

import numpy as np

LIB = os.path.join(os.path.dirname(__file__), "..", "sfx")
GROUPS = [
    ("Risers and build-ups", ["riser"], "Swell into a drop. Line up the end, or the peak, with the hit."),
    ("Whooshes", ["whoosh"], "Transitions, whips, zooms and text flying in. Line up the peak with the cut."),
    ("Impacts", ["impact"], "Drops, title slams, freeze frames, white flashes."),
    ("Slashes", ["slash"], "Fast cuts, wipes, text slicing in. Alternate the three on rapid cuts."),
    ("Glitch and time", ["glitch", "transition"], "Strobes, glitch frames, tape stops and slow motion."),
    ("Radio and foley", ["ui", "foley"], "Cues, channel switches and the reload before a reveal."),
    ("Ambience beds", ["ambience"], "Long loops to sit under a scene."),
]


def peaks(path, n=140):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32))
    edges = np.linspace(0, len(x), n + 1).astype(int)
    p = np.array([x[a:b].max() if b > a else 0 for a, b in zip(edges, edges[1:])])
    p = np.sqrt(p / max(p.max(), 1e-6))            # perceptual-ish scaling so quiet tails stay visible
    return [round(float(v), 3) for v in p]


def main():
    out = sys.argv[1]
    os.makedirs(os.path.join(out, "sfx"), exist_ok=True)
    man = json.load(open(os.path.join(LIB, "manifest.json")))
    items = []
    for s in man["sfx"]:
        src = os.path.join(LIB, s["file"])
        dst = os.path.join(out, "sfx", f"{s['id']}.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:a", "pcm_s16le", "-ar", "48000", dst], check=True)
        items.append(dict(id=s["id"], name=s["name"].split(" ", 1)[1] if s["name"].startswith("#") else s["name"],
                          num=s["name"].split(" ", 1)[0], cat=s["category"], dur=s["duration"], hit=s["hit_s"],
                          align=s["align"], desc=s["description"], wave=peaks(src)))
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    data = json.dumps(dict(items=items, groups=[dict(title=t, cats=c, note=n) for t, c, n in GROUPS]))
    tpl = open(os.path.join(os.path.dirname(__file__), "sfx_page_template.html"), encoding="utf-8").read()
    page = tpl.replace("/*DATA*/null", data).replace("<!--COUNT-->", str(len(items)))
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page)
    print(f"{len(items)} effects -> {out}")


if __name__ == "__main__":
    main()
