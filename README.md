# Task Decomposition: Multi-Step Reasoning Strategies

A Claude Associate course lesson for the Skool community, made fully locally with
[simpligen](https://github.com/rifaterdemsahin/simpligen) and edited by the rules of the
**edu-film-edit** skill ([skill.md](skill.md)).

**Learning objective:** after this, the viewer can break a big business request into a chain of
checkable steps that Claude reasons through one at a time.

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
| Recap & practice | Apply | stacked recap, one call to action |

## Build

```bash
./build.sh
```

Steps it runs:

1. **Voice:** `tools/kokoro_server.py` serves Kokoro-82M (kokoro-onnx int8, CPU) on `:8880` with the
   same API simpligen expects from Kokoro-FastAPI. Voice `af_heart`.
2. **Diagrams:** `tools/make_svgs.py` writes every SVG in `video/svg/` from data.
3. **Background art:** `tools/gen_images_local.py` draws procedural "idea network" images on CPU
   (motif per scene in `video/images/plan.json`). This box has no GPU, so FLUX via mflux
   (`tools/gen_images.py`, Apple Silicon) is not used here.
4. **Render:** `python -m simpligen video/task-decomposition.json …` (hard cuts: `"fade": 0`).
5. **Finish:** `tools/edu_finish.py` applies the edu-film-edit voice chain (highpass 75 Hz, 2.4:1
   compression, de-ess, pink-noise room tone, two-pass loudnorm to −14 LUFS), writes the SRT,
   chapters and description, and runs QA.

## Changes to simpligen (v0.4.1, Linux)

- Noto Color Emoji fallback when the Apple emoji font is missing
- Slide text wrapped by measured pixel width, so titles never run into diagrams
- Intro icons settable per scene (`icons`), intro frames piped to ffmpeg (no PNG per frame on disk)
- `chapter` scene field, project-level `fade` (0 = hard cuts), per-scene `.timeline.json` output

## Edit the lesson

Change narration or slides in `video/task-decomposition.json`, diagram wording in
`tools/make_svgs.py`, then run `./build.sh` again.
