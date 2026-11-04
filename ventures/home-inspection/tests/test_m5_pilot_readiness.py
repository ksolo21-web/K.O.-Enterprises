"""M5 V1 pilot cohort design contracts; synthetic records only."""
from __future__ import annotations
import copy
import unittest
from inspection_engine.m5_pilot_readiness import assess_pilot_cohort_design
from inspection_engine.serious_defect_benchmark import BenchmarkBlock, SYSTEMS


def fixture():
    subjects = sorted(SYSTEMS)
    rows = []
    for index in range(100):
        rows.append({
            "case_id": f"case-{index:03d}",
            "property_group_id": f"property-{index:03d}",
            "scope": "residential" if index % 2 else "commercial",
            "systems": [subjects[index % len(subjects)]],
            "critical_labels": 1 if index < 30 else 0,
            "total_defect_labels": 1 if index < 30 else 0,
            "clean_media_controls": 1 if 30 <= index < 40 else 0,
            "reviewer_id": "inspector-A",
            "adjudicator_id": "inspector-B",
            "custodian_id": "custodian-C",
            "consent_document_declared": True,
            "byte_preflight_declared": True,
            "synthetic": True,
        })
    return rows


class PilotReadinessTests(unittest.TestCase):
    def setUp(self):
        self.cases = fixture()

    def score(self, training=None):
        return assess_pilot_cohort_design(
            self.cases, training_property_groups=[] if training is None else training)

    def test_synthetic_design_meets_counts_but_never_authorizes(self):
        result = self.score()
        self.assertTrue(result["all_cohort_design_checks_met_only"])
        self.assertEqual(result["planned_cases"], 100)
        self.assertEqual(result["planned_critical_labels"], 30)
        self.assertEqual(result["planned_system_coverage"], 13)
        self.assertEqual(result["planned_clean_control_cases"], 10)
        self.assertEqual(result["synthetic_or_example_cases"], 100)
        self.assertFalse(result["field_pilot_authorized"])
        self.assertFalse(result["customer_release_allowed"])

    def test_below_hundred_fails_design(self):
        self.cases = self.cases[:99]
        self.assertFalse(self.score()["cohort_size_design_met"])

    def test_insufficient_critical_labels(self):
        self.cases[0]["critical_labels"] = 0
        self.assertFalse(self.score()["critical_label_design_met"])

    def test_missing_inspection_system(self):
        for c in self.cases:
            c["systems"] = ["roof"]
        self.assertFalse(self.score()["thirteen_system_design_met"])

    def test_missing_commercial_scope(self):
        for c in self.cases:
            c["scope"] = "residential"
        self.assertFalse(self.score()["residential_commercial_design_met"])

    def test_missing_clean_cases(self):
        for c in self.cases:
            c["clean_media_controls"] = 0
        self.assertFalse(self.score()["clean_controls_design_met"])

    def test_training_group_leakage_fails(self):
        r = self.score(training=["property-002"])
        self.assertEqual(r["training_property_group_collisions"], 1)
        self.assertFalse(r["all_cohort_design_checks_met_only"])

    def test_reused_property_family_rejected(self):
        self.cases[1]["property_group_id"] = self.cases[0]["property_group_id"]
        with self.assertRaisesRegex(BenchmarkBlock, "Repeated"):
            self.score()

    def test_self_approval_fails_documentary_consistency(self):
        self.cases[0]["custodian_id"] = self.cases[0]["reviewer_id"]
        self.assertFalse(self.score()["documentary_consistency_met"])

    def test_without_consent_record_fails(self):
        self.cases[0]["consent_document_declared"] = False
        self.assertFalse(self.score()["documentary_consistency_met"])

    def test_without_source_byte_check_fails(self):
        self.cases[0]["byte_preflight_declared"] = False
        self.assertFalse(self.score()["documentary_consistency_met"])

    def test_non_bool_declaration_rejected(self):
        self.cases[0]["consent_document_declared"] = 1
        with self.assertRaisesRegex(BenchmarkBlock, "boolean"):
            self.score()

    def test_negative_or_fractional_critical_labels_rejected(self):
        for invalid in (-1, 0.3, True):
            self.cases[0]["critical_labels"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(BenchmarkBlock):
                self.score()

    def test_duplicate_system_field_rejected(self):
        self.cases[0]["systems"] = ["roof", "roof"]
        with self.assertRaisesRegex(BenchmarkBlock, "Invalid"):
            self.score()

    def test_clean_photo_inside_defective_case_is_not_a_clean_case(self):
        self.cases[30]["total_defect_labels"] = 1
        self.assertEqual(self.score()["planned_clean_control_cases"], 9)
        self.assertFalse(self.score()["clean_controls_design_met"])

    def test_critical_labels_cannot_exceed_total_labels(self):
        self.cases[0]["total_defect_labels"] = 0
        with self.assertRaisesRegex(BenchmarkBlock, "Invalid bounded"):
            self.score()

    def test_empty_cohort_does_not_pass(self):
        self.cases = []
        self.assertFalse(self.score()["all_cohort_design_checks_met_only"])


if __name__ == "__main__":
    unittest.main()
