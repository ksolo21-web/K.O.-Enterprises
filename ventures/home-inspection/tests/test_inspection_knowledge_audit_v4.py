import unittest
from scripts.inspection_knowledge_audit import audit

class KnowledgeAuditV4(unittest.TestCase):
    def test_all_embedded_corpora_valid(self):
        v=audit()
        self.assertEqual(v['status'],'OFFLINE_POLICY_CONSISTENCY_PASSED_NOT_FIELD_VALIDATION')
        self.assertEqual(v['system_cards'],13)
        self.assertEqual(v['validated_engine_feature_codes'],46)
        self.assertEqual(v['michigan_code_status_count'],10)
    def test_law_and_certification_not_false_claims(self):
        v=audit()
        for flag in ('full_licensed_code_text_embedded','municipal_ahj_verified','external_source_freshness_verified',
                    'expert_annotated_field_accuracy_verified','customer_release_allowed'):
            self.assertIs(v[flag],False)
    def test_versions_not_silently_inferred(self):
        v=audit();self.assertEqual(v['scope_residential_2026']['standard'],'UNSELECTED')
        self.assertEqual(v['scope_residential_2027']['standard'],'UNSELECTED')
if __name__=='__main__':unittest.main()
