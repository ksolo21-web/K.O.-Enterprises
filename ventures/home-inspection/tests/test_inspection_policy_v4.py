"""Policy and report triage are controls; these do not prove defect detection."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from inspection_engine.descriptors import REQUIRED_FEATURES
from inspection_engine.source_of_truth import KnowledgeError
from inspection_engine.inspection_policy import (
    load_policy, validate_policy, policy_digest, active_sop_context,
    build_inspection_knowledge_brief)
from inspection_engine.inspection_triage import case_review_queue
from inspection_engine.agents import execute_specialists

class PolicyTests(unittest.TestCase):
    def setUp(self):self.policy=load_policy()
    def test_all_13_systems(self):self.assertEqual({x['system'] for x in self.policy['systems']},set(REQUIRED_FEATURES))
    def test_all_46_feature_codes(self):self.assertEqual(sum(len(x['feature_codes']) for x in self.policy['systems']),46)
    def test_embedded_reference_digest(self):self.assertEqual(len(policy_digest()),64)
    def test_defensive_copy(self):
        self.policy['systems'][0]['inspection_focus']='HACK';self.assertNotEqual(load_policy()['systems'][0]['inspection_focus'],'HACK')
    def test_reject_fake_source_url(self):
        p=copy.deepcopy(self.policy);p['sources'][0]['url']='https://nachi.org.evil.test/sop.htm'
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_reject_wrong_publisher(self):
        p=copy.deepcopy(self.policy);p['sources'][0]['publisher']='ASTM International'
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_reject_full_unlicensed_text_claim(self):
        p=copy.deepcopy(self.policy);p['sources'][0]['embedded_full_text']=True
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_reject_defect_free_policy(self):
        p=copy.deepcopy(self.policy);p['all_conditions_detected_guarantee']=True
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_reject_missing_system(self):
        p=copy.deepcopy(self.policy);p['systems'].pop()
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_reject_renamed_feature(self):
        p=copy.deepcopy(self.policy);p['systems'][0]['feature_codes'][0]='fictional'
        with self.assertRaises(KnowledgeError):validate_policy(p)
    def test_no_2027_ashi_premature(self):
        with self.assertRaises(KnowledgeError):active_sop_context('residential','2026-10-31','ASHI_SOP_2027')
    def test_2027_explicit_contract(self):
        self.assertEqual(active_sop_context('residential','2027-01-01','ASHI_SOP_2027')['standard'],'ASHI_SOP_2027')
    def test_unselected_sop_never_assumed(self):
        c=active_sop_context('residential');self.assertEqual(c['standard'],'UNSELECTED');self.assertFalse(c['standard_compliance_certified'])
    def test_old_ashi_current_rejected_after_transition(self):
        with self.assertRaises(KnowledgeError):active_sop_context('residential','2027-01-01','ASHI_SOP_CURRENT')
    def test_residential_not_commercial(self):
        with self.assertRaises(KnowledgeError):active_sop_context('residential',contracted_sop='ASTM_E2018_24')
    def test_commercial_not_residential(self):
        with self.assertRaises(KnowledgeError):active_sop_context('commercial',contracted_sop='INT_NACHI_SOP')
    def test_policy_packet_has_urgent_and_limits(self):
        s=build_inspection_knowledge_brief(['electrical','foundation'],property_kind='residential')
        self.assertIn('serious_warning_cue',s);self.assertIn('POLICY_DIGEST_SHA256',s)
        self.assertIn('InterNACHI',s);self.assertIn('never',s.lower())
    def test_policy_packet_missing_fireplace_scope(self):
        self.assertIn('Fireplace/hearth',build_inspection_knowledge_brief(['roof']))
    def test_commercial_packet_has_contract_separation(self):
        s=build_inspection_knowledge_brief(['hvac'],property_kind='commercial')
        self.assertIn('ASTM E2018-24',s);self.assertIn('standards',s.lower())
    def test_invalid_domain_rejected(self):
        with self.assertRaises(KnowledgeError):build_inspection_knowledge_brief(['fictional'])

class CaseTriageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        Image.new('RGB',(128,128),'white').save(self.root/'source.png')
        self.case={'case_id':'CASE-SYNTH-1','state':'MI','county':'Oakland','municipality':'Auburn Hills',
                   'building_type':'residential_one_two_family','inspection_date':'2026-10-31',
                   'work_type':'visual_inspection','media':[{'id':'P1','path':'source.png',
                     'sha256':hashlib.sha256((self.root/'source.png').read_bytes()).hexdigest()}]}
        self.finding={'finding_id':'F1','claim_type':'potential_defect','system':'foundation',
            'feature_code':'visible_foundation_condition','observed_symptom':'Visible line on foundation wall in synthetic image.',
            'evidence_ids':['P1'],'risk_priority':'major','possible_significance':'May warrant further structural evaluation if movement is suspected.',
            'recommended_next_step':'Have qualified inspector assess and consider licensed structural engineer.',
            'location':'Basement east wall','material_limitations':'Concealed foundation not inspected',
            'source_ids':['INT_NACHI_SOP'],
            'cause_assessment':{'status':'unknown','hypotheses':[]}}
    def do(self, findings=None, case=None):
        return case_review_queue(case or self.case,findings if findings is not None else [self.finding],self.root,inspection_scope='residential')
    def test_serious_issue_kept_for_review(self):
        r=self.do();self.assertEqual(len(r['mandatory_human_review_queue']),1)
        self.assertEqual(r['mandatory_human_review_queue'][0]['urgency'],'PROMPT_HUMAN_TRIAGE')
        self.assertFalse(r['customer_release_allowed']);self.assertFalse(r['qualified_inspector_approval_authenticated'])
    def test_internal_notes_not_exposed_in_draft(self):
        r=self.do();d=r['client_report_candidates_for_inspector_only'][0]
        self.assertIn('observed_condition',d);self.assertIn('why_it_matters',d);self.assertIn('recommended_follow_up',d)
        self.assertNotIn('cause_hypotheses',d);self.assertNotIn('reference_ids',d)
        self.assertFalse(d['publishable'])
    def test_tampered_evidence_keeps_urgent_queue_no_draft(self):
        (self.root/'source.png').write_bytes(b'tamper')
        r=self.do();self.assertEqual(len(r['mandatory_human_review_queue']),1)
        self.assertEqual(r['client_report_candidates_for_inspector_only'],[])
    def test_unknown_evidence_does_not_make_report_draft(self):
        f=copy.deepcopy(self.finding);f['evidence_ids']=['FAKE']
        r=self.do([f]);self.assertFalse(r['client_report_candidates_for_inspector_only'])
    def test_unknown_source_id_rejected(self):
        f=copy.deepcopy(self.finding);f['source_ids']=['FAKE_OFFICIAL_REF']
        with self.assertRaises(KnowledgeError):self.do([f])
    def test_duplicate_source_id_rejected(self):
        f=copy.deepcopy(self.finding);f['source_ids']=['INT_NACHI_SOP','INT_NACHI_SOP']
        with self.assertRaises(KnowledgeError):self.do([f])
    def test_code_claim_not_reported(self):
        f=copy.deepcopy(self.finding);f['claim_type']='code_violation';f['code_discipline']='building'
        r=self.do([f]);self.assertFalse(r['client_report_candidates_for_inspector_only'])
    def test_recall_claim_not_reported(self):
        f=copy.deepcopy(self.finding);f['claim_type']='recall_applicability'
        r=self.do([f]);self.assertFalse(r['client_report_candidates_for_inspector_only'])
    def test_minor_issue_internal_not_customer_report(self):
        f=copy.deepcopy(self.finding);f['risk_priority']='maintenance'
        r=self.do([f]);self.assertFalse(r['client_report_candidates_for_inspector_only']);self.assertEqual(len(r['internal_reasoning_ledger']),1)
    def test_no_findings_never_means_no_defects(self):
        r=self.do([]);self.assertEqual(r['system_coverage_gaps']['documented_feature_count'],0)
        self.assertFalse(r['comprehensive_visual_coverage_verified'])
    def test_one_finding_not_complete_coverage(self):
        r=self.do();self.assertEqual(r['system_coverage_gaps']['documented_feature_count'],1)
        self.assertEqual(r['system_coverage_gaps']['required_feature_count'],46)
    def test_duplicate_finding_ids_rejected(self):
        with self.assertRaises(KnowledgeError):self.do([self.finding,self.finding])
    def test_invented_feature_code_rejected(self):
        f=copy.deepcopy(self.finding);f['feature_code']='made_up'
        with self.assertRaises(KnowledgeError):self.do([f])
    def test_guaranteed_safe_assurance_rejected(self):
        f=copy.deepcopy(self.finding);f['possible_significance']='The system is guaranteed safe'
        with self.assertRaises(KnowledgeError):self.do([f])
    def test_critical_priority_preserved_without_cause(self):
        f=copy.deepcopy(self.finding);f['risk_priority']='immediate_safety'
        r=self.do([f]);self.assertEqual(r['mandatory_human_review_queue'][0]['unverified_priority'],'immediate_safety')
    def test_commercial_scope_needs_distinct_process(self):
        c=copy.deepcopy(self.case);c['building_type']='commercial_general'
        r=case_review_queue(c,[],self.root,inspection_scope='commercial')
        self.assertEqual(r['scope']['standard'],'UNSELECTED')
    def test_rejection_of_commercial_sop_on_home(self):
        with self.assertRaises(KnowledgeError):case_review_queue(self.case,[],self.root,inspection_scope='residential',contracted_sop='ASTM_E2018_24')
    def test_commercial_scope_not_assigned_to_house(self):
        with self.assertRaises(KnowledgeError):case_review_queue(self.case,[],self.root,inspection_scope='commercial')
    def test_unknown_priority_does_not_vanish_from_review(self):
        f=copy.deepcopy(self.finding);f['risk_priority']='unknown'
        r=self.do([f])
        self.assertEqual(len(r['mandatory_human_review_queue']),1)
        self.assertFalse(r['client_report_candidates_for_inspector_only'])
    def test_no_confirmed_code_or_release(self):
        r=self.do();self.assertFalse(r['internal_reasoning_ledger'][0]['customer_release_allowed'])
        self.assertNotIn('code_violation_verified',r['client_report_candidates_for_inspector_only'][0])

if __name__=='__main__':unittest.main()
