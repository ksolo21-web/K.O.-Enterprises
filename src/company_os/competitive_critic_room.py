"""CE-1N: sealed, read-only original-PDF reviewer workroom and verifier.

Stages *private* reproductions of the current CE-1K signed-staging original
PDF page task list, claim context and exact PDFium PNG bytes. A reviewer
process can read this workroom without access to staging, issuer credentials,
signer keys or creator-private state IF a real OS provisioner assigns separate
UIDs/permissions. This code cannot establish a qualified independent critic,
real human/agent viewing, original issuer identity or a publication right.

No external network, credentials, signing operations, customer send or release.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .capture_trust import StagingTrustLedger
from .competitive_evidence_engine import canonical as dossier_canonical
from .competitive_pdf_source_handoff import (
    _canon as worklist_canonical, inspect_issuer_pdf_handoff,
)
from .competitive_source_page_review import _check_png_structure
from .pdf_page_render import RENDER_PROFILE
from .source_provenance import EvidenceError

ROOM_FORMAT = "1.0"
MAX_ROOM_PAGES = 120
MAX_ROOM_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 1_500_000
MAX_SINGLE_IMAGE_BYTES = 1_000_000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROOM_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_DOC_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")


def _bytes(value: Any, limit: int) -> bytes:
    try:
        data = json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("critic review-room metadata is not valid canonical JSON") from exc
    if not 1 <= len(data) <= limit:
        raise EvidenceError("critic review-room manifest exceeds bounded size")
    return data


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise EvidenceError("invalid critic workroom " + label + " SHA256")
    return value


def _file_name(doc: str, num: int) -> str:
    if not isinstance(doc, str) or not _DOC_ID.fullmatch(doc):
        raise EvidenceError("invalid workroom PDF document ID")
    if type(num) is not int or not 1 <= num <= 60:
        raise EvidenceError("invalid workroom PDF page index")
    return doc + "-page-" + f"{num:03d}" + ".png"


def _page_inventory(worklist: Mapping[str, Any], images: Mapping[str, bytes]) -> list[dict[str, Any]]:
    pages = worklist.get("all_issuer_pdf_pages")
    if (not isinstance(pages, list) or not 1 <= len(pages) <= MAX_ROOM_PAGES
            or not isinstance(images, Mapping)):
        raise EvidenceError("workroom requires complete bounded issuer PDF page images")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    total = 0
    for item in pages:
        if not isinstance(item, dict):
            raise EvidenceError("invalid original PDF page worklist item")
        name = _file_name(item.get("document_id"), item.get("page_number"))
        if name in seen:
            raise EvidenceError("duplicate original issuer PDF page in reviewer room")
        seen.add(name)
        if item.get("renderer_profile") != RENDER_PROFILE:
            raise EvidenceError("unapproved original PDF renderer profile in workroom")
        expected = _sha(item.get("rendered_png_sha256"), "original page")
        png = images.get(name)
        if not isinstance(png, bytes) or not 70 <= len(png) <= MAX_SINGLE_IMAGE_BYTES:
            raise EvidenceError("reviewer room PDF page PNG unavailable or too large")
        _check_png_structure(png)
        actual = hashlib.sha256(png).hexdigest()
        if expected != actual:
            raise EvidenceError("reviewer PDF image differs from controlled original render")
        width = int.from_bytes(png[16:20], "big")
        height = int.from_bytes(png[20:24], "big")
        if (width != item.get("rendered_png_width")
                or height != item.get("rendered_png_height")):
            raise EvidenceError("workroom reviewer PNG dimensions differ from signed staging worklist")
        total += len(png)
        if total > MAX_ROOM_BYTES:
            raise EvidenceError("reviewer room exceeds private evidence capacity")
        out.append({"file": name, "sha256": actual, "size_bytes": len(png)})
    if set(images) != seen:
        raise EvidenceError("reviewer room original PDF pages missing or unexpected")
    return sorted(out, key=lambda x: x["file"])


def _manifest(handoff: Mapping[str, Any], dossier: Mapping[str, Any],
              images: Mapping[str, bytes]) -> dict[str, Any]:
    if (not isinstance(handoff, Mapping) or handoff.get("status")
            != "HOLD_SIGNED_STAGING_PDF_CRITIC_HANDOFF"
            or handoff.get("publication_authorized") is not False
            or handoff.get("independent_critic_approved") is not False
            or handoff.get("original_issuer_authenticated") is not False
            or not isinstance(handoff.get("critic_worklist"), dict)
            or not isinstance(dossier, dict)):
        raise EvidenceError("reviewer workroom requires non-authorized CE-1K handoff")
    work = handoff["critic_worklist"]
    dossier_sha = hashlib.sha256(dossier_canonical(dossier)).hexdigest()
    work_sha = hashlib.sha256(worklist_canonical(work)).hexdigest()
    if (dossier_sha != _sha(handoff.get("dossier_sha256"), "dossier")
            or dossier_sha != work.get("dossier_sha256")
            or work_sha != _sha(handoff.get("handoff_sha256"), "handoff")
            or work.get("issuer_inventory_head_sha256")
                != _sha(handoff.get("issuer_inventory_head_sha256"), "issuer inventory")):
        raise EvidenceError("critic workroom has altered dossier or CE-1K handoff hash")
    sources = {src["id"]: src for src in dossier["sources"]}
    claims = {c["id"]: c for c in dossier["claims"]}
    if len(sources) != len(dossier["sources"]) or len(claims) != len(dossier["claims"]):
        raise EvidenceError("review-room dossier contains duplicate source/claim")
    required = work.get("source_requirements")
    if not isinstance(required, list) or not required:
        raise EvidenceError("no actual original issuer PDF sources in critic workroom")
    seen_sources: set[str] = set()
    for item in required:
        if not isinstance(item, dict) or item.get("source_id") in seen_sources:
            raise EvidenceError("duplicate or invalid original issuer source requirement")
        sid = item["source_id"]
        seen_sources.add(sid)
        source = sources.get(sid)
        if (not source or source.get("kind") != "issuer_original"
                or source.get("sha256") != item.get("original_pdf_sha256")
                or not isinstance(item.get("citing_claim_ids"), list)
                or not item["citing_claim_ids"]
                or set(item["citing_claim_ids"]) - set(claims)):
            raise EvidenceError("critic workroom original source/claim citation is unbound")
        # The original source and exact excerpt were already validated by CE-1K.
        # Here we additionally expose the COMPLETE claim context to reviewer.
        referenced = {c["id"] for c in dossier["claims"]
                      if sid in c["source_ids"] or sid in c["counter_source_ids"]}
        if set(item["citing_claim_ids"]) != referenced:
            raise EvidenceError("critic workroom no longer matches cited claim context")
    if seen_sources != {s["id"] for s in dossier["sources"] if s["kind"] == "issuer_original"}:
        raise EvidenceError("critic room omits a dossier original issuer source")
    packet = {
        "schema_version": ROOM_FORMAT,
        "dossier_sha256": dossier_sha,
        "handoff_sha256": work_sha,
        "issuer_inventory_head_sha256": handoff["issuer_inventory_head_sha256"],
        "dossier": dossier,                # Private context: NEVER upload to public git.
        "original_pdf_worklist": work,     # Every source page, not only cited pages.
        "pages": _page_inventory(work, images),
        "review_status": "PENDING_SEPARATE_HUMAN_OR_AGENT_VISUAL_AND_FACTUAL_REVIEW",
        "source_transport_independently_authenticated": False,
        "reviewer_independence_operationally_verified": False,
        "reviewer_visual_inspection_completed": False,
        "publication_authorized": False,
    }
    _bytes(packet, MAX_MANIFEST_BYTES)
    return packet


def _safe_create(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(path, 0o400)
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def stage_critic_room(
    repo_root: Path | str,
    private_parent: Path | str,
    room_id: str,
    dossier: Mapping[str, Any],
    issuer_id: str,
    package_id: str,
    source_document_ids: Mapping[str, str],
    original_page_pngs: Mapping[str, bytes],
    *,
    staging_policy_envelope: Mapping[str, Any],
    staging_trust_ledger: StagingTrustLedger,
    now: datetime | None = None,
) -> dict[str, Any]:
    """One-shot creation of sealed private reviewer packet; never publish.

    The reviewed OS provisioner MUST transfer room ownership to a separate
    reviewer UID after staging. No implicit chmod/chown privileges are granted.
    """
    if not isinstance(room_id, str) or not _ROOM_ID.fullmatch(room_id):
        raise EvidenceError("invalid private reviewer room ID")
    parent = Path(private_parent)
    if (parent.is_symlink() or not parent.is_dir()
            or parent.stat().st_mode & 0o077):
        raise EvidenceError("reviewer room parent must be an existing private directory")
    if os.name == "posix" and parent.stat().st_uid != os.geteuid():
        raise EvidenceError("review room staging parent not owned by current process")
    handoff = inspect_issuer_pdf_handoff(
        repo_root, dossier, issuer_id, package_id, source_document_ids,
        policy_envelope=staging_policy_envelope,
        trust_ledger=staging_trust_ledger, now=now,
    )
    packet = _manifest(handoff, dossier, original_page_pngs)
    raw = _bytes(packet, MAX_MANIFEST_BYTES)
    directory = parent / room_id
    if directory.exists() or directory.is_symlink():
        raise EvidenceError("review-room identifier already staged or unsafe")
    directory.mkdir(mode=0o700)
    try:
        pages = directory / "pages"
        pages.mkdir(mode=0o700)
        for entry in packet["pages"]:
            _safe_create(pages / entry["file"], original_page_pngs[entry["file"]])
        _safe_create(directory / "manifest.json", raw)
        os.chmod(pages, 0o500)
        os.chmod(directory, 0o500)
    except BaseException:
        # Never leave an incompletely staged room masquerading as verified.
        # The provisioner must remove any failed private staging directory.
        raise
    return {
        "state": "SEALED_PRIVATE_CRITIC_WORKROOM_AWAITING_SEPARATE_REVIEWER",
        "workroom": str(directory),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "page_count": len(packet["pages"]),
        "original_source_count": len(packet["original_pdf_worklist"]["source_requirements"]),
        "separate_reviewer_uid_verified": False,
        "source_issuer_independently_authenticated": False,
        "independent_review_completed": False,
        "publication_authorized": False,
    }


def _check_metadata_file(path: Path, *, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("critic room file is missing or symlinked")
    meta = path.stat()
    if (meta.st_size < 1 or meta.st_size > maximum
            or meta.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)):
        raise EvidenceError("critic room evidence file is missing or writable")
    raw = path.read_bytes()
    if len(raw) != meta.st_size:
        raise EvidenceError("critic evidence file changed during verification")
    return raw


def inspect_sealed_critic_room(
    room: Path | str, *, expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Read only the provisioned room. Never access original capture or keys."""
    expected = _sha(expected_manifest_sha256, "externally supplied manifest")
    directory = Path(room)
    pages = directory / "pages"
    if (directory.is_symlink() or not directory.is_dir()
            or pages.is_symlink() or not pages.is_dir()
            or directory.stat().st_mode & 0o222
            or pages.stat().st_mode & 0o222):
        raise EvidenceError("critic room is not an immutable read-only directory")
    if {p.name for p in directory.iterdir()} != {"manifest.json", "pages"}:
        raise EvidenceError("unexpected critic room content or review result injection")
    raw = _check_metadata_file(directory / "manifest.json", maximum=MAX_MANIFEST_BYTES)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise EvidenceError("critic reviewer workroom manifest differs from external hash")
    try:
        packet = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise EvidenceError("critic workroom manifest unreadable") from exc
    if not isinstance(packet, dict) or _bytes(packet, MAX_MANIFEST_BYTES) != raw:
        raise EvidenceError("critic workroom manifest is not canonical")
    if (packet.get("schema_version") != ROOM_FORMAT
            or packet.get("review_status") != "PENDING_SEPARATE_HUMAN_OR_AGENT_VISUAL_AND_FACTUAL_REVIEW"
            or packet.get("publication_authorized") is not False
            or packet.get("reviewer_independence_operationally_verified") is not False
            or packet.get("source_transport_independently_authenticated") is not False
            or packet.get("reviewer_visual_inspection_completed") is not False):
        raise EvidenceError("critic workroom declares unsupported inspection or authority")
    digest = hashlib.sha256(dossier_canonical(packet["dossier"])).hexdigest()
    work = packet["original_pdf_worklist"]
    if (digest != packet.get("dossier_sha256")
            or work.get("dossier_sha256") != digest
            or hashlib.sha256(worklist_canonical(work)).hexdigest()
                != packet.get("handoff_sha256")
            or work.get("issuer_inventory_head_sha256")
                != packet.get("issuer_inventory_head_sha256")):
        raise EvidenceError("reviewer packet dossier and page worklist chain broken")
    listed = packet.get("pages")
    if (not isinstance(listed, list) or not 1 <= len(listed) <= MAX_ROOM_PAGES):
        raise EvidenceError("critic room page listing absent or unbounded")
    file_ids: set[str] = set()
    for item in listed:
        if not isinstance(item, dict) or set(item) != {"file", "sha256", "size_bytes"}:
            raise EvidenceError("critic page file metadata malformed")
        name = item["file"]
        if (not isinstance(name, str)
                or not re.fullmatch(r"[a-z][a-z0-9_-]{2,79}-page-[0-9]{3}[.]png", name)
                or name in file_ids):
            raise EvidenceError("critic page filename unsafe or duplicated")
        file_ids.add(name)
    # Validate all names BEFORE ever joining one to a private filesystem path.
    expected_pages = _page_inventory(work, {
        name: _check_metadata_file(pages / name, maximum=MAX_SINGLE_IMAGE_BYTES)
        for name in file_ids
    })
    if expected_pages != packet["pages"]:
        raise EvidenceError("critic room evidence image manifest altered")
    if {p.name for p in pages.iterdir()} != {p["file"] for p in packet["pages"]}:
        raise EvidenceError("extra or absent original PDF page in critic workroom")
    return {
        "state": "READ_ONLY_SOURCE_PAGE_ROOM_HASHES_VERIFIED_REVIEW_PENDING",
        "manifest_sha256": expected,
        "page_count": len(packet["pages"]),
        "original_source_count": len(work["source_requirements"]),
        "reviewer_visual_inspection_completed": False,
        "real_issuer_authenticated": False,
        "reviewer_independence_operationally_verified": False,
        "independent_critic_approved": False,
        "publication_authorized": False,
    }


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] != "--verify":
        print("BLOCK: reviewer room requires --verify ROOM EXPECTED_MANIFEST_SHA256")
        return 2
    try:
        result = inspect_sealed_critic_room(
            Path(sys.argv[2]), expected_manifest_sha256=sys.argv[3],
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (EvidenceError, OSError, KeyError, ValueError, TypeError) as exc:
        print("BLOCK: sealed reviewer workroom verification failed: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
