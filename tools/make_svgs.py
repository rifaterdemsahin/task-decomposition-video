"""Build the scene diagrams for the Task Decomposition video as SVG files.

Three of them are UML: a class + object diagram (decomposition), an activity diagram
(the five-step pipeline) and a sequence diagram (prompt chaining). Every diagram uses
colour emoji via <text data-emoji="SIZE" x y>E</text>, which simpligen's rasterize_svg
cuts out and draws with Pillow (rsvg has no colour emoji).

Rules from the simpligen skill: viewBox 0 0 840 760, transparent background,
check each with `rsvg-convert`.

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
            f'<defs>'
            f'<marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{DIM}"/></marker>'
            f'<marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10" fill="none" stroke="{DIM}" stroke-width="1.6"/></marker>'
            f'</defs>{body}</svg>')


def card(x, y, w, h, stroke, fill="#0F172A", rx=18, dash=False, sw=3):
    d = ' stroke-dasharray="10 8"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'fill-opacity="0.92" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=30, color=FG, weight="normal", anchor="start", font=FONT, italic=False):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{st}>{escape(s)}</text>')


def emo(x, y, ch, size=40):
    """Colour emoji centred on (x, y), drawn by simpligen with Pillow."""
    return f'<text data-emoji="{size}" x="{x}" y="{y}">{ch}</text>'


def line(x1, y1, x2, y2, color=DIM, w=3, dash=False, head="a"):
    d = ' stroke-dasharray="8 7"' if dash else ""
    m = f' marker-end="url(#{head})"' if head else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{d}{m}/>'


def arrow(x1, y1, x2, y2, color=DIM):
    return line(x1, y1, x2, y2, color, 4)


def badge(cx, cy, n, color, r=30):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            + text(cx, cy + 11, str(n), 32, "#0B1020", "bold", "middle"))


def frame(label, color):
    """UML diagram frame: outline + pentagon name tab in the top-left corner."""
    w = 30 + len(label) * 14
    return (f'<rect x="4" y="4" width="832" height="752" rx="6" fill="none" stroke="{color}" '
            f'stroke-opacity="0.55" stroke-width="2"/>'
            f'<path d="M4,4 H{w} V30 L{w - 14},44 H4 Z" fill="{color}" fill-opacity="0.18" '
            f'stroke="{color}" stroke-opacity="0.55" stroke-width="2"/>'
            + text(16, 32, label, 22, color, "bold", font=MONO))


def uml_class(x, y, w, name, emoji, attrs, ops, color):
    """Class box with name / attributes / operations compartments; returns (svg, height)."""
    h_name, h_attr, h_op = 60, 16 + 34 * len(attrs), 16 + 34 * len(ops)
    h = h_name + h_attr + h_op
    out = [card(x, y, w, h, color, rx=6),
           line(x, y + h_name, x + w, y + h_name, color, 2, head=None),
           line(x, y + h_name + h_attr, x + w, y + h_name + h_attr, color, 2, head=None),
           emo(x + 34, y + 30, emoji, 36),
           text(x + 62, y + 40, name, 30, FG, "bold")]
    for i, a in enumerate(attrs):
        out.append(text(x + 20, y + h_name + 38 + i * 34, a, 24, FG, font=MONO))
    for i, o in enumerate(ops):
        out.append(text(x + 20, y + h_name + h_attr + 38 + i * 34, o, 24, color, font=MONO))
    return "".join(out), h


def steps(items, color, top=20, h=118, gap=28):
    """Numbered vertical pipeline: (emoji, title, output) triples, arrows between cards."""
    out = []
    for i, (em, title, result) in enumerate(items):
        y = top + i * (h + gap)
        out.append(card(10, y, 820, h, color))
        out.append(badge(62, y + h / 2, i + 1, color, 26))
        out.append(emo(130, y + h / 2, em, 52))
        out.append(text(180, y + 52, title, 34, FG, "bold"))
        out.append(text(180, y + 94, "output: " + result, 26, color, font=MONO))
        if i < len(items) - 1:
            out.append(arrow(62, y + h + 2, 62, y + h + gap - 2))
    return "".join(out)


# ── UML class + object diagram: what decomposition produces ────────────────────────────────
def decompose():
    out = [frame("cd  Task decomposition", BLUE)]
    parent, hp = uml_class(150, 62, 540, "Q3StrategyTask", "📊",
                           ["- data: Q3 sales rows", "- goal: 5 strategies"],
                           ["+ decompose(): SubTask[5]"], BLUE)
    out.append(parent)
    py = 62 + hp
    # composition: filled diamond at the whole, line to the part
    out.append(f'<path d="M420,{py} l12,18 l-12,18 l-12,-18 z" fill="{BLUE}"/>')
    out.append(line(420, py + 36, 420, py + 82, BLUE, 3, head=None))
    out.append(text(436, py + 30, "1", 24, BLUE, "bold"))
    out.append(text(436, py + 78, "5  {ordered}", 24, BLUE, "bold"))
    child, hc = uml_class(150, py + 82, 540, "SubTask", "🧩",
                          ["- input: previous output", "- output: checkable result"],
                          ["+ run(input): output", "+ check(): bool"], BLUE)
    out.append(child)
    cy = py + 82 + hc
    # object row: the five instances
    objs = [("📥", "Extract"), ("📈", "Trends"), ("🔍", "Causes"), ("💡", "Options"), ("🏆", "Rank")]
    w, gap, oy = 150, 15, cy + 50
    for i, (em, name) in enumerate(objs):
        x = 17 + i * (w + gap)
        out.append(line(x + w / 2, oy, 420, cy + 4, DIM, 2, dash=True, head="open"))
        out.append(card(x, oy, w, 112, BLUE, rx=6, sw=2))
        out.append(emo(x + w / 2, oy + 38, em, 44))
        lbl = f"s{i + 1}:{name}"
        out.append(text(x + w / 2, oy + 92, lbl, 21, FG, "bold", "middle"))
        lw = len(lbl) * 12.5
        out.append(line(x + w / 2 - lw / 2, oy + 98, x + w / 2 + lw / 2, oy + 98, FG, 1.5, head=None))
    return svg("".join(out))


def before():
    out = [card(10, 20, 820, 300, RED),
           emo(52, 58, "📄", 40), text(84, 70, "PROMPT", 26, RED, "bold"),
           text(40, 130, "Analyze our Q3 market data", 34, FG, font=MONO),
           text(40, 178, "and propose 5 strategies.", 34, FG, font=MONO),
           text(40, 250, "[ 4,000 rows of data pasted ]", 30, DIM, font=MONO),
           emo(770, 70, "😵", 56),
           arrow(420, 325, 420, 395),
           card(10, 400, 820, 340, MUTED, "#111827"),
           emo(52, 444, "🤖", 40), text(84, 455, "ANSWER", 26, DIM, "bold")]
    for i, s in enumerate(["Numbers you can't trace", "Generic, one-size strategies",
                           "No way to see where it broke"]):
        out.append(emo(58, 523 + i * 70, "❌", 36))
        out.append(text(96, 535 + i * 70, s, 36, RED, "bold"))
    return svg("".join(out))


# ── UML activity diagram: the five-step pipeline with guard conditions ─────────────────────
def after():
    out = [frame("act  Q3 strategy pipeline", GREEN)]
    acts = [("📥", "Extract key metrics", "metrics table + rows"),
            ("📈", "Find the top 3 trends", "trend list"),
            ("🔍", "Explain each cause", "cause per trend"),
            ("💡", "Brainstorm 10 options", "option list"),
            ("🏆", "Score, pick the best 5", "5 strategies + reasons")]
    guards = ["[numbers match the data]", "[each trend cites a metric]", "[causes have evidence]",
              "[every option links a cause]", "[scores are justified]"]
    out.append(f'<circle cx="420" cy="70" r="15" fill="{FG}"/>')  # initial node
    out.append(arrow(420, 86, 420, 104))
    top, h, gap = 108, 80, 32
    for i, (em, name, res) in enumerate(acts):
        y = top + i * (h + gap)
        out.append(card(130, y, 580, h, GREEN, rx=40))
        out.append(emo(185, y + h / 2, em, 46))
        out.append(text(225, y + 36, name, 30, FG, "bold"))
        out.append(text(225, y + 66, "→ " + res, 22, GREEN, font=MONO))
        nxt = y + h + gap
        out.append(arrow(420, y + h + 2, 420, nxt - 4 if i < 4 else nxt + 6))
        out.append(text(432, y + h + 22, guards[i], 19, DIM, italic=True))
    ey = top + 5 * (h + gap) + 26
    out.append(f'<circle cx="420" cy="{ey}" r="20" fill="none" stroke="{FG}" stroke-width="3"/>'
               f'<circle cx="420" cy="{ey}" r="11" fill="{FG}"/>')  # final node
    out.append(emo(474, ey, "🏁", 40))
    return svg("".join(out))


def phrasing():
    tiers = [("WEAK", DIM, "😐", ["Think step by step."]),
             ("BETTER", AMBER, "🙂", ["First list the key metrics.", "Then find the top 3 trends.",
                                       "Then propose strategies."]),
             ("BEST", GREEN, "🤩", ["Reason inside <thinking> tags.", "Put the final list inside",
                                     "<answer> tags."])]
    out, y = [], 10
    for label, color, em, lines in tiers:
        h = 80 + 46 * len(lines)
        out.append(card(10, y, 820, h, color))
        out.append(text(40, y + 52, label, 28, color, "bold"))
        out.append(emo(770, y + h / 2, em, 60))
        for j, ln in enumerate(lines):
            out.append(text(40, y + 104 + j * 46, ln, 32, FG, font=MONO))
        y += h + 22
    out.append(emo(110, y + 30, "💡", 30))
    out.append(text(440, y + 40, "tip: ask it to quote the rows it used", 28, DIM, anchor="middle"))
    return svg("".join(out))


# ── UML sequence diagram: prompt chaining between you and Claude ───────────────────────────
def chain():
    you, cl = 210, 640
    out = [frame("sd  Prompt chaining", GREEN)]
    for cx, em, name in ((you, "🧑", "You"), (cl, "🤖", "Claude")):
        out.append(card(cx - 110, 58, 220, 66, GREEN, rx=6))
        out.append(emo(cx - 58, 91, em, 40))
        out.append(text(cx - 28, 102, name, 30, FG, "bold"))
        out.append(line(cx, 124, cx, 740, DIM, 2, dash=True, head=None))

    def call(y, label, n):
        return (f'<rect x="{cl - 9}" y="{y}" width="18" height="58" fill="{GREEN}" fill-opacity="0.85"/>'
                + line(you + 2, y + 4, cl - 12, y + 4, FG, 3)
                + text((you + cl) / 2, y - 8, f"{n}: {label}", 23, FG, "bold", "middle", MONO)
                + line(cl - 12, y + 52, you + 6, y + 52, DIM, 2.5, dash=True, head="open"))

    def reply(y, label):
        return text((you + cl) / 2, y + 44, label, 21, GREEN, anchor="middle", font=MONO)

    def check(y):
        return (f'<path d="M{you},{y} h46 v28 h-40" fill="none" stroke="{AMBER}" stroke-width="3" '
                f'marker-end="url(#a)"/>' + emo(you + 82, y + 14, "✅", 30)
                + text(you + 106, y + 24, "check", 22, AMBER, "bold"))

    rows = [("prompt(data)", "output₁ <answer>"), ("prompt(<output₁>)", "output₂ <answer>"),
            ("prompt(<output₂>)", "final answer")]
    y = 176
    for i, (msg, rep) in enumerate(rows):
        out.append(call(y, msg, i + 1))
        out.append(reply(y, rep))
        if i < 2:
            out.append(check(y + 72))
        y += 160
    out.append(emo(cl + 52, y - 108, "🎯", 36))
    # alt fragment: a failed check reruns only that step
    out.append(card(28, 650, 784, 84, AMBER, "#0F172A", rx=4, sw=2))
    out.append(f'<path d="M28,650 H182 V672 L170,684 H28 Z" fill="{AMBER}" fill-opacity="0.2"/>')
    out.append(text(38, 674, "alt [check fails]", 19, AMBER, "bold", font=MONO))
    out.append(line(you + 2, 710, cl - 12, 710, AMBER, 3))
    out.append(text((you + cl) / 2, 700, "rerun only that step", 22, AMBER, "bold", "middle"))
    return svg("".join(out))


def worksheet():
    cols = [("Step", 10, 110), ("Input", 120, 230), ("Output", 350, 230), ("Check", 580, 250)]
    out = [card(10, 10, 820, 100, AMBER),
           emo(48, 60, "📝", 44),
           text(84, 56, "TASK", 24, AMBER, "bold"),
           text(84, 94, "Plan our product launch", 34, FG, "bold"),
           emo(640, 82, "⏱️", 36),
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
    return svg(steps([("🎯", "Audience and goal", "persona + target number"),
                      ("🔍", "Competitor scan", "comparison table"),
                      ("💬", "Positioning, message", "one-line pitch"),
                      ("📣", "Channels and budget", "budget split"),
                      ("🗓️", "Timeline and risks", "plan + risk list")], AMBER))


def when():
    yes = ["Several stages", "Numbers or maths", "High-stakes decision", "Reasoning must be audited"]
    no = ["Simple lookups", "Quick rewrites", "One-line answers"]
    out = [card(10, 10, 820, 400, PURPLE), emo(52, 58, "🧩", 40),
           text(86, 70, "DECOMPOSE WHEN", 30, PURPLE, "bold")]
    for i, s in enumerate(yes):
        out.append(emo(58, 132 + i * 72, "✅", 38))
        out.append(text(96, 145 + i * 72, s, 38, FG, "bold"))
    out += [card(10, 440, 820, 310, MUTED, "#111827"), emo(52, 488, "⚡", 40),
            text(86, 500, "KEEP IT ONE PROMPT", 30, DIM, "bold")]
    for i, s in enumerate(no):
        out.append(emo(58, 563 + i * 64, "❌", 32))
        out.append(text(96, 575 + i * 64, s, 36, DIM))
    return svg("".join(out))


RECAP = [("🧩", "Big prompts hide many jobs", BLUE), ("👀", "Make the steps visible", GREEN),
         ("☝️", "One job per step", AMBER), ("⚖️", "Decompose multi-stage work", PURPLE)]


def recap(n):
    """Stacked recap list; scene k shows the first k lines (revealed line by line on the voice)."""
    out = []
    for i, (em, ln, color) in enumerate(RECAP):
        y = 30 + i * 180
        on = i < n
        out.append(card(10, y, 820, 150, color if on else MUTED, "#0F172A" if on else "#111827",
                        dash=not on))
        out.append(badge(72, y + 75, i + 1, color if on else MUTED, 32))
        if on:
            out.append(emo(156, y + 75, em, 56))
            out.append(text(206, y + 89, ln, 38, FG, "bold"))
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
