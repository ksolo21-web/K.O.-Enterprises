"""Synthetic test cases; no professional property cases or automatic learning."""
from __future__ import annotations
import copy,hashlib,io,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from inspection_engine.core import DataError
from inspection_engine.report_review_queue import digest
from inspection_engine.report_reading_order import build_reading_order,validate_reading_order
from inspection_engine.report_study_viewer import build_study_viewer,render_html,_checked_png,_box_overlay


def word(i,x,y,text):
    return {'word_index':i,'text_untrusted':text,'bbox_normalized':[x,y,round(x+.06,5),round(y+.018,5)],'confidence_untrusted':95}


def fixture(page=1,include_ocr=True,heading=False):
    words=[];rows=[]
    if include_ocr:
        if heading:
            # Full-width heading crosses any center gutter.
            words.append({'word_index':1,'text_untrusted':'HEADLINE','bbox_normalized':[.35,.03,.64,.06], 'confidence_untrusted':98})
            rows.append({'row_id':'ROW-0001','ocr_word_indices':[1]})
        for j in range(4):
            ids=[]
            for k,(x,text) in enumerate(((.09,f'L{j}a'),(.19,f'L{j}b'),(.60,f'R{j}a'),(.72,f'R{j}b'))):
                number=len(words)+1;words.append(word(number,x,.13+j*.07,text));ids.append(number)
            rows.append({'row_id':f'ROW-{len(rows)+1:04d}','ocr_word_indices':ids})
    ocr={'schema_version':1,'kind':'UNTRUSTED_LOCAL_OCR_PAGE_REVIEW','pages':[{'page':page,'ocr_word_count':len(words),'untrusted_ocr_words':words}],
         'converted_to_reference_quotes':False,'training_approved':False,'customer_release_allowed':False}
    ocr['record_sha256']=digest(ocr)
    l={'schema_version':1,'kind':'M3_UNVERIFIED_LAYOUT_NAVIGATION_V4','case_id':'SYNTH-M3-V5',
       'ocr_record_sha256':ocr['record_sha256'] if include_ocr else None,
       'pages':[{'page':page,'ocr_performed':include_ocr,'ocr_word_count':len(words),
                 'ocr_navigation_rows':rows,'text_span_ids':['P0001-C000000'],'raster_object_boxes_unverified':[[.1,.5,.5,.8]],
                 'pdf_text_line_boxes_untrusted':[[.1,.1,.9,.18]]}],
       'reading_order_verified':False,'training_approved':False,'customer_release_allowed':False}
    l['index_sha256']=digest(l)
    return l,ocr if include_ocr else None


