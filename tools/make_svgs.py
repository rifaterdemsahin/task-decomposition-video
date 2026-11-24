"""Build the scene diagrams for the Task Decomposition video as SVG files.

Every diagram is drawn from data here, so wording changes are one-line edits.
Rules from the simpligen skill: viewBox 0 0 840 760, transparent background,
no colour emoji (rsvg can't draw them), check each with `rsvg-convert`.

usage: python3 tools/make_svgs.py video/svg
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

FONT = "DejaVu Sans, Arial, sans-serif"
MONO = "DejaVu Sans Mono, Menlo, monospace"
FG, DIM, MUTED = "#F9FAFB", "#9CA3AF", "#374151"
BLUE, GREEN, AMBER, PURPLE, RED = "#60A5FA", "#4ADE80", "#FBBF24", "#C084FC", "#F87171"


def svg(body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 760" width="840" height="760">'
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{DIM}"/></marker></defs>{body}</svg>')


def card(x, y, w, h, stroke, fill="#0F172A", rx=18, dash=False, sw=3):
    d = ' stroke-dasharray="10 8"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'fill-opacity="0.92" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=30, color=FG, weight="normal", anchor="start", font=FONT):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(s)}</text>')


def arrow(x1, y1, x2, y2, color=DIM):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="4" '
            f'marker-end="url(#a)"/>')


def badge(cx, cy, n, color, r=30):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            + text(cx, cy + 11, str(n), 32, "#0B1020", "bold", "middle"))


def steps(items, color, top=20, h=118, gap=28):
    """Numbered vertical pipeline: (title, output) pairs, arrows between cards."""
    out = []
    for i, (title, result) in enumerate(items):
        y = top + i * (h + gap)
        out.append(card(10, y, 820, h, color))
        out.append(badge(70, y + h / 2, i + 1, color))
        out.append(text(125, y + 52, title, 36, FG, "bold"))
        out.append(text(125, y + 94, "output: " + result, 27, color, font=MONO))
        if i < len(items) - 1:
            out.append(arrow(70, y + h + 2, 70, y + h + gap - 2))
    return "".join(out)


def decompose():
    parts = ["Extract", "Trends", "Causes", "Options", "Rank"]
    out = [card(120, 20, 600, 170, BLUE),
           text(420, 80, "Analyze Q3 market data", 36, FG, "bold", "middle"),
           text(420, 130, "and propose 5 strategies", 36, FG, "bold", "middle"),
           text(420, 172, "one big job", 26, DIM, anchor="middle")]
    w, gap = 152, 15
    for i, p in enumerate(parts):
        x = 10 + i * (w + gap)
        out.append(arrow(420, 194, x + w / 2, 318))
        out.append(card(x, 325, w, 200, BLUE))
        out.append(badge(x + w / 2, 385, i + 1, BLUE, 28))
        out.append(text(x + w / 2, 470, p, 28, FG, "bold", "middle"))
    out += [card(10, 575, 820, 165, MUTED, "#111827"),
            text(420, 635, "every sub-task has", 30, DIM, anchor="middle"),
            text(420, 690, "1 input  →  1 job  →  1 output", 38, BLUE, "bold", "middle", MONO)]
    return svg("".join(out))


def before():
    out = [card(10, 20, 820, 300, RED),
           text(40, 70, "PROMPT", 26, RED, "bold"),
           text(40, 130, "Analyze our Q3 market data", 34, FG, font=MONO),
           text(40, 178, "and propose 5 strategies.", 34, FG, font=MONO),
           text(40, 250, "[ 4,000 rows of data pasted ]", 30, DIM, font=MONO),
           arrow(420, 325, 420, 395),
           card(10, 400, 820, 340, MUTED, "#111827"),
           text(40, 455, "ANSWER", 26, DIM, "bold")]
    for i, s in enumerate(["Numbers you can't trace", "Generic, one-size strategies",
                           "No way to see where it broke"]):
        out.append(text(40, 535 + i * 70, "✗  " + s, 36, RED, "bold"))
    return svg("".join(out))


def after():
    return svg(steps([("Extract key metrics", "metrics table + source rows"),
                      ("Find the top 3 trends", "trend list"),
                      ("Explain each cause", "cause per trend"),
                      ("Brainstorm 10 options", "option list"),
                      ("Score, pick the best 5", "5 strategies + reasons")], GREEN))


def phrasing():
    tiers = [("WEAK", DIM, ["Think step by step."]),
             ("BETTER", AMBER, ["First list the key metrics.", "Then find the top 3 trends.",
                                "Then propose strategies."]),
             ("BEST", GREEN, ["Reason inside <thinking> tags.", "Put the final list inside",
                              "<answer> tags."])]
    out, y = [], 10
    for label, color, lines in tiers:
        h = 80 + 46 * len(lines)
        out.append(card(10, y, 820, h, color))
        out.append(text(40, y + 52, label, 28, color, "bold"))
        for j, line in enumerate(lines):
            out.append(text(40, y + 104 + j * 46, line, 32, FG, font=MONO))
        y += h + 22
    out.append(text(420, y + 40, "tip: ask it to quote the rows it used", 30, DIM, anchor="middle"))
    return svg("".join(out))


def chain():
    out = []
    for i in range(3):
        y = 20 + i * 215
        last = i == 2
        out.append(card(10, y, 300, 130, GREEN))
        out.append(text(160, y + 78, f"Prompt {i + 1}", 36, FG, "bold", "middle"))
        out.append(arrow(315, y + 65, 395, y + 65))
        out.append(card(400, y, 300, 130, GREEN if last else MUTED, "#111827"))
        out.append(text(550, y + 78, "Final answer" if last else f"Output {i + 1}", 34,
                        GREEN if last else FG, "bold", "middle"))
        if not last:
            out.append(f'<circle cx="775" cy="{y + 65}" r="42" fill="none" stroke="{AMBER}" stroke-width="4"/>')
            out.append(text(775, y + 80, "✓", 44, AMBER, "bold", "middle"))
            out.append(text(775, y + 150, "check", 24, AMBER, anchor="middle"))
            out.append(f'<path d="M 775 {y + 160} L 775 {y + 185} L 160 {y + 185} L 160 {y + 210}" '
                       f'fill="none" stroke="{DIM}" stroke-width="4" marker-end="url(#a)"/>')
    out.append(text(420, 735, "a wrong step? fix and rerun only that step", 30, DIM, anchor="middle"))
    return svg("".join(out))


def worksheet():
    cols = [("Step", 10, 110), ("Input", 120, 230), ("Output", 350, 230), ("Check", 580, 250)]
    out = [card(10, 10, 820, 100, AMBER),
           text(40, 56, "TASK", 24, AMBER, "bold"),
           text(40, 94, "Plan our product launch", 34, FG, "bold"),
           text(800, 94, "5 min", 30, AMBER, "bold", "end")]
    for name, x, w in cols:
        out.append(text(x + w / 2, 165, name, 30, AMBER, "bold", "middle"))
    for r in range(5):
        y = 190 + r * 110
        for name, x, w in cols:
            out.append(card(x, y, w - 10, 94, MUTED, "#111827", 12, dash=True, sw=2))
        out.append(text(65, y + 60, str(r + 1), 34, DIM, "bold", "middle"))
    return svg("".join(out))


def sample():
    return svg(steps([("Audience and goal", "persona + target number"),
                      ("Competitor scan", "comparison table"),
                      ("Positioning and message", "one-line pitch"),
                      ("Channels and budget", "budget split"),
                      ("Timeline and risks", "plan + risk list")], AMBER))


def when():
    yes = ["Several stages", "Numbers or maths", "High-stakes decision", "Reasoning must be audited"]
    no = ["Simple lookups", "Quick rewrites", "One-line answers"]
    out = [card(10, 10, 820, 400, PURPLE), text(40, 70, "DECOMPOSE WHEN", 30, PURPLE, "bold")]
    for i, s in enumerate(yes):
        out.append(text(40, 145 + i * 72, "✓  " + s, 38, FG, "bold"))
    out += [card(10, 440, 820, 310, MUTED, "#111827"), text(40, 500, "KEEP IT ONE PROMPT", 30, DIM, "bold")]
    for i, s in enumerate(no):
        out.append(text(40, 575 + i * 64, "–  " + s, 36, DIM))
    return svg("".join(out))


RECAP = [("Big prompts hide many jobs", BLUE), ("Make the steps visible", GREEN),
         ("One job per step", AMBER), ("Decompose multi-stage work", PURPLE)]


def recap(n):
    """Stacked recap list; scene k shows the first k lines (revealed line by line on the voice)."""
    out = []
    for i, (line, color) in enumerate(RECAP):
        y = 30 + i * 180
        on = i < n
        out.append(card(10, y, 820, 150, color if on else MUTED, "#0F172A" if on else "#111827",
                        dash=not on))
        out.append(badge(80, y + 75, i + 1, color if on else MUTED, 34))
        if on:
            out.append(text(140, y + 88, line, 40, FG, "bold"))
    return svg("".join(out))


DIAGRAMS = {"04-decompose": decompose, "05-before": before, "06-after": after,
            "07-phrasing": phrasing, "08-chain": chain, "09-worksheet": worksheet,
            "10-sample": sample, "12-when": when,
            **{f"21-recap-{k}": (lambda k=k: recap(k)) for k in range(1, 5)}}

if __name__ == "__main__":
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "video/svg")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn in DIAGRAMS.items():
        (out_dir / f"{name}.svg").write_text(fn())
        print(out_dir / f"{name}.svg")
