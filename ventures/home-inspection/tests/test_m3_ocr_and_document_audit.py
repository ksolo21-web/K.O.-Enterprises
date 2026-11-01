"""Synthetic PDF/OCR integration; never a real inspector label or field benchmark."""
from __future__ import annotations
import copy
import io
import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from inspection_engine.core import DataError
from inspection_engine.report_page_evidence import render_batch,record_visual_marks
from inspection_engine.report_review_queue import build_review_queue,digest
from inspection_engine.report_ocr_review import ocr_review_batch,validate_ocr_record,_words
from inspection_engine.report_document_coverage import plan_document,audit_document,cross_modal_queue,record_cross_modal_decisions


class ScannedReportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pdf=self.root/'source.pdf'
        image=Image.new('RGB',(1000,340),'white')
        draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',37)
        draw.text((35,95),'ELECTRICAL PANEL COVER MISSING',fill='black',font=font)
        doc=Canvas(str(self.pdf),pagesize=(550,300))
        doc.setFont('Helvetica',16);doc.drawString(30,245,'Roof inspection narrative: no leaks observed.')
        doc.showPage()
        doc.drawImage(ImageReader(image),20,35,width=500,height=200)
        doc.showPage()
        doc.setFont('Helvetica',12);doc.drawString(20,245,'Water heater disconnected, not inspected.')
        doc.showPage();doc.save()
        raw=self.pdf.read_bytes()
        # The M3 v2 isolated test harness verifies source identity through its
        # stubbed source registry; production validators remain unchanged.
        self.bundle={'case_id':'SYNTHETIC-SCAN','partition':'locked_holdout',
            'kind':'UNVERIFIED_REFERENCE_TEXT','bundle_sha256':'a'*64,
            'source':{'format':'pdf','sha256':sha256(raw).hexdigest(),'bytes':len(raw)},
            'pages':[{'number':1,'text':'Roof inspection narrative: no leaks observed.',
                'text_available':True,'has_raster_images':False},
                {'number':2,'text':'','text_available':False,'has_raster_images':True},
                {'number':3,'text':'Water heater disconnected, not inspected.',
                'text_available':True,'has_raster_images':False}]}
        self.registry={'synthetic':True}
        self.queue=build_review_queue(self.bundle,self.registry)
        self.groups=[]

    def render(self,pages,which):
        root=self.root/which
        man=render_batch(self.bundle,self.registry,self.pdf,root,pages)
        self.groups.append({'manifest':man,'render_dir':str(root)})
        return man,root

    def mark(self,man,root,id,reviewer,*,system='electrical'):
        candidate={'id':id,'page':2,'bbox':[.12,.2,.88,.79],
            'system':system,'kind':'potential_concern','feature_code':None,
            'location':'Main service panel','description':'Human-declared review candidate',
            'reviewer_id':reviewer}
        return record_visual_marks(man,self.bundle,self.registry,self.pdf,root,[candidate])

    def test_real_offline_ocr_retains_original_image_receipt_and_no_findings(self):
        man,root=self.render([2],'pages')
        original=(root/'page-0002.png').read_bytes()
        out=ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2])
        self.assertEqual(out['kind'],'UNTRUSTED_LOCAL_OCR_PAGE_REVIEW')
        self.assertTrue(out['ocr_words_are_unverified'])
        self.assertFalse(out['converted_to_reference_quotes'])
        self.assertFalse(out['training_approved']);self.assertFalse(out['customer_release_allowed'])
        self.assertTrue(out['pages'][0]['ocr_word_count']>=2)
        words=' '.join(w['text_untrusted'] for w in out['pages'][0]['untrusted_ocr_words']).upper()
        self.assertIn('PANEL',words)
        self.assertEqual(out['pages'][0]['source_page_png_sha256'],man['pages'][0]['sha256'])
        self.assertEqual((root/'page-0002.png').read_bytes(),original)
        self.assertIs(validate_ocr_record(out,man),out)

    def test_ocr_wrong_source_and_bad_page_refused(self):
        man,root=self.render([2],'pages')
        with self.assertRaises(DataError):ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[1])
        with self.assertRaises(DataError):ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2,2])
        with self.assertRaises(DataError):ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[True])
        with self.assertRaises(DataError):ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[])
        (root/'page-0002.png').write_bytes(b'corrupt')
        with self.assertRaises(DataError):ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2])

    def test_fake_ocr_untrusted_classification_cannot_claim_promotion(self):
        man,root=self.render([2],'pages')
        out=ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2])
        for key,value in [('training_approved',True),('converted_to_reference_quotes',True),('status','APPROVED')]:
            forged=copy.deepcopy(out);forged[key]=value
            forged['record_sha256']=digest({k:v for k,v in forged.items() if k!='record_sha256'})
            with self.subTest(key=key),self.assertRaises(DataError):validate_ocr_record(forged,man)
        forged=copy.deepcopy(out);forged['pages'][0]['source_page_png_sha256']='0'*64
        forged['record_sha256']=digest({k:v for k,v in forged.items() if k!='record_sha256'})
        with self.assertRaises(DataError):validate_ocr_record(forged,man)

    def test_bad_tsv_geometry_and_oversized_rows_rejected(self):
        text=b'level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t999\t4\t40\tFake\n'
        with self.assertRaises(DataError):_words(text,100,100)
        with self.assertRaises(DataError):_words(b'nonsense',100,100)
        with self.assertRaises(DataError):_words(b'level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t1\t1\tNaN\tX\n',100,100)

    def test_plan_all_pages_in_bounded_batches_and_no_acceptance(self):
        plan=plan_document(self.bundle,self.registry)
        self.assertEqual(plan['total_pages'],3)
        self.assertEqual(plan['batches'],[{'batch_index':1,'pages':[1,2,3]}])
        self.assertEqual(plan['pages_actually_rendered'],0)
        self.assertFalse(plan['qualified_inspector_approved'])
        self.assertFalse(plan['training_approved'])
        with self.assertRaises(DataError):plan_document(self.bundle,{'synthetic':False})
        large=copy.deepcopy(self.bundle);large['pages']=[dict(self.bundle['pages'][0],number=i) for i in range(1,201)]
        result=plan_document(large,self.registry)
        self.assertEqual(len(result['batches']),25)
        self.assertEqual(result['batches'][-1]['pages'],[193,194,195,196,197,198,199,200])

    def test_incomplete_render_and_unreadable_page_are_reported(self):
        man,root=self.render([1,3],'partial')
        audit=audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups)
        self.assertEqual(audit['missing_rendered_pages'],[2])
        self.assertEqual(audit['missing_ocr_for_textless_pages'],[2])
        self.assertFalse(audit['pages_rendered_all'])
        self.assertFalse(audit['all_page_pixels_reviewed_by_qualified_person'])
        self.assertFalse(audit['customer_release_allowed'])
        self.assertEqual(len(audit['page_receipts']),2)

    def test_all_page_rasters_present_but_still_not_professionally_reviewed(self):
        self.render([1,2],'one');self.render([3],'two')
        audit=audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups)
        self.assertEqual(audit['missing_rendered_pages'],[])
        self.assertTrue(audit['pages_rendered_all'])
        self.assertFalse(audit['all_page_pixels_reviewed_by_qualified_person'])
        self.assertFalse(audit['visual_disagreements_resolved'])
        self.assertFalse(audit['training_approved'])

    def test_cross_batch_overlap_source_and_registry_change_block(self):
        self.render([1,2],'one');self.render([2,3],'two')
        with self.assertRaises(DataError):audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups)
        self.groups.pop()
        self.pdf.write_bytes(self.pdf.read_bytes()+b'attack')
        with self.assertRaises(DataError):audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups)

    def test_ocr_attachment_only_for_exact_page_and_no_text_quote(self):
        man,root=self.render([2],'scan')
        ocr=ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2])
        audit=audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups,ocr_records=[ocr])
        self.assertEqual(audit['missing_ocr_for_textless_pages'],[])
        self.assertIn('2',audit['ocr_page_receipts'])
        self.assertTrue(audit['no_report_defects_verified_from_ocr'])
        with self.assertRaises(DataError):audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups,
                                                        ocr_records=[ocr,ocr])

    def test_two_reviewers_and_cross_modal_queue_keep_original_marks(self):
        man,root=self.render([2],'scan')
        a=self.mark(man,root,'A','FIRST');b=self.mark(man,root,'B','SECOND',system='roof')
        pair={'manifest_sha256':man['manifest_sha256'],'first':a,'second':b}
        audit=audit_document(self.bundle,self.registry,self.queue,self.pdf,self.groups,
                             independent_reviews=[pair])
        self.assertEqual(audit['independent_visual_review_pairs'][0]['spatial_or_category_disputes'],1)
        self.assertFalse(audit['independent_reviewers_authenticated'])
        doc={'project_id':'SYNTHETIC-SCAN','property':{'label':'Synthetic','inspection_date':'2026-10-31',
            'synthetic':True},'media':[],'observations':[],'findings':[],'equipment':[],'limitations':[]}
        # Local v2 harness predates the real v1.6 imported comparison module;
        # mock only its no-agent export for this focused cross-modal boundary test.
        import inspection_engine.report_learning as learning
        def no_entries(document):return []
        with patch.object(learning,'_agent_entries',no_entries,create=True),patch.object(learning,'prepare_comparison',lambda *a,**kw:None,create=True):
            dossier=cross_modal_queue(doc,self.bundle,self.registry,self.queue,self.pdf,self.groups,
                 annotations=[],independent_reviews=[pair])
        self.assertEqual(len(dossier['visual_reference_entries']),2)
        self.assertEqual(len(dossier['visual_reference_review_ids']),2)
        self.assertTrue(dossier['all_claims_kept_separate'])
        self.assertFalse(dossier['professional_reviewer_approval_authenticated'])
        self.assertFalse(dossier['training_approved'])
        self.assertEqual(dossier['unresolved_page_numbers'],[1,2,3])

    def test_tampered_queue_rejected_by_whole_document_audit(self):
        self.render([1],'one')
        q=copy.deepcopy(self.queue);q['page_coverage'].pop()
        with self.assertRaises(DataError):audit_document(self.bundle,self.registry,q,self.pdf,self.groups)

    def test_false_review_completion_and_ocr_schema_downgrade_blocked(self):
        man,root=self.render([2],'scan')
        forged=copy.deepcopy(man);forged['all_report_pages_reviewed']=True
        forged['manifest_sha256']=digest({k:v for k,v in forged.items() if k!='manifest_sha256'})
        with self.assertRaises(DataError):audit_document(self.bundle,self.registry,self.queue,self.pdf,
              [{'manifest':forged,'render_dir':str(root)}])
        ocr=ocr_review_batch(man,self.bundle,self.registry,self.pdf,root,pages=[2])
        for field,value in [('schema_version',2),('engine_mode','AUTO_APPROVED'),('ocr_engine','Imagined engine')]:
            x=copy.deepcopy(ocr);x[field]=value
            x['record_sha256']=digest({k:v for k,v in x.items() if k!='record_sha256'})
            with self.subTest(field=field),self.assertRaises(DataError):validate_ocr_record(x,man)

    def test_link_decisions_reject_auto_approval_and_unverified_merges(self):
        man,root=self.render([2],'scan')
        a=self.mark(man,root,'A','FIRST');b=self.mark(man,root,'B','SECOND')
        pair={'manifest_sha256':man['manifest_sha256'],'first':a,'second':b}
        doc={'project_id':'SYNTHETIC-SCAN','property':{'label':'Synthetic','inspection_date':'2026-10-31',
            'synthetic':True},'media':[],'observations':[],'findings':[],'equipment':[],'limitations':[]}
        import inspection_engine.report_learning as learning
        with patch.object(learning,'_agent_entries',lambda doc: [],create=True),patch.object(learning,'prepare_comparison',lambda *a,**kw:None,create=True):
            q=cross_modal_queue(doc,self.bundle,self.registry,self.queue,self.pdf,self.groups,
                annotations=[],independent_reviews=[pair])
        choices=[{'reference_review_id':ident,'relation':'unresolved','candidate_agent_ids':[],
                 'explanation':'Qualified inspector still needed'} for ident in q['visual_reference_review_ids']]
        result=record_cross_modal_decisions(q,choices,reviewer_id='DECLARED-REVIEWER')
        self.assertEqual(result['source_decision_count'],2)
        self.assertTrue(result['all_references_preserved'])
        self.assertEqual(result['promotable_lessons'],[])
        self.assertFalse(result['reviewer_authenticated'])
        with self.assertRaises(DataError):record_cross_modal_decisions(q,choices[:1],reviewer_id='INSPECTOR')
        bad=copy.deepcopy(choices);bad[0]['relation']='possible_correspondence';bad[0]['candidate_agent_ids']=[]
        with self.assertRaises(DataError):record_cross_modal_decisions(q,bad,reviewer_id='INSPECTOR')
        fake=copy.deepcopy(q);fake['customer_release_allowed']=True
        fake['queue_sha256']=digest({k:v for k,v in fake.items() if k!='queue_sha256'})
        with self.assertRaises(DataError):record_cross_modal_decisions(fake,choices,reviewer_id='INSPECTOR')

    def test_no_text_reference_annotations_can_be_invented_from_ocr(self):
        self.render([1,2,3],'all')
        import inspection_engine.report_learning as learning
        doc={'project_id':'SYNTHETIC-SCAN','property':{'label':'Synthetic','inspection_date':'2026-10-31',
            'synthetic':True},'media':[],'observations':[],'findings':[],'equipment':[],'limitations':[]}
        with patch.object(learning,'_agent_entries',lambda doc: [],create=True),patch.object(learning,'prepare_comparison',side_effect=DataError('Invalid fabricated text annotation'),create=True):
            with self.assertRaises(DataError):cross_modal_queue(doc,self.bundle,self.registry,self.queue,
               self.pdf,self.groups,annotations=[{'fake':'OCR quote'}],independent_reviews=[])

if __name__=='__main__':unittest.main()
