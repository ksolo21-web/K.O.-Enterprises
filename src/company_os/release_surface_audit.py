"""CE-4C: deterministic, non-authorizing release execution-surface inventory.

Inventory source files and common outbound-effect indicators to assist a
GGENUINELY separate critic. Never certify complete external/connector coverage.
No network, secret reading, deployment, scheduling, email or release actions.
Requires PAUSE_AUTONOMY + hard production-release lock in the source tree.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .source_provenance import EvidenceError

SCAN_AREAS = ("src", "products", "scripts", ".github/workflows")
SOURCE_EXTENSIONS = frozenset({
    ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".sh", ".bash", ".yml", ".yaml",
})
MAX_FILES = 4000
MAX_FILE_BYTES = 2_000_000
MAX_HITS_PER_FILE = 80
SIGNALS: tuple[tuple[str, str], ...] = (
    ("http_mutation", r"\b(?:requests|httpx)\.(?:post|put|patch|delete)\s*\("),
    ("http_generic", r"\b(?:requests|httpx)\.(?:request|get)\s*\("),
    ("raw_http", r"\b(?:http\.client|urllib\.request|urllib3|aiohttp)\b"),
    ("raw_socket", r"\bsocket\.(?:socket|create_connection)\s*\("),
    ("email_or_messaging", r"\b(?:smtplib|sendgrid|mailgun|twilio|postmark|smtp)\b"),
    ("payment_or_checkout", r"\b(?:stripe|paypal|squareup|checkout_session|payment_intent)\b"),
    ("shell_execution", r"\b(?:subprocess\.(?:Popen|run|call)|os\.system|os\.exec)\s*\("),
    ("remote_deployment", r"\b(?:kubectl|terraform|gh\s+release|docker\s+push|npm\s+publish|git\s+push|gcloud\s+run|aws\s+ecs)\b"),
    ("workflow_action", r"(?m)^\s*uses\s*:\s*[^#\n]+"),
    ("workflow_shell", r"(?m)^\s*run\s*:\s*[^#\n]+"),
)
_COMPILED = tuple((name, re.compile(expr, re.IGNORECASE)) for name, expr in SIGNALS)


def _root_safety_contract(repo_root: Path) -> dict[str, bool]:
    paused = (repo_root / "PAUSE_AUTONOMY").is_file()
    lock_path = repo_root / "src" / "company_os" / "competitive_launch_guard.py"
    exact_false = False
    if lock_path.is_file() and not lock_path.is_symlink():
        tree = ast.parse(lock_path.read_text(encoding="utf-8"))
        values = [
            node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and any(isinstance(target, ast.Name)
                    and target.id == "PRODUCTION_RELEASE_CONTROLLER_CERTIFIED"
                    for target in node.targets)
        ]
        exact_false = values == [False]
    return {
        "root_emergency_pause_present": paused,
        "production_release_hard_lock_is_false": exact_false,
    }


def _collect_paths(repo_root: Path) -> list[Path]:
    collected: list[Path] = []
    for area in SCAN_AREAS:
        directory = repo_root / area
        if not directory.exists():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise EvidenceError("code inventory area must be a real directory: " + area)
        for location, folders, files in os.walk(directory, topdown=True, followlinks=False):
            base = Path(location)
            for folder in folders:
                if (base / folder).is_symlink():
                    raise EvidenceError("inventory must not traverse linked source directories")
            folders[:] = [f for f in sorted(folders)
                          if f not in {"__pycache__", "node_modules", "venv", ".venv",
                                       "dist", "build", ".git", ".cache"}]
            for name in sorted(files):
                source = base / name
                if source.suffix not in SOURCE_EXTENSIONS:
                    continue
                if source.is_symlink() or not source.is_file():
                    raise EvidenceError("linked or nonregular source file in execution inventory")
                if not source.resolve().is_relative_to(repo_root):
                    raise EvidenceError("execution source escaped repository root")
                collected.append(source)
                if len(collected) > MAX_FILES:
                    raise EvidenceError("execution inventory maximum file count exceeded")
    return sorted(collected, key=lambda path: path.relative_to(repo_root).as_posix())


def audit_release_surfaces(repo_root: Path | str) -> dict[str, Any]:
    """Return a conservative review inventory; ALWAYS release_authorized=False."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("execution inventory repository root is unavailable")
    safety = _root_safety_contract(root)
    candidates: list[dict[str, Any]] = []
    manifest: list[tuple[str, str]] = []
    total_signals = 0
    for path in _collect_paths(root):
        if path.stat().st_size > MAX_FILE_BYTES:
            raise EvidenceError("source file too large for bounded execution audit")
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise EvidenceError("source file changed during inventory scan")
        digest = hashlib.sha256(raw).hexdigest()
        relative = path.relative_to(root).as_posix()
        manifest.append((relative, digest))
        try:
            content = raw.decode("utf-8")
        except UnicodeError as exc:
            raise EvidenceError("source file not valid UTF-8") from exc
        matches: list[dict[str, Any]] = []
        for label, pattern in _COMPILED:
            for match in pattern.finditer(content):
                line_no = content.count("\n", 0, match.start()) + 1
                matches.append({"indicator": label, "line": line_no})
                if len(matches) > MAX_HITS_PER_FILE:
                    raise EvidenceError("source side-effect signals exceed bounded review cap")
        if matches:
            matches.sort(key=lambda m: (m["line"], m["indicator"]))
            candidates.append({
                "path": relative, "content_sha256": digest,
                "indicators": matches,
                "policy_call_text_present": (
                    "enforce_action(" in content or "evaluate_action(" in content
                    or "inspect_release_proposal(" in content
                ),
                "disposition": "MANUAL_EXECUTOR_BOUNDARY_REVIEW_REQUIRED",
            })
            total_signals += len(matches)

    digest_manifest = hashlib.sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()

    # This is intentionally *not* a PASS criterion. A static scan cannot
    # discover every plugin, external SaaS integration or out-of-repo flow.
    safe_flags = all(safety.values())
    return {
        "status": ("BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW" if safe_flags
                   else "BLOCK_SAFETY_CONTRACT_VIOLATION"),
        "scope": "repository_local_static_inventory_only",
        "scanned_source_files": len(manifest),
        "potential_execution_files": len(candidates),
        "potential_execution_indicators": total_signals,
        "inventory_sha256": digest_manifest,
        "root_safety": safety,
        "candidates": candidates,
        "out_of_repository_connectors_verified": False,
        "protected_host_release_boundaries_verified": False,
        "production_branch_ruleset_verified": False,
        "independent_review_completed": False,
        "release_authorized": False,
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded internal release surface inventory")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expect-not-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit_release_surfaces(args.repo_root)
    except (EvidenceError, OSError, ValueError, SyntaxError) as exc:
        print(json.dumps({
            "status": "BLOCK_SCAN_FAILED", "reason": str(exc)[:200],
            "release_authorized": False,
        }))
        return 2
    # Only aggregate counts, root safety and digest go to public CI logs.
    summary = {key: report[key] for key in (
        "status", "scanned_source_files", "potential_execution_files",
        "potential_execution_indicators", "inventory_sha256", "root_safety",
        "release_authorized",
    )}
    print(json.dumps(summary, sort_keys=True))
    if args.expect_not_ready:
        return 0 if report["status"] == "BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW" else 2
    return 1  # never return CLI success for production readiness


if __name__ == "__main__":
    raise SystemExit(main())
