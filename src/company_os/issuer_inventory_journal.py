"""CE-1C3e: offline permit-bound issuer listing / PDF inventory journal.

Links approved-source permits, locally staged byte hashes, and optionally
root-governed staging attestations. Detects missing PDF links, changed issuer
listings, removals, and source bytes across separately captured sessions.

NO real issuer/source authentication, external audit anchor, live collection,
scheduled activity, independent critic or publication authorization here.
Even a fully matched package remains on an explicit independent-review HOLD.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .approved_pdf_capture import StagedSource, _id
from .approved_source_fetch import inspect_source_permit
from .capture_trust import (
    StagingTrustLedger, _public_ip, canonical, verify_governance_policy,
    verify_staging_receipt,
)
from .pdf_evidence import MAX_PDF_BYTES, inspect_pdf_bytes
from .signed_capture_receipts import _listed_pdf_links
from .source_provenance import EvidenceError

MAX_EVENTS = 4000
MAX_LISTING_BYTES = 512_000
SOURCE_CAPTURE_WINDOW = timedelta(minutes=5)
LISTING_LIFETIME = timedelta(hours=24)
PDF_LIFETIME = timedelta(days=7)
MAX_SESSION_WINDOW = timedelta(hours=24)
CLOCK_SKEW = timedelta(minutes=2)
_DIGEST_FIELDS = ("sha256", "tls_peer_cert_sha256")


def _utc(raw: Any, name: str) -> datetime:
    if not isinstance(raw, str) or len(raw) > 48:
        raise EvidenceError("invalid " + name)
    try:
        when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid " + name) from exc
    if when.tzinfo is None:
        raise EvidenceError("timezone missing for " + name)
    return when.astimezone(timezone.utc)


def _moment(now: datetime | None) -> datetime:
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise EvidenceError("capture inspection time must have timezone")
    return current.astimezone(timezone.utc)


def _sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _source_file(root: Path, staged: StagedSource) -> bytes:
    _id(staged.package_id, "package id")
    _id(staged.document_id, "document id")
    listing = staged.document_id == "issuer-listing"
    filename = "issuer-listing.html" if listing else staged.document_id + ".pdf"
    if staged.file_name != filename:
        raise EvidenceError("source filename does not match package document id")
    path = root
    for name in ("state", "competitive_engine", "capture_staging", staged.package_id, filename):
        path = path / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise EvidenceError("source path outside private staging")
    if not path.is_file():
        raise EvidenceError("required staged original source is missing")
    cap = MAX_LISTING_BYTES if listing else MAX_PDF_BYTES
    length = path.stat().st_size
    if not 30 <= length <= cap:
        raise EvidenceError("staged source size outside reviewed bounds")
    raw = path.read_bytes()
    if len(raw) != length or len(raw) != staged.size_bytes or _sha256(raw) != staged.sha256:
        raise EvidenceError("staged original changed or no longer matches metadata")
    return raw


def _check_staging(
    root: Path, staged: StagedSource, permit: Mapping[str, Any], now: datetime,
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(staged, StagedSource):
        raise EvidenceError("record requires immutable staged-source metadata")
    if (staged.state != "UNSIGNED_CAPTURE_REQUIRES_SEPARATE_ATTESTATION"
            or staged.original_issuer_authenticated is not False
            or staged.capture_receipt_signed is not False
            or staged.independent_critic_approved is not False
            or staged.publication_authorized is not False):
        raise EvidenceError("staged source falsely claims original-source or release authority")
    scope = inspect_source_permit(permit, now=now)
    listing = staged.document_id == "issuer-listing"
    expected_type = "text/html" if listing else "application/pdf"
    expected_schema = "2.0" if listing else "3.0"
    if (scope["schema_version"] != expected_schema
            or scope["target_url"] != staged.source_url
            or scope["permit_id"] != staged.approved_source_permit_id
            or staged.media_type != expected_type
            or (not listing and scope["media_type"] != "application/pdf")):
        raise EvidenceError("signed permit does not cover exact staged source, type and file")
    if staged.size_bytes > scope["max_bytes"]:
        raise EvidenceError("staged file exceeds signed permit allowance")
    observed = _utc(staged.observed_at, "observed_at")
    allowed_start = _utc(scope["approved_at"], "permit approved_at")
    allowed_end = _utc(scope["expires_at"], "permit expires_at")
    if (not -CLOCK_SKEW <= now - observed <= SOURCE_CAPTURE_WINDOW
            or observed + CLOCK_SKEW < allowed_start
            or observed >= allowed_end):
        raise EvidenceError("capture observation stale or not within signed permit window")
    for value in (staged.sha256, staged.tls_peer_cert_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(
            c not in "0123456789abcdef" for c in value
        ):
            raise EvidenceError("staged capture digest malformed")
    _public_ip(staged.pinned_ip)
    if staged.tls_version not in ("TLSv1.2", "TLSv1.3"):
        raise EvidenceError("staged TLS version not approved")
    raw = _source_file(root, staged)
    urls: list[str] = []
    if listing:
        if staged.reviewed_pdf_pages is not None:
            raise EvidenceError("HTML listing cannot claim parsed PDF pages")
        hosts = tuple(x.strip() for x in os.environ.get("KO_SOURCE_APPROVED_HOSTS", "").split(","))
        urls = sorted(_listed_pdf_links(raw, staged.source_url, hosts))
        if not urls:
            raise EvidenceError("issuer listing contains no supported original PDF links")
        if len(urls) > 30:
            raise EvidenceError("issuer listing has too many PDFs for reviewed package cap")
    else:
        if type(staged.reviewed_pdf_pages) is not int or not 1 <= staged.reviewed_pdf_pages <= 60:
            raise EvidenceError("PDF page count was not inspected")
        inspected = inspect_pdf_bytes(raw)
        if inspected["page_count"] != staged.reviewed_pdf_pages:
            raise EvidenceError("parsed PDF page count differs from capture metadata")
    return scope, urls


def _check_attestation(
    staged: StagedSource, attestation: Any,
    policy_envelope: Mapping[str, Any] | None,
    trust_ledger: StagingTrustLedger | None,
    now: datetime,
) -> tuple[str, str | None]:
    if attestation is None:
        if policy_envelope is not None or trust_ledger is not None:
            raise EvidenceError("incomplete staging attestation inputs")
        return "NOT_ATTESTED", None
    if policy_envelope is None or trust_ledger is None:
        raise EvidenceError("signed staging attestation requires active policy and replay ledger")
    policy = verify_governance_policy(policy_envelope, now=now)
    data = verify_staging_receipt(attestation, policy, now=now)
    match = {
        "package_id": staged.package_id,
        "document_id": staged.document_id,
        "source_url": staged.source_url,
        "sha256": staged.sha256,
        "bytes_received": staged.size_bytes,
        "media_type": staged.media_type,
        "permit_id": staged.approved_source_permit_id,
        "tls_peer_cert_sha256": staged.tls_peer_cert_sha256,
        "pinned_ip": staged.pinned_ip,
        "observed_at": staged.observed_at,
    }
    if any(data.get(k) != value for k, value in match.items()):
        raise EvidenceError("signed staging receipt not bound to this source capture")
    current = trust_ledger.receipt_status(data["receipt_id"], policy_envelope, now=now)
    if current["state"] != "STAGING_ONLY_UNVERIFIED_ORIGIN":
        raise EvidenceError("staging receipt missing, revoked or not current")
    return "SIGNED_STAGING_ONLY_NOT_ORIGINAL_ISSUER", data["receipt_id"]


class IssuerInventoryJournal:
    """Private local integrity ledger; absolutely NO business release method."""

    def __init__(self, repo_root: Path | str) -> None:
        self.root = Path(repo_root).resolve()
        if not self.root.is_dir():
            raise EvidenceError("local issuer inventory root missing")
        folder = self.root
        for name in ("state", "competitive_engine", "issuer_inventory"):
            folder = folder / name
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                raise EvidenceError("issuer inventory journal directory unsafe")
            folder.mkdir(mode=0o700, exist_ok=True)
            if not folder.resolve().is_relative_to(self.root):
                raise EvidenceError("issuer inventory journal escapes private root")
            if name == "issuer_inventory" and os.name == "posix":
                if folder.stat().st_uid != os.geteuid():
                    raise EvidenceError("private issuer journal owner mismatch")
                folder.chmod(0o700)
        self.path = folder / "capture_inventory.sqlite3"
        if self.path.is_symlink():
            raise EvidenceError("issuer inventory database symlink rejected")
        self.db = sqlite3.connect(str(self.path), timeout=8, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS records (
                seq INTEGER PRIMARY KEY, event_json TEXT NOT NULL,
                previous_sha TEXT NOT NULL, event_sha TEXT NOT NULL
            )""")
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS deny_capture_update
            BEFORE UPDATE ON records
            BEGIN SELECT RAISE(ABORT, 'append-only'); END""")
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS deny_capture_delete
            BEFORE DELETE ON records
            BEGIN SELECT RAISE(ABORT, 'append-only'); END""")
        if os.name == "posix":
            self.path.chmod(0o600)

    def __enter__(self) -> "IssuerInventoryJournal":
        return self

    def __exit__(self, *unused: Any) -> None:
        self.db.close()

    def _events(self) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT seq, event_json, previous_sha, event_sha FROM records ORDER BY seq"
        ).fetchall()
        if len(rows) > MAX_EVENTS:
            raise EvidenceError("source history exceeds reviewed retention budget")
        previous = "GENESIS"
        results: list[dict[str, Any]] = []
        for index, (seq, content, prior, digest) in enumerate(rows, 1):
            try:
                event = json.loads(content)
            except (ValueError, TypeError) as exc:
                raise EvidenceError("issuer inventory event JSON corrupt") from exc
            if not isinstance(event, dict) or canonical(event).decode("utf-8") != content:
                raise EvidenceError("issuer inventory event no longer canonical")
            expected = _sha256(previous.encode("ascii") + b"\n" + content.encode("utf-8"))
            if seq != index or prior != previous or digest != expected:
                raise EvidenceError("local issuer inventory chain integrity failed")
            if event.get("sequence") != seq or event.get("status") != "LOCAL_ONLY_NOT_ISSUER_AUTHENTICATED":
                raise EvidenceError("issuer inventory event schema or authority mismatch")
            previous = digest
            results.append(event)
        return results

    def audit(self) -> dict[str, Any]:
        rows = self._events()
        return {
            "status": "LOCAL_CHAIN_UNANCHORED_REVIEW_REQUIRED",
            "events": len(rows),
            "head_sha256": self.db.execute(
                "SELECT event_sha FROM records ORDER BY seq DESC LIMIT 1"
            ).fetchone()[0] if rows else "GENESIS",
            "publication_authorized": False,
            "original_issuer_authenticated": False,
        }

    def record(
        self, *, issuer_id: str, staged: StagedSource,
        permit: Mapping[str, Any], now: datetime | None = None,
        attestation: Mapping[str, Any] | None = None,
        policy_envelope: Mapping[str, Any] | None = None,
        trust_ledger: StagingTrustLedger | None = None,
    ) -> dict[str, Any]:
        """Record one already locally staged and legally permitted document.

        Never initiates network requests, signs claims, or asserts issuer truth.
        """
        iid = _id(issuer_id, "issuer id")
        moment = _moment(now)
        scope, links = _check_staging(self.root, staged, permit, moment)
        attestation_state, rid = _check_attestation(
            staged, attestation, policy_envelope, trust_ledger, moment,
        )
        issuer_listing = staged.document_id == "issuer-listing"
        self.db.execute("BEGIN IMMEDIATE")
        try:
            historical = self._events()
            if len(historical) >= MAX_EVENTS:
                raise EvidenceError("issuer capture event budget exhausted")
            if any(
                row["package_id"] == staged.package_id and row["issuer_id"] != iid
                for row in historical
            ):
                raise EvidenceError("capture package ID already belongs to another issuer")
            same_issuer = [r for r in historical if r["issuer_id"] == iid]
            current = [r for r in same_issuer if r["package_id"] == staged.package_id]
            if any(r["document_id"] == staged.document_id for r in current):
                raise EvidenceError("source capture replay: package document already recorded")
            listings = [r for r in same_issuer if r["document_id"] == "issuer-listing"]
            prior_listing = listings[-1] if listings else None
            package_listing = next(
                (r for r in current if r["document_id"] == "issuer-listing"), None,
            )
            if issuer_listing:
                if current:
                    raise EvidenceError("issuer listing must be captured before package documents")
                if prior_listing and staged.source_url != prior_listing["source_url"]:
                    raise EvidenceError("issuer listing URL changed without source reconciliation")
                if prior_listing and (
                    scope["origin_id"] != prior_listing["permit_origin_id"]
                    or scope["publisher"] != prior_listing["permit_publisher"]
                ):
                    raise EvidenceError("issuer listing identity differs from prior signed permit")
                if prior_listing and _utc(staged.observed_at, "capture date") <= _utc(
                    prior_listing["observed_at"], "prior listing date",
                ):
                    raise EvidenceError("issuer listing clock rollback or replay")
            else:
                if package_listing is None:
                    raise EvidenceError("PDF must belong to a previously captured issuer listing")
                if staged.source_url not in package_listing["listed_urls"]:
                    raise EvidenceError("captured PDF was not in the original issuer listing")
                if (scope["origin_id"] != package_listing["permit_origin_id"]
                        or scope["publisher"] != package_listing["permit_publisher"]
                        or urlsplit(staged.source_url).hostname != urlsplit(
                            package_listing["source_url"]
                        ).hostname):
                    raise EvidenceError("PDF issuer identity/host differs from signed listing scope")
                if any(
                    r["source_url"] == staged.source_url for r in current
                    if r["document_id"] != "issuer-listing"
                ):
                    raise EvidenceError("same listed PDF URL mapped to two original documents")
                if (not -CLOCK_SKEW <= (
                    _utc(staged.observed_at, "document time")
                    - _utc(package_listing["observed_at"], "listing time")
                ) <= MAX_SESSION_WINDOW):
                    raise EvidenceError("PDF capture outside issuer listing observation window")
                prior_document = [
                    row for row in same_issuer if row["document_id"] == staged.document_id
                ]
                if prior_document and prior_document[-1]["source_url"] != staged.source_url:
                    raise EvidenceError("document ID source URL changed without reconciliation")
                if prior_document and _utc(
                    staged.observed_at, "document time",
                ) <= _utc(prior_document[-1]["observed_at"], "prior document time"):
                    raise EvidenceError("document observation replay or clock rollback")
            changes = {"added_links": [], "removed_links": []}
            if issuer_listing and prior_listing:
                changes = {
                    "added_links": sorted(set(links) - set(prior_listing["listed_urls"])),
                    "removed_links": sorted(set(prior_listing["listed_urls"]) - set(links)),
                }
            event = {
                "sequence": len(historical) + 1,
                "status": "LOCAL_ONLY_NOT_ISSUER_AUTHENTICATED",
                "issuer_id": iid, "package_id": staged.package_id,
                "document_id": staged.document_id,
                "filename": staged.file_name,
                "source_url": staged.source_url,
                "observed_at": staged.observed_at,
                "sha256": staged.sha256, "bytes": staged.size_bytes,
                "media_type": staged.media_type, "tls_cert_sha256": staged.tls_peer_cert_sha256,
                "tls_version": staged.tls_version, "pinned_ip": staged.pinned_ip,
                "permit_id": scope["permit_id"],
                "signed_permit_sha256": _sha256(canonical(permit)),
                "permit_rights_basis_asserted": scope["rights_basis"],
                "permit_origin_id": scope["origin_id"],
                "permit_publisher": scope["publisher"],
                "listed_urls": links,
                "link_changes": changes,
                "staging_attestation_state": attestation_state,
                "staging_receipt_id": rid,
                "original_issuer_authenticated": False,
                "independent_critic_approved": False,
                "publication_authorized": False,
            }
            encoded = canonical(event)
            previous_hash = self.db.execute(
                "SELECT event_sha FROM records ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prior = previous_hash[0] if previous_hash else "GENESIS"
            digest = _sha256(prior.encode("ascii") + b"\n" + encoded)
            self.db.execute(
                "INSERT INTO records (seq, event_json, previous_sha, event_sha) VALUES (?,?,?,?)",
                (event["sequence"], encoded.decode("utf-8"), prior, digest),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {
            "state": "LOCAL_CAPTURE_RECORDED_REVIEW_REQUIRED",
            "issuer_id": iid, "package_id": staged.package_id,
            "record_id": event["sequence"],
            "listing_changes": changes,
            "staging_attestation": attestation_state,
            "publication_authorized": False,
            "original_issuer_authenticated": False,
        }

    def inspect_session(
        self, issuer_id: str, package_id: str, *,
        now: datetime | None = None,
        require_staging_attestations: bool = False,
        policy_envelope: Mapping[str, Any] | None = None,
        trust_ledger: StagingTrustLedger | None = None,
    ) -> dict[str, Any]:
        """Fail closed on omitted links, removed links and revoked attestations."""
        try:
            issuer = _id(issuer_id, "issuer id")
            package = _id(package_id, "package id")
            moment = _moment(now)
            events = self._events()
            same = [r for r in events if r["issuer_id"] == issuer]
            current = [r for r in same if r["package_id"] == package]
            listings = [r for r in current if r["document_id"] == "issuer-listing"]
            if len(listings) != 1:
                raise EvidenceError("issuer session has no unique captured listing")
            listing = listings[0]
            all_issuer_listings = [
                row for row in same if row["document_id"] == "issuer-listing"
            ]
            if all_issuer_listings[-1]["sequence"] != listing["sequence"]:
                raise EvidenceError("issuer snapshot superseded by a newer listing capture")
            if not -CLOCK_SKEW <= moment - _utc(listing["observed_at"], "listing date") <= LISTING_LIFETIME:
                raise EvidenceError("issuer listing expired or future dated")
            links = set(listing["listed_urls"])
            observed = {r["source_url"] for r in current if r is not listing}
            if not links or links != observed:
                raise EvidenceError("issuer PDF package incomplete: missing or extra original links")
            if listing["link_changes"]["removed_links"]:
                raise EvidenceError("issuer listing removed earlier PDFs; independent reconciliation required")
            if require_staging_attestations and (
                policy_envelope is None or trust_ledger is None
            ):
                raise EvidenceError("strict issuer session requires signed staging governance")
            if policy_envelope is not None or trust_ledger is not None:
                if policy_envelope is None or trust_ledger is None:
                    raise EvidenceError("partial staging trust inputs")
            signed = 0
            changed_doc_ids: list[str] = []
            for event in current:
                if event["original_issuer_authenticated"] or event["publication_authorized"]:
                    raise EvidenceError("issuer inventory contains impossible approval claim")
                name = event["filename"]
                original = self.root
                for part in (
                    "state", "competitive_engine", "capture_staging", package, name,
                ):
                    original = original / part
                    if original.is_symlink() or not original.resolve().is_relative_to(self.root):
                        raise EvidenceError("source file path unsafe during inventory check")
                if not original.is_file():
                    raise EvidenceError("source file missing during inventory check")
                bytes_now = original.read_bytes()
                if len(bytes_now) != event["bytes"] or _sha256(bytes_now) != event["sha256"]:
                    raise EvidenceError("source file changed since issuer inventory recording")
                age_limit = LISTING_LIFETIME if event is listing else PDF_LIFETIME
                if not -CLOCK_SKEW <= moment - _utc(event["observed_at"], "source observation") <= age_limit:
                    raise EvidenceError("issuer original source capture stale")
                rid = event["staging_receipt_id"]
                if rid:
                    if policy_envelope is None or trust_ledger is None:
                        if require_staging_attestations:
                            raise EvidenceError("cannot check current signed staging revocation")
                    else:
                        current_state = trust_ledger.receipt_status(rid, policy_envelope, now=moment)
                        if current_state["state"] != "STAGING_ONLY_UNVERIFIED_ORIGIN":
                            raise EvidenceError("signed staging receipt revoked or no longer active")
                        signed += 1
                elif require_staging_attestations:
                    raise EvidenceError("original PDF/listing lacks a signed staging receipt")
                if event is not listing:
                    prior_doc = [
                        r for r in same if r["document_id"] == event["document_id"]
                        and r["sequence"] < event["sequence"]
                    ]
                    if prior_doc and prior_doc[-1]["sha256"] != event["sha256"]:
                        changed_doc_ids.append(event["document_id"])
            return {
                "status": "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW",
                "publication_authorized": False,
                "original_issuer_authenticated": False,
                "issuer_id": issuer, "package_id": package,
                "pdf_links_matched": len(links),
                "staging_attestations_currently_verified": signed,
                "new_pdf_links_since_prior_listing": listing["link_changes"]["added_links"],
                "changed_document_ids_since_prior_capture": sorted(changed_doc_ids),
                "limits": [
                    "HTML links cannot prove complete dynamic portal or bid/addenda inventory",
                    "Staging signatures cannot authenticate real issuer transport",
                    "No independent reviewer, release controller, or external audit anchor",
                ],
            }
        except (EvidenceError, ValueError, TypeError, OSError, KeyError) as exc:
            return {
                "status": "BLOCK", "publication_authorized": False,
                "original_issuer_authenticated": False,
                "errors": [str(exc)[:240]],
            }
