#!/usr/bin/env python3
"""clipper: turn a stream VOD into ready-to-post vertical clips.

  source (URL or file) → transcript with word timings (Groq/OpenAI Whisper)
  → hype score per moment (loudness spikes vs the streamer's baseline, hype words,
    "clip that", talking speed) → top N non-overlapping clips snapped to sentence edges
  → 1080×1920 render: face cam on top + gameplay below (or face-tracked crop / blur fill),
    word-by-word captions with the active word highlighted, an optional hook title,
    loudness normalised for Shorts/TikTok/Reels.

usage:
  python3 clipper.py <url-or-file> [--out clips] [--n 5] [--min 15] [--max 45]
                     [--start 1:20:00 --end 2:00:00] [--layout auto|split|crop|blur]
                     [--facecam x,y,w,h] [--hook auto|none|"TEXT"] [--keywords "word,word"]
                     [--pick 1,3] [--dry-run]

--dry-run scores and lists candidates without rendering, so you (or Claude) can pick with --pick.
Only clip streams you have permission to clip (e.g. a paid clipping campaign).
"""
from __future__ import annotations

import argparse, json, os, re, ssl, subprocess, sys, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "watch" / "scripts"))
try:
    from whisper import load_api_key  # reuse the watch skill's key lookup (~/.config/watch/.env)
except Exception:  # pragma: no cover
    load_api_key = None

ENDPOINTS = {"groq": ("https://api.groq.com/openai/v1/audio/transcriptions", "whisper-large-v3-turbo"),
             "openai": ("https://api.openai.com/v1/audio/transcriptions", "whisper-1")}
HYPE = {  # phrase → weight
    "clip that": 3, "clip it": 3, "no way": 2, "oh my god": 2, "what the": 1.5, "let's go": 2, "lets go": 2,
    "holy": 1.5, "bro": 1, "yo": .8, "dude": .8, "insane": 1.5, "crazy": 1.2, "wtf": 2, "omg": 2, "chat": .5,
    "haha": 1.2, "hahaha": 1.6, "lmao": 1.5, "help": 1, "run": .8, "what": .6, "nah": .8, "wait": .8, "bruh": 1,
}


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def tsec(s: str | None) -> float | None:
    if s is None: return None
    parts = [float(p) for p in str(s).split(":")]
    v = 0.0
    for p in parts: v = v * 60 + p
    return v


def fmt(t: float) -> str:
    t = max(t, 0); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


# ---------------------------------------------------------------- source
def fetch(source: str, work: Path) -> Path:
    if re.match(r"^https?://", source):
        import yt_dlp
        opts = {"outtmpl": str(work / "source.%(ext)s"), "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
                "merge_output_format": "mp4", "quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([source])
        found = sorted(work.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
        if not found: sys.exit("download failed")
        return found[0]
    p = Path(source).expanduser()
    if not p.exists(): sys.exit(f"not found: {p}")
    return p


def probe(path: Path) -> dict:
    out = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)]).stdout)
    st = out["streams"][0]; n, d = st["r_frame_rate"].split("/")
    return {"w": int(st["width"]), "h": int(st["height"]), "fps": float(n) / float(d), "dur": float(out["format"]["duration"])}


# ---------------------------------------------------------------- transcript (word timings)
def _multipart(fields: list[tuple[str, str]], file: Path) -> tuple[bytes, str]:
    b = uuid.uuid4().hex; out = bytearray()
    for k, v in fields:
        out += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    out += f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file.name}\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode()
    out += file.read_bytes() + f"\r\n--{b}--\r\n".encode()
    return bytes(out), b


def whisper_words(audio: Path, backend: str, key: str) -> list[dict]:
    url, model = ENDPOINTS[backend]
    body, b = _multipart([("model", model), ("response_format", "verbose_json"), ("temperature", "0"),
                          ("timestamp_granularities[]", "word"), ("timestamp_granularities[]", "segment")], audio)
    req = Request(url, data=body, method="POST", headers={"Authorization": f"Bearer {key}",
                  "Content-Type": f"multipart/form-data; boundary={b}", "User-Agent": "clipper/1.0 (python-urllib)"})
    try:
        data = json.loads(urlopen(req, context=ssl.create_default_context(), timeout=600).read())
    except HTTPError as e:
        sys.exit(f"whisper {e.code}: {e.read()[:300]!r}")
    return [{"w": w["word"].strip(), "s": float(w["start"]), "e": float(w["end"])} for w in data.get("words") or [] if w.get("word", "").strip()]


