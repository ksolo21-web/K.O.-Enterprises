"""CE-1C fail-closed procurement package and addenda preflight.

Only examines locally supplied, explicitly inventoried PDFs and operator
assertions. It cannot prove that an issuer published *all* documents or that
a deadline/eligibility interpretation is correct. It never authorizes bidding,
client delivery, contact, payments or any K.O. business launch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .pdf_evidence import MAX_PDF_BYTES, inspect_pdf_bytes
from .source_provenance import EvidenceError, validate_source_url

MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_DOCUMENTS = 20
MAX_EVIDENCE = 100
_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_FILE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}\.pdf$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_KINDS = frozenset({"solicitation", "notice", "attachment", "addendum"})
_TOP_FIELDS = frozenset({
    "schema_version", "package_id", "issuer_url", "issuer_name",
    "discovery", "documents", "required_document_ids", "expected_addenda",
    "evidence", "resolutions", "mandatory_events", "client_eligibility",
})
_DOC_FIELDS = frozenset({
    "id", "filename", "sha256", "kind", "source_url", "observed_at",
    "issuer_reference", "sequence",
})
_EVID_FIELDS = frozenset({"id", "topic", "value", "document_id", "page", "quote"})
_RES_FIELDS = frozenset({"topic", "selected_evidence_id", "reason"})
_EVENT_FIELDS = frozenset({
    "id", "evidence_id", "occurs_at", "attendance", "waiver_evidence_id",
})
_DISCOVERY_FIELDS = frozenset({
    "issuer_listing_checked_at", "issuer_listing_reference",
    "issuer_addenda_inventory_asserted_complete", "known_missing_records",
})


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise EvidenceError("duplicate key in procurement manifest")
        out[k] = v
    return out


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 48:
        raise EvidenceError("invalid source timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid source timestamp") from exc
    if dt.tzinfo is None:
        raise EvidenceError("source timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def _text(v: Any, name: str, maximum: int = 240) -> str:
    if (not isinstance(v, str) or not v.strip() or len(v) > maximum
            or any(ord(c) < 32 and c not in "\t" for c in v)):
        raise EvidenceError("invalid or missing " + name)
    return v.strip()


def _id(v: Any, name: str) -> str:
    item = _text(v, name, 80)
    if not _ID.fullmatch(item):
        raise EvidenceError("invalid " + name)
    return item


def _exact(value: Any, fields: frozenset[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise EvidenceError("missing or unexpected " + name + " fields")
    return value


def _list(value: Any, name: str, maximum: int, *, min_items: int = 0) -> list[Any]:
    if not isinstance(value, list) or not min_items <= len(value) <= maximum:
        raise EvidenceError("invalid " + name + " list")
    return value


def _observed(value: Any, moment: datetime, *, max_age: timedelta, label: str) -> datetime:
    stamp = _timestamp(value)
    if not timedelta(minutes=-5) <= moment - stamp <= max_age:
        raise EvidenceError(label + " missing, stale, or future dated")
    return stamp


def _safe_local_pdf(root: Path, filename: Any) -> bytes:
    name = _text(filename, "pdf filename", 104)
    if not _FILE.fullmatch(name):
        raise EvidenceError("PDF filename must be one safe relative basename")
    candidate = root / name
    if candidate.is_symlink() or not candidate.is_file():
        raise EvidenceError("missing or unsafe original PDF file")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise EvidenceError("PDF is outside procurement package")
    size = candidate.stat().st_size
    if not 100 <= size <= MAX_PDF_BYTES:
        raise EvidenceError("PDF file exceeds size or is empty")
    # File opened once; hash and parser inspect the same bytes.
    raw = candidate.read_bytes()
    if len(raw) != size:
        raise EvidenceError("PDF changed during acquisition")
    return raw


def _load_manifest(folder: Path) -> dict[str, Any]:
    path = folder / "package.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise EvidenceError("procurement manifest missing or oversized")
    try:
        doc = json.loads(
            path.read_text("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(EvidenceError("nonfinite JSON")),
        )
    except (OSError, ValueError, UnicodeError) as exc:
        raise EvidenceError("procurement manifest malformed") from exc
    return _exact(doc, _TOP_FIELDS, "package")


def _evaluate(folder: Path, now: datetime) -> dict[str, Any]:
    manifest = _load_manifest(folder)
    if manifest["schema_version"] != "1.0":
        raise EvidenceError("unknown package schema")
    package_id = _id(manifest["package_id"], "package_id")
    issuer = _text(manifest["issuer_name"], "issuer_name", 160)
    issuer_url = _text(manifest["issuer_url"], "issuer_url", 2048)
    from urllib.parse import urlsplit
    host = urlsplit(issuer_url).hostname
    if not host or validate_source_url(issuer_url, [host]) != issuer_url:
        raise EvidenceError("issuer URL must be canonical HTTPS")
    discovery = _exact(manifest["discovery"], _DISCOVERY_FIELDS, "discovery")
    _observed(
        discovery["issuer_listing_checked_at"], now,
        max_age=timedelta(hours=24), label="issuer listing check",
    )
    _text(discovery["issuer_listing_reference"], "issuer_listing_reference", 320)
    missing = _list(discovery["known_missing_records"], "known_missing_records", 100)
    if any(not isinstance(x, str) for x in missing):
        raise EvidenceError("missing record ids malformed")
    if discovery["issuer_addenda_inventory_asserted_complete"] is not True or missing:
        raise EvidenceError("issuer package inventory incomplete or acknowledged missing")

    docs = _list(manifest["documents"], "documents", MAX_DOCUMENTS, min_items=1)
    required = _list(manifest["required_document_ids"], "required ids", MAX_DOCUMENTS,
                     min_items=1)
    if len(set(map(str, required))) != len(required):
        raise EvidenceError("duplicate required document id")
    if any(not isinstance(x, str) or not _ID.fullmatch(x) for x in required):
        raise EvidenceError("invalid required document ids")
    expected_addenda = manifest["expected_addenda"]
    if type(expected_addenda) is not int or not 0 <= expected_addenda <= MAX_DOCUMENTS:
        raise EvidenceError("expected addenda count invalid")
    all_files: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    addenda_sequences: list[int] = []
    sequence_by_doc: dict[str, int] = {}
    for row in docs:
        d = _exact(row, _DOC_FIELDS, "document")
        doc_id = _id(d["id"], "document id")
        if doc_id in by_id:
            raise EvidenceError("duplicate document id")
        if d["kind"] not in _KINDS:
            raise EvidenceError("unknown document role")
        if d["filename"] in all_files:
            raise EvidenceError("document file reused under multiple ids")
        all_files.add(d["filename"])
        ref = _text(d["issuer_reference"], "issuer reference", 320)
        _observed(d["observed_at"], now, max_age=timedelta(days=7),
                  label="document observation")
        source = _text(d["source_url"], "source_url", 2048)
        # A recorded source URL has provenance, not independent authenticity.
        h = urlsplit(source).hostname
        if not h or validate_source_url(source, [h]) != source:
            raise EvidenceError("document source URL not canonical HTTPS")
        seq = d["sequence"]
        if d["kind"] == "addendum":
            if type(seq) is not int or seq < 1:
                raise EvidenceError("addendum must have positive sequence")
            addenda_sequences.append(seq)
        elif seq is not None:
            raise EvidenceError("non-addendum cannot declare addendum sequence")
        sequence_by_doc[doc_id] = seq if d["kind"] == "addendum" else 0
        raw = _safe_local_pdf(folder, d["filename"])
        total_bytes += len(raw)
        if total_bytes > MAX_PACKAGE_BYTES:
            raise EvidenceError("complete PDF package exceeds reviewed budget")
        claimed_sha = d["sha256"]
        if not isinstance(claimed_sha, str) or not _HEX.fullmatch(claimed_sha):
            raise EvidenceError("source SHA-256 digest missing")
        if hashlib.sha256(raw).hexdigest() != claimed_sha:
            raise EvidenceError("PDF bytes do not match declared source hash")
        scan = inspect_pdf_bytes(raw)
        by_id[doc_id] = {
            "kind": d["kind"], "filename": d["filename"],
            "sha256": claimed_sha, "pages": scan["pages"],
            "page_count": scan["page_count"], "issuer_reference": ref,
            "source_url": source,
        }

    if not any(v["kind"] == "solicitation" for v in by_id.values()):
        raise EvidenceError("complete solicitation PDF missing")
    if set(required) != set(by_id):
        raise EvidenceError("required inventory excludes, lacks, or misnames attachments")
    if len(addenda_sequences) != expected_addenda or sorted(addenda_sequences) != list(
        range(1, expected_addenda + 1)
    ):
        raise EvidenceError("missing, duplicate, or skipped addendum sequence")

    evidence_rows = _list(manifest["evidence"], "evidence", MAX_EVIDENCE, min_items=1)
    evidence: dict[str, dict[str, Any]] = {}
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_rows:
        e = _exact(item, _EVID_FIELDS, "evidence")
        eid = _id(e["id"], "evidence id")
        if eid in evidence:
            raise EvidenceError("duplicate evidence id")
        doc_id = _id(e["document_id"], "evidence document id")
        if doc_id not in by_id:
            raise EvidenceError("evidence cites unknown original document")
        topic = _text(e["topic"], "evidence topic", 120)
        if not re.fullmatch(r"[a-z][a-z0-9._-]+", topic):
            raise EvidenceError("invalid evidence topic")
        value = _text(e["value"], "evidence value", 320)
        quote = " ".join(_text(e["quote"], "quoted PDF text", 240).split())
        page_number = e["page"]
        pages = by_id[doc_id]["pages"]
        if type(page_number) is not int or not 1 <= page_number <= len(pages):
            raise EvidenceError("evidence page is not present")
        if len(quote) < 16 or pages[page_number - 1].count(quote) != 1:
            raise EvidenceError("quote not uniquely present on the declared PDF page")
        entry = {"id": eid, "topic": topic, "value": value, "document_id": doc_id,
                 "page": page_number, "quote": quote,
                 "sha256": by_id[doc_id]["sha256"]}
        evidence[eid] = entry
        by_topic.setdefault(topic, []).append(entry)
    # Each addendum must have at least one inspected quote, including
    # amendments declaring no substantive changes.
    for did, d in by_id.items():
        if d["kind"] == "addendum" and not any(
            item["document_id"] == did for item in evidence.values()
        ):
            raise EvidenceError("addendum has no page-specific inspected evidence")
    resolutions = _list(manifest["resolutions"], "resolutions", MAX_EVIDENCE)
    resolution_by_topic: dict[str, str] = {}
    for row in resolutions:
        record = _exact(row, _RES_FIELDS, "resolution")
        topic = _text(record["topic"], "resolution topic", 120)
        eid = _id(record["selected_evidence_id"], "resolution evidence id")
        _text(record["reason"], "resolution rationale", 700)
        if topic in resolution_by_topic or eid not in evidence or evidence[eid]["topic"] != topic:
            raise EvidenceError("unbound or duplicate conflict resolution")
        resolution_by_topic[topic] = eid
    selected_values: dict[str, str] = {}
    for topic, rows in by_topic.items():
        distinct = {r["value"] for r in rows}
        if len(distinct) > 1 and topic not in resolution_by_topic:
            raise EvidenceError("contradictory document values have no documented resolution")
        chosen = (
            evidence[resolution_by_topic[topic]]
            if topic in resolution_by_topic else rows[0]
        )
        if len(distinct) > 1 and sequence_by_doc[chosen["document_id"]] < max(
            sequence_by_doc[r["document_id"]] for r in rows
        ):
            raise EvidenceError("resolution selects obsolete pre-addendum evidence")
        selected_values[topic] = chosen["value"]
    if any(topic not in by_topic for topic in resolution_by_topic):
        raise EvidenceError("conflict resolution references absent topic")
    if "submission.deadline" not in selected_values:
        raise EvidenceError("submission deadline source evidence missing")
    deadline = _timestamp(selected_values["submission.deadline"])
    # A researcher cannot assign a deadline unrelated to the exact quoted
    # page. Only an exact ISO value in the quotation is machine checkable in
    # this version; other printed formats remain BLOCK until an independently
    # reviewed parser/evidence protocol handles them.
    selected_deadline = (
        evidence[resolution_by_topic["submission.deadline"]]
        if "submission.deadline" in resolution_by_topic
        else by_topic["submission.deadline"][0]
    )
    if selected_deadline["value"] not in selected_deadline["quote"]:
        raise EvidenceError("deadline value is not literally supported by quoted PDF text")
    if deadline <= now:
        raise EvidenceError("submission deadline expired; no current bid advice")
    events = _list(manifest["mandatory_events"], "mandatory events", 20)
    # This heuristic catches a common omission in otherwise tidy manifests.
    # It cannot prove the absence of mandatory events from an issuer packet.
    event_phrase = re.compile(
        r"\b(?:mandatory|required)\s+(?:pre[- ]?bid\s+)?"
        r"(?:site\s+(?:walk|visit)|walkthrough|meeting|conference)\b",
        re.IGNORECASE,
    )
    event_mentioned = any(
        event_phrase.search(page)
        for document in by_id.values() for page in document["pages"]
    )
    if event_mentioned and not events:
        raise EvidenceError("mandatory event wording in PDF was omitted from event inventory")
    event_flags: list[str] = []
    used_event_ids: set[str] = set()
    for e in events:
        v = _exact(e, _EVENT_FIELDS, "mandatory event")
        event_id = _id(v["id"], "mandatory event id")
        if event_id in used_event_ids:
            raise EvidenceError("duplicate mandatory event id")
        used_event_ids.add(event_id)
        eid = _id(v["evidence_id"], "mandatory event evidence id")
        if eid not in evidence or not evidence[eid]["topic"].startswith("mandatory."):
            raise EvidenceError("mandatory event missing a matching PDF citation")
        when = _timestamp(v["occurs_at"])
        if v["occurs_at"] not in evidence[eid]["quote"]:
            raise EvidenceError("mandatory event time is not literally supported by cited PDF text")
        attend = v["attendance"]
        if attend not in ("unknown", "confirmed", "not_attended", "waiver_claimed"):
            raise EvidenceError("unknown mandatory event attendance state")
        waiver = v["waiver_evidence_id"]
        if attend == "waiver_claimed":
            if (not isinstance(waiver, str) or waiver not in evidence
                    or evidence[waiver]["topic"] != "mandatory.waiver"):
                raise EvidenceError("claimed waiver lacks specifically cited waiver evidence")
        elif waiver is not None:
            raise EvidenceError("waiver citation not applicable")
        if when <= now and attend in ("unknown", "not_attended"):
            raise EvidenceError("mandatory event elapsed without verified attendance/exception")
        if attend != "confirmed":
            event_flags.append("MANDATORY_EVENT_STATUS_REQUIRES_ISSUER_CHECK")
    if manifest["client_eligibility"] not in ("unknown", "review_pending"):
        raise EvidenceError("client eligibility cannot be certified by offline preflight")

    return {
        "status": "HOLD_INDEPENDENT_ISSUER_AND_CLIENT_REVIEW",
        "publication_authorized": False,
        "package_id": package_id, "issuer_name": issuer,
        "documents": {did: {"kind": d["kind"], "page_count": d["page_count"],
                            "sha256": d["sha256"]}
                      for did, d in by_id.items()},
        "addenda_count": expected_addenda,
        "evidence_count": len(evidence),
        "resolved_topics_are_operator_assertions": selected_values,
        "mandatory_event_flags": event_flags,
        "limits": [
            "Issuer inventory completeness is an operator assertion",
            "Full PDFs and attachment content still require independent review",
            "Quoted text does not establish factual interpretation or client eligibility",
            "No commercial release, outreach or bid recommendation is authorized",
        ],
    }


def assess_package(folder: Path | str, *, now: datetime | None = None) -> dict[str, Any]:
    """Return BLOCK or HOLD; there is deliberately no APPROVE state."""
    when = now if now is not None else datetime.now(timezone.utc)
    if when.tzinfo is None:
        return {"status": "BLOCK", "publication_authorized": False,
                "errors": ["timezone-aware assessment time required"]}
    try:
        return _evaluate(Path(folder), when.astimezone(timezone.utc))
    except (EvidenceError, OSError, TypeError, KeyError, ValueError) as exc:
        # We can explain a *category* without echoing source content or secrets.
        return {"status": "BLOCK", "publication_authorized": False,
                "errors": [str(exc)[:240]]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CE-1C private procurement PDF preflight")
    parser.add_argument("folder", help="Private package directory containing package.json and PDFs")
    args = parser.parse_args(argv)
    result = assess_package(args.folder)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("HOLD") else 2


if __name__ == "__main__":
    raise SystemExit(main())
