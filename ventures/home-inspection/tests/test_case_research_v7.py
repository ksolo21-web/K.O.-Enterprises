from __future__ import annotations
from copy import deepcopy
from datetime import date
import json
import unittest
from inspection_engine.case_research_v7 import (
 registry_load,registry_validate,case_research,metadata_receipt,compare_receipts,
 verify_case_provision,agent_brief_v7,KnowledgeBlocked)
from inspection_engine.field_validation_v7 import evaluation_summary,prepare_qualification_check,CohortBlocked
from scripts.knowledge_watch_v7 import audit

CASE={'state':'MI','building_type':'residential','county':'Wayne','municipality':'Westland',
      'municipality_type':'city','inspection_date':'2026-10-31'}
class CaseResearchV7Tests(unittest.TestCase):
 def test_official_sources_and_nothing_embedded(self):
  a=registry_load();self.assertEqual(a['licensed_full_text_embedded'],0)
  self.assertGreaterEqual(len(a['sources']),14)
  for s in a['sources']:self.assertNotEqual(s['embedding'],'full_text')
 def test_official_hosts_allowlist(self):
  a=deepcopy(registry_load());a['sources'][0]['url']='https://codes.iccsafe.org.evil.example';
  with self.assertRaises(KnowledgeBlocked):registry_validate(a)
 def test_fake_publisher_cannot_register(self):
  a=deepcopy(registry_load());a['sources'][0]['publisher']='Unofficial ICC';
  with self.assertRaises(KnowledgeBlocked):registry_validate(a)
 def test_userinfo_not_accepted(self):
  a=deepcopy(registry_load());a['sources'][0]['url']='https://hacker@codes.iccsafe.org/';
  with self.assertRaises(KnowledgeBlocked):registry_validate(a)
 def test_prohibited_full_text_flag(self):
  a=deepcopy(registry_load());a['sources'][0]['embedding']='full_text';
  with self.assertRaises(KnowledgeBlocked):registry_validate(a)
 def test_unverified_city_scope(self):
  a=case_research(CASE);self.assertTrue(a['locality']['indexed_official_city_sources'])
  self.assertEqual(len(a['enforcement']),4)
  self.assertTrue(all(x['authority_status']=='UNVERIFIED' for x in a['enforcement']))
  self.assertFalse(a['report_releasable'])
 def test_unknown_city_blocks_claims_but_still_researches(self):
  c=dict(CASE,municipality='Example Village',municipality_type='village')
  a=case_research(c);self.assertFalse(a['locality']['indexed_official_city_sources'])
 def test_commercial_scope(self):
  a=case_research(dict(CASE,building_type='commercial'))
  self.assertEqual(a['scope'],'commercial')
 def test_unknown_type_blocks(self):
  with self.assertRaises(KnowledgeBlocked):case_research(dict(CASE,building_type='warehouse'))
 def test_missing_municipality_class_blocks(self):
  c=dict(CASE);del c['municipality_type']
  with self.assertRaises(KnowledgeBlocked):case_research(c)
 def test_invalid_future_date_blocks(self):
  with self.assertRaises(KnowledgeBlocked):case_research(dict(CASE,inspection_date='2999-01-01'))
 def test_missing_ahj_and_report_release_false(self):
  a=case_research(CASE);self.assertFalse(a['code_compliance_verified'])
  self.assertFalse(a['all_hazards_found'])
 def test_snapshot_digest_only(self):
  d=metadata_receipt('ICC_DIGITAL_BASIC',b'a few bytes reviewed by operator','2026-10-31',reviewer_id='inspector_02',content_rights='read_only_verified_manually')
  self.assertEqual(len(d['sha256']),64)
  self.assertFalse(d['full_text_retained_in_public_repo'])
  self.assertNotIn('content',d)
 def test_no_assumed_machine_license(self):
  with self.assertRaises(KnowledgeBlocked):metadata_receipt('ICC_DIGITAL_BASIC',b'text','2026-10-31',reviewer_id='human_01',content_rights='licensed_machine_use_verified')
 def test_digest_change_escalates(self):
  a=metadata_receipt('MI_BCC_OPEN_RULES',b'one','2026-10-30',reviewer_id='reviewer_a',content_rights='public_government_record')
  b=metadata_receipt('MI_BCC_OPEN_RULES',b'two','2026-10-31',reviewer_id='reviewer_b',content_rights='public_government_record')
  c=compare_receipts(a,b);self.assertTrue(c['changed']);self.assertFalse(c['automatic_legal_update_applied'])
 def test_unchanged_does_not_certify_edition(self):
  a=metadata_receipt('MI_BCC_OPEN_RULES',b'one','2026-10-30',reviewer_id='reviewer_a',content_rights='public_government_record')
  b=metadata_receipt('MI_BCC_OPEN_RULES',b'one','2026-10-31',reviewer_id='reviewer_b',content_rights='public_government_record')
  self.assertIn('NOT_PROOF',compare_receipts(a,b)['review_status'])
 def test_source_switch_rejected(self):
  a=metadata_receipt('MI_BCC_OPEN_RULES',b'one','2026-10-30',reviewer_id='reviewer_a',content_rights='public_government_record')
  b=metadata_receipt('ICC_DIGITAL_BASIC',b'two','2026-10-31',reviewer_id='reviewer_b',content_rights='read_only_verified_manually')
  with self.assertRaises(KnowledgeBlocked):compare_receipts(a,b)
 def test_provision_rejects_codebook_index_as_legal_proof(self):
  with self.assertRaises(KnowledgeBlocked):verify_case_provision({'source_id':'ICC_DIGITAL_BASIC'},CASE)
 def test_provision_requires_original_hashed_evidence(self):
  c=dict(CASE,ahj_receipt_sha256='a'*64,verified_media_sha256=['b'*64])
  receipt=dict(source_id='MI_ADMIN_RULES',discipline='electrical',edition='2023',section='408.30801',
       ahj_name='human_tbd',jurisdiction_document_sha256='a'*64,evidence_sha256='c'*64,reviewer_id='human_1')
  with self.assertRaises(KnowledgeBlocked):verify_case_provision(receipt,c)
 def test_provision_receipt_does_not_certify_violation(self):
  c=dict(CASE,ahj_receipt_sha256='a'*64,verified_media_sha256=['b'*64])
  receipt=dict(source_id='MI_ADMIN_RULES',discipline='electrical',edition='2023',section='408.30801',
       ahj_name='human_tbd',jurisdiction_document_sha256='a'*64,evidence_sha256='b'*64,reviewer_id='human_1')
  result=verify_case_provision(receipt,c)
  self.assertFalse(result['authority_verified_by_software']);self.assertFalse(result['customer_release_allowed'])
 def test_agent_context_bounded_and_independent_of_copyright(self):
  s=agent_brief_v7(CASE,['electrical','plumbing']);self.assertLess(len(s),1800)
  self.assertIn('KNOWLEDGE_V7_REFERENCE_POLICY',s)
  self.assertIn('electrical',s);self.assertIn('human technical review',s)
 def test_agent_missing_case_fails_closed(self):
  s=agent_brief_v7(dict(CASE,municipality=''),['roof']);self.assertIn('BLOCKED_CASE_METADATA',s)
 def test_benchmark_no_cases_is_blocked(self):
  r=evaluation_summary([],[]);self.assertFalse(r['field_detection_accuracy_verified'])
 def test_benchmark_fake_protocol_is_blocked(self):
  r=evaluation_summary([],[],{'version':7});self.assertEqual(r['status'],'BLOCKED')
 def test_professional_check_requires_distinct_people(self):
  with self.assertRaises(CohortBlocked):prepare_qualification_check([{'case_id':'C1','qualified_labeler_id':'same','independent_adjudicator_id':'same'}])
 def test_credential_check_is_not_self_certified(self):
  r=prepare_qualification_check([{'case_id':'C1','scope':'residential','qualified_labeler_id':'a','independent_adjudicator_id':'b'}]);self.assertEqual(r[0]['labeler_qualification'],'EXTERNAL_VERIFICATION_REQUIRED')
 def test_audit_exposes_pending_true_counts(self):
  r=audit();self.assertEqual(r['status'],'REQUIRES_EXTERNAL_EVIDENCE');self.assertEqual(r['fully_verified_michigan_jurisdictions'],0)
  self.assertEqual(r['professionally_adjudicated_field_cases'],0);self.assertFalse(r['customer_release_allowed'])

