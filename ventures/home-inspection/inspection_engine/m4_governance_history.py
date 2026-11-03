"""M4 V7: offline, witnessed, two-governor verifier enrollment/revocation history.

This is cryptographic integrity checking, NOT proof of real-world identity.
The genesis digest, latest head digest, and witness key MUST be independently
anchored outside this local operator's custody. Never derive pins from the
same candidate files being checked. All outputs remain PRIVATE/NO RELEASE.

No signing keys, live trust services, API calls, customer files or model
downloads are present here. Synthetic tests generate ephemeral signatures.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import DataError, sha256
from .m4_assembly import _digest
from .m4_pipeline import _load_json, _get_case
from .m4_human_review import _bytes, _trust
from .m4_credential_gate import _date, _ident, _sha, _registry, _envelope
from .m4_issuer_receipts import issuer_evidence_preflight, _verified_anchor

ZERO_HASH = "0" * 64
SIG_RE = re.compile(r"[0-9a-f]{128}\Z")
NONCE_RE = re.compile(r"[0-9a-f]{32,64}\Z")
EVENTS = {"enroll_issuer_verifier", "revoke_issuer_verifier"}
MAX_EVENTS = 4096
MAX_HISTORY_BYTES = 3_000_000

GENESIS_FIELDS = {"schema_version", "trust_domain", "jurisdiction", "trustees", "customer_release_allowed"}
TRUSTEE_FIELDS = {"trustee_id", "public_key_hex", "organization_id"}
PAYLOAD_FIELDS = {"schema_version", "event_sequence", "previous_event_sha256",
                  "action", "subject_id", "subject_public_key_hex",
                  "subject_organization_id", "subject_registry_sha256",
                  "effective_on", "nonce_hex", "reason_sha256",
                  "customer_release_allowed"}
WITNESS_FIELDS = {"schema_version", "witness_id", "witness_organization_id",
                  "witness_public_key_hex", "genesis_sha256", "head_sha256",
                  "event_sequence", "latest_event_date", "witnessed_on",
                  "valid_until", "customer_release_allowed"}
SIGNED_FIELDS = {"schema_version", "payload", "signatures"}
WITNESS_ENVELOPE_FIELDS = {"schema_version", "payload", "signature_hex", "key_algorithm"}


def _pub(hex_value: object, name: str) -> Ed25519PublicKey:
    value = _sha(hex_value, name)
    try:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise DataError("Malformed Ed25519 public key: " + name) from exc


def _verify(pub: Ed25519PublicKey, signature: object, payload: dict, what: str) -> None:
    if not isinstance(signature, str) or SIG_RE.fullmatch(signature) is None:
        raise DataError("Invalid signature encoding: " + what)
    try:
        pub.verify(bytes.fromhex(signature), _bytes(payload))
    except (ValueError, InvalidSignature) as exc:
        raise DataError("Invalid signed trust history: " + what) from exc


def _read(path: str | Path) -> dict:
    resolved = Path(path).resolve(strict=True)
    if resolved.stat().st_size > MAX_HISTORY_BYTES:
        raise DataError("Governance history exceeds safe file size")
    return _load_json(resolved)


def verify_governance_history(
    history_file: str | Path,
    witness_file: str | Path,
    *,
    independently_pinned_genesis_sha256: str,
    independently_pinned_head_sha256: str,
    independently_pinned_witness_public_key_hex: str,
    minimum_event_sequence: int,
    as_of: date | None = None,
) -> dict:
    """Verify complete signed history and newest signed witness checkpoint.

    An "independently_pinned_*" argument is a caller-supplied TRUST INPUT.
    This function cannot verify that the caller obtained it out of band.
    """
    when = as_of if as_of is not None else date.today()
    if not isinstance(when, date) or isinstance(when, datetime):
        raise DataError("Governance check needs a calendar date")
    for name, value in (
        ("genesis external pin", independently_pinned_genesis_sha256),
        ("head external pin", independently_pinned_head_sha256),
        ("witness public key external pin", independently_pinned_witness_public_key_hex),
    ):
        _sha(value, name)
    if type(minimum_event_sequence) is not int or minimum_event_sequence < 1:
        raise DataError("Independent minimum governance sequence required")
    ledger = _read(history_file)
    if set(ledger) != {"schema_version", "genesis", "events"} or ledger["schema_version"] != 1:
        raise DataError("Governance history envelope invalid")
    genesis = ledger["genesis"]
    if (not isinstance(genesis, dict) or set(genesis) != GENESIS_FIELDS
        or genesis["schema_version"] != 1
        or genesis["trust_domain"] != "M4_PRIVATE_INSPECTION_REVIEW"
        or genesis["jurisdiction"] != "US-MI"
        or genesis["customer_release_allowed"] is not False):
        raise DataError("Governance genesis contract invalid")
    genesis_hash = _digest(genesis)
    if genesis_hash != independently_pinned_genesis_sha256:
        raise DataError("Independently pinned genesis differs from current governance roots")
    trustees = genesis["trustees"]
    if not isinstance(trustees, list) or len(trustees) != 2:
        raise DataError("Two independent governance root trustees required")
    trustee_ids, trustee_keys, trustee_orgs, governors = set(), set(), set(), {}
    for item in trustees:
        if not isinstance(item, dict) or set(item) != TRUSTEE_FIELDS:
            raise DataError("Governance trustee schema invalid")
        ident = _ident(item["trustee_id"], "governance trustee")
        key = _sha(item["public_key_hex"], "trustee public key")
        org = _ident(item["organization_id"], "trustee organization")
        if ident in trustee_ids or key in trustee_keys or org in trustee_orgs:
            raise DataError("Independent governance trustee identities, keys and organizations required")
        trustee_ids.add(ident)
        trustee_keys.add(key)
        trustee_orgs.add(org)
        governors[ident] = _pub(key, "trustee public key")
    events = ledger["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS:
        raise DataError("Governance history requires bounded nonempty event sequence")

    previous = ZERO_HASH
    active: dict[str, dict] = {}
    all_subject_ids, all_subject_keys, all_subject_orgs = set(), set(), set()
    revoked_ids = set()
    nonces = set()
    latest_date = None
    for number, env in enumerate(events, start=1):
        if not isinstance(env, dict) or set(env) != SIGNED_FIELDS or env["schema_version"] != 1:
            raise DataError("Governance signed event envelope malformed")
        payload = env["payload"]
        if (not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS
            or payload["schema_version"] != 1
            or payload["customer_release_allowed"] is not False):
            raise DataError("Governance event contains unsupported fields or release claim")
        if type(payload["event_sequence"]) is not int or payload["event_sequence"] != number:
            raise DataError("Missing or reordered governance event")
        if payload["previous_event_sha256"] != previous:
            raise DataError("Governance chain broken, event reordered, or history edited")
        if payload["action"] not in EVENTS:
            raise DataError("Unknown governance event action")
        nonce = payload["nonce_hex"]
        if not isinstance(nonce, str) or NONCE_RE.fullmatch(nonce) is None or nonce in nonces:
            raise DataError("Missing or reused governance signing challenge nonce")
        nonces.add(nonce)
        when_event = _date(payload["effective_on"], "governance event")
        if when_event > when or (latest_date is not None and when_event < latest_date):
            raise DataError("Governance event is future dated or out of chronological order")
        latest_date = when_event
        subject_id = _ident(payload["subject_id"], "governed verifier ID")
        subject_org = _ident(payload["subject_organization_id"], "governed verifier organization")
        pubhex = _sha(payload["subject_public_key_hex"], "governed verifier key")
        reg_sha = _sha(payload["subject_registry_sha256"], "governed verifier registry digest")
        reason = _sha(payload["reason_sha256"], "governance reason receipt digest")
        if reason == ZERO_HASH or reg_sha == ZERO_HASH:
            raise DataError("Governance event lacks external evidence receipt")
        if subject_id in trustee_ids or pubhex in trustee_keys or subject_org in trustee_orgs:
            raise DataError("Governed verifier may not also govern enrollment authority")
        signer_rows = env["signatures"]
        if not isinstance(signer_rows, list) or len(signer_rows) != 2:
            raise DataError("Both independent governance signatures are required")
        seen = set()
        for entry in signer_rows:
            if not isinstance(entry, dict) or set(entry) != {"trustee_id", "signature_hex"}:
                raise DataError("Governance signature row invalid")
            trustee_id = entry["trustee_id"]
            if trustee_id not in governors or trustee_id in seen:
                raise DataError("Missing, duplicated, or unauthorized governance trustee signature")
            seen.add(trustee_id)
            _verify(governors[trustee_id], entry["signature_hex"], payload, "governor event")
        if seen != trustee_ids:
            raise DataError("Every governance trustee must endorse every event")

        subject = {"subject_id": subject_id, "public_key_hex": pubhex,
                   "organization_id": subject_org, "registry_sha256": reg_sha}
        if payload["action"] == "enroll_issuer_verifier":
            if subject_id in all_subject_ids or pubhex in all_subject_keys or subject_org in all_subject_orgs:
                raise DataError("Reused verifier ID/key/organization cannot be re-enrolled")
            _pub(pubhex, "governed verifier key")
            all_subject_ids.add(subject_id)
            all_subject_keys.add(pubhex)
            all_subject_orgs.add(subject_org)
            active[subject_id] = subject
        else:
            if subject_id not in active or active[subject_id] != subject:
                raise DataError("Revocation targets wrong or previously revoked enrollment")
            del active[subject_id]
            revoked_ids.add(subject_id)
        previous = _digest(env)

    if len(events) < minimum_event_sequence or previous != independently_pinned_head_sha256:
        raise DataError("History truncated, stale, or not equal to independently pinned head")

    wrapper = _read(witness_file)
    if (set(wrapper) != WITNESS_ENVELOPE_FIELDS
        or wrapper["schema_version"] != 1
        or wrapper["key_algorithm"] != "Ed25519"):
        raise DataError("Independent witness record is malformed")
    signed = wrapper["payload"]
    if (not isinstance(signed, dict) or set(signed) != WITNESS_FIELDS
        or signed["schema_version"] != 1
        or signed["customer_release_allowed"] is not False):
        raise DataError("Witness checkpoint schema invalid")
    wid = _ident(signed["witness_id"], "witness identity")
    worg = _ident(signed["witness_organization_id"], "witness organization")
    wkey = _sha(signed["witness_public_key_hex"], "witness signing key")
    if wid in trustee_ids or worg in trustee_orgs or wkey in trustee_keys:
        raise DataError("History witness cannot be a governance trustee")
    if wkey != independently_pinned_witness_public_key_hex:
        raise DataError("Witness signer differs from independent witness key pin")
    _verify(_pub(wkey, "witness key"), wrapper["signature_hex"], signed, "independent witness")
    if (signed["genesis_sha256"] != genesis_hash
        or signed["head_sha256"] != previous
        or type(signed["event_sequence"]) is not int
        or signed["event_sequence"] != len(events)
        or signed["latest_event_date"] != latest_date.isoformat()):
        raise DataError("Witness not bound to exact event history and pinned roots")
    observed = _date(signed["witnessed_on"], "witness observation")
    expires = _date(signed["valid_until"], "witness expiry")
    if (not latest_date <= observed <= when <= expires
        or when - observed > timedelta(days=1)
        or expires > observed + timedelta(days=2)):
        raise DataError("Witness not current or predates the governed events")
    for subject in active.values():
        if (subject["subject_id"] == wid or
            subject["public_key_hex"] == wkey or
            subject["organization_id"] == worg):
            raise DataError("Active verifier overlaps supposedly independent witness")

    return {
        "status": "SIGNED_MULTI_PARTY_HISTORY_AND_EXTERNAL_PINS_MATCH_ONLY",
        "genesis_sha256": genesis_hash,
        "head_sha256": previous,
        "event_sequence": len(events),
        "latest_event_date": latest_date.isoformat(),
        "active_verifiers": list(active.values()),
        "revoked_verifier_ids": sorted(revoked_ids),
        "witness_id": wid,
        "witness_public_key_hex": wkey,
        "witness_organization_id": worg,
        "trustee_identities": list(trustees),
        "external_pin_origin_independently_authenticated": False,
        "real_world_governance_independence_verified": False,
        "external_credential_issuer_status_verified": False,
        "customer_release_allowed": False,
    }


def governed_issuer_evidence_preflight(
    workspace: str | Path,
    reviewer_trust: str | Path,
    officer_registry: str | Path,
    qualification_attestation: str | Path,
    revocation_attestation: str | Path,
    proof_root: str | Path,
    issuer_verifier_registry: str | Path,
    issuer_receipts: str | Path,
    issuer_capture_root: str | Path,
    governance_history: str | Path,
    independent_witness: str | Path,
    *,
    independently_pinned_genesis_sha256: str,
    independently_pinned_head_sha256: str,
    independently_pinned_witness_public_key_hex: str,
    minimum_event_sequence: int,
    minimum_revocation_sequence: int,
    as_of: date | None = None,
) -> dict:
    """Compose V5+V6+V7 read-only gates; never approve legal credentials/release."""
    work, _, original_root, _ = _get_case(workspace)
    history_path = Path(governance_history).resolve(strict=True)
    witness_path = Path(independent_witness).resolve(strict=True)
    for name, loc in (("governance history", history_path), ("witness checkpoint", witness_path)):
        if (loc.is_relative_to(work) or loc.is_relative_to(original_root)
            or any((p / ".git").exists() for p in (loc.parent, *loc.parents))):
            raise DataError("Private " + name + " may not be kept in case, source, or Git")
    history = verify_governance_history(
        history_path, witness_path,
        independently_pinned_genesis_sha256=independently_pinned_genesis_sha256,
        independently_pinned_head_sha256=independently_pinned_head_sha256,
        independently_pinned_witness_public_key_hex=independently_pinned_witness_public_key_hex,
        minimum_event_sequence=minimum_event_sequence, as_of=as_of
    )
    issuer_path = Path(issuer_verifier_registry).resolve(strict=True)
    issuer_registry = _load_json(issuer_path)
    active = [x for x in history["active_verifiers"]
              if x["subject_id"] == issuer_registry.get("issuer_verifier_id")]
    if len(active) != 1:
        raise DataError("Issuer verifier has no active witnessed governance enrollment")
    enrolled = active[0]
    if (enrolled["registry_sha256"] != sha256(issuer_path)
        or enrolled["public_key_hex"] != issuer_registry.get("public_key_hex")
        or enrolled["organization_id"] != issuer_registry.get("organization_id")):
        raise DataError("Issuer verifier key, organization, or registry is not governed")
    # Trusted trustees and witness must be disjoint from the signed reviewers
    # and two V5 officers by ID, key and declared organization.
    trust = _trust(Path(reviewer_trust).resolve(strict=True))
    officer_reg = _registry(
        Path(officer_registry).resolve(strict=True),
        {r["public_key_hex"] for r in trust["reviewers"]},
        {r["reviewer_id"] for r in trust["reviewers"]}
    )
    qoff = officer_reg["qualification_officer"]
    qualification = _envelope(
        Path(qualification_attestation).resolve(strict=True),
        qoff["public_key_hex"], qoff["officer_id"]
    )
    others = (
        [{"id": r["reviewer_id"], "key": r["public_key_hex"],
          "org": next((q.get("organization_id") for q in qualification.get("reviewers", [])
                       if q.get("reviewer_id") == r["reviewer_id"]), "")}
         for r in trust["reviewers"]]
        + [{"id": o["officer_id"], "key": o["public_key_hex"], "org": o["organization_id"]}
           for k,o in officer_reg.items() if k != "schema_version"]
        + [{"id": issuer_registry["issuer_verifier_id"],
            "key": issuer_registry["public_key_hex"],
            "org": issuer_registry["organization_id"]}]
    )
    protected_ids = {x["id"] for x in others}
    protected_keys = {x["key"] for x in others}
    protected_orgs = {x["org"] for x in others}
    governance_people = [
        {"id": x["trustee_id"], "key": x["public_key_hex"], "org": x["organization_id"]}
        for x in history["trustee_identities"]
    ] + [{"id": history["witness_id"],
          "key": history["witness_public_key_hex"],
          "org": history["witness_organization_id"]}]
    if any(x["id"] in protected_ids or x["key"] in protected_keys
           or x["org"] in protected_orgs for x in governance_people):
        raise DataError("Witness/governance trustees cannot overlap review/qualification/issuer roles")
    v6 = issuer_evidence_preflight(
        workspace, reviewer_trust, officer_registry,
        qualification_attestation, revocation_attestation, proof_root,
        issuer_verifier_registry, issuer_receipts, issuer_capture_root,
        independently_pinned_registry_sha256=enrolled["registry_sha256"],
        minimum_revocation_sequence=minimum_revocation_sequence, as_of=as_of
    )
    if v6["customer_release_allowed"] is not False:
        raise DataError("Unsafe V6 customer release flag")
    return {
        "status": "V7_OFFLINE_GOVERNED_ISSUER_EVIDENCE_CUSTODY_ONLY",
        "previous_v6_status": v6["status"],
        "governance_event_sequence": history["event_sequence"],
        "governance_head_sha256": history["head_sha256"],
        "active_issuer_verifier_enrollment_checked": True,
        "witness_signature_and_history_verified": True,
        "out_of_band_pins_independently_proven": False,
        "real_verifier_identity_authenticated": False,
        "professional_certification_issuer_authenticity_verified": False,
        "professional_release_authorized": False,
        "customer_release_allowed": False,
    }
