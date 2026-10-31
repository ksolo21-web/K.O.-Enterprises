import copy,unittest
from inspection_engine.hazard_sweep import load_hazard_sweep,plan_hazard_sweep,ReferenceBlock
from inspection_engine.descriptors import REQUIRED_FEATURES

class CriticalSweepTests(unittest.TestCase):
 def test_thirteen_systems_one_per_system(self):
  x=load_hazard_sweep();self.assertEqual({t['system'] for t in x['topics']},set(REQUIRED_FEATURES))
 def test_no_photo_does_not_prove_safe(self):
  x=plan_hazard_sweep({});self.assertEqual(x['systems_needing_assessment'],13)
  self.assertTrue(all(not r['verified_absence_of_hazard'] for r in x['tasks']))
 def test_photo_alone_not_inspected(self):
  x=plan_hazard_sweep({'electrical':{'status':'partial','media_ids':['P0001']}})
  item=next(a for a in x['tasks'] if a['system']=='electrical')
  self.assertEqual(item['assessment_status'],'HUMAN_ASSESSMENT_MISSING')
 def test_inspector_checked_not_blanket_clearance(self):
  x=plan_hazard_sweep({'electrical':{'status':'inspector_evaluated','media_ids':['P0001'],'qualified_human_review':True}})
  item=next(a for a in x['tasks'] if a['system']=='electrical')
  self.assertFalse(item['verified_absence_of_hazard']);self.assertEqual(x['systems_needing_assessment'],12)
 def test_unreviewed_supposed_complete_still_missing(self):
  x=plan_hazard_sweep({'electrical':{'status':'inspector_evaluated','media_ids':['P0001']}})
  self.assertEqual(x['systems_needing_assessment'],13)
 def test_invalid_system_refused(self):
  with self.assertRaises(ReferenceBlock):plan_hazard_sweep({'telepathy':{}})
 def test_duplicate_system_refused(self):
  r=load_hazard_sweep();r['topics'].append(copy.deepcopy(r['topics'][0]))
  from inspection_engine.hazard_sweep import CATALOG
  # custom source must still enforce unique systems, not silently double-check
  with self.assertRaises(ReferenceBlock):
   import tempfile,json
   from pathlib import Path
   with tempfile.TemporaryDirectory() as p:
    f=Path(p)/'invalid.json';f.write_text(json.dumps(r));load_hazard_sweep(f)
 def test_null_evidence_not_clearance(self):
  with self.assertRaises(ReferenceBlock):plan_hazard_sweep({'electrical':{'status':'inspector_evaluated','media_ids':None}})

if __name__=='__main__':unittest.main()
