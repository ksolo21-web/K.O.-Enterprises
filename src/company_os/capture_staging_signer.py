"""CE-1C3b local-staging receipt issuer: use ONLY in a separately isolated signer.

This function receives an already-unlocked PRIVATE Ed25519 signer object,
NEVER looks up a private key from the source-fetcher's environment, and is
NOT imported into the approved PDF downloader. It will ONLY attest that a
private staged file matches an *unverified* StageSource metadata record.

This does not authenticate TLS/issuer provenance. Production capture-signing
requires a separate approved service, protected HSM/key custody, authenticated
transport evidence, audit anchoring, revocation and isolated credentials.
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .approved_pdf_capture import StagedSource
from .capture_trust import (
    DOMAIN_RECEIPT, _date, _id, _public_ip, canonical,
)
from .pdf_evidence import MAX_PDF_BYTES
from .source_provenance import EvidenceError, validate_source_url


def attest_local_staging(
    *,
    repo_root: Path | str,
    staged: StagedSource,
    key_id: str,
    receipt_id: str,
    sequence: int,
    signer: Any,
    signed_at: datetime | None = None,
) -> dict[str, Any]:
    """Generate ONLY an Ed25519 unverified-staging attestation, not a source receipt.

    The private key is a separate-deployment injected object, never loaded from
    a production fetcher's environment or a path in the public repo.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise EvidenceError("staging signer dependency unavailable") from exc
    if not isinstance(signer, Ed25519PrivateKey):
        raise EvidenceError("staging private signer must be injected by an isolated issuer")
    if not isinstance(staged, StagedSource):
        raise EvidenceError("staging receipt requires immutable StagedSource")
    if (staged.state != "UNSIGNED_CAPTURE_REQUIRES_SEPARATE_ATTESTATION"
            or staged.original_issuer_authenticated is not False
            or staged.capture_receipt_signed is not False
            or staged.independent_critic_approved is not False
            or staged.publication_authorized is not False):
        raise EvidenceError("staged metadata claims unsupported authentication or release")
    _id(key_id, "capture signer key id")
    _id(receipt_id, "capture receipt id")
    _id(staged.package_id, "capture package id")
    _id(staged.document_id, "capture document id")
    _id(staged.approved_source_permit_id, "permit id")
    if type(sequence) is not int or sequence < 1:
        raise EvidenceError("capture sequence must be positive integer")
    role = "listing" if staged.document_id == "issuer-listing" else "pdf"
    expected_name = "issuer-listing.html" if role == "listing" else staged.document_id + ".pdf"
    expected_media = "text/html" if role == "listing" else "application/pdf"
    if staged.file_name != expected_name or staged.media_type != expected_media:
        raise EvidenceError("staged filename or media role mismatch")
    allowed_hosts = os.environ.get("KO_SOURCE_APPROVED_HOSTS", "")
    if not allowed_hosts:
        raise EvidenceError("separately approved capture host registry unavailable")
    from urllib.parse import urlsplit
    host = urlsplit(staged.source_url).hostname
    if not host or validate_source_url(staged.source_url, tuple(allowed_hosts.split(","))) != staged.source_url:
        raise EvidenceError("staged source URL outside exact host authorization")
    _public_ip(staged.pinned_ip)
    root = Path(repo_root).resolve()
    location = root
    for part in ("state", "competitive_engine", "capture_staging", staged.package_id, expected_name):
        location = location / part
        if location.is_symlink():
            raise EvidenceError("staged source path is a symlink")
        if not location.resolve().is_relative_to(root):
            raise EvidenceError("staged source escapes approved private tree")
    if not location.is_file():
        raise EvidenceError("staged source file missing")
    size = location.stat().st_size
    minimum = 30 if role == "listing" else 100
    cap = 512_000 if role == "listing" else MAX_PDF_BYTES
    if not minimum <= size <= cap:
        raise EvidenceError("staged source bytes outside reviewed size policy")
    actual = location.read_bytes()
    if len(actual) != size or hashlib.sha256(actual).hexdigest() != staged.sha256:
        raise EvidenceError("staged source changed or digest mismatched")
    if len(actual) != staged.size_bytes:
        raise EvidenceError("staged source size disagrees with metadata")
    if role == "pdf" and not actual.startswith(b"%PDF-"):
        raise EvidenceError("staged PDF header missing")
    if role == "listing" and not staged.source_url.startswith("https://"):
        raise EvidenceError("issuer listing scheme invalid")
    if (not isinstance(staged.tls_peer_cert_sha256, str)
            or len(staged.tls_peer_cert_sha256) != 64
            or any(c not in "0123456789abcdef" for c in staged.tls_peer_cert_sha256)):
        raise EvidenceError("staged TLS cert fingerprint malformed")

    now = signed_at if signed_at is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise EvidenceError("signing time needs explicit timezone")
    moment = now.astimezone(timezone.utc)
    captured = _date(staged.observed_at, "staged observed_at")
    if (captured > moment or moment - captured > timedelta(hours=2)):
        raise EvidenceError("staged file age incompatible with signing")
    data = {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "key_id": key_id,
        "sequence": sequence,
        "role": role,
        "package_id": staged.package_id,
        "document_id": staged.document_id,
        "source_url": staged.source_url,
        "sha256": staged.sha256,
        "bytes_received": size,
        "media_type": expected_media,
        "capture_method": "local_staged_bytes_unverified",
        "observed_at": staged.observed_at,
        "signed_at": moment.isoformat(),
        "permit_id": staged.approved_source_permit_id,
        "tls_peer_cert_sha256": staged.tls_peer_cert_sha256,
        "pinned_ip": staged.pinned_ip,
        "original_issuer_authenticated": False,
        "publication_authorized": False,
    }
    signature = signer.sign(DOMAIN_RECEIPT + canonical(data))
    return {"receipt": data, "signature": base64.b64encode(signature).decode("ascii")}
