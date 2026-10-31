"""Video trial must reject a static-image loop as a motion-proof substitute."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from scripts.run_local_live_trial import _distinct_video_sample_frames


class TemporalRuntimeGateTests(unittest.TestCase):
    def test_still_loop_cannot_count_as_temporal_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.png'; b=Path(folder)/'b.png'
            Image.new('RGB',(100,100),'orange').save(a)
            Image.new('RGB',(100,100),'orange').save(b)
            self.assertFalse(_distinct_video_sample_frames(a,b))

    def test_large_visual_change_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.png'; b=Path(folder)/'b.png'
            Image.new('RGB',(100,100),'orange').save(a)
            Image.new('RGB',(100,100),'blue').save(b)
            self.assertTrue(_distinct_video_sample_frames(a,b))

    def test_small_compression_noise_cannot_count_as_motion(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.png'; b=Path(folder)/'b.png'
            im=Image.new('RGB',(100,100),(145,155,165))
            im.save(a)
            altered=im.copy()
            d=ImageDraw.Draw(altered)
            d.point((50,50),fill=(146,154,167))
            altered.save(b)
            self.assertFalse(_distinct_video_sample_frames(a,b))

if __name__=='__main__':unittest.main()
