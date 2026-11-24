"""Generate scene background images locally on CPU (no GPU, no model download).

simpligen's tools/gen_images.py uses FLUX.2 Klein via mflux, which needs Apple Silicon.
This Linux VM has no GPU and ~1 GB free disk, so this tool draws procedural
"idea network" art with Pillow instead: a glowing node graph whose shape matches the
lesson (tangle = the problem, tree = decomposition, chain = prompt chaining).
Swap in FLUX later by running tools/gen_images.py on the Mac with the same JSON.

usage: python3 tools/gen_images_local.py video/task-decomposition.json video/images
Reads  video/images/plan.json   {"<scene number>": "<motif>"}  motifs: tangle|tree|chain|grid|burst
Writes video/images/NN.png and sets each planned scene's "image" field.
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1920, 1080


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def base(bg, accent, rnd) -> Image.Image:
    """Diagonal gradient from bg to a dark accent tint + soft bokeh."""
    dark = mix(rgb(bg), (0, 0, 0), 0.35)
    tint = mix(rgb(bg), rgb(accent), 0.28)
    v = Image.linear_gradient("L").resize((W, H))  # top -> bottom
    h = Image.linear_gradient("L").rotate(90).resize((W, H))  # right -> left
    grad = ImageChops.add(v.point(lambda p: p // 2), h.point(lambda p: 127 - p // 2))  # diagonal
    img = Image.composite(Image.new("RGB", (W, H), tint), Image.new("RGB", (W, H), dark), grad)
    bokeh = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(bokeh)
    for _ in range(26):
        r = rnd.randint(30, 150)
        x, y = rnd.randint(W // 3, W), rnd.randint(0, H)
        d.ellipse([x - r, y - r, x + r, y + r], fill=mix((0, 0, 0), rgb(accent), rnd.uniform(0.08, 0.25)))
    return ImageChops.add(img, bokeh.filter(ImageFilter.GaussianBlur(28)))


def layout(motif: str, rnd) -> tuple[list, list]:
    """Node positions (x, y, r) and edges (i, j) for each motif, kept to the right ~60%."""
    nodes, edges = [], []
    if motif == "tangle":
        for _ in range(26):
            nodes.append((rnd.randint(860, 1820), rnd.randint(140, 940), rnd.randint(6, 16)))
        for i in range(len(nodes)):
            for j in rnd.sample(range(len(nodes)), 3):
                if i != j:
                    edges.append((i, j))
    elif motif == "tree":
        nodes.append((900, 540, 30))
        level = [0]
        for depth, n in enumerate([3, 7]):
            new = []
            for k in range(n):
                y = 140 + (k + 0.5) * (800 / n) + rnd.randint(-20, 20)
                nodes.append((1260 + depth * 420, int(y), 20 - depth * 6))
                new.append(len(nodes) - 1)
                edges.append((level[min(len(level) - 1, k * len(level) // n)], new[-1]))
            level = new
    elif motif == "chain":
        for k in range(7):
            x = 860 + k * 160
            nodes.append((x, int(540 + 230 * math.sin(k * 0.95)), 22))
            if k:
                edges.append((k - 1, k))
    elif motif == "grid":
        for r in range(4):
            for c in range(5):
                nodes.append((900 + c * 220, 220 + r * 210, 16 if (r + c) % 2 else 10))
                i = len(nodes) - 1
                if c:
                    edges.append((i - 1, i))
                if r and rnd.random() < 0.6:
                    edges.append((i - 5, i))
    else:  # burst: one bright centre, rays outward
        nodes.append((1340, 540, 36))
        for k in range(14):
            a = k / 14 * 2 * math.pi
            dist = rnd.randint(260, 440)
            nodes.append((int(1340 + dist * math.cos(a)), int(540 + dist * 0.85 * math.sin(a)), rnd.randint(8, 18)))
            edges.append((0, len(nodes) - 1))
    return nodes, edges


def network(img, motif, accent, rnd) -> Image.Image:
    nodes, edges = layout(motif, rnd)
    col = rgb(accent)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    sharp = Image.new("RGB", (W, H), (0, 0, 0))
    for layer, width, k in ((glow, 14, 0.55), (sharp, 4, 0.9)):
        d = ImageDraw.Draw(layer)
        for i, j in edges:
            (x1, y1, _), (x2, y2, _) = nodes[i], nodes[j]
            d.line([x1, y1, x2, y2], fill=mix((0, 0, 0), col, k * 0.6), width=width)
        for x, y, r in nodes:
            rr = r * (2.2 if layer is glow else 1)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=mix((0, 0, 0), col, k))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(18)))
    img = ImageChops.add(img, sharp.filter(ImageFilter.GaussianBlur(1)))
    # white-hot node centres
    d = ImageDraw.Draw(img)
    for x, y, r in nodes:
        c = max(2, r // 3)
        d.ellipse([x - c, y - c, x + c, y + c], fill=mix(col, (255, 255, 255), 0.7))
    return img


def grain(img, rnd) -> Image.Image:
    noise = Image.effect_noise((W // 2, H // 2), 18).resize((W, H)).convert("RGB")
    return Image.blend(img, ImageChops.overlay(img, noise), 0.12)


def main(scene_file: str, out_dir: str) -> None:
    sf, od = Path(scene_file), Path(out_dir)
    plan = json.loads((od / "plan.json").read_text())
    data = json.loads(sf.read_text())
    log = []
    for num, motif in plan.items():
        sc = data["scenes"][int(num) - 1]
        t0 = time.perf_counter()
        rnd = random.Random(100 + int(num))
        img = base(sc.get("bg", "#111827"), sc.get("accent", "#22D3EE"), rnd)
        img = grain(network(img, motif, sc.get("accent", "#22D3EE"), rnd), rnd)
        out = od / f"{int(num):02}.png"
        img.save(out, optimize=True)
        sc["image"] = str(out.resolve().relative_to(sf.resolve().parent))
        secs = round(time.perf_counter() - t0, 2)
        log.append({"scene": int(num), "title": sc["title"], "motif": motif, "seed": 100 + int(num),
                    "engine": "Pillow procedural (CPU)", "seconds": secs, "file": out.name})
        print(f"{int(num):02} {secs:>5}s  {motif:<7} {sc['title']}", flush=True)
    sf.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    (od / "images.log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
