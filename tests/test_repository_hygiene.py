"""Repository-level checks that run without third-party dependencies."""

from __future__ import annotations

import fnmatch
import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def repository_files() -> list[Path]:
    """Return tracked and non-ignored working files, including before commit one."""

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    relative_paths = [
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    ]
    return relative_paths


class RepositoryHygieneTests(unittest.TestCase):
    def test_pause_marker_is_present_and_explains_scope(self) -> None:
        marker = REPO_ROOT / "PAUSE_AUTONOMY"
        self.assertTrue(marker.is_file(), "PAUSE_AUTONOMY must ship enabled")
        text = marker.read_text(encoding="utf-8").lower()
        for required in ("external", "scheduled", "safe internal", "approval"):
            self.assertIn(required, text)

    def test_required_sensitive_patterns_are_ignored(self) -> None:
        ignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for required in (
            ".env",
            "state/*",
            "*.db",
            "reports/private/",
            "reports/generated/",
            "evidence/raw/",
            "*.pem",
            "*.key",
        ):
            self.assertIn(required, ignore_text)

    def test_ci_is_least_privilege_pinned_and_paused(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s+[A-Za-z_-]+:\s+write\s*$")
        self.assertIn('COMPANY_OS_PAUSED: "1"', workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("schedule:", workflow)

        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow)
        self.assertGreaterEqual(len(uses), 2)
        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_no_runtime_state_or_obvious_secret_file_is_tracked(self) -> None:
        forbidden_patterns = (
            ".env",
            ".env.*",
            "*.db",
            "*.db-*",
            "*.sqlite",
            "*.sqlite3",
            "*.pem",
            "*.key",
            "state/*",
            "reports/private/*",
            "reports/generated/*",
            "evidence/raw/*",
            "**/__pycache__/*",
            "*.pyc",
        )
        exceptions = {".env.example", "state/.gitkeep"}
        violations: list[str] = []
        for path in repository_files():
            normalized = path.as_posix()
            if normalized in exceptions:
                continue
            if any(fnmatch.fnmatch(normalized, pattern) for pattern in forbidden_patterns):
                violations.append(normalized)
        self.assertEqual([], violations, f"sensitive/runtime files present: {violations}")

    def test_no_common_live_secret_shape_in_text_files(self) -> None:
        patterns = {
            "OpenAI API key": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
            "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
            "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
            "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        }
        violations: list[str] = []
        for relative_path in repository_files():
            path = REPO_ROOT / relative_path
            try:
                data = path.read_bytes()
            except OSError as exc:
                self.fail(f"could not inspect {relative_path.as_posix()}: {exc}")
            if b"\0" in data:
                continue
            for label, pattern in patterns.items():
                if pattern.search(data):
                    violations.append(f"{relative_path.as_posix()} ({label})")
        self.assertEqual([], violations, f"possible live secrets found: {violations}")


if __name__ == "__main__":
    unittest.main()
