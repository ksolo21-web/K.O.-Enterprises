"""Pixel-level M4 evidence-image acceptance: entire edges and intended scale."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas as cv

from inspection_engine.report import evidence_img


class SourcePhotoContainmentTests(unittest.TestCase):
    def test_original_aspect_ratio_edges_remain_visible_and_image_fills_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/"panorama.png"
            im=Image.new("RGB",(240,160),"#368a54")
            draw=ImageDraw.Draw(im)
            draw.rectangle((0,0,19,159),fill="#ec2d29")
            draw.rectangle((220,0,239,159),fill="#293de9")
            im.save(source)
            destination=root/"image.pdf"
            c=cv.Canvas(str(destination),pagesize=(360,400))
            self.assertTrue(evidence_img(c,source,50,150,250,158))
            c.showPage()
            c.save()
            page=pdfium.PdfDocument(str(destination))[0]
            image=page.render(scale=1).to_pil().convert("RGB")
            red=[]
            blue=[]
            for y in range(92,270):
                for x in range(38,315):
                    r,g,b=image.getpixel((x,y))
                    if r>150 and g<100 and b<110:red.append(x)
                    if b>140 and r<110 and g<120:blue.append(x)
            self.assertTrue(red,"left edge of source photo lost")
            self.assertTrue(blue,"right edge of source photo lost")
            # A 240x160 source has the same near-3:2 aspect ratio as a
            # 250x158 frame; it should occupy >220pt, not the old ~120pt.
            self.assertGreater(max(blue)-min(red),220)
            self.assertLess(min(red),70)
            self.assertGreater(max(blue),280)

    def test_cover_helper_remains_separate_from_source_evidence_helper(self):
        from inspection_engine.report import img
        self.assertIsNot(img,evidence_img)


if __name__=="__main__":
    unittest.main()
