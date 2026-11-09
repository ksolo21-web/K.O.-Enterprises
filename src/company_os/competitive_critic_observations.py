"""CE-1O: require signed, page-by-page and claim-by-claim review assertions.

This is a substantive *reviewer intake* linked to the exact CE-1N sealed
workroom, not proof that a separate person/agent saw or understood anything.
Claims without issuer originals in the room remain unverified. Never release.
No signing key, network, external API, customer action or approval operation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .competitive_critic_review import (
    _id, _now, _public_key, _sha, _utc, _verify, canonical,
    inspect_review_policy,
)
from .competitive_critic_room import (
    MAX_MANIFEST_BYTES, _file_name, _bytes, inspect_sealed_critic_room,
)
from .source_provenance import EvidenceError

OBSERVATION_DOMAIN = b"KO-ORIGINAL-PAGE-AND-CLAIM-OBSERVATIONS-V1\n"
MAX_SIGNED_OBSERVATIONS_BYTES = 350_000
MAX_OBSERVATION_AGE = timedelta(hours=1)
RECEIPT_FIELDS = frozenset({
    "schema_version", "receipt_id", "reviewer_id", "reviewer_key_id",
    "author_id", "venture_id", "dossier_id",
    "dossier_sha256", "handoff_sha256", "issuer_inventory_head_sha256",
    "room_manifest_sha256", "completed_at", "expires_at",
    "page_observations", "claim_assessments", "reviewer_summary",
})
PAGE_FIELDS = frozenset({
    "file", "png_sha256", "observed_at", "visual_finding", "visual_notes",
})
CLAIM_FIELDS = frozenset({
    "claim_id", "source_ids_considered", "counter_source_ids_considered",
    "issuer_citation_refs", "assessed_at", "disposition", "reasoning",
})
CITATION_FIELDS = frozenset({
    "source_id", "document_id", "page_number", "png_sha256",
})
VISUAL_FINDINGS = frozenset({
    "legible_reported", "defect_reported", "unassessable",
})
DISPOSITIONS = frozenset({
    "packet_excerpt_located", "contradiction_reported", "unverified",
})


def _annotation(value: Any, label: str, *, minimum: int = 36,
                maximum: int = 1200) -> str:
    if (not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum
            or any(ord(ch) < 32 and ch not in "\t\n" for ch in value)):
        raise EvidenceError(label + " requires bounded substantive reasoning")
    return value


def _date(value: Any, completed: datetime) -> None:
    observed = _utc(value, "review observation timestamp")
    if not timedelta(minutes=-2) <= completed - observed <= MAX_OBSERVATION_AGE:
        raise EvidenceError("reviewer page/claim observation outside signed window")


def _get_room_packet(room: Path | str, expected_manifest_sha256: str) -> dict[str, Any]:
    # Recheck ALL page PNG bytes and the exact manifest before consulting it.
    status = inspect_sealed_critic_room(
        room, expected_manifest_sha256=expected_manifest_sha256,
    )
    if (status["state"] != "READ_ONLY_SOURCE_PAGE_ROOM_HASHES_VERIFIED_REVIEW_PENDING"
            or status["publication_authorized"] is not False):
        raise EvidenceError("reviewer workroom was not independently revalidated")
    path = Path(room) / "manifest.json"
    if path.is_symlink():
        raise EvidenceError("reviewer workroom manifest symlink forbidden")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise EvidenceError("reviewer workroom changed after image inspection")
    packet = json.loads(raw)
    if not isinstance(packet, dict) or _bytes(packet, MAX_MANIFEST_BYTES) != raw:
        raise EvidenceError("reviewer workroom canonical manifest changed")
    return packet


def _citation_refs(packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    work = packet["original_pdf_worklist"]
    pages = {
        x["file"]: x["sha256"] for x in packet["pages"]
    }
    citations: dict[str, dict[str, Any]] = {}
    for src in work["source_requirements"]:
        sid = _id(src["source_id"], "original issuer source ID")
        name = _file_name(src["document_id"], src["exact_excerpt_page"])
        png_digest = pages.get(name)
        if png_digest is None or sid in citations:
            raise EvidenceError("original issuer citation page not in reviewer packet")
        citations[sid] = {
            "source_id": sid,
            "document_id": src["document_id"],
            "page_number": src["exact_excerpt_page"],
            "png_sha256": png_digest,
        }
    return citations


def build_pending_observation_worklist(
    room: Path | str, *, expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Prepare exact tasks with NO answered questions and NO implied review."""
    packet = _get_room_packet(room, _sha(expected_manifest_sha256, "room manifest"))
    sources = _citation_refs(packet)
    page_tasks = []
    for page in packet["pages"]:
        page_tasks.append({
            "file": page["file"], "png_sha256": page["sha256"],
            "visual_finding": None, "visual_notes": None,
        })
    claim_tasks = []
    for claim in packet["dossier"]["claims"]:
        ids = set(claim["source_ids"] + claim["counter_source_ids"])
        claim_tasks.append({
            "claim_id": claim["id"],
            "source_ids_considered": list(claim["source_ids"]),
            "counter_source_ids_considered": list(claim["counter_source_ids"]),
            "issuer_citation_refs": [sources[s] for s in sorted(ids & sources.keys())],
            "disposition": None, "reasoning": None,
        })
    return {
        "state": "PENDING_QUALIFIED_SEPARATE_REVIEWER_INPUT",
        "room_manifest_sha256": expected_manifest_sha256,
        "page_tasks": page_tasks,
        "claim_tasks": claim_tasks,
        "page_tasks_unanswered": len(page_tasks),
        "claim_tasks_unanswered": len(claim_tasks),
        "independent_review_completed": False,
        "publication_authorized": False,
    }


