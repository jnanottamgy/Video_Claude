"""Word timings on the OUTPUT timeline, for captions and every synced graphic.

Inputs (both gitignored, derived from the footage):
  renders/captions_raw.json   caption chunks found by read_captions.py (frame ranges)
  renders/transcript.json     the text of each chunk, read off the frames, lightly cleaned
  renders/speech_env_db.npy   1-4 kHz speech envelope (10 ms hops), for onset refinement
Output:
  renders/words.json   [{chunk, text, words:[{w, t0, t1}], t0, t1, seg}] in output seconds.
                       A line inside the hook appears twice (hook + its place in the story).

  python3 tools/beats.py
"""
import json
import numpy as np
import edl

caps = json.load(open("renders/captions_raw.json"))
text = json.load(open("renders/transcript.json"))
db = np.load("renders/speech_env_db.npy")
flux = np.maximum(np.diff(db, prepend=db[0]), 0)
loud = db > np.percentile(db, 40)


def onset(t, win=0.22):
    """The strongest speech onset within `win` s of caption time `t` (captions lead speech by ~0.1 s)."""
    i0, i1 = int((t - win) * 100), int((t + win) * 100)
    k = flux[i0:i1] * loud[i0:i1]
    return (i0 + int(np.argmax(k))) / 100 if k.max() > 0 else t


def syllables(w):
    w = w.lower().strip(".,?!'")
    groups = sum(1 for i, c in enumerate(w) if c in "aeiouy" and (i == 0 or w[i - 1] not in "aeiouy"))
    return max(1, groups) + (2 if w.replace(".", "") == "shelf" and "." in w else 0)


# A chunk starts at its speech onset, unless that would run it into the previous chunk
# (back-to-back chunks share one onset); it ends where the next one starts, if they touch.
starts = []
for i, c in enumerate(caps):
    t0 = onset(c["t0"])
    if not (c["t0"] - 0.15 <= t0 <= c["t0"] + 0.22) or (starts and t0 < starts[-1] + 0.2):
        t0 = max(c["t0"], starts[-1] + 0.2) if starts else c["t0"]
    starts.append(t0)
chunks = []
for i, c in enumerate(caps):
    t0 = starts[i]
    touching = i + 1 < len(caps) and caps[i + 1]["t0"] - c["t1"] < 0.15
    t1 = max(starts[i + 1] if touching else c["t1"], t0 + 0.12)
    words = text[str(i)].split()
    wts = np.array([syllables(w) for w in words], float)
    edges = t0 + (min(t1, c["t1"]) - t0) * np.concatenate([[0], np.cumsum(wts) / wts.sum()])
    chunks.append({"chunk": i, "text": text[str(i)], "src_t0": t0, "src_t1": t1,
                   "words": [{"w": w, "src_t0": float(a), "src_t1": float(b)} for w, a, b in zip(words, edges[:-1], edges[1:])]})

out = []
for c in chunks:
    for s in edl.LAYOUT:
        if s["kind"] != "cut" or s.get("speed", 1.0) != 1.0 or s["audio"] != "orig":
            continue
        a, b = s["a"] / edl.FPS, s["b"] / edl.FPS
        if a - 0.05 <= c["src_t0"] < b:
            o = lambda t: round(edl.out_time(min(max(t, a), b), s["id"]), 3)
            out.append({"chunk": c["chunk"], "seg": s["id"], "text": c["text"], "t0": o(c["src_t0"]), "t1": o(c["src_t1"]),
                        "words": [{"w": w["w"], "t0": o(w["src_t0"]), "t1": o(w["src_t1"])} for w in c["words"]]})
out.sort(key=lambda r: r["t0"])
json.dump(out, open("renders/words.json", "w"), indent=1)
for r in out:
    print(f"{r['t0']:7.2f}-{r['t1']:7.2f}  {r['seg']:5s} #{r['chunk']:<2d} {r['text']}")
