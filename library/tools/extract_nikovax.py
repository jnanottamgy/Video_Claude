"""Cut the 28 sound effects out of the NIKOVAX showcase video into library/sfx/nikovax/.

  python3 library/tools/extract_nikovax.py library/sfx-import/src/sfx_pack_video.mov

The showcase plays each effect alone, separated by digital silence, with its name on screen.
Each one is searched for inside its own window (taken from the on-screen titles); its edges
are where the envelope first/last crosses -72 dBFS (10 ms pre-roll, 40 ms tail, 15 ms fade).
Every file is peak-normalised to -1 dBFS; the original peak, the attack/peak times and a
character summary go into library/sfx/manifest.json.
"""
import json
import os
import subprocess
import sys

import numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(__file__), "..", "sfx", "nikovax")
MANIFEST = os.path.join(os.path.dirname(__file__), "..", "sfx", "manifest.json")

# (id, on-screen name, search window in the showcase (s), category, how to align it, description)
PACK = [
    ("build-up-1", "#1 build up", (0.0, 3.9), "riser", "end", "Short tension build that swells into a cut."),
    ("radio-beep", "#2 radio beep", (3.9, 6.2), "ui", "start", "Radio / walkie-talkie beep: an on-air cue, a message in, a cut to a new scene."),
    ("build-up-2", "#3 build up (2)", (6.2, 11.0), "riser", "end", "Longer build-up swelling into a drop."),
    ("radio-switch", "#4 radio switch", (11.0, 12.5), "ui", "start", "Radio switch-over click and static: hard cut, channel change, POV change."),
    ("build-up-3", "#5 build up (3)", (12.5, 18.8), "riser", "peak", "Long build (~4.6 s of pulses accelerating) that climaxes then drops away: put its peak on the drop."),
    ("alien-digital-glitch", "#6 alien digital glitch", (18.8, 22.3), "glitch", "start", "Warbling alien/digital glitch texture: strobes, cut-outs, glitch frames."),
    ("beat-slowing", "#7 beat slowing", (22.3, 26.1), "transition", "start", "Tape-stop / beat slowing down: freezes, speed ramps into slow-mo, the music stopping."),
    ("slow-motion", "#8 slow motion", (26.1, 29.1), "transition", "start", "Slow-motion swell: the moment time slows (speed ramp down), aura moments."),
    ("gun-reload", "#9 gun reload", (29.1, 31.3), "foley", "start", "Gun reload / cocking: a 'loading up' beat before an action or reveal."),
    ("woosh-1", "#10 woosh (1)", (31.3, 36.2), "whoosh", "peak", "Big airy whoosh with a long tail: big transitions, camera moves."),
    ("woosh-2", "#11 WOOSH (2)", (36.2, 39.4), "whoosh", "peak", "Heavy punchy whoosh: hard transitions and whip pans."),
    ("woosh-3", "#12 woosh (3)", (39.4, 41.6), "whoosh", "peak", "Quick whoosh: whips, text flying in."),
    ("woosh-4", "#13 woosh (4)", (41.6, 44.4), "whoosh", "peak", "Medium whoosh: zoom transitions."),
    ("fast-swoosh", "#14 fast swoosh", (44.4, 45.52), "whoosh", "peak", "Very fast swish (~0.9 s): quick cuts, fast element moves."),
    ("slow-woosh", "#15 slow wosh", (45.52, 48.05), "whoosh", "peak", "Slow swelling whoosh: slow-mo moves, floating transitions."),
    ("glitchy-woosh", "#16 glitchy woosh", (48.05, 50.5), "whoosh", "peak", "Whoosh with digital glitch grit: glitch transitions, RGB splits."),
    ("lowpass-woosh", "#17 lowpass woosh", (50.5, 53.95), "whoosh", "peak", "Muffled (low-passed) whoosh: underwater or dream moments, muffled sections."),
    ("bass-woosh-1", "#18 Bass woosh (1)", (53.95, 56.5), "whoosh", "transient", "Rising bass sweep into a burst, then a sub tail: big reveals, drops, title slams (very loud)."),
    ("bass-woosh-2", "#19 Bass woosh (2)", (56.5, 58.79), "whoosh", "peak", "Rising bass sweep into a punchy hit: transition into a drop."),
    ("sword-impact", "#20 sword impact", (58.79, 63.5), "impact", "transient", "Metallic sword clash with a ringing tail: hero hits, title slams, freeze frames."),
    ("sword-slash-1", "#21 sword slash (1)", (63.5, 64.9), "slash", "peak", "Sword slash / swipe: fast cuts, wipes, text slicing in."),
    ("sword-slash-2", "#22 sword slash (2)", (64.9, 66.4), "slash", "start", "Sword slash flurry (four quick slashes): rapid cuts, a combo."),
    ("sword-slash-3", "#23 sword slash (3)", (66.4, 68.1), "slash", "transient", "Sword slash variant three."),
    ("cinematic-electric-hit", "#24 cinematic electric hit", (68.1, 74.5), "impact", "transient", "Cinematic hit with electric crackle and a long tail: drops, big reveals, aura moments."),
    ("wind-impact", "#25 wind impact", (74.5, 80.2), "impact", "transient", "Wind gust into an impact: dramatic entrances, dust and smoke moments."),
    ("lightning-strike", "#26 lightning strike", (80.2, 87.0), "impact", "transient", "Thunder crack and rumble: white flashes, power moments."),
    ("fire", "#27 fire sfx", (87.0, 103.0), "ambience", "start", "Fire crackle bed (~13 s): flames, heat, slow-burn shots. Loopable bed."),
    ("rain", "#28 rain sfx", (103.0, 120.0), "ambience", "start", "Rain bed (~13 s): moody, sad or atmospheric shots. Loopable bed."),
]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def env_db(x, win_ms=10):
    w = max(1, int(SR * win_ms / 1000))
    m = (x ** 2).mean(1)
    e = np.sqrt(np.convolve(m, np.ones(w) / w, "same"))
    return 20 * np.log10(e + 1e-12)