def transcribe(video: Path, work: Path, t0: float, t1: float) -> list[dict]:
    cache = work / f"words_{int(t0)}_{int(t1)}.json"
    if cache.exists(): return json.loads(cache.read_text())
    if load_api_key is None: sys.exit("watch skill scripts not found; cannot load a Whisper key")
    backend, key = load_api_key()
    if not key: sys.exit("no GROQ_API_KEY / OPENAI_API_KEY (see ~/.config/watch/.env)")
    words, chunk = [], 1200.0  # 20-minute chunks stay well under the upload cap
    s = t0
    while s < t1 - .5:
        e = min(s + chunk, t1); part = work / f"chunk_{int(s)}.mp3"
        sh(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-t", str(e - s), "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(part)])
        print(f"  transcribing {fmt(s)} → {fmt(e)} ({backend})", flush=True)
        for w in whisper_words(part, backend, key):
            words.append({"w": w["w"], "s": round(w["s"] + s, 3), "e": round(w["e"] + s, 3)})
        s = e
    cache.write_text(json.dumps(words))
    return words


# ---------------------------------------------------------------- scoring
def loudness(video: Path, t0: float, t1: float, hop: float = .25) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(video), "-vn", "-ac", "1",
                          "-ar", "8000", "-f", "s16le", "-"], check=True, capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int(8000 * hop); k = len(x) // n
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-9)
    return 20 * np.log10(rms)


def score_timeline(words, db, t0, hop, extra_kw):
    from scipy.ndimage import median_filter, uniform_filter1d
    n = len(db)
    base = median_filter(db, size=max(3, int(90 / hop)), mode="nearest")          # the streamer's normal level
    spread = np.median(np.abs(db - base)) * 1.4826 + 1e-3
    loud = np.clip((db - base) / spread, 0, 6)
    hype, rate = np.zeros(n), np.zeros(n)
    kw = dict(HYPE); kw.update({k.strip().lower(): 2.0 for k in extra_kw if k.strip()})
    toks = [re.sub(r"[^\w' ]", "", w["w"].lower()) for w in words]
    for i, w in enumerate(words):
        j = int((w["s"] - t0) / hop)
        if 0 <= j < n:
            rate[j] += 1
            for L in (3, 2, 1):  # match phrases up to 3 words
                ph = " ".join(toks[i:i + L])
                if ph in kw: hype[j] += kw[ph]; break
            if "!" in w["w"]: hype[j] += .6
    win = int(3 / hop)
    hype = uniform_filter1d(hype, win) * win
    rate = uniform_filter1d(rate, int(4 / hop)) * int(4 / hop) / 4      # words per second
    rate_z = np.clip((rate - np.median(rate)) / (np.std(rate) + 1e-3), 0, 3)
    s = .55 * uniform_filter1d(loud, int(2 / hop)) + .3 * np.minimum(hype, 6) + .15 * rate_z
    return uniform_filter1d(s, int(1.5 / hop))


def pick_moments(score, t0, hop, n, gap):
    s = score.copy(); out = []
    for _ in range(n):
        i = int(np.argmax(s))
        if s[i] <= .2: break
        out.append((t0 + i * hop, float(s[i])))
        a, b = max(0, i - int(gap / hop)), min(len(s), i + int(gap / hop))
        s[a:b] = -1
    return out


def snap_window(words, peak, mn, mx):
    """Start on a sentence edge before the peak, end on one after, within [mn, mx] seconds."""
    def gaps(lo, hi):  # (time, gap size) at word boundaries in [lo, hi]
        g = []
        for a, b in zip(words, words[1:]):
            if lo <= b["s"] <= hi:
                bonus = .6 if re.search(r"[.!?]$", a["w"]) else 0
                g.append((b["s"], b["s"] - a["e"] + bonus))
        return g
    st = max(gaps(peak - 14, peak - 3), key=lambda x: x[1], default=(peak - 7, 0))[0]
    en = max(gaps(peak + 5, peak + 20), key=lambda x: x[1], default=(peak + 10, 0))[0]
    if en - st < mn: en = st + mn
    if en - st > mx: st, en = max(st, peak - mx * .4), min(en, peak + mx * .6)
    return round(st - .15, 2), round(en + .1, 2)


def hook_text(words, st, en, peak):
    sent, cur = [], []
    for w in words:
        if w["s"] < st or w["s"] > en: continue
        cur.append(w)
        if re.search(r"[.!?]$", w["w"]): sent.append(cur); cur = []
    if cur: sent.append(cur)
    if not sent: return ""
    best = min(sent, key=lambda c: abs((c[0]["s"] + c[-1]["e"]) / 2 - peak))
    txt = " ".join(w["w"] for w in best[:8]).strip(" ,")
    return re.sub(r"[{}\\]", "", txt).upper()


