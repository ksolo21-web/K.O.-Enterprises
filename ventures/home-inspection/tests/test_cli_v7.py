import io
import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
import unittest
from scripts.knowledge_watch_v7 import main

class CLITests(unittest.TestCase):
 def exec(self,args):
  out=io.StringIO()
  with redirect_stdout(out): code=main(args)
  return code,json.loads(out.getvalue())
 def test_audit_fails_business_completion_gate(self):
  code,r=self.exec(['audit']);self.assertEqual(code,2)
  self.assertEqual(r['status'],'REQUIRES_EXTERNAL_EVIDENCE')
 def test_missing_case_raises_blocker(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.json';p.write_text('{}')
   code,r=self.exec(['case','--input',str(p)])
   self.assertEqual(code,2);self.assertEqual(r['status'],'BLOCKED')
 def test_michigan_case_returns_four_authority_checks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.json';p.write_text(json.dumps(dict(state='MI',building_type='residential',county='Wayne',municipality='Westland',municipality_type='city',inspection_date='2026-10-31')))
   code,r=self.exec(['case','--input',str(p)])
   self.assertEqual(code,0);self.assertEqual(len(r['enforcement']),4)
   self.assertFalse(r['code_compliance_verified'])
 def test_manual_exact_listing_not_installation_verification(self):
  code,r=self.exec(['manual-index','--brand','A. O. Smith','--model','ATHR-160M 100'])
  self.assertEqual(code,0);self.assertEqual(r['status'],'OFFICIAL_MODEL_LISTING_FOUND_MANUAL_NOT_VERIFIED')
  self.assertFalse(r['manual_file_verified'])
 def test_manual_missing_model_stays_open(self):
  code,r=self.exec(['manual-index','--brand','A. O. Smith','--model','UNKNOWN'])
  self.assertEqual(code,0);self.assertFalse(r['serial_or_revision_confirmed'])
 def test_ahj_import_cli_no_real_coverage_claim(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'rows.csv';p.write_text('county,municipality,municipality_type,building,building_effective_date,electrical,electrical_effective_date,mechanical,mechanical_effective_date,plumbing,plumbing_effective_date,temporary_assistance_notes\nWayne,Demo,city,LOCAL,,STATE,2000-01-01,STATE,,COUNTY,,\n')
   code,r=self.exec(['ahj-import','--csv',str(p),'--source-sha256','a'*64,'--revision','2026-09-28','--operator-id','case_reviewer'])
   self.assertEqual(code,0);self.assertFalse(r['complete_michigan_coverage_verified'])
 def test_benchmark_no_real_cases_not_claimed(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'cases.json';b=Path(d)/'predictions.json'
   a.write_text('[]');b.write_text('[]')
   code,r=self.exec(['benchmark','--cases',str(a),'--predictions',str(b)])
   self.assertEqual(code,2);self.assertFalse(r['field_detection_accuracy_verified'])

if __name__=='__main__':unittest.main()
