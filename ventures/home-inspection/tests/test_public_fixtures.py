"""Safety and reproducibility checks for synthetic fixtures distributed as source code."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from scripts.generate_public_fixtures import generate

class FixtureTests(unittest.TestCase):
    def test_generated_images_are_synthetic_and_native_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root, video=False)
            img = root/'examples'/'demo_exterior.png'
            self.assertTrue(img.is_file())
            with Image.open(img) as picture:
                self.assertEqual(picture.size, (1800, 960))
            self.assertEqual(img.read_bytes(), (root/'examples'/'v05_photo_from_video'/'demo_exterior.png').read_bytes())

    def test_generation_is_repeatable_without_video(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root, video=False)
            before = (root/'examples'/'demo_evidence.png').read_bytes()
            generate(root, video=False)
            self.assertEqual(before, (root/'examples'/'demo_evidence.png').read_bytes())
            self.assertFalse((root/'examples'/'v05_photo_from_video'/'synthetic_moving_house_view.mp4').exists())

if __name__=='__main__':unittest.main()
