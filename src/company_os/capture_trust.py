"""CE-1C3b: independent-root-governed staging attestations and replay audit.

This verifier does NOT mint approvals, fetch sources, authenticate real issuers,
or confer release authority. Its only accepted receipt type is explicitly
UNVERIFIED_OFFLINE_STAGING. The private signer key must be held by a separately
isolated process in an actual deployment; this repository provides no daemon.
The local hash ledger is not externally anchored or privileged-tamper-proof.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .source_provenance import EvidenceError, validate_source_url
from .pdf_evidence import MAX_PDF_BYTES

DOMAIN_POLICY = b"KO-CE1C3B-GOVERNANCE-POLICY-V1\n"
DOMAIN_RECEIPT = b"KO-CE1C3B-STAGING-RECEIPT-V1\n"
_POLICY_KEYS = frozenset({
    "schema_version", "policy_id", "revision", "issued_at", "expires_at",
    "trusted_keys", "revoked_keys", "revoked_receipts", "approved_hosts",
})
_SIGNER_KEYS = frozenset({
    "key_id", "public_key_b64", "roles", "valid_from", "valid_until",
})
_RECEIPT_KEYS = frozenset({
    "schema_version", "receipt_id", "key_id", "sequence", "role",
    "package_id", "document_id", "source_url", "sha256", "bytes_received",
    "media_type", "capture_method", "observed_at", "signed_at",
    "permit_id", "tls_peer_cert_sha256", "pinned_ip",
    "original_issuer_authenticated", "publication_authorized",
})
_ROLES = frozenset({"listing", "pdf"})
_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_POLICY_WINDOW = timedelta(days=7)
_KEY_WINDOW = timedelta(days=365)
_MAX_RECORD_BYTES = 12000


def canonical(obj: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError) as exc:
        raise EvidenceError("noncanonical trust record") from exc


def _id(raw: Any, name: str) -> str:
    if not isinstance(raw, str) or not _ID.fullmatch(raw):
        raise EvidenceError("invalid " + name)
    return raw


def _date(raw: Any, name: str) -> datetime:
    if not isinstance(raw, str) or len(raw) > 48:
        raise EvidenceError("invalid " + name)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid " + name) from exc
    if dt.tzinfo is None:
        raise EvidenceError(name + " lacks timezone")
    return dt.astimezone(timezone.utc)


def _bytes64(raw: Any, name: str, size: int) -> bytes:
    if not isinstance(raw, str):
        raise EvidenceError("invalid " + name)
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceError("invalid " + name) from exc
    if len(data) != size:
        raise EvidenceError("invalid " + name + " length")
    return data


def _verify_signature(public: bytes, signature: Any, msg: bytes) -> None:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise EvidenceError("cryptographic verifier unavailable") from exc
    raw_signature = _bytes64(signature, "signature", 64)
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(raw_signature, msg)
    except (InvalidSignature, ValueError) as exc:
        raise EvidenceError("signature not valid for trusted key") from exc


def _public_ip(raw: Any) -> None:
    if not isinstance(raw, str) or len(raw) > 64:
        raise EvidenceError("invalid pinned IP")
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError as exc:
        raise EvidenceError("invalid pinned IP") from exc
    if (not ip.is_global or ip.is_private or ip.is_reserved
            or ip.is_multicast or ip.is_loopback or ip.is_unspecified
            or ip.is_link_local or getattr(ip, "ipv4_mapped", None) is not None):
        raise EvidenceError("nonpublic pinned IP")


def verify_governance_policy(
    envelope: Mapping[str, Any], *, now: datetime | None = None,
) -> dict[str, Any]:
    """Verify root-signed short-lived trust, key roles and revocations."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(envelope, Mapping) or set(envelope) != {"policy", "signature"}:
        raise EvidenceError("governance envelope malformed")
    body = envelope["policy"]
    if not isinstance(body, dict) or set(body) != _POLICY_KEYS:
        raise EvidenceError("governance fields invalid")
    payload = canonical(body)
    if len(payload) > _MAX_RECORD_BYTES:
        raise EvidenceError("governance policy too large")
    root_pub = _bytes64(
        os.environ.get("KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64", ""),
        "independent governance root public key", 32,
    )
    _verify_signature(root_pub, envelope["signature"], DOMAIN_POLICY + payload)
    if body["schema_version"] != "1.0":
        raise EvidenceError("unsupported governance policy version")
    _id(body["policy_id"], "policy id")
    if type(body["revision"]) is not int or body["revision"] <= 0:
        raise EvidenceError("invalid governance policy revision")
    issued, expires = _date(body["issued_at"], "issued_at"), _date(body["expires_at"], "expires_at")
    if (issued > moment + timedelta(minutes=2) or expires <= moment
            or expires <= issued or expires - issued > _POLICY_WINDOW):
        raise EvidenceError("governance policy expired, future, or overlong")
    if not isinstance(body["approved_hosts"], list) or not 1 <= len(body["approved_hosts"]) <= 32:
        raise EvidenceError("governance host list invalid")
    hosts: set[str] = set()
    for host in body["approved_hosts"]:
        if not isinstance(host, str) or not host.isascii() or host != host.lower():
            raise EvidenceError("governance host invalid")
        validate_source_url("https://" + host + "/", (host,))
        if host in hosts:
            raise EvidenceError("duplicate governance host")
        hosts.add(host)
    configured = os.environ.get("KO_SOURCE_APPROVED_HOSTS", "")
    if not configured or set(configured.split(",")) != hosts:
        raise EvidenceError("signed source registry disagrees with operator's independent host list")
    if not isinstance(body["trusted_keys"], list) or not 1 <= len(body["trusted_keys"]) <= 32:
        raise EvidenceError("trusted capture signers unavailable")
    key_ids: set[str] = set()
    for row in body["trusted_keys"]:
        if not isinstance(row, dict) or set(row) != _SIGNER_KEYS:
            raise EvidenceError("capture signer record fields invalid")
        key_id = _id(row["key_id"], "capture signer id")
        if key_id in key_ids:
            raise EvidenceError("duplicate capture signer id")
        key_ids.add(key_id)
        _bytes64(row["public_key_b64"], "capture signer public key", 32)
        roles = row["roles"]
        if (not isinstance(roles, list) or not roles
                or len(set(roles)) != len(roles) or not set(roles) <= _ROLES):
            raise EvidenceError("capture signer roles invalid")
        start, end = _date(row["valid_from"], "valid_from"), _date(row["valid_until"], "valid_until")
        if end <= start or end - start > _KEY_WINDOW:
            raise EvidenceError("capture signer key validity invalid")
    for field, allowed in (("revoked_keys", key_ids), ("revoked_receipts", None)):
        values = body[field]
        if not isinstance(values, list) or len(values) > 2000:
            raise EvidenceError("revocation list invalid")
        parsed = [_id(value, field) for value in values]
        if len(parsed) != len(set(parsed)):
            raise EvidenceError("duplicate revocation")
        if allowed is not None and not set(parsed) <= allowed:
            raise EvidenceError("revoked key absent from trusted policy")
    return body


