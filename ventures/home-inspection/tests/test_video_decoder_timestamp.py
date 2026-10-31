"""Native timestamp selection is reproducible across FFmpeg versions."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from inspection_engine.capture import decode_video_frame
from inspection_engine.core import DataError

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class SingleFrameTimestampTests(unittest.TestCase):
    def test_exact_selected_source_pts_and_redecoding(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'sequence.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi',
                '-i','testsrc2=size=320x240:rate=4','-t','2.5','-pix_fmt','yuv420p',
                '-y',str(source)],check=True,capture_output=True)
            for requested in (0,0.25,0.5,1.0,1.25,1.5,2.0):
                a=root/'a.png';b=root/'b.png'
                first=decode_video_frame(source,a,requested)
                second=decode_video_frame(source,b,requested)
                self.assertAlmostEqual(first,requested,places=3)
                self.assertEqual(first,second)
                with Image.open(a) as im: self.assertEqual(im.size,(320,240))
                self.assertEqual(a.read_bytes(),b.read_bytes())

    def test_negative_seek_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            with self.assertRaises(DataError):
                decode_video_frame(p/'missing.mp4',p/'bad.png',-1)
