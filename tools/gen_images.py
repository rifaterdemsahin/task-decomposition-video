"""Generate one background image per scene, fully local.

1. A local LLM (Ollama, default gemma3:12b) turns each scene's title + narration
   into an image prompt.
2. mflux renders it with FLUX.2 Klein 4B (8-bit) on Apple Silicon.
3. The scene file gets an "image" field; prompts + timings go to prompts.json.

usage: python3 tools/gen_images.py examples/demo.json examples/images
If OUT_DIR/plan.json exists ({"<scene number>": "<motif>"}), only those scenes get an image
(diagram slides keep their full-size diagram).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434/api/generate"
LLM = "gemma3:12b"
STYLE = ("cinematic, wide 16:9 composition, soft volumetric light, rich colour, "
         "clean minimal background, no text, no letters, no logos")


def llm_prompt(title: str, narration: str) -> str:
    ask = (f"Write ONE image-generation prompt (max 35 words) for a background picture "
           f"for a video slide titled '{title}'. Narration: '{narration}'. "
           "Describe a concrete visual scene, objects and lighting. "
           "Never ask for text, words or logos in the image. Reply with the prompt only.")
    body = json.dumps({"model": LLM, "prompt": ask, "stream": False,
                       "options": {"temperature": 0.6}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["response"].strip().strip('"')
    return f"{text.rstrip('.')}. {STYLE}"


def render(prompt: str, out: Path, seed: int) -> float:
    t0 = time.perf_counter()
    subprocess.run(["mflux-generate-flux2", "--model", "flux2-klein-4b", "-q", "8",
                    "--seed", str(seed), "--width", "1344", "--height", "768",
                    "--prompt", prompt, "--output", str(out)],
                   check=True, capture_output=True)
    return round(time.perf_counter() - t0, 1)


def main(scene_file: str, out_dir: str) -> None:
    sf, od = Path(scene_file), Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    data = json.loads(sf.read_text())
    plan = od / "plan.json"
    wanted = {int(k) for k in json.loads(plan.read_text())} if plan.exists() else None
    log = []
    for i, sc in enumerate(data["scenes"]):
        if wanted is not None and i + 1 not in wanted:
            continue
        t0 = time.perf_counter()
        prompt = llm_prompt(sc["title"], sc.get("narration", ""))
        llm_s = round(time.perf_counter() - t0, 1)
        out = od / f"{i + 1:02}.png"
        img_s = render(prompt, out, seed=100 + i)
        sc["image"] = str(out.resolve().relative_to(sf.resolve().parent))
        log.append({"scene": i + 1, "title": sc["title"], "prompt": prompt,
                    "llm": LLM, "llm_seconds": llm_s, "model": "FLUX.2 Klein 4B (mflux, 8-bit)",
                    "image_seconds": img_s, "file": out.name})
        print(f"{i + 1:02} {img_s:>6}s  {sc['title']}", flush=True)
    sf.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    (od / "prompts.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
