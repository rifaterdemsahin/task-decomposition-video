#!/usr/bin/env bash
# Preflight for the simpligen pipeline: tools, local services, models, disk.
# Read-only: it never installs, downloads, deletes or reads credentials.
# usage: bash .claude/skills/simpligen-video/scripts/preflight.sh
set -u
ok()   { printf '✅ %s\n' "$1"; }
warn() { printf '⚠️  %s\n' "$1"; WARN=$((WARN+1)); }
bad()  { printf '❌ %s\n' "$1"; FAIL=$((FAIL+1)); }
FAIL=0; WARN=0

echo "── tools"
for t in python3 ffmpeg ffprobe rsvg-convert git fly; do
  command -v "$t" >/dev/null && ok "$t" || bad "$t missing"
done
python3 -c "import PIL" 2>/dev/null && ok "Pillow" || bad "Pillow missing (python3 -m pip install pillow)"
[ -f "/System/Library/Fonts/Apple Color Emoji.ttc" ] && ok "colour emoji font" || warn "no Apple Color Emoji font: slide emojis are skipped"

echo "── voice"
if curl -s -m 3 localhost:8880/v1/audio/voices >/dev/null 2>&1; then ok "Kokoro on :8880"
else warn "Kokoro not reachable: run 'docker compose up -d kokoro' (falls back to say/espeak)"; fi

echo "── images (only needed for tools/gen_images.py)"
command -v mflux-generate-flux2 >/dev/null && ok "mflux" || warn "mflux missing (uv tool install mflux)"
ls -d ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.2-klein-4B >/dev/null 2>&1 \
  && ok "FLUX.2 Klein 4B cached" || warn "FLUX.2 Klein 4B not cached: first run downloads ~15 GB"
if curl -s -m 3 localhost:11434/api/version >/dev/null 2>&1; then
  ok "Ollama on :11434"
  ollama list 2>/dev/null | grep -q '^gemma3:12b' && ok "gemma3:12b (prompt writer)" || warn "gemma3:12b missing (ollama pull gemma3:12b)"
else warn "Ollama not running: needed only to write new image prompts"; fi

echo "── disk"
FREE_GB=$(df -g ~ | awk 'NR==2{print $4}')
if [ "${FREE_GB:-0}" -ge 30 ]; then ok "${FREE_GB} GB free"; else warn "only ${FREE_GB} GB free (models need 6–15 GB each)"; fi

echo "── repo"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { bad "not inside a git repo"; ROOT=.; }
[ -f "$ROOT/simpligen/render.py" ] && ok "simpligen $(grep -m1 '^VERSION' "$ROOT/simpligen/render.py" | cut -d'"' -f2)" || bad "simpligen/render.py not found"
fly status -a simpligen-poc >/dev/null 2>&1 && ok "Fly app simpligen-poc reachable" || warn "fly status failed (logged in? app name?)"

echo "── result: $FAIL failed, $WARN warnings"
[ "$FAIL" -eq 0 ]
