"""Local speech-to-text: Silero VAD segments + Whisper large-v3-turbo (sherpa-onnx, int8, CPU).

  python3 tools/transcribe.py renders/analysis/audio.wav renders/analysis/transcript.json [--task translate]

Free and offline once the models are in /root/asr-models (fetched from the k2-fsa GitHub releases;
the usual Whisper/Hugging Face hosts are blocked here). Writes [{start, end, text, lang}] per segment.
"""
import argparse
import json
import subprocess

import numpy as np
import sherpa_onnx

M = "/root/asr-models"
SR = 16000


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def segments(x, min_silence=0.25):
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = f"{M}/silero_vad.onnx"
    cfg.silero_vad.min_silence_duration = min_silence
    cfg.silero_vad.min_speech_duration = 0.2
    cfg.silero_vad.max_speech_duration = 20
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    win = cfg.silero_vad.window_size
    out = []
    for i in range(0, len(x), win):
        vad.accept_waveform(x[i:i + win])
        while not vad.empty():
            out.append((vad.front.start / SR, np.array(vad.front.samples, np.float32)))
            vad.pop()
    vad.flush()
    while not vad.empty():
        out.append((vad.front.start / SR, np.array(vad.front.samples, np.float32)))
        vad.pop()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--task", default="transcribe", choices=["transcribe", "translate"])
    ap.add_argument("--language", default="")
    a = ap.parse_args()
    d = f"{M}/whisper-turbo/sherpa-onnx-whisper-turbo"
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{d}/turbo-encoder.int8.onnx", decoder=f"{d}/turbo-decoder.int8.onnx", tokens=f"{d}/turbo-tokens.txt",
        language=a.language, task=a.task, num_threads=4, tail_paddings=-1)
    x = load(a.audio)
    res = []
    for t0, seg in segments(x):
        s = rec.create_stream()
        s.accept_waveform(SR, seg)
        rec.decode_stream(s)
        r = s.result
        res.append(dict(start=round(t0, 2), end=round(t0 + len(seg) / SR, 2), text=r.text.strip(),
                        lang=getattr(r, "lang", "")))
        print(f"{res[-1]['start']:6.2f}-{res[-1]['end']:6.2f} [{res[-1]['lang']}] {res[-1]['text']}")
    json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
