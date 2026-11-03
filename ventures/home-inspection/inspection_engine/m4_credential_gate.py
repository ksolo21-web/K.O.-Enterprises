"""M4 offline professional-review PRECHECK, not legal qualification or release.

A verified Ed25519 signature proves control of a key; external professional
identity, issuer status, practice competence and legislative applicability all
require corroboration by qualified, externally trusted parties. This gate
enforces evidence binding, organization independence, trusted separation,
fresh revocation attestations, expiry, and a jurisdictional policy snapshot.

No network calls, assessor account provisioning, real credential verification,
Q03 hold clearance, release approval, or update of original review records.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import DataError, sha256, safe_path
from .m4_assembly import _digest
from .m4_pipeline import _get_case, _load_json
from .m4_human_review import _bytes, _trust, _get_packet, verify_reviews, ROLES

POLICY = Path(__file__).resolve().parents[1] / "knowledge" / "m4_michigan_reviewer_policy_v1.json"
QUALIFICATIONS = {"professional_certification", "professional_training", "documented_field_experience"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,63}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")


def _date(value: object, name: str) -> date:
    if not isinstance(value, str):
        raise DataError("Missing ISO date: " + name)
    try:
        out = date.fromisoformat(value)
    except ValueError as exc:
        raise DataError("Invalid date: " + name) from exc
    if out.isoformat() != value:
        raise DataError("Noncanonical ISO date: " + name)
    return out


def _ident(value: object, name: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise DataError("Invalid " + name)
    return value


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise DataError("Invalid SHA256 " + name)
    return value


def _registry(path: Path, reviewer_keys: set[str], reviewer_ids: set[str]) -> dict:
    reg = _load_json(path)
    if reg.get("schema_version") != 1 or set(reg) != {"schema_version", "qualification_officer", "revocation_officer"}:
        raise DataError("Professional-review officer registry contract invalid")
    officer_keys, officer_ids, officer_orgs = set(), set(), set()
    for role in ("qualification_officer", "revocation_officer"):
        o = reg[role]
        if not isinstance(o, dict) or set(o) != {"officer_id", "public_key_hex", "active", "organization_id"}:
            raise DataError("Officer registration fields invalid")
        ident = _ident(o["officer_id"], "officer ID")
        key = _sha(o["public_key_hex"], "officer public key")
        org = _ident(o["organization_id"], "officer organization")
        if o["active"] is not True or key in reviewer_keys or ident in reviewer_ids:
            raise DataError("Reviewer cannot self-verify professional qualifications or revocations")
        if ident in officer_ids or key in officer_keys or org in officer_orgs:
            raise DataError("Qualification and revocation officers and organizations must be different")
        officer_ids.add(ident)
        officer_keys.add(key)
        officer_orgs.add(org)
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key))
        except ValueError as exc:
            raise DataError("Invalid Ed25519 officer public key") from exc
    return reg


def _envelope(path: Path, pub: str, expected_signer: str) -> dict:
    env = _load_json(path)
    if (set(env) != {"schema_version", "payload", "signature_hex", "key_algorithm"}
        or env["schema_version"] != 1 or env["key_algorithm"] != "Ed25519"
        or not isinstance(env["payload"], dict)):
        raise DataError("Signed professional credential envelope malformed")
    payload = env["payload"]
    if payload.get("signer_id") != expected_signer:
        raise DataError("Unrecognized credential verifier signature identity")
    sig = env["signature_hex"]
    if not isinstance(sig, str) or not re.fullmatch(r"[0-9a-f]{128}", sig):
        raise DataError("Credential signature encoding invalid")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            bytes.fromhex(sig), _bytes(payload))
    except (InvalidSignature, ValueError) as exc:
        raise DataError("Credential/revocation attestation signature invalid") from exc
    return payload


def _policy(*, as_of: date) -> dict:
    policy = _load_json(POLICY)
    fields = {"schema_version", "policy_id", "jurisdiction", "scope",
              "state_home_inspector_license", "snapshot_date", "recheck_by",
              "sources", "professional_basis"}
    if set(policy) != fields or policy["schema_version"] != 1 or (
        policy["jurisdiction"] != "US-MI"
        or policy["scope"] != "private_residential_visual_home_inspection"
        or policy["state_home_inspector_license"] != "not_issued_for_general_home_inspection"
        or policy["professional_basis"] != "documented_competence_not_imaginary_state_license"
    ):
        raise DataError("Michigan qualification policy not approved or unknown")
    now = _date(policy["snapshot_date"], "policy snapshot")
    until = _date(policy["recheck_by"], "policy recheck")
    if not now <= as_of <= until or until > now + timedelta(days=45):
        raise DataError("Jurisdictional legal-status policy is stale or future dated")
    sources = policy["sources"]
    if not isinstance(sources, list) or len(sources) < 2:
        raise DataError("Michigan authority source references missing")
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"label", "url"}:
            raise DataError("Jurisdiction policy source fields incomplete")
        parsed = urlsplit(source["url"])
        if parsed.scheme != "https" or parsed.hostname not in ("www.michigan.gov", "nationalhomeinspectorexam.org"):
            raise DataError("Unknown jurisdictional policy authority")
    return policy


def professional_review_preflight(workspace: str | Path,
                                  reviewer_trust: str | Path,
                                  officer_registry: str | Path,
                                  qualification_attestation: str | Path,
                                  revocation_attestation: str | Path,
                                  proof_root: str | Path, *,
                                  minimum_revocation_sequence: int,
                                  as_of: date | None = None) -> dict:
    """Return internal precheck only when every required evidence gate passes.

    A complete pass establishes consistency of locally supplied signed records,
    not real legal authority, independent identity proof, or report release.
    """
    if type(minimum_revocation_sequence) is not int or minimum_revocation_sequence < 1:
        raise DataError("A trusted external minimum revocation sequence is required")
    when = as_of if as_of is not None else date.today()
    if not isinstance(when, date) or isinstance(when, __import__("datetime").datetime):
        raise DataError("Preflight date must be a calendar date")
    work, state, source_root, original = _get_case(workspace)
    packet = _get_packet(work, state)
    reviews = verify_reviews(work, reviewer_trust)
    if reviews["signatures_verified"] != 2:
        raise DataError("Both distinct human review signatures must be complete")
    policy = _policy(as_of=when)
    # A synthetic case without geographic metadata may exercise this machinery
    # only as a simulated MI case, never as evidence of legal applicability.
    reported_jurisdiction = original["property"].get("jurisdiction")
    if not original["property"].get("synthetic", False) and reported_jurisdiction != "US-MI":
        raise DataError("Actual property jurisdiction must be independently established")
    if reported_jurisdiction not in (None, "US-MI"):
        raise DataError("Property jurisdiction conflicts with Michigan policy")
    trust_path = Path(reviewer_trust).resolve(strict=True)
    trust = _trust(trust_path)
    officers = _registry(
        Path(officer_registry).resolve(strict=True),
        {r["public_key_hex"] for r in trust["reviewers"]},
        {r["reviewer_id"] for r in trust["reviewers"]})
    qualification = _envelope(
        Path(qualification_attestation).resolve(strict=True),
        officers["qualification_officer"]["public_key_hex"],
        officers["qualification_officer"]["officer_id"])
    revocations = _envelope(
        Path(revocation_attestation).resolve(strict=True),
        officers["revocation_officer"]["public_key_hex"],
        officers["revocation_officer"]["officer_id"])
    basic = {"schema_version", "signer_id", "project_id", "request_digest",
             "trust_sha256", "officer_registry_sha256", "policy_sha256",
             "jurisdiction", "checked_on", "valid_until", "reviewers"}
    if set(qualification) != basic or qualification["schema_version"] != 1:
        raise DataError("Incomplete qualification attestation")
    if (qualification["project_id"] != state["project_id"]
        or qualification["request_digest"] != _digest(packet)
        or qualification["trust_sha256"] != sha256(trust_path)
        or qualification["officer_registry_sha256"] != sha256(Path(officer_registry))
        or qualification["policy_sha256"] != sha256(POLICY)
        or qualification["jurisdiction"] != "US-MI"):
        raise DataError("Qualifications not bound to this case, law snapshot, or trusted keys")
    checked = _date(qualification["checked_on"], "qualification checked")
    valid = _date(qualification["valid_until"], "qualification expiry")
    if not checked <= when <= valid or valid > checked + timedelta(days=30):
        raise DataError("Qualification check expired, future-dated, or overlong")
    if not isinstance(qualification["reviewers"], list) or len(qualification["reviewers"]) != 2:
        raise DataError("Two complete professional qualification records required")
    index = {r["role"]: r for r in trust["reviewers"]}
    present = set()
    organizations = set()
    proot = Path(proof_root).resolve(strict=True)
    if proot.is_relative_to(work) or proot.is_relative_to(source_root) or any(
        (parent / ".git").exists() for parent in (proot, *proot.parents)
    ):
        raise DataError("Credential proof files cannot be kept inside a case or Git checkout")
    for record in qualification["reviewers"]:
        needed = {"reviewer_id", "role", "public_key_hex", "organization_id",
                  "qualification_basis", "qualification_issuer", "credential_identifier",
                  "scope", "evidence_path", "evidence_sha256", "verified_on",
                  "valid_until", "identity_checked_method", "independence_checked",
                  "conflict_declared"}
        if not isinstance(record, dict) or set(record) != needed:
            raise DataError("Credential evidence record missing a required field")
        role = record["role"]
        if role not in ROLES or role in present:
            raise DataError("Missing or repeated credential role")
        present.add(role)
        signer = index[role]
        if record["reviewer_id"] != signer["reviewer_id"] or record["public_key_hex"] != signer["public_key_hex"]:
            raise DataError("Credential does not identify the signed report reviewer")
        org = _ident(record["organization_id"], "reviewer organization")
        if org == officers["qualification_officer"]["organization_id"] or (
            org == officers["revocation_officer"]["organization_id"]
        ) or org in organizations:
            raise DataError("Independence failure: reviewer and verifier organizations overlap")
        organizations.add(org)
        if record["qualification_basis"] not in QUALIFICATIONS:
            raise DataError("Unknown professional competency basis")
        for label in ("qualification_issuer", "credential_identifier", "scope", "identity_checked_method"):
            val = record[label]
            if not isinstance(val, str) or not 6 <= len(val.strip()) <= 320:
                raise DataError("Missing substantive qualification metadata: " + label)
        if (record["scope"] != "private_residential_visual_home_inspection"
            or record["independence_checked"] is not True
            or record["conflict_declared"] is not False):
            raise DataError("Qualification scope or reviewer conflicts fail the gate")
        verified_on = _date(record["verified_on"], "credential verified")
        until = _date(record["valid_until"], "credential valid until")
        if not verified_on <= when <= until or when > verified_on + timedelta(days=30):
            raise DataError("Professional qualification evidence is expired or stale")
        rel = record["evidence_path"]
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise DataError("Unsafe qualification evidence path")
        raw = proot / rel
        if any(part.is_symlink() for part in (raw, *list(raw.parents)[:len(Path(rel).parts)])):
            raise DataError("Symlinked qualification evidence is prohibited")
        proof = safe_path(proot, rel)
        if not proof.is_relative_to(proot):
            raise DataError("Unsafe external qualification proof")
        if sha256(proof) != _sha(record["evidence_sha256"], "professional credential proof"):
            raise DataError("Professional qualification proof has changed")
    if present != set(ROLES):
        raise DataError("Both professional reviewer roles required")

    rev_fields = {"schema_version", "signer_id", "project_id", "request_digest",
                  "trust_sha256", "checked_on", "valid_until", "revoked_reviewer_ids",
                  "revoked_officer_ids", "revocation_sequence"}
    if set(revocations) != rev_fields or revocations["schema_version"] != 1:
        raise DataError("Revocation attestation contract invalid")
    if (revocations["project_id"] != state["project_id"]
        or revocations["request_digest"] != _digest(packet)
        or revocations["trust_sha256"] != sha256(trust_path)):
        raise DataError("Revocation evidence is not bound to the reviewed case")
    rev_on = _date(revocations["checked_on"], "revocation checked")
    rev_until = _date(revocations["valid_until"], "revocation expiry")
    if (rev_on > when or rev_until < when or rev_until > rev_on + timedelta(days=2)
        or when - rev_on > timedelta(days=1)):
        raise DataError("Revocation attestation expired, stale or future-dated")
    if type(revocations["revocation_sequence"]) is not int or (
        revocations["revocation_sequence"] < minimum_revocation_sequence
    ):
        raise DataError("Revocation sequence is missing, stale, or rolled back")
    for field in ("revoked_reviewer_ids", "revoked_officer_ids"):
        entries = revocations[field]
        if not isinstance(entries, list) or any(not isinstance(x, str) for x in entries) or len(entries) != len(set(entries)):
            raise DataError("Revocation list malformed")
    if ({r["reviewer_id"] for r in trust["reviewers"]} & set(revocations["revoked_reviewer_ids"])
        or {o["officer_id"] for role, o in officers.items() if role != "schema_version"} & set(revocations["revoked_officer_ids"])):
        raise DataError("Revoked reviewer or verifier cannot pass professional preflight")
    return {
        "status": "LOCAL_SIGNED_CREDENTIAL_EVIDENCE_PRECHECK_ONLY",
        "review_signatures_verified": reviews["signatures_verified"],
        "verified_credential_proof_files": 2,
        "qualification_attestation_signature_verified": True,
        "fresh_revocation_signature_verified": True,
        "minimum_revocation_sequence_enforced": minimum_revocation_sequence,
        "distinct_organizations_declared": True,
        "jurisdiction": "US-MI",
        "jurisdiction_snapshot_current_in_bundle": True,
        "real_identity_independently_authenticated": False,
        "professional_issuer_live_checked": False,
        "statutory_local_requirements_verified": False,
        "competence_field_benchmarked": False,
        "qualified_for_customer_release": False,
        "customer_release_allowed": False,
    }
