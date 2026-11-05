"""CE-1B: bounded, permissioned HTTPS source capture with DNS/IP pinning.

NOT a general web crawler or client-facing fact checker. There is NO scheduled
fetching, redirect following, PDF parsing, secret export or publication.
Requires an independently signed exact-target access permit AND the company
policy's live external-action approval; PAUSE_AUTONOMY stops all requests.
The transport authenticates TLS to a DNS name, not the truth of the source.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .policy import ActionRequest, enforce_action
from .pdf_evidence import MAX_PDF_BYTES
from .source_provenance import (
    ACQUISITION_METHODS, MAX_SOURCE_BYTES, MEDIA_TYPES, RIGHTS_BASIS,
    SOURCE_KINDS, EvidenceError, SourceLedger, SnapshotResult,
    extract_snapshot_text, validate_source_url,
)

POLICY_LIMIT = 8192
MAX_TARGET_BYTES = 512_000
MAX_POLICY_AGE = timedelta(days=7)
MAX_CLOCK_SKEW = timedelta(minutes=2)
TIMEOUT_SECONDS = 8
MAX_DNS_ANSWERS = 16
_POLICY_FIELDS = frozenset({
    "schema_version", "target_url", "publisher", "title", "origin_id",
    "source_kind", "rights_basis", "approved_by", "approved_at",
    "expires_at", "permit_id", "max_bytes",
})
_PDF_POLICY_FIELDS = _POLICY_FIELDS | {"media_type"}


@dataclass(frozen=True, slots=True)
class CaptureReceipt:
    document_id: str
    snapshot_id: str
    event_id: int
    observation: str
    source_url: str
    received_at: str
    source_sha256: str
    tls_peer_cert_sha256: str
    pinned_ip: str
    media_type: str
    bytes_read: int
    review_status: str = "HOLD_INDEPENDENT_REVIEW"
    publication_authorized: bool = False


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError("duplicate key in source authorization")
        value[key] = item
    return value


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 48:
        raise EvidenceError("invalid source-policy timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid source-policy timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("source-policy timestamp lacks timezone")
    return parsed.astimezone(timezone.utc)


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _verify_governance_signature(signed: bytes, signature: Any) -> None:
    """Verify Ed25519 with a public key only; NO signer secret in fetch worker."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise EvidenceError("Ed25519 verifier dependency unavailable") from exc

    encoded_public = os.environ.get("KO_SOURCE_PERMIT_PUBLIC_KEY_B64", "")
    if not isinstance(signature, str) or len(signature) != 88:
        raise EvidenceError("source permit signature malformed")
    try:
        raw_public = base64.b64decode(encoded_public, validate=True)
        raw_signature = base64.b64decode(signature, validate=True)
        if len(raw_public) != 32 or len(raw_signature) != 64:
            raise EvidenceError("source permit key/signature size invalid")
        public_key = Ed25519PublicKey.from_public_bytes(raw_public)
        public_key.verify(raw_signature, signed)
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        raise EvidenceError("source permit signature or trusted public key invalid") from exc


