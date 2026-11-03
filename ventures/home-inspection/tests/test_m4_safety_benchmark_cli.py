"""M4 V8 strict private audit file ingestion; synthetic JSON only."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from inspection_engine.serious_defect_benchmark import BenchmarkBlock
from scripts.m4_safety_benchmark_cli import _private_json


class FrozenAuditPrivateCLITests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.path=self.root/"synthetic_audit.json"
        self.path.write_text('{"synthetic":true,"customer_release_allowed":false}',
                             encoding="utf-8")

    def test_only_bounded_private_json_is_accepted(self):
        result=_private_json(self.path)
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["customer_release_allowed"])

    def test_ambiguous_duplicate_field_is_rejected(self):
        self.path.write_text('{"customer_release_allowed":false,"customer_release_allowed":true}')
        with self.assertRaisesRegex(BenchmarkBlock,"Duplicate private audit JSON key"):
            _private_json(self.path)

    def test_nonfinite_json_number_is_rejected(self):
        self.path.write_text('{"defect_recall":NaN}')
        with self.assertRaisesRegex(BenchmarkBlock,"Nonstandard private audit number"):
            _private_json(self.path)

    def test_symlink_to_private_source_is_rejected(self):
        alias=self.root/"alias.json"
        alias.symlink_to(self.path)
        with self.assertRaisesRegex(BenchmarkBlock,"symlink"):
            _private_json(alias)

    def test_real_or_synthetic_records_cannot_be_loaded_from_git_checkout(self):
        checkout=self.root/"checkout"
        checkout.mkdir()
        (checkout/".git").mkdir()
        inside=checkout/"audit.json"
        inside.write_bytes(self.path.read_bytes())
        with self.assertRaisesRegex(BenchmarkBlock,"outside Git"):
            _private_json(inside)


if __name__=="__main__":
    unittest.main()
