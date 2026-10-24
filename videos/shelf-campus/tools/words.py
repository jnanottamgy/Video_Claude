"""Word-level timings for the founders reel (NeMo Parakeet TDT 0.6b v2 via sherpa-onnx, offline).

Whisper (videos/cr-aura/tools/transcribe.py) gave the lines; Parakeet gives every word's start and,
from the next token, its end. Each line is decoded on its own (padded 0.4 s) so timestamps stay tight.
  python3 tools/words.py  ->  renders/analysis/words.json  [{line, words: [{w, s, e}]}]
"""
import json
import subprocess

import numpy as np
import sherpa_onnx

M = "/root/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
SRC = "renders/src/founders_reel_original.mp4"
SR = 16000
# speech regions (s): Whisper's lines plus the one it missed (31-35: "your AI-powered academic memory")
REGIONS = [(0.30, 3.30), (3.90, 6.60), (6.90, 9.95), (9.95, 11.90), (12.4, 15.3), (15.4, 17.6), (17.9, 20.2),
           (20.4, 24.5), (24.9, 27.6), (28.2, 31.0), (31.0, 34.2), (34.2, 37.5), (38.2, 41.0), (41.6, 44.4),
           (45.4, 48.3), (48.9, 51.5), (51.8, 54.7), (55.1, 57.6), (57.8, 59.7), (59.8, 62.5), (62.6, 65.4),
           (65.5, 69.4), (69.5, 72.16)]


def audio():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main():
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{M}/encoder.int8.onnx", decoder=f"{M}/decoder.int8.onnx", joiner=f"{M}/joiner.int8.onnx",
        tokens=f"{M}/tokens.txt", num_threads=4, model_type="nemo_transducer")
    x = audio()
    out = []
    for a, b in REGIONS:
        seg = x[int(a * SR):int(b * SR)]
        seg = np.concatenate([np.zeros(int(0.4 * SR), np.float32), seg, np.zeros(int(0.4 * SR), np.float32)])
        s = rec.create_stream()
        s.accept_waveform(SR, seg)
        rec.decode_stream(s)
        r = s.result
        toks, ts = list(r.tokens), list(r.timestamps)
        words = []
        for tok, t in zip(toks, ts):
            t = round(a + t - 0.4, 3)
            if tok.startswith("▁") or tok.startswith(" ") or not words:
                words.append({"w": tok.lstrip("▁ "), "s": t, "e": None})
            else:
                words[-1]["w"] += tok
        # a word ends where the next starts (minus a hair), the last one ~0.3 s after it starts
        for i, w in enumerate(words):
            nxt = words[i + 1]["s"] if i + 1 < len(words) else None
            w["e"] = round(min(nxt - 0.02, w["s"] + 0.6) if nxt else w["s"] + 0.35, 3)
        out.append({"region": [a, b], "text": r.text.strip(), "words": words})
        print(f"{a:6.2f}-{b:6.2f}  {r.text.strip()}")
        print("            " + "  ".join(f"{w['w']}@{w['s']:.2f}" for w in words))
    json.dump(out, open("renders/analysis/words.json", "w"), indent=1)


if __name__ == "__main__":
    main()
