"""Cut the 12 sound effects out of the "Sounds you need in your next edits" reel into library/sfx/soundsyouneed/.

  python3 library/tools/extract_soundsyouneed.py <reel.mp4>

The reel (720x1280, 19.7 s, sent 2026-11-23) scrolls a labelled waveform past a playhead and plays each effect
in turn: 8 Bit Talking, Old Flash, Cinematic Woosh, Night Vision, Nextel, Digital Text, Riser, Counter,
Bicycle Chain, Camera Click, Shine, Woosh. The windows below come from the reel's envelope (each effect is
separated by digital silence, except Digital Text -> Riser, split at the dip at 9.645 s). Trimming,
normalising and measuring are the same as extract_nikovax.py. Entries are merged into manifest.json by id.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from extract_nikovax import MANIFEST, SR, describe, env_db, load, write  # noqa: E402

SET = "soundsyouneed"
OUT = os.path.join(os.path.dirname(__file__), "..", "sfx", SET)

# (id, on-screen name, search window in the reel (s), category, how to align it, description)
PACK = [
    ("8-bit-talking", "8 Bit Talking", (0.0, 2.55), "ui", "start",
     "Retro 8-bit chatter blips (~2.4 s, continuous): a character talking in a chat bubble, text typing on, game UI."),
    ("old-flash", "Old Flash", (2.55, 3.95), "foley", "transient",
     "Vintage camera flashbulb pop: white flash frames, photo moments, freeze frames."),
    ("cinematic-woosh", "Cinematic Woosh", (3.95, 6.55), "whoosh", "peak",
     "Big swelling cinematic whoosh with a tail: major transitions, camera moves, title reveals."),
    ("night-vision", "Night Vision", (6.55, 8.50), "ui", "start",
     "Night-vision goggles switching on: a green/thermal look, POV or surveillance shots, a HUD turning on."),
    ("nextel", "Nextel", (8.50, 9.00), "ui", "start",
     "Nextel push-to-talk chirp (short double chirp): a message in, notifications, a walkie-talkie cue."),
    ("digital-text", "Digital Text", (9.00, 9.645), "glitch", "start",
     "Short digital data glitch burst: text decoding or typing in, glitch titles, data UI."),
    ("riser", "Riser", (9.645, 13.98), "riser", "peak",
     "Riser that swells to a peak and falls away (~4.3 s): put its peak on the drop or the reveal."),
    ("counter", "Counter", (13.98, 14.93), "ui", "start",
     "Fast ticking counter (~0.9 s): numbers rolling up, stat counters, a clock running."),
    ("bicycle-chain", "Bicycle Chain", (14.93, 15.75), "foley", "start",
     "Bicycle freewheel ratchet ticks: a dial or slider turning, a wheel spinning, scrubbing through time."),
    ("camera-click", "Camera Click", (15.75, 17.00), "foley", "transient",
     "Camera shutter: wind-up then a click. Snapshots, freeze frames, photo cards appearing."),
    ("shine", "Shine", (17.00, 18.45), "ui", "peak",
     "Sparkle / glint shine: a logo glint, text shine sweep, something brand new or premium."),
    ("woosh-5", "Woosh", (18.45, 19.72), "whoosh", "peak",
     "Short clean woosh: whip pans, text flying in, quick transitions."),
]


def main():
    x = load(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    e = env_db(x, 5)
    lib = []
    for sid, name, (a, b), cat, align, desc in PACK:
        i0, i1 = int(a * SR), min(len(x), int(b * SR))
        on = np.nonzero(e[i0:i1] > -72)[0]
        s = max(i0, i0 + on[0] - int(0.010 * SR))
        t = min(i1, i0 + on[-1] + int(0.040 * SR))
        y = x[s:t].copy()
        n = int(0.015 * SR)
        y[-n:] *= np.linspace(1, 0, n)[:, None]
        peak = float(np.abs(y).max())
        y *= 10 ** (-1 / 20) / peak
        write(os.path.join(OUT, f"{sid}.wav"), y)
        d = describe(y)
        hit = {"start": d["attack_s"], "peak": d["peak_s"], "end": d["duration"], "transient": d["transient_s"]}[align]
        lib.append(dict(id=sid, file=f"{SET}/{sid}.wav", name=name, category=cat, align=align, hit_s=round(hit, 3),
                        description=desc, source_window_s=[round(s / SR, 3), round(t / SR, 3)],
                        original_peak_dbfs=round(20 * np.log10(peak), 1), **d))
        print(f"{sid:16s} {d['duration']:5.2f}s  attack {d['attack_s']:5.2f}  peak {d['peak_s']:5.2f}  "
              f"transient {d['transient_s']:5.2f}  hit({align}) {hit:5.2f}  centroid {d['centroid_hz']:5d} Hz  "
              f"low {d['low_energy']:.2f}  orig peak {20 * np.log10(peak):6.1f} dBFS")
    man = json.load(open(MANIFEST))
    ids = {d["id"] for d in lib}
    man["sfx"] = [d for d in man["sfx"] if d["id"] not in ids] + lib
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print(f"{len(lib)} effects -> {OUT}; manifest now {len(man['sfx'])} effects")


if __name__ == "__main__":
    main()
