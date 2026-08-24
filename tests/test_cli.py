"""Subprocess smoke tests for documented module and environment workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from company_os.cli import _terminal_text
from company_os.storage import CompanyStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src"
COMPANY_ENV_KEYS = {
    "COMPANY_OS_ACTOR",
    "COMPANY_OS_DB",
    "COMPANY_OS_DB_PATH",
    "COMPANY_OS_PAUSED",
    "COMPANY_OS_REPORT_DIR",
    "COMPANY_OS_REPO_ROOT",
}


class CompanyOSCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.root = Path(self.temp_directory.name)
        (self.root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
        self.database = self.root / "state" / "cli.db"

    def _environment(self, **updates: str) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in COMPANY_ENV_KEYS
        }
        existing_path = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(SOURCE_ROOT) + (
            os.pathsep + existing_path if existing_path else ""
        )
        environment.update(updates)
        return environment

    def _run(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
        use_common_options: bool = True,
        expected_code: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "company_os"]
        if use_common_options:
            command.extend(
                [
                    "--db",
                    str(self.database),
                    "--repo-root",
                    str(self.root),
                ]
            )
        command.extend(arguments)
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=environment or self._environment(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(
            expected_code,
            result.returncode,
            f"command failed: {command!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def test_documented_end_to_end_module_workflow(self) -> None:
        initialized = self._run("init")
        self.assertIn("Initialized", initialized.stdout)

        status = json.loads(self._run("status", "--json").stdout)
        self.assertTrue(status["paused"])
        self.assertEqual(0, status["counts"]["opportunities"])

        opportunity = json.loads(
            self._run(
                "opportunity",
                "add",
                "Example candidate",
                "--description",
                "Specific buyer pain",
                "--buyer",
                "Defined user",
                "--budget-holder",
                "Defined buyer",
                "--entry-wedge",
                "Small reversible test",
                "--json",
            ).stdout
        )
        opportunity_id = str(opportunity["id"])

        first_evidence = json.loads(
            self._run(
                "evidence",
                "add",
                opportunity_id,
                "--criterion",
                "need_severity",
                "--claim",
                "What was directly observed",
                "--source",
                "https://evidence.test/source-one",
                "--observed-at",
                "2026-08-24",
                "--expires-at",
                "2099-01-01",
                "--strength",
                "strong",
                "--rating",
                "0.8",
                "--confidence",
                "0.8",
                "--json",
            ).stdout
        )
        self.assertEqual(opportunity["id"], first_evidence["opportunity_id"])
        self._run(
            "evidence",
            "add",
            opportunity_id,
            "--criterion",
            "reachable_beachhead",
            "--claim",
            "A permission-based channel was identified",
            "--source",
            "https://evidence.test/source-two",
            "--observed-at",
            "2026-08-24",
            "--expires-at",
            "2099-01-01",
            "--strength",
            "moderate",
            "--rating",
            "0.6",
            "--confidence",
            "0.7",
            "--json",
        )

        scored = json.loads(
            self._run("score", opportunity_id, "--json").stdout
        )
        self.assertGreater(scored["final_score"], 0)
        self.assertIn("result", scored)

        requested = json.loads(
            self._run(
                "approval",
                "request",
                "--action",
                "Exact external action",
                "--rationale",
                "Evidence-based reason",
                "--risk",
                "Primary risk",
                "--estimated-cost-cents",
                "0",
                "--class",
                "ceo_approval_required",
                "--expires-at",
                "2099-01-01",
                "--json",
            ).stdout
        )
        self.assertEqual("pending", requested["status"])
        approvals = json.loads(
            self._run("approval", "list", "--status", "pending", "--json").stdout
        )
        self.assertEqual([requested["id"]], [row["id"] for row in approvals])

        report_path = self.root / "reports" / "ceo.md"
        self._run(
            "report",
            "--output",
            str(report_path),
            "--title",
            "CLI Smoke Report",
        )
        report = report_path.read_text(encoding="utf-8")
        self.assertIn("# CLI Smoke Report", report)
        self.assertIn("Example candidate", report)
        self.assertIn("Exact external action", report)

        final_status = json.loads(self._run("status", "--json").stdout)
        self.assertEqual(1, final_status["counts"]["opportunities"])
        self.assertEqual(2, final_status["counts"]["evidence"])
        self.assertEqual(1, final_status["pending_approvals"])

    def test_invalid_cli_operation_returns_domain_error_code(self) -> None:
        result = self._run(
            "opportunity",
            "show",
            "does-not-exist",
            expected_code=2,
        )
        self.assertIn("error: opportunity not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_cannot_create_an_opportunity_at_an_advanced_status(self) -> None:
        result = self._run(
            "opportunity",
            "add",
            "Creation bypass",
            "--status",
            "launched",
            expected_code=2,
        )
        self.assertIn("invalid choice", result.stderr)
        self.assertIn("--status", result.stderr)

    def test_terminal_text_neutralizes_control_sequences(self) -> None:
        self.assertEqual("safe\\x1b[2Jtext", _terminal_text("safe\x1b[2Jtext"))

    def test_documented_environment_variables_control_paths_actor_and_report(self) -> None:
        environment_db = self.root / "env-state" / "company.db"
        report_directory = self.root / "env-reports"
        environment = self._environment(
            COMPANY_OS_DB_PATH=str(environment_db),
            COMPANY_OS_REPO_ROOT=str(self.root),
            COMPANY_OS_ACTOR="environment-test-operator",
            COMPANY_OS_REPORT_DIR=str(report_directory),
            COMPANY_OS_PAUSED="1",
        )

        self._run("init", environment=environment, use_common_options=False)
        opportunity = json.loads(
            self._run(
                "opportunity",
                "add",
                "Environment configured candidate",
                "--json",
                environment=environment,
                use_common_options=False,
            ).stdout
        )
        status = json.loads(
            self._run(
                "status",
                "--json",
                environment=environment,
                use_common_options=False,
            ).stdout
        )
        self.assertEqual(str(environment_db), status["database"])
        self.assertTrue(status["paused"])

        self._run("report", environment=environment, use_common_options=False)
        self.assertTrue((report_directory / "ceo-report.md").is_file())

        store = CompanyStore(environment_db)
        self.addCleanup(store.close)
        event = next(
            item
            for item in store.list_audit_events()
            if item["event_type"] == "opportunity.created"
            and item["entity_id"] == str(opportunity["id"])
        )
        self.assertEqual("environment-test-operator", event["actor"])

        example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        for variable in (
            "COMPANY_OS_DB_PATH",
            "COMPANY_OS_REPO_ROOT",
            "COMPANY_OS_ACTOR",
            "COMPANY_OS_REPORT_DIR",
            "COMPANY_OS_PAUSED",
        ):
            self.assertIn(variable, example)
        self.assertIn("does not auto-load .env", example)


if __name__ == "__main__":
    unittest.main()
