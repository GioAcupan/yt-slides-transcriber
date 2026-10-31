# /// script
# requires-python = ">=3.10"
# dependencies = ["yt-dlp[default]", "opencv-python-headless", "numpy"]
# ///
"""Pull the distinct slides out of a slides-only lecture video.

Usage:
    uv run extract_slides.py <youtube-url-or-local-video> [--out transcripts]

Writes <out>/<video-slug>/slides/slide_NNN.png plus manifest.json. Each slide
image is the *final* state of that slide, so build-up animations (bullets or
equations appearing one by one) collapse into a single image.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

COMPARE_WIDTH = 480
PIXEL_DIFF = 30  # grey-level change that counts as a "changed" pixel
INK_DIST = 40  # distance from the background colour that counts as content


def download(url: str, workdir: Path) -> tuple[Path, dict]:
    import yt_dlp

    args = [
        # No audio needed, and a single video-only stream avoids needing ffmpeg.
        "-f", "bv*[height<=1080][vcodec^=avc1]/bv*[height<=1080][vcodec^=vp]/bv*[height<=1080]/b",
        "-o", str(workdir / "%(id)s.%(ext)s"),
        "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
    ]
    # YouTube needs a JS runtime for its challenges; yt-dlp only tries deno by default.
    if not shutil.which("deno") and shutil.which("node"):
        args += ["--js-runtimes", "node"]
    opts = yt_dlp.parse_options(args).ydl_opts
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(info["requested_downloads"][0]["filepath"])
    return path, {"title": info.get("title"), "url": info.get("webpage_url", url)}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "video"


def sample_frames(video: Path, every: float):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        sys.exit(f"Could not open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps * every))
    i = 0
    while cap.grab():
        if i % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                yield i / fps, frame
        i += 1
    cap.release()


def to_grey(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (COMPARE_WIDTH, round(h * COMPARE_WIDTH / w)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def changed_mask(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return cv2.absdiff(a, b) > PIXEL_DIFF


def ink_mask(grey: np.ndarray) -> np.ndarray:
    background = np.bincount(grey.ravel(), minlength=256).argmax()
    return np.abs(grey.astype(np.int16) - int(background)) > INK_DIST


def find_stable_states(video: Path, every: float, min_hold: float, stable_frac: float) -> list[dict]:
    """Group samples into runs where the picture barely changes; keep each run's last frame."""
    states: list[dict] = []
    run = None
    prev_grey = None

    def close(run):
        if run and run["end"] - run["start"] >= min_hold:
            states.append(run)

    for t, frame in sample_frames(video, every):
        grey = to_grey(frame)
        if prev_grey is not None and changed_mask(prev_grey, grey).mean() < stable_frac:
            run.update(end=t, frame=frame, grey=grey)
        else:
            close(run)
            run = {"start": t, "end": t, "frame": frame, "grey": grey}
        prev_grey = grey
    close(run)
    return states


def merge_builds(states: list[dict], stable_frac: float) -> list[dict]:
    """Drop states that are duplicates of, or only partial builds of, the next state."""
    merged: list[dict] = []
    for state in states:
        if merged:
            prev = merged[-1]
            changed = changed_mask(prev["grey"], state["grey"])
            if changed.mean() < stable_frac:
                is_continuation = True
            else:
                # A build-up only adds content: nearly all changed pixels were background before.
                removed = (changed & ink_mask(prev["grey"])).sum() / changed.sum()
                is_continuation = removed < 0.05
            if is_continuation:
                state["start"] = prev["start"]
                merged[-1] = state
                continue
        merged.append(state)
    return merged


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="YouTube URL or path to a local video file")
    p.add_argument("--out", default="transcripts", help="output root directory (default: transcripts)")
    p.add_argument("--every", type=float, default=0.5, help="seconds between sampled frames (default: 0.5)")
    p.add_argument("--min-hold", type=float, default=1.0,
                   help="seconds a picture must stay still to count as a slide (default: 1.0)")
    p.add_argument("--sensitivity", type=float, default=0.004,
                   help="fraction of changed pixels below which two frames count as the same (default: 0.004)")
    p.add_argument("--keep-video", action="store_true", help="keep the downloaded video next to the slides")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        local = Path(args.source)
        if local.exists():
            video, meta = local, {"title": local.stem, "url": None}
        else:
            print(f"Downloading {args.source} ...", file=sys.stderr)
            video, meta = download(args.source, Path(tmp))

        out_dir = Path(args.out) / slugify(meta["title"] or video.stem)
        slides_dir = out_dir / "slides"
        if slides_dir.exists():
            shutil.rmtree(slides_dir)
        slides_dir.mkdir(parents=True)

        print("Detecting slides ...", file=sys.stderr)
        states = find_stable_states(video, args.every, args.min_hold, args.sensitivity)
        slides = merge_builds(states, args.sensitivity)

        entries = []
        for n, slide in enumerate(slides, 1):
            name = f"slide_{n:03d}.png"
            cv2.imwrite(str(slides_dir / name), slide["frame"])
            entries.append({"slide": n, "file": f"slides/{name}",
                            "start": fmt_time(slide["start"]), "end": fmt_time(slide["end"])})

        if args.keep_video and not local.exists():
            shutil.copy2(video, out_dir / video.name)

    manifest = {**meta, "slide_count": len(entries), "slides": entries}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(entries)} slides -> {out_dir.resolve()}", file=sys.stderr)
    print(out_dir.resolve())


if __name__ == "__main__":
    main()
