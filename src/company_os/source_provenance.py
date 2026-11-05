"""CE-1: offline, fail-closed evidence capture and provenance.

Accepts lawfully obtained *local* text/HTML snapshots and tracks source changes,
attributed claims and conflicting values. Performs NO network access, does NOT
authenticate a publisher, and NEVER authorizes commercial publication. Actual
online source fetching and reviewer identity require separate approved adapters.

Source documents are *not* copied to GitHub or stored in this ledger. Only a
bounded excerpt, source location, hashes and provenance metadata are retained
in a local state SQLite database. Protect that state as private operational data.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlsplit

MAX_SOURCE_BYTES = 2_000_000
MAX_EVENTS = 50_000
MAX_EXCERPT_CHARS = 240
MAX_FUTURE_SKEW = timedelta(minutes=5)
SOURCE_KINDS = frozenset(
    {"issuer_primary", "company_self_claim", "independent_secondary", "other"}
)
ACQUISITION_METHODS = frozenset({"operator_supplied", "approved_connector_export"})
RIGHTS_BASIS = frozenset({"public_access", "licensed", "permissioned"})
MEDIA_TYPES = frozenset({"text/plain", "text/html"})
CLAIM_TYPES = frozenset({"fact", "attributed_claim", "inference", "eligibility", "deadline"})
_ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{2,79}$")
_KEY = re.compile(r"^[a-z][a-z0-9._-]{2,119}$")
_HOST = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")
_SECRET_QUERY = re.compile(
    r"(?i)(?:secret|token|password|signature|api.?key|session|access.?key|auth)"
)


class EvidenceError(ValueError):
    """Evidence capture was refused; never silently infer missing proof."""


def _utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and len(value) <= 48:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EvidenceError("invalid timestamp") from exc
    else:
        raise EvidenceError("timestamp must be ISO-8601")
    if dt.tzinfo is None:
        raise EvidenceError("timestamp needs explicit timezone")
    return dt.astimezone(timezone.utc)


def _now_utc(value: datetime | None) -> datetime:
    dt = value if value is not None else datetime.now(timezone.utc)
    return _utc(dt)


def _normalize_space(text: str) -> str:
    return " ".join(text.split())


def _required_text(value: Any, field: str, maximum: int = 320) -> str:
    if not isinstance(value, str):
        raise EvidenceError(field + " must be a string")
    result = value.strip()
    if not result or len(result) > maximum or "\x00" in result:
        raise EvidenceError(field + " missing, oversized or invalid")
    return result


def _identifier(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    value = _required_text(value, field, 120)
    if not pattern.fullmatch(value):
        raise EvidenceError(field + " has invalid identifier")
    return value


def validate_source_url(url: str, allowed_hosts: Sequence[str]) -> str:
    """Permit an exact, explicitly approved HTTPS hostname only.

    This is a *metadata* validation, NOT an SSRF-proof HTTP transport. Real
    network adapters must separately pin resolved public IPs, validate TLS,
    disable redirects by default and reauthorize every redirect target.
    """
    if not isinstance(url, str) or len(url) > 2048 or any(
        ch in url for ch in ("\r", "\n", "\x00", "\\")
    ):
        raise EvidenceError("invalid URL syntax")
    try:
        part = urlsplit(url)
        host = part.hostname
        port = part.port
    except ValueError as exc:
        raise EvidenceError("invalid URL authority") from exc
    if (
        part.scheme != "https" or not host or part.username is not None
        or part.password is not None or part.fragment or port not in (None, 443)
        or not part.path.startswith(("/", "")) or not part.netloc
    ):
        raise EvidenceError("only exact approved HTTPS origins without credentials are allowed")
    if not host.isascii() or not _HOST.fullmatch(host) or host.endswith("."):
        raise EvidenceError("invalid hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise EvidenceError("IP-literal source URLs are forbidden")
    if host in ("localhost",) or host.endswith((".local", ".internal")):
        raise EvidenceError("local destinations are forbidden")
    allowed = set()
    for item in allowed_hosts:
        if not isinstance(item, str) or not item.isascii():
            raise EvidenceError("invalid allowed host policy")
        normalized = item.lower().strip()
        if not _HOST.fullmatch(normalized) or normalized.endswith("."):
            raise EvidenceError("invalid allowed host policy")
        allowed.add(normalized)
    if not allowed or host not in allowed:
        raise EvidenceError("source host is not explicitly allowlisted")
    if _SECRET_QUERY.search("&".join(k for k, _ in parse_qsl(part.query, keep_blank_values=True))):
        raise EvidenceError("URL query may contain a private credential")
    # Preserve case/path/query: changing a path may refer to a different record.
    # Exact-host check is case-insensitive; strip only the default explicit port.
    origin = "https://" + host
    return origin + (part.path or "/") + (("?" + part.query) if part.query else "")


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript", "template"):
            self.ignored += 1
        elif tag in ("p", "div", "li", "td", "th", "br", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "template"):
            self.ignored = max(0, self.ignored - 1)
        elif tag in ("p", "div", "li", "td", "th", "br", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def extract_snapshot_text(raw: bytes, media_type: str) -> str:
    if media_type not in MEDIA_TYPES:
        raise EvidenceError("unsupported media type; PDF extraction is not yet enabled")
    if not isinstance(raw, bytes) or not 20 <= len(raw) <= MAX_SOURCE_BYTES:
        raise EvidenceError("invalid or oversized source snapshot")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise EvidenceError("snapshot is not UTF-8") from exc
    if "\x00" in decoded:
        raise EvidenceError("binary content cannot masquerade as text")
    if media_type == "text/html":
        parser = _HTMLText()
        parser.feed(decoded)
        result = _normalize_space("".join(parser.parts))
    else:
        result = _normalize_space(decoded)
    if len(result) < 20:
        raise EvidenceError("snapshot has insufficient visible text")
    return result


def _json(obj: Mapping[str, Any]) -> str:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _event_hash(previous: str, kind: str, raw: str) -> str:
    return _sha((previous + "\n" + kind + "\n" + raw).encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    event_id: int
    snapshot_id: str
    observation: str
    previous_snapshot_id: str | None
    excerpt_offset: int
    publication_authorized: bool = False


class SourceLedger:
    """Local append-only event ledger (not externally anchored or tamper-proof)."""

    def __init__(self, repo_root: Path | str) -> None:
        self.root = Path(repo_root).resolve()
        self.directory = self.root / "state" / "competitive_engine"
        # Do not follow state-directory symlinks out of the permitted root.
        if not self.directory.resolve().is_relative_to(self.root):
            raise EvidenceError("private state directory escapes repository root")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "provenance.sqlite3"
        if self.path.is_symlink():
            raise EvidenceError("refusing symlink database path")
        if os.name == "posix":
            self.directory.chmod(0o700)
        self.connection = sqlite3.connect(str(self.path), timeout=5)
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('snapshot', 'claim')),
                payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            )"""
        )
        self.connection.execute(
            """CREATE TRIGGER IF NOT EXISTS events_no_update
               BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'immutable event'); END"""
        )
        self.connection.execute(
            """CREATE TRIGGER IF NOT EXISTS events_no_delete
               BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'immutable event'); END"""
        )
        self.connection.commit()
        if os.name == "posix":
            self.path.chmod(0o600)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SourceLedger":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _events(self) -> list[tuple[int, str, dict[str, Any], str]]:
        result: list[tuple[int, str, dict[str, Any], str]] = []
        previous = "GENESIS"
        last_seq = 0
        for seq, kind, raw, preceding, digest in self.connection.execute(
            "SELECT seq, kind, payload, previous_hash, event_hash FROM events ORDER BY seq"
        ):
            if kind not in ("snapshot", "claim") or seq != last_seq + 1:
                raise EvidenceError("ledger sequence or event type invalid")
            if not isinstance(raw, str) or not isinstance(preceding, str):
                raise EvidenceError("malformed ledger record")
            try:
                payload = json.loads(raw)
                canonical = _json(payload)
            except (ValueError, TypeError):
                raise EvidenceError("invalid ledger payload") from None
            if not isinstance(payload, dict) or canonical != raw:
                raise EvidenceError("noncanonical ledger record")
            if preceding != previous or digest != _event_hash(previous, kind, raw):
                raise EvidenceError("ledger hash chain invalid")
            result.append((seq, kind, payload, digest))
            previous = digest
            last_seq = seq
            if last_seq > MAX_EVENTS:
                raise EvidenceError("ledger exceeds reviewed processing capacity")
        return result

    def audit(self) -> dict[str, Any]:
        events = self._events()
        return {
            "integrity": "CHAIN_VALID_UNANCHORED",
            "events": len(events),
            "head_hash": events[-1][3] if events else "GENESIS",
            "publication_authorized": False,
            "warning": "SQLite chain detects ordinary corruption, not a hostile privileged rewrite.",
        }

    def _append(self, kind: str, payload: dict[str, Any]) -> int:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            events = self._events()
            if len(events) >= MAX_EVENTS:
                raise EvidenceError("ledger is full; safe rollover not implemented")
            previous = events[-1][3] if events else "GENESIS"
            raw = _json(payload)
            digest = _event_hash(previous, kind, raw)
            result = self.connection.execute(
                "INSERT INTO events(kind,payload,previous_hash,event_hash) VALUES(?,?,?,?)",
                (kind, raw, previous, digest),
            )
            self.connection.commit()
            return int(result.lastrowid)
        except Exception:
            self.connection.rollback()
            raise

    def capture(
        self, *,
        document_id: str,
        url: str,
        allowed_hosts: Sequence[str],
        publisher: str,
        title: str,
        origin_id: str,
        source_kind: str,
        acquisition_method: str,
        acquisition_reference: str,
        rights_basis: str,
        observed_at: str | datetime,
        raw: bytes,
        media_type: str,
        evidence_excerpt: str,
        complete_document: bool,
        now: datetime | None = None,
    ) -> SnapshotResult:
        """Register one operator-provided snapshot without claiming authenticity."""
        instant = _now_utc(now)
        doc_id = _identifier(document_id, "document_id", _ID)
        origin = _identifier(origin_id, "origin_id", _ID)
        checked_url = validate_source_url(url, allowed_hosts)
        pub = _required_text(publisher, "publisher", 160)
        name = _required_text(title, "title", 320)
        reference = _required_text(acquisition_reference, "acquisition_reference", 320)
        if source_kind not in SOURCE_KINDS:
            raise EvidenceError("unknown source kind")
        if acquisition_method not in ACQUISITION_METHODS or rights_basis not in RIGHTS_BASIS:
            raise EvidenceError("acquisition method or rights provenance missing")
        if type(complete_document) is not bool:
            raise EvidenceError("complete_document must be explicit boolean")
        observed = _utc(observed_at)
        if observed > instant + MAX_FUTURE_SKEW:
            raise EvidenceError("future observation is not accepted")
        visible = extract_snapshot_text(raw, media_type)
        quote = _normalize_space(
            _required_text(evidence_excerpt, "evidence_excerpt", MAX_EXCERPT_CHARS)
        )
        if len(quote) < 16 or visible.count(quote) != 1:
            raise EvidenceError("evidence excerpt missing, ambiguous or too short")
        location = visible.index(quote)
        digest = _sha(raw)
        snapshots = [(n, p) for n, kind, p, _ in self._events() if kind == "snapshot"]
        same_doc = [(n, p) for n, p in snapshots if p["document_id"] == doc_id]
        if same_doc and same_doc[-1][1]["url"] != checked_url:
            raise EvidenceError("document ID cannot be silently assigned to a different URL")
        same_url = [(n, p) for n, p in snapshots if p["url"] == checked_url]
        if same_url and same_url[-1][1]["document_id"] != doc_id:
            raise EvidenceError("URL cannot be silently assigned to a different document ID")
        prior = same_doc[-1][1] if same_doc else None
        if prior:
            old = _utc(prior["observed_at"])
            if observed < old:
                raise EvidenceError("out-of-order capture requires a separate reconciliation")
            if observed == old:
                if prior["content_sha256"] != digest:
                    raise EvidenceError("two different snapshots at identical observation time")
                return SnapshotResult(
                    same_doc[-1][0], prior["snapshot_id"], "IDEMPOTENT",
                    prior.get("previous_snapshot_id"), prior["excerpt_offset"],
                )
        prev_id = prior["snapshot_id"] if prior else None
        status = (
            "NEW" if prior is None else
            "UNCHANGED" if prior["content_sha256"] == digest else
            "CHANGED_RECHECK_REQUIRED"
        )
        # Unique snapshot ID ties captured bytes AND observation. This is a
        # content integrity key, not confirmation the origin was authentic.
        snapshot_id = _sha(
            (doc_id + "\n" + checked_url + "\n" + observed.isoformat() + "\n" + digest)
            .encode("utf-8")
        )
        data = {
            "document_id": doc_id, "snapshot_id": snapshot_id,
            "previous_snapshot_id": prev_id, "url": checked_url,
            "publisher": pub, "title": name, "origin_id": origin,
            "source_kind": source_kind, "acquisition_method": acquisition_method,
            "acquisition_reference": reference, "rights_basis": rights_basis,
            "observed_at": observed.isoformat(), "media_type": media_type,
            "content_sha256": digest,
            "normalized_text_sha256": _sha(visible.encode("utf-8")),
            "evidence_excerpt": quote,
            "excerpt_sha256": _sha(quote.encode("utf-8")),
            "excerpt_offset": location, "complete_document_asserted": complete_document,
            "observation": status,
            "verification": "OPERATOR_ATTESTED_NOT_INDEPENDENTLY_AUTHENTICATED",
        }
        event_id = self._append("snapshot", data)
        return SnapshotResult(event_id, snapshot_id, status, prev_id, location)

    def claim(
        self, *,
        claim_id: str,
        claim_key: str,
        value: str,
        text: str,
        claim_type: str,
        snapshot_id: str,
        evidence_quote: str,
        reasoning: str,
        recorded_at: str | datetime,
        now: datetime | None = None,
    ) -> int:
        """Bind a claim to captured words, NOT to a verified interpretation."""
        instant = _now_utc(now)
        cid = _identifier(claim_id, "claim_id", _ID)
        key = _identifier(claim_key, "claim_key", _KEY)
        value = _required_text(value, "claim value", 140)
        text = _required_text(text, "claim text", 500)
        reasoning = _required_text(reasoning, "evidence reasoning", 800)
        evidence_quote = _normalize_space(
            _required_text(evidence_quote, "evidence_quote", MAX_EXCERPT_CHARS)
        )
        if claim_type not in CLAIM_TYPES:
            raise EvidenceError("unknown claim type")
        recorded = _utc(recorded_at)
        if recorded > instant + MAX_FUTURE_SKEW:
            raise EvidenceError("future claim timestamp is not accepted")
        events = self._events()
        matches = [p for _, k, p, _ in events
                   if k == "snapshot" and p["snapshot_id"] == snapshot_id]
        if len(matches) != 1:
            raise EvidenceError("claim refers to nonexistent snapshot")
        source = matches[0]
        if not evidence_quote or evidence_quote not in source["evidence_excerpt"]:
            raise EvidenceError("claimed quote is not present in recorded excerpt")
        for event_id, kind, p, _ in events:
            if kind == "claim" and p["claim_id"] == cid:
                proposed = (key, value, text, claim_type, snapshot_id, evidence_quote)
                previous = tuple(p[x] for x in (
                    "claim_key", "value", "text", "claim_type", "snapshot_id", "evidence_quote"
                ))
                if previous == proposed:
                    return event_id
                raise EvidenceError("claim_id already used for different evidence")
        data = {
            "claim_id": cid, "claim_key": key, "value": value,
            "text": text, "claim_type": claim_type,
            "snapshot_id": snapshot_id, "evidence_quote": evidence_quote,
            "reasoning": reasoning, "recorded_at": recorded.isoformat(),
            "verification": "PENDING_INDEPENDENT_REVIEW",
        }
        return self._append("claim", data)

    def assess(self, *, now: datetime | None = None, max_age_days: int = 7) -> dict[str, Any]:
        """Expose review holds and conflicts without issuing factual certification."""
        if type(max_age_days) is not int or not 0 < max_age_days <= 365:
            raise EvidenceError("source age policy must be between 1 and 365 days")
        instant = _now_utc(now)
        events = self._events()
        documents: dict[str, dict[str, Any]] = {}
        sources_by_id: dict[str, dict[str, Any]] = {}
        claims: list[dict[str, Any]] = []
        for _, kind, item, _ in events:
            if kind == "snapshot":
                documents[item["document_id"]] = item
                sources_by_id[item["snapshot_id"]] = item
            else:
                claims.append(item)
        summaries: list[dict[str, Any]] = []
        conflicts: dict[str, set[str]] = {}
        claim_by_key: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
        for item in claims:
            src = sources_by_id[item["snapshot_id"]]
            latest = documents[src["document_id"]]
            flags = ["NOT_INDEPENDENTLY_AUTHENTICATED"]
            if latest["snapshot_id"] != src["snapshot_id"]:
                flags.append("SOURCE_SUPERSEDED")
            if instant - _utc(latest["observed_at"]) > timedelta(days=max_age_days):
                flags.append("SOURCE_STALE")
            if not latest["complete_document_asserted"]:
                flags.append("INCOMPLETE_SOURCE_SNAPSHOT")
            if src["source_kind"] == "company_self_claim":
                flags.append("ATTRIBUTED_COMPANY_CLAIM")
            if src["snapshot_id"] == latest["snapshot_id"]:
                claim_by_key.setdefault(item["claim_key"], []).append((item, src))
            summaries.append({
                "claim_id": item["claim_id"], "claim_key": item["claim_key"],
                "source_document": src["document_id"], "value": item["value"],
                "flags": flags, "status": "HOLD_INDEPENDENT_REVIEW",
            })
        for key, records in claim_by_key.items():
            values = {r[0]["value"] for r in records}
            if len(values) > 1:
                conflicts[key] = values
                for summary in summaries:
                    if summary["claim_key"] == key and "SOURCE_SUPERSEDED" not in summary["flags"]:
                        summary["flags"].append("CONTRADICTORY_ACTIVE_VALUES")
            # Distinct source counts from the SAME original publisher are not
            # independent corroboration; preserve origin IDs explicitly.
            origins = {src["origin_id"] for _, src in records}
            if len(records) > 1 and len(origins) == 1:
                for summary in summaries:
                    if summary["claim_key"] == key and "SOURCE_SUPERSEDED" not in summary["flags"]:
                        summary["flags"].append("SHARED_ORIGIN_NOT_INDEPENDENT")
        return {
            "state": "INTERNAL_ONLY_UNVERIFIED",
            "publication_authorized": False,
            "total_snapshots": len(sources_by_id),
            "latest_documents": len(documents),
            "claims": summaries,
            "active_conflicts": {k: sorted(v) for k, v in sorted(conflicts.items())},
            "source_changes_to_review": sorted(
                d for d, p in documents.items() if p["observation"] == "CHANGED_RECHECK_REQUIRED"
            ),
            "ledger": self.audit(),
        }