if __name__=='__main__': unittest.main()

class IntegrationV7Tests(unittest.TestCase):
 def test_existing_agent_knowledge_packet_includes_v7_without_losing_v6(self):
  from inspection_engine.knowledge_registry import safe_agent_reference_brief
  c=dict(CASE)
  text=safe_agent_reference_brief(c,['electrical'])
  self.assertIn('KNOWLEDGE_V7_REFERENCE_POLICY',text)
  self.assertIn('GOVERNED_CASE_RESEARCH_V6',text)
  self.assertIn('GOVERNED_MICHIGAN_SOURCE_PACKET_JSON',text)
 def test_non_michigan_case_does_not_gain_michigan_law(self):
  from inspection_engine.knowledge_registry import safe_agent_reference_brief
  text=safe_agent_reference_brief(dict(CASE,state='OH'),['roof'])
  self.assertNotIn('KNOWLEDGE_V7_REFERENCE_POLICY',text)
 def test_code_index_does_not_authorize_provision(self):
  c=dict(CASE,ahj_receipt_sha256='a'*64,verified_media_sha256=['b'*64])
  r=dict(source_id='MI_BCC_CODES',discipline='building',edition='2015',section='R1.4',
    ahj_name='external_check_pending',jurisdiction_document_sha256='a'*64,
    evidence_sha256='b'*64,reviewer_id='human_1')
  with self.assertRaises(KnowledgeBlocked):verify_case_provision(r,c)
 def test_source_id_cannot_be_relabelled_to_another_official_publisher(self):
  x=deepcopy(registry_load());x['sources'][0]['publisher']='NFPA';x['sources'][0]['url']='https://www.nfpa.org/for-professionals/codes-and-standards'
  with self.assertRaises(KnowledgeBlocked):registry_validate(x)