def inspect_source_permit(
    envelope: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate an exact-target permit issued by separate trusted governance.

    This verifies an Ed25519 signature using a PROVISIONED PUBLIC KEY ONLY,
    not whether an issuer's website is truthful. The private signing key must
    stay with a separately authenticated governance issuer; the fetch worker
    must never possess it. Key custody/rotation/revocation need live controls.
    """
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(envelope, Mapping) or set(envelope) != {"target", "signature"}:
        raise EvidenceError("source authorization envelope must be exact")
    target = envelope.get("target")
    signature = envelope.get("signature")
    # V2 remains narrowly text/HTML-scoped. The PDF capability requires an
    # independently issued V3 permit naming application/pdf explicitly.
    if not isinstance(target, dict) or (
        (target.get("schema_version") == "2.0" and set(target) != _POLICY_FIELDS)
        or (target.get("schema_version") == "3.0" and set(target) != _PDF_POLICY_FIELDS)
        or target.get("schema_version") not in ("2.0", "3.0")
    ):
        raise EvidenceError("source authorization fields or version invalid")
    signed = _canonical(target)
    if len(signed) > POLICY_LIMIT:
        raise EvidenceError("source authorization exceeds size budget")
    _verify_governance_signature(signed, signature)

    if target["schema_version"] == "3.0":
        if target["media_type"] != "application/pdf":
            raise EvidenceError("V3 source permit requires explicit PDF media type")
    else:
        # Preserve the exact old policy; never reinterpret V2 as PDF access.
        if "media_type" in target:
            raise EvidenceError("V2 permit cannot authorize PDF")
    for field in ("publisher", "title", "origin_id", "approved_by", "permit_id"):
        v = target[field]
        if (not isinstance(v, str) or not v.strip() or len(v) > 160
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in v)):
            raise EvidenceError("source authorization identity incomplete")
    if not all(ch.isascii() and (ch.isalnum() or ch in "-_") for ch in target["permit_id"]):
        raise EvidenceError("source authorization permit identifier invalid")
    if target["source_kind"] not in SOURCE_KINDS:
        raise EvidenceError("unrecognized source classification")
    if target["rights_basis"] not in RIGHTS_BASIS:
        raise EvidenceError("unspecified lawful source access")
    limit = target["max_bytes"]
    maximum = MAX_PDF_BYTES if target["schema_version"] == "3.0" else MAX_TARGET_BYTES
    minimum = 100 if target["schema_version"] == "3.0" else 20
    if type(limit) is not int or not minimum <= limit <= maximum:
        raise EvidenceError("source size allowance outside safe bounds")
    allowed_url = target["target_url"]
    if not isinstance(allowed_url, str):
        raise EvidenceError("source URL missing")
    try:
        host = urlsplit(allowed_url).hostname
    except ValueError as exc:
        raise EvidenceError("source authorization URL has invalid authority") from exc
    # A signed exact URL alone is not a trusted-source registry. An additional
    # host policy must be provisioned by the approved protected operator.
    raw_hosts = os.environ.get("KO_SOURCE_APPROVED_HOSTS", "")
    if not raw_hosts or len(raw_hosts) > 2048:
        raise EvidenceError("independent exact-host source registry unavailable")
    registered_hosts = tuple(x.strip() for x in raw_hosts.split(","))
    if len(registered_hosts) > 32 or any(not x or x != x.lower() for x in registered_hosts):
        raise EvidenceError("invalid trusted-source host registry")
    if not host or validate_source_url(allowed_url, registered_hosts) != allowed_url:
        raise EvidenceError("source authorization URL is not exact-host approved")

    approved_at = _utc(target["approved_at"])
    expires_at = _utc(target["expires_at"])
    if (approved_at > moment + MAX_CLOCK_SKEW or expires_at <= moment
            or expires_at <= approved_at or expires_at - approved_at > MAX_POLICY_AGE):
        raise EvidenceError("source permit expired, future-dated or overlong")
    return dict(target)


def _resolve_pinned_endpoint(host: str) -> tuple[int, tuple, str]:
    """Refuse DNS answers if even one result is not a public address.

    All addresses are inspected before picking a pinned socket endpoint; no
    later hostname DNS lookup is permitted while connecting.
    """
    try:
        results = socket.getaddrinfo(
            host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP,
        )
    except (OSError, ValueError) as exc:
        raise EvidenceError("DNS lookup failed") from exc
    if not 1 <= len(results) <= MAX_DNS_ANSWERS:
        raise EvidenceError("DNS answer count outside reviewed limits")
    checked: list[tuple[int, tuple, str]] = []
    for family, socktype, protocol, _, sockaddr in results:
        if family not in (socket.AF_INET, socket.AF_INET6) or (
            socktype != socket.SOCK_STREAM or protocol not in (0, socket.IPPROTO_TCP)
        ):
            raise EvidenceError("DNS returned an unsupported address")
        if not isinstance(sockaddr, tuple) or not sockaddr:
            raise EvidenceError("DNS address invalid")
        try:
            address = ipaddress.ip_address(sockaddr[0])
        except ValueError as exc:
            raise EvidenceError("DNS result is not a numeric address") from exc
        if (not address.is_global or address.is_multicast or address.is_reserved
                or address.is_unspecified or address.is_link_local
                or address.is_loopback or address.is_private
                or "%" in sockaddr[0]
                or getattr(address, "ipv4_mapped", None) is not None):
            raise EvidenceError("DNS returned a restricted/non-public address")
        if len(sockaddr) not in (2, 4) or sockaddr[1] != 443:
            raise EvidenceError("DNS returned a nonstandard destination")
        checked.append((family, sockaddr, str(address)))
    return checked[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """TLS SNI/certificate validation for original host, socket pinned to IP."""

    def __init__(
        self, host: str, family: int, sockaddr: tuple, timeout: int = TIMEOUT_SECONDS
    ) -> None:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        super().__init__(host=host, port=443, timeout=timeout, context=context)
        self._family = family
        self._sockaddr = sockaddr

    def connect(self) -> None:
        raw = socket.socket(self._family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        try:
            raw.settimeout(self.timeout)
            raw.connect(self._sockaddr)
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def _download_https(
    url: str, limit: int, *, expected_media: str = "text",
) -> tuple[bytes, str, str, str, str]:
    """Read one bounded non-redirected TLS response with an explicit media policy.

    Default remains text-only. PDF mode must be called only after a checked V3
    signed PDF permit and company action approval.
    """
    if expected_media not in ("text", "application/pdf"):
        raise EvidenceError("unsupported requested media type")
    if type(limit) is not int or not 20 <= limit <= (
        MAX_PDF_BYTES if expected_media == "application/pdf" else MAX_TARGET_BYTES
    ):
        raise EvidenceError("download limit violates media type policy")
    host = urlsplit(url).hostname
    if not host:
        raise EvidenceError("URL lacks hostname")
    family, pinned_address, ip_string = _resolve_pinned_endpoint(host)
    target = urlsplit(url)
    path = (target.path or "/") + (("?" + target.query) if target.query else "")
    connection = _PinnedHTTPSConnection(host, family, pinned_address)
    try:
        connection.request(
            "GET", path,
            headers={
                "Host": host,
                "User-Agent": "KO-ResearchSource/0.1 (approved-bounded-read)",
                "Accept": "application/pdf" if expected_media == "application/pdf"
                          else "text/html, text/plain",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            # 3xx redirects are refused. A redirect target requires a new
            # independently signed exact URL authorization.
            raise EvidenceError("source returned non-200 status or redirect")
        length_values = [
            value for key, value in response.getheaders()
            if key.lower() == "content-length"
        ]
        if len(length_values) > 1:
            raise EvidenceError("ambiguous content length")
        if length_values:
            try:
                announced = int(length_values[0])
            except ValueError as exc:
                raise EvidenceError("invalid content length") from exc
            if announced < 0 or announced > limit:
                raise EvidenceError("declared content exceeds allowed bytes")
        encoding_headers = [
            value for key, value in response.getheaders()
            if key.lower() == "content-encoding"
        ]
        if len(encoding_headers) > 1 or (
            encoding_headers and encoding_headers[0].strip().lower() != "identity"
        ):
            raise EvidenceError("ambiguous or compressed/encoded response not allowed")
        transfer_headers = [
            value for key, value in response.getheaders()
            if key.lower() == "transfer-encoding"
        ]
        if (len(transfer_headers) > 1
                or (transfer_headers and transfer_headers[0].strip().lower() != "chunked")
                or (transfer_headers and length_values)):
            raise EvidenceError("ambiguous or unsupported transfer encoding")
        types = [v for k, v in response.getheaders() if k.lower() == "content-type"]
        if len(types) != 1:
            raise EvidenceError("missing or ambiguous source content type")
        mime_components = [item.strip().lower() for item in types[0].split(";")]
        media_type = mime_components[0]
        if expected_media == "application/pdf":
            if media_type != "application/pdf" or len(mime_components) != 1:
                raise EvidenceError("PDF source returned unexpected media type or charset")
        elif media_type not in MEDIA_TYPES:
            raise EvidenceError("unexpected source media type")
        elif len(mime_components) > 2 or (
            len(mime_components) == 2
            and mime_components[1] not in ("charset=utf-8", "charset=utf8", "charset=us-ascii")
        ):
            raise EvidenceError("source charset unsupported")
        if connection.sock is None:
            raise EvidenceError("TLS connection unavailable")
        certificate = connection.sock.getpeercert(binary_form=True)
        if not isinstance(certificate, bytes) or not certificate:
            raise EvidenceError("TLS certificate evidence unavailable")
        tls_version = connection.sock.version()
        if tls_version not in ("TLSv1.2", "TLSv1.3"):
            raise EvidenceError("TLS connection does not meet policy")
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise EvidenceError("source body exceeds hard byte cap")
        if expected_media == "application/pdf":
            if len(raw) < 100 or not raw.startswith(b"%PDF-"):
                raise EvidenceError("PDF source body is not a valid PDF candidate")
            # The isolated PDF parser is invoked by the staging layer.
        else:
            extract_snapshot_text(raw, media_type)
        return raw, media_type, ip_string, hashlib.sha256(certificate).hexdigest(), tls_version
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise EvidenceError("TLS/HTTP source retrieval failed") from exc
    finally:
        connection.close()


def fetch_and_capture(
    *,
    ledger: SourceLedger,
    permit: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    document_id: str,
    evidence_excerpt: str,
    repo_root: Path | str,
) -> CaptureReceipt:
    """One approved read, source capture and held claim evidence.

    No retries, crawling, redirects, credential passthrough, implicit URL
    expansion, recurring/scheduled jobs or public client delivery.
    """
    # Check emergency pause and explicit action approval BEFORE DNS/network.
    enforce_action(
        ActionRequest(
            action="call_approved_api", external=True,
            actor="competitive_source_reader", reversible=True,
        ),
        approval=approval, repo_root=repo_root,
    )
    allowed = inspect_source_permit(permit)
    if allowed["schema_version"] != "2.0":
        raise EvidenceError("text snapshot capture rejects PDF-scoped permit")
    url = allowed["target_url"]
    raw, mime, pinned_ip, cert_sha, tls = _download_https(
        url, allowed["max_bytes"],
    )
    # A permit that expires while the network read is underway must not be
    # used to record newly sourced business evidence.
    inspect_source_permit(permit)
    observed = datetime.now(timezone.utc)
    reference = (
        "approved-https:" + allowed["permit_id"]
        + ";cert-sha256:" + cert_sha
        + ";pinned-ip:" + pinned_ip
        + ";tls:" + tls
    )
    saved: SnapshotResult = ledger.capture(
        document_id=document_id, url=url,
        allowed_hosts=(urlsplit(url).hostname or "",),
        publisher=allowed["publisher"], title=allowed["title"],
        origin_id=allowed["origin_id"], source_kind=allowed["source_kind"],
        acquisition_method="approved_connector_export",
        acquisition_reference=reference,
        rights_basis=allowed["rights_basis"],
        observed_at=observed,
        raw=raw, media_type=mime,
        evidence_excerpt=evidence_excerpt,
        complete_document=False,
    )
    return CaptureReceipt(
        document_id=document_id, snapshot_id=saved.snapshot_id,
        event_id=saved.event_id, observation=saved.observation,
        source_url=url, received_at=observed.isoformat(),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        tls_peer_cert_sha256=cert_sha,
        pinned_ip=pinned_ip, media_type=mime,
        bytes_read=len(raw),
    )
