"""Cheluvara Cheluva Namma Gommata Deva: the reel's cut, on the song's own rhythm.

Source: the client's YouTube copy of the Kaveri Dham programme (Bhagavan Bahubali Swamy Pratishtha Mahotsava,
Basadi Hosakote, Mandya district, 25 November 2023). It is 11:44 long. Jina Gaana Visharade Smt. Jayashree D
Jain sings throughout, over the ceremony's footage. The first song, "Cheluvara Cheluva Namma Gommata Deva",
runs 0:00-6:44.

The reel plays the song's finale in one continuous take, source 373.98-404.6 s, with no musical edits:
  - the last refrain: A "ಚೆಲುವರ ಚೆಲುವ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ", B "ಇವ ತ್ಯಾಗ ವೀರ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ", A, then B three
    times, the last with a long held note;
  - the chant "ಜೈ ಬೋಲೋ ಗೊಮ್ಮಟೇಶ್ವರ ಬಾಹುಬಲಿ ಭಗವಾನ್ ಕೀ — ಜೈ!";
  - the song's own ending.
Tempo is ~138 BPM (beat 0.435 s). Sa is G#, the drone's strongest pitch. The tabla's bass stroke falls every
4 beats, and every sung line starts on one, every 8 beats. All cuts land on those strokes, except the flash
cut on the shouted "ಜೈ!".
  python3 tools/edl.py        # print the cut
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
W, H = 1080, 1920
SRC0 = 373.98                       # source time at reel 0
MUSIC_END = 404.60 - SRC0           # the song's own ending (30.62 s)
DURATION = 33.0
TOTAL = int(round(DURATION * FPS))
SA = 415.30                         # G#4: the song's tonic, for the temple bells
JAI = 401.70 - SRC0                 # the shouted "Jai!" (27.72)

# the tabla's bass strokes (reel time), measured: the cut points
STROKES = [round(s - SRC0, 3) for s in (374.539, 376.298, 378.045, 379.793, 381.511, 383.270, 385.000, 386.735,
                                        388.460, 390.184, 391.873, 393.603, 395.269, 396.993, 398.827, 400.592,
                                        402.403)]
S = STROKES

# ---- the shots: reel span, source in-point, crop (centre x, y and width as fractions of the clean area),
#      push (zoom at start/end), drift (crop centre moves by dx, dy over the shot), the god rays' strength
SHOTS = [
    dict(t0=0.0, t1=S[2], src=607.0, cx=0.50, cy=0.56, cw=0.56, zoom=(1.00, 1.08), rays=0.55, name="face"),
    dict(t0=S[2], t1=S[4], src=5.25, cx=0.47, cy=0.56, cw=0.50, zoom=(1.00, 1.05), rays=0.0, name="stage"),
    dict(t0=S[4], t1=S[5], src=301.0, cx=0.50, cy=0.40, cw=0.66, zoom=(1.03, 1.08), rays=0.45, name="pour"),
    dict(t0=S[5], t1=S[6], src=292.2, cx=0.24, cy=0.46, cw=0.60, zoom=(1.06, 1.00), rays=0.40, name="pour2"),
    dict(t0=S[6], t1=S[7], src=108.6, cx=0.50, cy=0.55, cw=0.76, zoom=(1.00, 1.06), rays=0.25, name="legs"),
    dict(t0=S[7], t1=S[8], src=396.6, cx=0.50, cy=0.58, cw=0.72, zoom=(1.04, 1.00), rays=0.10, name="feet"),
    dict(t0=S[8], t1=S[9], src=516.0, cx=0.48, cy=0.48, cw=0.74, zoom=(1.00, 1.05), rays=0.0, name="kalasha"),
    dict(t0=S[9], t1=S[10], src=568.2, cx=0.52, cy=0.45, cw=0.78, zoom=(1.05, 1.00), rays=0.0, name="flag"),
    dict(t0=S[10], t1=S[11], src=64.6, cx=0.50, cy=0.52, cw=0.74, zoom=(1.00, 1.06), rays=0.0, name="dance"),
    dict(t0=S[11], t1=S[13], src=17.65, cx=0.47, cy=0.56, cw=0.46, zoom=(1.00, 1.08), rays=0.0, name="stage2"),
    dict(t0=S[13], t1=S[14], src=448.0, cx=0.45, cy=0.50, cw=0.80, zoom=(1.04, 1.00), rays=0.35, name="flagstatue"),
    dict(t0=S[14], t1=JAI, src=665.1, cx=0.50, cy=0.42, cw=0.80, zoom=(1.00, 1.07), rays=0.65, name="umbrella"),
    dict(t0=JAI, t1=29.40, src=609.0, cx=0.50, cy=0.56, cw=0.52, zoom=(1.14, 1.04), rays=0.9, name="jai"),
    dict(t0=29.40, t1=DURATION, src=24.0, cx=0.47, cy=0.56, cw=0.56, zoom=(1.00, 1.04), rays=0.0, name="end"),
]
for s in SHOTS:
    s["t0"], s["t1"] = round(s["t0"], 3), round(s["t1"], 3)

# ---- the lyrics (reel time): Kannada as sung, and its meaning
A = ("ಚೆಲುವರ ಚೆಲುವ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ", "Fairest of the fair, our Lord Gommata")
B = ("ಇವ ತ್ಯಾಗ ವೀರ ನಮ್ಮ ಗೊಮ್ಮಟ ದೇವ", "the hero of renunciation, our Lord Gommata")
LYRICS = [
    dict(t0=0.02, t1=3.95, kn=A[0], en=A[1]),
    dict(t0=4.10, t1=7.40, kn=B[0], en=B[1]),
    dict(t0=7.50, t1=11.30, kn=A[0], en=A[1]),
    dict(t0=14.80, t1=18.00, kn=B[0], en=B[1]),
    dict(t0=18.00, t1=22.95, kn=B[0], en=B[1]),
    dict(t0=23.50, t1=27.60, kn="ಜೈ ಬೋಲೋ ಗೊಮ್ಮಟೇಶ್ವರ ಬಾಹುಬಲಿ ಭಗವಾನ್ ಕೀ", en="Hail Lord Gommateshwara Bahubali"),
]

# ---- the cards (reel time)
CARDS = [
    dict(t0=S[2], t1=DURATION, kind="artist"),              # her name, from her first shot to the end
    dict(t0=11.45, t1=14.70, kind="event"),                  # between the lyrics: what this is, and where
    dict(t0=JAI, t1=29.40, kind="jai"),
    dict(t0=29.40, t1=DURATION, kind="end"),
]

# ---- light events: (reel time, kind)
FLASHES = [(JAI, "jai")]
PETALS = [(0.0, 0.5), (S[2], 0.6), (S[11], 0.9), (JAI, 3.2), (29.4, 1.0)]       # (time, density) keyframes


def shot_at(t):
    for s in SHOTS:
        if s["t0"] <= t < s["t1"]:
            return s
    return SHOTS[-1]


if __name__ == "__main__":
    print(f"{DURATION:.2f} s = {TOTAL} frames; music source {SRC0:.2f}-{SRC0 + MUSIC_END:.2f}; Jai! at {JAI:.2f}")
    for s in SHOTS:
        print(f"  {s['t0']:6.2f}-{s['t1']:6.2f} ({s['t1'] - s['t0']:4.2f} s)  {s['name']:10s} source {s['src']:7.2f}")
    for ly in LYRICS:
        print(f"  lyric {ly['t0']:5.2f}-{ly['t1']:5.2f}  {ly['kn']}  /  {ly['en']}")
