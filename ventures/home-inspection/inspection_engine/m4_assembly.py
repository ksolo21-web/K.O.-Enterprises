"""Milestone 4: assemble a private, source-bound Option 2 DRAFT from existing records.

This does not run a model, attest visual accuracy, approve findings or release a
report. Specialist/Q02/Q03/human work remains upstream and separately governed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .core import DataError, load_project, validate_project, sha256, safe_path, blockers
from .capture import verify_custody
from .adjudication import validate_record
from .m4_workflow import preflight_case
from .report import build_pdf
from .zoom import verify_zoom_record

EVIDENCE_CLASSES = frozenset({
    "directly_visible", "probable", "inaccessible",
    "physical_test_required", "unresolved",
})


def _digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _evidence_class(item: dict) -> str:
    """Explicit characterization only; never promote a model claim by inference."""
    value = item.get("evidence_class", "unresolved")
    if value not in EVIDENCE_CLASSES:
        raise DataError("Unrecognized evidence class")
    if value == "directly_visible" and (
        not item.get("evidence_ids")
        or (item.get("status") not in (None, "observed", "partially_observed"))
    ):
        raise DataError("Direct visibility requires cited, visible evidence")
    if value == "inaccessible" and item.get("status") in ("observed", "partially_observed"):
        raise DataError("Inaccessible claim conflicts with visible observation")
    return value


def _evidence_ledger(document: dict, root: Path) -> dict:
    """Include EVERY media item and EVERY source-linked claim, not only report cards."""
    media = []
    index = {}
    for m in document["media"]:
        if not re.fullmatch(r"[0-9a-f]{64}", m.get("sha256", "")):
            raise DataError("M4 requires an original SHA-256 for each media record")
        actual = sha256(safe_path(root, m["path"]))
        if actual != m["sha256"]:
            raise DataError("Evidence source hash mismatch")
        # Retain the entire case-local original record, including capture context,
        # video timing, provenance, inspector labels and evidence state.
        row = dict(m)
        media.append(row)
        index[m["id"]] = row
    zooms = []
    for z in document.get("zoom_views", []):
        verify_zoom_record(z, document, root, deep=True)
        zooms.append(dict(z))
    records = []
    for section in ("observations", "findings", "equipment", "limitations"):
        for item in document[section]:
            cited = list(item.get("evidence_ids", []))
            for ident in cited:
                if ident not in index:
                    raise DataError("Finding cites missing evidence")
            records.append({
                "section": section,
                "id": item["id"],
                "system": item["system"],
                "status": item.get("status", "not_applicable"),
                "review": item.get("review", "not_recorded"),
                "evidence_class": _evidence_class(item),
                "evidence_ids": cited,
                "zoom_view_ids": list(item.get("zoom_view_ids", [])),
                "source_record": dict(item),
            })
    return {"media": media, "zooms": zooms, "records": records}


def assemble_private_draft(project_path: str | Path, output_dir: str | Path,
                           *, q02: dict | None = None,
                           q03: dict | None = None,
                           evidence_root: Path | None = None) -> dict:
    """Produce an internal PDF and a deterministic audit receipt.

    Re-running the same input is safe; different source states cannot overwrite
    a previously assembled draft. No customer-release pathway exists here.
    """
    source = Path(project_path).resolve(strict=True)
    original_project_sha = sha256(source)
    root = Path(evidence_root).resolve() if evidence_root is not None else source.parent
    document = (validate_project(json.loads(source.read_text(encoding='utf-8')), root)
                if evidence_root is not None else load_project(source))
    errors = verify_custody(document, root)
    if errors:
        raise DataError("Q01 custody failure: " + "; ".join(errors))
    ledger = _evidence_ledger(document, root)
    preflight = preflight_case(source, evidence_root=root)
    if q03 is not None and (q02 is None or not isinstance(q03, dict)):
        raise DataError("Q03 requires the corresponding Q02 record")
    q03_held = None
    if q03 is not None:
        if not isinstance(q02, dict) or q03.get("technical_review") != q02:
            raise DataError("Q02 record does not match Q03 source")
        q03_held = validate_record(document, q03)
    elif q02 is not None and not isinstance(q02, dict):
        raise DataError("Q02 record must be an object")

    report_holds = blockers(document)
    review = {
        "Q01": "SOURCE_CUSTODY_VERIFIED",
        "Q02": "ATTACHED_UNVALIDATED" if q02 is not None and q03 is None
               else "REFERENCED_BY_VALID_Q03" if q03 is not None else "NOT_PROVIDED",
        "Q03": "VALIDATED_WITH_HOLDS" if q03_held else
               "VALIDATED_INTERNAL_ONLY" if q03_held == [] else "NOT_PROVIDED",
        "Q03_held_entry_ids": q03_held,
        "qualified_human_release": "NOT_ATTESTED",
    }
    receipt = {
        "schema_version": 1,
        "milestone": "M4",
        "stage": "PRIVATE_OPTION2_DRAFT",
        "project_id": document["project_id"],
        "source_project_sha256": original_project_sha,
        "evidence_root_sha256": _digest([{"id": m["id"], "sha256": m["sha256"]} for m in ledger["media"]]),
        "evidence": ledger,
        "specialist_plan_sha256": _digest(preflight["specialist_plan"]),
        "unrouted_evidence": preflight["unrouted_evidence"],
        "coverage": preflight["coverage"],
        "review": review,
        "report_holds": report_holds,
        "real_model_accuracy_verified": False,
        "inspector_approved": False,
        "customer_release_allowed": False,
    }
    # Bind any externally supplied review records without claiming independent execution.
    receipt["Q02_sha256"] = _digest(q02) if q02 is not None else None
    receipt["Q03_sha256"] = _digest(q03) if q03 is not None else None
    # Private source-bound disclosure: retain actual review decisions, not just digests.
    receipt["review_records"] = {"Q02": q02, "Q03": q03}

    out = Path(output_dir).resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", str(document["project_id"]))[:65]
    pdf = out / f"{slug}_option2_PRIVATE_DRAFT.pdf"
    audit = out / f"{slug}_option2_PRIVATE_DRAFT.json"
    if pdf.exists() != audit.exists():
        raise DataError("Incomplete prior output; inspect before recovery")
    if audit.exists():
        old = json.loads(audit.read_text(encoding="utf-8"))
        if ({k: v for k, v in old.items() if k != "pdf_sha256"} != receipt
                or old.get("pdf_sha256") != sha256(pdf)):
            raise DataError("Existing draft bound to different inputs; use a new output directory")
        return {"pdf": str(pdf), "receipt": str(audit), "reused": True,
                "customer_release_allowed": False, "holds": len(report_holds)}

    with tempfile.TemporaryDirectory(prefix=".m4_pending_", dir=out) as work:
        candidate = Path(work) / "draft.pdf"
        build_pdf(document, root, candidate, include_evidence_register=True)
        if sha256(source) != original_project_sha or _evidence_ledger(document, root) != ledger:
            raise DataError("Source evidence changed during report generation")
        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise DataError("Option 2 renderer did not produce a PDF")
        receipt["pdf_sha256"] = sha256(candidate)
        staged_receipt = Path(work) / "receipt.json"
        staged_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                                  encoding="utf-8")
        os.chmod(candidate, 0o600)
        os.chmod(staged_receipt, 0o600)
        os.replace(candidate, pdf)
        os.replace(staged_receipt, audit)
    return {"pdf": str(pdf), "receipt": str(audit), "reused": False,
            "customer_release_allowed": False, "holds": len(report_holds)}
