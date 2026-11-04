"""M5 V7 PR workflow security: read-only, unfiltered required checks.

Static protections for the current GitHub Actions configs. This detects
configuration drift; it does NOT install branch rules or verify reviewer
independence. An actual PR red/green rehearsal provides separate CI evidence.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
M3 = REPO / ".github/workflows/home-inspection-m3-v8-offline.yml"
M5 = REPO / ".github/workflows/home-inspection-m5-quality.yml"


def trigger_sections(workflow: str):
    """Parse our intentionally simple YAML event declarations without dependencies."""
    events = workflow.split("\non:\n", 1)
    if len(events) != 2 or "  workflow_dispatch:" not in events[1]:
        raise ValueError("Expected explicit GitHub events")
    events = events[1].split("  workflow_dispatch:", 1)[0]
    if "  push:\n" not in events or "  pull_request:\n" not in events:
        raise ValueError("Required push and pull request trigger missing")
    push = events.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
    pull = events.split("  pull_request:\n", 1)[1]
    return push, pull


def verify_premerge_triggers(workflow: str, name: str) -> bool:
    """Never path-filter PR checks that must become required status checks."""
    push, pull = trigger_sections(workflow)
    if "    branches: [home-inspection-development]" not in push:
        raise ValueError("Missing development push trigger")
    if "    paths:\n      - 'ventures/home-inspection/**'" not in push:
        raise ValueError("Inspection-only push optimization changed")
    if f"      - '.github/workflows/{name}'" not in push:
        raise ValueError("Workflow self-change push trigger missing")
    if pull.strip() != "branches: [home-inspection-development]":
        raise ValueError("Pull requests must be unfiltered and only target development")
    return True


class WorkflowPremergeGuards(unittest.TestCase):
    def test_both_workflows_always_run_for_prs_to_inspection_dev(self):
        for path in (M3, M5):
            with self.subTest(workflow=path.name):
                s = path.read_text(encoding="utf-8")
                self.assertTrue(verify_premerge_triggers(s, path.name))
                self.assertNotIn("pull_request_target:", s)
                self.assertNotIn("branches: [main]", s)

    def test_path_filtered_pr_regression_is_rejected(self):
        for path in (M3, M5):
            with self.subTest(workflow=path.name):
                s = path.read_text(encoding="utf-8")
                changed = s.replace(
                    "  pull_request:\n    branches: [home-inspection-development]\n",
                    "  pull_request:\n    branches: [home-inspection-development]\n"
                    "    paths:\n      - 'ventures/home-inspection/**'\n")
                self.assertNotEqual(s, changed)
                with self.assertRaisesRegex(ValueError, "unfiltered"):
                    verify_premerge_triggers(changed, path.name)

    def test_wrong_pr_target_is_rejected(self):
        for path in (M3, M5):
            s = path.read_text(encoding="utf-8")
            wrong = s.replace(
                "  pull_request:\n    branches: [home-inspection-development]\n",
                "  pull_request:\n    branches: [main]\n")
            self.assertNotEqual(s, wrong)
            with self.assertRaisesRegex(ValueError, "unfiltered"):
                verify_premerge_triggers(wrong, path.name)

    def test_both_premerge_jobs_use_read_only_token_and_ephemeral_checkout(self):
        for path in (M3, M5):
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
