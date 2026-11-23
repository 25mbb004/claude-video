#!/usr/bin/env python3
"""batch: many VODs in, one folder of ranked, ready-to-post clips out.

usage:
  python3 batch.py vods.txt [--out batch_out] [--per-vod 5] [--min 15] [--max 45]
                   [--zoom] [--sfx] [--cold-open] [--dry-run]

vods.txt — one VOD per line, optional credit and hashtags after "|":
  https://www.twitch.tv/videos/123456789 | @streamer on Twitch | #streamer #gta6 #fyp
  /path/to/local_vod.mp4 | @other on Kick
  # lines starting with # are ignored

For each VOD: clipper.py (find + render) → punchzoom.py (--zoom) → coldopen.py (--cold-open).
The best version of every clip is copied into <out>/_ready/, ranked by hype score, with its
post kit and an index.csv. One failing VOD is logged and skipped; the rest keep going.
"""
from __future__ import annotations

import argparse, csv, json, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def slug(s: str, i: int) -> str:
    s = s.strip()
    if re.match(r"^https?://", s):    # site + last path part, e.g. twitch-tv-videos-123456789
        s = re.sub(r"^https?://(www\.)?", "", s).split("?")[0]
    else:                              # local file: its name
        s = Path(s).stem
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[-40:] or "vod"
    return f"{i:02d}-{s}"


def run(cmd: list[str], log) -> bool:
    log.write("$ " + " ".join(cmd) + "\n"); log.flush()
    r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("list"); ap.add_argument("--out", default="batch_out")
    ap.add_argument("--per-vod", type=int, default=5); ap.add_argument("--min", type=float, default=15); ap.add_argument("--max", type=float, default=45)
    ap.add_argument("--zoom", action="store_true"); ap.add_argument("--sfx", action="store_true"); ap.add_argument("--cold-open", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="only score and list candidates for every VOD")
    a = ap.parse_args()

    out = Path(a.out); ready = out / "_ready"; out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for line in Path(a.list).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"): continue
        parts = [p.strip() for p in line.split("|")]
        jobs.append({"src": parts[0], "credit": parts[1] if len(parts) > 1 else "", "tags": parts[2] if len(parts) > 2 else ""})
    print(f"{len(jobs)} VODs · {a.per_vod} clips each · zoom={a.zoom} sfx={a.sfx} cold-open={a.cold_open}")

    results, failed = [], []
    for i, j in enumerate(jobs, 1):
        d = out / slug(j["src"], i); d.mkdir(exist_ok=True)
        t = time.time(); print(f"\n[{i}/{len(jobs)}] {j['src']}")
        with open(d / "log.txt", "a") as log:
            cmd = [PY, str(HERE / "clipper.py"), j["src"], "--out", str(d), "--n", str(a.per_vod), "--min", str(a.min), "--max", str(a.max)]
            if j["credit"]: cmd += ["--credit", j["credit"]]
            if j["tags"]: cmd += ["--tags", j["tags"]]
            if a.dry_run: cmd += ["--dry-run"]
            ok = run(cmd, log)
            if ok and not a.dry_run:
                src = next((p for p in sorted((d / ".work").glob("source.*"))), None) or Path(j["src"])
                if a.zoom: ok = run([PY, str(HERE / "punchzoom.py"), str(src), "--clips", str(d)] + (["--sfx"] if a.sfx else []), log)
                if ok and a.cold_open: ok = run([PY, str(HERE / "coldopen.py"), "--clips", str(d)], log)
        if not ok:
            failed.append(j["src"]); print(f"  ✗ failed, see {d / 'log.txt'}"); continue
        cands = json.loads((d / "candidates.json").read_text())
        for c in cands:
            c["vod"] = j["src"]; c["dir"] = d
            if a.dry_run: print(f"  {c['n']:2d}  score {c['score']:5.2f}  {c['hook'][:60]}"); continue
            base = d / f"clip_{c['n']:02d}"
            best = next((Path(f"{base}{s}.mp4") for s in ("_zoom_cold", "_cold", "_zoom", "") if Path(f"{base}{s}.mp4").exists()), None)
            if best: c["best"] = best; results.append(c)
        print(f"  done in {time.time() - t:.0f}s · {len(cands)} clips")

    if a.dry_run:
        print("\ndry run: nothing rendered"); return
    ready.mkdir(exist_ok=True)
    results.sort(key=lambda c: c["score"], reverse=True)
    with open(ready / "index.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["rank", "file", "score", "hook", "vod", "start", "end"])
        for r, c in enumerate(results, 1):
            name = f"{r:03d}_{c['dir'].name[3:40]}_{c['n']:02d}"
            shutil.copy2(c["best"], ready / f"{name}.mp4")
            kit = c["dir"] / f"clip_{c['n']:02d}.txt"
            if kit.exists(): shutil.copy2(kit, ready / f"{name}.txt")
            w.writerow([r, f"{name}.mp4", c["score"], c["hook"], c["vod"], round(c["start"], 2), round(c["end"], 2)])
    print(f"\n✓ {len(results)} clips ready in {ready} (best first, see index.csv)")
    if failed: print(f"✗ {len(failed)} VOD(s) failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
