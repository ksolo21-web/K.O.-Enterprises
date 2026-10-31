"""Offline, no-network safety and provenance tests for the reference registry."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inspection_source_of_truth_under_test',ROOT/'inspection_engine/source_of_truth.py')
kb=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=kb
spec.loader.exec_module(kb)
DIGEST='3'*64
CASE={'media_id':'P0002','media_sha256':DIGEST,'source_verified':True}

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'knowledge/source_registry_v2.json').read_text())
    def clone_first(self): return copy.deepcopy(self.catalog)
    def test_catalog_has_full_scope(self):
        validated=kb.validate_catalog(self.catalog)
        covered=set().union(*(set(x['systems']) for x in validated['source_records']))
        self.assertEqual(covered,kb.KNOWN_SYSTEMS)
        self.assertGreaterEqual(len(validated['source_records']),12)
    def test_every_source_is_not_case_evidence(self):
        for s in self.catalog['source_records']:
            self.assertFalse(s['may_prove_field_condition'])
            self.assertFalse(s['may_prove_local_code_compliance'])
            self.assertFalse(s['may_automatically_approve_report'])
            self.assertIsNone(s['content_snapshot_sha256'])
    def test_duplicate_ids_refused(self):
        c=self.clone_first();c['source_records'].append(copy.deepcopy(c['source_records'][0]))
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_unknown_system_refused(self):
        c=self.clone_first();c['source_records'][0]['systems'].append('imaginary_component')
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_unapproved_host_refused(self):
        c=self.clone_first();c['source_records'][0]['url']='https://evil.example.org/source'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_official_domain_cannot_impersonate_another_publisher(self):
        c=self.clone_first();c['source_records'][0]['url']='https://www.cdc.gov/carbon-monoxide/about/'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_review_requires_version_bump(self):
        c=self.clone_first();c['source_records'][0]['last_reviewed']='2027-01-01'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
        c['registry_version']='2027-01-01.v2'
        kb.validate_catalog(c)
    def test_insecure_transport_refused(self):
        c=self.clone_first();c['source_records'][0]['url']=c['source_records'][0]['url'].replace('https://','http://')
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_prohibited_source_promotion_refused(self):
        c=self.clone_first();c['source_records'][0]['may_automatically_approve_report']=True
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_pending_ashi_cannot_be_marked_active(self):
        c=self.clone_first();n=next(s for s in c['source_records'] if s['id']=='ASHI_PENDING_2026')
        n['status']='active_reference'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_stated_review_cannot_be_immutable_snapshot(self):
        c=self.clone_first();c['source_records'][0]['review_method']='webpage_snapshot_archived'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_does_not_allow_fictional_future_review_date(self):
        c=self.clone_first();c['source_records'][0]['last_reviewed']='2028-01-01'
        with self.assertRaises(kb.KnowledgeError):kb.validate_catalog(c)
    def test_pending_standard_excluded_by_default(self):
        self.assertNotIn('ASHI_PENDING_2026',[r['id'] for r in kb.reference_sources(['foundation'])])
        self.assertIn('ASHI_PENDING_2026',[r['id'] for r in kb.reference_sources(['foundation'],include_pending=True)])
    def test_manufacturer_purposes_scope_to_system(self):
        source=kb.reference_sources(['water_heating'],purpose='manufacture_date_code')
        self.assertEqual({r['id'] for r in source},{'BRADFORD_WHITE_DATE','RHEEM_WATER_DATE'})
        self.assertEqual(kb.reference_sources(['electrical'],purpose='manufacture_date_code'),[])
    def test_bounded_prompt_does_not_include_pending_sop(self):
        brief=kb.build_reference_brief(['hvac','water_heating'],limit=4)
        self.assertLessEqual(len(brief.splitlines()),6)
        self.assertIn('ASHI_CURRENT_SOP',brief)
        self.assertNotIn('ASHI_PENDING_2026',brief)
        self.assertIn('NO LIVE SOURCE LOOKUP',brief)
        self.assertIn('never' if 'never' in brief else 'NEVER',brief)
    def test_reject_bad_limit_and_unknown_system(self):
        with self.assertRaises(kb.KnowledgeError):kb.build_reference_brief(['hvac'],0)
        with self.assertRaises(kb.KnowledgeError):kb.reference_sources(['invisible'])
    def test_guidance_is_complete_and_does_not_certify_houses(self):
        data=kb.load_guidance()
        self.assertEqual(set(data['systems']),kb.KNOWN_SYSTEMS)
        for rule in data['systems'].values():
            self.assertTrue(rule['no_automatic_diagnosis'])
            self.assertTrue(rule['requires_human_verification'])
    def test_system_brief_contains_specific_cues_and_uncertainty(self):
        s=kb.build_knowledge_brief(['foundation','subfloor'])
        self.assertIn('foundation_material',s)
        self.assertIn('subfloor_material',s)
        self.assertIn('Cannot establish visually',s)
        self.assertNotIn('ASHI_PENDING_2026',s)
    def test_guidance_digest_deterministic(self):
        self.assertEqual(kb.guidance_digest(),hashlib.sha256(kb.GUIDANCE.read_bytes()).hexdigest())
    def test_sha256_deterministic(self):
        self.assertEqual(kb.catalog_digest(),hashlib.sha256(kb.CATALOG.read_bytes()).hexdigest())

class ClaimTests(unittest.TestCase):
    def test_valid_observed_feature_stays_provisional(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'foundation','source_ids':['ASHI_CURRENT_SOP']},case_evidence=CASE)
        self.assertEqual(r['status'],'PROVISIONAL_HUMAN_REVIEW')
        self.assertFalse(r['customer_release_allowed']);self.assertFalse(r['verified_defect'])
    def test_missing_source_media_blocks(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'foundation','source_ids':['ASHI_CURRENT_SOP']})
        self.assertEqual(r['status'],'BLOCKED')
    def test_hash_missing_or_unverified_blocks(self):
        c=dict(CASE,media_sha256='not a digest');r=kb.assess_claim({'kind':'potential_concern','system':'foundation','source_ids':['INTERNACHI_RESIDENTIAL_SOP']},case_evidence=c)
        self.assertEqual(r['status'],'BLOCKED')
        c=dict(CASE,source_verified=False);r=kb.assess_claim({'kind':'observed_feature','system':'foundation','source_ids':['ASHI_CURRENT_SOP']},case_evidence=c)
        self.assertEqual(r['status'],'BLOCKED')
    def test_generic_guidance_not_sufficient_for_a_condition(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'foundation','source_ids':['EPA_MOISTURE']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_manufacturer_code_stays_unverified(self):
        r=kb.assess_claim({'kind':'manufacture_date_code','system':'water_heating','brand':'Bradford White','source_ids':['BRADFORD_WHITE_DATE']},case_evidence=CASE)
        self.assertEqual(r['status'],'CODE_ONLY_UNVERIFIED')
        self.assertFalse(r['customer_release_allowed'])
    def test_generic_warranty_page_cannot_verify_age(self):
        r=kb.assess_claim({'kind':'manufacture_date_code','system':'hvac','source_ids':['CARRIER_WARRANTY']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_installation_date_never_inferred(self):
        r=kb.assess_claim({'kind':'installation_date','system':'water_heating','source_ids':['BRADFORD_WHITE_DATE']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_remaining_life_not_guessed(self):
        r=kb.assess_claim({'kind':'remaining_service_life','system':'hvac','source_ids':['ASHI_CURRENT_SOP']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_code_compliance_cannot_be_inferred_from_doe(self):
        r=kb.assess_claim({'kind':'code_compliance','system':'roof','source_ids':['DOE_CODE_ADOPTION']},case_evidence=CASE,
                          jurisdiction_receipt={'jurisdiction':'Michigan'})
        self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['code_compliance_verified'])
    def test_recall_index_not_proof_specific_serial(self):
        r=kb.assess_claim({'kind':'recall_confirmed','system':'water_heating','source_ids':['CPSC_RECALL_API']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_unseen_risk_cannot_be_diagnosed_by_image(self):
        r=kb.assess_claim({'kind':'hazard_presence','system':'foundation','source_ids':['EPA_RADON']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_pending_standard_cannot_substitute_current(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'foundation','source_ids':['ASHI_PENDING_2026']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_cross_system_source_blocks(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'roof','source_ids':['BRADFORD_WHITE_DATE']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_unknown_source_id_blocks(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'roof','source_ids':['NONEXISTENT']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_wrong_brand_cannot_borrow_date_decoder(self):
        r=kb.assess_claim({'kind':'manufacture_date_code','system':'water_heating','brand':'Rheem','source_ids':['BRADFORD_WHITE_DATE']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_date_code_requires_brand(self):
        r=kb.assess_claim({'kind':'manufacture_date_code','system':'water_heating','source_ids':['RHEEM_WATER_DATE']},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_scope_limitation_cannot_use_mold_guide(self):
        r=kb.assess_claim({'kind':'scope_limitation','system':'crawlspace','source_ids':['EPA_MOISTURE']})
        self.assertEqual(r['status'],'BLOCKED')
    def test_specific_safety_referral_has_correct_reference(self):
        r=kb.assess_claim({'kind':'safety_referral','system':'hvac','source_ids':['CDC_CARBON_MONOXIDE']})
        self.assertEqual(r['status'],'PROVISIONAL_HUMAN_REVIEW')
        self.assertFalse(r['customer_release_allowed'])
    def test_sources_cannot_be_omitted(self):
        r=kb.assess_claim({'kind':'observed_feature','system':'roof','source_ids':[]},case_evidence=CASE)
        self.assertEqual(r['status'],'BLOCKED')

if __name__=='__main__':unittest.main()
