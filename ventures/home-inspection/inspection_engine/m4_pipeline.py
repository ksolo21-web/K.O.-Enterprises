"""Milestone 4 source-bound, explicitly invoked, resumable PRIVATE case pipeline.

No scheduler, network calls, model installation, automatic retrials, approvals, or
customer release. Callers must supply three distinct role-specific providers.
An interrupted in-flight stage stays blocked for inspection, never auto-replays
a potentially costly inference call or tool-derived evidence mutation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Callable

from .core import DataError, load_project, validate_project, sha256
from .capture import verify_custody
from .agents import plan_specialists, execute_specialists
from .critic import review_specialist_dossier
from .adjudication import adjudicate, validate_record
from .m4_assembly import assemble_private_draft, _evidence_ledger, _digest

STAGES = ("specialists", "q02", "q03", "report")
FILES = {
    "specialists": ("staged_project.json", "specialist_dossier.json"),
    "q02": ("technical_review.json",),
    "q03": ("adjudicated_project.json", "adjudication.json"),
    "report": ("report_receipt.json",),
}


def _atomic_json(path: Path, payload: dict, *, replace: bool = False) -> None:
    if not replace and path.exists():
        raise DataError("Refusing to overwrite prior M4 stage artifact")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                dir=path.parent, prefix=".m4_atomic_", suffix=".json",
                delete=False) as handle:
            tmp = Path(handle.name)
            os.chmod(tmp, 0o600)
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True,
                      allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataError("M4 stage JSON unavailable or malformed") from exc
    if not isinstance(value, dict):
        raise DataError("M4 stage artifact must be a JSON object")
    return value


def _source_bound(state: dict) -> tuple[Path, Path, dict]:
    if state.get("schema_version") != 1 or state.get("release_allowed") is not False:
        raise DataError("M4 state contract invalid")
    source = Path(state["source_project"]).resolve(strict=True)
    if sha256(source) != state["source_sha256"]:
        raise DataError("Source project changed: start a new private run")
    root = source.parent
    original = load_project(source)
    if verify_custody(original, root):
        raise DataError("Original evidence custody no longer valid")
    original_media = _evidence_ledger(original, root)["media"]
    if _digest(original_media) != state["source_media_digest"]:
        raise DataError("Original media record/bytes differ from case checkpoint")
    selected = state["selected_media_ids"]
    if not selected or len(selected) != len(set(selected)) or (
        not set(selected).issubset({m["id"] for m in original["media"]})
    ):
        raise DataError("Selected evidence list is malformed or stale")
    return source, root, original


def _workspace(state_dir: str | Path) -> tuple[Path, dict]:
    work = Path(state_dir).resolve()
    state = _load_json(work / "case_state.json")
    if state.get("stage") not in ("PREPARED", "PRIVATE_DRAFT"):
        raise DataError("Unknown case stage")
    for stage, records in state.get("completed", {}).items():
        if stage not in FILES or set(records) != set(FILES[stage]):
            raise DataError("Unexpected M4 stage receipt")
        for name, expected in records.items():
            target = work / name
            if not re.fullmatch("[0-9a-f]{64}", str(expected)):
                raise DataError("Invalid stage artifact digest")
            if not target.is_file() or sha256(target) != expected:
                raise DataError("Saved stage artifact hash mismatch")
    if "report" in state.get("completed", {}):
        recorded = _load_json(work / "report_receipt.json")
        for name_key, sha_key in (
            ("draft_pdf_relative_path", "draft_pdf_sha256"),
            ("draft_receipt_relative_path", "draft_receipt_sha256"),
        ):
            rel = recorded.get(name_key)
            if not isinstance(rel, str) or not rel.startswith("option2_draft/") or (
                (work / rel).resolve().parent != (work / "option2_draft").resolve()
            ):
                raise DataError("Private report artifact path invalid")
            target = work / rel
            if not target.is_file() or sha256(target) != recorded.get(sha_key):
                raise DataError("Private report PDF/receipt hash mismatch")
    return work, state


def _assert_no_inflight(work: Path) -> None:
    if (work / "in_flight.json").exists():
        raise DataError("Interrupted stage is held for manual audit; never auto-replay model calls")


def prepare_case(source_project: str | Path, workspace: str | Path,
                 *, media_ids: list[str] | None = None) -> dict:
    """Bind an immutable source input and explicit photo work-order selection."""
    source = Path(source_project).resolve(strict=True)
    original = load_project(source)
    if verify_custody(original, source.parent):
        raise DataError("Q01 source custody failed")
    inventory = _evidence_ledger(original, source.parent)["media"]
    selected = list(media_ids) if media_ids is not None else [
        x["id"] for x in original["media"] if x["kind"] == "photo"
    ]
    if not selected or len(selected) != len(set(selected)):
        raise DataError("Choose one or more unique photo evidence IDs")
    index = {m["id"]: m for m in original["media"]}
    if any(mid not in index or index[mid]["kind"] != "photo" for mid in selected):
        raise DataError("Select actual photos (extract video stills before M4)")
    plan = plan_specialists(original, selected)
    if not plan["jobs"] or plan["unassigned_media"] or plan["unreviewed_videos"]:
        raise DataError("No routable selected photos; inspector must resolve areas/stills")
    work = Path(workspace).resolve()
    if work == source.parent or work == source:
        raise DataError("M4 workspace must be separate from source project directory")
    if any((parent / ".git").exists() for parent in (work, *work.parents)):
        raise DataError("Private M4 workspace cannot be inside a Git repository")
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(work, 0o700)
    state_path = work / "case_state.json"
    state = {
        "schema_version": 1, "milestone": "M4", "stage": "PREPARED",
        "source_project": str(source), "source_sha256": sha256(source),
        "source_media_digest": _digest(inventory),
        "project_id": original["project_id"],
        "selected_media_ids": selected,
        "plan_digest": _digest(plan),
        "coverage_gap_count": len(plan["unassigned_media"]) + len(plan["unreviewed_videos"]),
        "completed": {}, "release_allowed": False,
        "real_model_accuracy_verified": False, "human_approved": False,
    }
    if state_path.exists():
        work_existing, current = _workspace(work)
        _assert_no_inflight(work_existing)
        _source_bound(current)
        if current["source_project"] != state["source_project"] or (
            current["source_sha256"] != state["source_sha256"]
            or current["selected_media_ids"] != selected
            or current["source_media_digest"] != state["source_media_digest"]
        ):
            raise DataError("Workspace already belongs to a different source/selection")
        return {"status": "PREVIOUS_CHECKPOINT", "completed": [p for p in STAGES if p in current["completed"]],
                "customer_release_allowed": False}
    _atomic_json(state_path, state)
    return {"status": "PREPARED", "jobs": len(plan["jobs"]),
            "unselected_media": len(original["media"]) - len(selected),
            "customer_release_allowed": False}


def status_case(workspace: str | Path) -> dict:
    work, state = _workspace(workspace)
    _, _, _ = _source_bound(state)
    return {
        "milestone": "M4", "project_id": state["project_id"],
        "completed": [p for p in STAGES if p in state["completed"]],
        "in_flight": (work / "in_flight.json").exists(),
        "unselected_media_retained_in_source": True,
        "customer_release_allowed": False,
        "human_approved": False,
    }


def _enter_stage(work: Path, stage: str, state: dict, *,
                 provider_id: str = "no_model") -> None:
    _assert_no_inflight(work)
    if stage in state["completed"]:
        raise DataError("Stage already completed; no automatic model replay")
    previous = {
        "specialists": None, "q02": "specialists",
        "q03": "q02", "report": "q03",
    }[stage]
    if previous and previous not in state["completed"]:
        raise DataError(f"Stage {stage} requires completed {previous}")
    marker = {"stage": stage, "provider_id": provider_id,
              "source_sha256": state["source_sha256"],
              "manual_recovery_required_if_interrupted": True,
              "customer_release_allowed": False}
    fd = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(work / "in_flight.json", flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            json.dump(marker, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if fd is not None:
            os.close(fd)


def _commit_stage(work: Path, state: dict, stage: str,
                  artifacts: dict[str, dict]) -> dict:
    if set(artifacts) != set(FILES[stage]):
        raise DataError("Stage completion lacks required artifacts")
    digests = {}
    for filename, payload in artifacts.items():
        target = work / filename
        _atomic_json(target, payload)
        digests[filename] = sha256(target)
    state["completed"][stage] = digests
    if stage == "report":
        state["stage"] = "PRIVATE_DRAFT"
    _atomic_json(work / "case_state.json", state, replace=True)
    (work / "in_flight.json").unlink()
    return {"stage": stage, "completed": list(state["completed"]),
            "customer_release_allowed": False}


def _get_case(workspace: str | Path) -> tuple[Path, dict, Path, dict]:
    work, state = _workspace(workspace)
    _assert_no_inflight(work)
    source, root, original = _source_bound(state)
    if state["project_id"] != original["project_id"]:
        raise DataError("Checkpoint project identity mismatch")
    return work, state, root, original


def _staged(work: Path, root: Path) -> dict:
    doc = _load_json(work / "staged_project.json")
    validate_project(doc, root)
    if verify_custody(doc, root):
        raise DataError("Staged evidence custody invalid")
    return doc


def run_specialists(workspace: str | Path, provider: Callable, *,
                    provider_id: str, provider_accepts_schema: bool = False) -> dict:
    work, state, root, original = _get_case(workspace)
    if not callable(provider) or not provider_id or len(provider_id) > 85:
        raise DataError("Explicit named specialist provider required")
    if _digest(plan_specialists(original, state["selected_media_ids"])) != state["plan_digest"]:
        raise DataError("Specialist routing changed since preflight")
    _enter_stage(work, "specialists", state, provider_id=provider_id)
    staged, dossier = execute_specialists(
        original, root, provider, media_ids=state["selected_media_ids"],
        provider_id=provider_id, provider_accepts_schema=provider_accepts_schema
    )
    validate_project(staged, root)
    if verify_custody(staged, root):
        raise DataError("Specialist custody or derived evidence failed")
    _source_bound(state)
    if dossier.get("customer_release_allowed") is not False:
        raise DataError("Specialists cannot authorize customer release")
    return _commit_stage(work, state, "specialists", {
        "staged_project.json": staged, "specialist_dossier.json": dossier
    })


def run_q02(workspace: str | Path, provider: Callable, *, provider_id: str) -> dict:
    work, state, root, _ = _get_case(workspace)
    if "specialists" not in state["completed"]:
        raise DataError("Stage q02 requires completed specialists")
    dossier = _load_json(work / "specialist_dossier.json")
    staged = _staged(work, root)
    if not callable(provider) or not provider_id or provider_id == dossier.get("provider"):
        raise DataError("Q02 must use an explicitly different provider")
    _enter_stage(work, "q02", state, provider_id=provider_id)
    review = review_specialist_dossier(
        staged, root, dossier, provider, reviewer_id="Q02", provider_id=provider_id
    )
    if review.get("state") != "SECOND_PASS_COMPLETE_HUMAN_REVIEW_REQUIRED" or (
        review.get("customer_release_allowed") is not False
    ):
        raise DataError("Q02 completion/authority contract not satisfied")
    _source_bound(state)
    if verify_custody(staged, root):
        raise DataError("Q02 source evidence changed during review")
    return _commit_stage(work, state, "q02", {"technical_review.json": review})


def run_q03(workspace: str | Path, provider: Callable, *, provider_id: str) -> dict:
    work, state, root, _ = _get_case(workspace)
    if "q02" not in state["completed"]:
        raise DataError("Stage q03 requires completed q02")
    staged = _staged(work, root)
    review = _load_json(work / "technical_review.json")
    writer = _load_json(work / "specialist_dossier.json").get("provider")
    if not callable(provider) or not provider_id or provider_id in (
        writer, review.get("technical_review_provider")
    ):
        raise DataError("Q03 requires a third distinct reasoning provider")
    _enter_stage(work, "q03", state, provider_id=provider_id)
    result = adjudicate(staged, root, review, provider, provider_id=provider_id)
    validate_record(staged, result)
    adjudicated = dict(staged, adjudication=result)
    validate_project(adjudicated, root)
    _source_bound(state)
    if result.get("customer_release_allowed") is not False:
        raise DataError("Q03 cannot authorize customer release")
    return _commit_stage(work, state, "q03", {
        "adjudicated_project.json": adjudicated,
        "adjudication.json": result
    })


def render_private_case(workspace: str | Path) -> dict:
    """Render only after source-bound Q01 + Q02 + Q03 stage receipts exist."""
    work, state, root, _ = _get_case(workspace)
    if "q03" not in state["completed"]:
        raise DataError("Stage report requires completed q03")
    reviewed = _load_json(work / "adjudicated_project.json")
    validate_project(reviewed, root)
    q02 = _load_json(work / "technical_review.json")
    q03 = _load_json(work / "adjudication.json")
    if reviewed.get("adjudication") != q03:
        raise DataError("Saved adjudicated project no longer matches Q03")
    validate_record(reviewed, q03)
    _enter_stage(work, "report", state)
    result = assemble_private_draft(
        work / "adjudicated_project.json", work / "option2_draft",
        q02=q02, q03=q03, evidence_root=root
    )
    receipt = _load_json(Path(result["receipt"]))
    if receipt.get("customer_release_allowed") is not False:
        raise DataError("Draft report unexpectedly claims customer release")
    _source_bound(state)
    return _commit_stage(work, state, "report", {
        "report_receipt.json": {
            "draft_pdf_sha256": sha256(Path(result["pdf"])),
            "draft_receipt_sha256": sha256(Path(result["receipt"])),
            "draft_pdf_relative_path": "option2_draft/" + Path(result["pdf"]).name,
            "draft_receipt_relative_path": "option2_draft/" + Path(result["receipt"]).name,
            "Q03_status": q03["status"],
            "report_holds": receipt["report_holds"],
            "customer_release_allowed": False,
        }
    })
