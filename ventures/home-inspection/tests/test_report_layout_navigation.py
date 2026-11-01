"""Synthetic offline PDFium layout navigation, not inspector/defect validation."""
from __future__ import annotations
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from inspection_engine.core import DataError
from inspection_engine.report_review_queue import digest
from inspection_engine.report_layout_navigation import (
    _ocr_rows,_table_like,_image_objects_from_pdf,build_layout_index,validate_layout_index,main
)


class LayoutNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pdf=self.root/'synthetic.pdf'
        image=Image.new('RGB',(120,80),(128,40,20))
        b=io.BytesIO();image.save(b,format='PNG')
        c=canvas.Canvas(str(self.pdf),pagesize=(600,800))
        c.drawString(75,750,'Example inspection report - NOT A REAL CASE')
        for y,words in [(690,['Item','Condition','Note']),(655,['Roof','Unknown','Review']),(620,['Flue','Unknown','Review'])]:
            for x,w in zip([75,250,420],words):c.drawString(x,y,w)
        c.drawImage(ImageReader(io.BytesIO(b.getvalue())),150,360,width=240,height=160)
        c.showPage();c.save()
        raw=self.pdf.read_bytes();self.sha=hashlib.sha256(raw).hexdigest()
        self.bundle={'case_id':'SYNTH-M3-LAYOUT','partition':'training_candidate','bundle_sha256':'a'*64}
        self.registry={}
        self.manifest={'case_id':self.bundle['case_id'],'manifest_sha256':'b'*64,
                       'pdf_source_sha256':self.sha,
                       'pages':[{'page':1,'sha256':'c'*64,'raster_image_objects_reported':1,
                                 'untrusted_text_line_rectangles':[[.12,.03,.85,.09]],
                                 'line_rectangles_unmapped_due_to_geometry':0}]}
        self.queue={'queue_sha256':'d'*64,'spans':[{'page':1,'span_id':'P0001-C000000','text_sha256':'e'*64}],
                    'page_coverage':[{'page':1,'source_text_sha256':'f'*64}]}
        self.words=[]
        for j,y in enumerate([.15,.20,.25]):
            for i,x in enumerate([.1,.4,.7]):
                self.words.append({'word_index':len(self.words)+1,'text_untrusted':f'w{j}{i}',
                                   'bbox_normalized':[x,y,x+.08,y+.02],'confidence_untrusted':99.0})
        self.ocr={'record_sha256':'0'*64,'pages':[{'page':1,'untrusted_ocr_words':self.words}]}

    def build(self,*,ocr=True):
        with (patch('inspection_engine.report_layout_navigation.validate_page_evidence',return_value=self.manifest) as v,
              patch('inspection_engine.report_layout_navigation.validate_review_queue',return_value=self.queue) as q,
              patch('inspection_engine.report_ocr_review.validate_ocr_record',return_value=self.ocr) as o,
              patch('inspection_engine.report_layout_navigation._source',side_effect=lambda p:Path(p).read_bytes())):
            out=build_layout_index(self.manifest,self.bundle,self.registry,self.pdf,self.root,self.queue,
                                   ocr_record=self.ocr if ocr else None)
            self.assertEqual(v.call_count,1);self.assertEqual(q.call_count,1)
            self.assertEqual(o.call_count,1 if ocr else 0)
            return out

    def test_actual_pdfium_reports_image_region_and_page_binding(self):
        out=self.build();p=out['pages'][0]
        self.assertEqual(p['embedded_raster_object_count'],1)
        self.assertEqual(p['unlocated_raster_objects'],0)
        bb=p['raster_object_boxes_unverified'][0]
        self.assertTrue(.2<bb[0]<.3 and .3<bb[2]<.8)
        self.assertEqual(p['pdf_source_sha256'],self.sha)
        self.assertEqual(p['page_image_sha256'],'c'*64)
        self.assertFalse(out['training_approved']);self.assertFalse(out['customer_release_allowed'])
        self.assertFalse(out['table_cells_interpreted']);self.assertFalse(out['reading_order_verified'])

    def test_three_ocr_rows_and_possible_alignment_are_not_a_table_claim(self):
        out=self.build();p=out['pages'][0]
        self.assertEqual([len(row['ocr_word_indices']) for row in p['ocr_navigation_rows']],[3,3,3])
        self.assertEqual(len(p['possible_table_alignments_not_verified']),1)
        self.assertFalse(p['possible_table_alignments_not_verified'][0]['table_structure_confirmed'])
        self.assertTrue(p['photos_vs_diagrams_not_classified'])

    def test_images_without_ocr_still_require_review(self):
        p=self.build(ocr=False)['pages'][0]
        self.assertFalse(p['ocr_performed']);self.assertEqual(p['ocr_word_count'],0)
        self.assertEqual(p['embedded_raster_object_count'],1)
        self.assertTrue(p['page_requires_human_review'])

    def test_tampered_pdf_source_rejected(self):
        self.pdf.write_bytes(self.pdf.read_bytes()+b'altered')
        with self.assertRaises(DataError):self.build()

    def test_forged_raster_image_object_count_rejected(self):
        self.manifest['pages'][0]['raster_image_objects_reported']=0
        with self.assertRaises(DataError):self.build()

    def test_overlapping_or_corrupted_geometry_rejected(self):
        for bbox in ([0,0,1.5,1],[.4,.1,.3,.9],[0,0,True,1],[0,0,float('nan'),1]):
            with self.subTest(bbox=bbox):
                self.manifest['pages'][0]['untrusted_text_line_rectangles']=[bbox]
                with self.assertRaises(DataError):self.build()
        self.manifest['pages'][0]['untrusted_text_line_rectangles']=[[.1,.1,.9,.9]]

    def test_ocr_word_bound_and_corruption_rejected(self):
        row=self.words[0]
        for bad in ([[0,0,2,1],[0,0,0,1],[0,True,1,1]]):
            with self.subTest(bad=bad):
                row['bbox_normalized']=bad
                with self.assertRaises(DataError):self.build()
        row['bbox_normalized']=[.1,.15,.18,.17]

    def test_disabled_or_untrusted_review_cannot_approve_training(self):
        out=self.build()
        out['training_approved']=True
        with patch('inspection_engine.report_layout_navigation.validate_page_evidence'),patch('inspection_engine.report_layout_navigation.validate_review_queue'),patch('inspection_engine.report_ocr_review.validate_ocr_record'),patch('inspection_engine.report_layout_navigation._source',side_effect=lambda p:Path(p).read_bytes()):
            with self.assertRaises(DataError):validate_layout_index(out,self.manifest,self.bundle,self.registry,self.pdf,self.root,self.queue,ocr_record=self.ocr)

    def test_missing_pdf_image_is_incomplete(self):
        self.pdf=self.root/'noimage.pdf'
        c=canvas.Canvas(str(self.pdf));c.drawString(50,750,'text only');c.save()
        self.manifest['pdf_source_sha256']=hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        with self.assertRaises(DataError):self.build()

    def test_actual_pdf_rotation_retains_normalized_object_coordinates(self):
        from pypdf import PdfReader, PdfWriter
        writer=PdfWriter();page=writer.add_page(PdfReader(str(self.pdf)).pages[0]);page.rotate(90)
        rotated=self.root/'rotated.pdf'
        with rotated.open('wb') as f:writer.write(f)
        objects=_image_objects_from_pdf(rotated.read_bytes(),[1])[0]
        self.assertEqual(objects['raster_object_count'],1)
        self.assertEqual(objects['unlocated_raster_objects'],0)
        bb=objects['raster_object_boxes_normalized'][0]
        self.assertTrue(all(0<=v<=1 for v in bb))
        self.assertLess(bb[0],bb[2]);self.assertLess(bb[1],bb[3])

    def test_alignment_does_not_create_verified_table_or_cells(self):
        rows=_ocr_rows(self.words[:6])
        self.assertEqual(_table_like(rows),[])
        rows=_ocr_rows(self.words)
        self.assertTrue(_table_like(rows))
        self.assertNotIn('cells',_table_like(rows)[0])

    def test_bad_worker_arguments_fail_without_output(self):
        raw=self.pdf.read_bytes()
        cmd=[sys.executable,'-m','inspection_engine.report_layout_navigation','_worker','[1,1]']
        p=subprocess.run(cmd,input=raw,capture_output=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(p.returncode,2);self.assertFalse(p.stdout)

    def test_worker_limits_and_fails_closed(self):
        raw=self.pdf.read_bytes()
        for pages in ([],[True],[0],[201],[1]*9):
            with self.subTest(pages=pages):
                cmd=[sys.executable,'-m','inspection_engine.report_layout_navigation','_worker',json.dumps(pages)]
                r=subprocess.run(cmd,input=raw,capture_output=True,cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(r.returncode,2)

    def test_identical_repeat_validation_offline(self):
        v=self.build()
        with patch('inspection_engine.report_layout_navigation.validate_page_evidence'),patch('inspection_engine.report_layout_navigation.validate_review_queue'),patch('inspection_engine.report_ocr_review.validate_ocr_record'),patch('inspection_engine.report_layout_navigation._source',side_effect=lambda p:Path(p).read_bytes()):
            self.assertEqual(v,validate_layout_index(v,self.manifest,self.bundle,self.registry,self.pdf,self.root,self.queue,ocr_record=self.ocr))

    def test_row_coverage_keeps_every_word(self):
        rows=_ocr_rows(self.words)
        self.assertEqual(set(x for r in rows for x in r['ocr_word_indices']),set(range(1,10)))
        self.assertFalse(any(r.get('table_structure_confirmed') for r in rows))

if __name__=='__main__':unittest.main()
