"""M5 V5 adversarial synthetic report evidence backup and recovery tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.m5_synthetic_recovery import (
    MEMBERS, RecoveryBlock, _info, _read_bundle,
    create_synthetic_bundle, restore_synthetic_bundle, verify_synthetic_bundle,
)


class SyntheticRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.working = tempfile.TemporaryDirectory(prefix="m5_recovery_tests_")
        cls.base = Path(cls.working.name)
        cls.source = cls.base / "good.zip"
        cls.first_result = create_synthetic_bundle(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.working.cleanup()

    def rewrite(self, changes=None, *, members=None):
        entries = _read_bundle(self.source)
        entries.update(changes or {})
        names = members or MEMBERS
        tmp = tempfile.TemporaryDirectory(prefix="m5_mutation_")
        self.addCleanup(tmp.cleanup)
        file = Path(tmp.name) / "changed.zip"
        with zipfile.ZipFile(file, "w") as archive:
            for name in names:
                archive.writestr(_info(name), entries.get(name, b"attack"))
        return file

    def test_generated_evidence_archive_contains_only_five_synthetic_files(self):
        self.assertEqual(self.first_result["archive_members_checked"], 5)
        self.assertEqual(self.first_result["rendered_pages_reverified"], 16)
        self.assertFalse(self.first_result["customer_data_recovered"])
        self.assertFalse(self.first_result["customer_release_allowed"])
        self.assertTrue(verify_synthetic_bundle(self.source)["page_fingerprint_matches_pinned_baseline"])

    def test_verified_restore_reproduces_pdf_and_receipts(self):
        with tempfile.TemporaryDirectory(prefix="m5_recovery_target_") as parent:
            destination = Path(parent) / "new_restoration"
            result = restore_synthetic_bundle(self.source, destination)
            self.assertEqual(result["restored_synthetic_files"], 5)
            self.assertTrue((destination / "option2_synthetic.pdf").is_file())
            self.assertEqual(len(result["restored_pdf_sha256"]), 64)
            self.assertFalse(result["customer_release_allowed"])

    def test_existing_restore_destination_blocks_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="m5_recovery_target_") as parent:
            with self.assertRaisesRegex(RecoveryBlock, "new"):
                restore_synthetic_bundle(self.source, Path(parent))

    def test_pdf_substitution_blocks_original_hash(self):
        file = self.rewrite({"proof/option2_synthetic.pdf": b"not a real pdf"})
        with self.assertRaisesRegex(RecoveryBlock, "hash mismatch"):
            verify_synthetic_bundle(file)

    def test_rehashed_fake_pdf_cannot_escape_golden_visual_check(self):
        original = _read_bundle(self.source)
        receipt = json.loads(original["proof/receipt.json"])
        receipt["members_sha256"]["proof/option2_synthetic.pdf"] = (
            __import__("hashlib").sha256(b"not a pdf").hexdigest())
        file = self.rewrite({
            "proof/option2_synthetic.pdf": b"not a pdf",
            "proof/receipt.json": json.dumps(receipt).encode(),
        })
        with self.assertRaisesRegex(RecoveryBlock, "PDF could not"):
            verify_synthetic_bundle(file)

    def test_release_permission_cannot_be_backed_up(self):
        original = _read_bundle(self.source)
        receipt = json.loads(original["proof/receipt.json"])
        receipt["customer_release_allowed"] = True
        file = self.rewrite({"proof/receipt.json": json.dumps(receipt).encode()})
        with self.assertRaisesRegex(RecoveryBlock, "release"):
            verify_synthetic_bundle(file)

    def test_source_manifest_substitution_blocks(self):
        file = self.rewrite({"proof/source_manifest.json": b'{"synthetic":false}'})
        with self.assertRaisesRegex(RecoveryBlock, "hash mismatch"):
            verify_synthetic_bundle(file)

    def test_missing_archive_member_blocks(self):
        file = self.rewrite(members=MEMBERS[:-1])
        with self.assertRaisesRegex(RecoveryBlock, "archive members"):
            verify_synthetic_bundle(file)

    def test_duplicate_member_blocks(self):
        file = self.rewrite(members=(*MEMBERS, MEMBERS[0]))
        with self.assertRaisesRegex(RecoveryBlock, "archive members"):
            verify_synthetic_bundle(file)

    def test_zip_path_traversal_is_never_extracted(self):
        file = self.rewrite(members=(*MEMBERS[:-1], "../escape.txt"))
        with self.assertRaisesRegex(RecoveryBlock, "archive members"):
            verify_synthetic_bundle(file)

    def test_zip_symlink_entry_blocks(self):
        original = _read_bundle(self.source)
        tmp = tempfile.TemporaryDirectory(prefix="m5_mutation_")
        self.addCleanup(tmp.cleanup)
        file = Path(tmp.name) / "symlink.zip"
        with zipfile.ZipFile(file, "w") as archive:
            for name in MEMBERS:
                info = _info(name)
                if name == MEMBERS[-1]:
                    info.external_attr = (0o120777 << 16)
                archive.writestr(info, original[name])
        with self.assertRaisesRegex(RecoveryBlock, "Unsafe"):
            verify_synthetic_bundle(file)

    def test_truncated_zip_blocks(self):
        with tempfile.TemporaryDirectory(prefix="m5_bad_zip_") as folder:
            path = Path(folder) / "broken.zip"
            path.write_bytes(self.source.read_bytes()[:80])
            with self.assertRaises(RecoveryBlock):
                verify_synthetic_bundle(path)

    def test_archive_cannot_live_inside_git_checkout(self):
        from scripts.m5_release_quality_gate import ROOT
        with self.assertRaisesRegex(RecoveryBlock, "outside Git"):
            create_synthetic_bundle(ROOT / "must_not_create_recovery.zip")

    def test_restore_refuses_git_path(self):
        from scripts.m5_release_quality_gate import ROOT
        with self.assertRaisesRegex(RecoveryBlock, "outside Git"):
            restore_synthetic_bundle(self.source, ROOT / "never_restore_here")


if __name__ == "__main__":
    unittest.main()
