# yt-slides-transcriber

Turns a silent, slides-only lecture video (YouTube link or local file) into standalone
Markdown lecture notes, with math written as LaTeX.

Two parts:

1. **`extract_slides.py`** downloads the video and saves one image per slide. It keeps the
   final state of each slide, so bullets or equations that animate in collapse into one image.
2. **The `/transcribe-slides` Claude Code skill** hands each video to a Sonnet subagent that
   runs the extractor, reads the slide images in order, and writes `transcripts/<video>/notes.md`:
   the slide text organised by topic, each thing once, with no slide numbers or timestamps.
   A second Sonnet subagent then checks the notes against the images and fixes mistakes.

## Requirements

- [uv](https://docs.astral.sh/uv/) (it installs the Python dependencies automatically)
- Node.js or Deno on `PATH` (yt-dlp needs a JS runtime for YouTube)
- Claude Code, for the transcription step

No ffmpeg needed: only the video stream is downloaded.

## Usage

From this folder, in Claude Code:

```
/transcribe-slides https://www.youtube.com/watch?v=...
```

For a backlog, pass several links, or a text file with one link per line (`#` comments
allowed). Up to 3 videos run at once, and videos that already have a `notes.md` are
skipped, so you can re-run the same list as it grows:

```
/transcribe-slides backlog.txt
```

Output, one folder per video:

```
transcripts/<video-title>-<video-id>/
  manifest.json      slide list with timestamps
  slides/            slide_001.png, slide_002.png, ...
  notes.md           the lecture notes ($...$ / $$...$$ math renders in Obsidian, VS Code, GitHub)
```

To only grab the slide images:

```
uv run extract_slides.py <url-or-file> [--out transcripts]
```

If YouTube says "Sign in to confirm you're not a bot" (it does after several downloads in a
row), pass your browser login. Cookies are read straight from the browser profile; no
cookies file is written.

```
uv run extract_slides.py <url> --cookies-from-browser chrome
uv run extract_slides.py <url> --cookies-from-browser "firefox:C:\Users\you\AppData\Roaming\zen\Profiles\xxxx.Default (release)"
```

(Zen and other Firefox-based browsers use `firefox:` plus the profile folder.)

### Tuning

| Symptom | Fix |
|---|---|
| Slides missing or merged | `--sensitivity 0.002` |
| Near-duplicate slides | `--sensitivity 0.01` or `--min-hold 2` |
| Text that's on screen for under half a second is cut off | `--min-hold 0.25` |
