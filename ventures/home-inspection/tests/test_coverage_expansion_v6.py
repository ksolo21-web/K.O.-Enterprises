import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from inspection_engine.coverage_expansion import (
 load_expansion,validate_expansion,plan_municipal_verification,
 validate_local_snapshot,compare_snapshots,manufacturer_lookup,
 verify_model_manual_receipt,specialty_work_orders,case_knowledge_packet,
 ReferenceBlock)
from inspection_engine.knowledge_registry import safe_agent_reference_brief

H='a'*64

def case(city='Westland',county='Wayne',kind='residential'):
 return {'state':'MI','county':county,'municipality':city,'municipality_type':'city',
         'building_type':kind,'inspection_date':'2026-10-31'}

class MunicipalityTests(unittest.TestCase):
 def test_catalogs_valid(self):
  for kind in ('municipal','manufacturers','specialties'):
   self.assertTrue(validate_expansion(kind,load_expansion(kind)))
 def test_list_not_case_certification(self):
  a=plan_municipal_verification(case());self.assertTrue(a['jurisdiction_indexed']);self.assertEqual(len(a['ahj_by_discipline']),4)
  self.assertFalse(a['all_municipal_amendments_verified']);self.assertFalse(a['code_violations_confirmed'])
 def test_wayne_pilot_three(self):
  for city in ('Westland','Livonia','Detroit'):self.assertTrue(plan_municipal_verification(case(city))['jurisdiction_indexed'])
 def test_unknown_municipality_needs_state_list(self):
  a=plan_municipal_verification(case('Canton','Wayne'));self.assertFalse(a['jurisdiction_indexed']);self.assertEqual(a['municipality_source_id'],None)
 def test_detroit_old_edition_warning(self):
  a=plan_municipal_verification(case('Detroit'));self.assertTrue(a['edition_conflict_flag']);self.assertIn('conflicting_publications',[x['discipline'] for x in a['verification_tickets']])
 def test_case_does_not_guess_township_as_city(self):
  c=case();c['municipality_type']='township';self.assertFalse(plan_municipal_verification(c)['jurisdiction_indexed'])
 def test_incomplete_case_refused(self):
  c=case();del c['municipality_type']
  with self.assertRaises(ReferenceBlock):plan_municipal_verification(c)
 def test_nonmi_refused(self):
  c=case();c['state']='OH'
  with self.assertRaises(ReferenceBlock):plan_municipal_verification(c)
 def test_future_review_date_refused(self):
  d=load_expansion('municipal');d['reviewed_on']='2099-01-01'
  with self.assertRaises(ReferenceBlock):validate_expansion('municipal',d)
 def test_fake_municipal_identity_and_matching_fake_domain_refused(self):
  d=load_expansion('municipal');d['locations'][0]['publisher_host']='www.municipality-fraud.net';d['locations'][0]['source_url']='https://www.municipality-fraud.net/fake';d['locations'][0]['additional_url']='https://www.municipality-fraud.net/also'
  with self.assertRaises(ReferenceBlock):validate_expansion('municipal',d)
 def test_fake_manufacturer_matching_fake_domain_refused(self):
  d=load_expansion('manufacturers');d['portals'][0]['host']='www.fake-smith.net';d['portals'][0]['url']='https://www.fake-smith.net/official'
  with self.assertRaises(ReferenceBlock):validate_expansion('manufacturers',d)
 def test_malicious_official_host_refused(self):
  d=load_expansion('municipal');d['locations'][0]['source_url']='https://www.cityofwestland.com.evil.net/foo'
  with self.assertRaises(ReferenceBlock):validate_expansion('municipal',d)
 def test_false_claim_amendments_indexed_refused(self):
  d=load_expansion('municipal');d['locations'][0]['verified_local_amendments']=True
  with self.assertRaises(ReferenceBlock):validate_expansion('municipal',d)
 def test_duplicate_cities_refused(self):
  d=load_expansion('municipal');d['locations'].append(copy.deepcopy(d['locations'][0]))
  with self.assertRaises(ReferenceBlock):validate_expansion('municipal',d)
 def test_municipal_snapshot_has_real_file_bytes(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);file=root/'municipal.html';file.write_bytes(b'<html>Recorded human-source snapshot</html>')
   url='https://www.cityofwestland.com/194/Building-Division'
   record={'source_url':url,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
           'retrieved_on':'2026-10-31','reviewer_id':'qualified-source-reviewer'}
   a=validate_local_snapshot(file,root,record,source_url=url)
   self.assertFalse(a['authenticated_government_copy']);self.assertTrue(a['human_AHJ_confirmation_required'])
   file.write_bytes(b'Source was edited after capture!')
   with self.assertRaises(ReferenceBlock):validate_local_snapshot(file,root,record,source_url=url)
 def test_snapshot_outside_root_blocked(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   file=Path(b)/'test.html';file.write_bytes(b'Hello '*30)
   with self.assertRaises(ReferenceBlock):validate_local_snapshot(file,Path(a),{},source_url='https://www.cityofwestland.com')
 def test_diff_never_auto_updates(self):
  url='https://www.cityofwestland.com/194/Building-Division'
  old={'source_url':url,'sha256':'a'*64,'retrieved_on':'2026-10-25'}
  new={'source_url':url,'sha256':'b'*64,'retrieved_on':'2026-10-31'}
  a=compare_snapshots(old,new);self.assertTrue(a['content_changed']);self.assertFalse(a['code_applicability_reverified']);self.assertTrue(a['disallow_automatic_code_update'])
 def test_diff_mismatch_url_rejected(self):
  with self.assertRaises(ReferenceBlock):compare_snapshots({'source_url':'https://foo','sha256':H,'retrieved_on':'2026-10-25'}, {'source_url':'https://bar','sha256':H,'retrieved_on':'2026-10-31'})

class ManufacturerTests(unittest.TestCase):
 def test_manufacturers_official(self):
  for brand,system in [('A. O. Smith','water_heating'),('Goodman','hvac'),('Carrier','hvac'),('Rheem','water_heating')]:
   x=manufacturer_lookup(brand,'A123-45',system);self.assertIn('https://',x['official_portal_url']);self.assertFalse(x['manual_file_verified'])
 def test_mismatched_system_refused(self):
  with self.assertRaises(ReferenceBlock):manufacturer_lookup('Carrier','ABC123','water_heating')
 def test_brand_mismatch_refused(self):
  with self.assertRaises(ReferenceBlock):manufacturer_lookup('Unlisted Brand','ABC123','hvac')
 def test_unsafe_model_refused(self):
  with self.assertRaises(ReferenceBlock):manufacturer_lookup('Carrier','../../bad','hvac')
 def test_proof_with_real_matching_bytes_still_not_qualified(self):
  lookup=manufacturer_lookup('Carrier','A123-45','hvac')
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);file=root/'manual.pdf';file.write_bytes(b'Synthetic placeholder manual reference - not a manufacturer document'*3)
   receipt={'brand':'Carrier','model':'A123-45','rating_plate_image_sha256':H,'portal_url':lookup['official_portal_url'],
            'revision':'revision-test','reviewer_id':'expert','reviewed_on':'2026-10-31',
            'manual_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'machine_full_text_ingest_authorized':False}
   a=verify_model_manual_receipt(root,file,receipt,lookup=lookup)
   self.assertEqual(a['status'],'EXACT_MODEL_DOCUMENT_MATCH_PENDING_QUALIFIED_REVIEW')
   self.assertFalse(a['manufacturer_guidance_verified_for_installed_revision']);self.assertFalse(a['manual_full_text_embedded'])
   receipt['model']='ANOTHER'
   with self.assertRaises(ReferenceBlock):verify_model_manual_receipt(root,file,receipt,lookup=lookup)
 def test_manufacturer_license_never_inferred(self):
  lookup=manufacturer_lookup('Carrier','ABC123','hvac')
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);p=root/'a.pdf';p.write_bytes(b'A'*100)
   r={'brand':'Carrier','model':'ABC123','rating_plate_image_sha256':H,'portal_url':lookup['official_portal_url'],
      'revision':'r1','reviewer_id':'expert','reviewed_on':'2026-10-31',
      'manual_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'machine_full_text_ingest_authorized':True}
   with self.assertRaises(ReferenceBlock):verify_model_manual_receipt(root,p,r,lookup=lookup)

class SpecialistTests(unittest.TestCase):
 def test_fireplace_and_garage_supplements(self):
  s=specialty_work_orders('residential');names=[x['id'] for x in s['tasks']]
  self.assertIn('FIREPLACE_HEARTH',names);self.assertIn('GARAGE_DOOR',names);self.assertFalse(s['SOP_compliance_certified'])
 def test_commercial_specialty_separate(self):
  tasks=specialty_work_orders('commercial')['tasks'];self.assertEqual([x['id'] for x in tasks],['COMMERCIAL_FIRE_LIFE_SAFETY'])
 def test_claimed_coverage_not_evidence(self):
  x=specialty_work_orders('residential',['GARAGE_DOOR']);row=next(r for r in x['tasks'] if r['id']=='GARAGE_DOOR')
  self.assertEqual(row['review_status'],'CLAIMED_COVERAGE_REQUIRES_EVIDENCE')
 def test_alternative_causes_survive(self):
  x=specialty_work_orders('residential')['tasks'][0]
  self.assertTrue(x['possible_mechanisms_not_diagnoses']);self.assertTrue(x['alternative_causes']);self.assertTrue(x['cannot_prove_from_photos'])
 def test_case_packet_includes_municipality_pilot(self):
  s=case_knowledge_packet(case(),'interior');self.assertIn('GOVERNED_CASE_RESEARCH_V6_JSON',s);self.assertIn('FIREPLACE_HEARTH',s);self.assertIn('STAIR_FALL_GUARDING',s)
 def test_existing_knowledge_agent_packet_still_presents_no_verdict(self):
  x=safe_agent_reference_brief({'state':'MI','county':'Wayne','municipality':'Detroit','municipality_type':'city',
          'building_type':'residential_one_two_family','inspection_date':'2026-10-31'},['roof'])
  self.assertIn('GOVERNED_MICHIGAN_SOURCE_PACKET_JSON',x)
  self.assertIn('GOVERNED_CASE_RESEARCH_V6_JSON',x)
  self.assertIn('edition_conflict_flag',x)
 def test_missing_municipality_type_not_assumed(self):
  x=safe_agent_reference_brief({'state':'MI','county':'Wayne','municipality':'Detroit',
          'building_type':'residential','inspection_date':'2026-10-31'},['roof'])
  self.assertIn('MISSING_MUNICIPALITY_TYPE',x)
  self.assertNotIn('GOVERNED_CASE_RESEARCH_V6_JSON',x)

if __name__=='__main__':unittest.main()
