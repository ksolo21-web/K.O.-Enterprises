"""Adversarial tests of the M5 synthetic-only serious-defect QA matrix.

No inspections, actual models, professional credentials or customer evidence.
"""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from inspection_engine.serious_defect_benchmark import (
    METRIC_REVIEW_PENDING, SYSTEMS, score_serious_defects,
)
from inspection_engine.m5_pilot_readiness import assess_pilot_cohort_design
from scripts import m5_benchmark_contract_gate as gate


class M5BenchmarkContractTests(unittest.TestCase):
    def setUp(self):
        self.cases, self.predictions, self.cohort = gate.fixture()

    def test_100_invented_cases_cover_13_systems_and_both_scopes(self):
        self.assertEqual(len(self.cases), 100)
        self.assertEqual(len(set(c["case_id"] for c in self.cases)), 100)
        self.assertEqual(len(self.predictions), 90)
        self.assertEqual({l["system"] for c in self.cases for l in c["labels"]}, SYSTEMS)
        self.assertEqual({c["scope"] for c in self.cases}, {"residential", "commercial"})
        self.assertEqual(sum(not c["labels"] for c in self.cases), 10)

    def test_fixture_is_purely_declared_and_not_validated_field_evidence(self):
        self.assertTrue(all(c["qualified_labeler_id"].startswith("UNVERIFIED")
                            for c in self.cases))
        self.assertTrue(all(x["synthetic"] is True for x in self.cohort))
        self.assertTrue(all(c["case_id"].startswith("synthetic-contract")
                            for c in self.cases))
        report = gate.run_matrix()
        self.assertFalse(report["professional_labeling_or_consent_authenticated"])
        self.assertFalse(report["actual_accuracy_verified"])
        self.assertFalse(report["model_inference_run"])
        self.assertFalse(report["customer_release_allowed"])

    def test_baseline_metric_success_still_rejects_production(self):
        score = score_serious_defects(self.cases, self.predictions)
        self.assertEqual(score["status"], METRIC_REVIEW_PENDING)
        self.assertEqual(score["critical_defects"], 30)
        self.assertEqual(score["human_adjudicated_defects"], 90)
        self.assertTrue(score["metric_thresholds_met"])
        self.assertFalse(score["professional_credentials_externally_verified"])
        self.assertFalse(score["production_release_allowed"])

    def test_missed_critical_is_fatal(self):
        result = score_serious_defects(self.cases, self.predictions[1:])
        self.assertEqual(len(result["critical_misses"]), 1)
        self.assertFalse(result["metric_thresholds_met"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_missed_major_is_fatal(self):
        result = score_serious_defects(self.cases, [
            d for d in self.predictions if d["case_id"] != self.cases[30]["case_id"]])
        self.assertEqual(len(result["major_misses"]), 1)
        self.assertFalse(result["metric_thresholds_met"])

    def test_five_false_positives_breach_precision_floor(self):
        false = [gate.false_positive(self.cases[90+i], i) for i in range(5)]
        score = score_serious_defects(self.cases, self.predictions + false)
        self.assertAlmostEqual(score["human_verified_precision"], 90 / 95)
        self.assertFalse(score["metric_thresholds_met"])
        self.assertEqual(len(score["unmatched_or_unverified_predictions"]), 5)

    def test_one_false_positive_above_floor_not_independent_approval(self):
        score = score_serious_defects(
            self.cases, self.predictions+[gate.false_positive(self.cases[90], 0)])
        self.assertTrue(score["metric_thresholds_met"])
        self.assertFalse(score["production_release_allowed"])

    def test_nine_clean_controls_fail_design_even_with_100_cases(self):
        altered = copy.deepcopy(self.cohort)
        altered[90]["clean_media_controls"] = 0
        summary = assess_pilot_cohort_design(altered, training_property_groups=[])
        self.assertEqual(summary["planned_clean_control_cases"], 9)
        self.assertFalse(summary["clean_controls_design_met"])
        self.assertFalse(summary["field_pilot_authorized"])

    def test_training_family_overlap_fails_design(self):
        summary = assess_pilot_cohort_design(
            self.cohort, training_property_groups=[self.cohort[0]["property_group_id"]])
        self.assertEqual(summary["training_property_group_collisions"], 1)
        self.assertFalse(summary["all_cohort_design_checks_met_only"])

    def test_ninety_nine_cases_fail_threshold(self):
        summary = score_serious_defects(self.cases[:-1], self.predictions)
        self.assertFalse(summary["minimum_cohort_met"])

    def test_missing_moderate_is_visible_but_not_false_customer_approval(self):
        s = score_serious_defects(
            self.cases,
            [p for p in self.predictions if p["case_id"] != self.cases[60]["case_id"]])
        self.assertTrue(s["metric_thresholds_met"])
        self.assertEqual(len(s["all_misses"]), 1)
        self.assertEqual(s["all_misses"][0]["severity"], "moderate")
        self.assertFalse(s["production_release_allowed"])

    def test_static_summary_still_reports_all_nine_scenarios(self):
        r = gate.run_matrix()
        self.assertEqual(r["synthetic_scenarios_checked"], 9)
        self.assertEqual(r["systems_covered"], 13)
        self.assertEqual(r["invented_clean_control_cases"], 10)
        self.assertEqual(r["status"], "NINE_SYNTHETIC_SOFTWARE_BENCHMARK_CONTRACTS_ONLY")

    def test_mutated_scoring_reports_missing_critical_as_pass_matrix_catches(self):
        original = gate.score_serious_defects
        def compromised(cases, detections):
            score = original(cases, detections)
            if score["critical_misses"]:
                score["metric_thresholds_met"] = True
            return score
        with patch.object(gate, "score_serious_defects", side_effect=compromised):
            with self.assertRaisesRegex(gate.ContractBlock, "critical finding"):
                gate.run_matrix()

    def test_mutated_scoring_approves_production_matrix_catches(self):
        original = gate.score_serious_defects
        def compromised(cases, detections):
            score = original(cases, detections)
            score["production_release_allowed"] = True
            return score
        with patch.object(gate, "score_serious_defects", side_effect=compromised):
            with self.assertRaisesRegex(gate.ContractBlock, "professional approval"):
                gate.run_matrix()

    def test_mutated_cohort_approves_field_pilot_matrix_catches(self):
        original = gate.assess_pilot_cohort_design
        def compromised(cases, *, training_property_groups):
            r = original(cases, training_property_groups=training_property_groups)
            r["field_pilot_authorized"] = True
            return r
        with patch.object(gate, "assess_pilot_cohort_design", side_effect=compromised):
            with self.assertRaisesRegex(gate.ContractBlock, "design-only"):
                gate.run_matrix()


if __name__ == "__main__":
    unittest.main()
