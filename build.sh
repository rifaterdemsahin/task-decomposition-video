#!/usr/bin/env bash
# Build this lesson video end to end, fully local (Linux CPU, or macOS on Apple Silicon).
# 1) Kokoro TTS server  2) diagrams  3) background art  4) render  5) edu-film-edit finish + QA
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  # kokoro-onnx has no wheels for the newest Python (macOS Homebrew ships 3.15); prefer 3.12
  BASE=$(command -v python3.12 || command -v python3)
  "$BASE" -m venv .venv && $PY -m pip install -q kokoro-onnx soundfile pillow
fi
if [ ! -f models/kokoro/kokoro-v1.0.int8.onnx ]; then
  mkdir -p models/kokoro
  base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
  curl -sSL -o models/kokoro/kokoro-v1.0.int8.onnx $base/kokoro-v1.0.int8.onnx
  curl -sSL -o models/kokoro/voices-v1.0.bin $base/voices-v1.0.bin
fi
# Always use this repo's Kokoro server (0.45 s between sentences keeps 140-170 wpm), on its own
# port so a Kokoro-FastAPI Docker container on :8880 (no pauses, ~171 wpm) is never picked up.
export KOKORO_PORT=${KOKORO_PORT:-8881} KOKORO_URL=http://localhost:${KOKORO_PORT:-8881}
if ! curl -s -m 2 "$KOKORO_URL/v1/audio/voices" >/dev/null; then
  $PY tools/kokoro_server.py & KPID=$!; trap 'kill $KPID' EXIT
  until curl -s -m 2 "$KOKORO_URL/v1/audio/voices" >/dev/null; do sleep 1; done
fi
python3 tools/make_svgs.py video/svg >/dev/null
# FLUX images made on the Mac (tools/gen_images.py writes prompts.json) win over CPU art
if [ ! -f video/images/prompts.json ]; then
  $PY tools/gen_images_local.py video/task-decomposition.json video/images
fi
$PY -m simpligen video/task-decomposition.json video/out/task-decomposition-raw.mp4
$PY tools/edu_finish.py video/task-decomposition.json video/out/task-decomposition-raw.mp4 video/out/task-decomposition.mp4
