# Task Decomposition: Multi-Step Reasoning Strategies

A Claude Associate course lesson for the Skool community, made fully locally with
[simpligen](https://github.com/rifaterdemsahin/simpligen) and edited by the rules of the
**edu-film-edit** skill ([skill.md](skill.md)).

**Learning objective:** after this, the viewer can break a big business request into a chain of
checkable steps that Claude reasons through one at a time.

## Links

| What | Link |
| --- | --- |
| Watch the lesson (GitHub Pages) | https://rifaterdemsahin.github.io/task-decomposition-video/ |
| Video file | https://rifaterdemsahin.github.io/task-decomposition-video/task-decomposition.mp4 |
| Captions (SRT) | https://rifaterdemsahin.github.io/task-decomposition-video/task-decomposition.srt |
| QA report | https://rifaterdemsahin.github.io/task-decomposition-video/task-decomposition.qa.json |
| Production board (Pages) | https://rifaterdemsahin.github.io/task-decomposition-video/kanban.html |
| Effort report (Pages) | https://rifaterdemsahin.github.io/task-decomposition-video/effort.html |
| Mac FLUX one-liner (Pages) | https://rifaterdemsahin.github.io/task-decomposition-video/mac-flux.html |
| skool-course-video-creator skill (Pages) | https://rifaterdemsahin.github.io/task-decomposition-video/skill.html |
| Research notes (Claude doc) | https://claude.ai/artifact/CLrGTg5UoMx7UdJHjoMYNg |
| Production board (Claude artifact) | https://claude.ai/artifact/JeK93WVKQAui3G8Lwrt8se |
| Effort report (Claude artifact) | https://claude.ai/artifact/54ereVfN9t1hiQnTbhtLLj |
| Source code | https://github.com/rifaterdemsahin/task-decomposition-video |
| Renderer upstream | https://github.com/rifaterdemsahin/simpligen |

The Claude links are private to the owner until shared from each page's Share menu.

## Output

| File | What it is |
| --- | --- |
| `video/out/task-decomposition.mp4` | the finished lesson, 1080p30 |
| `video/out/task-decomposition.srt` | captions (upload as a separate YouTube track) |
| `video/out/task-decomposition.description.md` | objective, YouTube chapters, credits |
| `video/out/task-decomposition.qa.json` | automated QA results (LUFS, peak, flashes, WPM, chapters) |
| `video/out/qa_sheet.jpg` | one frame every 12 s, for the eye check |

## Structure (Tell · Show · Do · Apply + edu-film-edit)

| Part | Phase | Takeaway |
| --- | --- | --- |
| Hook & promise | | the problem, a 5-step result preview, the promise |
| 1. Spot the hidden jobs | Tell | Many jobs, many steps |
| 2. Turn one prompt into five | Show | Visible, checked steps |
| 3. Decompose it yourself | Do | One job per step |
| 4. Know when to use it | Apply | Decompose multi-stage work |
| Recap & assignment | Apply | stacked recap, animated assignment checklist (one call to action) |

**Visual language:** colour emoji on every slide and inside every diagram; UML for the core ideas:
a class + object diagram (decomposition), an activity diagram with guard conditions (the 5-step
pipeline) and a sequence diagram (prompt chaining between you and Claude). Captions are small,
burned in, and fill word by word as they are spoken.

## Reusable skill: skool-course-video-creator

`.claude/skills/skool-course-video-creator/` turns a topic brief into a lesson video and site the
way this one was made. Start a new lesson from this repo:

```bash
bash .claude/skills/skool-course-video-creator/scripts/new_lesson.sh <slug> "<Title>" ../<slug>-video
```

Then ask Claude Code to use the `skool-course-video-creator` skill with your topic brief.

## Build

```bash
./build.sh
```

Steps it runs:

1. **Voice:** `tools/kokoro_server.py` serves Kokoro-82M (kokoro-onnx int8, CPU) on `:8881` with the
   same API simpligen expects from Kokoro-FastAPI. Voice `af_heart`. Sentences are joined with a
   0.45 s pause (`KOKORO_PAUSE`), which keeps the pace inside 140–170 words per minute.
2. **Diagrams:** `tools/make_svgs.py` writes every SVG in `video/svg/` from data, UML included.
   Emoji in an SVG are written as `<text data-emoji="SIZE" x y>E</text>`; simpligen cuts them out
   before rsvg and draws them in colour with Pillow.
3. **Background art:** if `video/images/prompts.json` exists, the FLUX.2 Klein images made on a Mac
   (`tools/gen_images.py`) are kept. Otherwise `tools/gen_images_local.py` draws procedural "idea
   network" images on CPU (motif per scene in `video/images/plan.json`).
4. **Render:** `python -m simpligen video/task-decomposition.json …` (hard cuts: `"fade": 0`).
5. **Finish:** `tools/edu_finish.py` applies the edu-film-edit voice chain (highpass 75 Hz, 2.4:1
   compression, de-ess, pink-noise room tone, two-pass loudnorm to −14 LUFS), burns in small
   animated captions (ASS karaoke, timed per sentence from the measured pauses), writes the SRT,
   chapters and description, and runs QA.

## Changes to simpligen (v0.4.1, Linux)

- Noto Color Emoji fallback when the Apple emoji font is missing
- Slide text wrapped by measured pixel width, so titles never run into diagrams
- Intro icons settable per scene (`icons`), intro frames piped to ffmpeg (no PNG per frame on disk)
- `chapter` scene field, project-level `fade` (0 = hard cuts), per-scene `.timeline.json` output
- project-level `footer` (`""` = no footer text on slides)
- colour emoji inside SVG diagrams
- `animate: "assignment"` scene: checklist items revealed one per spoken sentence, with
  self-drawing ticks and a progress bar
- per-sentence speech timing (ffmpeg `silencedetect`) stored in the timeline

## Build on an Apple Silicon Mac (FLUX images + render)

Needs Homebrew `uv`, `ollama`, `ffmpeg-full`, `python@3.12`, `librsvg`, and mflux
(`uv tool install mflux`). FLUX.2 Klein 4B (~15 GB) and `gemma3:12b` (~8 GB) download on first use.

```bash
git pull
python3 tools/gen_images.py video/task-decomposition.json video/images   # 8 images, ~35 s each
./build.sh                                                               # voice, render, captions, QA
tools/build_site.sh --publish                                            # site/ → main → GitHub Pages
```

Mac gotchas, all hit on the first Mac build (2026-11-24):

| Symptom | Fix (already in the repo) |
|---|---|
| `pip` can't resolve `kokoro-onnx` | Homebrew's `python3` is 3.15, too new for kokoro-onnx. `build.sh` builds `.venv` with `python3.12` when present |
| `No option name near '…ass'` at the caption burn | Homebrew's `ffmpeg` has no libass. `brew install ffmpeg-full` (keg-only, sits alongside the plain `ffmpeg`); `edu_finish.py` uses it automatically, or set `FFMPEG=/path/to/ffmpeg` |
| New images land as `01_1.png` and the video still shows the old art | mflux won't overwrite. `gen_images.py` now deletes the old file first |
| QA `wpm` 170.6, fails | the Docker Kokoro on `:8880` was used. `build.sh` now runs the repo server on `:8881` |

Measured on this Mac: FLUX 33.8–38.8 s per image (8 images, 5 min 12 s with prompts); `./build.sh`
2 min 24 s; QA 7/7 (−14.0 LUFS, 164.7 wpm, 307.6 s).

`build.sh` always uses this repo's Kokoro server, on `:8881` (`KOKORO_PORT`). A Kokoro-FastAPI
Docker container on `:8880` has no 0.45 s sentence pause; using it gave 170.6 wpm and failed QA.

## FLUX images only, from the Mac (one-liner)

On an Apple Silicon Mac with uv and Ollama:

```bash
curl -fsSL https://raw.githubusercontent.com/rifaterdemsahin/task-decomposition-video/main/tools/mac_flux.sh | bash
```

It clones or pulls the repo, installs mflux, pulls `gemma3:12b`, generates FLUX.2 Klein images for
the scenes in `video/images/plan.json`, and pushes them. `build.sh` then keeps them.

## Publish to GitHub Pages

```bash
tools/build_site.sh --publish
```

Builds `site/` from `pages/` (landing page, Mac FLUX page), `kanban.html` and `effort.html`, with
one shared menu from `pages/menu.html` inserted into every page. Copies the video, captions
(SRT + VTT), QA report and poster into `site/`, commits
it and pushes `main`. The workflow in `.github/workflows/static.yml` deploys `site/` to GitHub
Pages, then runs `tests/test_site.py` against the live URL.

Test locally: `.venv/bin/python -m unittest tests.test_site` (set
`SITE_URL=https://rifaterdemsahin.github.io/task-decomposition-video/` to add the live checks).

## Edit the lesson

Change narration or slides in `video/task-decomposition.json`, diagram wording in
`tools/make_svgs.py`, then run `./build.sh` again.