def main(argv: Sequence[str] | None = None) -> int:
    """Private/local operator tool. There is deliberately no HTTP fetch mode."""
    parser = argparse.ArgumentParser(description="Offline K.O. source provenance; never publishes")
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="Record a lawfully provided LOCAL text/HTML snapshot")
    for flag in (
        "document-id", "url", "publisher", "title", "origin-id", "source-kind",
        "acquisition-method", "acquisition-reference", "rights-basis",
        "observed-at", "media-type", "evidence-excerpt", "source-file",
    ):
        capture.add_argument("--" + flag, required=True)
    capture.add_argument("--allow-host", action="append", required=True)
    capture.add_argument("--complete-document", action="store_true")
    sub.add_parser("status", help="Show review holds, changes and conflicts (no approval)")
    sub.add_parser("audit", help="Validate unanchored append-only event chain")
    args = parser.parse_args(argv)
    try:
        with SourceLedger(Path(args.repo_root)) as ledger:
            if args.command == "capture":
                # Prevent accidentally capturing credentials via symlink.
                path = Path(args.source_file)
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
                    raise EvidenceError("local source file unavailable or too large")
                raw = path.read_bytes()
                outcome = ledger.capture(
                    document_id=args.document_id, url=args.url,
                    allowed_hosts=args.allow_host, publisher=args.publisher,
                    title=args.title, origin_id=args.origin_id,
                    source_kind=args.source_kind,
                    acquisition_method=args.acquisition_method,
                    acquisition_reference=args.acquisition_reference,
                    rights_basis=args.rights_basis, observed_at=args.observed_at,
                    raw=raw, media_type=args.media_type,
                    evidence_excerpt=args.evidence_excerpt,
                    complete_document=args.complete_document,
                )
                result: Any = outcome.__dict__ if hasattr(outcome, "__dict__") else {
                    k: getattr(outcome, k) for k in outcome.__dataclass_fields__
                }
            elif args.command == "status":
                result = ledger.assess()
            else:
                result = ledger.audit()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (EvidenceError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"status": "BLOCK", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
