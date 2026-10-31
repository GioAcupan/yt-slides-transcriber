---
name: transcribe-slides
description: Transcribe slides-only (no audio) lecture videos — usually YouTube links — into Markdown with LaTeX math. Use when the user gives one or more YouTube URLs, video files, or a text file of URLs of lecture slides and wants the slide content as text/notes.
argument-hint: <url-or-video-path ...> | <urls.txt>
---

# Transcribe slides-only lecture videos

The videos are PowerPoint-style slides with no audio, mostly math. The goal is a faithful,
readable Markdown copy of what is on the slides — not a summary, not an explanation.

You (the main agent) only coordinate. Sonnet subagents do the transcribing and checking, one
video each, so a backlog doesn't fill your context with slide images.

## Coordinating

`<repo>` below is the absolute path of the folder containing `extract_slides.py`; always
give subagents absolute paths.

1. **Collect the videos** from `$ARGUMENTS`: URLs and video paths, or a `.txt` file with one
   per line (skip blank lines and lines starting with `#`).
2. **Skip finished ones.** For a YouTube URL, take the video id (the `v=` value, or the path
   after `youtu.be/`). If `<repo>/transcripts/*-<id>/transcript.md` exists, it is done — skip
   it and say so, unless the user asked to redo it.
3. **Transcribe.** For each remaining video, start a background subagent with the Agent tool
   (`subagent_type: "general-purpose"`, `model: "sonnet"`) using the transcriber prompt
   below. Run at most 3 at a time; start the next one as each finishes. More than that
   makes the downloads and frame decoding compete, and YouTube may throttle.
4. **Check.** When a transcriber finishes, start a checker subagent (`model: "sonnet"`) on
   its folder with the checker prompt below. Skip this step only if the user said to.
5. **Report** once everything is done: one line per video with its `transcript.md` path,
   slide count, how many fixes the checker made, and anything left `[unclear]` or flagged as
   odd. Mention any video that failed (private, removed, download error) instead of retrying
   it forever.

### Transcriber prompt

> Transcribe one slides-only lecture video. Follow the "Per-video procedure" (steps 1–3) in
> `<repo>/.claude/skills/transcribe-slides/SKILL.md` exactly — read that file first.
> Video: `<url-or-path>`. Run commands from `<repo>`.
> When done, reply with only: the output folder path, the slide count, which slides you
> merged as animation steps, which slides you re-checked in step 3, any `[unclear]` items,
> and anything odd (e.g. a slide held for minutes, a slide that contradicts itself, an
> extractor re-run with different settings).

### Checker prompt

> Check a lecture-slide transcription against its slide images. Folder: `<folder>`. It has
> `slides/slide_NNN.png`, `manifest.json`, and `transcript.md` (sections headed
> `## Slide N`, or `## Slides N–M` for merged animation steps). The transcript should be
> verbatim, with math in LaTeX, tables as Markdown tables, and colours noted in italics; the
> rules are under "Transcription rules" in `<repo>/.claude/skills/transcribe-slides/SKILL.md`.
> Open every slide image with the Read tool and compare it to its section: every symbol,
> sub/superscript, number, table cell, and word; nothing missing or added; headings'
> times match `manifest.json`. Check merged `## Slides N–M` sections against the merging
> rule: if the earlier image has anything the later one lacks, or the section copies values
> from another slide, split it and transcribe each image as shown. Don't flag layout choices
> (e.g. `array` for stacked premises) or the omitted repeating footer/logo.
> Fix errors you are certain of directly in `transcript.md` with the Edit tool. If a value is
> genuinely ambiguous in the image, don't change it — mark it `[unclear: ...]` instead.
> Reply with only: the list of fixes (slide, was → now), the ambiguous items, and a final
> line "Checked N slides, fixed K."

## Per-video procedure

### 1. Extract the slides

```bash
uv run extract_slides.py "<url-or-path>" --out transcripts
```

