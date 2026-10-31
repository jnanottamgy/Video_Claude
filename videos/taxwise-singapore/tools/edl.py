"""TaxWise Consultants, Singapore expansion: the cut, on the music's beat grid.

Source: the team's 56 s reel (HK Vinay at his desk, plus 23 s of a camera pointed at a cabinet while he kept
talking). His eleven lines are kept in order; the director's cues ("Okay", "Go", "take one, start", "Go") are
cut. The cabinet footage is dropped: those lines (the team, the services, India to Singapore) play over
full-screen graphics.

Music: "Timeless Instrumental", 120.00 BPM (beat 0.5 s, bar 2 s), from song 187.542 s. Its last section:
  a 4 s drum-less break (song 196.042)    -> lands exactly as he says "TaxWise", under the announcement
  the drop (song 200.042)                 -> on "SINGAPORE" (the S at src 15.88)
  a rising glide, then a new lead (212.042) -> into the globe section
  6 bars lifted (song 218.042 -> 230.042: the 2-bar progression makes the seam invisible)
  the drums stop on a held chord (248.042) -> the logo reveal, 0.8 s after "this is just the beginning"
  python3 tools/edl.py     # print the timeline
"""
import json
import os

FPS = 30
W, H = 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "renders/src/drive/reel_original.mp4")
SONG = os.path.join(ROOT, "renders/analysis/song.wav")
DURATION = 52.0
TOTAL = int(round(DURATION * FPS))

# ---- music: (output start, song start, length); the song's grid: beats at 112.542 + k * 0.5
BEAT = 0.5
SONG_IN = 187.542
JUMP_OUT = 30.5                          # output time of the 6-bar lift
MUSIC = [(0.0, SONG_IN, JUMP_OUT), (JUMP_OUT, 230.042, DURATION - JUMP_OUT + 2.0)]


def song_time(t):
    """Song time playing at output time t."""
    return SONG_IN + t if t < JUMP_OUT else 230.042 + (t - JUMP_OUT)


BREAK = 196.042 - SONG_IN                # 8.5: the drums drop out (on "TaxWise")
DROP = 200.042 - SONG_IN                 # 12.5: the beat returns on "SINGAPORE"
GLIDE = 208.042 - SONG_IN                # 20.5: a synth glide rises
LIFT = 212.042 - SONG_IN                 # 24.5: the lead comes in
END = JUMP_OUT + (248.042 - 230.042)     # 48.5: the drums stop, a chord rings out


def beats(t0=0.0, t1=DURATION):
    """Output times of every beat (the grid follows the jump; downbeats every 4th, from the drop)."""
    out = []
    for k in range(-40, 200):
        t = DROP + k * BEAT
        if t0 <= t < min(t1, JUMP_OUT) or (t >= JUMP_OUT and t0 <= t < t1):
            out.append(round(t, 3))
    return out


def is_downbeat(t):
    return abs(((t - DROP) / (4 * BEAT)) - round((t - DROP) / (4 * BEAT))) < 1e-3


# ---- picture + dialogue: (output start, source start, source end, kind)
#   A = HK Vinay on camera (sound and picture in sync), G = full-screen graphic (his voice continues as VO)
SEGMENTS = [
    dict(id="A1", out=0.00, src=1.30, src_end=7.40, kind="A", shot="A",
         text="Big ambitions deserve bigger horizons. And we're taking ours global."),
    dict(id="A2", out=6.10, src=9.48, src_end=16.60, kind="A", shot="B",
         text="I am HK Vinay, Managing Partner at TaxWise. And I'm excited to announce our expansion into Singapore."),
    dict(id="G1", out=14.22, src=19.00, src_end=29.75, kind="G",
         text="With a dedicated team of over thirty in-house specialists, we bring together expertise across finance, "
              "taxation, payroll, compliance and advisory."),
    dict(id="G2", out=25.47, src=30.80, src_end=40.45, kind="G",
         text="From supporting businesses in India to helping them navigate Singapore's financial landscape, we are "
              "building stronger connections across borders."),
    dict(id="A3", out=35.82, src=41.85, src_end=48.40, kind="A", shot="E",
         text="Our commitment remains the same: expertise, transparency and building lasting relationships."),
    dict(id="A4", out=42.97, src=50.62, src_end=55.45, kind="A", shot="F",
         text="TaxWise, now in Singapore. And trust us, this is just the beginning."),
]
for s in SEGMENTS:
    s["out_end"] = round(s["out"] + (s["src_end"] - s["src"]), 3)
    s["offset"] = round(s["src"] - s["out"], 3)           # src = out + offset

