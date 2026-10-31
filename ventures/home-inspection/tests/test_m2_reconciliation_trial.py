"""Synthetic controlled end-to-end evidence. No live inference or field accuracy."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pypdf import PdfReader
from inspection_engine.adjudication import ollama_reasoner,validate_record
from inspection_engine.core import DataError,load_project,sha256
from scripts.run_m2_reconciliation_trial import run_reconciliation_trial,_preflight


class M2ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'trial'
    def writer(self,image,prompt):
        if 'evidence ID P0001' in prompt and 'region [0, 0, 1, 1]' in prompt:
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.15,.15,.55,.60]}]}
        if 'evidence ID V0001-F01' in prompt and 'region [0, 0, 1, 1]' in prompt:
            return {'candidates':[],'requests':[{'kind':'video_still','timestamp_seconds':2.5}]}
        return {'candidates':[{'type':'feature','system':'exterior','feature_code':'cladding_type',
            'status':'partially_observed','description':'Visible synthetic exterior wall illustration',
            'location':'Front','bbox':[.1,.1,.4,.4]}],'requests':[]}
    def reviewer(self,image,prompt):
        return {'decision':'insufficient_evidence','reason':'Synthetic illustration only',
            'missing_evidence':'Qualified inspector view and physical follow-up'}
    def reasoner(self,prompt,schema):
        packet=json.loads(prompt.split('LEDGER_PACKET_JSON: ')[1])
        return {'decisions':[{'entry_id':e['entry_id'],'decision':'distinct','related_ids':[],
            'reason':'Controlled reconciliation only','evidence_gap':''} for e in packet['queue']['entries']]}
    def run_controlled(self,**opts):
        return run_reconciliation_trial(self.root,'writer:fixture','reviewer:fixture','reasoner:fixture',
            writer=self.writer,reviewer=self.reviewer,reasoner=self.reasoner,**opts)
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required for real native video decoding')
    def test_full_chain_saves_tool_Q02_Q03_and_held_PDF_evidence(self):
        r=self.run_controlled();self.assertEqual(r['status'],'SYNTHETIC_RECONCILIATION_COMPLETE_UNVERIFIED',r)
        self.assertTrue(r['tool_lineage_verified']);self.assertTrue(r['q03_provider_invoked']);self.assertFalse(r['q03_live_call_completed'])
        self.assertEqual(r['q03_status'],'ADJUDICATION_HOLD');self.assertGreaterEqual(len(r['held_entry_ids']),15)
        self.assertFalse(r['field_accuracy_verified']);self.assertFalse(r['full_milestone_2_approved']);self.assertFalse(r['customer_release_allowed'])
        document=load_project(self.root/'adjudicated_project.json');validate_record(document,document['adjudication'])
        pdf=PdfReader(self.root/'held_report.pdf');self.assertGreater(len(pdf.pages),1)
        text='\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertIn('NOT RELEASED',text);self.assertIn('NOT A FIELD INSPECTION',text)
        self.assertIn('NOT FOR CLIENT RELEASE',r['report_status'])
        manifest=json.loads((self.root/'reconciliation_manifest.json').read_text())
        for name,value in manifest['files'].items():self.assertEqual(sha256(self.root/name),value)
        self.assertIn('q03_response.json',manifest['files']);self.assertIn('held_report.pdf',manifest['files'])
    def test_no_tool_output_remains_gap_even_with_Q03_and_PDF(self):
        r=run_reconciliation_trial(self.root,'w','r','q',writer=lambda i,p:{'candidates':[],'requests':[]},
            reviewer=self.reviewer,reasoner=self.reasoner,with_video=False)
        self.assertEqual(r['status'],'SYNTHETIC_RECONCILIATION_WITH_GAPS',r)
        self.assertTrue(r['workflow_contract_completed']);self.assertFalse(r['tool_lineage_verified'])
    def test_bad_writer_blocks_before_Q03_but_keeps_base_record(self):
        r=run_reconciliation_trial(self.root,'w','r','q',writer=lambda i,p:{'candidates':[],'requests':[{'kind':'zoom','bbox':[0,0,1,1]}]},
            reviewer=self.reviewer,reasoner=self.reasoner,with_video=False)
        self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['q03_provider_invoked'])
        self.assertTrue((self.root/'trial_status.json').exists())
    def test_Q03_omission_rejected_and_actual_reply_retained(self):
        r=run_reconciliation_trial(self.root,'w','r','q',writer=lambda i,p:{'candidates':[],'requests':[]},
            reviewer=self.reviewer,reasoner=lambda p,s:{'decisions':[]},with_video=False)
        self.assertEqual(r['status'],'BLOCKED');self.assertTrue(r['q03_provider_invoked'])
        self.assertFalse((self.root/'held_report.pdf').exists())
        self.assertEqual(json.loads((self.root/'q03_response.json').read_text())['structured_response_untrusted'],{'decisions':[]})
    def test_live_optin_and_mixed_providers_rejected_before_calls(self):
        with patch('scripts.run_m2_reconciliation_trial._preflight') as pf:
            with self.assertRaises(DataError):run_reconciliation_trial(self.root,'w','r','q')
            pf.assert_not_called()
        with self.assertRaises(DataError):run_reconciliation_trial(self.root,'w','r','q',writer=self.writer)
        self.assertFalse(self.root.exists())
    def test_provider_alias_and_existing_output_refused(self):
        with self.assertRaises(DataError):run_reconciliation_trial(self.root,'w','w','q')
        self.root.mkdir()
        with self.assertRaises(DataError):self.run_controlled(with_video=False)
    def test_preflight_three_digests_and_completion_required(self):
        def metadata(method,path,body=None):
            if path=='/api/tags':return {'models':[{'name':n,'digest':str(i)*64} for i,n in enumerate(['w','r','q'],1)]}
            return {'capabilities':['completion']}
        with patch('scripts.run_m2_reconciliation_trial.preflight_models'),patch('scripts.run_m2_reconciliation_trial.local_json',side_effect=metadata):
            self.assertEqual(len(_preflight('w','r','q')),3)
        def aliased(method,path,body=None):
            if path=='/api/tags':return {'models':[{'name':n,'digest':'a'*64} for n in ['w','r','q']]}
            return {'capabilities':['completion']}
        with patch('scripts.run_m2_reconciliation_trial.preflight_models'),patch('scripts.run_m2_reconciliation_trial.local_json',side_effect=aliased),self.assertRaises(DataError):_preflight('w','r','q')
        def wrong_cap(method,path,body=None):
            return metadata(method,path,body) if path=='/api/tags' else {'capabilities':['vision']}
        with patch('scripts.run_m2_reconciliation_trial.preflight_models'),patch('scripts.run_m2_reconciliation_trial.local_json',side_effect=wrong_cap),self.assertRaises(DataError):_preflight('w','r','q')
    def test_reasoner_transport_audit_excludes_thinking_and_records_incomplete(self):
        envelope={'done':False,'done_reason':'load','response':'test-only','thinking':'PRIVATE-INTERNAL','context':[1,2]};seen=[]
        with patch('inspection_engine.local_runtime.local_json',return_value=envelope),self.assertRaises(DataError):
            ollama_reasoner('p',{},'q',response_audit=seen.append)
        self.assertEqual(seen[0]['response'],'test-only');self.assertNotIn('thinking',seen[0]);self.assertNotIn('context',seen[0])
