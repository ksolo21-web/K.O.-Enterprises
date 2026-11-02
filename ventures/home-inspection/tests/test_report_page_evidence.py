"""Synthetic PDF visual review checks only; NOT live inspector/OCR validation."""
import copy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader,PdfWriter
from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from inspection_engine.core import DataError
from inspection_engine.report_learning import import_reference
from inspection_engine.study_registry import empty_registry, register_bundle
from inspection_engine.report_page_evidence import (render_batch,validate_page_evidence,
    record_visual_marks,main, MAX_BATCH_PAGES, digest)


class PDFPageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pdf=self.root/'source.pdf'
        c=Canvas(str(self.pdf),pagesize=(360,240))
        c.setFont('Helvetica',12);c.drawString(30,210,'ROOF: Inspect stained chimney flashing.')
        c.line(25,190,335,190)
        c.drawString(30,165,'Service | Observation | Referral')
        c.showPage()
        im=Image.new('RGB',(100,100),'white')
        for x in range(20,80):
            for y in range(30,65):im.putpixel((x,y),(80,80,80))
        c.drawImage(ImageReader(im),35,40,width=200,height=150)
        c.showPage()
        c.setFont('Helvetica',12);c.drawString(30,210,'Rotated floor plan, unverified')
        c.showPage();c.save()
        source=PdfReader(str(self.pdf));writer=PdfWriter()
        for idx,page in enumerate(source.pages):
            if idx==2:page.rotate(90)
            writer.add_page(page)
        with (self.root/'rotated.pdf').open('wb') as fh:writer.write(fh)
        self.pdf=(self.root/'rotated.pdf')
        self.bundle=import_reference(self.pdf,case_id='SYNTHETIC-M3-PAGE',partition='locked_holdout',
            authorized_use=True,consented=True)
        self.registry=register_bundle(self.bundle,empty_registry())
        self.output=self.root/'private_pages'

    def render(self,pages=None):
        return render_batch(self.bundle,self.registry,self.pdf,self.output,[1,2,3] if pages is None else pages)

    def mark(self,p=1):
        return {'id':'manual-1','page':p,'bbox':[0.08,0.12,0.82,0.9],
            'system':'roof','kind':'potential_concern','feature_code':None,
            'location':'Roof at chimney','description':'Human-selected area for independent inspection',
            'reviewer_id':'UNAUTHENTICATED-REVIEWER'}

    def test_render_three_pages_with_scan_and_rotated_layout(self):
        x=self.render()
        self.assertEqual([z['page'] for z in x['pages']],[1,2,3])
        self.assertEqual(len(list(self.output.glob('*.png'))),3)
        self.assertTrue(x['all_requested_pages_rendered'])
        self.assertFalse(x['all_report_pages_reviewed'])
        self.assertFalse(x['training_approved'])
        self.assertFalse(x['customer_release_allowed'])
        self.assertFalse(x['ocr_performed'])
        self.assertTrue(x['human_review_required'])
        self.assertTrue(x['pages'][1]['raster_image_objects_reported']>0)
        self.assertEqual(x['pages'][2]['pixel_width'],350)
        self.assertEqual(x['pages'][2]['pixel_height'],525)
        self.assertGreaterEqual(len(x['pages'][2]['untrusted_text_line_rectangles']),1)
        self.assertTrue(all(0<=v<=1 for r in x['pages'][2]['untrusted_text_line_rectangles'] for v in r))
        self.assertTrue(all(z['renderer_text_may_differ_from_imported_offsets'] for z in x['pages']))
        self.assertEqual(validate_page_evidence(x,self.bundle,self.registry,self.pdf,self.output),x)
        self.assertEqual((self.output/'manifest.json').stat().st_mode&0o777,0o600)
        self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in self.output.glob('*.png')))
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)

    def test_valid_manual_mark_is_not_a_verified_defect_or_training_label(self):
        manifest=self.render([1]);out=record_visual_marks(manifest,self.bundle,self.registry,self.pdf,self.output,[self.mark()])
        self.assertEqual(out['kind'],'PENDING_HUMAN_PDF_VISUAL_MARKS')
        self.assertFalse(out['training_approved']);self.assertFalse(out['customer_release_allowed'])
        self.assertTrue(out['not_text_quote_annotations'])
        self.assertEqual(out['marks'][0]['source_page_png_sha256'],manifest['pages'][0]['sha256'])
        self.assertFalse(out['marks'][0]['reviewer_authenticated'])
        self.assertEqual(out['marks'][0]['status'],'HUMAN_DECLARED_UNVERIFIED')
        self.assertNotIn('quote',out['marks'][0])

    def test_missing_or_swapped_source_blocks_before_creating_directory(self):
        self.bundle['source']['sha256']='0'*64
        with self.assertRaises(DataError):self.render()
        self.assertFalse(self.output.exists())
        self.bundle['source']['sha256']=sha256(self.pdf.read_bytes()).hexdigest()
        self.pdf.write_bytes(self.pdf.read_bytes()+b'attack')
        with self.assertRaises(DataError):self.render()
        self.assertFalse(self.output.exists())

    def test_bounded_page_batch_and_existing_output(self):
        for bad in ([],[1,1],[0],[4],[True],[2,1],list(range(1,MAX_BATCH_PAGES+2))):
            with self.subTest(bad=bad),self.assertRaises(DataError):self.render(bad)
        self.render([1])
        with self.assertRaises(DataError):self.render([1])

    def test_invalid_registered_bundle_or_partition_blocks(self):
        with self.assertRaises(DataError):render_batch(self.bundle,{'synthetic':False},self.pdf,self.output,[1])
        self.assertFalse(self.output.exists())
        self.bundle['bundle_sha256']='bad'
        with self.assertRaises(DataError):self.render([1])
        self.assertFalse(self.output.exists())

    def test_source_symlink_and_fifo_block(self):
        symlink=self.root/'link.pdf';symlink.symlink_to(self.pdf)
        with self.assertRaises((DataError,OSError)):render_batch(self.bundle,self.registry,symlink,self.output,[1])
        fifo=self.root/'pipe.pdf';os.mkfifo(fifo)
        with self.assertRaises((DataError,OSError)):render_batch(self.bundle,self.registry,fifo,self.output,[1])
        self.assertFalse(self.output.exists())

    def test_png_bit_change_and_forged_metadata_block_visual_marks(self):
        x=self.render([1])
        pic=self.output/'page-0001.png'
        b=bytearray(pic.read_bytes());b[-20] ^= 10;pic.write_bytes(b)
        with self.assertRaises(DataError):record_visual_marks(x,self.bundle,self.registry,self.pdf,self.output,[self.mark()])
        # Even with recomputed file+manifest hashes, an altered PNG cannot pass
        # source-PDF re-render comparison.
        forged=copy.deepcopy(x);forged['pages'][0]['sha256']=sha256(b).hexdigest()
        forged['manifest_sha256']=digest({k:v for k,v in forged.items() if k!='manifest_sha256'})
        with self.assertRaises(DataError):record_visual_marks(forged,self.bundle,self.registry,self.pdf,self.output,[self.mark()])

    def test_manifest_forgery_unrelated_field_blocked(self):
        x=self.render([2]);forged=copy.deepcopy(x)
        forged['customer_release_allowed']=True
        forged['manifest_sha256']=digest({k:v for k,v in forged.items() if k!='manifest_sha256'})
        with self.assertRaises(DataError):validate_page_evidence(forged,self.bundle,self.registry,self.pdf,self.output)

    def test_mark_rejects_invented_page_region_and_code(self):
        m=self.render([1]);mark=self.mark()
        bad=[dict(mark,page=2),dict(mark,bbox=[0,0,1,1.5]),dict(mark,bbox=[0,0,0,1]),
             dict(mark,bbox=[True,.1,.2,.4]),dict(mark,kind='feature',feature_code='cladding_type'),
             dict(mark,kind='potential_concern',feature_code='roof_covering'),
             dict(mark,reviewer_id=''),dict(mark,id='bad/../../'),dict(mark,location='')]
        for row in bad:
            with self.subTest(row=row),self.assertRaises(DataError):record_visual_marks(
                m,self.bundle,self.registry,self.pdf,self.output,[row])
        with self.assertRaises(DataError):record_visual_marks(m,self.bundle,self.registry,self.pdf,self.output,[mark,mark])

    def test_stale_registry_and_broken_png_after_render_block(self):
        x=self.render([1])
        with self.assertRaises(DataError):record_visual_marks(x,self.bundle,{'synthetic':False},self.pdf,self.output,[self.mark()])
        (self.output/'page-0001.png').unlink()
        with self.assertRaises(DataError):record_visual_marks(x,self.bundle,self.registry,self.pdf,self.output,[self.mark()])

    def test_page_images_and_original_pdf_remain_unchanged_after_marking(self):
        x=self.render([1,2]);b=self.pdf.read_bytes();pngs={p.name:p.read_bytes() for p in self.output.glob('*.png')}
        record_visual_marks(x,self.bundle,self.registry,self.pdf,self.output,[self.mark(1)])
        self.assertEqual(self.pdf.read_bytes(),b)
        self.assertEqual({p.name:p.read_bytes() for p in self.output.glob('*.png')},pngs)

    def test_integrated_independent_review_cli_rechecks_original_source_pixels(self):
        from inspection_engine.report_visual_reconciliation import main as compare_main
        x=self.render([1]);src=self.root/'bundle.json';reg=self.root/'registry.json'
        src.write_text(json.dumps(self.bundle));reg.write_text(json.dumps(self.registry))
        first=record_visual_marks(x,self.bundle,self.registry,self.pdf,self.output,[self.mark()])
        second_mark=dict(self.mark(),id='second',reviewer_id='OTHER-REVIEWER',bbox=[.10,.12,.78,.8])
        second=record_visual_marks(x,self.bundle,self.registry,self.pdf,self.output,[second_mark])
        a=self.root/'first.json';b=self.root/'second.json';out=self.root/'compared.json'
        a.write_text(json.dumps(first));b.write_text(json.dumps(second))
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(compare_main(['--reference',str(src),'--registry',str(reg),
                '--source-pdf',str(self.pdf),'--manifest',str(self.output/'manifest.json'),
                '--first',str(a),'--second',str(b),'--out',str(out)]),0)
        r=json.loads(out.read_text());self.assertEqual(len(r['possible_spatial_matches']),1)
        self.assertFalse(r['ground_truth_established']);self.assertFalse(r['training_approved'])
        self.assertEqual(out.stat().st_mode&0o777,0o600)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(compare_main(['--reference',str(src),'--registry',str(reg),
                '--source-pdf',str(self.pdf),'--manifest',str(self.output/'manifest.json'),
                '--first',str(a),'--second',str(b),'--out',str(out)]),2)

    def test_cli_render_and_mark_no_customer_text_in_stdout(self):
        src=self.root/'bundle.json';reg=self.root/'reg.json';marks=self.root/'marks.json';out=self.root/'marks-out.json'
        src.write_text(json.dumps(self.bundle));reg.write_text(json.dumps(self.registry));marks.write_text(json.dumps([self.mark()]))
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code=main(['render','--reference',str(src),'--registry',str(reg),'--source-pdf',str(self.pdf),
                       '--pages','1','--out-dir',str(self.output)])
        self.assertEqual(code,0)
        self.assertNotIn('chimney',stdout.getvalue().lower())
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code=main(['mark','--reference',str(src),'--registry',str(reg),'--source-pdf',str(self.pdf),
                       '--manifest',str(self.output/'manifest.json'),'--marks',str(marks),'--out',str(out)])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out.read_text())['marks'][0]['source_pdf_sha256'],self.bundle['source']['sha256'])
        self.assertNotIn('Roof at chimney',stdout.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['mark','--reference',str(src),'--registry',str(reg),'--source-pdf',str(self.pdf),
                       '--manifest',str(self.output/'manifest.json'),'--marks',str(marks),'--out',str(out)]),2)

if __name__=='__main__':unittest.main()
