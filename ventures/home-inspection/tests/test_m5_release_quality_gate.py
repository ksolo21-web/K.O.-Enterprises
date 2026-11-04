"""M5 actual GitHub milestone: versioned examples and deterministic PDF pages."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.m5_release_quality_gate import (
    ROOT, MANIFEST, EXAMPLE_PATHS, QualityGateBlock,
    _blob_sha, verify_versioned_examples, verify_reproducible_report,
    BASELINE_FILE, verify_pinned_render_baseline,
)


class RepositoryM5Tests(unittest.TestCase):
    def copy_sources(self, dst):
        for relative in [MANIFEST, *EXAMPLE_PATHS]:
            source = ROOT / relative
            target = dst / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_pinned_synthetic_example_source_set(self):
        result = verify_versioned_examples()
        self.assertEqual(result["manifest_version"], 1)
        self.assertEqual(result["pinned_source_files"], 4)

    def test_changed_example_byte_requires_new_version(self):
        with tempfile.TemporaryDirectory(prefix="m5_fixture_integrity_") as folder:
            root = Path(folder)
            self.copy_sources(root)
            file = root / "examples" / "human_reference.json"
            file.write_bytes(file.read_bytes() + b" ")
            with self.assertRaisesRegex(QualityGateBlock, "bytes changed"):
                verify_versioned_examples(root)

    def test_incomplete_inventory_fails(self):
        with tempfile.TemporaryDirectory(prefix="m5_fixture_integrity_") as folder:
            root = Path(folder)
            self.copy_sources(root)
            manifest = json.loads((root / MANIFEST).read_text())
            manifest["examples"].pop()
            (root / MANIFEST).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(QualityGateBlock, "Incomplete"):
                verify_versioned_examples(root)

    def test_false_release_claim_in_registry_fails(self):
        with tempfile.TemporaryDirectory(prefix="m5_fixture_integrity_") as folder:
            root = Path(folder)
            self.copy_sources(root)
            manifest = json.loads((root / MANIFEST).read_text())
            manifest["customer_release_allowed"] = True
            (root / MANIFEST).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(QualityGateBlock, "Invalid"):
                verify_versioned_examples(root)

    def test_missing_synthetic_flag_cannot_be_re_pinned_as_real(self):
        with tempfile.TemporaryDirectory(prefix="m5_fixture_integrity_") as folder:
            root = Path(folder)
            self.copy_sources(root)
            project_path = root / "examples" / "editorial_demo_project.json"
            doc = json.loads(project_path.read_text())
            doc["property"]["synthetic"] = False
            project_path.write_text(json.dumps(doc, indent=2))
            manifest = json.loads((root / MANIFEST).read_text())
            for row in manifest["examples"]:
                if row["path"] == "examples/editorial_demo_project.json":
                    row["git_blob_sha1"] = _blob_sha(project_path.read_bytes())
            (root / MANIFEST).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(QualityGateBlock, "synthetic flag"):
                verify_versioned_examples(root)

    def test_clean_fixture_report_pixels_and_text_reproduce(self):
        report = verify_reproducible_report()
        self.assertTrue(report["all_pages_raster_and_text_reproducible"])
        self.assertGreaterEqual(report["rendered_page_count"], 5)
        self.assertEqual(len(report["page_visual_and_text_fingerprint"]), 64)
        self.assertFalse(report["customer_release_allowed"])
        self.assertFalse(report["model_accuracy_verified"])
        self.assertEqual(report["approved_synthetic_render_baseline"],
                         "m5-option2-synthetic-ubuntu24-py312-v1")

    def test_wrong_golden_visual_fingerprint_rejected(self):
        reference = json.loads((ROOT / BASELINE_FILE).read_text())
        with self.assertRaisesRegex(QualityGateBlock, "pinned"):
            verify_pinned_render_baseline(reference, 16, "0" * 64)

    def test_missing_report_pages_rejected_by_golden(self):
        reference = json.loads((ROOT / BASELINE_FILE).read_text())
        with self.assertRaisesRegex(QualityGateBlock, "pinned"):
            verify_pinned_render_baseline(
                reference, 15, reference["expected_visual_and_text_fingerprint"])

    def test_dependency_drift_rejected_even_with_same_pixels(self):
        reference = json.loads((ROOT / BASELINE_FILE).read_text())
        reference["packages"]["Pillow"] = "0.0.0"
        with self.assertRaisesRegex(QualityGateBlock, "runtime dependency"):
            verify_pinned_render_baseline(
                reference, 16, reference["expected_visual_and_text_fingerprint"])

    def test_baseline_not_customer_release_permission(self):
        reference = json.loads((ROOT / BASELINE_FILE).read_text())
        reference["customer_release_allowed"] = True
        with self.assertRaisesRegex(QualityGateBlock, "Unapproved"):
            verify_pinned_render_baseline(
                reference, 16, reference["expected_visual_and_text_fingerprint"])


if __name__ == "__main__":
    unittest.main()
