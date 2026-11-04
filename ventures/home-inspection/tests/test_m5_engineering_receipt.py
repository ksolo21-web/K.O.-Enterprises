"""M5 V8 engineering receipt invariants and adversarial byte-tampering.

Fast mock source/recovery objects exercise receipt serialization and gating;
the GitHub M5 workflow additionally runs genuine source checks, full PDF
fingerprinting, 9-scenario scoring and actual ZIP creation/recovery.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import m5_engineering_receipt as receipt

COMMIT = "a" * 40
RUN_ID = "41840060056"


class EngineeringReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m5_v8_receipt_tests_")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.archive = self.directory / "synthetic.zip"
        self.archive.write_bytes(b"FAKE-ARCHIVE-MOCKED-VALIDATOR-NOT-A-REAL-PDF")
        self.path = self.directory / "evidence.json"
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.head = self.stack.enter_context(
            patch.object(receipt, "_git_head", return_value=COMMIT))
        self.safety = self.stack.enter_context(
            patch.object(receipt, "verify_safety_change_registry",
                         return_value={"checked_critical_sources": 10,
                                       "root_pause_marker_matches_pin": True,
                                       "customer_release_allowed": False}))
        self.examples = self.stack.enter_context(
            patch.object(receipt, "verify_versioned_examples",
                         return_value={"pinned_source_files": 4}))
        self.recovered = self.stack.enter_context(
            patch.object(receipt, "verify_synthetic_bundle",
                         return_value={"archive_members_checked": 5,
                                       "rendered_pages_reverified": 16,
                                       "page_fingerprint_matches_pinned_baseline": True,
                                       "customer_release_allowed": False}))
        self.matrix = self.stack.enter_context(
            patch.object(receipt, "run_matrix",
                         return_value={"synthetic_scenarios_checked": 9,
                                       "scenario_names": list(receipt.SCENARIOS),
                                       "invented_cases": 100,
                                       "invented_defect_labels": 90,
                                       "invented_critical_labels": 30,
                                       "invented_clean_control_cases": 10,
                                       "systems_covered": 13,
                                       "scopes": ["commercial", "residential"],
                                       "actual_accuracy_verified": False,
                                       "model_inference_run": False,
                                       "customer_release_allowed": False}))

    def make(self):
        return receipt.create_receipt(
            self.path, self.archive, commit=COMMIT,
            event="pull_request", run_id=RUN_ID)

    def check(self, **overrides):
        fields = dict(commit=COMMIT, event="pull_request", run_id=RUN_ID)
        fields.update(overrides)
        return receipt.verify_receipt(self.path, self.archive, **fields)

    def test_receipt_roundtrip_is_bounded_and_not_release_authority(self):
        result = self.make()
        self.assertTrue(self.path.is_file())
        self.assertLess(self.path.stat().st_size, receipt.MAX_RECEIPT)
        self.assertEqual(result["synthetic_scenarios_checked"], 9)
        self.assertTrue(result["archive_sha256_matches"])
        self.assertFalse(result["customer_release_allowed"])
        self.assertFalse(result["real_model_accuracy_verified"])
        self.assertEqual(result, self.check())

    def test_schema_pins_all_known_test_scenario_names(self):
        self.make()
        data = json.loads(self.path.read_text())
        self.assertEqual(data["synthetic_scenario_names"], list(receipt.SCENARIOS))
        self.assertEqual(data["verified_protected_safety_sources"], 10)
        self.assertEqual(data["verified_versioned_synthetic_files"], 4)
        self.assertEqual(data["verified_archive_member_count"], 5)
        self.assertEqual(data["rendered_pdf_pages"], 16)
        self.assertEqual(data["git_checkout_sha"], COMMIT)

    def test_no_authentication_claims_or_independent_signature(self):
        self.make()
        data = json.loads(self.path.read_text())
        self.assertFalse(data["source_evidence_is_real"])
        self.assertFalse(data["real_case_inspector_credentials_verified"])
        self.assertFalse(data["independent_repo_review_verified"])
        self.assertFalse(data["branch_protection_verified"])
        self.assertFalse(data["real_model_detection_accuracy_verified"])
        self.assertFalse(data["authentic_professional_holdout_verified"])
        self.assertFalse(data["signed_by_independent_authority"])
        self.assertFalse(data["field_pilot_authorized"])
        self.assertFalse(data["customer_release_allowed"])

    def test_changed_archive_bytes_are_rejected_even_if_its_validation_still_claims_success(self):
        self.make()
        self.archive.write_bytes(b"ALTERED-SYNTHETIC-ZIP-MOCK")
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check()

    def test_modified_receipt_release_flag_is_rejected(self):
        self.make()
        data = json.loads(self.path.read_text())
        data["customer_release_allowed"] = True
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check()

    def test_unauthenticated_evaluator_flag_cannot_be_flipped(self):
        self.make()
        data = json.loads(self.path.read_text())
        data["real_model_detection_accuracy_verified"] = True
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check()

    def test_wrong_or_changed_git_checkout_rejected(self):
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs from current"):
            receipt.expected_receipt(
                self.archive, commit="b" * 40, event="push", run_id=RUN_ID)
        self.make()
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs from current"):
            self.check(commit="b" * 40)

    def test_changed_declared_ci_event_or_run_id_rejected(self):
        self.make()
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check(event="push")
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check(run_id="41840060057")

    def test_unknown_ci_event_and_bad_run_id_rejected(self):
        with self.assertRaisesRegex(receipt.EvidenceBlock, "event"):
            receipt.expected_receipt(
                self.archive, commit=COMMIT, event="release",
                run_id=RUN_ID)
        with self.assertRaisesRegex(receipt.EvidenceBlock, "run ID"):
            receipt.expected_receipt(
                self.archive, commit=COMMIT, event="push", run_id="0")

    def test_overwritten_receipt_is_blocked(self):
        self.make()
        with self.assertRaisesRegex(receipt.EvidenceBlock, "new"):
            self.make()

    def test_duplicate_json_fields_rejected(self):
        self.make()
        source = self.path.read_bytes()
        self.path.write_bytes(source.replace(
            b'{"authentic_professional_holdout_verified":false,',
            b'{"authentic_professional_holdout_verified":false,'
            b'"authentic_professional_holdout_verified":true,'))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.check()

    def test_reformatted_json_rejected_as_noncanonical(self):
        self.make()
        data = json.loads(self.path.read_text())
        self.path.write_text(json.dumps(data, indent=2))
        with self.assertRaisesRegex(receipt.EvidenceBlock, "differs"):
            self.check()

    def test_missing_critical_safety_pin_fails(self):
        self.safety.return_value["root_pause_marker_matches_pin"] = False
        with self.assertRaisesRegex(receipt.EvidenceBlock, "Protected"):
            receipt.expected_receipt(self.archive, commit=COMMIT, event="push", run_id=RUN_ID)

    def test_missing_source_file_fails(self):
        self.examples.return_value["pinned_source_files"] = 3
        with self.assertRaisesRegex(receipt.EvidenceBlock, "source inventory"):
            receipt.expected_receipt(self.archive, commit=COMMIT, event="push", run_id=RUN_ID)

    def test_shortened_benchmark_matrix_fails(self):
        self.matrix.return_value["synthetic_scenarios_checked"] = 8
        with self.assertRaisesRegex(receipt.EvidenceBlock, "benchmark"):
            receipt.expected_receipt(self.archive, commit=COMMIT, event="push", run_id=RUN_ID)

    def test_archive_report_permission_drift_fails(self):
        self.recovered.return_value["customer_release_allowed"] = True
        with self.assertRaisesRegex(receipt.EvidenceBlock, "Recovery"):
            receipt.expected_receipt(self.archive, commit=COMMIT, event="push", run_id=RUN_ID)

    def test_symlink_receipt_is_rejected(self):
        target = self.directory / "link_target"
        target.write_bytes(b"hello")
        self.path.symlink_to(target)
        with self.assertRaisesRegex((receipt.EvidenceBlock, ValueError), "symlink"):
            self.check()

    def test_no_receipt_ever_written_inside_git_checkout(self):
        with self.assertRaisesRegex(ValueError, "outside Git"):
            receipt.create_receipt(
                receipt.ROOT / "forbidden-m5-receipt.json",
                self.archive, commit=COMMIT, event="push", run_id=RUN_ID)


if __name__ == "__main__":
    unittest.main()
