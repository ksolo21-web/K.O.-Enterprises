"""Synthetic CE-1P session and protected output checks."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from company_os.competitive_visual_review import page_bytes, private_record, reviewer_access
from company_os.source_provenance import EvidenceError


class VisualReviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)

    def test_output_is_private_and_existing_observation_survives_retry(self):
        private_record(self.path, "receipt.json", b"original")
        with self.assertRaises(FileExistsError):
            private_record(self.path, "receipt.json", b"replacement")
        target = self.path / "receipt.json"
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.path.iterdir()), [target])

    def test_shared_output_and_symlink_denied(self):
        self.path.chmod(0o750)
        with self.assertRaises(EvidenceError):
            private_record(self.path, "receipt", b"private")
        link = self.path / "linked"
        link.symlink_to(self.path)
        with self.assertRaises(EvidenceError):
            private_record(link, "receipt", b"private")

    def test_display_rechecks_bytes_after_room_was_opened(self):
        pages = self.path / "pages"
        pages.mkdir()
        img = pages / "original-page-001.png"
        img.write_bytes(b"first")
        img.chmod(0o400)
        row = {"file": img.name, "png_sha256": hashlib.sha256(b"first").hexdigest()}
        self.assertEqual(page_bytes(self.path, row), b"first")
        img.chmod(0o600)
        img.write_bytes(b"other")
        img.chmod(0o400)
        with self.assertRaises(EvidenceError):
            page_bytes(self.path, row)

    def test_rejects_unprovisioned_room_and_privileged_reader(self):
        with self.assertRaises(EvidenceError):
            reviewer_access(self.path)
        with patch.object(os, "geteuid", return_value=0), self.assertRaises(EvidenceError):
            reviewer_access(self.path)
