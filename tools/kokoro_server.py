"""Local Kokoro TTS on CPU, served on :8880 with the same API simpligen expects.

simpligen's render.py talks to Kokoro-FastAPI (Docker) at KOKORO_URL. This box has no
Docker image or GPU for that, so this file serves the same two endpoints with
kokoro-onnx (Kokoro-82M, int8 ONNX, ~120 MB, CPU only):

  GET  /v1/audio/voices   -> {"voices": [...]}
  POST /v1/audio/speech   {"input": "...", "voice": "af_heart", "speed": 1.0} -> audio/wav

usage:  .venv/bin/python tools/kokoro_server.py            (models in models/kokoro/)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import re

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", ROOT / "models" / "kokoro"))
PORT = int(os.environ.get("KOKORO_PORT", "8880"))
PAUSE = float(os.environ.get("KOKORO_PAUSE", "0.3"))  # seconds of silence between sentences

print(f"loading Kokoro from {MODEL_DIR} ...", flush=True)
t0 = time.perf_counter()
KOKORO = Kokoro(str(MODEL_DIR / "kokoro-v1.0.int8.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
VOICES = sorted(KOKORO.get_voices())
print(f"ready in {time.perf_counter() - t0:.1f}s, {len(VOICES)} voices, :{PORT}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") == "/v1/audio/voices":
            self._send(200, json.dumps({"voices": VOICES}).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/v1/audio/speech":
            return self._send(404, b"not found", "text/plain")
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        voice = req.get("voice") or "af_heart"
        if voice not in VOICES:
            return self._send(400, f"unknown voice {voice}".encode(), "text/plain")
        t0 = time.perf_counter()
        lang = req.get("lang", "en-gb" if voice[0] == "b" else "en-us")
        speed = float(req.get("speed", 1.0))
        # edu-film-edit: if the pace runs fast, add pauses at idea boundaries instead of slowing
        # the voice. One sentence at a time, joined with PAUSE seconds of silence.
        parts, rate = [], 24000
        for sent in [s for s in re.split(r"(?<=[.!?:])\s+", req["input"].strip()) if s]:
            audio, rate = KOKORO.create(sent, voice=voice, speed=speed, lang=lang)
            parts += [audio, np.zeros(int(rate * PAUSE), dtype=audio.dtype)]
        samples = np.concatenate(parts[:-1]) if parts else np.zeros(1, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, samples, rate, format="WAV")
        audio_s = len(samples) / rate
        print(f"{voice} {audio_s:5.1f}s audio in {time.perf_counter() - t0:5.1f}s", flush=True)
        self._send(200, buf.getvalue(), "audio/wav")

    def log_message(self, *args):  # quiet default access log
        pass


if __name__ == "__main__":
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
