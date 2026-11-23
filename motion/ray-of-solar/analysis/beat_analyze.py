#!/usr/bin/env python3
"""Beat map for a four-on-the-floor track: BPM, beats, bars, phrases, per-bar energy.

usage: python3 beat_analyze.py <audio.wav> <out_dir> [--bpm-hint 136] [--downbeat 63.82]

Writes beatmap.json (beats, bars, 8-bar phrases) and markers.csv (bar/phrase markers
for After Effects / Premiere). Prints a bar-by-bar energy table (full / low / high)
so you can see grooves, breakdowns, builds and drops at a glance.

Why the hint: librosa's tracker can lock onto 2/3 tempo (it read 89 BPM on
"Ray of Solar"); the low-band kick spacing gave the true ~136 BPM. Pass --bpm-hint
with the kick tempo, and --downbeat with the time of a known downbeat (the drop),
so the bar grid lands on real bar lines.
"""
import argparse, csv, json

import librosa
import numpy as np
import scipy.signal as ss

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("out")
ap.add_argument("--bpm-hint", type=float, default=136.0)
ap.add_argument("--downbeat", type=float, default=None, help="a known downbeat in seconds (e.g. the drop)")
ap.add_argument("--beat", type=float, default=None, help="beat length in seconds, overrides detection (Ray of Solar: 0.443)")
a = ap.parse_args()

y, sr = librosa.load(a.audio, sr=22050)
dur = len(y) / sr

# kick check: median spacing of low-band peaks in the loudest 10 s
b, c = ss.butter(4, 120 / (sr / 2)); low = ss.filtfilt(b, c, y)
rms = librosa.feature.rms(y=y, hop_length=sr)[0]
loud = int(np.argmax(np.convolve(rms, np.ones(10), "valid")))
seg = low[loud * sr:(loud + 10) * sr]
env = ss.savgol_filter(np.abs(ss.hilbert(seg)), 501, 2)
pk, _ = ss.find_peaks(env, height=env.max() * .4, distance=int(.25 * sr))
kick_bpm = 60 / np.median(np.diff(pk / sr)) if len(pk) > 3 else None
print(f"kick spacing → {kick_bpm:.1f} BPM" if kick_bpm else "kick check: not enough peaks")

tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", start_bpm=a.bpm_hint, tightness=400)
bpm = float(np.atleast_1d(tempo)[0]); beat = float(np.median(np.diff(beats)))
print(f"tracked {bpm:.1f} BPM · beat {beat:.3f}s · bar {beat * 4:.3f}s · {len(beats)} beats")

# bar grid anchored on a known downbeat when given
# fixed bar grid through the downbeat. The tracker jitters around breaks and silences,
# so the beat length comes from --beat, else the measured kick spacing, else the tracker.
beat = a.beat or (60 / kick_bpm if kick_bpm else beat)
bar = beat * 4
anchor = a.downbeat if a.downbeat is not None else float(beats[0])
k0 = -int(anchor // bar)
bars = [anchor + k * bar for k in range(k0, int((dur - anchor) // bar) + 1)]
print(f"bar grid: {bar:.3f}s through {anchor:.2f}s")

bh, ah = ss.butter(4, 4000 / (sr / 2), "high"); hi = ss.filtfilt(bh, ah, y)
print("\n bar   time     full            low (kick/bass)   high")
for i, t0 in enumerate(bars):
    s = slice(int(t0 * sr), int(min(t0 + bar, dur) * sr))
    r, l, h = (float(np.sqrt(np.mean(x[s] ** 2))) for x in (y, low, hi))
    print(f"{i + 1:4d} {int(t0 // 60)}:{t0 % 60:05.2f}  {'#' * int(r * 60):<16}{'#' * int(l * 60):<18}{'#' * int(h * 300)}")

json.dump({"bpm": round(bpm, 2), "beat": round(beat, 4), "bar": round(bar, 4), "downbeat": anchor,
           "beats": [round(float(x), 3) for x in beats], "bars": [round(x, 3) for x in bars],
           "phrases_8bar": [round(x, 3) for x in bars[::8]]}, open(f"{a.out}/beatmap.json", "w"), indent=1)
with open(f"{a.out}/markers.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Name", "Start", "Type"])
    for i, t in enumerate(bars):
        w.writerow([("PHRASE " if i % 8 == 0 else "") + f"Bar {i + 1}", f"{t:.3f}", "phrase" if i % 8 == 0 else "bar"])
print(f"\nwrote {a.out}/beatmap.json and {a.out}/markers.csv")
