"""Synthetic video must show changing source pixels, not a looped still."""
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
import unittest
from PIL import Image

from scripts.generate_public_fixtures import generate
from inspection_engine.capture import probe_video


class TemporalVideoFixtureTests(unittest.TestCase):
    def _frame(self, source: Path, second: float) -> Image.Image:
        output = subprocess.run(
            ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
             '-ss', str(second), '-i', str(source), '-frames:v', '1',
             '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'],
            capture_output=True, check=True, timeout=30)
        with Image.open(BytesIO(output.stdout)) as image:
            return image.convert('RGB')

    def test_early_and_late_frames_have_different_source_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root, video=True)
            source = root / 'examples/v05_photo_from_video/synthetic_moving_house_view.mp4'
            info = probe_video(source)
            self.assertGreaterEqual(info['duration_seconds'], 3.5)
            early = self._frame(source, 0.5)
            late = self._frame(source, 2.5)
            self.assertEqual(early.size, late.size)
            # Distinct shapes and colors at the same patch of the house image.
            p = (1460, 245)
            a, b = early.getpixel(p), late.getpixel(p)
            self.assertGreater(abs(a[0]-b[0]) + abs(a[1]-b[1]) + abs(a[2]-b[2]), 110)
            self.assertGreater(a[0], a[2])  # orange at the beginning
            self.assertGreater(b[2], b[0])  # blue at the end

    def test_video_generation_is_repeatable_with_same_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root, video=True)
            source = root / 'examples/v05_photo_from_video/synthetic_moving_house_view.mp4'
            baseline = (self._frame(source, 0.5).getpixel((1460, 245)),
                        self._frame(source, 2.5).getpixel((1460, 245)))
            generate(root, video=True)
            again = (self._frame(source, 0.5).getpixel((1460, 245)),
                     self._frame(source, 2.5).getpixel((1460, 245)))
            self.assertEqual(baseline, again)

    def test_no_video_request_creates_no_video(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root, video=False)
            self.assertFalse((root / 'examples/v05_photo_from_video/synthetic_moving_house_view.mp4').exists())

if __name__ == '__main__':
    unittest.main()
