"""Actual synthetic PDF/OCR custody tests. No inference or professional review."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.m3_source_reading_probe import prepare,verify_sources
from inspection_engine.core import DataError


class FrozenSourceProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'fixtures'
        cls.oracle=prepare(cls.root)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_three_cases_preserve_polarity_table_and_blank_gold(self):
        oracle,_=verify_sources(self.root)
        self.assertEqual([c['polarity_expectation'] for c in oracle['cases']],
            ['reported_affirmative','reported_negation','reported_negation'])
        for case in oracle['cases']:
            self.assertEqual(len(case['cells']),12)
            blank=[c for c in case['cells'] if c['role']=='blank']
            self.assertEqual(len(blank),1);self.assertEqual(blank[0]['ocr_word_indices'],[])
            self.assertFalse(oracle['professional_accuracy_verified'])
            self.assertFalse(oracle['lesson_activation_allowed'])
        scan=json.loads((self.root/'C-reference.json').read_text())
        self.assertFalse(any(p.get('text','') for p in scan['pages']))

    def test_existing_directory_is_never_overwritten(self):
        original=(self.root/'oracle.json').read_bytes()
        with self.assertRaises(DataError):prepare(self.root)
        self.assertEqual((self.root/'oracle.json').read_bytes(),original)

    def test_altered_oracle_is_rejected(self):
        p=self.root/'oracle.json';original=p.read_bytes()
        try:
            value=json.loads(original);value['cases'][0]['cells'][0]['printed_text']='altered'
            p.write_text(json.dumps(value))
            with self.assertRaises(DataError):verify_sources(self.root)
        finally:p.write_bytes(original)

    def test_altered_pdf_and_scan_parent_are_rejected(self):
        for name in ('A.pdf','B-scan-source.png'):
            p=self.root/name;original=p.read_bytes()
            try:
                p.write_bytes(original+b'changed')
                with self.subTest(name=name),self.assertRaises(DataError):verify_sources(self.root)
            finally:p.write_bytes(original)


if __name__=='__main__':unittest.main()