# ---------------------------------------------------------------- framing
def detect_faces(video: Path, st: float, en: float, meta: dict):
    import cv2
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes, samples = [], 40
    for k in range(samples):
        t = st + (en - st) * (k + .5) / samples
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf",
                              "scale=960:-2", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        h = int(round(meta["h"] * 960 / meta["w"] / 2) * 2)
        if len(raw) < 960 * h: continue
        img = np.frombuffer(raw[:960 * h], np.uint8).reshape(h, 960)
        f = casc.detectMultiScale(img, 1.1, 5, minSize=(24, 24))
        if len(f):
            x, y, w, hh = max(f, key=lambda b: b[2] * b[3]); s = meta["w"] / 960
            boxes.append((x * s, y * s, w * s, hh * s))
    if len(boxes) < max(3, samples * .25): return None
    return tuple(float(v) for v in np.median(np.array(boxes), 0))


def plan_layout(face, meta, forced):
    W, H = meta["w"], meta["h"]
    if forced == "blur" or (forced == "auto" and face is None): return {"kind": "blur"}
    if face is None: return {"kind": "blur"}
    fx, fy, fw, fh = face; cx, cy = fx + fw / 2, fy + fh / 2
    big_center = fw > .11 * W and .2 * W < cx < .8 * W
    if forced == "crop" or (forced == "auto" and big_center):          # just-chatting / IRL: follow the face
        cw = min(W, H * 9 / 16); x = min(max(cx - cw / 2, 0), W - cw)
        return {"kind": "crop", "x": x, "w": cw}
    cw = min(W * .45, fw * 2.5); ch = cw / (1080 / 700)                 # face-cam panel, head and shoulders
    x = min(max(cx - cw / 2, 0), W - cw); y = min(max(cy - ch * .45, 0), H - ch)
    gw = min(W, H * 1080 / 1220)
    return {"kind": "split", "cam": (x, y, cw, ch), "game": ((W - gw) / 2, 0, gw, H)}


def vf_for(lay):
    if lay["kind"] == "split":
        x, y, w, h = (int(v) // 2 * 2 for v in lay["cam"]); gx, gy, gw, gh = (int(v) // 2 * 2 for v in lay["game"])
        return (f"[0:v]crop={w}:{h}:{x}:{y},scale=1080:700:force_original_aspect_ratio=increase,crop=1080:700[top];"
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:1220:force_original_aspect_ratio=increase,crop=1080:1220[bot];"
                f"[top][bot]vstack=inputs=2,setsar=1[v0]"), 760
    if lay["kind"] == "crop":
        return (f"[0:v]crop={int(lay['w']) // 2 * 2}:ih:{int(lay['x']) // 2 * 2}:0,scale=1080:1920,setsar=1[v0]"), 1380
    return ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:3,eq=brightness=-0.12[bg];"
            "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2,setsar=1[v0]"), 1380


# ---------------------------------------------------------------- captions (ASS, word by word)
def ass_time(t): t = max(t, 0); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_ass(path: Path, words, st, en, cap_y, hook, font="Inter Display Black"):
    ws = [w for w in words if w["e"] > st and w["s"] < en]
    groups, cur = [], []
    for w in ws:  # 1–3 words per caption, break on punctuation or pauses
        if cur and (len(cur) == 3 or w["s"] - cur[-1]["e"] > .35 or re.search(r"[.!?,]$", cur[-1]["w"])):
            groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,5,60,60,0,1
Style: Hook,{font},64,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,0,0,0,0,100,100,0,0,3,18,0,8,70,70,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    flat = [w for g in groups for w in g]
    nxt = {id(w): (flat[i + 1]["s"] if i + 1 < len(flat) else en) for i, w in enumerate(flat)}
    for g in groups:
        for k, w in enumerate(g):
            a = w["s"] - st
            b = (g[k + 1]["s"] if k + 1 < len(g) else min(max(w["e"], w["s"] + .25), nxt[id(w)])) - st
            parts = []
            for m, x in enumerate(g):
                t = re.sub(r"[{}\\]", "", x["w"]).upper()
                parts.append(r"{\c&H00E5FF&}" + t + r"{\c&HFFFFFF&}" if m == k else t)
            pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}" if k == 0 else ""
            ev.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{{\\pos(540,{cap_y})}}{pop}{' '.join(parts)}")
    if hook:
        ev.append(f"Dialogue: 2,{ass_time(0)},{ass_time(min(3.2, en - st))},Hook,,0,0,0,,{{\\fad(0,250)}}{hook}")
    path.write_text(head + "\n".join(ev) + "\n")


