#!/usr/bin/env bash
# Generate the lesson's background images with FLUX.2 Klein on an Apple Silicon Mac,
# then push them back so the Linux build uses them (build.sh keeps them when
# video/images/prompts.json exists).
#
# one-liner:
#   curl -fsSL https://raw.githubusercontent.com/rifaterdemsahin/task-decomposition-video/main/tools/mac_flux.sh | bash
#
# Needs: Apple Silicon (mflux runs on MLX), git with push access, uv, Ollama.
# First run downloads FLUX.2 Klein 4B (~15 GB) and gemma3:12b (~8 GB).
set -euo pipefail
REPO=https://github.com/rifaterdemsahin/task-decomposition-video.git
DIR=${DIR:-$HOME/task-decomposition-video}

[ "$(uname -s)/$(uname -m)" = "Darwin/arm64" ] || { echo "❌ needs an Apple Silicon Mac (mflux runs on MLX)"; exit 1; }
command -v uv >/dev/null     || { echo "❌ uv missing:     brew install uv"; exit 1; }
command -v ollama >/dev/null || { echo "❌ Ollama missing: brew install ollama"; exit 1; }

echo "📥 repo → $DIR"
[ -d "$DIR/.git" ] || git clone "$REPO" "$DIR"
cd "$DIR" && git pull --ff-only

echo "🎨 mflux"
command -v mflux-generate-flux2 >/dev/null || uv tool install mflux

echo "🦙 Ollama + gemma3:12b (writes the image prompts)"
curl -s -m 3 localhost:11434/api/version >/dev/null || { (ollama serve >/dev/null 2>&1 &); sleep 5; }
ollama list | grep -q '^gemma3:12b' || ollama pull gemma3:12b

echo "🖼️  generating the scenes listed in video/images/plan.json"
python3 tools/gen_images.py video/task-decomposition.json video/images

echo "🚀 pushing"
git add video/images video/task-decomposition.json
git commit -m "FLUX.2 Klein backgrounds" && git push
echo "✅ done: tell Claude to pull and rebuild (or build here: see README \"Build on an Apple Silicon Mac\")"
