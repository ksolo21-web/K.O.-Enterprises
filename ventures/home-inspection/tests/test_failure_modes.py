import copy
import unittest
from inspection_engine.failure_modes import load_playbooks,validate_playbooks,build_failure_mode_brief,KnowledgeError
from inspection_engine.descriptors import REQUIRED_FEATURES
class FailureModeValidation(unittest.TestCase):
    def setUp(self):self.catalog=load_playbooks()
    def test_complete_13_domains(self):self.assertEqual(len(self.catalog['systems']),13)
    def test_complete_46_features(self):
        self.assertEqual(sum(len(p['feature_codes']) for p in self.catalog['systems']),46)
    def test_codes_exact(self):
        self.assertEqual({p['system']:p['feature_codes'] for p in self.catalog['systems']},
                         {k:list(v) for k,v in REQUIRED_FEATURES.items()})
    def test_purpose_not_authoritative_code(self):
        self.assertIn('not_source_verified_code',self.catalog['status'])
    def test_no_unsound_permission(self):
        p=copy.deepcopy(self.catalog);p['systems'][0]['may_declare_cause_proven']=True
        with self.assertRaises(KnowledgeError):validate_playbooks(p)
    def test_no_undocumented_system(self):
        p=copy.deepcopy(self.catalog);p['systems'][0]['system']='pool'
        with self.assertRaises(KnowledgeError):validate_playbooks(p)
    def test_no_drift_in_codes(self):
        p=copy.deepcopy(self.catalog);p['systems'][0]['feature_codes'].append('imaginary_feature')
        with self.assertRaises(KnowledgeError):validate_playbooks(p)
    def test_missing_alternatives_rejected(self):
        p=copy.deepcopy(self.catalog);p['systems'][0]['alternative_explanation']=''
        with self.assertRaises(KnowledgeError):validate_playbooks(p)
    def test_prompt_includes_possible_and_alternative(self):
        b=build_failure_mode_brief(['foundation'])
        self.assertIn('ALTERNATIVE',b);self.assertIn('ADDITIONAL TEST',b);self.assertIn('not diagnosing',b)
    def test_ambiguous_system_rejected(self):
        with self.assertRaises(KnowledgeError):build_failure_mode_brief(['unknown'])
    def test_mutation_isolated(self):
        d=load_playbooks();d['systems'][0]['possible_mechanism']='false'
        self.assertNotEqual(load_playbooks()['systems'][0]['possible_mechanism'],'false')
if __name__=='__main__':unittest.main()
