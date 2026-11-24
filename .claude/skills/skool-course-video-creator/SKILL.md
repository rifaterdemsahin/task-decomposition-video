---
name: skool-course-video-creator
description: Use when asked to make a narrated lesson or course video for a Skool community (e.g. a Claude Associate course topic), from a topic brief to a published GitHub Pages lesson page - local Kokoro voice, Tell-Show-Do-Apply structure, UML diagrams with emoji, burned-in animated captions, an animated assignment at the end, research notes, a production board and an effort report.
---

# Skool course video creator

## Overview

Turns a topic brief into a ~5 minute narrated lesson video plus its lesson site, with **only
local tools** (Kokoro TTS on CPU, Pillow, rsvg, ffmpeg). This repo is the template: scaffold a
new lesson from it, write the script and diagrams, build, check, publish.

**Core principle:** the video teaches ONE objective ("After this, the viewer can ___"), every
on-screen element points at what is being said, and every number you report was measured in
this run (QA report, timestamps), never estimated.

It combines two skills in this repo: **edu-film-edit** (lesson structure, audio, captions, QA) and
**simpligen-video** (the renderer). Read edu-film-edit when a structural question comes up.

## Pipeline

| # | Step | Command / file | Done when |
|---|------|----------------|-----------|
| 1 | Scaffold | `bash .claude/skills/skool-course-video-creator/scripts/new_lesson.sh <slug> "<Title>" <dir>` | new repo with `video/<slug>.json` |
| 2 | Objective + outline | `objective` field; 3–5 chapters = Tell / Show / Do / Apply | one sentence, outcome-named chapters |
| 3 | Script | `video/<slug>.json` (scene shapes below) | `python3 -c "import json;json.load(open('video/<slug>.json'))"` |
| 4 | Diagrams | edit `tools/make_svgs.py` (UML + emoji), run it | every SVG passes `rsvg-convert -w 100` |
| 5 | Backgrounds | `video/images/plan.json` → Mac FLUX one-liner, else CPU art | one PNG per planned scene |
| 6 | Build | `./build.sh` (Kokoro server → SVG → images → render → finish + QA) | `video/out/<slug>.qa.json` has `"pass": true` |
| 7 | **Look at it** | `ffmpeg -ss <t> -i video/out/<slug>.mp4 -frames:v 1 f.png` at 4–6 times, read them | no overlaps, captions small, emoji in colour |
| 8 | Publish | `tools/build_site.sh --publish`, then `SITE_URL=… python -m unittest tests.test_site` | Pages workflow green, live tests OK |
| 9 | Companions | research doc (sources fetched), `kanban.html`, `effort.html` | linked from the shared menu and README |

## Scene shapes (`video/<slug>.json`)

Top level: `"objective"`, `"tts": "kokoro"`, `"voice": "af_heart"`, `"fade": 0` (hard cuts),
`"footer": ""` (no tool/version text on slides).

| Part | Scene recipe |
|------|--------------|
| Hook (≤ 30 s) | `animate: "intro"`, `icons: [["🗣️","Tell"],["👀","Show"],["✍️","Do"],["🚀","Apply"]]`, `chapter` = first chapter name; narration = the problem in 1–3 short sentences |
| Preview | the finished diagram (`svg`) + the promise: "By the end of this lesson, you'll be able to …" |
| Chapter card | `chapter: "<outcome name>"`, subtitle `Chapter N of M · TELL`, narration "Chapter N. <name>." |
| Explain / Show | one idea per scene: `emoji` + short `title` + `svg` (diagram) **or** `image` (background) |
| Takeaway | title = 1–4 word key term, subtitle `Takeaway`, emoji 💡, narration "Takeaway: …" |
| Do | worksheet SVG + "Pause the video now…" exercise, then a sample-answer scene |
| Recap | 3–4 scenes `svg/NN-recap-1..k.svg`, each showing one more line (stacked reveal) |
| Assignment (last) | `animate: "assignment"`, `items: [[emoji, text], …]` (≤ 46 chars each); narration = 1 intro sentence + **one sentence per item, in order** + a short sign-off. The only call to action (Skool post). |

## Diagrams: UML + emoji

| Idea in the lesson | UML diagram |
|---|---|
| A thing made of parts (task → sub-tasks, system → components) | class + object diagram (composition ◆, multiplicity, instances `s1:Name`) |
| A process with checks | activity diagram (initial ●, rounded actions, `[guard]` on each arrow, final ◉) |
| Who talks to whom, in what order | sequence diagram (lifelines, sync → / reply ⇠, `alt [condition]` fragment) |
| Alternatives / when-to-use | two-column checklist with ✅ / ❌ |

Emoji inside an SVG: `<text data-emoji="SIZE" x="X" y="Y">🧠</text>` (attribute order fixed).
simpligen cuts these out before rsvg (no colour emoji there) and draws them with Pillow.
viewBox `0 0 840 760`, dark/transparent background, `frame("sd  Name", COLOR)` tab on UML.

## Narration rules

- Write for the ear: "Q three", not "Q3"; add written forms to `CAPTION_FIXES` in `tools/edu_finish.py`.
- Sentences end with `. ! ? :` — Kokoro pauses 0.45 s there and captions/assignment items are timed per sentence.
- Pace target 140–170 words/min (QA `wpm`). Too fast → raise `KOKORO_PAUSE`, never cut content blindly.

## Quick reference

| Need | Run |
|---|---|
| FLUX backgrounds (Apple Silicon Mac) | `curl -fsSL https://raw.githubusercontent.com/<owner>/<slug>-video/main/tools/mac_flux.sh \| bash` |
| Rebuild everything | `./build.sh` (≈ 10–12 min for 25 scenes on 4 CPUs) |
| One slide preview | `python - <<'EOF'` → `R.draw_slide(scene, i, n, Path("x.png"), base_dir, footer="")` |
| Tests | `.venv/bin/python -m unittest tests.test_render tests.test_site` |
| gh login | token from your secret store piped into `gh auth login --with-token` (never printed) |

## Common mistakes (all hit in practice)

| Symptom | Cause / fix |
|---|---|
| Pages URL 404 after a green deploy | workflow uploads `.`; it must upload `./site` |
| Title runs into the diagram | wrap by measured pixel width (`wrap_px`), not character count |
| Disk fills during the intro | frames must be piped to ffmpeg, never one PNG per frame |
| Build does odd things after you edit `build.sh` | bash reads scripts while running; never edit a running script (restore it, edit after) |
| Captions show twice on the site | burned-in captions → the `<track>` must not be `default` |
| Assignment items appear at the wrong moment | narration needs exactly one sentence per item after the intro sentence |
| Emoji renders as a box | emoji only via `emoji`, `icons`, `items` or `data-emoji` in SVG — never in titles, subtitles or captions |
| Artifact page renders in quirks mode on Pages | artifact HTML has no doctype; `build_site.sh` wraps it |
| QA `wpm_in_140_170` false | raise `KOKORO_PAUSE` (0.3 → 0.45) and rebuild |
| FLUX "not available" on Linux VM | mflux needs Apple Silicon; use the Mac one-liner, keep CPU art meanwhile |

## Red flags: stop and check

- About to report a number not in `qa.json`, a timestamp, or a measured file size
- About to push without looking at 4–6 frames of the final video
- About to add a second call to action
- About to put a paragraph of narration on a slide
