"""simpligen VideoStudio — local, zero-API video generation.

A scene file (JSON) becomes an MP4:
  Pillow draws each slide -> local TTS voices the narration -> ffmpeg
  times each slide to its audio, crossfades, and concatenates.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VERSION = "0.4.1"
W, H = 1920, 1080
FPS = 30
FADE = 0.5
MIN_SCENE = 2.5
PAD = 0.6  # seconds of breathing room after narration
KOKORO_URL = os.environ.get("KOKORO_URL", "http://localhost:8880")
KOKORO_DEFAULT_VOICE = "af_heart"
SVG_BOX = (840, 760)  # max size of a scene diagram, right half of the frame

# colour-emoji font + its bitmap strike size: Apple on macOS, Noto on Linux
EMOJI_FONTS = [("/System/Library/Fonts/Apple Color Emoji.ttc", 160),
               ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)]
EMOJI_FONT, EMOJI_STRIKE = next(((f, s) for f, s in EMOJI_FONTS if Path(f).exists()), EMOJI_FONTS[0])
EMOJI_SIZE = 132  # drawn size in px (scaled from the font's bitmap strike)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


@dataclass
class Scene:
    title: str
    narration: str = ""
    subtitle: str = ""
    bg: str = "#111827"
    fg: str = "#F9FAFB"
    accent: str = "#22D3EE"
    duration: float | None = None
    svg: str | None = None  # path to an SVG diagram, relative to the scene file
    image: str | None = None  # background picture (e.g. AI-generated), relative to the scene file
    emoji: str | None = None  # big emoji shown above the title
    animate: str | None = None  # "intro" = animated title sequence (simpligen.animate)
    icons: list | None = None  # intro only: [[emoji, label], ...] row of feature icons
    chapter: str | None = None  # marks a chapter start (YouTube chapter name)


@dataclass
class Project:
    scenes: list[Scene]
    voice: str | None = None
    tts: str = "auto"  # auto | kokoro | say | espeak-ng | espeak | none
    fade: float = FADE  # seconds of fade in/out per slide; 0 = hard cuts
    base_dir: Path = field(default_factory=Path.cwd)


def load_project(path: str | Path) -> Project:
    data = json.loads(Path(path).read_text())
    raw = data["scenes"] if isinstance(data, dict) else data
    if not raw:
        raise ValueError("scene file has no scenes")
    scenes = []
    for i, s in enumerate(raw):
        if "title" not in s:
            raise ValueError(f"scene {i} is missing 'title'")
        scenes.append(Scene(**s))
    cfg = data if isinstance(data, dict) else {}
    return Project(scenes=scenes, voice=cfg.get("voice"), tts=cfg.get("tts", "auto"),
                   fade=float(cfg.get("fade", FADE)), base_dir=Path(path).resolve().parent)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def rasterize_svg(svg_path: Path, box: tuple[int, int] = SVG_BOX) -> Image.Image:
    """SVG -> RGBA image that fits inside `box`, keeping aspect ratio."""
    if not svg_path.exists():
        raise FileNotFoundError(f"scene svg not found: {svg_path}")
    if not shutil.which("rsvg-convert"):
        raise RuntimeError("rsvg-convert is required for svg scenes (brew install librsvg)")
    png = subprocess.run(["rsvg-convert", "-a", "-w", str(box[0]), "-h", str(box[1]),
                          str(svg_path)], capture_output=True, check=True).stdout
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    img.thumbnail(box)
    return img


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def background(scene: Scene, base_dir: Path) -> Image.Image:
    """Solid colour, or a cover-cropped picture under a scrim that keeps text readable."""
    if not scene.image:
        return Image.new("RGB", (W, H), scene.bg)
    path = base_dir / scene.image
    if not path.exists():
        raise FileNotFoundError(f"scene image not found: {path}")
    pic = Image.open(path).convert("RGB")
    scale = max(W / pic.width, H / pic.height)
    pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.LANCZOS)
    left, top = (pic.width - W) // 2, (pic.height - H) // 2
    pic = pic.crop((left, top, left + W, top + H))
    # left side nearly opaque (text), right side lighter (picture shows through)
    alpha = Image.linear_gradient("L").rotate(-90).resize((W, H))  # 255 at left -> 0 at right
    alpha = alpha.point(lambda v: int(95 + v * (230 - 95) / 255))
    scrim = Image.new("RGB", (W, H), _hex_rgb(scene.bg))
    return Image.composite(scrim, pic, alpha)


def render_emoji(emoji: str, size: int = EMOJI_SIZE) -> Image.Image | None:
    """Colour emoji as RGBA, or None when no colour-emoji font is available."""
    if not emoji or not Path(EMOJI_FONT).exists():
        return None
    text = emoji.replace("\ufe0f", "")
    font = ImageFont.truetype(EMOJI_FONT, EMOJI_STRIKE)
    box = font.getbbox(text)
    tile = Image.new("RGBA", (box[2] + 20, box[3] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((10, 10), text, font=font, embedded_color=True)
    bbox = tile.getbbox()
    if not bbox:
        return None
    tile = tile.crop(bbox)
    scale = size / tile.height  # Noto's 109px strike must be scaled up, Apple's 160px down
    return tile.resize((max(1, round(tile.width * scale)), size), Image.LANCZOS)


def wrap_px(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Greedy word wrap that measures each line in pixels with the real font."""
    lines: list[str] = []
    for word in text.split():
        if lines and font.getlength(lines[-1] + " " + word) <= max_w:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def draw_slide(scene: Scene, index: int, total: int, out: Path,
               base_dir: Path | None = None) -> Path:
    base_dir = base_dir or Path.cwd()
    img = background(scene, base_dir)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, 24, H], fill=scene.accent)
    has_svg = bool(scene.svg)
    if has_svg:
        if scene.image:  # smaller diagram, lower right, on a card: the picture stays visible
            art = rasterize_svg(base_dir / scene.svg, (500, 450))
            x, ytop = W - 110 - art.width, H - 150 - art.height
            d.rounded_rectangle([x - 20, ytop - 20, x + art.width + 20, ytop + art.height + 20],
                                radius=30, fill=(*_hex_rgb(scene.bg), 170))
        else:
            art = rasterize_svg(base_dir / scene.svg)
            x = W - 120 - SVG_BOX[0] + (SVG_BOX[0] - art.width) // 2
            ytop = (H - art.height) // 2
        img.paste(art, (x, ytop), art)
    emoji = render_emoji(scene.emoji) if scene.emoji else None
    title_font = _font(92 if has_svg else 110)
    sub_font, small = _font(44 if has_svg else 48), _font(30)
    lh = 112 if has_svg else 130
    # wrap by measured pixel width, so text never runs into the diagram on the right
    max_w = (W - 120 - SVG_BOX[0] - 60 - 140) if has_svg else (W - 280)
    lines = wrap_px(scene.title, title_font, max_w) or [""]
    sub_lines = wrap_px(scene.subtitle, sub_font, max_w)
    emoji_h = emoji.height + 36 if emoji else 0
    y = H // 2 - (emoji_h + len(lines) * lh + len(sub_lines) * 58) // 2
    if emoji:
        img.paste(emoji, (140, y), emoji)
        y += emoji_h
    for line in lines:
        d.text((140, y), line, font=title_font, fill=scene.fg)
        y += lh
    for line in sub_lines:
        d.text((144, y + 24), line, font=sub_font, fill=scene.accent)
        y += 58
    d.text((140, H - 90), f"simpligen v{VERSION}", font=small, fill=scene.accent)
    d.text((W - 220, H - 90), f"{index + 1} / {total}", font=small, fill=scene.fg)
    img.save(out)
    return out