class SourceAuthenticityV7Tests(unittest.TestCase):
 def test_false_path_on_legitimate_domain_rejected(self):
  x=deepcopy(registry_load());x['sources'][0]['url']='https://codes.iccsafe.org/unsupported-fake-research'
  with self.assertRaises(KnowledgeBlocked):registry_validate(x)
 def test_open_rules_not_enacted_provision(self):
  c=dict(CASE,ahj_receipt_sha256='a'*64,verified_media_sha256=['b'*64])
  receipt=dict(source_id='MI_BCC_OPEN_RULES',discipline='building',edition='2015',section='R408.1',
   ahj_name='placeholder',jurisdiction_document_sha256='a'*64,evidence_sha256='b'*64,reviewer_id='human_1')
  with self.assertRaises(KnowledgeBlocked):verify_case_provision(receipt,c)

class PublishedAHJLeadTests(unittest.TestCase):
 def test_three_wayne_city_pilots_share_published_local_levels(self):
  for municipality in ('Westland','Livonia','Detroit'):
   d=case_research(dict(CASE,municipality=municipality))['locality']
   self.assertEqual(d['state_published_directory_lead'],{k:'LOCAL' for k in ('building','electrical','mechanical','plumbing')})
   self.assertEqual(d['directory_revision'],'2026-09-28')
   self.assertTrue(d['live_enforcement_and_temporary_assistance_reconfirmation_required'])
 def test_directory_lead_cannot_be_relabelled_verified(self):
  a=deepcopy(registry_load());a['pilot_municipalities'][0]['directory_snapshot_verified']=True
  with self.assertRaises(KnowledgeBlocked):registry_validate(a)
 def test_unknown_location_has_no_guessed_directory_level(self):
  d=case_research(dict(CASE,municipality='Not A City'))['locality']
  self.assertIsNone(d['state_published_directory_lead'])