class ReadingOrderTests(unittest.TestCase):
    def test_two_column_order_has_exact_no_loss_coverage(self):
        layout,ocr=fixture();result=build_reading_order(layout,ocr);p=result['pages'][0]
        self.assertEqual(p['mode'],'POSSIBLE_TWO_COLUMN_UNVERIFIED')
        lines=p['candidate_lines'];self.assertEqual(len(lines),8)
        self.assertEqual([row['untrusted_reading_text'] for row in lines][:4],['L0a L0b','L1a L1b','L2a L2b','L3a L3b'])
        self.assertEqual([row['untrusted_reading_text'] for row in lines][4:],['R0a R0b','R1a R1b','R2a R2b','R3a R3b'])
        self.assertEqual(sorted(i for row in lines for i in row['word_indices']),list(range(1,17)))
        self.assertFalse(result['reading_order_verified']);self.assertFalse(result['training_approved'])
        self.assertEqual(result,validate_reading_order(result,layout,ocr))
    def test_full_width_heading_stays_above_both_columns(self):
        layout,ocr=fixture(heading=True);result=build_reading_order(layout,ocr)
        self.assertEqual(result['pages'][0]['candidate_lines'][0]['untrusted_reading_text'],'HEADLINE')
        self.assertEqual(len(result['pages'][0]['candidate_lines']),9)
    def test_missing_ocr_is_explicit_unavailable(self):
        layout,_=fixture(include_ocr=False);r=build_reading_order(layout)
        self.assertEqual(r['pages'][0]['mode'],'NO_OCR_READING_ORDER_AVAILABLE')
        self.assertEqual(r['pages'][0]['text_span_ids_unordered'],['P0001-C000000'])
    def test_one_row_does_not_prove_columns(self):
        l,o=fixture();o['pages'][0]['untrusted_ocr_words']=o['pages'][0]['untrusted_ocr_words'][:4]
        o['pages'][0]['ocr_word_count']=4;o['record_sha256']=digest({k:v for k,v in o.items() if k!='record_sha256'})
        l['pages'][0]['ocr_navigation_rows']=l['pages'][0]['ocr_navigation_rows'][:1]
        l['pages'][0]['ocr_word_count']=4;l['ocr_record_sha256']=o['record_sha256'];l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        self.assertEqual(build_reading_order(l,o)['pages'][0]['mode'],'ROW_MAJOR_UNVERIFIED')
    def test_changed_ocr_word_or_digest_rejected(self):
        l,o=fixture();o['pages'][0]['untrusted_ocr_words'][0]['text_untrusted']='TAMPER'
        with self.assertRaises(DataError):build_reading_order(l,o)
    def test_missing_or_repeated_word_index_rejected(self):
        l,o=fixture();l['pages'][0]['ocr_navigation_rows'][0]['ocr_word_indices']=[1,1,3,4]
        l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        with self.assertRaises(DataError):build_reading_order(l,o)
    def test_duplicate_row_word_silently_not_allowed(self):
        l,o=fixture();l['pages'][0]['ocr_navigation_rows'][0]['ocr_word_indices'].append(4)
        l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        with self.assertRaises(DataError):build_reading_order(l,o)
    def test_invalid_geometry_and_boolean_rejected(self):
        for bbox in ([0,0,1.3,.2],[0,0,False,.2],[.8,.2,.7,.3]):
            l,o=fixture();o['pages'][0]['untrusted_ocr_words'][0]['bbox_normalized']=bbox
            o['record_sha256']=digest({k:v for k,v in o.items() if k!='record_sha256'})
            l['ocr_record_sha256']=o['record_sha256'];l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
            with self.subTest(bbox=bbox),self.assertRaises(DataError):build_reading_order(l,o)
    def test_ocr_without_record_refused(self):
        l,o=fixture();withheld=copy.deepcopy(l)
        with self.assertRaises(DataError):build_reading_order(withheld,None)
    def test_forged_approval_rejected(self):
        l,o=fixture();l['training_approved']=True;l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        with self.assertRaises(DataError):build_reading_order(l,o)
    def test_reordered_source_evidence_fails_validation(self):
        l,o=fixture();r=build_reading_order(l,o);r['pages'][0]['candidate_lines'][0]['word_indices']=[16]
        with self.assertRaises(DataError):validate_reading_order(r,l,o)


class ViewerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.src=self.root/'input.pdf';self.src.write_bytes(b'%PDF-test synthetic only')
        self.render_dir=self.root/'private-render';self.render_dir.mkdir(mode=0o700)
        out=io.BytesIO();Image.new('RGB',(220,150),(230,235,240)).save(out,format='PNG')
        self.raw=out.getvalue();self.sha=hashlib.sha256(self.raw).hexdigest()
        (self.render_dir/'page-0001.png').write_bytes(self.raw)
        self.manifest={'manifest_sha256':'b'*64,'pages':[{'page':1,'image_path':'page-0001.png','sha256':self.sha}],
                       'pdf_source_sha256':hashlib.sha256(self.src.read_bytes()).hexdigest()}
        self.layout,self.ocr=fixture()
        self.bundle={'case_id':'SYNTH-M3-V5','source':{'format':'pdf','sha256':self.manifest['pdf_source_sha256']},
                     'bundle_sha256':'a'*64,'pages':[{'number':1},{'number':2}]}
        self.registry={};self.queue={'spans':[{'page':1,'span_id':'P0001-C000000','text':'<script>alert("XSS")</script>\nA roof photo is not proof.'}]}
        self.batch={'manifest':self.manifest,'layout':self.layout,'ocr_record':self.ocr,'render_dir':self.render_dir}

    def build(self,out=None,batches=None):
        # Isolated fixture supplies the already-verified upstream source receipts.
        # Actual production function calls those immutable validations without stubbing.
        stub_learn=types.SimpleNamespace(validate_bundle=lambda x:x)
        stub_registry=types.SimpleNamespace(require_registered=lambda b,r:r)
        with patch.dict(sys.modules,{'inspection_engine.report_learning':stub_learn,'inspection_engine.study_registry':stub_registry}), \
             patch('inspection_engine.report_study_viewer.validate_review_queue',return_value=self.queue), \
             patch('inspection_engine.report_study_viewer.validate_layout_index',return_value=self.layout), \
             patch('inspection_engine.report_study_viewer._source',side_effect=lambda path:Path(path).read_bytes()):
            return build_study_viewer(self.bundle,self.registry,self.queue,self.src,
                                      batches=batches if batches is not None else [self.batch],
                                      out_dir=out or (self.root/'viewer'))
    def test_private_offline_html_assets_and_missing_pages(self):
        record=self.build();html=(self.root/'viewer/index.html').read_text()
        self.assertEqual(record['unrendered_pages'],[2]);self.assertFalse(record['all_pdf_pages_rendered'])
        self.assertEqual((self.root/'viewer/assets/page-0001.png').read_bytes(),self.raw)
        self.assertIn('PARTIAL_SOURCE_COVERAGE',html);self.assertIn('Missing rendered pages: 2',html)
        self.assertIn('L0a L0b',html);self.assertIn('R0a R0b',html)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        self.assertIn('Content-Security-Policy',html);self.assertNotIn('https://',html)
        self.assertNotIn('<script ',html);self.assertFalse(record['customer_release_allowed'])
        self.assertEqual((self.root/'viewer').stat().st_mode&0o777,0o700)
        self.assertEqual((self.root/'viewer/index.html').stat().st_mode&0o777,0o600)
    def test_refuses_existing_output_and_preserves_original(self):
        self.build()
        with self.assertRaises(DataError):self.build()
        self.assertEqual((self.root/'viewer/assets/page-0001.png').read_bytes(),self.raw)
    def test_tampered_png_blocks_and_no_partial_output(self):
        (self.render_dir/'page-0001.png').write_bytes(b'not a PNG')
        with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/'viewer').exists())
    def test_symlinked_png_blocks(self):
        p=self.render_dir/'page-0001.png';p.unlink();p.symlink_to(self.src)
        with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/'viewer').exists())
    def test_duplicate_batches_rejected(self):
        with self.assertRaises(DataError):self.build(batches=[self.batch,self.batch])
    def test_no_script_injection_through_case_id(self):
        html=render_html('<img src=x onerror=alert(1)>',[1],[],[])
        self.assertIn('&lt;img',html);self.assertNotIn('<img src=x',html)
    def test_unsafe_box_rejected(self):
        for bbox in ([0,0,2,.3],[0,0,False,.3],[.7,.5,.2,.9]):
            with self.subTest(bbox=bbox),self.assertRaises(DataError):_box_overlay(bbox,'text')
    def test_html_does_not_run_remote_scripts(self):
        s=render_html('TEST',[1],[2],[])
        self.assertIn("connect-src 'none'",s)
        self.assertNotIn('<script',s);self.assertNotIn('<iframe',s)
    def test_changed_pdf_detected_before_any_output(self):
        self.src.write_bytes(self.src.read_bytes()+b'changed')
        with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/'viewer').exists())
    def test_pdf_changed_during_asset_copy_rolls_back(self):
        original=_checked_png
        def mutate(*args):
            value=original(*args)
            self.src.write_bytes(self.src.read_bytes()+b'RACE')
            return value
        with patch('inspection_engine.report_study_viewer._checked_png',side_effect=mutate):
            with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/'viewer').exists())
    def test_source_unknown_page_not_disguised_as_complete(self):
        self.bundle['pages'].append({'number':3})
        receipt=self.build();self.assertEqual(receipt['unrendered_pages'],[2,3])
    def test_cleanup_on_write_exception(self):
        with patch('inspection_engine.report_study_viewer.os.fsync',side_effect=OSError('disk write failed')):
            with self.assertRaises(OSError):self.build()
        self.assertFalse((self.root/'viewer').exists())
    def test_parent_symlink_is_refused(self):
        linked=self.root/'linked';linked.symlink_to(self.render_dir,target_is_directory=True)
        with self.assertRaises(DataError):self.build(out=linked/'viewer')

if __name__=='__main__':unittest.main()