def kokoro_available(url: str | None = None) -> bool:
    try:
        with urllib.request.urlopen(f"{url or KOKORO_URL}/v1/audio/voices", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def tts_engine(preference: str = "auto") -> str | None:
    """Pick a local TTS engine. Kokoro (Docker) first, then OS voices."""
    if preference == "none":
        return None
    order = ["kokoro", "say", "espeak-ng", "espeak"]
    if preference != "auto":
        order = [preference] + [e for e in order if e != preference]
    for name in order:
        if name == "kokoro":
            if kokoro_available():
                return name
        elif shutil.which(name):
            return name
    return None


def kokoro_speech(text: str, voice: str | None, url: str | None = None) -> bytes:
    body = json.dumps({"model": "kokoro", "input": text,
                       "voice": voice or KOKORO_DEFAULT_VOICE,
                       "response_format": "wav"}).encode()
    req = urllib.request.Request(f"{url or KOKORO_URL}/v1/audio/speech", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def synthesize(text: str, out_wav: Path, voice: str | None = None,
               engine: str | None = None) -> bool:
    """Write narration to WAV with a local TTS engine. False if none / no text."""
    if engine is None:
        engine = tts_engine()
    if not text.strip() or engine is None:
        return False
    if engine == "kokoro":
        raw = out_wav.with_suffix(".kokoro.wav")
        raw.write_bytes(kokoro_speech(text, voice))
        _ff(["-i", str(raw), "-ar", "44100", "-ac", "2", str(out_wav)])
    elif engine == "say":
        aiff = out_wav.with_suffix(".aiff")
        cmd = ["say", "-o", str(aiff)] + (["-v", voice] if voice and "_" not in voice else []) + [text]
        subprocess.run(cmd, check=True)
        _ff(["-i", str(aiff), "-ar", "44100", "-ac", "2", str(out_wav)])
    else:
        subprocess.run([engine, "-w", str(out_wav), text], check=True)
    return True


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def scene_length(scene: Scene, audio_seconds: float | None) -> float:
    if scene.duration:
        return float(scene.duration)
    if audio_seconds is None:
        return MIN_SCENE
    return max(MIN_SCENE, audio_seconds + PAD)


def _ff(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def render_clip(png: Path, wav: Path | None, seconds: float, out: Path, fade: float = FADE) -> Path:
    fade_out = max(0.0, seconds - fade)
    vf = (f"fade=t=in:st=0:d={fade},fade=t=out:st={fade_out:.3f}:d={fade},format=yuv420p"
          if fade > 0 else "format=yuv420p")
    audio = (["-i", str(wav)] if wav else
             ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
    _ff(["-loop", "1", "-framerate", str(FPS), "-i", str(png), *audio,
         "-t", f"{seconds:.3f}", "-vf", vf, "-af", "apad",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-r", str(FPS), str(out)])
    return out


def render(scene_file: str | Path, output: str | Path, workdir: Path | None = None) -> dict:
    t0 = time.perf_counter()
    project = load_project(scene_file)
    tmp = Path(workdir or tempfile.mkdtemp(prefix="simpligen-"))
    tmp.mkdir(parents=True, exist_ok=True)
    clips = []
    total = len(project.scenes)
    engine = tts_engine(project.tts)
    animated_seconds = 0.0
    timeline, t_cursor = [], 0.0
    for i, sc in enumerate(project.scenes):
        wav = tmp / f"s{i:03}.wav"
        has_audio = synthesize(sc.narration, wav, project.voice, engine)
        audio_secs = media_duration(wav) if has_audio else None
        secs = scene_length(sc, audio_secs)
        if sc.animate == "intro":
            secs = max(secs, 4.0)  # same floor render_intro_clip applies
        timeline.append({"scene": i + 1, "start": round(t_cursor, 3), "end": round(t_cursor + secs, 3),
                         "audio_seconds": round(audio_secs or 0.0, 3), "title": sc.title,
                         "chapter": sc.chapter, "narration": sc.narration})
        t_cursor += secs
        if sc.animate == "intro":
            from .animate import render_intro_clip
            t_anim = time.perf_counter()
            clips.append(render_intro_clip(sc, project.base_dir, wav if has_audio else None,
                                           secs, tmp / f"c{i:03}.mp4", tmp))
            animated_seconds += time.perf_counter() - t_anim
            continue
        png = draw_slide(sc, i, total, tmp / f"s{i:03}.png", project.base_dir)
        clips.append(render_clip(png, wav if has_audio else None, secs, tmp / f"c{i:03}.mp4",
                                 project.fade))
    listing = tmp / "list.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    _ff(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
         "-movflags", "+faststart", str(out)])
    stats = {
        "simpligen_version": VERSION,
        "output": str(out),
        "scenes": total,
        "video_seconds": round(media_duration(out), 2),
        "render_seconds": round(time.perf_counter() - t0, 2),
        "bytes": out.stat().st_size,
        "intro_render_seconds": round(animated_seconds, 2),
        "tts": engine or "none",
        "voice": project.voice or (KOKORO_DEFAULT_VOICE if engine == "kokoro" else "default"),
    }
    # per-scene timing, used by tools/edu_finish.py for SRT captions and YouTube chapters
    Path(f"{out}.timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False) + "\n")
    return stats


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print("usage: simpligen <scenes.json> <out.mp4>")
        return 2
    print(json.dumps(render(argv[0], argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
