"""Synthetic report-study inputs; not professional cases, labels or training."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from reportlab.pdfgen import canvas
from pypdf import PdfReader,PdfWriter
from inspection_engine.core import DataError,sha256
from inspection_engine.report_learning import (import_reference,validate_bundle,prepare_comparison,
    record_corrections,digest,MAX_TEXT)
from inspection_engine.study_registry import empty_registry,register_bundle,require_registered


class ReportLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'reference.txt';self.source.write_text('Possible mark at front wall. Same quote. Same quote.',encoding='utf-8')
        Image.new('RGB',(48,48),'gray').save(self.root/'photo.png')
        self.doc={'project_id':'SYNTHETIC-STUDY','property':{'label':'Controlled study','inspection_date':'2026-10-31','synthetic':True},
            'media':[{'id':'P1','kind':'photo','path':'photo.png','area':'exterior','sha256':sha256(self.root/'photo.png')}],
            'observations':[{'id':'O1','system':'exterior','feature':'Wall finish','feature_code':'cladding_type',
                'location':'Front wall','description':'Possible illustrative mark','status':'partially_observed',
                'review':'review_pending','evidence_ids':['P1']}],'findings':[],'equipment':[],'limitations':[]}
        self.ann=[{'id':'R1','system':'exterior','kind':'feature','feature_code':'cladding_type','location':'Front wall',
            'description':'Possible mark','page':1,'offset':0,'quote':'Possible mark at front wall.'}]
        self.bundle=self.imp();self.registry=register_bundle(self.bundle,empty_registry())

    def imp(self,**updates):
        return import_reference(self.source,**dict({'case_id':'SYNTHETIC-STUDY','partition':'training_candidate',
            'authorized_use':True,'consented':True},**updates))
    def comparison(self,bundle=None,registry=None):
        return prepare_comparison(self.doc,bundle or self.bundle,self.ann,registry=registry or self.registry)
    def decisions(self,c):
        return [{'entry_id':i,'category':'description_correction','related_entry_ids':[],
            'evidence_ids':['P1'],'explanation':'Synthetic declared correction only','lesson_text':'Use source view before describing marks'}
            for i in c['review_entry_ids']]
    def correct(self,c,ds,b=None,r=None):
        return record_corrections(self.doc,self.root,b or self.bundle,c,ds,reviewer_id='TEST-DECLARATION',registry=r or self.registry)

    def test_text_import_has_source_hash_untrusted_scope_and_no_activation(self):
        b=self.bundle;self.assertEqual(b['source']['sha256'],sha256(self.source));self.assertFalse(b['training_approved'])
        self.assertFalse(b['source_author_authenticated']);self.assertIn('IMAGES_LAYOUT',b['scope'])
        self.assertEqual(b['pages'][0]['text'],self.source.read_text())
    def test_consent_and_authorized_use_require_exact_true(self):
        for key in ('authorized_use','consented'):
            for value in (False,1,'yes',None):
                with self.subTest(key=key,value=value),self.assertRaises(DataError):self.imp(**{key:value})
    def test_corrupt_encrypted_and_empty_PDF_are_not_silent_successes(self):
        p=self.root/'bad.pdf';p.write_bytes(b'not PDF');self.source=p
        with self.assertRaises(DataError):self.imp()
        w=PdfWriter();w.add_blank_page(width=100,height=100);w.encrypt('test-only');w.write(p)
        with self.assertRaises(DataError):self.imp()
    def test_mixed_text_and_image_pages_record_limits_per_page(self):
        p=self.root/'mixed.pdf';c=canvas.Canvas(str(p));c.drawString(50,700,'Synthetic page with text and image')
        c.drawImage(str(self.root/'photo.png'),50,600,50,50);c.showPage();c.drawImage(str(self.root/'photo.png'),50,600,50,50);c.showPage();c.save()
        self.source=p;b=self.imp();self.assertEqual(len(b['pages']),2)
        self.assertTrue(b['pages'][0]['has_raster_images']);self.assertTrue(b['pages'][0]['text_available'])
        self.assertFalse(b['pages'][1]['text_available']);self.assertEqual(b['unreadable_text_pages'],[2])
        self.assertIn('NO_EXTRACTABLE_TEXT_OCR_REQUIRED',b['pages'][1]['review_limitations'])
    def test_text_limit_never_truncates(self):
        self.source.write_text('x'*(MAX_TEXT+1))
        with self.assertRaises(DataError):self.imp()
    def test_page_limit_rejected(self):
        with patch('inspection_engine.report_learning._pdf_pages',return_value=[{'text':'x','has_raster_images':False}]*201):
            p=self.root/'many.pdf';p.write_bytes(b'fixture');self.source=p
            with self.assertRaises(DataError):self.imp()
    def test_parser_timeout_is_explicit(self):
        p=self.root/'timeout.pdf';p.write_bytes(b'fixture');self.source=p
        with patch('inspection_engine.report_learning.subprocess.run',side_effect=subprocess.TimeoutExpired('test',20)),self.assertRaisesRegex(DataError,'20-second'):self.imp()
    def test_symlink_reference_rejected(self):
        p=self.root/'alias.txt';p.symlink_to(self.source);self.source=p
        with self.assertRaises(DataError):self.imp()
    def test_source_mutation_during_pdf_extract_rejected(self):
        p=self.root/'mutating.pdf';p.write_bytes(b'first');self.source=p
        def mutate(path):p.write_bytes(b'second');return [{'text':'t','has_raster_images':False}]
        with patch('inspection_engine.report_learning._pdf_pages',side_effect=mutate),self.assertRaisesRegex(DataError,'changed'):self.imp()
    def test_invented_quote_wrong_page_or_offset_rejected(self):
        for change in ({'quote':'not in source'},{'page':2},{'offset':1},{'offset':True}):
            a=copy.deepcopy(self.ann);a[0].update(change)
            with self.subTest(change=change),self.assertRaises(DataError):prepare_comparison(self.doc,self.bundle,a,registry=self.registry)
    def test_repeated_quote_bound_to_explicit_offset(self):
        a=copy.deepcopy(self.ann);a[0].update(quote='Same quote.',offset=self.source.read_text().rfind('Same quote.'))
        c=prepare_comparison(self.doc,self.bundle,a,registry=self.registry)
        self.assertEqual(c['reference_entries'][0]['offset'],a[0]['offset'])
    def test_duplicate_reference_ids_rejected_instead_of_overwritten(self):
        with self.assertRaises(DataError):prepare_comparison(self.doc,self.bundle,self.ann*2,registry=self.registry)
    def test_ambiguous_agent_matches_preserved_and_not_accepted(self):
        self.doc['observations'].append(dict(self.doc['observations'][0],id='O2'))
        c=self.comparison();self.assertEqual(len(c['candidate_matches']['reference:R1']),2)
        self.assertEqual(len(c['agent_entries']),2);self.assertFalse(c['exact_key_is_semantic_match'])
    def test_all_reference_and_agent_entries_in_review(self):
        self.doc['observations'][0]['location']='Rear wall';c=self.comparison()
        self.assertEqual(c['candidate_matches']['reference:R1'],[]);self.assertEqual(len(c['review_entry_ids']),2)
    def test_reference_case_mismatch_rejected(self):
        self.doc['project_id']='OTHER'
        with self.assertRaises(DataError):self.comparison()
    def test_bundle_tamper_and_recomputed_approval_flag_rejected(self):
        b=copy.deepcopy(self.bundle);b['pages'][0]['text']='bad'
        with self.assertRaises(DataError):validate_bundle(b)
        b=copy.deepcopy(self.bundle);b['training_approved']=True;b.pop('bundle_sha256');b['bundle_sha256']=digest(b)
        with self.assertRaises(DataError):validate_bundle(b)
    def test_forged_candidate_matches_or_stale_project_not_reused(self):
        c=self.comparison();ds=self.decisions(c);bad=copy.deepcopy(c);bad['candidate_matches']={}
        with self.assertRaises(DataError):self.correct(bad,ds)
        self.doc['observations'][0]['description']='changed'
        with self.assertRaises(DataError):self.correct(c,ds)
    def test_every_entry_requires_one_decision(self):
        c=self.comparison();ds=self.decisions(c)
        for items in (ds[:-1],ds+[ds[0]],ds+[dict(ds[0],entry_id='UNKNOWN')]):
            with self.assertRaises(DataError):self.correct(c,items)
    def test_corrected_lessons_remain_quarantined_and_unauthenticated(self):
        c=self.comparison();r=self.correct(c,self.decisions(c))
        self.assertEqual(len(r['lesson_candidates']),2);self.assertEqual(r['status'],'CORRECTIONS_CAPTURED_NOT_ACTIVATED')
        for field in ('training_approved','customer_release_allowed','prompt_modified','weights_modified','reviewer_credentials_authenticated'):
            self.assertIs(r[field],False)
    def test_actionable_correction_requires_case_evidence_and_lesson(self):
        c=self.comparison()
        for update in ({'evidence_ids':[]},{'evidence_ids':['UNKNOWN']},{'lesson_text':''}):
            ds=self.decisions(c);ds[0].update(update)
            with self.assertRaises(DataError):self.correct(c,ds)
    def test_stale_evidence_pixels_rejected(self):
        c=self.comparison();(self.root/'photo.png').write_bytes(b'tampered')
        with self.assertRaises(DataError):self.correct(c,self.decisions(c))
    def test_unresolved_rows_do_not_generate_lessons(self):
        c=self.comparison();ds=self.decisions(c)
        for d in ds:d.update(category='evidence_gap',evidence_ids=[],lesson_text='')
        self.assertEqual(self.correct(c,ds)['lesson_candidates'],[])
    def test_holdout_has_no_lesson_candidates(self):
        b=self.imp(partition='locked_holdout');r=register_bundle(b,empty_registry());c=self.comparison(b,r)
        result=self.correct(c,self.decisions(c),b,r)
        self.assertEqual(result['lesson_candidates'],[]);self.assertTrue(result['holdout_learning_excluded'])
    def test_renamed_source_cannot_move_holdout_to_training_or_new_case(self):
        b=self.imp(partition='locked_holdout');r=register_bundle(b,empty_registry())
        alias=self.root/'renamed.txt';alias.write_bytes(self.source.read_bytes());self.source=alias
        for change in ({'partition':'training_candidate'},{'partition':'training_candidate','case_id':'OTHER'}):
            with self.assertRaises(DataError):register_bundle(self.imp(**change),r)
    def test_reformatted_text_alias_cannot_evade_holdout(self):
        b=self.imp(partition='locked_holdout');r=register_bundle(b,empty_registry())
        self.source.write_text(self.source.read_text().upper().replace(' ','\n\n'))
        with self.assertRaises(DataError):register_bundle(self.imp(case_id='OTHER'),r)
    def test_new_source_for_same_case_cannot_repartition(self):
        b=self.imp(partition='locked_holdout');r=register_bundle(b,empty_registry());self.source.write_text('different report entirely')
        with self.assertRaises(DataError):register_bundle(self.imp(),r)
    def test_missing_or_tampered_registry_rejected(self):
        with self.assertRaises(DataError):require_registered(self.bundle,empty_registry())
        r=copy.deepcopy(self.registry);r['case_partitions']['SYNTHETIC-STUDY']='reference'
        with self.assertRaises(DataError):require_registered(self.bundle,r)
    def test_import_and_corrections_do_not_mutate_sources(self):
        d=copy.deepcopy(self.doc);b=copy.deepcopy(self.bundle);r=copy.deepcopy(self.registry);c=self.comparison()
        self.correct(c,self.decisions(c));self.assertEqual(self.doc,d);self.assertEqual(self.bundle,b);self.assertEqual(self.registry,r)
    def cli(self,args):
        return subprocess.run([sys.executable,'-m','inspection_engine.report_learning',*map(str,args)],capture_output=True,text=True)
    def test_cli_import_compare_correct_and_refuse_overwrite(self):
        reg=self.root/'registry.json';out=self.root/'reference.json';proj=self.root/'project.json';ann=self.root/'annotations.json'
        proj.write_text(json.dumps(self.doc));ann.write_text(json.dumps(self.ann))
        args=['import',self.source,'--case-id',self.doc['project_id'],'--partition','training_candidate','--authorized-use','--consented','--registry',reg,'--out',out]
        r=self.cli(args);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(out.stat().st_mode&0o777,0o600);self.assertEqual(reg.stat().st_mode&0o777,0o600)
        cpath=self.root/'comparison.json';r=self.cli(['compare',proj,'--reference',out,'--annotations',ann,'--registry',reg,'--out',cpath])
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);c=json.loads(cpath.read_text());dec=self.root/'decisions.json';dec.write_text(json.dumps(self.decisions(c)))
        corrected=self.root/'corrections.json';r=self.cli(['correct',proj,'--reference',out,'--comparison',cpath,'--decisions',dec,'--reviewer-id','TEST','--registry',reg,'--out',corrected])
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(json.loads(corrected.read_text())['training_approved'])
        self.assertEqual(self.cli(args).returncode,2);self.assertEqual(json.loads(proj.read_text()),self.doc)
    def test_cli_registry_lock_prevents_concurrent_update(self):
        reg=self.root/'registry.json';(self.root/'registry.json.lock').touch();out=self.root/'out.json'
        r=self.cli(['import',self.source,'--case-id','X','--partition','reference','--authorized-use','--consented','--registry',reg,'--out',out])
        self.assertEqual(r.returncode,2);self.assertFalse(out.exists());self.assertFalse(reg.exists())

    def test_source_reads_are_bounded_even_if_file_grows_after_stat(self):
        from inspection_engine.report_learning import _bounded_source
        with patch('inspection_engine.report_learning.MAX_SOURCE_BYTES',10),self.assertRaises(DataError):
            _bounded_source(self.source)

    def test_pdf_warning_stream_is_discarded_not_buffered(self):
        from inspection_engine.report_learning import _pdf_pages
        with patch('inspection_engine.report_learning.subprocess.run',return_value=
            subprocess.CompletedProcess([],0,stdout=b'[]')) as run:
            _pdf_pages(self.source.read_bytes())
        self.assertIs(run.call_args.kwargs['stderr'],subprocess.DEVNULL)
        self.assertNotIn('capture_output',run.call_args.kwargs)

    def test_agent_claim_text_is_bounded_without_truncating(self):
        self.doc['observations'][0]['description']='x'*2001
        with self.assertRaises(DataError):self.comparison()

    def test_pdf_parser_receives_hashed_bytes_not_a_reopenable_source_path(self):
        p=self.root/'race.pdf';c=canvas.Canvas(str(p));c.drawString(50,700,'Original source text');c.showPage();c.save()
        original=p.read_bytes();self.source=p
        from inspection_engine.report_learning import _pdf_pages
        def read_and_swap(raw):
            self.assertEqual(raw,original)
            p.write_bytes(b'replaced while worker runs')
            pages=_pdf_pages(raw)
            self.assertIn('Original source text',pages[0]['text'])
            return pages
        with patch('inspection_engine.report_learning._pdf_pages',side_effect=read_and_swap),self.assertRaisesRegex(DataError,'changed'):
            self.imp()
