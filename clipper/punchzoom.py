#!/usr/bin/env python3
"""punchzoom: re-render clipper clips with a punch-in zoom + shake on the hype moment.

The zoom happens *under* the captions, so the text stays sharp and still while the
picture punches in. Optional --sfx adds a short sub-bass boom on the same frame.

usage:
  python3 punchzoom.py <source-video-or-url-already-downloaded> --clips clips [--pick 1,3]
                       [--zoom 1.18] [--hold 0.9] [--sfx]

Reads clips/candidates.json and the cached transcript from a previous clipper run,
writes clips/clip_NN_zoom.mp4 next to the originals.
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clipper as C  # noqa: E402


def zoom_expr(p: float, amount: float, hold: float) -> tuple[str, str, str]:
    """Envelope E(t): snap in over 0.12 s just before the peak, hold, ease out over 0.6 s."""
    a = max(p - .08, 0)
    E = (f"if(lt(t,{a:.3f}),0,if(lt(t,{a + .12:.3f}),(t-{a:.3f})/0.12,"
         f"if(lt(t,{a + .12 + hold:.3f}),1,if(lt(t,{a + .72 + hold:.3f}),1-(t-{a + .12 + hold:.3f})/0.6,0))))")
    Z = f"(1+{amount - 1:.3f}*{E})"
    shake = f"if(between(t,{a:.3f},{a + .45:.3f}),{E},0)"          # shake only on the hit
    sx = f"(iw-1080)/2+9*{shake}*sin(t*97)"
    sy = f"(ih-1920)/2+7*{shake}*sin(t*131+1.3)"
    return Z, sx, sy


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("--clips", default="clips"); ap.add_argument("--pick")
    ap.add_argument("--zoom", type=float, default=1.18); ap.add_argument("--hold", type=float, default=.9)
    ap.add_argument("--sfx", action="store_true", help="add a sub-bass boom on the punch")
    a = ap.parse_args()

    out = Path(a.clips); work = out / ".work"
    cands = json.loads((out / "candidates.json").read_text())
    video = C.fetch(a.source, work); meta = C.probe(video)
    words_files = sorted(work.glob("words_*.json"))
    words = json.loads(words_files[0].read_text()) if words_files else []
    pick = {int(x) for x in a.pick.split(",")} if a.pick else None
    face = None
    for c in cands:
        if pick and c["n"] not in pick: continue
        lay = c.get("lay")
        if not lay:                                    # rendered before layouts were saved: detect again
            if face is None:
                face = C.detect_faces(video, c["start"], c["end"], meta) or False
            lay = C.plan_layout(face or None, meta, "auto")
        vf, cap_y = C.vf_for(lay)
        ass = work / (c.get("ass") or f"clip_{c['n']:02d}.ass")
        if not ass.exists() and words:
            C.write_ass(ass, words, c["start"], c["end"], cap_y, c.get("hook", ""))
        p = c["peak"] - c["start"]
        Z, sx, sy = zoom_expr(p, a.zoom, a.hold)
        chain = (vf + f";[v0]scale=w='trunc(1080*{Z}/2)*2':h='trunc(1920*{Z}/2)*2':eval=frame,"
                 f"crop=1080:1920:x='{sx}':y='{sy}',setsar=1[vz]"
                 + (f";[vz]ass={ass.as_posix()}[v]" if ass.exists() else ";[vz]null[v]"))
        dur = c["end"] - c["start"]
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{c['start']:.3f}", "-t", f"{dur:.3f}", "-i", str(video)]
        if a.sfx:
            boom = (f"aevalsrc='0.9*sin(2*PI*(48+70*exp(-t*14))*t)*exp(-t*4.5)':s=48000:d=1.2,"
                    f"adelay={int(max(p - .08, 0) * 1000)}|{int(max(p - .08, 0) * 1000)}")
            chain += (f";[0:a:0]aresample=48000,aformat=channel_layouts=stereo[a0];{boom},aformat=channel_layouts=stereo[b];"
                      f"[a0][b]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
            amap = ["-map", "[a]"]
        else:
            amap = ["-map", "0:a:0?", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        dst = out / f"clip_{c['n']:02d}_zoom.mp4"
        C.sh(cmd + ["-filter_complex", chain, "-map", "[v]"] + amap +
             ["-r", str(min(60, round(meta["fps"]))), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)])
        print(f"  ✓ {dst}  (punch at {p:.2f}s{' + boom' if a.sfx else ''})")


if __name__ == "__main__":
    main()
