"""CE-3A: reviewer-key trust and exact-digest critic attestation verifier.

A valid signature proves ONLY the configured reviewer key signed assertions.
It does NOT prove the reviewer is a real separate human/agent, inspected the
original source or PDF pages, is qualified, or that live publication is safe.
No private signing keys, source fetch, contact, deployment or release here.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .competitive_evidence_engine import canonical as dossier_canonical
from .competitive_launch_guard import REQUIRED_CRITIC_CHECKS
from .source_provenance import EvidenceError
from .pdf_evidence import inspect_pdf_bytes, MAX_PDF_BYTES

POLICY_DOMAIN = b"KO-INDEPENDENT-CRITIC-GOV-POLICY-V1\n"
REVIEW_DOMAIN = b"KO-INDEPENDENT-CRITIC-REVIEW-V1\n"
_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_POLICY_KEYS = frozenset({
    "schema_version", "policy_id", "revision", "issued_at", "expires_at",
    "reviewers", "revoked_key_ids", "revoked_review_ids",
})
_REVIEWER_KEYS = frozenset({
    "reviewer_id", "key_id", "public_key_b64", "venture_ids",
    "valid_from", "valid_until",
})
_REVIEW_KEYS = frozenset({
    "schema_version", "review_id", "reviewer_id", "reviewer_key_id",
    "author_id", "venture_id", "dossier_id", "dossier_sha256",
    "artifact_sha256", "completed_at", "expires_at", "score",
    "checks", "source_inspections", "page_inspections",
    "critical_findings", "unresolved_objections", "reviewer_notes",
    "independent_identity_attested",
})
_SOURCE_INSPECTION = frozenset({
    "source_id", "sha256", "inspected_at", "method",
})
_PAGE_INSPECTION = frozenset({
    "document_sha256", "page_number", "screenshot_sha256",
})
MAX_POLICY = 16000
MAX_REVIEW = 30000
MAX_AGE = timedelta(hours=1)


def canonical(value: Any, max_bytes: int = MAX_REVIEW) -> bytes:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("critic record cannot be serialized") from exc
    if len(raw) > max_bytes:
        raise EvidenceError("critic record exceeds reviewed size limit")
    return raw


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise EvidenceError("invalid critic " + name)
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise EvidenceError("invalid critic " + name + " hash")
    return value


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or len(value) > 48:
        raise EvidenceError("invalid critic timestamp " + name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid critic timestamp " + name) from exc
    if dt.tzinfo is None:
        raise EvidenceError("critic timestamp without timezone " + name)
    return dt.astimezone(timezone.utc)


def _now(value: datetime | None) -> datetime:
    stamp = value if value is not None else datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise EvidenceError("critic assessment requires timezone-aware clock")
    return stamp.astimezone(timezone.utc)


def _public_key(encoded: Any, name: str) -> bytes:
    if not isinstance(encoded, str):
        raise EvidenceError("critic " + name + " public key missing")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceError("critic " + name + " public key malformed") from exc
    if len(raw) != 32:
        raise EvidenceError("critic " + name + " public key length invalid")
    return raw


def _verify(pub: bytes, signature: Any, message: bytes) -> None:
    if not isinstance(signature, str):
        raise EvidenceError("critic signature missing")
    try:
        raw = base64.b64decode(signature, validate=True)
        if len(raw) != 64:
            raise EvidenceError("critic signature length incorrect")
        Ed25519PublicKey.from_public_bytes(pub).verify(raw, message)
    except (binascii.Error, ValueError, InvalidSignature) as exc:
        raise EvidenceError("critic signature invalid or signer untrusted") from exc


def inspect_review_policy(
    envelope: Mapping[str, Any], *, now: datetime | None = None,
) -> dict[str, Any]:
    moment = _now(now)
    if not isinstance(envelope, Mapping) or set(envelope) != {"policy", "signature"}:
        raise EvidenceError("critic governance envelope invalid")
    policy = envelope["policy"]
    if not isinstance(policy, dict) or set(policy) != _POLICY_KEYS:
        raise EvidenceError("critic governance policy fields invalid")
    root = _public_key(
        os.environ.get("KO_CRITIC_ROOT_PUBLIC_KEY_B64", ""),
        "independent governance root",
    )
    _verify(root, envelope["signature"], POLICY_DOMAIN + canonical(policy, MAX_POLICY))
    if policy["schema_version"] != "1.0":
        raise EvidenceError("critic policy version invalid")
    _id(policy["policy_id"], "policy ID")
    if type(policy["revision"]) is not int or policy["revision"] < 1:
        raise EvidenceError("critic policy revision invalid")
    start, end = _utc(policy["issued_at"], "policy issued"), _utc(policy["expires_at"], "policy expiry")
    if (start > moment + timedelta(minutes=2) or end <= moment or
            end <= start or end-start > timedelta(days=7)):
        raise EvidenceError("critic policy expired/future/too long")
    reviewers = policy["reviewers"]
    if not isinstance(reviewers, list) or not 1 <= len(reviewers) <= 20:
        raise EvidenceError("no approved critic reviewer identities")
    ids: set[str] = set()
    keys: set[str] = set()
    for reviewer in reviewers:
        if not isinstance(reviewer, dict) or set(reviewer) != _REVIEWER_KEYS:
            raise EvidenceError("critic registry record incomplete")
        rid = _id(reviewer["reviewer_id"], "reviewer identity")
        key = _id(reviewer["key_id"], "key identity")
        if rid in ids or key in keys:
            raise EvidenceError("duplicate reviewer or signer key identity")
        ids.add(rid); keys.add(key)
        _public_key(reviewer["public_key_b64"], "reviewer")
        ventures = reviewer["venture_ids"]
        if (not isinstance(ventures, list) or not 1 <= len(ventures) <= 20
                or len(ventures) != len(set(ventures))):
            raise EvidenceError("critic reviewer's venture scope invalid")
        for venture in ventures:
            _id(venture, "venture scope")
        start_key = _utc(reviewer["valid_from"], "reviewer start")
        end_key = _utc(reviewer["valid_until"], "reviewer expiry")
        if end_key <= start_key or end_key - start_key > timedelta(days=365):
            raise EvidenceError("critic signing-key lifetime invalid")
    for field in ("revoked_key_ids", "revoked_review_ids"):
        values = policy[field]
        if (not isinstance(values, list) or len(values) > 1000
                or len(values) != len(set(values))):
            raise EvidenceError("critic revocation list invalid")
        for v in values:
            _id(v, field)
    return policy


def inspect_signed_critic_review(
    dossier: Mapping[str, Any], artifact_sha256: str,
    policy_envelope: Mapping[str, Any],
    review_envelope: Mapping[str, Any], *,
    artifact_pdf_path: Path | str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate signed review metadata, not actual human independence or truth.

    This is an internal governance HOLD even if all mandatory checks are true.
    """
    moment = _now(now)
    policy = inspect_review_policy(policy_envelope, now=moment)
    if not isinstance(dossier, Mapping):
        raise EvidenceError("critic dossier missing")
    digest = hashlib.sha256(dossier_canonical(dossier)).hexdigest()
    artifact_digest = _sha(artifact_sha256, "artifact")
    pdf_path = Path(artifact_pdf_path)
    if (pdf_path.is_symlink() or not pdf_path.is_file()
            or not 100 <= pdf_path.stat().st_size <= MAX_PDF_BYTES):
        raise EvidenceError("critic original PDF is missing, unsafe or oversized")
    original_pdf = pdf_path.read_bytes()
    if hashlib.sha256(original_pdf).hexdigest() != artifact_digest:
        raise EvidenceError("critic actual PDF artifact bytes differ from supplied digest")
    actual_pdf = inspect_pdf_bytes(original_pdf)
    if actual_pdf["pdf_sha256"] != artifact_digest:
        raise EvidenceError("critic PDF parser digest mismatch")
    if not isinstance(review_envelope, Mapping) or set(review_envelope) != {"review", "signature"}:
        raise EvidenceError("critic review signature envelope malformed")
    review = review_envelope["review"]
    if not isinstance(review, dict) or set(review) != _REVIEW_KEYS:
        raise EvidenceError("critic review record incomplete")
    rid = _id(review["review_id"], "review ID")
    reviewer_id = _id(review["reviewer_id"], "reviewer ID")
    key_id = _id(review["reviewer_key_id"], "reviewer key ID")
    for field in ("author_id", "venture_id", "dossier_id"):
        _id(review[field], field)
    signer = next((item for item in policy["reviewers"] if item["reviewer_id"] == reviewer_id), None)
    if (signer is None or signer["key_id"] != key_id or
            key_id in policy["revoked_key_ids"] or rid in policy["revoked_review_ids"]):
        raise EvidenceError("critic signer unknown, mismatched or revoked")
    _verify(
        _public_key(signer["public_key_b64"], "reviewer"),
        review_envelope["signature"], REVIEW_DOMAIN + canonical(review),
    )
    if review["schema_version"] != "1.0":
        raise EvidenceError("critic review schema invalid")
    if (reviewer_id == review["author_id"] or
            review["author_id"] != dossier.get("author_id") or
            review["dossier_id"] != dossier.get("dossier_id") or
            review["venture_id"] != dossier.get("venture_id") or
            review["venture_id"] not in signer["venture_ids"]):
        raise EvidenceError("critic self-review, wrong dossier or unauthorized venture")
    if review["dossier_sha256"] != digest or review["artifact_sha256"] != artifact_digest:
        raise EvidenceError("critic review bound to another report or dossier version")
    completed = _utc(review["completed_at"], "review completion")
    expires = _utc(review["expires_at"], "review expiry")
    if (not timedelta(minutes=-2) <= moment-completed <= MAX_AGE
            or expires <= moment or expires <= completed
            or expires-completed > MAX_AGE):
        raise EvidenceError("critic review stale, future, expired or overlong")
    if not _utc(signer["valid_from"], "key start") <= completed <= _utc(
        signer["valid_until"], "key expiry"
    ):
        raise EvidenceError("review outside signer key validity")
    score = review["score"]
    if isinstance(score, bool) or type(score) not in (float, int) or not 9.0 < score <= 10.0:
        raise EvidenceError("critic score must be strictly greater than 9.0")
    checks = review["checks"]
    if (not isinstance(checks, dict) or set(checks) != REQUIRED_CRITIC_CHECKS
            or any(checks[k] is not True for k in REQUIRED_CRITIC_CHECKS)):
        raise EvidenceError("critic mandatory twelve checks not all passed")
    if (type(review["critical_findings"]) is not int or review["critical_findings"] != 0
            or review["unresolved_objections"] != []):
        raise EvidenceError("critic critical findings or objections unresolved")
    if review["independent_identity_attested"] is not True:
        raise EvidenceError("reviewer did not assert separate reviewer boundary")
    if not isinstance(review["reviewer_notes"], str) or not 20 <= len(review["reviewer_notes"]) <= 1800:
        raise EvidenceError("critic reasoning and limitations missing")

    sources = dossier.get("sources")
    if not isinstance(sources, list) or not sources:
        raise EvidenceError("critic dossier has no source evidence")
    expected = {}
    for source in sources:
        if not isinstance(source, dict):
            raise EvidenceError("critic source record malformed")
        sid = _id(source.get("id"), "source ID")
        digest_source = _sha(source.get("sha256"), "source")
        if sid in expected:
            raise EvidenceError("duplicate source in critic dossier")
        expected[sid] = digest_source
    observed = {}
    inspected = review["source_inspections"]
    if not isinstance(inspected, list) or not 1 <= len(inspected) <= 80:
        raise EvidenceError("critic source inspection evidence absent")
    for entry in inspected:
        if not isinstance(entry, dict) or set(entry) != _SOURCE_INSPECTION:
            raise EvidenceError("critic source inspection schema invalid")
        sid = _id(entry["source_id"], "inspected source ID")
        if sid in observed or entry["method"] != "reviewer_claimed_original_review":
            raise EvidenceError("critic duplicate or unverified inspection method")
        observed[sid] = _sha(entry["sha256"], "inspected source")
        inspected_at = _utc(entry["inspected_at"], "inspection time")
        if not timedelta(minutes=-2) <= completed-inspected_at <= MAX_AGE:
            raise EvidenceError("critic original-source inspection outside review window")
    if expected != observed:
        raise EvidenceError("critic did not cover exact current source digests")

    pages = review["page_inspections"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= 500:
        raise EvidenceError("critic rendered page inspection records missing")
    page_set = set()
    for page in pages:
        if not isinstance(page, dict) or set(page) != _PAGE_INSPECTION:
            raise EvidenceError("critic visual inspection schema invalid")
        if page["document_sha256"] != artifact_digest:
            raise EvidenceError("critic reviewed different output document")
        num = page["page_number"]
        if type(num) is not int or not 1 <= num <= 2000 or num in page_set:
            raise EvidenceError("critic PDF page invalid, duplicate or unbounded")
        page_set.add(num)
        _sha(page["screenshot_sha256"], "PDF screenshot")
    if sorted(page_set) != list(range(1, actual_pdf["page_count"] + 1)):
        raise EvidenceError("critic page review must cover every actual PDF page")

    return {
        "state": "SIGNED_REVIEW_METADATA_VALID_EXTERNAL_INDEPENDENCE_UNVERIFIED",
        "review_id": rid,
        "reviewer_id": reviewer_id,
        "dossier_sha256": digest,
        "artifact_sha256": artifact_digest,
        "signed_source_inspections": len(observed),
        "reviewer_claimed_visual_pages": len(page_set),
        "actual_pdf_pages_parsed": actual_pdf["page_count"],
        "rendered_pdf_pixels_independently_inspected": False,
        "mandatory_checks_true": len(REQUIRED_CRITIC_CHECKS),
        "score_asserted": float(score),
        "original_source_truth_independently_verified": False,
        "reviewer_independence_operationally_proven": False,
        "external_publication_authorized": False,
        "production_engine_ready": False,
    }


def assess_signed_review(
    dossier: Mapping[str, Any], artifact_sha256: str,
    policy_envelope: Mapping[str, Any],
    review_envelope: Mapping[str, Any], *,
    artifact_pdf_path: Path | str,
    now: datetime | None = None,
) -> dict[str, Any]:
    try:
        return inspect_signed_critic_review(
            dossier, artifact_sha256, policy_envelope, review_envelope,
            artifact_pdf_path=artifact_pdf_path, now=now,
        )
    except (EvidenceError, TypeError, KeyError, ValueError, OverflowError) as exc:
        return {
            "state": "BLOCK",
            "errors": [str(exc)[:240]],
            "external_publication_authorized": False,
            "reviewer_independence_operationally_proven": False,
            "production_engine_ready": False,
        }