# picture plan (output): which source frames show, where nothing is spoken too
#   (t0, t1, source offset or None for a graphic, shot)
PICTURE = [
    (0.00, 6.10, SEGMENTS[0]["offset"], "A"),
    (6.10, 13.22, SEGMENTS[1]["offset"], "B"),
    (13.22, 35.57, None, None),                            # the drop's slam, then the graphics for G1 + G2
    (35.57, 42.37, SEGMENTS[4]["offset"], "E"),             # he is on screen 0.25 s before he speaks
    (42.37, 48.25, SEGMENTS[5]["offset"], "F"),             # 0.6 s of him listening, then the last line
    (48.25, DURATION, None, None),                          # the end card
]

# the original's shots (source seconds), from cut detection
SHOTS = {"A": (0.0, 7.87), "B": (7.87, 17.30), "E": (40.83, 48.93), "F": (48.93, 56.0)}


def words():
    """Every spoken word in output time: [{w, s, e, seg}], from renders/analysis/words.json (Parakeet)."""
    raw = json.load(open(os.path.join(ROOT, "renders/analysis/words.json")))
    fix = {"Minai,": "Vinay,", "H.K.": "HK", "arises.": "horizons.", "Deserves": "deserve", "adversary.": "advisory.",
           "Taxmas,": "TaxWise,", "Taxwise.": "TaxWise.", "thirty": "thirty", "our": "our"}
    out = []
    for r in raw:
        for w in r["words"]:
            for s in SEGMENTS:
                if s["src"] - 0.05 <= w["s"] < s["src_end"]:
                    txt = fix.get(w["w"], w["w"])
                    out.append(dict(w=txt, s=round(w["s"] - s["offset"], 3), e=round(w["e"] - s["offset"], 3),
                                    seg=s["id"]))
    # "in our specialists" is "in-house specialists"; "a beginning" is "the beginning"
    for i, w in enumerate(out):
        if w["w"] == "in" and i + 1 < len(out) and out[i + 1]["w"] == "our":
            w["w"] = "in-house"
            out[i + 1]["w"] = ""
        if w["w"] == "a" and i + 1 < len(out) and out[i + 1]["w"].startswith("beginning"):
            w["w"] = "the"
    return [w for w in out if w["w"]]


def word_time(word, after=0.0):
    """Output start of the first word starting with `word` at or after `after`."""
    for w in words():
        if w["s"] >= after and w["w"].lower().strip(".,:").startswith(word.lower()):
            return w["s"]
    raise KeyError(word)


if __name__ == "__main__":
    print(f"{DURATION:.2f} s = {TOTAL} frames; song from {SONG_IN} (break {BREAK:.2f}, drop {DROP:.2f}, glide "
          f"{GLIDE:.2f}, lift {LIFT:.2f}, 6-bar lift at {JUMP_OUT:.2f}, drums stop {END:.2f})")
    for s in SEGMENTS:
        print(f"{s['id']:3s} out {s['out']:6.2f}-{s['out_end']:6.2f}  src {s['src']:6.2f}-{s['src_end']:6.2f}  "
              f"{s['kind']}  {s['text'][:70]}")
    print(" ".join(f"{w['w']}@{w['s']:.2f}" for w in words()))
