"""Animated intro for simpligen, drawn frame by frame with Pillow.

Timeline (seconds):
  0.0-end  background picture pans slowly (Ken Burns) under a dark scrim
  0.0-end  film-strip perforations scroll along the top and bottom edges
  0.2-0.9  emoji pops in (ease-out-back)
  0.6-1.8  title letters rise and fade in, staggered
  1.6-2.3  subtitle fades in
  2.0-2.8  accent underline grows
  2.4-3.6  feature icons pop in one by one
  last 0.5 fade to black (handled by ffmpeg)
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import importlib

R = importlib.import_module(__package__ + ".render")  # module, not the re-exported render()


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def progress(t: float, start: float, end: float) -> float:
    return clamp01((t - start) / (end - start))


def ease_out_cubic(p: float) -> float:
    return 1 - (1 - p) ** 3


def ease_out_back(p: float, s: float = 1.70158) -> float:
    p -= 1
    return p * p * ((s + 1) * p + s) + 1


def _cover(pic: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / pic.width, h / pic.height)
    pic = pic.resize((math.ceil(pic.width * scale), math.ceil(pic.height * scale)), Image.LANCZOS)
    left, top = (pic.width - w) // 2, (pic.height - h) // 2
    return pic.crop((left, top, left + w, top + h))


ICONS = ["🎨", "🔊", "🗺️", "🎬"]
ICON_LABELS = ["AI images", "Kokoro voice", "SVG diagrams", "ffmpeg"]


class IntroAnimator:
    def __init__(self, scene: R.Scene, base_dir: Path):
        self.scene = scene
        self.bg_rgb = R._hex_rgb(scene.bg)
        self.fg_rgb = R._hex_rgb(scene.fg)
        self.accent_rgb = R._hex_rgb(scene.accent)
        pan = 1.12  # oversize so the window can travel
        if scene.image:
            src = Image.open(base_dir / scene.image).convert("RGB")
            self.plate = _cover(src, int(R.W * pan), int(R.H * pan))
        else:
            self.plate = Image.new("RGB", (int(R.W * pan), int(R.H * pan)), self.bg_rgb)
        alpha = Image.linear_gradient("L").rotate(-90).resize((R.W, R.H))
        self.scrim_mask = alpha.point(lambda v: int(120 + v * (225 - 120) / 255))
        self.scrim = Image.new("RGB", (R.W, R.H), self.bg_rgb)
        self.emoji = R.render_emoji(scene.emoji or "🎬", 220)
        pairs = scene.icons or list(zip(ICONS, ICON_LABELS))
        self.icons = [R.render_emoji(e, 96) for e, _ in pairs]
        self.icon_labels = [label for _, label in pairs]
        self.title_font = R._font(150)
        self.sub_font = R._font(56)
        self.label_font = R._font(30)
        self.small = R._font(30)

    def frame(self, t: float, duration: float) -> Image.Image:
        # 1. Ken Burns pan, left -> right and slightly down
        p = t / max(duration, 0.001)
        max_x, max_y = self.plate.width - R.W, self.plate.height - R.H
        x, y = int(max_x * p), int(max_y * 0.5 * p)
        img = Image.composite(self.scrim, self.plate.crop((x, y, x + R.W, y + R.H)), self.scrim_mask)
        layer = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)

        # 2. film strip perforations scrolling
        offset = int((t * 160) % 90)
        for band_y in (18, R.H - 58):
            d.rectangle([0, band_y - 10, R.W, band_y + 50], fill=(0, 0, 0, 120))
            for hx in range(-90 + offset, R.W, 90):
                d.rounded_rectangle([hx, band_y, hx + 46, band_y + 40], radius=8,
                                    fill=(*self.fg_rgb, 60))

        left = 150
        # 3. emoji pop
        if self.emoji:
            s = ease_out_back(progress(t, 0.2, 0.9))
            if s > 0.01:
                e = self.emoji.resize((max(1, int(self.emoji.width * s)), max(1, int(self.emoji.height * s))),
                                      Image.LANCZOS)
                cx, cy = left + self.emoji.width // 2, 300
                layer.alpha_composite(e, (cx - e.width // 2, cy - e.height // 2))

        # 4. title letters, staggered rise + fade
        title = self.scene.title
        x_cursor, base_y = left, 430
        for i, ch in enumerate(title):
            q = ease_out_cubic(progress(t, 0.6 + i * 0.06, 1.1 + i * 0.06))
            if q > 0:
                d.text((x_cursor, base_y + int((1 - q) * 60)), ch, font=self.title_font,
                       fill=(*self.fg_rgb, int(255 * q)))
            x_cursor += int(self.title_font.getlength(ch))
        title_w = x_cursor - left

        # 5. subtitle fade
        q = ease_out_cubic(progress(t, 1.6, 2.3))
        if q > 0 and self.scene.subtitle:
            d.text((left + 4, 620 + int((1 - q) * 20)), self.scene.subtitle, font=self.sub_font,
                   fill=(*self.accent_rgb, int(255 * q)))

        # 6. underline grows
        q = ease_out_cubic(progress(t, 2.0, 2.8))
        if q > 0:
            d.rounded_rectangle([left, 605, left + max(8, int(title_w * q)), 615], radius=5,
                                fill=(*self.accent_rgb, 255))

        # 7. feature icons pop in one by one
        for i, (icon, label) in enumerate(zip(self.icons, self.icon_labels)):
            q = ease_out_back(progress(t, 2.4 + i * 0.25, 2.9 + i * 0.25))
            if q <= 0.01 or icon is None:
                continue
            ix = left + i * 300
            ic = icon.resize((max(1, int(icon.width * q)), max(1, int(icon.height * q))), Image.LANCZOS)
            layer.alpha_composite(ic, (ix + (icon.width - ic.width) // 2, 760 + (icon.height - ic.height) // 2))
            d.text((ix, 875), label, font=self.label_font,
                   fill=(*self.fg_rgb, int(255 * clamp01(q))))

        d.text((R.W - 360, R.H - 140), f"simpligen v{R.VERSION}", font=self.small,
               fill=(*self.accent_rgb, 200))
        img = img.convert("RGBA")
        img.alpha_composite(layer)
        return img.convert("RGB")


def render_intro_clip(scene: R.Scene, base_dir: Path, wav: Path | None, seconds: float,
                      out: Path, workdir: Path) -> Path:
    """Render the animated intro as an MP4 clip (with narration if given)."""
    seconds = max(seconds, 4.0)
    # frames are piped to ffmpeg as raw RGB: no PNG per frame on disk (~4 MB each at 1080p)
    anim = IntroAnimator(scene, base_dir)
    n = int(round(seconds * R.FPS))
    fade_out = max(0.0, seconds - R.FADE)
    audio = (["-i", str(wav)] if wav else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}", "-framerate", str(R.FPS),
                             "-i", "-", *audio, "-t", f"{seconds:.3f}",
                             "-vf", f"fade=t=out:st={fade_out:.3f}:d={R.FADE},format=yuv420p",
                             "-af", "apad", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-c:a", "aac", "-b:a", "160k", "-r", str(R.FPS), str(out)],
                            stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(anim.frame(i / R.FPS, seconds).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise subprocess.CalledProcessError(proc.returncode, "ffmpeg (intro)")
    return out
