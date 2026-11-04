"""M5 V4 synthetic governance integrity tests: cannot silently relax source pins."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.m5_safety_change_gate import (
    ROOT, MANIFEST, PROTECTED_PATHS, GovernanceBlock,
    _git_blob, verify_safety_change_registry,
)


class SafetySourceChangeControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m5_change_control_")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.product = self.repo / "ventures" / "home-inspection"
        for relative in (MANIFEST, *PROTECTED_PATHS):
            target = self.product / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copy2(ROOT.parents[1] / "PAUSE_AUTONOMY",
                     self.repo / "PAUSE_AUTONOMY")

    def check(self):
        return verify_safety_change_registry(self.product, repo_root=self.repo)

    def registry(self):
        return json.loads((self.product / MANIFEST).read_text())

    def save(self, value):
        (self.product / MANIFEST).write_text(json.dumps(value), encoding="utf-8")

    def test_all_ten_critical_modules_and_pause_pin_match(self):
        result = self.check()
        self.assertEqual(result["checked_critical_sources"], 10)
        self.assertTrue(result["root_pause_marker_matches_pin"])
        self.assertFalse(result["external_peer_review_enforced"])
        self.assertFalse(result["github_branch_protection_verified"])
        self.assertFalse(result["customer_release_allowed"])

    def test_changed_serious_defect_threshold_module_blocks(self):
        file = self.product / PROTECTED_PATHS[0]
        file.write_bytes(file.read_bytes() + b"\n# unauthorized change\n")
        with self.assertRaisesRegex(GovernanceBlock, "changed without registry"):
            self.check()

    def test_changed_human_review_gate_blocks(self):
        file = self.product / "inspection_engine/m4_human_review.py"
        file.write_bytes(file.read_bytes() + b"\n# unreviewed edit\n")
        with self.assertRaisesRegex(GovernanceBlock, "human_review"):
            self.check()

    def test_missing_protected_module_blocks(self):
        (self.product / PROTECTED_PATHS[-1]).unlink()
        with self.assertRaises(GovernanceBlock):
            self.check()

    def test_missing_pause_marker_blocks(self):
        (self.repo / "PAUSE_AUTONOMY").unlink()
        with self.assertRaises(GovernanceBlock):
            self.check()

    def test_pause_marker_tampered_blocks(self):
        (self.repo / "PAUSE_AUTONOMY").write_text("removed")
        with self.assertRaisesRegex(GovernanceBlock, "pause"):
            self.check()

    def test_reordered_safety_files_blocks(self):
        registry = self.registry()
        registry["files"].reverse()
        self.save(registry)
        with self.assertRaisesRegex(GovernanceBlock, "reordered"):
            self.check()

    def test_dropped_protected_source_blocks(self):
        registry = self.registry()
        registry["files"].pop()
        self.save(registry)
        with self.assertRaisesRegex(GovernanceBlock, "Incomplete"):
            self.check()

    def test_false_release_claim_blocks(self):
        registry = self.registry()
        registry["customer_release_allowed"] = True
        self.save(registry)
        with self.assertRaisesRegex(GovernanceBlock, "Unsafe"):
            self.check()

    def test_registry_duplicate_keys_rejected(self):
        path = self.product / MANIFEST
        contents = path.read_text()
        path.write_text(contents.replace('"schema_version": 1,',
                                         '"schema_version": 1, "schema_version": 1,', 1))
        with self.assertRaisesRegex(GovernanceBlock, "Duplicate"):
            self.check()

    def test_symlinked_code_blocks(self):
        path = self.product / PROTECTED_PATHS[0]
        target = self.product / "backup.txt"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(GovernanceBlock, "Symlinked"):
            self.check()

    def test_registry_cannot_claim_other_branch(self):
        registry = self.registry()
        registry["required_branch"] = "main"
        self.save(registry)
        with self.assertRaisesRegex(GovernanceBlock, "Unsafe"):
            self.check()

    def test_registry_repin_is_not_independent_review(self):
        source = self.product / PROTECTED_PATHS[0]
        source.write_bytes(source.read_bytes() + b"\n# modified with explicit repin\n")
        registry = self.registry()
        registry["files"][0]["git_blob_sha1"] = _git_blob(source.read_bytes())
        self.save(registry)
        result = self.check()
        # Explicit co-editing passes local equality; a human reviewer must
        # challenge the paired source+registry diff. Do not claim otherwise.
        self.assertFalse(result["external_peer_review_enforced"])
        self.assertFalse(result["customer_release_allowed"])


if __name__ == "__main__":
    unittest.main()
