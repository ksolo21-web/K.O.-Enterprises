"""M4 V8 frozen serious-defect evaluation contract: synthetic fixtures only.

NO REAL CASES, INSPECTOR CREDENTIALS OR COMMERCIAL AUTHORITY CREATED. Even a
100-case all-green synthetic test never authorizes production/customer release.
"""
from __future__ import annotations

import copy
import hashlib
import unittest

from inspection_engine.m4_frozen_safety_audit import score_frozen_safety_audit, digest
from inspection_engine.serious_defect_benchmark import BenchmarkBlock, SYSTEMS


def sha(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def synthetic_case(i, *, severity="critical", system="electrical", scope="residential"):
    cid=f"synthetic-case-{i:03d}"
    return {
        "case_id":cid,
        "source_group_id":f"synthetic-property-group-{i:03d}",
        "evidence_sha256":sha("SYNTHETIC_EVIDENCE_"+str(i)),
        "synthetic":False,   # DECLARED only; test cannot authenticate real provenance
        "consented_for_evaluation":True,
        "partition":"locked_holdout",
        "training_overlap":False,
        "qualified_labeler_id":f"unverified-human-labeler-{i:03d}",
        "independent_adjudicator_id":f"unverified-reviewer-{i:03d}",
        "jurisdiction":"MI",
        "scope":scope,
        "labels":[{"label_id":"label-001","status":"adjudicated",
                   "severity":severity,"system":system}]
    }


def prediction(case, *, pid="prediction-001"):
    return {
        "case_id":case["case_id"],"prediction_id":pid,
        "system":case["labels"][0]["system"],
        "source_evidence_sha256":case["evidence_sha256"]
    }


def matched(case, *, pid="prediction-001", disposition="matched"):
    return {
        "case_id":case["case_id"],"prediction_id":pid,
        "adjudicator_id":case["independent_adjudicator_id"],
        "disposition":disposition,
        "matched_label_id":"label-001" if disposition=="matched" else None,
        "reason":"Synthetic independent review; source and human identity not authenticated"
    }


class FrozenSafetyAuditTests(unittest.TestCase):
    def setUp(self):
        self.cases=[synthetic_case(1)]
        self.predictions=[prediction(self.cases[0])]
        self.matches=[matched(self.cases[0])]
        self.training={
            "schema_version":1,
            "model_sha256":sha("SYNTHETIC-LOCAL-MODEL"),
            "source_digests":[sha("OTHER-TRAINING-SOURCE")],
            "source_group_ids":["different-property-family"],
            "registry_scope":"ALL_KNOWN_TRAINING_AND_TUNING_SOURCES",
            "customer_release_allowed":False,
        }
        self.reseal()

    def reseal(self):
        self.model={
            "schema_version":1,
            "evaluation_id":"synthetic-evaluation-001",
            "model_id":"synthetic-model-A",
            "model_sha256":self.training["model_sha256"],
            "prompt_sha256":sha("SYNTHETIC_PROMPT"),
            "generated_at_utc":"2026-11-03T13:00:00Z",
            "case_manifest_sha256":digest(self.cases),
            "training_index_sha256":digest(self.training),
            "predictions_sha256":digest(self.predictions),
            "blinded_to_labels_declared":True,
            "customer_release_allowed":False,
        }
        self.adjudication={
            "schema_version":1,
            "evaluation_id":self.model["evaluation_id"],
            "case_manifest_sha256":digest(self.cases),
            "model_snapshot_sha256":digest(self.model),
            "matches_sha256":digest(self.matches),
            "adjudicated_at_utc":"2026-11-03T13:01:00Z",
            "reviewer_independent_of_model_declared":True,
            "customer_release_allowed":False,
        }

    def evaluate(self, **pins):
        return score_frozen_safety_audit(
            self.cases,self.predictions,self.matches,self.model,
            self.adjudication,self.training,
            independent_case_pin_sha256=pins.get("case",digest(self.cases)),
            independent_model_snapshot_pin_sha256=pins.get("model",digest(self.model)),
            independent_adjudication_pin_sha256=pins.get("adjudication",digest(self.adjudication)),
            independent_training_index_pin_sha256=pins.get("training",digest(self.training)),
        )

    def test_single_synthetic_case_does_not_meet_cohort_and_never_releases(self):
        result=self.evaluate()
        self.assertEqual(result["prediction_count"],1)
        self.assertEqual(result["serious_defect_score"]["critical_misses"],[])
        self.assertFalse(result["metric_thresholds_met_only"])
        self.assertFalse(result["customer_release_allowed"])
        self.assertFalse(result["real_world_case_consent_independently_verified"])
        self.assertFalse(result["model_never_saw_labels_independently_proven"])

    def test_missing_critical_defect_is_recorded_and_blocks(self):
        self.predictions=[]
        self.matches=[]
        self.reseal()
        r=self.evaluate()
        self.assertEqual(len(r["serious_defect_score"]["critical_misses"]),1)
        self.assertEqual(r["prediction_count"],0)
        self.assertFalse(r["metric_thresholds_met_only"])

    def test_false_positive_is_counted_conservatively(self):
        self.matches[0]=matched(self.cases[0],disposition="false_positive")
        self.reseal()
        r=self.evaluate()
        self.assertEqual(r["false_positives"],1)
        self.assertEqual(len(r["serious_defect_score"]["critical_misses"]),1)
        self.assertEqual(r["serious_defect_score"]["human_verified_precision"],0.0)

    def test_inconclusive_prediction_is_not_a_true_positive(self):
        self.matches[0]=matched(self.cases[0],disposition="inconclusive")
        self.reseal()
        r=self.evaluate()
        self.assertEqual(r["inconclusive_count"],1)
        self.assertEqual(r["false_positives"],1)
        self.assertEqual(len(r["serious_defect_score"]["critical_misses"]),1)

    def test_external_case_pin_mismatch_blocks(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Holdout case manifest changed"):
            self.evaluate(case="f"*64)

    def test_external_model_pin_mismatch_blocks(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Frozen model snapshot differs"):
            self.evaluate(model="f"*64)

    def test_external_match_pin_mismatch_blocks(self):
        with self.assertRaisesRegex(BenchmarkBlock,"adjudication snapshot differs"):
            self.evaluate(adjudication="f"*64)

    def test_external_training_pin_mismatch_blocks(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Training exclusion registry differs"):
            self.evaluate(training="f"*64)

    def test_changed_prediction_after_freeze_blocks(self):
        self.predictions[0]["prediction_id"]="unfrozen-new-ID"
        with self.assertRaisesRegex(BenchmarkBlock,"Predictions not bound"):
            self.evaluate()

    def test_changed_matching_decision_after_adjudication_freeze_blocks(self):
        self.matches[0]["reason"]="Now changed, must not pass after sealing"
        with self.assertRaisesRegex(BenchmarkBlock,"Post-freeze adjudication"):
            self.evaluate()

    def test_training_evidence_digest_collision_rejected(self):
        self.training["source_digests"].append(self.cases[0]["evidence_sha256"])
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Training/holdout source collision"):
            self.evaluate()

    def test_training_property_family_collision_rejected(self):
        self.training["source_group_ids"].append(self.cases[0]["source_group_id"])
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Training/holdout source collision"):
            self.evaluate()

    def test_repeated_source_file_in_two_holdout_cases_rejected(self):
        other=synthetic_case(2)
        other["evidence_sha256"]=self.cases[0]["evidence_sha256"]
        self.cases.append(other)
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Duplicate holdout"):
            self.evaluate()

    def test_repeated_property_in_two_holdout_cases_rejected(self):
        other=synthetic_case(2)
        other["source_group_id"]=self.cases[0]["source_group_id"]
        self.cases.append(other)
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Duplicate holdout"):
            self.evaluate()

    def test_invalid_prediction_evidence_hash_rejected(self):
        self.predictions[0]["source_evidence_sha256"]=sha("wrong")
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"exact source evidence"):
            self.evaluate()

    def test_duplicate_model_prediction_id_rejected(self):
        self.predictions.append(copy.deepcopy(self.predictions[0]))
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"repeated ID"):
            self.evaluate()

    def test_missing_match_disposition_rejected(self):
        self.matches=[]
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"every frozen prediction|Every frozen prediction"):
            self.evaluate()

    def test_multiple_decisions_for_single_prediction_rejected(self):
        self.matches.append(copy.deepcopy(self.matches[0]))
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"duplicate model prediction"):
            self.evaluate()

    def test_two_model_predictions_cannot_claim_same_defect(self):
        self.predictions.append(prediction(self.cases[0],pid="prediction-002"))
        self.matches.append(matched(self.cases[0],pid="prediction-002"))
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"matched multiple times"):
            self.evaluate()

    def test_invented_label_match_rejected(self):
        self.matches[0]["matched_label_id"]="invented-label"
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"nonexistent"):
            self.evaluate()

    def test_wrong_system_matched_label_rejected(self):
        self.predictions[0]["system"]="roof"
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Wrong-system"):
            self.evaluate()

    def test_match_reviewer_identity_must_equal_independent_adjudicator(self):
        self.matches[0]["adjudicator_id"]="original-labeler"
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"independent case adjudicator"):
            self.evaluate()

    def test_adjudication_timestamp_must_follow_model_freeze(self):
        self.adjudication["adjudicated_at_utc"]=self.model["generated_at_utc"]
        with self.assertRaisesRegex(BenchmarkBlock,"strictly after"):
            self.evaluate()

    def test_blindness_must_be_explicitly_declared(self):
        self.model["blinded_to_labels_declared"]=False
        self.adjudication["model_snapshot_sha256"]=digest(self.model)
        with self.assertRaisesRegex(BenchmarkBlock,"Explicit blind"):
            self.evaluate()

    def test_training_index_must_include_tuning_sources(self):
        self.training["registry_scope"]="TRAINING_ONLY"
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Incomplete training or tuning"):
            self.evaluate()

    def test_model_artifact_hash_cannot_change_after_training_snapshot(self):
        self.model["model_sha256"]=sha("ANOTHER_MODEL")
        self.adjudication["model_snapshot_sha256"]=digest(self.model)
        with self.assertRaisesRegex(BenchmarkBlock,"frozen model"):
            self.evaluate()

    def test_unconsented_case_rejected_even_if_label_present(self):
        self.cases[0]["consented_for_evaluation"]=False
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Real, specifically consented"):
            self.evaluate()

    def test_ai_generated_or_unreviewed_label_rejected(self):
        self.cases[0]["labels"][0]["status"]="model_invented"
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Unreviewed defect label"):
            self.evaluate()

    def test_duplicate_training_registry_sources_rejected(self):
        self.training["source_digests"]*=2
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Duplicate training source"):
            self.evaluate()

    def test_naive_boolean_overrides_are_not_accepted(self):
        self.training["customer_release_allowed"]=True
        self.reseal()
        with self.assertRaisesRegex(BenchmarkBlock,"Incomplete training"):
            self.evaluate()

    def test_nan_in_manifest_hashing_fails_closed(self):
        self.cases[0]["untrusted_number"]=float("nan")
        with self.assertRaisesRegex(BenchmarkBlock,"Noncanonical safety benchmark"):
            self.evaluate()

    def test_full_synthetic_threshold_fixture_may_pass_metrics_but_never_production(self):
        systems=sorted(SYSTEMS)
        self.cases=[synthetic_case(i+1,
                     severity="critical" if i<30 else "moderate",
                     system=systems[i%len(systems)],
                     scope="commercial" if i%2 else "residential")
                    for i in range(100)]
        self.predictions=[prediction(c) for c in self.cases]
        self.matches=[matched(c) for c in self.cases]
        self.reseal()
        result=self.evaluate()
        s=result["serious_defect_score"]
        self.assertEqual(s["cases"],100)
        self.assertEqual(s["critical_defects"],30)
        self.assertEqual(len(result["per_system"]),13)
        self.assertTrue(result["metric_thresholds_met_only"])
        self.assertEqual(s["human_verified_precision"],1)
        self.assertEqual(s["critical_misses"],[])
        self.assertFalse(result["real_world_case_consent_independently_verified"])
        self.assertFalse(result["human_professional_credentials_independently_verified"])
        self.assertFalse(result["customer_release_allowed"])
        self.assertFalse(s["production_release_allowed"])

    def test_one_missed_critical_in_100_case_fixture_fails_metric_gate(self):
        systems=sorted(SYSTEMS)
        self.cases=[synthetic_case(i+1,
                     severity="critical" if i<30 else "moderate",
                     system=systems[i%len(systems)],
                     scope="commercial" if i%2 else "residential")
                    for i in range(100)]
        self.predictions=[prediction(c) for c in self.cases]
        self.matches=[matched(c) for c in self.cases]
        self.matches[0]=matched(self.cases[0],disposition="false_positive")
        self.reseal()
        result=self.evaluate()
        self.assertFalse(result["metric_thresholds_met_only"])
        self.assertEqual(len(result["serious_defect_score"]["critical_misses"]),1)
        self.assertFalse(result["customer_release_allowed"])

if __name__=="__main__":
    unittest.main()
