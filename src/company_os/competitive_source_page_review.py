"""CE-1L: bind original PDF page assertions to CE-1K and CE-3A critic review.

This module verifies exact signed *metadata* and reviewer-provided PNG bytes.
A signature does not prove a reviewer is separate, qualified, actually looked
at a page or that PNG pixels show the correct PDF page. Never authorize release.
No network, rendering, signing-key custody, broker, payments or side effects.
"""
from __future__ import annotations

import hashlib
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .capture_trust import StagingTrustLedger
from .competitive_critic_review import (
    _id, _now, _public_key, _sha, _utc, _verify, canonical,
    inspect_review_policy, inspect_signed_critic_review,
)
from .competitive_pdf_source_handoff import inspect_issuer_pdf_handoff
from .source_provenance import EvidenceError

SOURCE_PAGE_REVIEW_DOMAIN = b"KO-CRITIC-SOURCE-PDF-PAGES-V1\n"
SOURCE_PAGE_REVIEW_KEYS = frozenset({
    "schema_version", "receipt_id", "review_id",
    "reviewer_id", "reviewer_key_id", "author_id", "venture_id",
    "dossier_id", "dossier_sha256", "handoff_sha256",
    "issuer_inventory_head_sha256", "completed_at", "expires_at",
    "source_inspections", "page_inspections",
    "critical_findings", "unresolved_objections", "reviewer_notes",
})
SOURCE_INSPECTION_KEYS = frozenset({
    "source_id", "document_id", "original_pdf_sha256", "excerpt_sha256",
    "exact_excerpt_page", "inspected_at", "inspection_note",
})
PAGE_INSPECTION_KEYS = frozenset({
    "document_id", "document_sha256", "page_number", "extracted_text_sha256",
    "screenshot_sha256", "inspected_at", "inspection_note",
})
MAX_RECEIPT_BYTES = 512_000
MAX_SCREENSHOT_BYTES = 1_000_000
MAX_SOURCE_TASKS = 80
MAX_PAGE_TASKS = 1200
MAX_REVIEW_AGE = timedelta(hours=1)
PNG_HEADER = b"\x89PNG\r\n\x1a\n"



def _check_png_structure(png: bytes) -> None:
    """Validate bounded PNG chunks/CRCs, NOT screenshot/PDF page fidelity."""
    if not isinstance(png, bytes) or not 70 <= len(png) <= MAX_SCREENSHOT_BYTES:
        raise EvidenceError("original page PNG bytes absent or too large")
    if not png.startswith(PNG_HEADER):
        raise EvidenceError("original page image is not a PNG")
    offset, pieces, have_pixels, have_end = 8, 0, False, False
    while offset < len(png):
        if offset + 12 > len(png) or pieces >= 2048:
            raise EvidenceError("original page PNG chunk layout incomplete")
        n = int.from_bytes(png[offset:offset + 4], "big")
        end = offset + 12 + n
        if end > len(png) or n > MAX_SCREENSHOT_BYTES:
            raise EvidenceError("original page PNG chunk length invalid")
        kind = png[offset + 4:offset + 8]
        payload = png[offset + 8:offset + 8 + n]
        expected_crc = int.from_bytes(png[end - 4:end], "big")
        if zlib.crc32(kind + payload) & 0xffffffff != expected_crc:
            raise EvidenceError("original page PNG chunk CRC mismatch")
        if pieces == 0:
            if kind != b"IHDR" or n != 13:
                raise EvidenceError("original page PNG header is invalid")
            width = int.from_bytes(payload[:4], "big")
            height = int.from_bytes(payload[4:8], "big")
            depth, color = payload[8], payload[9]
            allowed = {
                0: (1, 2, 4, 8, 16),
                2: (8, 16), 3: (1, 2, 4, 8),
                4: (8, 16), 6: (8, 16),
            }
            if (not 64 <= width <= 8192 or not 64 <= height <= 8192
                    or depth not in allowed.get(color, ())
                    or payload[10] != 0 or payload[11] != 0
                    or payload[12] not in (0, 1)):
                raise EvidenceError("original page PNG dimensions or header invalid")
        elif kind == b"IHDR":
            raise EvidenceError("duplicate PNG header chunk")
        if kind == b"IDAT" and n:
            have_pixels = True
        if kind == b"IEND":
            if n != 0 or not have_pixels or end != len(png):
                raise EvidenceError("original page PNG incomplete or has appended bytes")
            have_end = True
            break
        offset, pieces = end, pieces + 1
    if not have_end:
        raise EvidenceError("original page PNG has no complete ending")


def _note(raw: Any, name: str) -> None:
    if (not isinstance(raw, str) or not 24 <= len(raw) <= 1000
            or any(ord(ch) < 32 and ch not in "\t\n" for ch in raw)):
        raise EvidenceError(name + " requires bounded reviewer reasoning")


def _inspection_stamp(raw: Any, completed: datetime) -> None:
    observed = _utc(raw, "original page inspection time")
    if not timedelta(minutes=-2) <= completed-observed <= MAX_REVIEW_AGE:
        raise EvidenceError("original source inspection time outside reviewer window")


