"""CE-1J: bind queued competitive sources to local capture-ledger snapshots.

This is a private, offline integrity check. Operator-supplied capture metadata
does NOT authenticate a publisher, a buyer, rights to access, factual claims,
or an independent reviewer. No network, signature, release, or send path.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .competitive_evidence_engine import assess_competitive_dossier
from .source_provenance import EvidenceError, SourceLedger, _normalize_space, _utc

_SHA = re.compile(r"^[a-f0-9]{64}$")
_CAPTURE_KINDS = {
    "issuer_original": "issuer_primary",
    "vendor_original": "company_self_claim",
    "buyer_firsthand": "other",
    "secondary": "independent_secondary",
}
MAX_BINDINGS_BYTES = 12000
MAX_BINDING_AGE = timedelta(days=7)
MAX_CLOCK_SKEW = timedelta(minutes=2)


def _time(now: datetime | None) -> datetime:
    value = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise EvidenceError("source binding check needs timezone-aware timestamp")
    return value.astimezone(timezone.utc)


def canonical_bindings(bindings: Mapping[str, str]) -> str:
    if not isinstance(bindings, dict):
        raise EvidenceError("source bindings must be a dictionary")
    if (any(not isinstance(sid, str) or not isinstance(snapshot, str)
            or not _SHA.fullmatch(snapshot) for sid, snapshot in bindings.items())
            or len(set(bindings.values())) != len(bindings)):
        raise EvidenceError("source binding identifier or duplicate snapshot invalid")
    data = json.dumps(bindings, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if not data or len(data.encode("utf-8")) > MAX_BINDINGS_BYTES:
        raise EvidenceError("source binding manifest exceeds capacity")
    return data


def inspect_source_bindings(
    repo_root: Path | str,
    dossier: Mapping[str, Any],
    bindings: Mapping[str, str],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Check every dossier source against its *latest* exact local snapshot.

    Missing, changed, expired or previously-revised capture records fail closed.
    All matching sources remain on genuine original-source and critic HOLD.
    """
    moment = _time(now)
    assessment = assess_competitive_dossier(dossier, now=moment)
    if assessment["status"] == "BLOCK":
        raise EvidenceError("cannot bind structurally invalid competitive dossier")
    expected = {item["id"]: item for item in dossier["sources"]}
    blob = canonical_bindings(bindings)
    if set(bindings) != set(expected) or not expected:
        raise EvidenceError("every dossier source requires exactly one snapshot binding")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("source binding project root unavailable")
    folder = root
    for component in ("state", "competitive_engine"):
        folder /= component
        if folder.is_symlink() or not folder.is_dir():
            raise EvidenceError("provenance directory missing or unsafe")
    dbpath = folder / "provenance.sqlite3"
    if dbpath.is_symlink() or not dbpath.is_file():
        raise EvidenceError("real recorded source ledger missing or unsafe")

    with SourceLedger(root) as ledger:
        events = ledger._events()  # validates the entire private local hash chain
        audit = ledger.audit()
        snapshots = [item for _, kind, item, _ in events if kind == "snapshot"]
        by_id = {item["snapshot_id"]: item for item in snapshots}
        if len(by_id) != len(snapshots):
            raise EvidenceError("duplicate source snapshot identity in local ledger")
        latest: dict[str, str] = {}
        changed: set[str] = set()
        for item in snapshots:
            latest[item["document_id"]] = item["snapshot_id"]
            if item["observation"] == "CHANGED_RECHECK_REQUIRED":
                changed.add(item["document_id"])
        for sid, source in expected.items():
            saved = by_id.get(bindings[sid])
            if saved is None:
                raise EvidenceError("dossier references missing captured snapshot")
            if (latest[saved["document_id"]] != saved["snapshot_id"]
                    or saved["document_id"] in changed):
                raise EvidenceError("dossier source superseded or pending source-change review")
            observed = _utc(saved["observed_at"])
            if not -MAX_CLOCK_SKEW <= moment - observed <= MAX_BINDING_AGE:
                raise EvidenceError("dossier capture is stale or future-dated")
            if (
                source["capture_type"] != "operator_supplied"
                or saved["acquisition_method"] != "operator_supplied"
                or not saved["complete_document_asserted"]
                or saved["verification"] != "OPERATOR_ATTESTED_NOT_INDEPENDENTLY_AUTHENTICATED"
                or saved["rights_basis"] != "public_access"
                or source["rights_basis"] != "public_access"
                or saved["source_kind"] != _CAPTURE_KINDS.get(source["kind"])
                or source["url"] != saved["url"]
                or source["publisher"] != saved["publisher"]
                or source["origin_id"] != saved["origin_id"]
                or source["sha256"] != saved["content_sha256"]
                or _utc(source["observed_at"]) != observed
                or _normalize_space(source["excerpt"]) != saved["evidence_excerpt"]
            ):
                raise EvidenceError("dossier source differs from captured original metadata")
        binding_digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return {
            "status": "HOLD_LOCAL_CAPTURE_LINKAGE_NOT_ISSUER_AUTHENTICATION",
            "dossier_sha256": assessment["dossier_sha256"],
            "bindings_sha256": binding_digest,
            "ledger_head_sha256": audit["head_hash"],
            "matched_sources": len(expected),
            "original_sources_independently_authenticated": False,
            "independent_critic_approved": False,
            "publication_authorized": False,
            "limits": [
                "Local source snapshots and their excerpts remain operator-attested",
                "Local hash chains are not externally anchored or tamper-proof",
                "No source-side completeness, actual buyer payment, or critic evidence",
            ],
        }
