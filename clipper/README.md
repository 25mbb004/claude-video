# clipper

Turns a stream VOD into ready-to-post vertical clips for TikTok, YouTube Shorts and Instagram Reels.

1. **Download** a URL with yt-dlp, or use a local file
2. **Transcribe** with word-level timings (Groq or OpenAI Whisper, using the same key as the `/watch` skill in `~/.config/watch/.env`)
3. **Find the hype moments.** Each moment is scored on:
   - loudness spikes measured against *that streamer's* normal volume (screams, yelling)
   - hype words: "clip that", "no way", "let's go", "oh my god", laughter, plus your own `--keywords`
   - talking speed
4. **Cut** the top N non-overlapping moments, snapped to sentence edges (15–45 s by default)
5. **Render 1080×1920**, picking a layout automatically:
   - `split`: face cam on top, gameplay below (face cam found automatically, or set it with `--facecam`)
   - `crop`: follows the face (just chatting / IRL)
   - `blur`: no face found, so a 16:9 frame over a blurred fill
6. **Burn in captions** word by word, uppercase, with the active word in yellow, plus a 3-second **hook title**. Audio is normalised to −14 LUFS.
7. Write a **post kit** per clip (`clip_NN.txt`): title, caption, credit line and hashtags

## Requirements
`ffmpeg`, Python 3 with `numpy`, `scipy`, `opencv-python-headless<5` (OpenCV 5 dropped the Haar face detector) and `yt-dlp`, plus a Groq (or OpenAI) API key.
```bash
pip install numpy scipy "opencv-python-headless<5" yt-dlp
```

## Usage
```bash
# 1. score a VOD and list candidates without rendering
python3 clipper/clipper.py "https://www.twitch.tv/videos/…" --out clips --n 10 --dry-run

# 2. render the ones you like, with credit and tags in the post kit
python3 clipper/clipper.py "https://www.twitch.tv/videos/…" --out clips --n 10 --pick 1,2,5 \
    --credit "@streamer on Twitch" --tags "#streamer #gta6 #fyp"

# long VOD: only look at a section
python3 clipper/clipper.py vod.mp4 --start 1:20:00 --end 2:10:00 --n 8

# the streamer has catchphrases? make them count as hype
python3 clipper/clipper.py vod.mp4 --keywords "chat is this real,we're so back"

# face cam detected wrong? set it in source pixels (x,y,w,h)
python3 clipper/clipper.py vod.mp4 --facecam 40,620,420,420
```
The transcript is cached in `clips/.work/`, so re-running with different `--pick`, `--hook` or `--layout` doesn't pay for transcription again.

## Notes
- **Only clip streams you're allowed to clip**, for example a paid clipping campaign or a streamer who allows it. Credit the streamer.
- YouTube often blocks downloads from cloud servers ("confirm you're not a bot"). Run it on your own computer, or pass yt-dlp cookies.
- Music playing on stream can trigger copyright claims. Check before you post.
- Captions come from Whisper, so read them before posting, especially names and slang.
