"""Rough word timing for the edit audio (offline): Parakeet TDT for timed tokens, Whisper medium.en for a second
reading of the text. Music under rap makes both approximate; the result guides where words land, nothing more.
  python3 tools/lyrics_asr.py renders/audio/dna.wav  ->  renders/analysis/audio/asr.json"""
import json, sys
import numpy as np, soundfile as sf, librosa, sherpa_onnx

x, sr = sf.read(sys.argv[1], always_2d=True)
m = librosa.resample(x.mean(1).astype(np.float32), orig_sr=sr, target_sr=16000)
P = "/root/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f"{P}/encoder.int8.onnx", decoder=f"{P}/decoder.int8.onnx",
    joiner=f"{P}/joiner.int8.onnx", tokens=f"{P}/tokens.txt", num_threads=4, model_type="nemo_transducer")
out = {"parakeet": [], "whisper": []}
# 10 s windows with 2 s overlap keep the transducer in its comfort zone
for a in np.arange(0, len(m) / 16000, 8.0):
    seg = m[int(a * 16000): int((a + 10) * 16000)]
    s = rec.create_stream(); s.accept_waveform(16000, seg); rec.decode_stream(s)
    r = s.result
    toks = [(t, round(a + ts, 2)) for t, ts in zip(r.tokens, r.timestamps)]
    out["parakeet"].append({"t0": float(a), "text": r.text, "tokens": toks})
    print(f"[parakeet {a:4.1f}] {r.text}")
W = "/root/asr-models/sherpa-onnx-whisper-medium.en"
wr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f"{W}/medium.en-encoder.int8.onnx", decoder=f"{W}/medium.en-decoder.int8.onnx",
    tokens=f"{W}/medium.en-tokens.txt", num_threads=4)
for a in np.arange(0, len(m) / 16000, 5.0):
    seg = m[int(a * 16000): int((a + 6) * 16000)]
    s = wr.create_stream(); s.accept_waveform(16000, seg); wr.decode_stream(s)
    out["whisper"].append({"t0": float(a), "text": s.result.text})
    print(f"[whisper {a:4.1f}] {s.result.text}")
json.dump(out, open("renders/analysis/audio/asr.json", "w"), indent=1)
