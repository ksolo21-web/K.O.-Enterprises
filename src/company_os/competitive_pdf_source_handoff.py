"""CE-1K: hand off signed-staging issuer PDFs to an actual critic worklist.

Offline inspection only. Approved permits, staged PDFs and cryptographic
staging receipts are not original-issuer authentication or independent review.
This module does not contact any source or authorize publication.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .approved_pdf_capture import _id
from .capture_trust import StagingTrustLedger
from .competitive_evidence_engine import assess_competitive_dossier
from .issuer_inventory_journal import IssuerInventoryJournal
from .pdf_evidence import inspect_pdf_bytes
from .source_provenance import EvidenceError, _normalize_space

MAX_HANDOFF_SOURCES = 80
MAX_HANDOFF_BYTES = 100_000


def _current(now: datetime | None) -> datetime:
    current = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise EvidenceError("issuer PDF handoff requires timezone-aware time")
    return current.astimezone(timezone.utc)


def _canon(item: Any) -> bytes:
    try:
        blob = json.dumps(
            item, sort_keys=True, separators=(",", ":"),
            allow_nan=False, ensure_ascii=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("issuer critic handoff cannot be serialized") from exc
    if len(blob) > MAX_HANDOFF_BYTES:
        raise EvidenceError("issuer critic handoff exceeds bounded capacity")
    return blob


def inspect_issuer_pdf_handoff(
    repo_root: Path | str,
    dossier: Mapping[str, Any],
    issuer_id: str,
    package_id: str,
    source_document_ids: Mapping[str, str],
    *,
    policy_envelope: Mapping[str, Any],
    trust_ledger: StagingTrustLedger,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Bind all dossier issuer sources to current signed-staging PDF package.

    Returns hash-only page/source tasks requiring a *separate real critic*.
    A valid returned worklist is never a signed review or release authority.
    """
    moment = _current(now)
    issuer, package = _id(issuer_id, "issuer id"), _id(package_id, "package id")
    if (not isinstance(dossier, Mapping)
            or dossier.get("schema_version") != "1.1"):
        raise EvidenceError("issuer handoff requires attributed v1.1 dossier")
    appraisal = assess_competitive_dossier(dossier, now=moment)
    if appraisal["status"] != "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW":
        raise EvidenceError("invalid or blocked competitive dossier cannot enter critic handoff")
    if (not isinstance(source_document_ids, dict)
            or not 1 <= len(source_document_ids) <= MAX_HANDOFF_SOURCES):
        raise EvidenceError("issuer source-to-document mapping absent or oversized")
    if (not isinstance(trust_ledger, StagingTrustLedger)
            or not isinstance(policy_envelope, Mapping)):
        raise EvidenceError("root-governed signed staging trust is mandatory")
    root = Path(repo_root).resolve()
    if not root.is_dir() or trust_ledger.root != root:
        raise EvidenceError("issuer handoff root and trusted ledger disagree")
    all_sources = dossier["sources"]
    issuer_sources = {s["id"]: s for s in all_sources if s["kind"] == "issuer_original"}
    if not issuer_sources or set(source_document_ids) != set(issuer_sources):
        raise EvidenceError("each issuer-original dossier source requires an exact PDF binding")
    if any(not isinstance(doc, str) for doc in source_document_ids.values()):
        raise EvidenceError("invalid mapped issuer document id")
    for doc in source_document_ids.values():
        _id(doc, "mapped PDF document id")
        if doc == "issuer-listing":
            raise EvidenceError("issuer listing HTML cannot be treated as source PDF")

    with IssuerInventoryJournal(root) as journal:
        status = journal.inspect_session(
            issuer, package, now=moment, require_staging_attestations=True,
            policy_envelope=policy_envelope, trust_ledger=trust_ledger,
        )
        if status["status"] != "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW":
            raise EvidenceError("current signed issuer PDF inventory session invalid")
        records = [
            row for row in journal._events()
            if row["issuer_id"] == issuer and row["package_id"] == package
        ]
        audit = journal.audit()
    pdf_records = {row["document_id"]: row for row in records
                   if row["document_id"] != "issuer-listing"}
    if (len(pdf_records) != len(records) - 1
            or not pdf_records or
            not set(source_document_ids.values()) <= set(pdf_records)):
        raise EvidenceError("issuer PDF bindings reference missing or duplicated inventory")
    if (status["staging_attestations_currently_verified"] != len(records)
            or not all(row["staging_receipt_id"] for row in records)):
        raise EvidenceError("issuer PDF handoff has unsigned staging records")

    source_requirements = []
    package_page_requirements = []
    analyzed: dict[str, dict[str, Any]] = {}
    for document_id in sorted(pdf_records):
        event = pdf_records[document_id]
        if (event["original_issuer_authenticated"] is not False
                or event["independent_critic_approved"] is not False
                or event["publication_authorized"] is not False
                or event["permit_rights_basis_asserted"] != "public_access"
                or event["media_type"] != "application/pdf"):
            raise EvidenceError("issuer PDF record exceeds permissible provenance assertions")
        # Re-read the actual bytes after the journal inspection boundary.
        # Refuse symlinked files and parent paths before opening.
        path = root
        for part in ("state", "competitive_engine", "capture_staging",
                     package, event["filename"]):
            path = path / part
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise EvidenceError("issuer PDF changed into an unsafe storage path")
        if not path.is_file():
            raise EvidenceError("issuer original PDF missing before critic handoff")
        contents = path.read_bytes()
        if (len(contents) != event["bytes"]
                or hashlib.sha256(contents).hexdigest() != event["sha256"]):
            raise EvidenceError("issuer original PDF changed after inventory verification")
        parsed = inspect_pdf_bytes(contents)
        if parsed["pdf_sha256"] != event["sha256"]:
            raise EvidenceError("PDF inspection and original capture digest disagree")
        analyzed[document_id] = parsed
        for page_number, page_text in enumerate(parsed["pages"], 1):
            package_page_requirements.append({
                "document_id": document_id,
                "document_sha256": event["sha256"],
                "page_number": page_number,
                "extracted_text_sha256": hashlib.sha256(
                    page_text.encode("utf-8")
                ).hexdigest(),
                "visual_page_inspection_completed": False,
            })

    for sid in sorted(issuer_sources):
        src = issuer_sources[sid]
        doc_id = source_document_ids[sid]
        event = pdf_records[doc_id]
        if (src["capture_type"] != "local_staging_receipt"
                or src["rights_basis"] != "public_access"
                or src["url"] != event["source_url"]
                or src["publisher"] != event["permit_publisher"]
                or src["origin_id"] != event["permit_origin_id"]
                or src["sha256"] != event["sha256"]
                or src["observed_at"] != event["observed_at"]):
            raise EvidenceError("competitive issuer source does not match signed inventory record")
        quote = _normalize_space(src["excerpt"])
        locations = [
            n for n, page in enumerate(analyzed[doc_id]["pages"], 1)
            if page.count(quote) == 1
        ]
        if (len(locations) != 1 or any(
            page.count(quote) > 1 for page in analyzed[doc_id]["pages"]
        )):
            raise EvidenceError("issuer claim excerpt missing, duplicated or spans multiple PDF pages")
        referenced_by = sorted(
            claim["id"] for claim in dossier["claims"]
            if sid in claim["source_ids"] or sid in claim["counter_source_ids"]
        )
        if not referenced_by:
            raise EvidenceError("orphan issuer original source with no cited claim")
        source_requirements.append({
            "source_id": sid, "document_id": doc_id,
            "original_pdf_sha256": event["sha256"],
            "capture_record_sequence": event["sequence"],
            "signed_staging_receipt_id": event["staging_receipt_id"],
            "excerpt_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            "exact_excerpt_page": locations[0],
            "citing_claim_ids": referenced_by,
            "independent_source_inspection_completed": False,
        })
    tasks = {
        "schema_version": "1.0",
        "issuer_id": issuer, "package_id": package,
        "dossier_sha256": appraisal["dossier_sha256"],
        "issuer_inventory_head_sha256": audit["head_sha256"],
        "source_requirements": source_requirements,
        "all_issuer_pdf_pages": package_page_requirements,
    }
    digest = hashlib.sha256(_canon(tasks)).hexdigest()
    return {
        "status": "HOLD_SIGNED_STAGING_PDF_CRITIC_HANDOFF",
        "handoff_sha256": digest,
        "dossier_sha256": appraisal["dossier_sha256"],
        "issuer_inventory_head_sha256": audit["head_sha256"],
        "referenced_issuer_sources": len(source_requirements),
        "original_pdf_documents_in_package": len(pdf_records),
        "all_pdf_pages_requiring_visual_inspection": len(package_page_requirements),
        "critic_worklist": tasks,
        "original_issuer_authenticated": False,
        "independent_source_inspection_completed": False,
        "independent_page_inspection_completed": False,
        "independent_critic_approved": False,
        "publication_authorized": False,
        "limits": [
            "Signed staging receipts do not independently authenticate actual issuer transport",
            "PDF text recognition is not a rendered visual inspection of any page",
            "Complete issuer listing from HTML cannot prove dynamically loaded attachments",
            "Separate qualified human or agent critic and external release guard are required",
        ],
    }
