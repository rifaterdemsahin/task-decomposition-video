---
name: simpligen-video
description: Use when asked to make, update, re-render or publish a narrated explainer or demo video locally on a Mac with simpligen - scene JSON, Kokoro voice, AI background images (Ollama prompts + mflux FLUX.2 Klein), emojis, SVG diagrams, animated intro - or to add a version, page, diagram or HyperFrames comparison to the simpligen site and ship it with git push and fly deploy.
---

# simpligen video: start to end

## Overview

simpligen turns a JSON script into a narrated 1080p MP4 with **only local tools**, then publishes the video and its pages to GitHub and Fly.io.

**Core principle:** every number on a slide, in narration or on a page is **measured in this run**. Estimates are labelled "est.", and claims you couldn't verify are labelled "not measured".

```
demo.json ─► 🦙 Ollama gemma3:12b (prompts) ─► 🎨 mflux FLUX.2 Klein 4B (PNGs)   [step 2, slow, once]
         └─► 🔊 Kokoro :8880 (voice) + Pillow/rsvg/animate.py + ffmpeg ─► demo.mp4 [step 3]
site/*.html + diagrams ─► git commit/tag/push ─► fly deploy (static nginx) ─► curl-verify [steps 5-7]
```

## Pipeline (do the steps in this order)

| # | Step | Command | Done when |
|---|------|---------|-----------|
| 0 | Preflight | `bash .claude/skills/simpligen-video/scripts/preflight.sh` | every line ✅ (or a ⚠️ you accept) |
| 1 | Write or edit the script | edit `examples/demo.json` (schema below) | `python3 -c "import json;json.load(open('examples/demo.json'))"` passes |
| 2 | AI images (only for new or changed scenes) | `python3 tools/gen_images.py examples/demo.json examples/images` | 1 PNG per scene + `prompts.json` |
| 3 | Render | `python3 -m simpligen examples/demo.json site/demo.mp4` | JSON stats printed, `"tts": "kokoro"` |
| 4 | **Look at it** | `ffmpeg -ss <t> -i site/demo.mp4 -frames:v 1 f.png` for 2–3 times, then Read the PNGs | text readable, no overlaps, version visible |
| 5 | Pages | `python3 tools/build_gallery.py` and edit `site/*.html` | same menu on every page, version updated |
| 6 | Test + ship | `bash .claude/skills/simpligen-video/scripts/ship.sh X.Y.Z "summary"` | tests OK, tag pushed |
| 7 | Verify live | (ship.sh does it) | every URL 200, version string on the page |

Bump `VERSION` in `simpligen/render.py` **before step 3**, because the version is burned into every slide footer.

## Scene schema (`examples/demo.json`)

```json
{
  "tts": "kokoro", "voice": "af_heart",
  "scenes": [
    {"title": "simpligen", "subtitle": "VideoStudio · local AI video", "emoji": "🎬",
     "animate": "intro", "image": "images/01.png", "bg": "#0B1020",
     "narration": "Welcome to simpligen..."},
    {"title": "Render locally", "subtitle": "Pillow draws, Kokoro speaks", "emoji": "⚙️",
     "svg": "svg/03-pipeline.svg", "image": "images/03.png", "bg": "#052E16", "accent": "#4ADE80",
     "narration": "Pillow draws each slide..."}
  ]
}
```

| Field | Effect |
|---|---|
| `title` (required), `subtitle` | text block on the left |
| `narration` | Kokoro voice. The scene lasts as long as the narration + 0.6 s (minimum 2.5 s), or set `duration` |
| `emoji` | colour emoji above the title (Apple Color Emoji) |
| `svg` | diagram on the right. Made smaller and moved to the lower right when `image` is set |
| `image` | cover-cropped background behind a left-to-right scrim |
| `animate: "intro"` | animated title sequence (`simpligen/animate.py`, ~50 ms per frame) |
| `bg`, `fg`, `accent` | colours (`bg` also tints the scrim) |
| top-level `tts` | `auto` (Kokoro → say → espeak), `kokoro`, `say`, `none`. `voice`: Kokoro voice id |

Paths are relative to the scene file. SVGs: dark or transparent background, viewBox `0 0 840 760`. Check each one with `rsvg-convert -w 100 f.svg >/dev/null`.

## Site conventions

- Every page in `site/` has the **same emoji menu**: 🏠 Home · 🏗️ Architecture · 🎨 AI images · 🖼️ Local images · 📘 README.md · 💰 Costs · ⚔️ vs HyperFrames · 🐙 GitHub. Use `aria-current="page"` on the current page.
- Every page has an SVG diagram (`site/diagrams/`), emoji headings, the `🎬 simpligen vX.Y.Z` badge, and an audio/image credit (Kokoro-82M `af_heart`; FLUX.2 Klein 4B via mflux; prompts by gemma3:12b).
- `site/gallery.html` is **generated**. Edit `tools/gallery_template.html`, not the output.
- README, `docs/COSTS.md` and `docs/HYPERFRAMES-COMPARISON.md` get a section per version with measured numbers.

## Common mistakes (all hit in practice)

| Symptom | Cause / fix |
|---|---|
| `'function' object has no attribute ...` when importing `simpligen.render` | `simpligen/__init__.py` re-exports `render()`, which shadows the module. Use `sys.modules["simpligen.render"]` or `importlib.import_module("simpligen.render")` |
| Text side of the slide too light, picture side too dark | `Image.linear_gradient("L")` runs top→bottom. Use `.rotate(-90)` (not `90`) for left = opaque |
| A scripted find/replace silently does nothing | An earlier step already changed the string (e.g. a version bump). Assert every `old in text` before replacing, and grep afterwards |
| Narration states a number that doesn't match the video | Re-measure after the final render. Prefer rates ("~50 ms per frame") over totals that change with scene length |
| Rendering takes 2–3× longer than last time | Kokoro cold start or speed varies between runs. Quote a range (95–160 s), not one value |
| `ollama run x/z-image-turbo` → "image generation models are not currently supported" | Ollama 0.40.16 can't do it. Use mflux for images and Ollama only for prompts |
| LM Studio `/v1/chat/completions` → "API token is required" | Don't go looking for tokens. Use Ollama (`:11434`, no auth) or ask the user for the token |
| `npx hyperframes ...` blocked | Installing or executing a new package needs the user's approval. Write the composition (`comparisons/hyperframes-intro/`) and label HyperFrames numbers "not measured" |
| Emoji renders as a box or overlaps text in an SVG rasterised by rsvg | rsvg has no colour emoji. Draw emojis with Pillow (`render_emoji`) on slides. SVG emojis are fine on web pages |
| Disk full during model download | FLUX.2 Klein 4B ≈ 15 GB, Ollama image models 6–13 GB. Run preflight first and never delete the user's models without asking |
| Diagram card hides the AI image | Expected only without `image`. With `image` the SVG goes in a 500×450 box in the lower right |

## Red flags: stop and check

- About to write "fast", "cheap" or "works" without a number from this session
- About to `git push` without running the tests and looking at frames
- About to delete models, read credential files, or run a newly downloaded CLI without asking
- About to edit `site/gallery.html` by hand

## Reference

- Version history and what each version added: [history.md](history.md)
- Starter script for a new video: [templates/scenes.example.json](templates/scenes.example.json)
- Live site: https://simpligen-poc.fly.dev/ · repo: https://github.com/rifaterdemsahin/simpligen
