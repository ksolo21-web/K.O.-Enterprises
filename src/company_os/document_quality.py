"""Fail-closed, offline quality gate for K.O. Enterprises client document packs.

The gate checks provenance *records*, content integrity, freshness, reviewer
attestations and safety boundaries. It cannot prove that a source is true or
that an attestation represents a real independent person; that requires an
external reviewer and authenticated protected publishing environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CHECKS = (
    "source_accuracy", "claim_completeness", "contradictions", "recency",
    "client_fit", "compliance", "privacy", "professional_writing",
    "visual_pages", "links_and_citations", "numbers_and_tables", "scope_and_limits",
)
SOURCE_TYPES = {"primary", "secondary", "client_provided"}
RISK_TYPES = {"standard", "critical", "deadline"}
BUSINESS_LINES = {"market_intelligence", "contractor_operations"}
REPORT_CLAIM = re.compile(r"\[(C-[A-Za-z0-9_-]+)\]")
REPORT_SOURCE = re.compile(r"\[(S-[A-Za-z0-9_-]+)\]")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
HEDGE = re.compile(r"(?i)^(consider\b|one option\b|a possible\b|it may\b|you (?:may|could)\b|depending on\b|an option\b)")
SECRETS = (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
           re.compile(r"\bsk_live_[A-Za-z0-9]{12,}"),
           re.compile(r"\bAKIA[A-Z0-9]{16}\b"))


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _local_file(folder: Path, name: Any) -> Path | None:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        return None
    rel = Path(name)
    if any(part in ("..", ".") for part in rel.parts) or rel.is_absolute():
        return None
    resolved = (folder / rel).resolve()
    if not resolved.is_relative_to(folder.resolve()) or not resolved.is_file():
        return None
    return resolved


def payload_digest(manifest: dict[str, Any]) -> str:
    """Hash research evidence and deliverable digests without the review block."""
    core = {key: value for key, value in manifest.items() if key != "review"}
    return _hash(json.dumps(core, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8"))


def audit_pack(folder: Path, as_of: date | None = None, *, public_repo: bool = False) -> dict[str, Any]:
    """Evaluate a pack; any violation blocks release (never grants publication)."""
    as_of = as_of or datetime.now(timezone.utc).date()
    errors: list[str] = []
    notices: list[str] = []
    manifest_path = folder / "manifest.json"
    try:
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("manifest must be a JSON object")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "BLOCK", "errors": [f"MANIFEST: {exc}"], "notices": [], "digest": None}

    def fail(code: str, explanation: str) -> None:
        errors.append(f"{code}: {explanation}")

    if obj.get("schema_version") != "1.0":
        fail("SCHEMA", "unsupported schema_version; expected 1.0")
    if obj.get("business_line") not in BUSINESS_LINES:
        fail("BUSINESS", "unknown business line")
    if obj.get("output_type") not in ("test_fixture", "public_demo", "client_delivery"):
        fail("OUTPUT_TYPE", "must declare output type")
    if obj.get("classification") not in ("public_demo", "client_confidential"):
        fail("CLASSIFICATION", "explicit classification required")
    if public_repo and obj.get("classification") != "public_demo":
        fail("PUBLIC_DATA", "client-confidential packs cannot be checked into public CI")
    for key in ("pack_id", "title", "author", "scope", "limitations"):
        if not _text(obj.get(key)):
            fail("METADATA", f"{key} must be nonempty")
    prepared = _date(obj.get("prepared_at"))
    if prepared is None or prepared > as_of:
        fail("DATE", "prepared_at invalid or after verification date")
    if not isinstance(obj.get("sources"), list) or not obj["sources"]:
        fail("SOURCES", "at least one source required")
    if not isinstance(obj.get("claims"), list) or not obj["claims"]:
        fail("CLAIMS", "at least one traced claim required")
    if not isinstance(obj.get("deliverables"), list) or not obj["deliverables"]:
        fail("DOCUMENTS", "at least one checked deliverable required")

    sources: dict[str, dict[str, Any]] = {}
    for src in obj.get("sources", []) if isinstance(obj.get("sources"), list) else []:
        if not isinstance(src, dict):
            fail("SOURCE_RECORD", "source must be an object")
            continue
        sid = src.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"S-[A-Za-z0-9_-]+", sid) or sid in sources:
            fail("SOURCE_ID", f"invalid or duplicate source ID: {sid!r}")
            continue
        sources[sid] = src
        if src.get("type") not in SOURCE_TYPES:
            fail("SOURCE_TYPE", f"{sid}: source type must be explicit")
        for key in ("title", "publisher", "evidence_excerpt", "verification_method", "record_reference"):
            if not _text(src.get(key)):
                fail("SOURCE_METADATA", f"{sid}: missing {key}")
        excerpt = src.get("evidence_excerpt")
        if not _text(excerpt) or _hash(str(excerpt).encode("utf-8")) != src.get("excerpt_sha256"):
            fail("SOURCE_EXCERPT_HASH", f"{sid}: evidence excerpt changed or is not fingerprinted")
        url = src.get("url")
        if src.get("type") != "client_provided":
            try:
                parsed = urlparse(url) if isinstance(url, str) else None
                safe_url = bool(parsed and parsed.scheme == "https" and parsed.hostname)
            except ValueError:
                safe_url = False
            if not safe_url:
                fail("SOURCE_URL", f"{sid}: public source needs valid https URL")
        elif not _text(src.get("file_reference")):
            fail("CLIENT_SOURCE", f"{sid}: private source needs secure file reference")
        checked = _date(src.get("checked_at"))
        if checked is None or checked > as_of:
            fail("SOURCE_DATE", f"{sid}: invalid or future checked_at")
        elif (as_of - checked).days > 30:
            fail("STALE_SOURCE", f"{sid}: source last checked more than 30 days ago")
        if src.get("access") != "complete":
            fail("SOURCE_ACCESS", f"{sid}: complete issuer/source document not verified")
        if src.get("verification") != "verified":
            fail("SOURCE_VERIFY", f"{sid}: verification pending or disputed")

    claims: dict[str, dict[str, Any]] = {}
    for claim in obj.get("claims", []) if isinstance(obj.get("claims"), list) else []:
        if not isinstance(claim, dict):
            fail("CLAIM_RECORD", "claim must be an object")
            continue
        cid = claim.get("id")
        if not isinstance(cid, str) or not re.fullmatch(r"C-[A-Za-z0-9_-]+", cid) or cid in claims:
            fail("CLAIM_ID", f"invalid/duplicate claim ID {cid!r}")
            continue
        claims[cid] = claim
        for key in ("text", "evidence_reasoning", "limitations"):
            if not _text(claim.get(key)):
                fail("CLAIM_METADATA", f"{cid}: missing {key}")
        if claim.get("status") != "verified":
            fail("CLAIM_UNVERIFIED", f"{cid}: cannot issue unresolved claims")
        risk = claim.get("risk")
        if risk not in RISK_TYPES:
            fail("CLAIM_RISK", f"{cid}: invalid risk class")
        listed = claim.get("source_ids")
        if not isinstance(listed, list) or not listed or any(not isinstance(i, str) or i not in sources for i in listed):
            fail("CLAIM_SOURCES", f"{cid}: missing or unknown source IDs")
            listed = []
        elif risk in ("critical", "deadline") and not any(sources[i].get("type") == "primary" for i in listed):
            fail("CRITICAL_PRIMARY", f"{cid}: high-risk claim needs primary source")
        verified_at = _date(claim.get("verified_at"))
        if verified_at is None or verified_at > as_of:
            fail("CLAIM_DATE", f"{cid}: invalid verification date")
        elif (as_of - verified_at).days > (1 if risk == "deadline" else 30):
            fail("CLAIM_STALE", f"{cid}: verification expired for {risk} claim")
        if claim.get("counterevidence_checked") is not True:
            fail("COUNTEREVIDENCE", f"{cid}: opposing evidence was not assessed")
        if claim.get("kind") == "recommendation" and not HEDGE.match(str(claim.get("text", "")).strip()):
            fail("DIRECTIVE", f"{cid}: recommendation must describe an option, not an instruction")
        if claim.get("kind") not in ("fact", "analysis", "recommendation"):
            fail("CLAIM_KIND", f"{cid}: invalid kind")

    opps = obj.get("opportunities", [])
    if not isinstance(opps, list):
        fail("OPPORTUNITIES", "opportunities must be an array")
        opps = []
    for opp in opps:
        if not isinstance(opp, dict):
            fail("OPPORTUNITY", "opportunity must be an object")
            continue
        oid = opp.get("id", "unknown")
        if not _text(opp.get("source_id")) or opp.get("source_id") not in sources:
            fail("OPPORTUNITY_SOURCE", f"{oid}: original solicitation missing")
        elif sources[opp["source_id"]].get("type") != "primary":
            fail("OPPORTUNITY_PRIMARY", f"{oid}: primary issuer source required")
        if not all(opp.get(k) is True for k in ("complete_documents_checked", "addenda_checked")):
            fail("OPPORTUNITY_DOCS", f"{oid}: original documents/addenda not completely checked")
        if opp.get("fit") not in ("hold", "no_go", "qualified"):
            fail("OPPORTUNITY_FIT", f"{oid}: fit must be explicit")
        attendance = opp.get("mandatory_events", [])
        if not isinstance(attendance, list):
            fail("OPPORTUNITY_EVENTS", f"{oid}: mandatory_events must be a list")
            attendance = []
        if any(e.get("status") == "missed" for e in attendance if isinstance(e, dict)) and opp.get("fit") != "no_go":
            fail("MISSED_EVENT", f"{oid}: missed mandatory event must be NO-GO")
        if any(e.get("status") not in ("met", "missed") for e in attendance if isinstance(e, dict)) and opp.get("fit") == "qualified":
            fail("UNKNOWN_EVENT", f"{oid}: unverified mandatory event cannot qualify")
        if opp.get("fit") == "qualified" and (opp.get("client_eligibility") != "confirmed" or not _text(opp.get("eligibility_basis"))):
            fail("CLIENT_FIT", f"{oid}: client eligibility not independently established")
        if opp.get("fit") == "qualified" and (_date(opp.get("deadline")) is None or _date(opp.get("deadline")) < as_of):
            fail("EXPIRED_OPPORTUNITY", f"{oid}: passed or unknown deadline")

    docs = obj.get("deliverables", [])
    documents: list[tuple[str, bytes]] = []
    if isinstance(docs, list):
        names: set[str] = set()
        for doc in docs:
            if not isinstance(doc, dict):
                fail("DOCUMENT", "deliverable record must be an object")
                continue
            name = doc.get("path")
            if isinstance(name, str) and name in names:
                fail("DUPLICATE_DOC", f"{name!r}: duplicate deliverable")
            if isinstance(name, str):
                names.add(name)
            file = _local_file(folder, name)
            if file is None:
                fail("MISSING_DOC", f"{name!r}: missing or unsafe path")
                continue
            raw = file.read_bytes()
            if _hash(raw) != doc.get("sha256"):
                fail("DOCUMENT_HASH", f"{name!r}: file changed after manifest")
            if not raw:
                fail("EMPTY_DOC", f"{name!r}: empty deliverable")
            if file.suffix.lower() == ".pdf" and not (raw.startswith(b"%PDF-") and b"%%EOF" in raw[-2048:]):
                fail("PDF_STRUCTURE", f"{name!r}: corrupt PDF marker/trailer")
            if file.suffix.lower() not in (".md", ".txt", ".pdf"):
                fail("DOCUMENT_FORMAT", f"{name!r}: unsupported format")
            documents.append((str(name), raw))
        # A mapped Markdown evidence annex must be included for deterministic claim checks.
        annex = [(name, raw) for name, raw in documents if name.endswith(".md")]
        if obj.get("output_type") == "client_delivery" and not any(name.lower().endswith(".pdf") for name, _ in documents):
            fail("CLIENT_PDF", "client delivery requires at least one validated PDF")
        if not annex:
            fail("ANNEX", "a readable Markdown evidence annex is required")
        else:
            decoded = "\n".join(raw.decode("utf-8", errors="replace") for _, raw in annex)
            for id_, claim in claims.items():
                rows = [line for line in decoded.splitlines() if f"[{id_}]" in line]
                if not rows:
                    fail("ANNEX_MISSING", f"{id_}: claim absent from evidence annex")
                elif not any(str(claim.get("text", "")).strip() in line and
                             all(f"[{sid}]" in line for sid in claim.get("source_ids", []) if isinstance(sid, str) and sid in sources)
                             for line in rows):
                    fail("ANNEX_LINK", f"{id_}: claim text or cited source missing on annotated line")
            for id_ in set(REPORT_CLAIM.findall(decoded)) - set(claims):
                fail("ANNEX_UNKNOWN", f"{id_}: unregistered claim marker")
            for id_ in set(REPORT_SOURCE.findall(decoded)) - set(sources):
                fail("ANNEX_SOURCE", f"{id_}: unknown source marker")
        for name, raw in documents:
            if name.endswith((".md", ".txt")):
                decoded = raw.decode("utf-8", errors="replace")
                for secret in SECRETS:
                    if secret.search(decoded):
                        fail("POSSIBLE_SECRET", f"{name}: potential credential exposed")

    review = obj.get("review")
    digest = payload_digest(obj)
    if not isinstance(review, dict):
        fail("NO_REVIEW", "independent critic attestation required")
    else:
        if review.get("decision") != "approve":
            fail("REVIEW_DENIED", "reviewer did not approve")
        score = review.get("quality_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not (9.0 < score <= 10.0):
            fail("REVIEW_SCORE", "independent review score must be strictly above 9.0/10")
        if not _text(review.get("reviewer_id")) or review.get("reviewer_id") == obj.get("author"):
            fail("REVIEW_INDEPENDENCE", "distinct reviewer identity required")
        if review.get("reviewed_digest") != digest:
            fail("REVIEW_DIGEST", "critic reviewed a different evidence/document bundle")
        reviewed_at = _date(review.get("reviewed_at"))
        if reviewed_at is None or reviewed_at > as_of or (as_of - reviewed_at).days > 7:
            fail("REVIEW_STALE", "review must be current (at most seven days)")
        if reviewed_at is not None and prepared is not None and reviewed_at < prepared:
            fail("REVIEW_CHRONOLOGY", "review cannot predate report preparation")
        if reviewed_at is not None:
            dates = [_date(s.get("checked_at")) for s in sources.values()] + [_date(c.get("verified_at")) for c in claims.values()]
            if any(d is not None and d > reviewed_at for d in dates):
                fail("REVIEW_CHRONOLOGY", "critic approval predates evidence verification")
        checks = review.get("checks") if isinstance(review.get("checks"), dict) else {}
        for check in CHECKS:
            if checks.get(check) is not True:
                fail("REVIEW_CHECK", f"{check}: reviewer attestation missing")
        for key in ("notes", "review_context", "visual_evidence"):
            if not _text(review.get(key)):
                fail("REVIEW_EVIDENCE", f"{key}: review evidence/limitations required")
    if obj.get("publication_authorization") is not False:
        # This module never grants sending or public publication. A separate
        # authenticated authorization gateway must handle external release.
        fail("PUBLICATION_AUTH", "publication_authorization must remain false in pack")
    notices.append("Static checks cannot establish source truth, reviewer identity, legal safety or visual quality; external review and authenticated authorization remain mandatory.")
    return {"status": "PASS_REVIEWED_NOT_AUTHORIZED" if not errors else "BLOCK",
            "errors": sorted(set(errors)), "notices": notices, "digest": digest,
            "sources": len(sources), "claims": len(claims), "deliverables": len(documents)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline document evidence/critic release preflight")
    parser.add_argument("pack", type=Path, help="directory with manifest.json and deliverables")
    parser.add_argument("--as-of", help="verification date YYYY-MM-DD (UTC default)")
    parser.add_argument("--public-repo", action="store_true", help="block confidential pack handling")
    parser.add_argument("--json", action="store_true")
    opts = parser.parse_args(argv)
    day = _date(opts.as_of) if opts.as_of else None
    if opts.as_of and day is None:
        parser.error("--as-of must be YYYY-MM-DD")
    outcome = audit_pack(opts.pack, day, public_repo=opts.public_repo)
    if opts.json:
        print(json.dumps(outcome, indent=2))
    else:
        print(f"{outcome['status']}: {len(outcome['errors'])} blocker(s)")
        for message in outcome["errors"]:
            print(f" - {message}")
        for message in outcome["notices"]:
            print(f" ! {message}")
    return 0 if outcome["status"] == "PASS_REVIEWED_NOT_AUTHORIZED" else 1


if __name__ == "__main__":
    sys.exit(main())