def inspect_signed_observation_receipt(
    room: Path | str, expected_manifest_sha256: str,
    policy_envelope: Mapping[str, Any],
    observation_envelope: Mapping[str, Any],
    *, now: datetime | None = None,
) -> dict[str, Any]:
    """Verify signed assertions tied to ALL exact room pages and dossier claims.

    Metadata/UID separation never proves operational independence or truth.
    All successful results are HOLD, not release authority.
    """
    moment = _now(now)
    digest = _sha(expected_manifest_sha256, "out-of-band room")
    packet = _get_room_packet(room, digest)
    policy = inspect_review_policy(policy_envelope, now=moment)
    if (not isinstance(observation_envelope, Mapping)
            or set(observation_envelope) != {"receipt", "signature"}):
        raise EvidenceError("review observations require exact signed envelope")
    receipt = observation_envelope["receipt"]
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise EvidenceError("signed observation record has missing or extra fields")
    if receipt["schema_version"] != "1.0":
        raise EvidenceError("unsupported signed observation schema")
    rid = _id(receipt["receipt_id"], "observation receipt ID")
    reviewer = _id(receipt["reviewer_id"], "observation reviewer ID")
    key = _id(receipt["reviewer_key_id"], "observation key ID")
    dossier = packet["dossier"]
    if (rid in policy["revoked_review_ids"] or key in policy["revoked_key_ids"]
            or receipt["author_id"] != dossier["author_id"]
            or reviewer == receipt["author_id"]
            or receipt["dossier_id"] != dossier["dossier_id"]
            or receipt["venture_id"] != dossier["venture_id"]
            or receipt["dossier_sha256"] != packet["dossier_sha256"]
            or receipt["handoff_sha256"] != packet["handoff_sha256"]
            or receipt["issuer_inventory_head_sha256"] !=
                packet["issuer_inventory_head_sha256"]
            or receipt["room_manifest_sha256"] != digest):
        raise EvidenceError("critic observations revoked, self-signed or bound to different evidence")
    signer = next(
        (x for x in policy["reviewers"] if x["reviewer_id"] == reviewer), None,
    )
    if (signer is None or signer["key_id"] != key
            or receipt["venture_id"] not in signer["venture_ids"]):
        raise EvidenceError("critic observation key/venture not root-governed")
    _verify(
        _public_key(signer["public_key_b64"], "observation reviewer"),
        observation_envelope["signature"],
        OBSERVATION_DOMAIN + canonical(receipt, MAX_SIGNED_OBSERVATIONS_BYTES),
    )
    completed = _utc(receipt["completed_at"], "observation completion")
    expires = _utc(receipt["expires_at"], "observation expiry")
    if (not timedelta(minutes=-2) <= moment - completed <= MAX_OBSERVATION_AGE
            or not completed < expires <= completed + MAX_OBSERVATION_AGE
            or expires <= moment
            or not _utc(signer["valid_from"], "observation key start") <= completed <=
                _utc(signer["valid_until"], "observation key expiry")):
        raise EvidenceError("signed observation outside current approved reviewer window")
    _annotation(receipt["reviewer_summary"], "overall reviewer findings",
                minimum=60, maximum=2000)

    pages = packet["pages"]
    observations = receipt["page_observations"]
    if (not isinstance(observations, list) or len(observations) != len(pages)):
        raise EvidenceError("reviewer did not cover every actual PDF page")
    expected_pages = {p["file"]: p["sha256"] for p in pages}
    if len(expected_pages) != len(pages):
        raise EvidenceError("duplicate page in sealed packet")
    seen_pages: set[str] = set()
    problem_pages = 0
    for entry in observations:
        if not isinstance(entry, dict) or set(entry) != PAGE_FIELDS:
            raise EvidenceError("reviewer page observation fields invalid")
        name = entry["file"]
        if (not isinstance(name, str) or name not in expected_pages
                or name in seen_pages or entry["png_sha256"] != expected_pages[name]):
            raise EvidenceError("page evidence unknown, duplicated or altered")
        seen_pages.add(name)
        if entry["visual_finding"] not in VISUAL_FINDINGS:
            raise EvidenceError("reviewer did not supply explicit page visual finding")
        _annotation(entry["visual_notes"], "page-specific visual observation")
        _date(entry["observed_at"], completed)
        if entry["visual_finding"] != "legible_reported":
            problem_pages += 1
    if seen_pages != set(expected_pages):
        raise EvidenceError("reviewer page observations omitted original PDF pages")

    original_refs = _citation_refs(packet)
    claims = {c["id"]: c for c in dossier["claims"]}
    if len(claims) != len(dossier["claims"]):
        raise EvidenceError("duplicate claim in reviewed dossier")
    assessments = receipt["claim_assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(claims):
        raise EvidenceError("reviewer did not assess every dossier claim")
    seen_claims: set[str] = set()
    unresolved = 0
    contradictions = 0
    located = 0
    for item in assessments:
        if not isinstance(item, dict) or set(item) != CLAIM_FIELDS:
            raise EvidenceError("claim observation fields invalid")
        cid = item["claim_id"]
        if not isinstance(cid, str) or cid not in claims or cid in seen_claims:
            raise EvidenceError("claim assessment missing, repeated or unrelated")
        seen_claims.add(cid)
        claim = claims[cid]
        if (item["source_ids_considered"] != claim["source_ids"]
                or item["counter_source_ids_considered"] != claim["counter_source_ids"]):
            raise EvidenceError("claim review dropped, reordered or changed cited counterevidence")
        if (not isinstance(item["issuer_citation_refs"], list)
                or any(not isinstance(ref, dict) or set(ref) != CITATION_FIELDS
                       for ref in item["issuer_citation_refs"])):
            raise EvidenceError("claim review has malformed original page references")
        cited = set(claim["source_ids"] + claim["counter_source_ids"])
        expected_refs = [original_refs[sid] for sid in sorted(cited & original_refs.keys())]
        if item["issuer_citation_refs"] != expected_refs:
            raise EvidenceError("claim review omitted original issuer source or counterevidence page")
        finding = item["disposition"]
        if finding not in DISPOSITIONS:
            raise EvidenceError("claim observation disposition unsupported")
        # Exact packet citation can be located, but absent original issuer
        # records must not be classified as independently corroborated facts.
        if finding == "packet_excerpt_located" and not expected_refs:
            raise EvidenceError("unverified nonissuer source cannot be declared reviewed original")
        _annotation(item["reasoning"], "claim-specific limitations/reasoning",
                    minimum=48, maximum=1500)
        _date(item["assessed_at"], completed)
        if finding == "unverified":
            unresolved += 1
        elif finding == "contradiction_reported":
            contradictions += 1
        else:
            located += 1
    if seen_claims != set(claims):
        raise EvidenceError("claim assessments do not cover complete current dossier")

    return {
        "state": "HOLD_SIGNED_PAGE_AND_CLAIM_OBSERVATIONS_NOT_INDEPENDENTLY_VERIFIED",
        "room_manifest_sha256": digest,
        "dossier_sha256": packet["dossier_sha256"],
        "handoff_sha256": packet["handoff_sha256"],
        "issuer_inventory_head_sha256": packet["issuer_inventory_head_sha256"],
        "receipt_id": rid,
        "reviewer_id": reviewer,
        "all_original_pdf_pages_accounted_for": len(seen_pages),
        "all_dossier_claims_accounted_for": len(seen_claims),
        "reported_page_problems": problem_pages,
        "claims_unverified": unresolved,
        "claims_with_reported_contradictions": contradictions,
        "issuer_packet_citations_reported_located": located,
        "reviewer_identity_operationally_independent": False,
        "actual_human_or_agent_visual_inspection_proven": False,
        "source_claim_truth_independently_verified": False,
        "independent_critic_approved": False,
        "publication_authorized": False,
        "production_engine_ready": False,
    }


def assess_signed_observation_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return a definite BLOCK on untrusted or incomplete observation records."""
    try:
        return inspect_signed_observation_receipt(*args, **kwargs)
    except (EvidenceError, OSError, TypeError, ValueError, KeyError, OverflowError) as exc:
        return {
            "state": "BLOCK",
            "errors": [str(exc)[:240]],
            "independent_critic_approved": False,
            "publication_authorized": False,
            "production_engine_ready": False,
        }
