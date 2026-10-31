"""Word-level timings for HK Vinay's lines (Silero VAD + NeMo Parakeet TDT 0.6b v2 via sherpa-onnx, offline).

Silero finds the speech regions; each is decoded on its own (padded 0.4 s) so timestamps stay tight. A word
ends where the next starts (minus a hair); the last word of a region ~0.35 s after its start.
  python3 tools/words.py  ->  renders/analysis/words.json  [{region, text, words: [{w, s, e}]}]
"""
import json
import os
import subprocess

import numpy as np
import sherpa_onnx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = "/root/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
VAD = "/root/asr-models/silero_vad.onnx"
SRC = os.path.join(ROOT, "renders/src/drive/reel_original.mp4")
SR = 16000


def audio():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def regions(x):
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = VAD
    cfg.silero_vad.threshold = 0.4
    cfg.silero_vad.min_silence_duration = 0.35
    cfg.silero_vad.min_speech_duration = 0.2
    cfg.silero_vad.max_speech_duration = 12
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    win = cfg.silero_vad.window_size
    out = []
    for i in range(0, len(x) - win, win):
        vad.accept_waveform(x[i:i + win])
        while not vad.empty():
            seg = vad.front
            out.append((seg.start / SR, seg.start / SR + len(seg.samples) / SR))
            vad.pop()
    vad.flush()
    while not vad.empty():
        seg = vad.front
        out.append((seg.start / SR, seg.start / SR + len(seg.samples) / SR))
        vad.pop()
    return out


def main():
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{M}/encoder.int8.onnx", decoder=f"{M}/decoder.int8.onnx", joiner=f"{M}/joiner.int8.onnx",
        tokens=f"{M}/tokens.txt", num_threads=4, model_type="nemo_transducer")
    x = audio()
    out = []
    for a, b in regions(x):
        a, b = max(0.0, a - 0.15), min(len(x) / SR, b + 0.15)
        seg = x[int(a * SR):int(b * SR)]
        seg = np.concatenate([np.zeros(int(0.4 * SR), np.float32), seg, np.zeros(int(0.4 * SR), np.float32)])
        s = rec.create_stream()
        s.accept_waveform(SR, seg)
        rec.decode_stream(s)
        r = s.result
        words = []
        for tok, t in zip(list(r.tokens), list(r.timestamps)):
            t = round(a + t - 0.4, 3)
            if tok.startswith("▁") or tok.startswith(" ") or not words:
                words.append({"w": tok.lstrip("▁ "), "s": t, "e": None})
            else:
                words[-1]["w"] += tok
        for i, w in enumerate(words):
            nxt = words[i + 1]["s"] if i + 1 < len(words) else None
            w["e"] = round(min(nxt - 0.02, w["s"] + 0.6) if nxt else w["s"] + 0.35, 3)
        out.append({"region": [round(a, 3), round(b, 3)], "text": r.text.strip(), "words": words})
        print(f"{a:6.2f}-{b:6.2f}  {r.text.strip()}")
        print("            " + "  ".join(f"{w['w']}@{w['s']:.2f}" for w in words))
    os.makedirs(os.path.join(ROOT, "renders/analysis"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "renders/analysis/words.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
