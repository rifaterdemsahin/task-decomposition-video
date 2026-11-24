#!/usr/bin/env bash
# Test, commit, tag, push, deploy and verify one simpligen version.
# usage: bash .claude/skills/simpligen-video/scripts/ship.sh 0.5.0 "what changed" [--dry-run]
# Expects VERSION in simpligen/render.py to already equal the version given, with the video re-rendered.
set -euo pipefail
VER="${1:?version, e.g. 0.5.0}"; MSG="${2:?one-line summary}"; DRY="${3:-}"
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"
URL="https://simpligen-poc.fly.dev"
run() { if [ "$DRY" = "--dry-run" ]; then echo "DRY: $*"; else eval "$@"; fi; }

CODE_VER=$(grep -m1 '^VERSION' simpligen/render.py | cut -d'"' -f2)
[ "$CODE_VER" = "$VER" ] || { echo "❌ simpligen/render.py VERSION is $CODE_VER, not $VER. Bump it and re-render first."; exit 1; }
git rev-parse -q --verify "refs/tags/v$VER" >/dev/null && { echo "❌ tag v$VER already exists"; exit 1; }

echo "── tests"
python3 -m unittest discover -s tests -t . 2>&1 | tail -1 | grep -q '^OK' || { echo "❌ tests failed"; exit 1; }
echo "✅ tests"

echo "── version strings"
STALE=$(grep -l "simpligen v" site/*.html | xargs grep -L "simpligen v$VER" || true)
[ -z "$STALE" ] || { echo "❌ pages not on v$VER: $STALE"; exit 1; }
echo "✅ all pages say v$VER"

echo "── commit, tag, push"
run git add -A
run "git commit -q -m \"simpligen v$VER: $MSG\" -m \"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\""
run git tag -a "v$VER" -m "simpligen v$VER"
run git push -q origin main --follow-tags

echo "── deploy"
run "fly deploy --remote-only 2>&1 | grep -E 'Visit|rror' || true"

echo "── verify live"
FAILED=0
for p in "" architecture.html gallery.html images.html demo.mp4; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$URL/$p"); echo "$code /$p"; [ "$code" = 200 ] || FAILED=1
done
if [ "$DRY" != "--dry-run" ]; then
  curl -s "$URL/" | grep -q "simpligen v$VER" && echo "✅ live page shows v$VER" || { echo "❌ live page not on v$VER"; FAILED=1; }
fi
exit $FAILED
