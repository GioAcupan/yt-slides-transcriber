---
name: transcribe-slides
description: Turn slides-only (no audio) lecture videos — usually YouTube links — into standalone Markdown lecture notes with LaTeX math. Use when the user gives one or more YouTube URLs, video files, or a text file of URLs of lecture slides and wants the slide content as text/notes.
argument-hint: <url-or-video-path ...> | <urls.txt>
---

# Lecture notes from slides-only videos

The videos are PowerPoint-style slides with no audio, mostly math. The goal is a clear,
standalone lecture note built from the text on the slides: someone who never saw the video
should be able to study from it. It is not a slide-by-slide transcript, and not a summary
or an explanation either: everything the slides teach is there, nothing that isn't.

You (the main agent) only coordinate. Sonnet subagents write and check the notes, one video
each, so a backlog doesn't fill your context with slide images.

## Coordinating

`<repo>` below is the absolute path of the folder containing `extract_slides.py`; always
give subagents absolute paths.

1. **Collect the videos** from `$ARGUMENTS`: URLs and video paths, or a `.txt` file with one
   per line (skip blank lines and lines starting with `#`).
2. **Skip finished ones.** For a YouTube URL, take the video id (the `v=` value, or the path
   after `youtu.be/`). If `<repo>/transcripts/*-<id>/notes.md` exists, it is done — skip it
   and say so, unless the user asked to redo it.
3. **Write notes.** For each remaining video, start a background subagent with the Agent
   tool (`subagent_type: "general-purpose"`, `model: "sonnet"`) using the writer prompt
   below. Run at most 3 at a time; start the next one as each finishes. More than that
   makes the downloads and frame decoding compete, and YouTube may throttle.
4. **Check.** When a writer finishes, start a checker subagent (`model: "sonnet"`) on its
   folder with the checker prompt below. Skip this step only if the user said to.
5. **Report** once everything is done: one line per video with its `notes.md` path, how
   many fixes the checker made, and anything left `[unclear]` or flagged as odd. Mention
   any video that failed (private, removed, download error) instead of retrying it forever.

### Writer prompt

> Write lecture notes for one slides-only lecture video. Follow the "Per-video procedure"
> (steps 1–3) in `<repo>/.claude/skills/transcribe-slides/SKILL.md` exactly — read that
> file first. Video: `<url-or-path>`. Run commands from `<repo>`.
> When done, reply with only: the output folder path, the slide count, which slides you
> re-checked in step 3, any `[unclear]` items, and anything odd (e.g. a slide that
> contradicts itself, an extractor re-run with different settings).

### Checker prompt

> Check lecture notes against the slide images they were written from. Folder: `<folder>`.
> It has `slides/slide_NNN.png`, `manifest.json`, and `notes.md`. The rules for the notes
> are under "Note rules" in `<repo>/.claude/skills/transcribe-slides/SKILL.md` — read them.
> Open every slide image with the Read tool, in order, and find where its content is in the
> notes. Check every symbol, sub/superscript, number, table cell, and word of definitions,
> rules, and problems; that nothing the slides teach is missing; and that nothing was added
> that isn't on the slides (beyond connecting words and headings). Ignore channel
> intros/outros, decorations, and the repeating footer/logo.
> Fix errors you are certain of directly in `notes.md` with the Edit tool, including adding
> missing content where it belongs. If a value is genuinely ambiguous in the image, don't
> change it — mark it `[unclear: ...]` instead.
> Reply with only: the list of fixes (where, was → now), the ambiguous items, and a final
> line "Checked N slides, fixed K."

## Per-video procedure

### 1. Extract the slides

```bash
uv run extract_slides.py "<url-or-path>" --out transcripts
```

The last stdout line is the output folder (`transcripts/<title>-<video id>/`). It contains
`manifest.json` (title, url, and each slide's file and start/end time) and
`slides/slide_NNN.png`. Each image is the final state of a slide, so build-up animations
are mostly collapsed already. If that folder already has `manifest.json` and `slides/`,
skip this step.

If the slide count looks wrong for the video length (e.g. 0, or far more than plausible),
re-run with a tweak and say what you changed:
- slides missing / merged together → `--sensitivity 0.002`
- many near-duplicate slides → `--sensitivity 0.01` or `--min-hold 2`

### 2. Write the notes

Read `manifest.json`, then view the slide images **in order**, a few at a time (about 5
Read calls in parallel per batch). After each batch, add that batch's content to
`<output folder>/notes.md` so progress is saved as you go. Use the Write/Edit tools for
this, not shell heredocs: the shell can collapse LaTeX's `\\` into `\`. Later slides often
continue or complete what earlier ones started, so edit earlier parts of the file when
needed instead of repeating them.

Start the file with:

```markdown
# <lecture title>

*Source: <url>*
```

#### Note rules

- **Organise by topic, in lecture order.** Use `##`/`###` headings for the lecture's
  topics, taken from slide titles where there are any (e.g. `## Method A: Conditional-form
  Method`, `### Example 1`). No slide numbers, timestamps, or per-slide sections.
- **Each thing once.** When several slides show the same content building up (an empty
  table, then filled; a problem, then the problem with its answer), write it once in its
  most complete form. Never merge different content into one: if a later slide shows a
  different state on purpose (values blanked out to highlight some columns, a different
  row boxed), describe that in words rather than overwriting the earlier version.
- **Keep the professor's words** for definitions, rules, theorems, problem statements, and
  conclusions. You may join fragments into sentences, turn labels into lists or headings,
  and add short connecting words ("For example:", "Steps:"). Do not add explanations,
  examples, steps, or facts that aren't on the slides, and do not solve, simplify, or
  correct anything. If a slide contradicts itself, write it as shown and add
  `*(as written on the slide)*` with a short note.
- **No colours.** Where colour, a box, or a circle marks the key term, the answer, or the
  deciding row/column, use **bold** or say it in words ("the main-connective column is all
  T"). Callout boxes with a rule or definition become a blockquote.
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
- **Tables** as Markdown tables with every cell as shown (truth tables: one column per
  column on the slide, same order).
- **Figures, graphs, diagrams** that carry content: describe them briefly in italics — what
  is plotted, axes and labels, key points, shaded regions — and include any text in them.
  Skip decoration: mascots, stick figures, the channel's intro/outro, "like and subscribe",
  the repeating footer/logo.
- "Common mistake" or right/wrong slides (✓ / ✗ marks): say which statement is wrong and
  which is right, in words.
- If something is genuinely unreadable, write `[unclear: best guess]` rather than inventing.

### 3. Check (required)

When the notes are done, re-open the images (Read them again) of the 3–5 slides with the
densest math or largest tables and compare them symbol by symbol against the notes; fix any
mismatches. Don't check by re-deriving the math or truth values yourself: the notes must
match the image, not what the answer should be. Then read `notes.md` top to bottom once to
make sure it reads as a coherent lecture note with nothing repeated. Say which slides you
re-checked in your reply.
