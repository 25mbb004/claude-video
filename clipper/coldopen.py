#!/usr/bin/env python3
"""coldopen: put the best 2 seconds of each clip at the very start, then a white flash,
then the whole clip from the beginning. Viewers see the payoff first and stay for the context.

usage:
  python3 coldopen.py --clips clips [--pick 1,3] [--len 1.8] [--lead 0.35] [--from zoom]

Works on any clipper output folder (reads candidates.json for each clip's peak).
--from zoom uses clip_NN_zoom.mp4 when punchzoom.py has been run, else clip_NN.mp4.
Writes clip_NN_cold.mp4 (or clip_NN_zoom_cold.mp4).
"""
from __future__ import annotations

import argparse, json, subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", default="clips"); ap.add_argument("--pick")
    ap.add_argument("--len", type=float, default=1.8, help="teaser length in seconds")
    ap.add_argument("--lead", type=float, default=.35, help="start the teaser this long before the peak")
    ap.add_argument("--from", dest="src", default="auto", choices=["auto", "plain", "zoom"])
    a = ap.parse_args()

    out = Path(a.clips)
    cands = json.loads((out / "candidates.json").read_text())
    pick = {int(x) for x in a.pick.split(",")} if a.pick else None
    for c in cands:
        if pick and c["n"] not in pick: continue
        plain, zoom = out / f"clip_{c['n']:02d}.mp4", out / f"clip_{c['n']:02d}_zoom.mp4"
        src = zoom if (a.src == "zoom" or (a.src == "auto" and zoom.exists())) else plain
        if not src.exists():
            print(f"  – skip {src.name} (not rendered)"); continue
        p = c["peak"] - c["start"]; dur = c["end"] - c["start"]
        t0 = min(max(p - a.lead, 0), max(dur - a.len, 0)); L = min(a.len, dur)
        f = .09  # white flash between the teaser and the clip
        chain = (f"[0:v]split[v1][v2];[0:a]asplit[a1][a2];"
                 f"[v1]trim={t0:.3f}:{t0 + L:.3f},setpts=PTS-STARTPTS,fade=t=out:st={L - f:.3f}:d={f}:color=white[tv];"
                 f"[a1]atrim={t0:.3f}:{t0 + L:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={L - .06:.3f}:d=0.06[ta];"
                 f"[v2]setpts=PTS-STARTPTS,fade=t=in:st=0:d={f * 1.5:.3f}:color=white[mv];"
                 f"[a2]asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.05[ma];"
                 f"[tv][ta][mv][ma]concat=n=2:v=1:a=1[v][a]")
        dst = src.with_name(src.stem + "_cold.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-filter_complex", chain, "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(dst)], check=True)
        print(f"  ✓ {dst}  (teaser {t0:.2f}–{t0 + L:.2f}s, +{L:.1f}s)")


if __name__ == "__main__":
    main()
