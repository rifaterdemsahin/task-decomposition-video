#!/usr/bin/env bash
# Build the Task Decomposition lesson end to end, fully local (Linux, CPU only).
# 1) Kokoro TTS server  2) diagrams  3) background art  4) render  5) edu-film-edit finish + QA
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  python3 -m venv .venv && $PY -m pip install -q kokoro-onnx soundfile pillow
fi
if [ ! -f models/kokoro/kokoro-v1.0.int8.onnx ]; then
  mkdir -p models/kokoro
  base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
  curl -sSL -o models/kokoro/kokoro-v1.0.int8.onnx $base/kokoro-v1.0.int8.onnx
  curl -sSL -o models/kokoro/voices-v1.0.bin $base/voices-v1.0.bin
fi
if ! curl -s -m 2 localhost:8880/v1/audio/voices >/dev/null; then
  $PY tools/kokoro_server.py & KPID=$!; trap 'kill $KPID' EXIT
  until curl -s -m 2 localhost:8880/v1/audio/voices >/dev/null; do sleep 1; done
fi
python3 tools/make_svgs.py video/svg >/dev/null
# FLUX images made on the Mac (tools/gen_images.py writes prompts.json) win over CPU art
if [ ! -f video/images/prompts.json ]; then
  $PY tools/gen_images_local.py video/task-decomposition.json video/images
fi
$PY -m simpligen video/task-decomposition.json video/out/task-decomposition-raw.mp4
$PY tools/edu_finish.py video/task-decomposition.json video/out/task-decomposition-raw.mp4 video/out/task-decomposition.mp4
