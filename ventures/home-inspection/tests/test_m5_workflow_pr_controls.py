"""Static M5 V6 workflow PR checks: read-only, synthetic, never release.

Not GitHub branch protection, independent peer review, or an approved field run.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
M3 = REPO / ".github/workflows/home-inspection-m3-v8-offline.yml"
M5 = REPO / ".github/workflows/home-inspection-m5-quality.yml"

class WorkflowPremergeGuards(unittest.TestCase):
    def test_both_workflows_trigger_on_pull_requests_to_dev_only(self):
        for path in [M3, M5]:
            with self.subTest(workflow=path.name):
                s = path.read_text(encoding="utf-8")
                trigger = s[s.index("\non:"):s.index("\npermissions:")] if "\npermissions:" in s else s[s.index("\non:"):s.index("\nconcurrency:")]
                self.assertIn("\n  pull_request:\n    branches: [home-inspection-development]", trigger)
                self.assertIn("\n    paths:\n      - 'ventures/home-inspection/**'", trigger)
                self.assertIn(f"      - '.github/workflows/{path.name}'", trigger)
                self.assertIn("\n  push:\n    branches: [home-inspection-development]", trigger)
                self.assertNotIn("pull_request_target:", trigger)
                self.assertNotIn("branches: [main]", trigger)

    def test_both_premerge_jobs_use_read_only_token_and_ephemeral_checkout(self):
        for path in [M3, M5]:
            with self.subTest(workflow=path.name):
                s = path.read_text(encoding="utf-8")
                self.assertIn("permissions:\n  contents: read", s)
                self.assertIn("persist-credentials: false", s)
                self.assertNotIn("secrets.", s)
                self.assertNotIn("git push", s)
                self.assertNotIn("pull_request_target", s)
                self.assertNotIn("customer_data/", s)
                self.assertIn("COMPANY_OS_PAUSED: '1'", s)
                self.assertIn("git diff --exit-code -- .", s)

    def test_critical_premerge_test_scopes_remain_unchanged(self):
        m3 = M3.read_text(encoding="utf-8")
        m5 = M5.read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -q", m3)
        self.assertIn("python -m scripts.m5_safety_change_gate", m5)
        self.assertIn("python -m scripts.m5_release_quality_gate", m5)
        self.assertIn("python -m scripts.m5_benchmark_contract_gate", m5)
        self.assertIn("python -m scripts.m5_synthetic_recovery --restore", m5)
        self.assertIn("test_m5_benchmark_contract_gate.py", m5)
        self.assertIn("test_m5_synthetic_recovery.py", m5)
        self.assertIn("retention-days: 7", m5)
        self.assertIn("github.event_name != 'pull_request'", m5)
        self.assertIn("test ! -d customer_data", m5)


if __name__ == "__main__":
    unittest.main()