# ---------------------------------------------------------------- render
def render(video: Path, out: Path, st, en, lay, ass: Path | None, fps):
    vf, _ = vf_for(lay)
    chain = vf + (f";[v0]ass={ass.as_posix()}[v]" if ass else ";[v0]null[v]")
    sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{st:.3f}", "-t", f"{en - st:.3f}", "-i", str(video), "-filter_complex", chain,
        "-map", "[v]", "-map", "0:a:0?", "-r", str(min(60, round(fps))), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out)])


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("--out", default="clips"); ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--min", type=float, default=15); ap.add_argument("--max", type=float, default=45)
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--layout", default="auto", choices=["auto", "split", "crop", "blur"])
    ap.add_argument("--facecam", help="x,y,w,h of the face cam in source pixels (skips detection)")
    ap.add_argument("--hook", default="auto", help='auto | none | "YOUR TEXT"')
    ap.add_argument("--keywords", default="", help="extra hype words, comma separated (e.g. the streamer's catchphrases)")
    ap.add_argument("--pick", help="render only these candidate numbers, e.g. 1,3")
    ap.add_argument("--credit", default="", help='who the clip is from, e.g. "@streamer on Twitch" (goes in the post kit)')
    ap.add_argument("--tags", default="", help='hashtags for the post kit, e.g. "#streamer #gta6 #fyp"')
    ap.add_argument("--no-captions", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    out = Path(a.out); work = out / ".work"; work.mkdir(parents=True, exist_ok=True)
    video = fetch(a.source, work); meta = probe(video)
    t0 = tsec(a.start) or 0.0; t1 = min(tsec(a.end) or meta["dur"], meta["dur"])
    print(f"source {video.name} · {meta['w']}x{meta['h']} · {fmt(t0)} → {fmt(t1)}")

    words = transcribe(video, work, t0, t1)
    hop = .25; db = loudness(video, t0, t1, hop)
    score = score_timeline(words, db, t0, hop, a.keywords.split(","))
    peaks = pick_moments(score, t0, hop, a.n, gap=a.max)
    cands = []
    for i, (pk, sc) in enumerate(peaks, 1):
        st, en = snap_window(words, pk, a.min, a.max)
        st, en = max(st, t0), min(en, t1)
        text = " ".join(w["w"] for w in words if st <= w["s"] <= en)
        hook = hook_text(words, st, en, pk) if a.hook == "auto" else ("" if a.hook == "none" else a.hook.upper())
        cands.append({"n": i, "start": st, "end": en, "peak": round(pk, 2), "score": round(sc, 2), "hook": hook, "text": text})
    (out / "candidates.json").write_text(json.dumps(cands, indent=1))
    print("\n  #  score   start → end          len   hook")
    for c in cands:
        print(f"{c['n']:3d}  {c['score']:5.2f}   {fmt(c['start'])} → {fmt(c['end'])}  {c['end'] - c['start']:4.1f}s  {c['hook'][:60]}")
    if a.dry_run: return

    pick = {int(x) for x in a.pick.split(",")} if a.pick else None
    fixed = tuple(float(v) for v in a.facecam.split(",")) if a.facecam else None
    face = None
    if not fixed and a.layout != "blur":
        face = detect_faces(video, t0, t1, meta)   # one pass over the whole VOD: the cam stays put
        print(f"  face cam: {'found at ' + ','.join(str(int(v)) for v in face) if face else 'none, using blur layout'}")
    for c in cands:
        if pick and c["n"] not in pick: continue
        if fixed:
            x, y, w, h = fixed; gw = min(meta["w"], meta["h"] * 1080 / 1220)
            lay = {"kind": "split", "cam": fixed, "game": ((meta["w"] - gw) / 2, 0, gw, meta["h"])}
        else:
            lay = plan_layout(face, meta, a.layout)
        _, cap_y = vf_for(lay)
        ass = None
        if not a.no_captions:
            ass = work / f"clip_{c['n']:02d}.ass"; write_ass(ass, words, c["start"], c["end"], cap_y, c["hook"])
        dst = out / f"clip_{c['n']:02d}.mp4"
        render(video, dst, c["start"], c["end"], lay, ass, meta["fps"])
        c["layout"] = lay["kind"]; c["file"] = dst.name
        title = (c["hook"] or c["text"][:60]).capitalize().rstrip(",")
        kit = [f"TITLE (≤ 60 chars, put the payoff first):\n{title[:60]}", "",
               "CAPTION:", f"{title} 😭" + (f"\n\nClip from {a.credit}" if a.credit else ""), (a.tags or "").strip(), "",
               f"CLIP: {fmt(c['start'])} → {fmt(c['end'])} of the VOD · score {c['score']}",
               "CHECK: captions spelled right · on-screen text not covering the face · no copyrighted music"]
        (out / f"clip_{c['n']:02d}.txt").write_text("\n".join(kit) + "\n")
        print(f"  ✓ {dst}  ({lay['kind']} layout)")
    (out / "candidates.json").write_text(json.dumps(cands, indent=1))


if __name__ == "__main__":
    main()
