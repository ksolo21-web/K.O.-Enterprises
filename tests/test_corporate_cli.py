"""Subprocess coverage for the corporate and autonomous CLI surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src"


class CorporateCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.root = Path(self.temp_directory.name)
        (self.root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
        self.database = self.root / "state" / "corporation.db"
        self.environment = dict(os.environ)
        self.environment["PYTHONPATH"] = str(SOURCE_ROOT)

    def _run(self, *arguments: str, expected_code: int = 0) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-m",
            "company_os",
            "--db",
            str(self.database),
            "--repo-root",
            str(self.root),
            *arguments,
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            expected_code,
            result.returncode,
            f"command failed: {command!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def test_bootstrap_org_status_and_internal_cycle(self) -> None:
        bootstrap = json.loads(self._run("corporation", "bootstrap", "--json").stdout)
        self.assertEqual(12, bootstrap["departments"])
        self.assertEqual(28, bootstrap["roles"])
        self.assertEqual(28, bootstrap["workers"])

        organization = json.loads(self._run("org", "show", "--json").stdout)
        self.assertEqual(28, len(organization["roles"]))
        self.assertIn(
            "kaleb_ceo", {worker["worker_key"] for worker in organization["workers"]}
        )

        cycle = json.loads(
            self._run("cycle", "run", "--mode", "internal", "--json").stdout
        )
        self.assertEqual("awaiting_workers", cycle["cycle"]["status"])
        self.assertEqual(0, cycle["summary"]["external_effects_executed"])
        self.assertEqual("succeeded", cycle["summary"]["integrity_check_status"])

        status = json.loads(self._run("corporation", "status", "--json").stdout)
        self.assertTrue(status["paused"])
        self.assertEqual(3, status["operations"]["active_objectives"])

        active = json.loads(
            self._run("objective", "list", "--status", "active", "--json").stdout
        )
        self.assertEqual(3, len(active))
        objective = json.loads(
            self._run(
                "objective",
                "show",
                "company.validate-first-demand",
                "--json",
            ).stdout
        )
        self.assertEqual(1, len(objective["key_results"]))
        self.assertEqual(
            "decision-grade-validation", objective["key_results"][0]["result_key"]
        )

    def test_scheduled_cycle_fails_closed_while_paused(self) -> None:
        result = self._run(
            "cycle", "run", "--scheduled", "--json", expected_code=2
        )
        self.assertIn("PAUSE_AUTONOMY is active", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_management_escalation_can_be_routed_through_cli(self) -> None:
        self._run("corporation", "bootstrap")
        row = json.loads(
            self._run(
                "escalation",
                "add",
                "--raised-by",
                "software_engineer",
                "--routed-to",
                "product_technology_chief",
                "--decision-class",
                "department_operation",
                "--reason-code",
                "scope_conflict",
                "--title",
                "Clarify the bounded scope",
                "--context",
                "Two acceptance clauses conflict.",
                "--recommendation",
                "Use the safer narrower clause.",
                "--safe-default",
                "Hold only the conflicting task.",
                "--json",
            ).stdout
        )
        self.assertEqual("product_technology_chief", row["routed_to_role_key"])
        self.assertEqual(0, row["owner_attention"])

    def test_complete_work_lifecycle_through_cli(self) -> None:
        self._run("corporation", "bootstrap")
        objective = json.loads(
            self._run(
                "objective",
                "add",
                "--key",
                "cli.product-quality",
                "--title",
                "Verify the product work lifecycle",
                "--owner-role",
                "product_technology_chief",
                "--json",
            ).stdout
        )
        created = json.loads(
            self._run(
                "work",
                "add",
                "--key",
                "cli.software-change",
                "--assigned-role",
                "software_engineer",
                "--assigned-worker",
                "software_engineer",
                "--reviewer-role",
                "product_technology_chief",
                "--task-type",
                "software_change",
                "--title",
                "CLI work lifecycle",
                "--description",
                "Exercise durable work commands.",
                "--acceptance-criteria",
                "Independent reviewer accepts structured result.",
                "--objective-id",
                str(objective["id"]),
                "--input-json",
                '{"scope":"test"}',
                "--json",
            ).stdout
        )
        claimed = json.loads(
            self._run(
                "work", "claim", "--worker", "software_engineer", "--json"
            ).stdout
        )
        self.assertEqual(created["id"], claimed["id"])
        started = json.loads(
            self._run(
                "work",
                "start",
                str(created["id"]),
                "--worker",
                "software_engineer",
                "--lease-token",
                claimed["lease_token"],
                "--lease-epoch",
                str(claimed["lease_epoch"]),
                "--json",
            ).stdout
        )
        submitted = json.loads(
            self._run(
                "work",
                "submit",
                str(created["id"]),
                "--worker",
                "software_engineer",
                "--lease-token",
                started["lease_token"],
                "--lease-epoch",
                str(started["lease_epoch"]),
                "--result-json",
                '{"artifact":"test","tests":"passed"}',
                "--json",
            ).stdout
        )
        self.assertEqual("review", submitted["status"])
        accepted = json.loads(
            self._run(
                "work",
                "review",
                str(created["id"]),
                "--reviewer",
                "product_technology_chief",
                "--decision",
                "accept",
                "--notes",
                "Acceptance evidence verified.",
                "--quality-score",
                "1",
                "--json",
            ).stdout
        )
        self.assertEqual("succeeded", accepted["status"])

    def test_invalid_work_json_returns_domain_error_without_traceback(self) -> None:
        self._run("corporation", "bootstrap")
        result = self._run(
            "work",
            "add",
            "--key",
            "cli.invalid-json",
            "--assigned-role",
            "software_engineer",
            "--reviewer-role",
            "product_technology_chief",
            "--task-type",
            "software_change",
            "--title",
            "Invalid input",
            "--description",
            "Invalid JSON must fail safely.",
            "--acceptance-criteria",
            "No traceback.",
            "--objective-id",
            "1",
            "--input-json",
            "not-json",
            expected_code=2,
        )
        self.assertIn("input_json must be valid JSON", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