def write(path, y):
    pcm = np.clip(y, -1, 1).astype(np.float32).tobytes()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", path], input=pcm, check=True)


def describe(y):
    """Duration, attack, peak and spectral character of one effect."""
    m = y.mean(1)
    e = env_db(y, 10)
    pk = int(np.argmax(e))
    att = int(np.argmax(e > e.max() - 20))
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    cent = float((spec * f).sum() / spec.sum())
    low = float(spec[f < 150].sum() / spec.sum())
    # transient: the strongest broadband onset (spectral flux), i.e. where a hit is heard
    n_fft, hop = 1024, 240
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(m, (n_fft // 2, n_fft // 2)), n_fft)[::hop]
    mag = np.abs(np.fft.rfft(frames * np.hanning(n_fft), axis=1))
    flux = np.maximum(np.diff(np.log1p(mag * 50), axis=0), 0).sum(1)
    tr = (int(np.argmax(flux)) + 1) * hop
    return dict(duration=round(len(m) / SR, 3), attack_s=round(att / SR, 3), peak_s=round(pk / SR, 3),
                transient_s=round(tr / SR, 3), centroid_hz=int(cent), low_energy=round(low, 3))


def main():
    x = load(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    e = env_db(x, 5)
    lib = []
    for sid, name, (a, b), cat, align, desc in PACK:
        i0, i1 = int(a * SR), int(b * SR)
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
        lib.append(dict(id=sid, file=f"nikovax/{sid}.wav", name=name, category=cat, align=align, hit_s=round(hit, 3),
                        description=desc, source_window_s=[round(s / SR, 3), round(t / SR, 3)],
                        original_peak_dbfs=round(20 * np.log10(peak), 1), **d))
        print(f"{sid:24s} {d['duration']:6.2f}s  attack {d['attack_s']:5.2f}  peak {d['peak_s']:5.2f}  transient {d['transient_s']:5.2f}  hit({align}) {hit:5.2f}  "
              f"centroid {d['centroid_hz']:5d} Hz  low {d['low_energy']:.2f}  orig peak {20 * np.log10(peak):6.1f} dBFS")
    man = dict(
        description="Sound-effect library for edits. 'nikovax' = 28 effects cut from the NIKOVAX showcase video the user "
                    "sent (2026-10-23). Audio is gitignored (third-party pack, public repo); restore it from the private "
                    "artifact named in README.md or re-run library/tools/extract_nikovax.py on the showcase video.",
        sample_rate=SR, format="wav pcm_s24le stereo, peak-normalised to -1 dBFS",
        usage="Place an effect so its hit_s lands on the event: start = event_time - hit_s. "
              "align=start (attack on the event), peak (loudest point on the event), end (the swell ends on the event), "
              "transient (the sharpest onset, the heard hit, on the event).",
        sfx=lib)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print(f"{len(lib)} effects -> {OUT}; manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
