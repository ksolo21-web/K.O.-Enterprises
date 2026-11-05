"""CE-1C3a: staged, approved read-only issuer listing and PDF capture.

This fetch worker has *no signer*, release authority, scheduler, or outbound
publishing capability. It writes only to an ignored private state directory.
Any output is UNSIGNED and unreviewed until a separately authenticated
capture service attests the actual source acquisition and a critic inspects
the originals. Company PAUSE_AUTONOMY prohibits running it live by default.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .approved_source_fetch import _download_https, inspect_source_permit
from .pdf_evidence import inspect_pdf_bytes
from .policy import ActionRequest, enforce_action
from .signed_capture_receipts import _listed_pdf_links
from .source_provenance import EvidenceError, validate_source_url

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
MAX_LISTING_BYTES = 512_000


@dataclass(frozen=True, slots=True)
class StagedSource:
    package_id: str
    document_id: str
    file_name: str
    source_url: str
    observed_at: str
    sha256: str
    size_bytes: int
    media_type: str
    tls_peer_cert_sha256: str
    pinned_ip: str
    tls_version: str
    approved_source_permit_id: str
    reviewed_pdf_pages: int | None
    state: str = "UNSIGNED_CAPTURE_REQUIRES_SEPARATE_ATTESTATION"
    original_issuer_authenticated: bool = False
    capture_receipt_signed: bool = False
    independent_critic_approved: bool = False
    publication_authorized: bool = False

    def unsigned_metadata(self) -> dict[str, Any]:
        """For private handoff; never valid in a signed capture sidecar."""
        return asdict(self)


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise EvidenceError("invalid " + field)
    return value


def _private_stage_dir(repo_root: Path | str, package_id: str) -> Path:
    """Create only under the ignored private state tree, refusing symlink paths."""
    package = _id(package_id, "capture package id")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("capture repository root unavailable")
    location = root
    for component in ("state", "competitive_engine", "capture_staging", package):
        location = location / component
        if location.is_symlink():
            raise EvidenceError("capture storage component is a symlink")
        if location.exists() and not location.is_dir():
            raise EvidenceError("capture storage component is not a directory")
        location.mkdir(mode=0o700, exist_ok=True)
        if not location.resolve().is_relative_to(root):
            raise EvidenceError("capture storage escaped approved private directory")
        if os.name == "posix":
            location.chmod(0o700)
    return location


def _write_once(directory: Path, name: str, body: bytes) -> None:
    """No overwrites, predictable names or dangling temp files on failure."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    path = directory / name
    fd: int | None = None
    created = False
    try:
        fd = os.open(path, flags, 0o600)
        created = True
        with os.fdopen(fd, "wb") as sink:
            fd = None
            sink.write(body)
            sink.flush()
            os.fsync(sink.fileno())
    except FileExistsError as exc:
        raise EvidenceError("private source file already staged; no overwrite") from exc
    except OSError as exc:
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise EvidenceError("unable to write private source snapshot") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _capture(
    *,
    repo_root: Path | str,
    package_id: str,
    document_id: str,
    permit: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    kind: str,
) -> StagedSource:
    """One explicitly approved GET and one write; never automatic crawling."""
    _id(package_id, "capture package id")
    if kind not in ("pdf", "listing"):
        raise EvidenceError("unknown capture kind")
    if kind == "pdf":
        _id(document_id, "capture document id")
        filename, mime = document_id + ".pdf", "application/pdf"
    else:
        if document_id != "issuer-listing":
            raise EvidenceError("issuer listing must use reserved listing ID")
        filename, mime = "issuer-listing.html", "text/html"

    # The emergency pause and approval check MUST precede DNS/network.
    action = ActionRequest(
        action="call_approved_api", actor="competitive_capture_worker",
        external=True, reversible=True, estimated_cost_cents=0,
    )
    enforce_action(action, approval=approval, repo_root=repo_root)
    authorized = inspect_source_permit(permit)
    if kind == "pdf":
        if authorized["schema_version"] != "3.0" or authorized["media_type"] != mime:
            raise EvidenceError("PDF requires signed V3 application/pdf permit")
    elif authorized["schema_version"] != "2.0":
        raise EvidenceError("issuer listing requires scoped signed V2 text permit")
    url = authorized["target_url"]
    output = _download_https(
        url, authorized["max_bytes"],
        expected_media=mime if kind == "pdf" else "text",
    )
    raw, actual_media, pinned_ip, cert_sha, tls_version = output
    if actual_media != mime:
        raise EvidenceError("capture media type did not match signed scope")
    # The network read may straddle an expiry or newly activated emergency stop.
    enforce_action(action, approval=approval, repo_root=repo_root)
    inspect_source_permit(permit)

    pdf_pages: int | None = None
    if kind == "pdf":
        pdf_pages = inspect_pdf_bytes(raw)["page_count"]
    else:
        hosts = tuple(x.strip() for x in os.environ.get("KO_SOURCE_APPROVED_HOSTS", "").split(","))
        urls = _listed_pdf_links(raw, url, hosts)
        if not urls:
            raise EvidenceError("issuer listing has no supported explicitly linked PDFs")
        if len(raw) > MAX_LISTING_BYTES:
            raise EvidenceError("issuer listing exceeds configured source size")

    # One final pause/permit check just before storing private evidence.
    enforce_action(action, approval=approval, repo_root=repo_root)
    inspect_source_permit(permit)
    directory = _private_stage_dir(repo_root, package_id)
    _write_once(directory, filename, raw)

    return StagedSource(
        package_id=package_id,
        document_id=document_id,
        file_name=filename,
        source_url=url,
        observed_at=datetime.now(timezone.utc).isoformat(),
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        media_type=actual_media,
        tls_peer_cert_sha256=cert_sha,
        pinned_ip=pinned_ip,
        tls_version=tls_version,
        approved_source_permit_id=authorized["permit_id"],
        reviewed_pdf_pages=pdf_pages,
    )


def stage_pdf(
    *,
    repo_root: Path | str,
    package_id: str,
    document_id: str,
    permit: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
) -> StagedSource:
    """Stage a PDF under private storage after strict signed permit and parsing."""
    return _capture(
        repo_root=repo_root, package_id=package_id,
        document_id=document_id, permit=permit, approval=approval, kind="pdf",
    )


def stage_issuer_listing(
    *,
    repo_root: Path | str,
    package_id: str,
    permit: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
) -> StagedSource:
    """Stage the actual bytes of an issuer HTML listing, not its inferred completeness."""
    return _capture(
        repo_root=repo_root, package_id=package_id, document_id="issuer-listing",
        permit=permit, approval=approval, kind="listing",
    )