def verify_staging_receipt(
    envelope: Mapping[str, Any],
    policy: Mapping[str, Any],
    *, now: datetime | None = None,
) -> dict[str, Any]:
    """Verify signed ORIGINAL BYTE metadata. It is still not issuer-authenticated."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(envelope, Mapping) or set(envelope) != {"receipt", "signature"}:
        raise EvidenceError("staging receipt envelope malformed")
    r = envelope["receipt"]
    if not isinstance(r, dict) or set(r) != _RECEIPT_KEYS:
        raise EvidenceError("staging receipt fields invalid")
    message = canonical(r)
    if len(message) > _MAX_RECORD_BYTES:
        raise EvidenceError("staging receipt too large")
    if r["schema_version"] != "1.0" or r["capture_method"] != "local_staged_bytes_unverified":
        raise EvidenceError("unsupported receipt type or forged transport assertion")
    if r["original_issuer_authenticated"] is not False or r["publication_authorized"] is not False:
        raise EvidenceError("staging receipt cannot assert business authentication or release")
    role = r["role"]
    if role not in _ROLES:
        raise EvidenceError("invalid source role")
    for name in ("receipt_id", "key_id", "package_id", "document_id", "permit_id"):
        _id(r[name], name)
    if type(r["sequence"]) is not int or r["sequence"] <= 0:
        raise EvidenceError("invalid capture sequence")
    if not isinstance(r["sha256"], str) or not _SHA.fullmatch(r["sha256"]):
        raise EvidenceError("invalid staged byte digest")
    if not isinstance(r["tls_peer_cert_sha256"], str) or not _SHA.fullmatch(r["tls_peer_cert_sha256"]):
        raise EvidenceError("invalid staged TLS fingerprint")
    minimum = 100 if role == "pdf" else 30
    maximum = MAX_PDF_BYTES if role == "pdf" else 512_000
    if type(r["bytes_received"]) is not int or not minimum <= r["bytes_received"] <= maximum:
        raise EvidenceError("invalid staged byte count")
    media = "application/pdf" if role == "pdf" else "text/html"
    if r["media_type"] != media:
        raise EvidenceError("staging media type does not match role")
    if role == "listing" and r["document_id"] != "issuer-listing":
        raise EvidenceError("issuer listing id invalid")
    if role == "listing" and r["bytes_received"] > 512000:
        raise EvidenceError("issuer listing too large")
    allowed = tuple(policy["approved_hosts"])
    url = r["source_url"]
    if not isinstance(url, str) or validate_source_url(url, allowed) != url:
        raise EvidenceError("unapproved or noncanonical staged URL")
    _public_ip(r["pinned_ip"])
    captured, signed = _date(r["observed_at"], "receipt observed_at"), _date(r["signed_at"], "receipt signed_at")
    if (signed > moment + timedelta(minutes=2) or signed < captured
            or signed - captured > timedelta(hours=2)
            or moment - captured > timedelta(days=7)):
        raise EvidenceError("staging receipt time inconsistent or stale")
    if role == "listing" and moment - captured > timedelta(hours=24):
        raise EvidenceError("issuer listing capture stale")
    keys = {item["key_id"]: item for item in policy["trusted_keys"]}
    signer = keys.get(r["key_id"])
    if signer is None or r["key_id"] in policy["revoked_keys"]:
        raise EvidenceError("signer untrusted or revoked")
    if role not in signer["roles"]:
        raise EvidenceError("signer not authorized for document role")
    if not (_date(signer["valid_from"], "key valid_from") <= signed <= _date(signer["valid_until"], "key valid_until")):
        raise EvidenceError("signing timestamp outside key validity")
    if r["receipt_id"] in policy["revoked_receipts"]:
        raise EvidenceError("receipt has been revoked")
    _verify_signature(
        _bytes64(signer["public_key_b64"], "signer public key", 32),
        envelope["signature"], DOMAIN_RECEIPT + message,
    )
    return r


class StagingTrustLedger:
    """Private append-only replay ledger with monotonic policy revisions.

    Local hash chains detect accidental tampering, not a privileged rewrite.
    Independent durable anchoring and external identity remain blockers.
    """

    def __init__(self, repo_root: Path | str):
        root = Path(repo_root).resolve()
        if not root.is_dir():
            raise EvidenceError("trust root unavailable")
        self.root = root
        directory = root
        for part in ("state", "competitive_engine", "trust"):
            directory = directory / part
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise EvidenceError("trust state path unsafe")
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not directory.resolve().is_relative_to(root):
                raise EvidenceError("trust state escapes repository")
            if os.name == "posix":
                directory.chmod(0o700)
        self.path = directory / "staging_trust.sqlite3"
        if self.path.is_symlink():
            raise EvidenceError("trust state database symlink forbidden")
        self.db = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                reference_id TEXT NOT NULL,
                key_id TEXT NOT NULL,
                generation INTEGER NOT NULL,
                record_sha TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )""")
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS block_event_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'append-only'); END""")
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS block_event_delete BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'append-only'); END""")
        if os.name == "posix":
            self.path.chmod(0o600)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def _read(self) -> list[tuple]:
        entries = self.db.execute("""
            SELECT seq, kind, reference_id, key_id, generation,
                   record_sha, previous_hash, event_hash
            FROM events ORDER BY seq""").fetchall()
        prev = "GENESIS"
        for pos, event in enumerate(entries, start=1):
            seq, kind, ref, key, generation, digest, prior, event_hash = event
            content = canonical({"seq":seq,"kind":kind,"reference_id":ref,"key_id":key,
                                 "generation":generation,"record_sha":digest})
            expected = hashlib.sha256(prev.encode() + b"\n" + content).hexdigest()
            if (seq != pos or prior != prev or event_hash != expected
                    or kind not in ("policy", "receipt", "revoked_key", "revoked_receipt")):
                raise EvidenceError("trust audit chain integrity failure")
            prev = event_hash
        return entries

    def audit(self) -> dict[str, Any]:
        entries = self._read()
        return {"integrity": "LOCAL_CHAIN_VALID_NOT_EXTERNALLY_ANCHORED",
                "events": len(entries),
                "head_sha256": entries[-1][-1] if entries else "GENESIS",
                "publication_authorized": False}

    def _append(self, kind: str, reference: str, key: str, generation: int, digest: str) -> None:
        old = self._read()
        seq = len(old) + 1
        prior = old[-1][-1] if old else "GENESIS"
        content = canonical({"seq":seq,"kind":kind,"reference_id":reference,
                             "key_id":key,"generation":generation,"record_sha":digest})
        event_hash = hashlib.sha256(prior.encode() + b"\n" + content).hexdigest()
        self.db.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?)",
            (seq, kind, reference, key, generation, digest, prior, event_hash),
        )

    def accept_policy(self, envelope: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        policy = verify_governance_policy(envelope, now=now)
        digest = hashlib.sha256(DOMAIN_POLICY + canonical(policy)).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self._read()
            for row in rows:
                if row[1] == "policy" and row[2] != policy["policy_id"]:
                    raise EvidenceError("governance policy id changed unexpectedly")
            histories = [row for row in rows if row[1] == "policy"]
            # Permanently record revocations as signed-policy-derived chain
            # events. No newer revision may silently restore a revoked key or
            # receipt, even with a valid new governance root signature.
            prior_revoked_keys = {row[2] for row in rows if row[1] == "revoked_key"}
            prior_revoked_receipts = {row[2] for row in rows if row[1] == "revoked_receipt"}
            if (not prior_revoked_keys.issubset(set(policy["revoked_keys"]))
                    or not prior_revoked_receipts.issubset(set(policy["revoked_receipts"]))):
                raise EvidenceError("governance revocation rollback forbidden")
            if histories:
                last = histories[-1]
                if policy["revision"] < last[4] or (
                    policy["revision"] == last[4] and digest != last[5]
                ):
                    raise EvidenceError("governance policy rollback or revision collision")
                if policy["revision"] == last[4]:
                    self.db.commit()
                    return {"state": "SAME_POLICY_RECHECKED", "publication_authorized": False}
            self._append("policy", policy["policy_id"], "root-governance",
                         policy["revision"], digest)
            for key_id in sorted(set(policy["revoked_keys"]) - prior_revoked_keys):
                self._append("revoked_key", key_id, "root-governance",
                             policy["revision"], digest)
            for receipt_id in sorted(set(policy["revoked_receipts"]) - prior_revoked_receipts):
                self._append("revoked_receipt", receipt_id, "root-governance",
                             policy["revision"], digest)
            self.db.commit()
            return {"state": "POLICY_RECORDED_UNANCHORED", "publication_authorized": False}
        except Exception:
            self.db.rollback()
            raise

    def _check_source_file(self, data: Mapping[str, Any]) -> None:
        """Bind the accepted signature to the CURRENT private staged bytes."""
        name = ("issuer-listing.html" if data["role"] == "listing"
                else data["document_id"] + ".pdf")
        candidate = self.root
        for part in ("state", "competitive_engine", "capture_staging",
                     data["package_id"], name):
            candidate = candidate / part
            if candidate.is_symlink() or not candidate.resolve().is_relative_to(self.root):
                raise EvidenceError("signed receipt staged path unsafe")
        if not candidate.is_file():
            raise EvidenceError("signed receipt original file unavailable")
        size = candidate.stat().st_size
        if size != data["bytes_received"]:
            raise EvidenceError("signed receipt file size mismatch")
        original = candidate.read_bytes()
        if len(original) != size or hashlib.sha256(original).hexdigest() != data["sha256"]:
            raise EvidenceError("signed receipt original bytes mismatch")

    def accept_receipt(
        self, receipt: Mapping[str, Any], policy_envelope: Mapping[str, Any],
        *, now: datetime | None = None,
    ) -> dict[str, Any]:
        policy = verify_governance_policy(policy_envelope, now=now)
        data = verify_staging_receipt(receipt, policy, now=now)
        self._check_source_file(data)
        digest = hashlib.sha256(DOMAIN_RECEIPT + canonical(data)).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self._read()
            existing_policies = [r for r in rows if r[1] == "policy"]
            policy_digest = hashlib.sha256(DOMAIN_POLICY + canonical(policy)).hexdigest()
            if (not existing_policies or existing_policies[-1][4] != policy["revision"]
                    or existing_policies[-1][5] != policy_digest):
                raise EvidenceError("signed governance policy not active in replay ledger")
            for event in rows:
                if event[1] != "receipt":
                    continue
                if event[2] == data["receipt_id"]:
                    raise EvidenceError("replayed capture receipt id")
                if event[3] == data["key_id"] and event[4] >= data["sequence"]:
                    raise EvidenceError("capture sequence rollback/replay")
            self._append("receipt", data["receipt_id"], data["key_id"],
                         data["sequence"], digest)
            self.db.commit()
            return {
                "state": "LOCAL_STAGING_RECEIPT_RECORDED_UNVERIFIED_ORIGIN",
                "receipt_id": data["receipt_id"],
                "publication_authorized": False,
                "independent_critic_approved": False,
            }
        except Exception:
            self.db.rollback()
            raise
