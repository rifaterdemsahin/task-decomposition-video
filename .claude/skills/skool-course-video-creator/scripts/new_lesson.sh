#!/usr/bin/env bash
# Scaffold a new Skool lesson video project from this repo (the template).
# usage: bash .claude/skills/skool-course-video-creator/scripts/new_lesson.sh <slug> "<Title>" <target-dir>
#   slug        lower-case-hyphens, e.g. prompt-chaining  -> repo <slug>-video, files <slug>.*
# Copies the toolchain (simpligen, tools, tests, skills, pages, workflow), renames the lesson slug
# everywhere, starts video/<slug>.json from templates/lesson.template.json, and runs git init.
# Never copies: .git, .venv, models, rendered video, site/, generated images.
set -euo pipefail
SLUG=${1:?slug}; TITLE=${2:?title}; DEST=${3:?target dir}
[[ "$SLUG" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "slug must be lower-case-hyphens"; exit 1; }
[ -e "$DEST" ] && { echo "$DEST already exists"; exit 1; }
SRC=$(cd "$(dirname "$0")/../../../.." && pwd)
OLD=task-decomposition
mkdir -p "$DEST"
tar -C "$SRC" --exclude=.git --exclude=.venv --exclude=models --exclude=site --exclude=video/out \
    --exclude=video/images --exclude=video/svg --exclude='__pycache__' \
    --exclude="video/$OLD.json" -cf - . | tar -C "$DEST" -xf -
cd "$DEST"
mkdir -p site video/out video/images video/svg
echo '{}' > video/images/plan.json
sed -e "s/__TITLE__/$TITLE/" "$SRC/.claude/skills/skool-course-video-creator/templates/lesson.template.json" \
    > "video/$SLUG.json"
# rename the slug in every text file that names it (scripts, pages, tests, README, workflow)
grep -rlI --exclude-dir=.claude "$OLD" . | while read -r f; do sed -i "s/$OLD/$SLUG/g" "$f"; done
# page titles and the landing page's objective line
for f in pages/*.html; do
  sed -i -e "s|Task Decomposition: Multi-Step Reasoning Strategies|${TITLE//|/\\|}|g" \
         -e "s|Task Decomposition|${TITLE//|/\\|}|g" \
         -e "s|After this lesson you can break a big business request into a chain of checkable steps that Claude reasons through one at a time.|After this lesson you can __OBJECTIVE__.|" "$f"
done
# lesson-specific companions start as stubs (the shared menu links to them)
rm -f skill.md
for page in kanban:Board effort:Effort; do
  f=${page%%:*}; name=${page#*:}
  printf '<title>%s %s</title>\n<style>body{font:16px/1.5 system-ui,sans-serif;background:#F3F5F9;color:#141A26}\n@media (prefers-color-scheme: dark){body{background:#0E121A;color:#E8ECF3}}\nmain{max-width:900px;margin:0 auto;padding:32px 16px}</style>\n<main><h1>%s</h1><p>To fill in for this lesson.</p></main>\n' \
    "$TITLE" "$name" "$name" > "$f.html"
done
printf '# %s\n\nSkool lesson video. Build: `./build.sh`. Publish: `tools/build_site.sh --publish`.\n' \
    "$TITLE" > README.md
git init -q
echo "✅ $DEST ready: edit video/$SLUG.json and tools/make_svgs.py, then ./build.sh"
