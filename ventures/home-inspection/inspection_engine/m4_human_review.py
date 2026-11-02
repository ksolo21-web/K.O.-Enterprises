"""Private M4 two-key human-review declarations, not customer release.

Ed25519 verifies possession of a registered key, NOT a professional license,
employer authority, independence of actual people, or in-person inspection.
This module does not change findings to human_verified, approve code compliance,
publish any PDF, or unblock Q03/report holds.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from .core import DataError, SYSTEM_NAME, sha256
from .m4_assembly import _digest
from .m4_pipeline import _get_case, _load_json, _atomic_json

ROLES = ("qualified_inspector", "independent_quality_reviewer")
DECISIONS = ("accepted_for_internal_review", "correction_required", "insufficient_evidence")
MEDIA_STATES = ("visually_reviewed", "not_reviewed", "inconclusive")
COVERAGE_STATES = ("confirmed_partial", "not_verified", "requires_field_inspection")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,63}\Z")
ROLE_FILE = {
    "qualified_inspector": "inspector_review_signed.json",
    "independent_quality_reviewer": "quality_review_signed.json",
}


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _trust(path: Path) -> dict:
    value = _load_json(path)
    rows = value.get("reviewers")
    if value.get("schema_version") != 1 or not isinstance(rows, list):
        raise DataError("Trusted reviewer key registry is invalid")
    if len(rows) != 2:
        raise DataError("Exactly two distinct reviewer registrations required for this gate")
    roles = set()
    names = set()
    keys = set()
    for row in rows:
        if not isinstance(row, dict):
            raise DataError("Reviewer registration must be an object")
        name = row.get("reviewer_id")
        role = row.get("role")
        key = row.get("public_key_hex")
        if not isinstance(name, str) or not ID_RE.fullmatch(name):
            raise DataError("Reviewer identifier is malformed")
        if role not in ROLES or not isinstance(key, str):
            raise DataError("Reviewer role or Ed25519 key absent")
        try:
            raw = bytes.fromhex(key)
            if len(raw) != 32:
                raise ValueError("Invalid key length")
            Ed25519PublicKey.from_public_bytes(raw)
        except (ValueError, TypeError) as exc:
            raise DataError("Reviewer key must be a 32-byte Ed25519 public key") from exc
        if row.get("active") is not True:
            raise DataError("Inactive human reviewer cannot sign")
        if role in roles or name in names or key in keys:
            raise DataError("Reviewer roles, names and signing keys must differ")
        roles.add(role)
        names.add(name)
        keys.add(key)
    if roles != set(ROLES):
        raise DataError("Both independent roles must be registered")
    return value


def _get_packet(work: Path, state: dict) -> dict:
    if "report" not in state["completed"]:
        raise DataError("Signed human review requires completed private report")
    packet = _load_json(work / "review_request.json")
    if packet.get("schema_version") != 1 or packet.get("stage") != "PRIVATE_HUMAN_REVIEW":
        raise DataError("Invalid human review packet")
    if packet.get("source_project_sha256") != state["source_sha256"]:
        raise DataError("Human review source hash mismatch")
    if packet.get("stage_receipts_digest") != _digest(state["completed"]):
        raise DataError("Human review stage receipts changed")
    receipt = _load_json(work / "report_receipt.json")
    if packet.get("pdf_sha256") != receipt.get("draft_pdf_sha256") or (
        packet.get("audit_sha256") != receipt.get("draft_receipt_sha256")
    ):
        raise DataError("Human review PDF/audit source changed")
    if packet.get("customer_release_allowed") is not False:
        raise DataError("Review packet illegally claims release")
    return packet


def prepare_review_request(workspace: str | Path, trust_file: str | Path) -> dict:
    """Create a private, immutable reviewer request after the Q03 report stage."""
    work, state, root, _ = _get_case(workspace)
    if "report" not in state["completed"]:
        raise DataError("Review packet requires completed M4 private report")
    trust_path = Path(trust_file).resolve(strict=True)
    trust = _trust(trust_path)
    adjudicated = _load_json(work / "adjudicated_project.json")
    q03 = _load_json(work / "adjudication.json")
    receipt = _load_json(work / "report_receipt.json")
    if adjudicated.get("adjudication") != q03:
        raise DataError("Q03 source mismatch")
    forbidden = {
        _load_json(work / "specialist_dossier.json").get("provider"),
        _load_json(work / "technical_review.json").get("technical_review_provider"),
        q03.get("provider"),
    }
    if any(r["reviewer_id"] in forbidden for r in trust["reviewers"]):
        raise DataError("A model-stage provider ID cannot act as human review identity")
    sections = ("observations", "findings", "equipment", "limitations")
    items = [{
        "section": section, "id": entry["id"], "system": entry["system"],
        "evidence_ids": list(entry.get("evidence_ids", [])),
        "summary": str(entry.get("description", entry.get("condition", entry.get("feature", entry.get("model", ""))))),
    } for section in sections for entry in adjudicated[section]]
    media = [{
        "id": entry["id"], "kind": entry["kind"], "area": entry["area"],
        "sha256": entry["sha256"],
        "path": entry["path"],
        "derived_from_id": entry.get("derived_from_id"),
        "timestamp_seconds": entry.get("timestamp_seconds"),
    } for entry in adjudicated["media"]]
    packet = {
        "schema_version": 1, "stage": "PRIVATE_HUMAN_REVIEW",
        "project_id": state["project_id"],
        "source_project_sha256": state["source_sha256"],
        "stage_receipts_digest": _digest(state["completed"]),
        "pdf_sha256": receipt["draft_pdf_sha256"],
        "audit_sha256": receipt["draft_receipt_sha256"],
        "trust_file_sha256": sha256(trust_path),
        "items": items, "media": media,
        "systems": list(SYSTEM_NAME),
        "q03_held_entry_ids": q03.get("held_entry_ids", []),
        "report_holds": receipt.get("report_holds", []),
        "identity_claim": "Registered key possession only; no real license verification",
        "customer_release_allowed": False,
    }
    request = work / "review_request.json"
    if request.exists():
        if _load_json(request) != packet:
            raise DataError("Review request is already bound to a different source")
        return {"status": "REUSED", "review_request": str(request),
                "digest": _digest(packet), "customer_release_allowed": False}
    _atomic_json(request, packet)
    return {"status": "CREATED", "review_request": str(request),
            "digest": _digest(packet), "customer_release_allowed": False}


def _response_valid(packet: dict, record: dict) -> None:
    if not isinstance(record, dict):
        raise DataError("Human review response must be an object")
    if set(record) != {"request_digest", "role", "reviewer_id", "items", "media", "systems", "note"}:
        raise DataError("Review response schema mismatch")
    if record["request_digest"] != _digest(packet):
        raise DataError("Review response belongs to another evidence/report snapshot")
    if record["role"] not in ROLES or not isinstance(record["reviewer_id"], str) or (
        not ID_RE.fullmatch(record["reviewer_id"])
    ):
        raise DataError("Review role/identity malformed")
    if not isinstance(record["note"], str) or len(record["note"]) > 5000:
        raise DataError("Review note invalid")
    for field, source_key, id_key, choices in (
        ("items", "items", "id", DECISIONS),
        ("media", "media", "id", MEDIA_STATES),
        ("systems", "systems", None, COVERAGE_STATES),
    ):
        rows = record.get(field)
        if not isinstance(rows, list):
            raise DataError(f"Missing human review {field} checklist")
        expected = (
            {(x["section"], x["id"]) for x in packet[source_key]}
            if field == "items" else
            set(x["id"] for x in packet[source_key])
            if field == "media" else set(packet[source_key])
        )
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise DataError("Review checklist row must be object")
            needed = {"section", "id", "decision", "note"} if field == "items" else (
                {"id", "decision", "note"} if field == "media" else
                {"system", "decision", "note"}
            )
            if set(row) != needed:
                raise DataError("Review checklist fields mismatch")
            identifier = (row["section"], row["id"]) if field == "items" else (
                row["id"] if field == "media" else row["system"]
            )
            if identifier in seen or identifier not in expected:
                raise DataError("Duplicate or unrecognized review item")
            seen.add(identifier)
            if row["decision"] not in choices:
                raise DataError("Human reviewer must explicitly choose a valid disposition")
            if not isinstance(row["note"], str) or len(row["note"]) > 1600:
                raise DataError("Review line note invalid")
            if row["decision"] in ("correction_required", "insufficient_evidence",
                                    "inconclusive", "requires_field_inspection") and not row["note"].strip():
                raise DataError("Held review decisions require an explicit explanation")
        if seen != expected:
            raise DataError("Incomplete human review: every item/media/system must be assessed")


def _registered(trust: dict, reviewer_id: str, role: str) -> dict:
    person = next((r for r in trust["reviewers"] if r["reviewer_id"] == reviewer_id), None)
    if person is None or person["role"] != role:
        raise DataError("Reviewer not registered for the requested role")
    return person


def sign_review(workspace: str | Path, trust_file: str | Path,
                private_key_file: str | Path, response: dict) -> dict:
    """Require explicit prepared reviewer choices and a local private Ed25519 key."""
    work, state, _, _ = _get_case(workspace)
    packet = _get_packet(work, state)
    trust_path = Path(trust_file).resolve(strict=True)
    if sha256(trust_path) != packet["trust_file_sha256"]:
        raise DataError("Reviewer key registry changed after review packet preparation")
    trust = _trust(trust_path)
    _response_valid(packet, response)
    person = _registered(trust, response["reviewer_id"], response["role"])
    key_path = Path(private_key_file).resolve(strict=True)
    if key_path.is_relative_to(work) or any((p / ".git").exists() for p in (key_path.parent, *key_path.parents)):
        raise DataError("Private signing key must remain outside case workspace and Git")
    if key_path.stat().st_mode & 0o077:
        raise DataError("Private signing key must be accessible to its owner only")
    key = load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise DataError("Only Ed25519 signing keys supported")
    from cryptography.hazmat.primitives import serialization
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if pub.hex() != person["public_key_hex"]:
        raise DataError("Private key does not match registered review identity")
    signature = key.sign(_bytes(response)).hex()
    envelope = {"schema_version": 1, "payload": response,
                "signature_hex": signature, "key_algorithm": "Ed25519",
                "customer_release_allowed": False}
    target = work / ROLE_FILE[response["role"]]
    if target.exists():
        if _load_json(target) != envelope:
            raise DataError("Review role already signed; cannot replace evidence-bound declaration")
        return {"status": "REUSED", "customer_release_allowed": False}
    _atomic_json(target, envelope)
    return {"status": "SIGNED_INTERNAL_DECLARATION",
            "role": response["role"], "customer_release_allowed": False}


def verify_reviews(workspace: str | Path, trust_file: str | Path) -> dict:
    """Verify both distinct signatures, current source/custody, and complete choices."""
    work, state, _, _ = _get_case(workspace)
    packet = _get_packet(work, state)
    trust_path = Path(trust_file).resolve(strict=True)
    if sha256(trust_path) != packet["trust_file_sha256"]:
        raise DataError("Reviewer key registry has changed")
    trust = _trust(trust_path)
    checked = {}
    for role in ROLES:
        target = work / ROLE_FILE[role]
        if not target.exists():
            continue
        env = _load_json(target)
        if (set(env) != {"schema_version", "payload", "signature_hex", "key_algorithm",
                          "customer_release_allowed"}
            or env["schema_version"] != 1
            or env["key_algorithm"] != "Ed25519"
            or env["customer_release_allowed"] is not False):
            raise DataError("Invalid signed review envelope")
        response = env["payload"]
        _response_valid(packet, response)
        if response["role"] != role:
            raise DataError("Signed review role changed")
        person = _registered(trust, response["reviewer_id"], role)
        try:
            signature = bytes.fromhex(env["signature_hex"])
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(person["public_key_hex"])).verify(signature, _bytes(response))
        except (ValueError, TypeError, InvalidSignature) as exc:
            raise DataError("Human review signature verification failed") from exc
        checked[role] = {
            "reviewer_id": response["reviewer_id"],
            "signed_payload_sha256": _digest(response),
            "items_held": sum(x["decision"] != DECISIONS[0] for x in response["items"]),
            "media_held": sum(x["decision"] != MEDIA_STATES[0] for x in response["media"]),
            "systems_held": sum(x["decision"] != COVERAGE_STATES[0] for x in response["systems"]),
        }
    if len(checked) == 2 and (
        checked[ROLES[0]]["reviewer_id"] == checked[ROLES[1]]["reviewer_id"]
    ):
        raise DataError("Inspector and independent quality signers must be different")
    return {
        "status": "TWO_REGISTERED_SIGNATURES_VERIFIED"
                  if len(checked) == 2 else "HUMAN_REVIEW_INCOMPLETE",
        "signatures_verified": len(checked),
        "required_signatures": 2,
        "reviews": checked,
        "q03_held_entry_count": len(packet["q03_held_entry_ids"]),
        "report_hold_count": len(packet["report_holds"]),
        "professional_license_verified": False,
        "real_world_independence_verified": False,
        "inspector_approved_for_release": False,
        "customer_release_allowed": False,
    }
