import unittest
import tempfile
import hashlib
from pathlib import Path
from PIL import Image
from scripts.case_knowledge_audit import audit_case
class AuditCaseTests(unittest.TestCase):
    def test_audit_is_never_release_authority_and_lists_missing_features(self):
        with tempfile.TemporaryDirectory() as temp:
            r=Path(temp);Image.new('RGB',(64,64),'white').save(r/'synthetic.png')
            c={'case_id':'MI-DEMO','state':'MI','county':'Oakland','municipality':'Auburn Hills',
               'building_type':'residential_one_two_family','work_type':'visual_inspection','inspection_date':'2026-10-31',
               'media':[{'id':'P1','path':'synthetic.png','sha256':hashlib.sha256((r/'synthetic.png').read_bytes()).hexdigest()}]}
            f={'claim_type':'visual_observation','system':'roof','feature_code':'roof_covering',
               'observed_symptom':'Visible synthetic roof surface with no actual dwelling condition established.',
               'evidence_ids':['P1'],'cause_assessment':{'status':'unknown','hypotheses':[]},
               'qualified_review_receipt':{'decision':'approve','reviewer':'MODEL'}}
            v=audit_case(c,[f],r)
            self.assertFalse(v['customer_release_allowed'])
            self.assertFalse(v['independent_authentication_complete'])
            self.assertEqual(v['findings'][0]['assessment']['review_receipt_status'],'SUBMITTED_BUT_AUTHENTICATION_UNVERIFIED')
            self.assertEqual(v['coverage']['required_feature_count'],46)
            self.assertIn('MI_RES_2021_STAYED',v['selected_reference_candidates']['excluded_reference_ids'])
if __name__=='__main__':unittest.main()
