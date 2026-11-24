import json
import tempfile
import unittest
from pathlib import Path

from simpligen.render import (MIN_SCENE, PAD, Scene, load_project,
                              media_duration, render, scene_length)


class SceneFileTests(unittest.TestCase):
    def _write(self, data):
        f = Path(tempfile.mkdtemp()) / "s.json"
        f.write_text(json.dumps(data))
        return f

    def test_loads_scenes_and_voice(self):
        p = load_project(self._write({"voice": "Samantha", "scenes": [{"title": "Hi"}]}))
        self.assertEqual(p.voice, "Samantha")
        self.assertEqual(p.scenes[0].title, "Hi")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            load_project(self._write({"scenes": []}))

    def test_rejects_missing_title(self):
        with self.assertRaises(ValueError):
            load_project(self._write({"scenes": [{"narration": "x"}]}))


class TimingTests(unittest.TestCase):
    def test_explicit_duration_wins(self):
        self.assertEqual(scene_length(Scene("t", duration=7), 2.0), 7.0)

    def test_no_audio_uses_minimum(self):
        self.assertEqual(scene_length(Scene("t"), None), MIN_SCENE)

    def test_audio_plus_padding(self):
        self.assertAlmostEqual(scene_length(Scene("t"), 5.0), 5.0 + PAD)


class EndToEndTests(unittest.TestCase):
    def test_renders_mp4_of_expected_length(self):
        d = Path(tempfile.mkdtemp())
        f = d / "s.json"
        f.write_text(json.dumps({"scenes": [
            {"title": "One", "duration": 2, "narration": ""},
            {"title": "Two", "duration": 3},
        ]}))
        stats = render(f, d / "out.mp4", workdir=d / "work")
        self.assertTrue((d / "out.mp4").exists())
        self.assertAlmostEqual(media_duration(d / "out.mp4"), 5.0, delta=0.3)
        self.assertEqual(stats["scenes"], 2)



class SvgSceneTests(unittest.TestCase):
    def test_svg_is_drawn_on_right_half(self):
        from PIL import Image
        from simpligen.render import draw_slide
        d = Path(tempfile.mkdtemp())
        (d / "box.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect width="100" height="100" fill="#ff0000"/></svg>')
        out = draw_slide(Scene("T", bg="#000000", svg="box.svg"), 0, 1, d / "s.png", d)
        img = Image.open(out).convert("RGB")
        self.assertEqual(img.getpixel((1920 - 120 - 420, 540)), (255, 0, 0))
        self.assertEqual(img.getpixel((600, 100)), (0, 0, 0))

    def test_missing_svg_raises(self):
        from simpligen.render import draw_slide
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(FileNotFoundError):
            draw_slide(Scene("T", svg="nope.svg"), 0, 1, d / "s.png", d)


class KokoroTests(unittest.TestCase):
    """Fake Kokoro server: proves the OpenAI-style request and the fallback."""

    def setUp(self):
        import http.server
        import subprocess
        import threading
        wav = Path(tempfile.mkdtemp()) / "t.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=d=1.2:r=24000", "-ac", "1", str(wav)], check=True)
        payload, self.requests = wav.read_bytes(), []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"voices":[]}')

            def do_POST(self):
                n = int(self.headers["Content-Length"])
                outer.requests.append(json.loads(self.rfile.read(n)))
                self.send_response(200); self.end_headers(); self.wfile.write(payload)

        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        import sys
        r = sys.modules["simpligen.render"]
        self.r, self.old = r, r.KOKORO_URL
        r.KOKORO_URL = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        self.r.KOKORO_URL = self.old

    def test_auto_prefers_kokoro(self):
        self.assertEqual(self.r.tts_engine("auto"), "kokoro")

    def test_synthesize_posts_voice_and_converts(self):
        out = Path(tempfile.mkdtemp()) / "o.wav"
        self.assertTrue(self.r.synthesize("hello", out, "bm_george", "kokoro"))
        self.assertEqual(self.requests[0]["voice"], "bm_george")
        self.assertEqual(self.requests[0]["input"], "hello")
        self.assertAlmostEqual(media_duration(out), 1.2, delta=0.1)

    def test_falls_back_when_kokoro_down(self):
        self.r.KOKORO_URL = "http://127.0.0.1:9"
        self.assertNotEqual(self.r.tts_engine("auto"), "kokoro")



class ImageAndEmojiTests(unittest.TestCase):
    def test_image_background_shows_through_on_right(self):
        from PIL import Image
        from simpligen.render import draw_slide
        d = Path(tempfile.mkdtemp())
        Image.new("RGB", (640, 360), (255, 255, 0)).save(d / "bg.png")
        out = draw_slide(Scene("T", bg="#000000", image="bg.png"), 0, 1, d / "s.png", d)
        img = Image.open(out).convert("RGB")
        r_left, _, _ = img.getpixel((60, 300))
        r_right, g_right, _ = img.getpixel((1880, 300))
        self.assertLess(r_left, 80)        # scrim darkens the text side
        self.assertGreater(r_right, 120)   # picture visible on the right
        self.assertGreater(g_right, 120)

    def test_missing_image_raises(self):
        from simpligen.render import draw_slide
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(FileNotFoundError):
            draw_slide(Scene("T", image="nope.png"), 0, 1, d / "s.png", d)

    def test_emoji_renders_in_colour(self):
        from simpligen.render import EMOJI_FONT, render_emoji
        if not Path(EMOJI_FONT).exists():
            self.skipTest("no colour emoji font on this OS")
        tile = render_emoji("🎬")
        self.assertIsNotNone(tile)
        colours = {px[:3] for px in tile.getdata() if px[3] > 200}
        self.assertGreater(len(colours), 20)
        self.assertIsNotNone(render_emoji("⚙️"))  # variation selector is handled



class IntroAnimationTests(unittest.TestCase):
    def test_frames_change_over_time_and_title_appears(self):
        from simpligen.animate import IntroAnimator
        d = Path(tempfile.mkdtemp())
        a = IntroAnimator(Scene("simpligen", subtitle="sub", bg="#000000", fg="#FFFFFF"), d)
        early, late = a.frame(0.0, 5.0), a.frame(4.0, 5.0)
        self.assertEqual(early.size, (1920, 1080))
        box = (150, 430, 900, 600)  # title area: empty at t=0, white text by t=4
        bright = lambda im: sum(1 for p in im.crop(box).getdata() if sum(p) > 600)
        self.assertEqual(bright(early), 0)
        self.assertGreater(bright(late), 1000)

    def test_easing_endpoints(self):
        from simpligen.animate import ease_out_back, ease_out_cubic, progress
        self.assertEqual(progress(0.5, 1, 2), 0.0)
        self.assertEqual(progress(3, 1, 2), 1.0)
        self.assertAlmostEqual(ease_out_cubic(1.0), 1.0)
        self.assertAlmostEqual(ease_out_back(1.0), 1.0)
        self.assertAlmostEqual(ease_out_back(0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
