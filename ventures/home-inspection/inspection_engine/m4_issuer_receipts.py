"""M4 V6 issuer corroboration receipts: OFFLINE source-bound custody preflight.

Signed evidence captured from association pages or documented issuer contact
is not equivalent to a cryptographic assertion by the issuer. The trusted root
digest must come from an independent, separately governed enrollment system;
a user-chosen digest is insufficient for production. This module NEVER marks a
real credential, real-world identity, or client report release as approved.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import DataError, sha256, safe_path
from .m4_assembly import _digest
from .m4_human_review import _bytes, _get_packet, _trust
from .m4_pipeline import _get_case, _load_json
from .m4_credential_gate import (
    professional_review_preflight, _date, _ident, _sha, _envelope, _registry
)

ISSUER_HOSTS = {
    "ASHI": ("www.homeinspector.org", "homeinspector.org"),
    "INTERNACHI": ("www.nachi.org", "nachi.org"),
}
MAX_CAPTURE_BYTES = 8_000_000
SHA512_SIG = re.compile("[0-9a-f]{128}\\Z")


def _validated_issuer_source(issuer: str, url: str) -> None:
    if issuer not in ISSUER_HOSTS or not isinstance(url, str):
        raise DataError("Issuer is unrecognized; no automatic acceptance")
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname not in ISSUER_HOSTS[issuer]
        or p.username or p.password or p.port not in (None, 443)
        or p.fragment or p.query or not p.path.startswith("/")
        or any(token in p.path for token in ("%2e", "%2E", "//", ".."))):
        raise DataError("Receipt does not reference an approved issuer-controlled URL")
    if issuer == "ASHI" and not p.path.startswith(("/for-consumers/find-an-inspector", "/membership/")):
        raise DataError("ASHI source must be its inspector directory or member channel")
    if issuer == "INTERNACHI" and not p.path.startswith(("/verify/", "/members/", "/certification/")):
        raise DataError("InterNACHI source must be a membership/credential verification channel")


def _capture(root: Path, name: object, expected_digest: object) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute() or (
        ".." in Path(name).parts or "\\" in name or "\x00" in name
    ):
        raise DataError("Issuer evidence path is unsafe")
    raw = root / name
    if any(x.is_symlink() for x in (raw, *[root / Path(*Path(name).parts[:i])
                                           for i in range(1,len(Path(name).parts))])):
        raise DataError("Issuer capture may not use symbolic links")
    path = safe_path(root, name)
    if path.stat().st_size < 64 or path.stat().st_size > MAX_CAPTURE_BYTES:
        raise DataError("Issuer capture file has invalid size")
    if sha256(path) != _sha(expected_digest, "issuer captured bytes"):
        raise DataError("Issuer capture bytes differ from the signed receipt")
    return path


def _verified_anchor(registry: Path, *, expected_sha256: str,
                     reviewer_keys: set[str], officer_keys: set[str],
                     reviewer_ids: set[str], officer_ids: set[str],
                     reviewer_orgs: set[str], officer_orgs: set[str]) -> dict:
    if sha256(registry) != _sha(expected_sha256, "independent issuer root pin"):
        raise DataError("Externally anchored issuer verifier registry digest mismatch")
    root = _load_json(registry)
    needed = {"schema_version", "issuer_verifier_id", "organization_id",
              "public_key_hex", "active", "enrolled_by_external_authority",
              "external_enrollment_reference"}
    if set(root) != needed or root["schema_version"] != 1:
        raise DataError("Issuer verifier root contract invalid")
    signer = _ident(root["issuer_verifier_id"], "issuer verifier identity")
    org = _ident(root["organization_id"], "issuer verifier organization")
    pub = _sha(root["public_key_hex"], "issuer verifier public key")
    if (root["active"] is not True or root["enrolled_by_external_authority"] is not True
        or not isinstance(root["external_enrollment_reference"], str)
        or len(root["external_enrollment_reference"]) < 12):
        raise DataError("Issuer verifier has no explicit external enrollment claim")
    if (signer in reviewer_ids or signer in officer_ids or
        pub in reviewer_keys or pub in officer_keys or
        org in reviewer_orgs or org in officer_orgs):
        raise DataError("Issuer verifier must be independent of reviewers and both officers")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub))
    except ValueError as exc:
        raise DataError("Invalid issuer verifier key") from exc
    return root


def issuer_evidence_preflight(workspace: str | Path,
                              reviewer_trust: str | Path,
                              officer_registry: str | Path,
                              qualification_attestation: str | Path,
                              revocation_attestation: str | Path,
                              proof_root: str | Path,
                              issuer_verifier_registry: str | Path,
                              issuer_receipts: str | Path,
                              issuer_capture_root: str | Path, *,
                              independently_pinned_registry_sha256: str,
                              minimum_revocation_sequence: int,
                              as_of: date | None = None) -> dict:
    """Verify issuer evidence custody + third-role signature; NEVER customer release."""
    when = as_of if as_of is not None else date.today()
    if not isinstance(when, date) or isinstance(when, datetime):
        raise DataError("Calendar date required")
    stage = professional_review_preflight(
        workspace, reviewer_trust, officer_registry,
        qualification_attestation, revocation_attestation, proof_root,
        minimum_revocation_sequence=minimum_revocation_sequence, as_of=when
    )
    if stage["customer_release_allowed"] is not False:
        raise DataError("Untrusted qualification gate release claim")
    work, state, source_root, _ = _get_case(workspace)
    packet = _get_packet(work, state)
    trust_path = Path(reviewer_trust).resolve(strict=True)
    trust = _trust(trust_path)
    officers_path = Path(officer_registry).resolve(strict=True)
    officers = _registry(
        officers_path,
        {r["public_key_hex"] for r in trust["reviewers"]},
        {r["reviewer_id"] for r in trust["reviewers"]}
    )
    verified = _envelope(
        Path(qualification_attestation).resolve(strict=True),
        officers["qualification_officer"]["public_key_hex"],
        officers["qualification_officer"]["officer_id"]
    )
    orgs = {entry["role"]: entry["organization_id"] for entry in verified["reviewers"]}
    anchor_path = Path(issuer_verifier_registry).resolve(strict=True)
    anchor = _verified_anchor(
        anchor_path, expected_sha256=independently_pinned_registry_sha256,
        reviewer_keys={r["public_key_hex"] for r in trust["reviewers"]},
        officer_keys={v["public_key_hex"] for k,v in officers.items() if k!="schema_version"},
        reviewer_ids={r["reviewer_id"] for r in trust["reviewers"]},
        officer_ids={v["officer_id"] for k,v in officers.items() if k!="schema_version"},
        reviewer_orgs=set(orgs.values()),
        officer_orgs={v["organization_id"] for k,v in officers.items() if k!="schema_version"}
    )
    path=Path(issuer_receipts).resolve(strict=True)
    env=_load_json(path)
    if (set(env)!={"schema_version","payload","signature_hex","key_algorithm"}
        or env["schema_version"]!=1 or env["key_algorithm"]!="Ed25519"
        or not isinstance(env["payload"],dict)
        or not isinstance(env["signature_hex"],str)
        or not SHA512_SIG.fullmatch(env["signature_hex"])):
        raise DataError("Issuer evidence receipt envelope invalid")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(anchor["public_key_hex"])).verify(
            bytes.fromhex(env["signature_hex"]),_bytes(env["payload"]))
    except (ValueError, InvalidSignature) as exc:
        raise DataError("Independent issuer evidence receipt signature invalid") from exc
    data=env["payload"]
    needed={"schema_version","issuer_verifier_id","verifier_registry_sha256",
            "officer_registry_sha256","reviewer_registry_sha256","project_id",
            "request_digest","qualifications_digest","checked_on",
            "valid_until","claims","customer_release_allowed"}
    if set(data)!=needed or data["schema_version"]!=1 or data["customer_release_allowed"] is not False:
        raise DataError("Issuer receipt lacks complete bound source contract")
    if (data["issuer_verifier_id"]!=anchor["issuer_verifier_id"]
        or data["verifier_registry_sha256"]!=sha256(anchor_path)
        or data["officer_registry_sha256"]!=sha256(officers_path)
        or data["reviewer_registry_sha256"]!=sha256(trust_path)
        or data["project_id"]!=state["project_id"]
        or data["request_digest"]!=_digest(packet)
        or data["qualifications_digest"]!=_digest(verified)):
        raise DataError("Issuer receipts are stale or from a different case/reviewer/qualification")
    checked=_date(data["checked_on"],"issuer checked")
    valid=_date(data["valid_until"],"issuer valid")
    if not checked<=when<=valid or when-checked>timedelta(days=7) or (
        valid>checked+timedelta(days=7)
    ):
        raise DataError("Issuer corroboration evidence stale, future dated, or expired")
    claims=data["claims"]
    if not isinstance(claims,list) or len(claims)!=2:
        raise DataError("One issuer corroboration receipt per qualified reviewer required")
    capture_root=Path(issuer_capture_root).resolve(strict=True)
    proof=Path(proof_root).resolve(strict=True)
    if (capture_root.is_relative_to(work)
        or capture_root.is_relative_to(source_root)
        or capture_root.is_relative_to(proof)
        or any((x/".git").exists() for x in (capture_root,*capture_root.parents))):
        raise DataError("Issuer evidence must be stored in its own private non-Git area")
    expected={r["role"]:r for r in verified["reviewers"]}
    seen=set()
    for claim in claims:
        required={"role","reviewer_id","qualification_issuer","credential_identifier",
                  "issuer_url","issuer_record_type","association_status_claim",
                  "identity_match_method","captured_at","captured_relative_path",
                  "captured_sha256","evidence_provenance","verifier_notes"}
        if not isinstance(claim,dict) or set(claim)!=required:
            raise DataError("Issuer claim receipt fields missing")
        role=claim["role"]
        if role not in expected or role in seen:
            raise DataError("Issuer claim role missing or duplicated")
        seen.add(role)
        q=expected[role]
        if (claim["reviewer_id"]!=q["reviewer_id"]
            or claim["credential_identifier"]!=q["credential_identifier"]
            or claim["qualification_issuer"]!=q["qualification_issuer"]
            or q["qualification_basis"]!="professional_certification"):
            raise DataError("Issuer corroboration must match a certified reviewer, not a training/experience claim")
        _validated_issuer_source(claim["qualification_issuer"],claim["issuer_url"])
        if claim["issuer_record_type"]!="association_directory_or_direct_response":
            raise DataError("Issuer corroboration requires issuer-side directory or direct response")
        if claim["association_status_claim"]!="active_certification_evidence":
            raise DataError("Issuer evidence cannot claim inactive, membership-only or unverified certification")
        if claim["evidence_provenance"] not in ("verifier_captured_official_page","verifier_documented_issuer_reply"):
            raise DataError("Unsigned, self-supplied issuer evidence is not accepted")
        if (not isinstance(claim["identity_match_method"],str) or
            len(claim["identity_match_method"].strip())<12 or
            not isinstance(claim["verifier_notes"],str) or len(claim["verifier_notes"])<12):
            raise DataError("Issuer identity and certification match require documented method")
        captured=_date(claim["captured_at"],"issuer source captured")
        if not checked-timedelta(days=1)<=captured<=checked:
            raise DataError("Issuer capture not contemporaneous with verification")
        _capture(capture_root,claim["captured_relative_path"],claim["captured_sha256"])
    if seen!=set(expected):
        raise DataError("Incomplete issuer corroboration coverage")
    return {
        "status":"ISSUER_SOURCE_CUSTODY_AND_INDEPENDENT_SIGNATURE_VERIFIED_ONLY",
        "issuer_captured_sources_bound":2,
        "registered_verifier_signature_verified":True,
        "review_signatures_verified":stage["review_signatures_verified"],
        "claims_current_as_of":when.isoformat(),
        "independent_official_issuer_authenticity_verified":False,
        "out_of_band_verifier_enrollment_independently_verified":False,
        "real_identity_independently_authenticated":False,
        "qualified_for_customer_release":False,
        "customer_release_allowed":False,
    }
