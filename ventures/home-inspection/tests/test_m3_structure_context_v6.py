"""Synthetic geometry and unpatched import/OCR/viewer integration evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from inspection_engine.core import DataError
from inspection_engine.report_layout_navigation import _ocr_rows, build_layout_index
from inspection_engine.report_review_queue import digest
from inspection_engine.report_structure_candidates import (
    build_structure_candidates, validate_structure_candidates, build_boundary_context)
from inspection_engine.report_study_viewer import build_study_viewer
from scripts.build_m3_study_demo import prepare_demo


def geometry(rows=4, columns=3):
    words=[]
    for y in range(rows):
        for x in range(columns):
            words.append({'word_index':len(words)+1,'text_untrusted':f'word-{y}-{x}',
                'bbox_normalized':[.08+x*.27,.10+y*.055,.18+x*.27,.125+y*.055],
                'confidence_untrusted':95})
    return words


def candidate_fixture(words):
    ocr={'pages':[{'page':1,'ocr_word_count':len(words),'untrusted_ocr_words':words}],
        'training_approved':False,'customer_release_allowed':False,'converted_to_reference_quotes':False}
    ocr['record_sha256']=digest(ocr)
    layout={'kind':'M3_UNVERIFIED_LAYOUT_NAVIGATION_V4','case_id':'SYNTH-V6',
        'training_approved':False,'customer_release_allowed':False,'reading_order_verified':False,
        'ocr_record_sha256':ocr['record_sha256'],'pages':[{'page':1,'ocr_performed':True,
            'ocr_word_count':len(words),'ocr_navigation_rows':_ocr_rows(words),'text_span_ids':[]}]}
    layout['index_sha256']=digest(layout)
    return layout,ocr


class StructureCandidatesTests(unittest.TestCase):
    def build(self,words):
        layout,ocr=candidate_fixture(words)
        return build_structure_candidates(layout,ocr),layout,ocr

    def test_exact_source_word_identity_text_and_geometry_preserved(self):
        words=geometry();result,l,o=self.build(words)
        p=result['pages'][0];self.assertEqual(len(p['table_candidates_unverified']),1)
        cells=[cell for row in p['table_candidates_unverified'][0]['rows_unverified'] for cell in row['cells_unverified']]
        self.assertEqual([w for c in cells for w in c['source_words_untrusted']],words)
        self.assertEqual(p['unassigned_word_indices'],[])
        self.assertEqual(result,validate_structure_candidates(result,l,o))
        self.assertFalse(result['table_structure_verified'])

    def test_two_rows_never_establish_candidate(self):
        result,_,_=self.build(geometry(rows=2));p=result['pages'][0]
        self.assertEqual(p['table_candidates_unverified'],[])
        self.assertEqual(p['unassigned_word_indices'],list(range(1,7)))

    def test_multiword_cell_stays_exact_and_not_a_pdf_quote(self):
        words=geometry()
        words.insert(1,{'word_index':0,'text_untrusted':'second','bbox_normalized':[.19,.1,.23,.125],'confidence_untrusted':80})
        for i,w in enumerate(words,1):w['word_index']=i
        result,_,_=self.build(words)
        cell=result['pages'][0]['table_candidates_unverified'][0]['rows_unverified'][0]['cells_unverified'][0]
        self.assertEqual(cell['word_indices'],[1,2]);self.assertEqual(cell['text_untrusted'],'word-0-0 second')
        self.assertNotIn('verified_pdf_quote',cell)

    def test_missing_column_is_unassigned_without_inferred_blank(self):
        words=geometry(rows=7);words.pop(10)
        for i,w in enumerate(words,1):w['word_index']=i
        result,_,_=self.build(words);p=result['pages'][0]
        self.assertEqual(len(p['table_candidates_unverified']),2)
        self.assertEqual(len(p['unassigned_word_indices']),2)
        self.assertTrue(all(not c['blank_cells_inferred'] for c in p['table_candidates_unverified']))

    def test_multiline_extra_row_does_not_join_to_neighbor(self):
        words=geometry()
        words.append({'word_index':len(words)+1,'text_untrusted':'wrapped',
            'bbox_normalized':[.08,.135,.18,.145],'confidence_untrusted':80})
        result,_,_=self.build(words);p=result['pages'][0]
        self.assertIn(len(words),p['unassigned_word_indices'])
        self.assertTrue(all(not c['multiline_cells_joined'] for c in p['table_candidates_unverified']))

    def test_crossing_word_retained_without_fabricated_cells(self):
        words=geometry();words[4]['bbox_normalized'][2]=.7
        result,_,_=self.build(words);p=result['pages'][0]
        self.assertTrue(p['all_ocr_words_accounted_for_once'])
        self.assertEqual(p['table_candidates_unverified'],[])
        self.assertEqual(p['unassigned_word_indices'],list(range(1,13)))

    def test_two_column_prose_is_always_labeled_ambiguous(self):
        result,_,_=self.build(geometry(columns=2))
        c=result['pages'][0]['table_candidates_unverified'][0]
        self.assertIn('ALIGNED_PROSE_OR_COLUMNS_MAY_MIMIC_A_TABLE',c['warnings'])
        self.assertFalse(c['headers_identified'])

    def test_repeated_header_does_not_receive_header_role(self):
        words=geometry()
        for w in words:w['text_untrusted']='Header'
        result,_,_=self.build(words)
        self.assertFalse(result['pages'][0]['table_candidates_unverified'][0]['headers_identified'])

    def test_large_vertical_break_splits_candidate_blocks(self):
        words=geometry(rows=6)
        for w in words[9:]:
            w['bbox_normalized'][1]+=.2;w['bbox_normalized'][3]+=.2
        result,_,_=self.build(words)
        self.assertEqual(len(result['pages'][0]['table_candidates_unverified']),2)

    def test_stale_or_rehashed_candidate_output_rejected(self):
        result,l,o=self.build(geometry());result['pages'][0]['unassigned_word_indices']=[999]
        result['structure_sha256']=digest({k:v for k,v in result.items() if k!='structure_sha256'})
        with self.assertRaises(DataError):validate_structure_candidates(result,l,o)

    def test_altered_ocr_without_new_receipt_rejected(self):
        result,l,o=self.build(geometry());o['pages'][0]['untrusted_ocr_words'][0]['text_untrusted']='changed'
        with self.assertRaises(DataError):build_structure_candidates(l,o)

    def test_no_ocr_has_no_invented_table(self):
        l,o=candidate_fixture([]);l['ocr_record_sha256']=None
        l['pages'][0]['ocr_performed']=False
        l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        p=build_structure_candidates(l)['pages'][0]
        self.assertFalse(p['ocr_performed']);self.assertEqual(p['table_candidates_unverified'],[])


class RealUpstreamIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.data=prepare_demo(cls.root/'case',with_ocr=bool(shutil.which('tesseract')))

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def build(self,*,data=None,batches=None):
        b,r,q,p,groups=data or self.data
        target=self.root/f'viewer-{self._testMethodName}'
        return build_study_viewer(b,r,q,p,batches=groups if batches is None else batches,out_dir=target),target

    def test_real_import_registry_render_layout_ocr_viewer_two_batches(self):
        receipt,out=self.build();b,r,q,p,groups=self.data
        self.assertEqual(receipt['rendered_pages'],[1,2,3]);self.assertEqual(receipt['unrendered_pages'],[])
        self.assertFalse(receipt['all_pages_professionally_reviewed'])
        context=json.loads((out/'boundary-context.json').read_text())
        self.assertEqual([x['boundary_id'] for x in context['boundaries']],['P0001-P0002','P0002-P0003'])
        self.assertFalse(context['boundaries'][0]['sides'][1]['extractable_text_available'])
        self.assertEqual(context['boundaries'][0]['sides'][1]['source_spans'],[])
        if not shutil.which('tesseract'):self.skipTest('Tesseract absent: OCR integration untested')
        self.assertTrue(groups[0]['ocr_record']['pages'][1]['ocr_word_count']>0)
        structure=json.loads((out/'structure-candidates.json').read_text())
        self.assertTrue(structure[0]['pages'][0]['table_candidates_unverified'])
        self.assertFalse(receipt['training_approved']);self.assertFalse(receipt['customer_release_allowed'])
        for key,name in [('structure_file_sha256','structure-candidates.json'),('boundary_context_file_sha256','boundary-context.json')]:
            self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),receipt[key])
            self.assertEqual((out/name).stat().st_mode&0o777,0o600)
        s=(out/'index.html').read_text();self.assertIn('&lt;script&gt;',s)
        self.assertNotIn('<script>',s);self.assertNotIn('https://',s)

    def test_missing_middle_render_never_bridges_pages_one_and_three(self):
        b,r,q,p,groups=self.data
        # Build a genuine separate manifest for page 1 only, retaining page 3.
        from inspection_engine.report_page_evidence import render_batch
        manifest=render_batch(b,r,p,self.root/'one-page',[1])
        layout=build_layout_index(manifest,b,r,p,self.root/'one-page',q)
        partial=[{'manifest':manifest,'layout':layout,'render_dir':self.root/'one-page'},groups[1]]
        receipt,out=self.build(batches=partial)
        self.assertEqual(receipt['unrendered_pages'],[2])
        context=json.loads((out/'boundary-context.json').read_text())
        self.assertEqual(len(context['boundaries']),2)
        self.assertFalse(any(x['both_page_images_available'] for x in context['boundaries']))
        self.assertTrue(all(not x['text_joined'] for x in context['boundaries']))
        self.assertIn('id="page-2"',(out/'index.html').read_text())

    def test_rehashed_layout_forgery_rejected_by_actual_upstream(self):
        data=list(copy.deepcopy(self.data));groups=data[4]
        groups[0]['layout']['pages'][0]['raster_object_boxes_unverified']=[[.1,.1,.8,.8]]
        l=groups[0]['layout'];l['index_sha256']=digest({k:v for k,v in l.items() if k!='index_sha256'})
        with self.assertRaises(DataError):self.build(data=data)

    def test_real_registry_tamper_blocks_viewer(self):
        data=list(copy.deepcopy(self.data));data[1]['case_partitions']['SYNTH-M3-V6']='training_candidate'
        with self.assertRaises(DataError):self.build(data=data)

    def test_real_source_and_image_mutation_fail_before_output(self):
        data=list(copy.deepcopy(self.data));altered=self.root/'altered.pdf'
        altered.write_bytes(data[3].read_bytes()+b'changed');data[3]=altered
        with self.assertRaises(DataError):self.build(data=data)

    def test_boundary_chunks_remain_exact_source_spans(self):
        b,r,q,p,g=self.data;context=build_boundary_context(b,r,q,[1,3])
        source={s['span_id']:s for s in q['spans']}
        for boundary in context['boundaries']:
            self.assertFalse(boundary['semantic_continuation_established'])
            for side in boundary['sides']:
                for span in side['source_spans']:self.assertEqual(span,source[span['span_id']])

    def test_bad_render_coverage_rejected(self):
        b,r,q,p,g=self.data
        for pages in ([True],[1,1],[3,1],[4]):
            with self.subTest(pages=pages),self.assertRaises(DataError):build_boundary_context(b,r,q,pages)

    def test_total_assets_bound_leaves_no_partial_output(self):
        with patch('inspection_engine.report_study_viewer.MAX_TOTAL_ASSET_BYTES',1):
            with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/f'viewer-{self._testMethodName}').exists())

    def test_metadata_bound_leaves_no_partial_output(self):
        with patch('inspection_engine.report_study_viewer.MAX_METADATA_BYTES',1):
            with self.assertRaises(DataError):self.build()
        self.assertFalse((self.root/f'viewer-{self._testMethodName}').exists())

    def test_no_symlink_ancestors_in_output(self):
        b,r,q,p,g=self.data
        linked=self.root/'link';linked.symlink_to(self.root/'case',target_is_directory=True)
        with self.assertRaises(DataError):
            build_study_viewer(b,r,q,p,batches=g,out_dir=linked/'render-1'/'viewer')


if __name__=='__main__':unittest.main()
