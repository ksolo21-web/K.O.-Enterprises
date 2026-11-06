"""Adversarial static execution inventory; detection never means approval."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from company_os.release_surface_audit import (
    audit_release_surfaces, main,
)
from company_os.source_provenance import EvidenceError


class ReleaseSurfaceAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "PAUSE_AUTONOMY").write_text("intentionally paused\n")
        guard = self.root / "src" / "company_os" / "competitive_launch_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text("PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False\n")
        self.source = guard.parent / "prospect_sender.py"

    def inspect(self):
        return audit_release_surfaces(self.root)

    def test_detects_multiple_direct_external_effect_indicators(self):
        self.source.write_text(
            "import requests\nimport smtplib\n"
            "requests.post('https://example.invalid/publish')\n"
            "smtplib.SMTP('localhost')\n"
        )
        report = self.inspect()
        self.assertEqual(report["status"], "BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW")
        self.assertEqual(report["potential_execution_files"], 1)
        self.assertFalse(report["release_authorized"])
        candidate = report["candidates"][0]
        self.assertEqual(candidate["path"], "src/company_os/prospect_sender.py")
        self.assertFalse(candidate["policy_call_text_present"])
        indicators = {r["indicator"] for r in candidate["indicators"]}
        self.assertIn("http_mutation", indicators)
        self.assertIn("email_or_messaging", indicators)
        self.assertFalse(report["out_of_repository_connectors_verified"])

    def test_textual_policy_reference_is_not_treated_as_authorized(self):
        self.source.write_text(
            "# enforce_action(...) will eventually be integrated\n"
            "import requests\nrequests.post('https://example.invalid/')\n"
        )
        report = self.inspect()
        self.assertTrue(report["candidates"][0]["policy_call_text_present"])
        self.assertFalse(report["protected_host_release_boundaries_verified"])
        self.assertFalse(report["release_authorized"])

    def test_empty_source_inventory_still_blocks_approval(self):
        report = self.inspect()
        self.assertEqual(report["potential_execution_files"], 0)
        self.assertFalse(report["release_authorized"])
        self.assertEqual(report["status"], "BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW")

    def test_missing_root_emergency_pause_is_safety_failure(self):
        (self.root / "PAUSE_AUTONOMY").unlink()
        self.assertEqual(self.inspect()["status"], "BLOCK_SAFETY_CONTRACT_VIOLATION")

    def test_attempt_to_flip_release_controller_literal_fails_contract(self):
        guard = self.root / "src" / "company_os" / "competitive_launch_guard.py"
        guard.write_text("PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = True\n")
        report = self.inspect()
        self.assertFalse(report["root_safety"]["production_release_hard_lock_is_false"])
        self.assertEqual(report["status"], "BLOCK_SAFETY_CONTRACT_VIOLATION")

    def test_duplicate_false_assignment_is_safety_violation(self):
        guard = self.root / "src" / "company_os" / "competitive_launch_guard.py"
        guard.write_text(
            "PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False\n"
            "PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False\n"
        )
        self.assertEqual(self.inspect()["status"], "BLOCK_SAFETY_CONTRACT_VIOLATION")

    def test_source_file_symlink_refused_even_with_safe_target(self):
        other = self.root / "outside.py"
        other.write_text("import requests\nrequests.post('https://example.invalid')")
        self.source.symlink_to(other)
        with self.assertRaises(EvidenceError):
            self.inspect()

    def test_source_directory_symlink_refused(self):
        script_area = self.root / "scripts"
        script_area.symlink_to(self.root / "src", target_is_directory=True)
        with self.assertRaises(EvidenceError):
            self.inspect()

    def test_nontarget_secret_file_not_read_or_exposed(self):
        self.source.write_text("import smtplib\n")
        secret = self.root / "src" / "company_os" / "secret.env"
        secret.write_text("PASSWORD=A-PRIVATE-SENTINEL")
        payload = json.dumps(self.inspect())
        self.assertNotIn("A-PRIVATE-SENTINEL", payload)
        self.assertNotIn("secret.env", payload)

    def test_workflow_shell_and_external_action_are_inventory_candidates(self):
        workflow = self.root / ".github" / "workflows" / "release.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            "name: Unsafe example\njobs:\n  release:\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - run: git push\n"
        )
        report = self.inspect()
        rows = [r for r in report["candidates"] if r["path"].endswith("release.yml")]
        self.assertEqual(len(rows), 1)
        names = {r["indicator"] for r in rows[0]["indicators"]}
        self.assertIn("workflow_action", names)
        self.assertIn("workflow_shell", names)
        self.assertIn("remote_deployment", names)
        self.assertFalse(report["release_authorized"])

    def test_stable_input_inventory_has_deterministic_digest(self):
        self.source.write_text("import requests\n")
        first = self.inspect()
        second = self.inspect()
        self.assertEqual(first["inventory_sha256"], second["inventory_sha256"])
        self.source.write_text("import requests\n# source code changed\n")
        self.assertNotEqual(first["inventory_sha256"], self.inspect()["inventory_sha256"])

    def test_oversized_source_fails_closed(self):
        self.source.write_text("x" * 2_000_001)
        with self.assertRaises(EvidenceError):
            self.inspect()

    def test_failed_python_syntax_in_hardlock_fails_closed(self):
        guard = self.root / "src" / "company_os" / "competitive_launch_guard.py"
        guard.write_text("PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = (\n")
        with self.assertRaises(SyntaxError):
            self.inspect()

    def test_expect_not_ready_cli_is_internal_success_only(self):
        self.source.write_text("import smtplib\n")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            exit_code = main(["--repo-root", str(self.root), "--expect-not-ready"])
        self.assertEqual(exit_code, 0)
        printed = json.loads(output.getvalue())
        self.assertEqual(printed["status"], "BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW")
        self.assertFalse(printed["release_authorized"])
        self.assertNotIn("candidates", printed)

    def test_regular_cli_exit_cannot_be_misread_as_production_ready(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--repo-root", str(self.root)]), 1)

    def test_expect_not_ready_fails_if_emergency_marker_removed(self):
        (self.root / "PAUSE_AUTONOMY").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(["--repo-root", str(self.root), "--expect-not-ready"]), 2,
            )

    def test_root_gitignored_state_not_walked(self):
        state = self.root / "state" / "competitive_engine"
        state.mkdir(parents=True)
        (state / "sensitive.py").write_text(
            "import smtplib\nPASSWORD=A-PRIVATE-SENTINEL\n"
        )
        report = self.inspect()
        self.assertFalse(any("state/" in item["path"] for item in report["candidates"]))
        self.assertNotIn("PRIVATE-SENTINEL", json.dumps(report))

    def test_every_candidate_requires_manual_boundary_review(self):
        self.source.write_text(
            "import smtplib\nsmtplib.SMTP('example.invalid')\n"
        )
        record = self.inspect()["candidates"][0]
        self.assertEqual(
            record["disposition"], "MANUAL_EXECUTOR_BOUNDARY_REVIEW_REQUIRED",
        )

    def test_no_network_or_release_action_module_capability(self):
        import company_os.release_surface_audit as module
        self.assertFalse(hasattr(module, "send_message"))
        self.assertFalse(hasattr(module, "publish"))
        self.assertFalse(hasattr(module, "deploy"))
        self.assertFalse(hasattr(module, "authorize_release"))


if __name__ == "__main__":
    unittest.main()
