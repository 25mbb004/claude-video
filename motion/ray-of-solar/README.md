# Ray of Solar: motion toolkit

Code-built motion graphics for a music-video channel, made for *Ray of Solar* (Swedish House Mafia).
Everything here is procedural: shaders, canvas and three.js, rendered frame by frame with headless
Chromium and muxed with ffmpeg. No stock footage and no AI video. Every visual parameter is keyed to a beat map.

The song audio and rendered videos are **not** in the repo (copyright and size). Bring your own audio file.

## What's here

| Folder | What it is |
|---|---|
| `analysis/` | `beat_analyze.py` (BPM, beat grid, bars, phrases, energy table), the Ray of Solar `beatmap.json`, `markers.csv` for AE/Premiere, and `lyrics.srt` |
| `render/` | The style-frame shaders and the **Ink Ridges** animator (the chosen style) |
| `board/` | The style-frames presentation page (5 styles + the C+D merge, 3 key frames each) |
| `eclipse/` | First attempt: a three.js dark-cinematic scene (eclipse, fog, god rays). Kept for reference. |

### The five styles (`render/`)
| | Style | File | Engine |
|---|---|---|---|
| A | Storm Ascent | `storm.frag` | volumetric raymarched clouds, fractal lightning |
| B | Liquid Chrome | `chrome.frag` | raymarched SDF, ferrofluid spikes, one inter-reflection bounce |
| C | Gold Ink | `ink.frag` | 3-level domain-warped fbm, metallic sheen from the gradient |
| D | Ridge Lines | `ridge.html` | canvas 2D, 96 occluding terrain lines |
| E | Brutalist Type | `type.html` | HTML/CSS type, Inter Display + JetBrains Mono |
| C+D | **Ink Ridges** | `merge.html` (stills), `anim.html` (15 s), `anim2.html` (1:41 cut) | ridge terrain painted with live gold ink |

## Ray of Solar facts (from the analysis)
- **136 BPM** four-on-the-floor (beat 0.443 s, bar 1.772 s), key ≈ F♯ minor
- Drop 1 downbeat **1:03.82**; silence 1:02.70 → 1:03.82; snare roll ≈ 0:56.8 → 1:02.6
- Bar lines: `1:03.82 + k × 1.772`. The long cut runs bar −27 → bar 30 (0:15.98 → 1:56.98, 101 s).
- Sections, bar by bar: groove + lyrics 0:16–0:35 · breakdown (bass out) 0:35–0:50 · bass back 0:50–0:57 · build 0:57–1:02.7 · drop 1:03.8–1:32 · filter dip 1:32–1:39 · groove + lyrics 1:39–1:58
- Lyrics (two lines alternating, each 4 bars): see `analysis/lyrics.srt`

## Requirements
- Node 20+ with **Playwright** and Chromium (renderers use SwiftShader WebGL, no GPU needed)
- ffmpeg, Python 3 with `librosa` and `scipy` (for analysis)
- Fonts: Inter / Inter Display, JetBrains Mono (installed system-wide)

Run renderers with `NODE_PATH=$(npm root -g)` if Playwright is installed globally.

## Recipes

**1. Analyse a song**
```bash
ffmpeg -i song.mp4 -vn -ac 1 -ar 22050 audio.wav
python3 analysis/beat_analyze.py audio.wav analysis --downbeat 63.82 --beat 0.443
```

**2. Render style frames** (writes PNGs to `render/out/`)
```bash
cd render
node snap.mjs out "shader.html?s=chrome&shot=2&tiles=8=chrome_2"   # shot 0 build · 1 silence · 2 drop
node snap.mjs out "ridge.html?shot=2=ridge_2" "type.html?shot=2=type_2"
```
`merge.html` needs the ink stills first: render `ink` shots 0, 1 and 2 as `out/ink_0.png`, `out/ink_1.png` and `out/ink_2.png`.

**3. Render the Ink Ridges video**
```bash
cd render
node animrender2.mjs frames 24                       # full 1:41 cut → frames/f_00000.jpg …
RANGE=0-1124 node animrender2.mjs frames 24          # re-render only a frame range after a fix
node animrender2.mjs test 24 56.6,64.5,90            # spot-check single song times
ffmpeg -ss 15.98 -t 101 -i song.mp4 -vn -af "afade=t=in:d=0.6,afade=t=out:st=99.9:d=1.1" long.wav
ffmpeg -framerate 24 -i frames/f_%05d.jpg -i long.wav -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -b:a 320k -shortest out.mp4
```
`anim2.html` takes **song time**. All the timing (chapters, lyric times, roll onsets, drop) is in the constants at the top of the script. Change those to retime it for another song.

## Reusing for a new song
1. Run the analysis and note the drop downbeat, BPM and section boundaries from the energy table.
2. Copy `render/anim2.html` and edit `DROP`, `BEAT`, the `CH` chapter table, `ROLL` onsets and `LYRICS`.
3. Spot-check a few times, then render and mux.

Known gotchas: tempo trackers can lock to 2/3 tempo, so check the kick spacing. Any sky element should fade through a continuous curve rather than switch on a chapter boundary (that's how the sun popped at 0:40 in v1).
