"""CE-1C2: verify signed *capture metadata* against local issuer PDF package.

A signature proves that the holder of the configured capture key attested the
record. It does NOT prove that the record came from the issuer, that the issuer
listed every addendum, that portal access was lawful, or that an independent
reviewer approved a claim. There is no signing interface or network access here.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import json
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from .source_provenance import EvidenceError, validate_source_url

MAX_CAPTURE_BUNDLE = 128 * 1024
MAX_LISTING_BYTES = 1024 * 1024
MAX_CAPTURE_RECORDS = 20
MAX_CAPTURE_AGE = timedelta(hours=24)
MAX_DOC_AGE = timedelta(days=7)
MAX_SEQUENCE_DRIFT = timedelta(minutes=5)
MAX_DOC_AFTER_LISTING = timedelta(hours=24)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_ENVELOPE_FIELDS = {"payload", "signature"}
_INVENTORY_FIELDS = {
    "schema_version", "record_kind", "capture_id", "package_id", "listing_url",
    "listing_filename", "listing_sha256", "listing_observed_at",
    "listing_reference", "listed_items", "capture_actor", "capture_method",
}
_DOCUMENT_FIELDS = {
    "schema_version", "record_kind", "capture_id", "package_id", "document_id",
    "source_url", "sha256", "bytes_received", "media_type", "observed_at",
    "capture_actor", "capture_method", "permit_id", "tls_certificate_sha256",
    "pinned_ip",
}
_ITEM_FIELDS = {"document_id", "source_url", "kind", "sequence"}
_BUNDLE_FIELDS = {"schema_version", "listing", "documents"}
_DOCUMENT_KINDS = {"solicitation", "notice", "attachment", "addendum"}


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        if k in obj:
            raise EvidenceError("duplicate key in signed capture evidence")
        obj[k] = v
    return obj


def _stamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or len(value) > 48:
        raise EvidenceError("invalid capture " + name)
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid capture " + name) from exc
    if d.tzinfo is None:
        raise EvidenceError("capture timestamp lacks timezone")
    return d.astimezone(timezone.utc)


def _short(value: Any, name: str, size: int = 160) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > size
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise EvidenceError("invalid capture " + name)
    return value


def _capture_id(value: Any) -> str:
    token = _short(value, "record id", 80)
    if not _ID.fullmatch(token):
        raise EvidenceError("invalid capture record id")
    return token


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise EvidenceError("invalid capture " + name)
    return value


def _canonical(payload: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("capture payload cannot be encoded") from exc


def _approved_hosts() -> tuple[str, ...]:
    raw = os.environ.get("KO_SOURCE_APPROVED_HOSTS", "")
    if not raw or len(raw) > 2048:
        raise EvidenceError("approved exact-host registry unavailable")
    hosts = tuple(x.strip() for x in raw.split(","))
    if (not 1 <= len(hosts) <= 32 or any(
        not h or h != h.lower() or "://" in h or "/" in h or h.endswith(".")
        for h in hosts
    )):
        raise EvidenceError("invalid capture host registry")
    return hosts


def _source_url(value: Any, hosts: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        raise EvidenceError("capture source URL missing")
    checked = validate_source_url(value, hosts)
    if checked != value:
        raise EvidenceError("noncanonical capture URL")
    return value


def _trusted_public_key():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise EvidenceError("capture public-key dependency missing") from exc
    raw = os.environ.get("KO_CAPTURE_RECEIPT_PUBLIC_KEY_B64", "")
    try:
        key = base64.b64decode(raw, validate=True)
        if len(key) != 32:
            raise EvidenceError("capture verifier public key invalid")
        return Ed25519PublicKey.from_public_bytes(key)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceError("capture verifier public key invalid") from exc


def _verified(envelope: Any, fields: set[str], key: Any) -> dict[str, Any]:
    from cryptography.exceptions import InvalidSignature

    if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_FIELDS:
        raise EvidenceError("capture signature envelope malformed")
    payload = envelope["payload"]
    if not isinstance(payload, dict) or set(payload) != fields:
        raise EvidenceError("signed capture record fields invalid")
    signature = envelope["signature"]
    if not isinstance(signature, str) or len(signature) != 88:
        raise EvidenceError("capture signature malformed")
    try:
        decoded = base64.b64decode(signature, validate=True)
        if len(decoded) != 64:
            raise EvidenceError("capture signature length invalid")
        key.verify(decoded, _canonical(payload))
    except (ValueError, InvalidSignature, binascii.Error) as exc:
        raise EvidenceError("capture signature invalid or key not trusted") from exc
    if payload["schema_version"] != "1.0":
        raise EvidenceError("unsupported capture schema")
    return payload


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.urls.append(v)


def _listed_pdf_links(raw: bytes, listing_url: str, hosts: tuple[str, ...]) -> set[str]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise EvidenceError("issuer listing is not UTF-8") from exc
    if "\x00" in text or len(text) < 30:
        raise EvidenceError("issuer listing bytes incomplete")
    parser = _Anchors()
    try:
        parser.feed(text)
    except ValueError as exc:
        raise EvidenceError("malformed issuer listing markup") from exc
    pdf_links: set[str] = set()
    for href in parser.urls:
        full = urljoin(listing_url, href)
        # Reject unsupported protocol and untrusted origins for any linked PDF.
        if urlsplit(full).path.lower().endswith(".pdf"):
            pdf_links.add(_source_url(full, hosts))
    return pdf_links


def inspect_signed_capture_bundle(
    folder: Path, manifest: dict[str, Any], *, now: datetime,
) -> dict[str, Any]:
    """Match signed listing and each PDF receipt to the original package bytes.

    It does not independently enumerate a real issuer site. Never return a
    publication/eligibility approval.
    """
    if now.tzinfo is None:
        raise EvidenceError("capture assessment time needs timezone")
    moment = now.astimezone(timezone.utc)
    root = Path(folder).resolve()
    archive = root / "capture_receipts.json"
    if archive.is_symlink() or not archive.is_file():
        raise EvidenceError("signed capture receipts missing")
    if not 20 <= archive.stat().st_size <= MAX_CAPTURE_BUNDLE:
        raise EvidenceError("signed capture receipt bundle oversized or invalid")
    try:
        bundle = json.loads(
            archive.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(EvidenceError("nonfinite JSON")),
        )
    except (ValueError, OSError, UnicodeError) as exc:
        raise EvidenceError("invalid capture receipt bundle") from exc
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_FIELDS:
        raise EvidenceError("capture receipt bundle fields invalid")
    if bundle["schema_version"] != "1.0":
        raise EvidenceError("capture receipt bundle version unsupported")
    signed_docs = bundle["documents"]
    if not isinstance(signed_docs, list) or not 1 <= len(signed_docs) <= MAX_CAPTURE_RECORDS:
        raise EvidenceError("capture document receipts missing or excessive")

    key = _trusted_public_key()
    hosts = _approved_hosts()
    listing = _verified(bundle["listing"], _INVENTORY_FIELDS, key)
    if listing["record_kind"] != "issuer_listing_capture":
        raise EvidenceError("capture listing record kind invalid")
    package_id = manifest["package_id"]
    if listing["package_id"] != package_id:
        raise EvidenceError("capture listing bound to wrong package")
    _capture_id(listing["capture_id"])
    _short(listing["capture_actor"], "listing capture actor")
    _short(listing["listing_reference"], "issuer listing reference", 320)
    if listing["capture_method"] != "approved_tls_fetch":
        raise EvidenceError("capture listing method was not authorized")
    _source_url(listing["listing_url"], hosts)
    if listing["listing_url"] != manifest["issuer_url"]:
        raise EvidenceError("issuer listing receipt URL does not match manifest")
    _digest(listing["listing_sha256"], "listing hash")
    if listing["listing_filename"] != "issuer-listing.html":
        raise EvidenceError("capture listing filename not permitted")
    listing_path = root / "issuer-listing.html"
    if listing_path.is_symlink() or not listing_path.is_file():
        raise EvidenceError("issuer listing snapshot absent or unsafe")
    if not 30 <= listing_path.stat().st_size <= MAX_LISTING_BYTES:
        raise EvidenceError("issuer listing snapshot size invalid")
    source_bytes = listing_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != listing["listing_sha256"]:
        raise EvidenceError("signed issuer listing hash mismatch")
    observed_listing = _stamp(listing["listing_observed_at"], "listing observed_at")
    if not timedelta(minutes=-2) <= moment - observed_listing <= MAX_CAPTURE_AGE:
        raise EvidenceError("signed issuer listing capture stale or future-dated")
    declared_listing = _stamp(manifest["discovery"]["issuer_listing_checked_at"], "manifest listing check")
    if abs(observed_listing - declared_listing) > timedelta(minutes=1):
        raise EvidenceError("issuer listing timestamp not bound to signed capture")
    if listing["listing_reference"] != manifest["discovery"]["issuer_listing_reference"]:
        raise EvidenceError("issuer listing reference not bound to signed capture")

    manifest_docs = manifest["documents"]
    if not isinstance(manifest_docs, list):
        raise EvidenceError("procurement manifest documents malformed")
    by_id = {d["id"]: d for d in manifest_docs}
    if len(by_id) != len(manifest_docs):
        raise EvidenceError("duplicate document in procurement manifest")
    rows = listing["listed_items"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CAPTURE_RECORDS:
        raise EvidenceError("capture listing inventory missing")
    items: dict[str, dict[str, Any]] = {}
    listed_links: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _ITEM_FIELDS:
            raise EvidenceError("captured issuer inventory record fields invalid")
        did = _capture_id(row["document_id"])
        if did in items:
            raise EvidenceError("duplicate captured listing item")
        if row["kind"] not in _DOCUMENT_KINDS:
            raise EvidenceError("captured issuer listing role invalid")
        if row["kind"] == "addendum":
            if type(row["sequence"]) is not int or row["sequence"] < 1:
                raise EvidenceError("captured addendum sequence invalid")
        elif row["sequence"] is not None:
            raise EvidenceError("non-addendum has a sequence")
        source_url = _source_url(row["source_url"], hosts)
        if source_url in listed_links:
            raise EvidenceError("duplicate issuer document URL")
        listed_links.add(source_url)
        items[did] = row
    if set(items) != set(by_id):
        raise EvidenceError("signed issuer listing and package inventory differ")
    actual_links = _listed_pdf_links(source_bytes, listing["listing_url"], hosts)
    if actual_links != listed_links:
        raise EvidenceError("issuer listing PDF links differ from signed document inventory")
    for did, row in items.items():
        doc = by_id[did]
        if any(doc[field] != row[field] for field in ("source_url", "kind", "sequence")):
            raise EvidenceError("signed listing item differs from package document")

    signed_by_id: dict[str, dict[str, Any]] = {}
    capture_ids = {listing["capture_id"]}
    for envelope in signed_docs:
        item = _verified(envelope, _DOCUMENT_FIELDS, key)
        if item["record_kind"] != "pdf_document_capture":
            raise EvidenceError("signed document capture kind invalid")
        did = _capture_id(item["document_id"])
        cap_id = _capture_id(item["capture_id"])
        if did in signed_by_id or cap_id in capture_ids:
            raise EvidenceError("duplicate document capture or capture identifier")
        capture_ids.add(cap_id)
        if did not in by_id or item["package_id"] != package_id:
            raise EvidenceError("signed capture belongs to wrong package or document")
        d = by_id[did]
        if item["source_url"] != d["source_url"] or _source_url(item["source_url"], hosts) != item["source_url"]:
            raise EvidenceError("document capture URL not bound to document")
        if item["media_type"] != "application/pdf" or item["capture_method"] != "approved_tls_fetch":
            raise EvidenceError("document capture transport not authorized")
        _short(item["capture_actor"], "document capture actor")
        _short(item["permit_id"], "document capture permit id")
        _digest(item["sha256"], "document hash")
        _digest(item["tls_certificate_sha256"], "TLS certificate hash")
        if item["sha256"] != d["sha256"]:
            raise EvidenceError("document capture hash differs from manifest PDF")
        filesize = (root / d["filename"]).stat().st_size
        if type(item["bytes_received"]) is not int or item["bytes_received"] != filesize:
            raise EvidenceError("document capture size differs from original PDF")
        ip_text = _short(item["pinned_ip"], "pinned IP", 64)
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError as exc:
            raise EvidenceError("capture pinned IP invalid") from exc
        if (not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_private
                or ip.is_loopback or ip.is_link_local or ip.is_unspecified
                or getattr(ip, "ipv4_mapped", None) is not None):
            raise EvidenceError("capture pinned IP is not public/global")
        observed = _stamp(item["observed_at"], "document observed_at")
        if not timedelta(minutes=-2) <= moment - observed <= MAX_DOC_AGE:
            raise EvidenceError("signed PDF capture stale or future dated")
        if not (-MAX_SEQUENCE_DRIFT <= observed - observed_listing <= MAX_DOC_AFTER_LISTING):
            raise EvidenceError("document capture time inconsistent with issuer listing")
        doc_observed = _stamp(d["observed_at"], "manifest PDF observation")
        if abs(doc_observed - observed) > timedelta(minutes=1):
            raise EvidenceError("manifest PDF timestamp differs from capture record")
        signed_by_id[did] = item
    if set(signed_by_id) != set(by_id):
        raise EvidenceError("missing or extra signed PDF capture receipt")

    return {
        "state": "SIGNED_CAPTURE_METADATA_MATCHED_REVIEW_REQUIRED",
        "publication_authorized": False,
        "document_receipts_matched": len(signed_by_id),
        "listing_sha256": listing["listing_sha256"],
        "capture_key_type": "ed25519_public_only",
        "listing_capture_id": listing["capture_id"],
        "limits": [
            "Signer identity and acquisition rights must be independently authenticated",
            "Issuer listing may omit hidden, dynamically loaded or subsequently published addenda",
            "Signed metadata cannot prove full issuer-package completeness or client qualification",
            "PDF pages and conflicting interpretation require independent critic inspection",
        ],
    }
