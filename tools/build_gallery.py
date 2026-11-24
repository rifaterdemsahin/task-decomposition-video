"""Build site/gallery.html + web-sized JPGs from examples/images/prompts.json."""
from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from simpligen.render import VERSION  # noqa: E402

SRC = ROOT / "examples" / "images"
OUT = ROOT / "site" / "gallery"


def ollama_status() -> str:
    f = SRC / "ollama.json"
    if not f.exists():
        return "ℹ️ not tested"
    d = json.loads(f.read_text())
    cls = "ok" if d.get("ok") else "no"
    return f'<span class="{cls}">{html.escape(d["status"])}</span>'


def main() -> None:
    log = json.loads((SRC / "prompts.json").read_text())
    emojis = {s["title"]: s.get("emoji", "")
              for s in json.loads((ROOT / "examples" / "demo.json").read_text())["scenes"]}
    OUT.mkdir(parents=True, exist_ok=True)
    cards = []
    for e in log:
        jpg = OUT / (Path(e["file"]).stem + ".jpg")
        subprocess.run(["magick", str(SRC / e["file"]), "-resize", "1024x", "-quality", "82", str(jpg)], check=True)
        cards.append(f'''    <figure class="shot">
      <img src="gallery/{jpg.name}" alt="{html.escape(e['prompt'][:140])}" loading="lazy" width="1024" height="585">
      <figcaption>
        <b>{emojis.get(e['title'], '🎬')} Scene {e['scene']} · {html.escape(e['title'])}</b>
        <span class="meta">⏱️ {e['image_seconds']} s image · 🧠 {e['llm_seconds']} s prompt</span>
        <details><summary>📝 Prompt written by {html.escape(e['llm'])}</summary><p>{html.escape(e['prompt'])}</p></details>
      </figcaption>
    </figure>''')
    total = round(sum(e["image_seconds"] for e in log), 1)
    avg = round(total / len(log), 1)
    page = (ROOT / "tools" / "gallery_template.html").read_text()
    page = (page.replace("{{VERSION}}", VERSION).replace("{{CARDS}}", "\n".join(cards))
                .replace("{{COUNT}}", str(len(log))).replace("{{AVG}}", str(avg))
                .replace("{{TOTAL}}", str(total))
                .replace("{{OLLAMA_STATUS}}", ollama_status()))
    (ROOT / "site" / "gallery.html").write_text(page)
    print(f"gallery: {len(log)} images, avg {avg}s")


if __name__ == "__main__":
    main()
