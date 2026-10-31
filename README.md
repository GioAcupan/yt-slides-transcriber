# yt-slides-transcriber

Turns a silent, slides-only lecture video (YouTube link or local file) into Markdown notes,
with math written as LaTeX.

Two parts:

1. **`extract_slides.py`** downloads the video and saves one image per slide. It keeps the
   final state of each slide, so bullets or equations that animate in collapse into one image.
2. **The `/transcribe-slides` Claude Code skill** runs the extractor, has Claude read each
   slide image, and writes `transcripts/<video>/transcript.md`.

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

Output:

```
transcripts/<video-title>/
  manifest.json      slide list with timestamps
  slides/            slide_001.png, slide_002.png, ...
  transcript.md      the notes ($...$ / $$...$$ math renders in Obsidian, VS Code, GitHub)
```

To only grab the slide images:

```
uv run extract_slides.py <url-or-file> [--out transcripts]
```

### Tuning

| Symptom | Fix |
|---|---|
| Slides missing or merged | `--sensitivity 0.002` |
| Near-duplicate slides | `--sensitivity 0.01` or `--min-hold 2` |
| Slides flash by quickly | `--min-hold 0.5` |
