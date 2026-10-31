---
name: transcribe-slides
description: Transcribe a slides-only (no audio) lecture video — usually a YouTube link — into Markdown with LaTeX math. Use when the user gives a YouTube URL or video file of lecture slides and wants the slide content as text/notes.
argument-hint: <youtube-url-or-video-path> [more urls...]
---

# Transcribe slides-only lecture videos

The videos are PowerPoint-style slides with no audio, mostly math. The goal is a faithful,
readable Markdown copy of what is on the slides — not a summary, not an explanation.

## 1. Extract the slides

Run from the repository root, once per video in `$ARGUMENTS`:

```bash
uv run extract_slides.py "<url-or-path>" --out transcripts
```

The last stdout line is the output folder. It contains `manifest.json` (title, url, and each
slide's file and start/end time) and `slides/slide_NNN.png`. Each image is the final state
of a slide, so build-up animations are already collapsed.

If the slide count looks wrong for the video length (e.g. 0, or far more than plausible),
re-run with a tweak and say what you changed:
- slides missing / merged together → `--sensitivity 0.002`
- many near-duplicate slides → `--sensitivity 0.01` or `--min-hold 2`

## 2. Transcribe

Read `manifest.json`, then view the slide images **in order**, a few at a time (about 5
Read calls in parallel per batch). After each batch, append that batch's transcription to
`<output folder>/transcript.md` so progress is saved as you go.

Start the file with:

```markdown
# <video title>

Source: <url> · <N> slides
```

Then for each slide:

```markdown
---

## Slide <n> · <start>–<end> — <slide title, or a short label if it has none>

<content>
```

### Transcription rules

- **Verbatim.** Copy the slide's words and math as written. Do not solve, simplify, correct,
  complete, or explain anything. Keep the professor's notation even if unusual.
- **Math in LaTeX**: inline `$...$`, display `$$...$$` on their own lines. Use the matching
  constructs: `\frac`, `\sqrt`, `\int_a^b`, `\sum_{n=1}^{\infty}`, `\lim_{x \to 0}`,
  `\begin{bmatrix}`/`pmatrix`/`vmatrix` as drawn, `\begin{cases}` for piecewise,
  `\begin{aligned}` with `&=` for multi-line derivations, `\mathbb{R}`, `\vec{v}` vs
  `\mathbf{v}` vs `\hat{\imath}` exactly as shown, primes as `f'(x)`.
- Look closely at characters that are easy to confuse in math: `x`/`\times`, `\epsilon`/`\in`,
  `\nu`/`v`, `1`/`l`/`I`, `0`/`O`/`\theta`, `-`/`\pm`/`\mp`, `\le`/`<`, subscripts vs
  superscripts, and what a fraction bar or radical actually spans.
- Keep structure: bullets and numbering as on the slide, **bold**/*italic* where the slide
  emphasises, Markdown tables for tables. If colour is used to mean something (e.g. a term
  highlighted in red), note it: `$x^2$ (in red)`.
- **Figures, graphs, diagrams**: describe them in an italic block — what is plotted, axes and
  labels, key points/intercepts/asymptotes, shaded regions, arrows — so the slide still
  makes sense without the image. Transcribe any text or labels inside the figure exactly.
- If two consecutive images are the same slide (a leftover animation step), transcribe
  it once using the most complete image and give it the combined time range.
- If something is genuinely unreadable, write `[unclear: best guess]` rather than inventing.

## 3. Check

After all slides are done, re-open the 3–5 slides with the densest math and compare them
symbol by symbol against the transcript; fix any mismatches. Then tell the user the path to
`transcript.md`, the slide count, and anything flagged `[unclear]`.
