"""M5 V8: bounded synthetic engineering QA receipt tied to Git checkout and ZIP.

A run-local reproducibility receipt, NOT a cryptographic signature, repository
branch rule, real-source attestation, independent code review or field approval.
All inputs are public synthetic test fixtures. No customer data or model use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.m5_benchmark_contract_gate import run_matrix
from scripts.m5_release_quality_gate import (
    ROOT, MANIFEST as FIXTURE_MANIFEST, BASELINE_FILE, verify_versioned_examples,
)
from scripts.m5_safety_change_gate import (
    MANIFEST as SAFETY_MANIFEST, verify_safety_change_registry,
)
from scripts.m5_synthetic_recovery import (
    _json, _outside_checkout, verify_synthetic_bundle,
)

SCENARIOS = (
    "all_declared_matches",
    "one_false_alarm_above_precision_floor",
    "five_false_alarms",
    "one_missing_critical",
    "one_missing_major",
    "ninety_nine_cases",
    "missing_moderate_is_reported",
    "nine_clean_controls",
    "training_family_overlap",
)
SOURCE_FILES = (
    FIXTURE_MANIFEST, BASELINE_FILE, SAFETY_MANIFEST,
)
REPO_NAME = "ksolo21-web/K.O.-Enterprises"
SHA_PATTERN = re.compile(r"[a-f0-9]{40}\Z")
RUN_PATTERN = re.compile(r"[1-9][0-9]{0,17}\Z")
ALLOWED_EVENTS = frozenset(("push", "pull_request", "workflow_dispatch"))
MAX_RECEIPT = 32_000


class EvidenceBlock(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root.parents[1], capture_output=True, text=True,
            check=True, timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise EvidenceBlock("Git checkout identity could not be determined") from exc
    return result.stdout.strip()


def _source_sha256(root: Path) -> dict:
    result = {}
    for name in SOURCE_FILES:
        file = root / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 40_000:
            raise EvidenceBlock("Source manifest absent, symlinked or oversized")
        result[name] = _sha256(file.read_bytes())
    return result


def expected_receipt(archive: Path, *, commit: str, event: str,
                     run_id: str, root: Path = ROOT) -> dict:
    """Recheck the actual ZIP and code contracts each time; no cached claims."""
    root = Path(root).resolve(strict=True)
    if not isinstance(commit, str) or not SHA_PATTERN.fullmatch(commit):
        raise EvidenceBlock("Full Git commit SHA required")
    if commit != _git_head(root):
        raise EvidenceBlock("Receipt commit differs from current checked-out Git HEAD")
    if event not in ALLOWED_EVENTS:
        raise EvidenceBlock("Unsupported CI event")
    if not isinstance(run_id, str) or not RUN_PATTERN.fullmatch(run_id):
        raise EvidenceBlock("Positive numeric GitHub run ID required")
    archive = _outside_checkout(Path(archive))
    if not archive.is_file() or archive.is_symlink():
        raise EvidenceBlock("Missing separate synthetic recovery archive")
    if not 1 <= archive.stat().st_size <= 24_000_000:
        raise EvidenceBlock("Synthetic recovery archive size invalid")
    safety = verify_safety_change_registry(root=root)
    examples = verify_versioned_examples(root=root)
    recovered = verify_synthetic_bundle(archive, root=root)
    contract = run_matrix()
    if (safety.get("checked_critical_sources") != 10
            or safety.get("root_pause_marker_matches_pin") is not True
            or safety.get("customer_release_allowed") is not False):
        raise EvidenceBlock("Protected source checks incomplete")
    if examples.get("pinned_source_files") != 4:
        raise EvidenceBlock("Synthetic source inventory incomplete")
    if (recovered.get("archive_members_checked") != 5
            or recovered.get("rendered_pages_reverified") != 16
            or recovered.get("page_fingerprint_matches_pinned_baseline") is not True
            or recovered.get("customer_release_allowed") is not False):
        raise EvidenceBlock("Recovery fingerprint, page count or permission mismatch")
    if (contract.get("synthetic_scenarios_checked") != len(SCENARIOS)
            or contract.get("scenario_names") != list(SCENARIOS)
            or contract.get("invented_cases") != 100
            or contract.get("invented_defect_labels") != 90
            or contract.get("invented_critical_labels") != 30
            or contract.get("invented_clean_control_cases") != 10
            or contract.get("systems_covered") != 13
            or contract.get("scopes") != ["commercial", "residential"]
            or contract.get("actual_accuracy_verified") is not False
            or contract.get("model_inference_run") is not False
            or contract.get("customer_release_allowed") is not False):
        raise EvidenceBlock("Synthetic benchmark matrix incomplete or misrepresented")
    baseline_file = root / BASELINE_FILE
    baseline = _json(baseline_file.read_bytes())
    if (baseline.get("expected_pages") != 16
            or baseline.get("customer_release_allowed") is not False):
        raise EvidenceBlock("Expected source-controlled report baseline invalid")
    return {
        "schema_version": 1,
        "status": "M5_SYNTHETIC_ENGINEERING_EVIDENCE_ONLY",
        "repository": REPO_NAME,
        "git_checkout_sha": commit,
        "ci_event_declared": event,
        "ci_run_id_declared": run_id,
        "synthetic_archive_sha256": _sha256(archive.read_bytes()),
        "pinned_repository_sources_sha256": _source_sha256(root),
        "rendered_pdf_pages": 16,
        "pinned_pdf_visual_and_text_fingerprint": baseline["expected_visual_and_text_fingerprint"],
        "verified_archive_member_count": 5,
        "verified_protected_safety_sources": 10,
        "verified_versioned_synthetic_files": 4,
        "invented_evaluation_cases": 100,
        "invented_adjudicated_labels": 90,
        "invented_critical_labels": 30,
        "invented_clean_control_cases": 10,
        "covered_inspection_systems": 13,
        "synthetic_scenario_names": list(SCENARIOS),
        "synthetic_scenario_count": len(SCENARIOS),
        "source_evidence_is_real": False,
        "real_case_inspector_credentials_verified": False,
        "independent_repo_review_verified": False,
        "branch_protection_verified": False,
        "real_model_detection_accuracy_verified": False,
        "authentic_professional_holdout_verified": False,
        "field_pilot_authorized": False,
        "customer_release_allowed": False,
        "signed_by_independent_authority": False,
        "note": "Local GitHub-run declaration and replay; no external attestation.",
    }


def _encode(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def verify_receipt(path: Path, archive: Path, *, commit: str, event: str,
                   run_id: str, root: Path = ROOT) -> dict:
    path = _outside_checkout(Path(path))
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_RECEIPT:
        raise EvidenceBlock("Receipt missing, symlinked or oversized")
    observed = _json(path.read_bytes())
    if not isinstance(observed, dict):
        raise EvidenceBlock("Receipt must be a JSON object")
    expected = expected_receipt(
        archive, commit=commit, event=event, run_id=run_id, root=root)
    if observed != expected or path.read_bytes() != _encode(expected):
        raise EvidenceBlock("Evidence receipt differs from actual replayed synthetic checks")
    return {
        "status": "M5_SYNTHETIC_EVIDENCE_RECEIPT_VERIFIED_ONLY",
        "git_checkout_sha": commit,
        "synthetic_scenarios_checked": len(SCENARIOS),
        "synthetic_pdf_pages": 16,
        "archive_sha256_matches": True,
        "independent_repo_review_verified": False,
        "real_model_accuracy_verified": False,
        "customer_release_allowed": False,
    }


def create_receipt(path: Path, archive: Path, *, commit: str, event: str,
                   run_id: str, root: Path = ROOT) -> dict:
    path = _outside_checkout(Path(path))
    if path.exists() or not path.parent.is_dir():
        raise EvidenceBlock("Receipt must be new in existing non-Git directory")
    payload = expected_receipt(
        archive, commit=commit, event=event, run_id=run_id, root=root)
    encoded = _encode(payload)
    if len(encoded) > MAX_RECEIPT:
        raise EvidenceBlock("Evidence receipt exceeds size budget")
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
        return verify_receipt(path, archive, commit=commit, event=event,
                              run_id=run_id, root=root)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="M5 V8 public synthetic CI evidence ledger")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create", type=Path)
    modes.add_argument("--verify", type=Path)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.create is not None:
            result = create_receipt(args.create, args.archive, commit=args.commit,
                                    event=args.event, run_id=args.run_id)
        else:
            result = verify_receipt(args.verify, args.archive, commit=args.commit,
                                    event=args.event, run_id=args.run_id)
    except (EvidenceBlock, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({
            "status": "M5_SYNTHETIC_ENGINEERING_EVIDENCE_BLOCKED",
            "reason": str(exc), "customer_release_allowed": False,
        }))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
