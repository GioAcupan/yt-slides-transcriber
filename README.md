# yt-slides-transcriber

Turns a silent, slides-only lecture video (YouTube link or local file) into Markdown notes,
with math written as LaTeX.

Two parts:

1. **`extract_slides.py`** downloads the video and saves one image per slide. It keeps the
   final state of each slide, so bullets or equations that animate in collapse into one image.
2. **The `/transcribe-slides` Claude Code skill** hands each video to a Sonnet subagent that
   runs the extractor, reads each slide image, and writes `transcripts/<video>/transcript.md`.
   A second Sonnet subagent then checks the transcript against the images and fixes mistakes.

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
allowed). Up to 3 videos run at once, and videos that already have a `transcript.md` are
skipped, so you can re-run the same list as it grows:

```
/transcribe-slides backlog.txt
```

Output, one folder per video:

```
transcripts/<video-title>-<video-id>/
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
