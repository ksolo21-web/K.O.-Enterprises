"""M5 V4 — offline detection of unreviewed changes to inspection safety sources.

Pins Git blob IDs for safety-critical modules and PAUSE_AUTONOMY. A matching
repository-controlled pin is NOT an external signature, verified independent
review, branch protection, or permission to release a customer report.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "examples/m5_safety_contract_registry_v1.json"
PROTECTED_PATHS = (
    "inspection_engine/serious_defect_benchmark.py",
    "inspection_engine/m4_frozen_safety_audit.py",
    "inspection_engine/m4_media_grounding.py",
    "inspection_engine/m4_source_byte_custody.py",
    "inspection_engine/m4_credential_gate.py",
    "inspection_engine/m4_human_review.py",
    "inspection_engine/m4_governance_history.py",
    "inspection_engine/m4_issuer_receipts.py",
    "inspection_engine/m4_workflow.py",
    "inspection_engine/m4_pipeline.py",
)
PAUSE_SHA1 = "37455fd13813683bb0169d36cb24b86a07094aa7"
SHA1 = re.compile(r"[0-9a-f]{40}\Z")


class GovernanceBlock(ValueError):
    pass


def _reject_duplicate_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GovernanceBlock("Duplicate change-control registry field")
        result[key] = value
    return result


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") +
                        b"\x00" + data).hexdigest()


def _bounded_regular(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise GovernanceBlock("Symlinked protected source is not accepted")
    try:
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode) or not 1 <= details.st_size <= limit:
            raise GovernanceBlock("Missing, nonregular or oversized protected source")
        raw = path.read_bytes()
    except OSError as exc:
        raise GovernanceBlock("Protected source unreadable") from exc
    if len(raw) != details.st_size or len(raw) > limit:
        raise GovernanceBlock("Protected source changed during read")
    return raw


def _strict_manifest(path: Path):
    try:
        return json.loads(_bounded_regular(path, 25_000).decode("utf-8"),
                          object_pairs_hook=_reject_duplicate_json,
                          parse_constant=lambda v: (_ for _ in ()).throw(
                              GovernanceBlock("Invalid registry constant")))
    except GovernanceBlock:
        raise
    except (UnicodeError, ValueError, TypeError) as exc:
        raise GovernanceBlock("Invalid JSON safety-change registry") from exc


def verify_safety_change_registry(root: Path = ROOT, *, repo_root: Path | None = None) -> dict:
    """Verify exact declared sources without executing them or modifying Git."""
    root = Path(root).resolve(strict=True)
    repo = Path(repo_root).resolve(strict=True) if repo_root else root.parents[1]
    manifest = _strict_manifest(root / MANIFEST)
    if (not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "registry_type", "required_branch",
            "root_pause_autonomy_blob_sha1", "customer_release_allowed", "files"}
            or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] != 1
            or manifest["registry_type"] != "M5_SAFETY_CHANGE_DETECTION_ONLY"
            or manifest["required_branch"] != "home-inspection-development"
            or manifest["customer_release_allowed"] is not False
            or manifest["root_pause_autonomy_blob_sha1"] != PAUSE_SHA1):
        raise GovernanceBlock("Unsafe safety-change registry header")
    rows = manifest["files"]
    if not isinstance(rows, list) or len(rows) != len(PROTECTED_PATHS):
        raise GovernanceBlock("Incomplete required safety-source inventory")
    for i, row in enumerate(rows):
        if (not isinstance(row, dict) or set(row) != {"path", "git_blob_sha1"}
                or row["path"] != PROTECTED_PATHS[i]
                or not isinstance(row["git_blob_sha1"], str)
                or not SHA1.fullmatch(row["git_blob_sha1"])):
            raise GovernanceBlock("Missing, reordered or invalid protected safety source")
        actual = _git_blob(_bounded_regular(root / row["path"], 2_000_000))
        if actual != row["git_blob_sha1"]:
            raise GovernanceBlock("Protected safety source changed without registry update: " +
                                  row["path"])
    pause_path = repo / "PAUSE_AUTONOMY"
    if _git_blob(_bounded_regular(pause_path, 10_000)) != PAUSE_SHA1:
        raise GovernanceBlock("Root autonomy pause marker changed or removed")
    return {
        "schema_version": 1,
        "status": "LOCAL_SAFETY_SOURCE_CHANGE_DETECTION_ONLY",
        "registry_type": manifest["registry_type"],
        "checked_critical_sources": len(PROTECTED_PATHS),
        "root_pause_marker_matches_pin": True,
        "external_peer_review_enforced": False,
        "github_branch_protection_verified": False,
        "qualified_inspector_authorized": False,
        "customer_release_allowed": False,
    }


def main() -> int:
    try:
        result = verify_safety_change_registry()
    except (GovernanceBlock, OSError, ValueError) as exc:
        print(json.dumps({"status": "M5_CHANGE_GOVERNANCE_BLOCKED", "reason": str(exc),
                          "customer_release_allowed": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