def inspect_signed_source_pdf_review(
    repo_root: Path | str,
    dossier: Mapping[str, Any],
    issuer_id: str,
    package_id: str,
    source_document_ids: Mapping[str, str],
    *,
    staging_policy_envelope: Mapping[str, Any],
    staging_trust_ledger: StagingTrustLedger,
    critic_policy_envelope: Mapping[str, Any],
    report_review_envelope: Mapping[str, Any],
    report_pdf_path: Path | str,
    report_pdf_sha256: str,
    source_page_review_envelope: Mapping[str, Any],
    original_page_pngs: Mapping[str, bytes],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Recheck actual issuer originals and compare both signed review records.

    Input originals and report are reread by the existing CE-1K/CE-3A
    inspectors; all original page PNG bytes are checked against the signed
    page assertions, but PDF rendering fidelity is NOT authenticated.
    """
    moment = _now(now)
    handoff = inspect_issuer_pdf_handoff(
        repo_root, dossier, issuer_id, package_id, source_document_ids,
        policy_envelope=staging_policy_envelope,
        trust_ledger=staging_trust_ledger, now=moment,
    )
    if (handoff["status"] != "HOLD_SIGNED_STAGING_PDF_CRITIC_HANDOFF"
            or handoff["publication_authorized"] is not False):
        raise EvidenceError("current signed-staging PDF handoff not on internal HOLD")
    report = inspect_signed_critic_review(
        dossier, report_pdf_sha256, critic_policy_envelope,
        report_review_envelope, artifact_pdf_path=report_pdf_path, now=moment,
    )
    if (report["state"] != "SIGNED_REVIEW_METADATA_VALID_EXTERNAL_INDEPENDENCE_UNVERIFIED"
            or report["external_publication_authorized"] is not False):
        raise EvidenceError("critic report metadata is invalid or falsely authorized")
    policy = inspect_review_policy(critic_policy_envelope, now=moment)
    if (not isinstance(source_page_review_envelope, Mapping)
            or set(source_page_review_envelope) != {"receipt", "signature"}):
        raise EvidenceError("original source-page reviewer receipt envelope malformed")
    receipt = source_page_review_envelope["receipt"]
    if not isinstance(receipt, dict) or set(receipt) != SOURCE_PAGE_REVIEW_KEYS:
        raise EvidenceError("original source-page reviewer receipt fields invalid")
    if receipt["schema_version"] != "1.0":
        raise EvidenceError("original source-page review schema unsupported")
    rid = _id(receipt["receipt_id"], "original page receipt")
    reviewer = _id(receipt["reviewer_id"], "original page reviewer")
    key = _id(receipt["reviewer_key_id"], "original page reviewer key")
    if (rid in policy["revoked_review_ids"] or key in policy["revoked_key_ids"]
            or receipt["review_id"] in policy["revoked_review_ids"]):
        raise EvidenceError("original source-page reviewer identity or receipt revoked")
    signer = next(
        (r for r in policy["reviewers"] if r["reviewer_id"] == reviewer), None,
    )
    if (signer is None or signer["key_id"] != key
            or receipt["review_id"] != report["review_id"]
            or reviewer != report["reviewer_id"]
            or receipt["author_id"] != dossier["author_id"]
            or reviewer == receipt["author_id"]
            or receipt["venture_id"] != dossier["venture_id"]
            or receipt["venture_id"] not in signer["venture_ids"]
            or receipt["dossier_id"] != dossier["dossier_id"]
            or receipt["dossier_sha256"] != handoff["dossier_sha256"]
            or receipt["handoff_sha256"] != handoff["handoff_sha256"]
            or receipt["issuer_inventory_head_sha256"] !=
                handoff["issuer_inventory_head_sha256"]):
        raise EvidenceError("original source-page receipt not bound to current dossier, reviewer and inventory")
    _verify(
        _public_key(signer["public_key_b64"], "original page reviewer"),
        source_page_review_envelope["signature"],
        SOURCE_PAGE_REVIEW_DOMAIN + canonical(receipt, MAX_RECEIPT_BYTES),
    )
    completed = _utc(receipt["completed_at"], "original review completion")
    expires = _utc(receipt["expires_at"], "original review expiry")
    report_completed = _utc(
        report_review_envelope["review"]["completed_at"], "report review completion",
    )
    if (not timedelta(minutes=-2) <= moment-completed <= MAX_REVIEW_AGE
            or expires <= moment or expires <= completed
            or expires-completed > MAX_REVIEW_AGE
            or completed > report_completed + timedelta(minutes=2)
            or not _utc(signer["valid_from"], "reviewer validity") <= completed <=
                _utc(signer["valid_until"], "reviewer expiry")):
        raise EvidenceError("original source-page receipt stale, future or outside reviewer validity")
    if (type(receipt["critical_findings"]) is not int
            or receipt["critical_findings"] != 0
            or receipt["unresolved_objections"] != []):
        raise EvidenceError("original source-page review has unresolved findings")
    _note(receipt["reviewer_notes"], "original source-page reviewer notes")

    task = handoff["critic_worklist"]
    expected_sources = {row["source_id"]: row for row in task["source_requirements"]}
    claimed_sources = receipt["source_inspections"]
    if (not isinstance(claimed_sources, list) or
            not 1 <= len(claimed_sources) <= MAX_SOURCE_TASKS):
        raise EvidenceError("original PDF source inspection records absent or excessive")
    seen_sources: set[str] = set()
    for row in claimed_sources:
        if not isinstance(row, dict) or set(row) != SOURCE_INSPECTION_KEYS:
            raise EvidenceError("source PDF reviewer inspection schema invalid")
        sid = _id(row["source_id"], "source inspection source")
        if sid in seen_sources or sid not in expected_sources:
            raise EvidenceError("duplicate or unrelated original PDF source inspection")
        seen_sources.add(sid)
        goal = expected_sources[sid]
        if any(row[key] != goal[key] for key in (
            "document_id", "original_pdf_sha256", "excerpt_sha256",
            "exact_excerpt_page",
        )):
            raise EvidenceError("source PDF inspection altered the exact cited original")
        _inspection_stamp(row["inspected_at"], completed)
        _note(row["inspection_note"], "source evidence inspection note")
    if seen_sources != set(expected_sources):
        raise EvidenceError("original PDF reviewer omitted a cited source")

    expected_pages = {
        (r["document_id"], r["page_number"]): r
        for r in task["all_issuer_pdf_pages"]
    }
    claimed_pages = receipt["page_inspections"]
    if (not isinstance(claimed_pages, list)
            or not 1 <= len(claimed_pages) <= MAX_PAGE_TASKS
            or not isinstance(original_page_pngs, Mapping)):
        raise EvidenceError("original PDF page inspections or PNG evidence unavailable")
    seen_pages: set[tuple[str, int]] = set()
    screenshot_hashes: set[str] = set()
    for row in claimed_pages:
        if not isinstance(row, dict) or set(row) != PAGE_INSPECTION_KEYS:
            raise EvidenceError("original PDF page inspection schema invalid")
        doc = _id(row["document_id"], "page source document")
        num = row["page_number"]
        if type(num) is not int or (doc, num) not in expected_pages:
            raise EvidenceError("original PDF page inspection not in current worklist")
        identifier = (doc, num)
        if identifier in seen_pages:
            raise EvidenceError("duplicate original PDF page inspection")
        seen_pages.add(identifier)
        goal = expected_pages[identifier]
        if (row["document_sha256"] != goal["document_sha256"]
                or row["extracted_text_sha256"] != goal["extracted_text_sha256"]):
            raise EvidenceError("original PDF page digest or extracted text changed")
        _inspection_stamp(row["inspected_at"], completed)
        _note(row["inspection_note"], "PDF visual inspection note")
        shot = _sha(row["screenshot_sha256"], "original page PNG")
        if shot in screenshot_hashes:
            raise EvidenceError("one reviewer PNG reused as multiple original PDF pages")
        screenshot_hashes.add(shot)
        name = doc + ":" + str(num)
        png = original_page_pngs.get(name)
        if not isinstance(png, bytes) or hashlib.sha256(png).hexdigest() != shot:
            raise EvidenceError("original PDF page reviewer PNG missing or changed")
        _check_png_structure(png)
    if (seen_pages != set(expected_pages) or len(original_page_pngs) != len(seen_pages)
            or set(original_page_pngs) != {doc + ":" + str(num) for doc, num in seen_pages}):
        raise EvidenceError("reviewer original-PDF page screenshots missing or unexpected")

    return {
        "state": "HOLD_SIGNED_SOURCE_PAGE_METADATA_EXTERNAL_INDEPENDENCE_UNVERIFIED",
        "dossier_sha256": handoff["dossier_sha256"],
        "handoff_sha256": handoff["handoff_sha256"],
        "issuer_inventory_head_sha256": handoff["issuer_inventory_head_sha256"],
        "review_id": report["review_id"],
        "receipt_id": rid,
        "reviewer_id": reviewer,
        "signed_sources_matched": len(seen_sources),
        "signed_original_pdf_pages_matched": len(seen_pages),
        "png_evidence_byte_hashes_matched": len(screenshot_hashes),
        "report_review_score_asserted": report["score_asserted"],
        "reported_checks_true": report["mandatory_checks_true"],
        "rendered_source_pages_independently_verified": False,
        "original_issuer_authenticated": False,
        "reviewer_independence_operationally_proven": False,
        "independent_critic_approved": False,
        "publication_authorized": False,
        "production_engine_ready": False,
    }


def assess_signed_source_pdf_review(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Safe wrapper for internal callers; never promote a failed review."""
    try:
        return inspect_signed_source_pdf_review(*args, **kwargs)
    except (EvidenceError, ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        return {
            "state": "BLOCK", "errors": [str(exc)[:240]],
            "publication_authorized": False,
            "independent_critic_approved": False,
            "production_engine_ready": False,
        }
