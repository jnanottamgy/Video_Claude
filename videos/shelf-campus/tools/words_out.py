"""Word timings on the OUTPUT timeline (for captions and for the builders' cue sheets).

Parakeet (tools/words.py) gives word starts quantised to 80 ms; each line's first word is pulled to the
measured speech onset. Writes renders/words_out.json: [{seg, who, text, words: [{w, t0, t1}]}].
  python3 tools/words_out.py [--print]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import edl  # noqa: E402

os.chdir(edl.ROOT)
WORDS = json.load(open("renders/analysis/words.json"))
# measured speech onsets (src s) where Parakeet's first token is early
ONSET = {0.30: 0.47, 3.90: 4.32, 6.90: 7.14, 9.95: 10.13, 12.40: 12.99, 15.40: 15.77, 17.90: 18.24, 20.40: 20.53, 24.90: 25.25,
         28.20: 28.69, 31.00: 31.16, 34.20: 35.43, 38.20: 38.45, 41.60: 41.96, 45.40: 45.82, 48.90: 49.37,
         51.80: 52.33, 55.10: 55.60, 57.80: 58.22, 59.80: 60.14, 62.60: 62.95, 69.50: 69.57}


def src_words(s0, s1):
    out = []
    for r in WORDS:
        ws = [dict(w) for w in r["words"]]
        if r["region"][0] in ONSET and ws:
            ws[0]["s"] = max(ws[0]["s"], ONSET[r["region"][0]])
        for w in ws:
            if s0 - 0.05 <= w["s"] < s1:
                out.append(w)
    return out


def main():
    lines = []
    for s in edl.SEGMENTS:
        pieces = []
        if s["kind"] == "talk":
            pieces.append((s["src"], s["src"] + s["out1"] - s["out0"], s["out0"], s["who"], s["id"]))
        for v in s.get("vo", []):
            pieces.append((v["src0"], v["src1"], v["out0"], v.get("who", "VO"), s["id"]))
        for a, b, o, who, sid in pieces:
            ws = src_words(a, b)
            words = []
            for i, w in enumerate(ws):
                t0 = o + w["s"] - a
                t1 = o + (ws[i + 1]["s"] - a if i + 1 < len(ws) else min(w["e"], b) - a)
                words.append(dict(w=w["w"], t0=round(t0, 3), t1=round(min(t1, t0 + 0.75), 3)))
            lines.append(dict(seg=sid, who=who, words=words, text=" ".join(w["w"] for w in words)))
    json.dump(lines, open("renders/words_out.json", "w"), indent=1)
    if "--print" in sys.argv:
        for l in lines:
            print(f"{l['seg']:4s} {l['who']:2s} " + "  ".join(f"{w['w']}@{w['t0']:.2f}" for w in l["words"]))


if __name__ == "__main__":
    main()
