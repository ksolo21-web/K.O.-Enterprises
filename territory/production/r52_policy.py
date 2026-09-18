#!/usr/bin/env python3
"""Pinned R52 policy loader for the GitHub territory runtime.

The legacy 138-file source capsule remains immutable evidence.  R52 is loaded as
a separate exact-byte policy layer so the production runtime can advance without
rewriting the historical source capsule.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R52_ROOT = ROOT / "r52"
REVISION = "segment-role-whole-label-2026-09-13-r52"

REQUIRED = (
    "ACTIVE-SKILLS.json",
    "Territory-Map-Card-Builder-SKILL.md",
    "Territory-Card-Critic-SKILL.md",
    "Kaleb-Quality-Loop-SKILL.md",
    "Territory-Automatic-Execution-Contract.md",
    "New-Designed-Card-Family-Contract.md",
    "New-Designed-Visual-Regression-Standard.md",
    "Territory-Label-Completeness-Preflight-Contract.md",
    "Territory-PDF-Label-Metric-Contract.md",
    "Territory-Segment-Role-Whole-Label-Contract.md",
    "Territory-Source-Truth-Preflight-Contract.md",
    "Territory-Identity-Naming-Contract.md",
    "Locked-Template-Style-Token-Contract.md",
    "R52-FINAL-ACCEPTANCE.json",
    "R52-MANIFEST-SHA256.json",
    "scripts/validate_territory_activation.py",
    "scripts/validate_internal_reviewer_parity.py",
    "scripts/validate_label_navigation_contract.py",
    "scripts/validate_label_completeness_preflight.py",
    "scripts/validate_label_placement_contract.py",
    "scripts/validate_pdf_label_metrics.py",
    "scripts/validate_source_truth_preflight.py",
    "scripts/validate_new_designed_family.py",
    "scripts/validate_style_token_layer.py",
    "scripts/validate_territory_identity.py",
    "scripts/validate_pdf_identity.py",
    "scripts/render_locked_template.py",
    "scripts/territory_identity.py",
    "references/R48-Canonical-Style-Tokens.json",
)

class R52PolicyError(RuntimeError):
    pass

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _manifest_key(rel: str) -> str:
    return rel

def verify(root: Path | None = None) -> dict:
    root = Path(root or R52_ROOT).resolve()
    active_path = root / "ACTIVE-SKILLS.json"
    manifest_path = root / "R52-MANIFEST-SHA256.json"
    if not active_path.is_file() or not manifest_path.is_file():
        raise R52PolicyError("R52 policy files are missing")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    if active.get("revision") != REVISION:
        raise R52PolicyError("active territory policy is not R52")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("files")
    if not isinstance(expected, dict):
        raise R52PolicyError("R52 manifest is malformed")
    checked = {}
    source_hash_mismatches = {}
    source_unmanifested = []
    for rel in REQUIRED:
        path = root / rel
        key = _manifest_key(rel)
        if not path.is_file():
            raise R52PolicyError("missing R52 core file: " + rel)
        want = expected.get(key)
        got = sha(path)
        if not isinstance(want, str):
            source_unmanifested.append(rel)
        elif got != want:
            source_hash_mismatches[rel] = {"source_sha256": want, "deployed_sha256": got, "bytes": path.stat().st_size}
        checked[rel] = got
    deployment_manifest = root / "R52-GITHUB-DEPLOYMENT-MANIFEST.json"
    if not deployment_manifest.is_file():
        report = {k:{"deployed_sha256":v} for k,v in checked.items()}
        for k,v in source_hash_mismatches.items(): report[k].update(v)
        raise R52PolicyError("R52 GitHub deployment manifest missing; source_unmanifested=" + json.dumps(source_unmanifested) + "; deployed_hashes=" + json.dumps(report, sort_keys=True))
    deployed = json.loads(deployment_manifest.read_text(encoding="utf-8"))
    if deployed.get("source_package_sha256") != "193e82ee45cf9e4cfd355f0d0efdc5163b0fbf722cf9b95dcc7fc2bf57e8597e":
        raise R52PolicyError("deployment manifest is not bound to the saved R52 package")
    if deployed.get("revision") != REVISION:
        raise R52PolicyError("deployment manifest revision mismatch")
    if deployed.get("normalization") != "strip_single_final_lf_from_library_text_transport":
        raise R52PolicyError("unexpected R52 deployment normalization")
    hashes = deployed.get("files")
    if not isinstance(hashes, dict):
        raise R52PolicyError("deployment manifest file hashes missing")
    for rel, got in checked.items():
        if hashes.get(rel) != got:
            raise R52PolicyError("deployed R52 file drift: " + rel)

    inherited = deployed.get("inherited_source_sha256") or {}
    source_manifest_sha = deployed.get("source_manifest_sha256")
    if source_manifest_sha != "2281abfa6c433b472f9db0dbe794d422fb16d97e556d031fdd429e84ffe3dabb":
        raise R52PolicyError("unexpected exact R52 source-manifest identity")

    # Prove the GitHub text mirror round-trips to the exact saved source:
    # package text arrived with only one terminal LF stripped by the Library
    # text transport. No other byte change is accepted.
    restored = {}
    for rel, got in checked.items():
        raw = (root / rel).read_bytes()
        source_sha = expected.get(rel)
        if rel == "R52-MANIFEST-SHA256.json":
            source_sha = source_manifest_sha
        elif source_sha is None:
            source_sha = inherited.get(rel)
        if not isinstance(source_sha, str):
            raise R52PolicyError("no source identity for deployed R52 dependency: " + rel)
        if sha(root / rel) == source_sha:
            restored[rel] = raw
        elif hashlib.sha256(raw + b"\n").hexdigest() == source_sha:
            restored[rel] = raw + b"\n"
        else:
            raise R52PolicyError("deployed file is not exact source or exact source minus one final LF: " + rel)

    # Run the original R52 activation validator against the byte-restored mirror.
    with tempfile.TemporaryDirectory() as temp:
        restored_root = Path(temp) / "r52"
        for rel, raw in restored.items():
            target = restored_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        script = restored_root / "scripts" / "validate_territory_activation.py"
        result = subprocess.run(
            [sys.executable, str(script), str(restored_root)],
            cwd=restored_root,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    if result.returncode != 0:
        raise R52PolicyError("R52 activation failed: " + (result.stdout + result.stderr)[-2000:])
    payload = json.loads(result.stdout)
    if payload.get("passed") is not True:
        raise R52PolicyError("R52 activation did not pass")
    return {
        "revision": REVISION,
        "verified_core_files": len(checked),
        "source_package_sha256": deployed.get("source_package_sha256"),
        "source_hash_normalization_count": len(source_hash_mismatches),
        "source_unmanifested_required_files": source_unmanifested,
        "deployment_manifest_verified": True,
        "activation_passed": True,
        "default_minimum": active.get("default_minimum"),
        "score_operator": active.get("score_operator"),
        "target": active.get("target"),
        "mandatory_internal_reviewer": active.get("mandatory_internal_reviewer"),
        "exact_segment_role_binding_required": active.get("exact_segment_role_binding_required"),
        "whole_label_suffix_review_required": active.get("whole_label_suffix_review_required"),
        "native_font_spacing_visual_review_required": active.get("native_font_spacing_visual_review_required"),
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