The last stdout line is the output folder (`transcripts/<title>-<video id>/`). It contains
`manifest.json` (title, url, and each slide's file and start/end time) and
`slides/slide_NNN.png`. Each image is the final state of a slide, so build-up animations
are already collapsed.

If the slide count looks wrong for the video length (e.g. 0, or far more than plausible),
re-run with a tweak and say what you changed:
- slides missing / merged together → `--sensitivity 0.002`
- many near-duplicate slides → `--sensitivity 0.01` or `--min-hold 2`

### 2. Transcribe

Read `manifest.json`, then view the slide images **in order**, a few at a time (about 5
Read calls in parallel per batch). After each batch, append that batch's transcription to
`<output folder>/transcript.md` so progress is saved as you go. Use the Write/Edit tools for
this, not shell heredocs: the shell can collapse LaTeX's `\\` into `\`.

Start the file with:

```markdown
# <video title>

Source: <url> · <N> slides
```

If every slide repeats the same footer or logo, note it once under the header instead of on
every slide. Then for each slide:

```markdown
---

## Slide <n> · <start>–<end> — <slide title, or a short label if it has none>

<content>
```

#### Transcription rules

- **Verbatim.** Copy the slide's words and math as written. Do not solve, simplify, correct,
  complete, or explain anything. Keep the professor's notation even if unusual. If a slide
  contradicts itself, transcribe it as shown and add a short italic note.
- **Math in LaTeX**: inline `$...$`, display `$$...$$` on their own lines. Use the matching
  constructs: `\frac`, `\sqrt`, `\int_a^b`, `\sum_{n=1}^{\infty}`, `\lim_{x \to 0}`,
  `\begin{bmatrix}`/`pmatrix`/`vmatrix` as drawn, `\begin{cases}` for piecewise,
  `\begin{aligned}` with `&=` for multi-line derivations, `\mathbb{R}`, `\vec{v}` vs
  `\mathbf{v}` vs `\hat{\imath}` exactly as shown, primes as `f'(x)`. Logic: `\to`,
  `\leftrightarrow`, `\land`, `\lor`, `\sim` (if the slide uses ~) or `\neg` (if it uses ¬),
  `\therefore`; stacked premises/conclusion as a `\begin{array}{rl}` with `\therefore &` on
  the last line.
- Look closely at characters that are easy to confuse in math: `x`/`\times`, `\epsilon`/`\in`,
  `\nu`/`v`, `1`/`l`/`I`, `0`/`O`/`\theta`, `-`/`\pm`/`\mp`, `\le`/`<`, `\land`/`\lor`,
  subscripts vs superscripts, and what a fraction bar or radical actually spans.
- Keep structure: bullets and numbering as on the slide, **bold**/*italic* where the slide
  emphasises, Markdown tables for tables (truth tables: one column per column on the slide,
  same order). If colour is used to mean something (e.g. a term highlighted in red), note
  it: `$x^2$ (in red)`. Note circled/boxed cells or rows.
- **Figures, graphs, diagrams**: describe them in an italic block — what is plotted, axes and
  labels, key points/intercepts/asymptotes, shaded regions, arrows — so the slide still
  makes sense without the image. Transcribe any text or labels inside the figure exactly.
- **Each section describes one image.** Never copy text, values, or table cells from
  another slide, even if a slide shows a table with cells blanked out or a step removed:
  transcribe the blanks as blanks (an empty cell, or `—` with a note).
- **Merging is rare.** The extractor already collapses build-ups, so consecutive images
  usually differ for a reason (a callout appears while a highlight moves, values are
  cleared, a row is boxed). Merge two images into one `## Slides <n>–<m>` section (combined
  time range) only when the earlier one is a half-finished animation frame: text mid-flight
  or overlapping itself, a half-drawn shape, an empty table, a wipe in progress. Everything
  it shows must also appear in the later image, so you transcribe only the later image.
  If anything on the earlier image is missing or different on the later one, give them
  separate sections. Don't write "slide X only" notes inside a section.
- Frames with no lecture content (the channel's intro/outro animation, a blank board, a
  "like and subscribe" end card) get one line each, e.g. `*(channel intro animation)*`, or
  one merged section for a run of them.
- If something is genuinely unreadable, write `[unclear: best guess]` rather than inventing.

### 3. Check (required)

After all slides are done, re-open the images (Read them again) of the 3–5 slides with the
densest math or largest tables and compare them symbol by symbol against the transcript; fix
any mismatches. Don't check by re-deriving the math or truth values yourself: the
transcript must match the image, not what the answer should be. Also confirm every
merged section follows the merging rule above. Say which slides you re-checked in your reply.
