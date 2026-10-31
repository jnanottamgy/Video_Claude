"""Word timings for the voice-over karaoke guide, on the REEL timeline (output seconds).

The script words of every line (edl.SEGMENTS text, the captions' wording) map one to one onto the ASR's timed
words (edl.words()). The ASR places some phrase-initial words ~0.35 s early (into the silence before them), so each
start is snapped to where his voice actually begins: the first 10 ms frame within 0.6 s whose speech-band energy is
within 12 dB of the coming syllable's peak. A word lasts until the next one starts; a line's last word until its
energy falls 20 dB under its peak (0.25-0.9 s).

  python3 tools/karaoke_timing.py   # prints the timings
"""
import os
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(__file__))
import dialogue as Dg  # noqa: E402
import edl  # noqa: E402

SR = 48000
HOP = SR // 100


def energy():
    x = Dg.load_src().mean(1)
    f = sosfiltfilt(butter(4, [250, 4000], "bandpass", fs=SR, output="sos"), x)
    k = len(f) // HOP
    return 10 * np.log10((f[:k * HOP].reshape(k, HOP) ** 2).mean(1) + 1e-14)


def lines():
    """[{id, kind, text, words: [{w, s, e}]}] in output seconds."""
    env = energy()
    W = edl.words()
    out = []
    for seg in edl.SEGMENTS:
        script = seg["text"].split()
        asr = [w for w in W if w["seg"] == seg["id"]]
        assert len(script) == len(asr), seg["id"]
        starts = []
        for w in asr:
            src = w["s"] + seg["offset"]
            i = int(src * 100)
            pk = env[i:i + 60].max()
            if env[i] < pk - 12:                                  # starts in silence: snap to the onset
                j = i + int(np.argmax(env[i:i + 60] >= pk - 12))
                src = j / 100
            starts.append(round(src - seg["offset"], 2))
        for k in range(1, len(starts)):                           # keep them strictly increasing
            starts[k] = max(starts[k], starts[k - 1] + 0.08)
        words = []
        for k, (txt, s) in enumerate(zip(script, starts)):
            if k + 1 < len(starts):
                e = min(starts[k + 1] - 0.02, s + 0.9)
            else:
                i = int((s + seg["offset"]) * 100)
                pk = env[i:i + 40].max()
                below = np.nonzero(env[i + 10:i + 90] < pk - 20)[0]
                e = s + (0.10 + below[0] / 100 if len(below) else 0.9)
                e = min(max(e, s + 0.25), s + 0.9, seg["out_end"])
            words.append(dict(w=txt, s=s, e=round(e, 2)))
        out.append(dict(id=seg["id"], kind=seg["kind"], text=seg["text"], words=words))
    return out


if __name__ == "__main__":
    for ln in lines():
        print(ln["id"], " ".join(f"{w['w']}@{w['s']:.2f}" for w in ln["words"]))
