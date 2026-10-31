import json,tempfile,unittest
from pathlib import Path
from scripts.knowledge_expansion_v6 import audit,main
class OfflineExpansionAudit(unittest.TestCase):
 def test_audit_has_counts_and_blocked_status(self):
  a=audit();self.assertEqual(a['indexed_pilot_municipalities'],3);self.assertEqual(a['manufacturer_official_portals'],4)
  self.assertEqual(a['hazard_systems_indexed'],13);self.assertEqual(a['supplemental_specialties_indexed'],3)
  self.assertEqual(a['manufacturer_manual_titles_indexed'],2);self.assertEqual(a['manufacturer_model_listings_indexed'],18)
  self.assertFalse(a['customer_release_allowed'])
 def test_audit_declares_zero_licensed_full_text(self):
  a=audit();self.assertEqual(a['licensed_full_copyrighted_text_ingested'],0);self.assertEqual(a['exact_model_manuals_verified'],0)
 def test_case_plan_fails_without_location_type(self):
  c={'state':'MI','county':'Wayne','municipality':'Detroit','building_type':'residential','inspection_date':'2026-10-31'}
  from inspection_engine.coverage_expansion import ReferenceBlock
  with self.assertRaises(ReferenceBlock):audit(c)
 def test_valid_case_produces_no_code_verdict(self):
  c={'state':'MI','county':'Wayne','municipality':'Detroit','municipality_type':'city','building_type':'residential','inspection_date':'2026-10-31'}
  a=audit(c);self.assertTrue(a['case_plan']['edition_conflict_flag']);self.assertFalse(a['case_plan']['code_violations_confirmed'])
 def test_cli_does_not_overwrite_audit(self):
  with tempfile.TemporaryDirectory() as t:
   file=Path(t)/'audit.json'
   self.assertEqual(main(['--out',str(file)]),2)
   self.assertTrue(file.exists());previous=file.read_bytes()
   self.assertEqual(main(['--out',str(file)]),2)
   self.assertEqual(file.read_bytes(),previous)
 def test_no_embedded_personal_cases(self):
  s=json.dumps(audit());self.assertNotIn('customer_image',s)
if __name__=='__main__':unittest.main()
