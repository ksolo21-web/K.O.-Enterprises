"""Real source-bound study workflow and held learning lifecycle tests."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from inspection_engine.core import DataError, sha256
from inspection_engine.report_layout_navigation import _image_objects_from_pdf
from inspection_engine.report_learning import import_reference,prepare_comparison,record_corrections
from inspection_engine.study_registry import empty_registry,register_bundle
from inspection_engine.report_review_queue import digest
from inspection_engine.report_understanding import capture_report_mapping,validate_report_mapping,milestone_readiness
from inspection_engine.report_study_pipeline import prepare_study,load_prepared,record_mapping,main
from inspection_engine.report_learning_candidate import build_candidate,freeze_evaluation,capture_evaluation,prepare_rollback
from scripts.build_m3_study_demo import prepare_demo


def mapping_fixture(bundle,queue,groups):
    def text(n):
        span=next(s for s in queue['spans'] if s['page']==n)
        return {'kind':'pdf_text','page':n,'span_id':span['span_id'],'offset':0,'quote':span['text'][:25]}
    region={'kind':'image_region','page':2,'bbox':[.05,.05,.95,.5]}
    return {'reviewer_id':'SYNTHETIC-DECLARATION',
        'coverage':[{'page':p['number'],'status':'declared_reviewed','note':'Synthetic source reviewed; no professional authentication'} for p in bundle['pages']],
        'sections':[{'id':'S1','title':'Declared section','anchors':[text(1)]}],
        'tables':[{'id':'T1','page':1,'column_count':3,'rows':[{'id':'R1','cells':[
            {'id':'C1','column':1,'column_span':1,'role':'header','anchors':[text(1)]},
            {'id':'C2','column':2,'column_span':1,'role':'data','anchors':[{'kind':'ocr_words','page':1,'word_indices':[1,2]}]},
            {'id':'C3','column':3,'column_span':1,'role':'blank','anchors':[{'kind':'image_region','page':1,'bbox':[.75,.2,.9,.3]}]}]}]}],
        'figures':[{'id':'FIG1','kind':'diagram','region':region,'caption_anchors':[]}],
        'findings':[{'id':'F1','system':'roof','location':'Source page 1','description':'Declared content; not a property defect',
            'anchors':[text(1)],'section_ids':['S1'],'figure_ids':['FIG1'],'table_cell_ids':['C2']},
            {'id':'F2','system':'roof','location':'Source page 3','description':'Another source context',
            'anchors':[text(3)],'section_ids':[],'figure_ids':[],'table_cell_ids':[]}],
        'relations':[{'id':'REL1','kind':'continuation','from_finding':'F1','to_finding':'F2',
            'reason':'Human declaration only','anchors':[text(1),text(3)]}]}


class CompletionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.b,cls.r,cls.q,cls.pdf,cls.groups=prepare_demo(cls.root/'demo',with_ocr=True)
        cls.declarations=mapping_fixture(cls.b,cls.q,cls.groups)
        cls.receipt=prepare_study(cls.b,cls.r,cls.pdf,cls.root/'study',ocr=True,batch_size=2)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def mapping(self,d=None,groups=None):
        return capture_report_mapping(self.b,self.r,self.q,self.pdf,
            self.groups if groups is None else groups,self.declarations if d is None else d)

    def test_unpatched_full_study_all_pages_and_receipts(self):
        self.assertEqual(self.receipt['rendered_pages'],[1,2,3])
        self.assertEqual(self.receipt['missing_ocr_for_textless_pages'],[])
        receipt,q,groups=load_prepared(self.root/'study',self.b,self.r)
        self.assertEqual(len(groups),2);self.assertEqual(q,self.q)
        self.assertFalse(receipt['full_milestone_3_complete'])
        self.assertTrue(all((self.root/'study'/p).stat().st_mode&0o777==0o600 for p in receipt['files']))

    def test_source_backed_sections_cells_figures_findings_relations(self):
        m=self.mapping();validate_report_mapping(m,self.b,self.r,self.q,self.pdf,self.groups)
        self.assertEqual(m['unresolved_pages'],[])
        self.assertEqual(m['tables'][0]['rows'][0]['unassigned_columns'],[])
        cell=m['tables'][0]['rows'][0]['cells'][1]
        self.assertEqual(len(cell['anchors'][0]['source_words_untrusted']),2)
        self.assertFalse(cell['anchors'][0]['text_is_verified_pdf_quote'])
        self.assertFalse(m['relations'][0]['records_merged'])
        self.assertFalse(m['figures'][0]['classification_verified'])
        self.assertFalse(milestone_readiness(m)['full_milestone_3_complete'])

    def test_multiline_cell_preserves_each_original_ocr_word(self):
        d=copy.deepcopy(self.declarations)
        ids=[w['word_index'] for w in self.groups[0]['ocr_record']['pages'][0]['untrusted_ocr_words']]
        d['tables'][0]['rows'][0]['cells'][1]['anchors'][0]['word_indices']=ids
        m=self.mapping(d)
        self.assertEqual(m['tables'][0]['rows'][0]['cells'][1]['anchors'][0]['source_words_untrusted'],
            self.groups[0]['ocr_record']['pages'][0]['untrusted_ocr_words'])

    def test_ragged_table_does_not_infer_blank(self):
        d=copy.deepcopy(self.declarations);d['tables'][0]['rows'][0]['cells'].pop()
        row=self.mapping(d)['tables'][0]['rows'][0]
        self.assertEqual(row['unassigned_columns'],[3]);self.assertEqual(len(row['cells']),2)

    def test_wrong_quote_offset_and_ocr_ids_rejected(self):
        for update in ({'quote':'fabricated'},{'offset':True},{'offset':999}):
            d=copy.deepcopy(self.declarations);d['sections'][0]['anchors'][0].update(update)
            with self.subTest(update=update),self.assertRaises(DataError):self.mapping(d)
        for ids in ([1,1],[999],[True],[2,1]):
            d=copy.deepcopy(self.declarations);d['tables'][0]['rows'][0]['cells'][1]['anchors'][0]['word_indices']=ids
            with self.subTest(ids=ids),self.assertRaises(DataError):self.mapping(d)

    def test_overlapping_cells_and_false_blank_rejected(self):
        d=copy.deepcopy(self.declarations);d['tables'][0]['rows'][0]['cells'][0]['column_span']=2
        with self.assertRaises(DataError):self.mapping(d)
        d=copy.deepcopy(self.declarations);d['tables'][0]['rows'][0]['cells'][1]['role']='blank'
        with self.assertRaises(DataError):self.mapping(d)

    def test_duplicate_mapping_ids_unknown_targets_and_approval_fields_rejected(self):
        changes=[lambda d:d['figures'][0].update(id='F1'),lambda d:d['findings'][0].update(figure_ids=['UNKNOWN']),
            lambda d:d.update(training_approved=True),lambda d:d['relations'][0].update(to_finding='F1')]
        for change in changes:
            d=copy.deepcopy(self.declarations);change(d)
            with self.assertRaises(DataError):self.mapping(d)

    def test_coverage_requires_all_pages_exactly_once(self):
        d=copy.deepcopy(self.declarations);d['coverage'].pop()
        with self.assertRaises(DataError):self.mapping(d)
        d=copy.deepcopy(self.declarations);d['coverage'].append(copy.deepcopy(d['coverage'][0]))
        with self.assertRaises(DataError):self.mapping(d)

    def test_unresolved_page_is_retained(self):
        d=copy.deepcopy(self.declarations);d['coverage'][1]['status']='unresolved'
        m=self.mapping(d);self.assertEqual(m['unresolved_pages'],[2])
        self.assertIn('UNRESOLVED_PAGE_DISPOSITIONS',milestone_readiness(m)['blockers'])

    def test_cross_page_relation_cannot_borrow_unrelated_page_anchors(self):
        d=copy.deepcopy(self.declarations);d['findings'][1]['anchors']=copy.deepcopy(d['findings'][0]['anchors'])
        with self.assertRaisesRegex(DataError,'endpoint'):self.mapping(d)

    def test_same_ocr_word_cannot_populate_multiple_table_cells(self):
        d=copy.deepcopy(self.declarations)
        d['tables'][0]['rows'][0]['cells'][0]['anchors']=copy.deepcopy(d['tables'][0]['rows'][0]['cells'][1]['anchors'])
        with self.assertRaisesRegex(DataError,'multiple table cells'):self.mapping(d)

    def test_no_cross_page_relation_over_missing_render(self):
        from inspection_engine.report_page_evidence import render_batch
        from inspection_engine.report_layout_navigation import build_layout_index
        root=self.root/'partial';man=render_batch(self.b,self.r,self.pdf,root,[1,3])
        layout=build_layout_index(man,self.b,self.r,self.pdf,root,self.q)
        d=copy.deepcopy(self.declarations);d['coverage'][1]['status']='unresolved';d['tables']=[];d['figures']=[]
        for f in d['findings']:f['figure_ids']=[];f['table_cell_ids']=[]
        with self.assertRaisesRegex(DataError,'intervening'):self.mapping(d,[{'manifest':man,'layout':layout,'render_dir':root}])

    def test_rehashed_mapping_changes_rejected_by_reconstruction(self):
        m=self.mapping();m['findings'][0]['finding_verified']=True
        m['mapping_sha256']=digest({k:v for k,v in m.items() if k!='mapping_sha256'})
        with self.assertRaises(DataError):validate_report_mapping(m,self.b,self.r,self.q,self.pdf,self.groups)
        m['reviewer_authenticated']=True;m['mapping_sha256']=digest({k:v for k,v in m.items() if k!='mapping_sha256'})
        with self.assertRaises(DataError):milestone_readiness(m)

    def test_mapping_export_private_and_no_overwrite(self):
        out=self.root/'mapping'
        m,g=record_mapping(self.b,self.r,self.pdf,self.root/'study',self.declarations,out)
        self.assertTrue((out/'index.html').is_file());self.assertFalse(g['full_milestone_3_complete'])
        self.assertEqual(out.stat().st_mode&0o777,0o700)
        self.assertTrue(all(p.stat().st_mode&0o777==0o700 for p in out.rglob('*') if p.is_dir()))
        with self.assertRaises(DataError):record_mapping(self.b,self.r,self.pdf,self.root/'study',self.declarations,out)

    def test_prepare_failure_rolls_back_only_new_output(self):
        out=self.root/'failure'
        with patch('inspection_engine.report_study_pipeline.build_layout_index',side_effect=DataError('synthetic failure')):
            with self.assertRaises(DataError):prepare_study(self.b,self.r,self.pdf,out)
        self.assertFalse(out.exists());self.assertTrue(self.pdf.exists())
        with self.assertRaises(DataError):prepare_study(self.b,self.r,self.pdf,self.root/'study')

    def test_study_tampering_symlinks_and_batch_traversal_rejected(self):
        copied=self.root/'altered-study';shutil.copytree(self.root/'study',copied)
        (copied/'audit.json').write_text('{}')
        with self.assertRaises(DataError):load_prepared(copied,self.b,self.r)
        link=self.root/'linked-study';link.symlink_to(self.root/'study',target_is_directory=True)
        with self.assertRaises(DataError):load_prepared(link,self.b,self.r)

    def test_rehashed_imported_html_script_is_rejected_before_export(self):
        import hashlib
        copied=self.root/'rehashed-html';shutil.copytree(self.root/'study',copied)
        page=copied/'viewer/index.html';page.write_text(page.read_text()+'<script>UNTRUSTED</script>')
        receipt=json.loads((copied/'preparation.json').read_text())
        receipt['files']['viewer/index.html']=hashlib.sha256(page.read_bytes()).hexdigest()
        receipt['preparation_sha256']=digest({k:v for k,v in receipt.items() if k!='preparation_sha256'})
        (copied/'preparation.json').write_text(json.dumps(receipt))
        out=self.root/'rejected-html-export'
        with self.assertRaisesRegex(DataError,'source-reconstructed'):
            record_mapping(self.b,self.r,self.pdf,copied,self.declarations,out)
        self.assertFalse(out.exists())

    def test_scan_without_ocr_stays_explicit(self):
        result=prepare_study(self.b,self.r,self.pdf,self.root/'no-ocr',ocr=False)
        self.assertEqual(result['missing_ocr_for_textless_pages'],[2])

    def test_cli_errors_do_not_echo_private_source_values(self):
        from contextlib import redirect_stdout
        output=io.StringIO()
        with redirect_stdout(output):
            code=main(['prepare','--reference','PRIVATE-SOURCE-DO-NOT-PRINT','--registry','missing',
                '--source-pdf','missing','--out-dir','missing'])
        self.assertEqual(code,2);self.assertNotIn('PRIVATE-SOURCE',output.getvalue())


class NestedFormTests(unittest.TestCase):
    def test_translated_scaled_nested_form_is_counted_but_not_wrongly_located(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'form.pdf';c=Canvas(str(path),pagesize=(600,800))
            c.beginForm('inner');c.drawImage(ImageReader(Image.new('RGB',(40,60),'blue')),10,20,40,60);c.endForm()
            c.beginForm('outer');c.saveState();c.scale(1.5,1.5);c.doForm('inner');c.restoreState();c.endForm()
            c.saveState();c.translate(200,300);c.doForm('outer');c.restoreState();c.showPage();c.save()
            r=_image_objects_from_pdf(path.read_bytes(),[1])[0]
            self.assertEqual(r['raster_object_count'],1);self.assertEqual(r['unlocated_raster_objects'],1)
            self.assertEqual(r['raster_object_boxes_normalized'],[])


class LearningLifecycleTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.doc,self.bundle,self.reg,self.ref=self.case('TRAIN','training_candidate','gray')
        quote=self.bundle['pages'][0]['text']
        a=[{'id':'R1','system':'roof','kind':'potential_concern','feature_code':None,'location':'Roof',
            'description':'Source declaration','page':1,'offset':0,'quote':quote}]
        self.comparison=prepare_comparison(self.doc,self.bundle,a,registry=self.reg)
        ds=[{'entry_id':'reference:R1','category':'description_correction','related_entry_ids':[],
            'evidence_ids':['P1'],'explanation':'Synthetic declared correction','lesson_text':'Original evidence first'}]
        self.corrections=record_corrections(self.doc,self.root,self.bundle,self.comparison,ds,reviewer_id='DECLARED',registry=self.reg)

    def case(self,ident,partition,color):
        image=self.root/f'{ident}.png';Image.new('RGB',(40,40),color).save(image)
        ref=self.root/f'{ident}.txt';ref.write_text('Synthetic unique report '+ident)
        b=import_reference(ref,case_id=ident,partition=partition,authorized_use=True,consented=True)
        r=register_bundle(b,empty_registry())
        d={'project_id':ident,'property':{'label':'Synthetic','inspection_date':'2026-11-01','synthetic':True},
            'media':[{'id':'P1','kind':'photo','path':image.name,'area':'roof','sha256':sha256(image)}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}
        return d,b,r,ref

    def build(self,version=1,parent=None,**updates):
        kw=dict(document=self.doc,root=self.root,bundle=self.bundle,registry=self.reg,reference_path=self.ref,
            comparison=self.comparison,corrections=self.corrections,version=version,parent=parent);kw.update(updates)
        return build_candidate(**kw)

    def test_version_lineage_rollback_never_activates(self):
        a=self.build();b=self.build(2,a);rollback=prepare_rollback(b,a)
        self.assertEqual(rollback['restored_candidate'],a);self.assertFalse(rollback['runtime_changed'])
        self.assertFalse(a['activated']);self.assertFalse(rollback['training_approved'])
        with self.assertRaises(DataError):self.build(3,a)
        with self.assertRaises(DataError):prepare_rollback(a,b)

    def test_frozen_disjoint_holdout_results_stay_unverified(self):
        c=self.build();d,b,r,ref=self.case('HOLD','locked_holdout','blue')
        plan=freeze_evaluation(c,[{'bundle':b,'registry':r,'document':d,'root':self.root,'reference_path':ref}])
        result=capture_evaluation(plan,[{'case_id':'HOLD','true_positives':5,'false_positives':0,'false_negatives':0,
            'critical_false_negatives':0,'review_record_sha256':'a'*64}])
        self.assertFalse(result['promotion_eligible']);self.assertFalse(result['labels_authenticated'])
        self.assertFalse(result['activated'])

    def test_holdout_cannot_be_candidate_and_media_leaks_reject(self):
        c=self.build();d,b,r,ref=self.case('HOLD','locked_holdout','gray')
        with self.assertRaisesRegex(DataError,'media reused'):
            freeze_evaluation(c,[{'bundle':b,'registry':r,'document':d,'root':self.root,'reference_path':ref}])
        with self.assertRaisesRegex(DataError,'Holdout'):
            self.build(bundle=b,registry=r,reference_path=ref)

    def test_corrections_source_media_and_approval_tamper_block(self):
        bad=copy.deepcopy(self.corrections);bad['training_approved']=True
        with self.assertRaises(DataError):self.build(corrections=bad)
        c=self.build();c['activated']=True;c['candidate_sha256']=digest({k:v for k,v in c.items() if k!='candidate_sha256'})
        with self.assertRaises(DataError):freeze_evaluation(c,[])
        self.ref.write_text('changed source')
        with self.assertRaises(DataError):self.build()

    def test_rehashed_authentication_flags_reject_in_lineage_and_plan(self):
        a=self.build();a['reviewer_credentials_authenticated']=True
        a['candidate_sha256']=digest({k:v for k,v in a.items() if k!='candidate_sha256'})
        with self.assertRaises(DataError):self.build(2,a)
        c=self.build();d,b,r,ref=self.case('HOLD','locked_holdout','blue')
        plan=freeze_evaluation(c,[{'bundle':b,'registry':r,'document':d,'root':self.root,'reference_path':ref}])
        plan['labels_authenticated']=True;plan['plan_sha256']=digest({k:v for k,v in plan.items() if k!='plan_sha256'})
        with self.assertRaises(DataError):capture_evaluation(plan,[])

    def test_lifecycle_cli_writes_only_new_held_plan(self):
        from contextlib import redirect_stdout
        from inspection_engine.report_learning_candidate import main as lifecycle_main
        a=self.build();b=self.build(2,a)
        old=self.root/'v1.json';new=self.root/'v2.json';out=self.root/'rollback.json'
        old.write_text(json.dumps(a));new.write_text(json.dumps(b))
        args=['rollback-plan','--current',str(new),'--previous',str(old),'--out',str(out)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(lifecycle_main(args),0);self.assertEqual(lifecycle_main(args),2)
        self.assertFalse(json.loads(out.read_text())['runtime_changed'])
        self.assertEqual(out.stat().st_mode&0o777,0o600)

    def test_rehashed_empty_or_malformed_candidate_media_reject(self):
        for changes in ({'case_media_sha256':[]},{'source_sha256':'x'*64},
                {'case_media_sha256':['a'*64,'a'*64]}):
            a=self.build();a.update(changes);a['candidate_sha256']=digest({k:v for k,v in a.items() if k!='candidate_sha256'})
            with self.subTest(changes=changes),self.assertRaises(DataError):self.build(2,a)


if __name__=='__main__':unittest.main()
