from datetime import date
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.knowledge_audit import audit

class KnowledgeAuditTests(unittest.TestCase):
    def test_full_systems_and_no_production_release(self):
        a=audit(date(2026,10,31))
        self.assertEqual(a['source_count'],13)
        self.assertTrue(a['all_systems_covered'])
        self.assertEqual(a['system_count'],13)
        self.assertFalse(a['customer_release_allowed'])
    def test_no_fake_live_fetch_or_archived_claim(self):
        a=audit(date(2026,10,31))
        self.assertEqual(a['pages_archived_with_verified_hashes'],0)
        self.assertFalse(a['live_web_validation_performed'])
    def test_ashi_revision_is_pending(self):
        a=audit(date(2026,10,31))
        self.assertIn('ASHI_PENDING_2026',a['pending_effective_date'])
    def test_old_sources_flagged_for_review(self):
        a=audit(date(2027,10,31))
        self.assertGreaterEqual(len(a['older_than_180_days']),12)
