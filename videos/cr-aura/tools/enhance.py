"""Clarity pass: Real-ESRGAN general v3 (SRVGGNetCompact) 4x super-resolution with its denoise blend,
supersampled down to 1080x1920, then a light temporal smooth.

  python3 tools/enhance.py renders/src/source.mp4 renders/src/enhanced.mp4 [--denoise 0.5] [--frames a-b] [--bench]

WhatsApp's 576x1024 at ~0.9 Mbps is soft and blocky. The model removes the blocking and restores
edges; rendering at 4x (2304x4096) and area-downscaling to 1080x1920 keeps that detail without
the over-sharpened "AI" look. Runs on CPU in bfloat16 (AMX). Weights: /root/vfx-models/realesrgan
(xinntao/Real-ESRGAN v0.2.5.0 release). --denoise blends the plain model (0) with the denoise
model (1).
"""
import argparse
import subprocess
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

W_DIR = "/root/vfx-models/realesrgan"
OUT_W, OUT_H = 1080, 1920


class SRVGGNetCompact(nn.Module):
    def __init__(self, num_feat=64, num_conv=32, upscale=4):
        super().__init__()
        self.upscale = upscale
        body = [nn.Conv2d(3, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        for _ in range(num_conv):
            body += [nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        body += [nn.Conv2d(num_feat, 3 * upscale * upscale, 3, 1, 1)]
        self.body = nn.ModuleList(body)
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        return self.upsampler(out) + F.interpolate(x, scale_factor=self.upscale, mode="nearest")


def load_model(denoise):
    def sd(name):
        d = torch.load(f"{W_DIR}/{name}.pth", map_location="cpu", weights_only=True)
        return d.get("params", d)
    a, b = sd("realesr-general-x4v3"), sd("realesr-general-wdn-x4v3")
    blend = {k: (1 - denoise) * a[k] + denoise * b[k] for k in a}   # deep network interpolation
    m = SRVGGNetCompact()
    m.load_state_dict(blend, strict=True)
    return m.eval()


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    w, h, r = out.strip().split(",")
    n, d = r.split("/")
    return int(w), int(h), float(n) / float(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--denoise", type=float, default=0.5)
    ap.add_argument("--frames", default=None, help="a-b (inclusive) to process only that range")
    ap.add_argument("--bench", action="store_true")
    a = ap.parse_args()
    torch.set_num_threads(4)
    model = load_model(a.denoise).to(memory_format=torch.channels_last)
    w, h, fps = probe(a.src)
    f0, f1 = (int(v) for v in a.frames.split("-")) if a.frames else (0, 10 ** 9)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = None
    if not a.bench:
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
                                "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
                                "-pix_fmt", "yuv444p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
                                "-color_trc", "bt709", a.out], stdin=subprocess.PIPE)
    size = w * h * 3
    i, t_start, done = 0, time.time(), 0
    with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16):
        while True:
            buf = dec.stdout.read(size)
            if len(buf) < size:
                break
            if i < f0:
                i += 1
                continue
            if i > f1:
                break
            x = torch.from_numpy(np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()).permute(2, 0, 1)[None].float() / 255
            x = x.contiguous(memory_format=torch.channels_last)
            t = time.time()
            y = model(x).float().clamp(0, 1)
            y = F.interpolate(y, size=(OUT_H, OUT_W), mode="area")
            img = (y[0].permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8)
            if a.bench:
                print(f"frame {i}: {time.time() - t:.2f} s")
                if done >= 2:
                    import cv2
                    cv2.imwrite(a.out, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                    break
            else:
                enc.stdin.write(img.tobytes())
            done += 1
            i += 1
            if done % 25 == 0:
                el = time.time() - t_start
                print(f"{done} frames, {el / done:.2f} s/frame", flush=True)
    dec.kill()
    if enc:
        enc.stdin.close()
        enc.wait()
    print(f"done: {done} frames in {time.time() - t_start:.0f} s")


if __name__ == "__main__":
    main()
