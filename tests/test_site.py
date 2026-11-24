"""Tests for the GitHub Pages site.

Offline (always):   site/ has every file index.html points at, pages are full HTML documents,
                    captions and chapters are well formed, the video is a real H.264/AAC MP4.
Live (SITE_URL set): every page and asset answers 200 with the right content type, and the
                    deployed video is byte-for-byte the same size as the local one.

run:  .venv/bin/python -m unittest tests.test_site
live: SITE_URL=https://rifaterdemsahin.github.io/task-decomposition-video/ .venv/bin/python -m unittest tests.test_site
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
PAGES = ["index.html", "kanban.html", "effort.html", "mac-flux.html", "skill.html"]


class Refs(HTMLParser):
    """Collect local src/href references (skips external links and anchors)."""

    def __init__(self):
        super().__init__()
        self.refs: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("src", "href", "poster") and v and not re.match(r"^(https?:|mailto:|#|data:)", v):
                self.refs.add(v)


def local_refs(page: str) -> set[str]:
    p = Refs()
    p.feed((SITE / page).read_text())
    return p.refs


class TestSiteFiles(unittest.TestCase):
    def test_pages_are_full_documents(self):
        for page in PAGES:
            html = (SITE / page).read_text()
            self.assertTrue(html.lstrip().lower().startswith("<!doctype html>"), page)
            self.assertIn("<title>", html, page)
            self.assertIn('name="viewport"', html, page)

    def test_every_local_reference_exists(self):
        for page in PAGES:
            for ref in local_refs(page):
                self.assertTrue((SITE / ref).is_file(), f"{page} -> {ref} missing")

    def test_every_page_has_the_shared_menu(self):
        menus = []
        for page in PAGES:
            html = (SITE / page).read_text()
            self.assertNotIn("<!--MENU-->", html, page)
            start, end = html.index('<nav class="tdm"'), html.index("</nav>")
            menu = html[start:end]
            self.assertIn(f'href="{page}" aria-current="page"', menu, page)
            menus.append(menu.replace(' aria-current="page"', ""))
            for target in PAGES:  # every page links to every other page
                self.assertIn(f'href="{target}"', menu, f"{page} menu lacks {target}")
        self.assertEqual(len(set(menus)), 1, "menus differ between pages")

    def test_mac_page_has_the_one_liner(self):
        html = (SITE / "mac-flux.html").read_text()
        self.assertIn("raw.githubusercontent.com/rifaterdemsahin/task-decomposition-video/main/tools/mac_flux.sh | bash", html)
        self.assertTrue((SITE.parent / "tools" / "mac_flux.sh").is_file())

    def test_index_links_video_captions_and_pages(self):
        refs = local_refs("index.html")
        for need in ["task-decomposition.mp4", "task-decomposition.vtt", "poster.jpg",
                     "kanban.html", "effort.html", "task-decomposition.srt"]:
            self.assertIn(need, refs)

    def test_video_is_h264_aac_and_long_enough(self):
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "stream=codec_name:format=duration", "-of", "json",
                              str(SITE / "task-decomposition.mp4")],
                             capture_output=True, text=True, check=True).stdout
        info = json.loads(out)
        codecs = {s["codec_name"] for s in info["streams"]}
        self.assertEqual(codecs, {"h264", "aac"})
        self.assertGreater(float(info["format"]["duration"]), 180)

    def test_captions_are_valid(self):
        vtt = (SITE / "task-decomposition.vtt").read_text()
        self.assertTrue(vtt.startswith("WEBVTT"))
        stamp = r"((?:\d\d:)?\d\d:\d\d\.\d{3})"  # WebVTT hours are optional
        cues = re.findall(stamp + " --> " + stamp, vtt)
        self.assertGreater(len(cues), 50)

        def secs(t: str) -> float:
            return sum(float(p) * 60 ** i for i, p in enumerate(reversed(t.split(":"))))

        for start, end in cues:
            self.assertLessEqual(secs(start), secs(end))

    def test_chapters_parse_like_the_page_does(self):
        text = (SITE / "task-decomposition.description.md").read_text()
        chapters = re.findall(r"^(\d+):(\d\d) (.+)$", text, re.M)
        self.assertGreaterEqual(len(chapters), 3)
        self.assertEqual(chapters[0][:2], ("0", "00"))  # YouTube needs 0:00 first


@unittest.skipUnless(SITE_URL, "set SITE_URL to test the deployed site")
class TestLiveSite(unittest.TestCase):
    def head(self, path: str) -> tuple[int, str, int]:
        req = urllib.request.Request(f"{SITE_URL}/{path}", method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), int(r.headers.get("Content-Length", -1))

    def test_pages_and_assets_answer(self):
        expect = {"": "text/html", "kanban.html": "text/html", "effort.html": "text/html",
                  "mac-flux.html": "text/html", "skill.html": "text/html",
                  "task-decomposition.mp4": "video/mp4", "task-decomposition.vtt": "text/vtt",
                  "poster.jpg": "image/jpeg", "task-decomposition.description.md": "text/markdown",
                  "task-decomposition.srt": "", "task-decomposition.qa.json": "application/json"}
        for path, ctype in expect.items():
            status, got, _ = self.head(path)
            self.assertEqual(status, 200, path)
            self.assertIn(ctype, got, path)

    def test_deployed_video_matches_local(self):
        _, _, size = self.head("task-decomposition.mp4")
        self.assertEqual(size, (SITE / "task-decomposition.mp4").stat().st_size)

    def test_index_has_player(self):
        with urllib.request.urlopen(f"{SITE_URL}/", timeout=30) as r:
            html = r.read().decode()
        self.assertIn('<video id="v"', html)
        self.assertIn("task-decomposition.vtt", html)


if __name__ == "__main__":
    unittest.main()
