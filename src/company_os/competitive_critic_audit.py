"""CE-3A local critic attestation replay and irrevocable revocation journal.

A hash-linked local ledger is not externally anchored; privileged attackers
could rewrite it. The audit NEVER proves real reviewer independence or
authorizes a real customer release. Original-source truth remains pending.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .competitive_critic_review import (
    POLICY_DOMAIN, REVIEW_DOMAIN, assess_signed_review, canonical, inspect_review_policy,
    _id,
)
from .source_provenance import EvidenceError


class CriticReviewLedger:
    def __init__(self, repo_root: Path | str) -> None:
        root = Path(repo_root).resolve()
        if not root.is_dir():
            raise EvidenceError("critic audit root missing")
        location = root
        for part in ("state", "competitive_engine", "critic_audit"):
            location = location / part
            if location.is_symlink() or (location.exists() and not location.is_dir()):
                raise EvidenceError("critic audit storage path unsafe")
            location.mkdir(mode=0o700, exist_ok=True)
            if not location.resolve().is_relative_to(root):
                raise EvidenceError("critic audit path escaped private root")
            if os.name == "posix" and part == "critic_audit":
                if location.stat().st_uid != os.geteuid():
                    raise EvidenceError("critic audit directory owner mismatch")
                location.chmod(0o700)
        path = location / "reviews.sqlite3"
        if path.is_symlink():
            raise EvidenceError("critic review audit DB symlink forbidden")
        self.path = path
        self.db = sqlite3.connect(str(path), timeout=8, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,reference_id TEXT NOT NULL,
                key_id TEXT NOT NULL,generation INTEGER NOT NULL,
                record_digest TEXT NOT NULL,prior_sha TEXT NOT NULL,event_sha TEXT NOT NULL
            )""")
        for op in ("UPDATE", "DELETE"):
            self.db.execute(
                f"CREATE TRIGGER IF NOT EXISTS deny_critic_{op.lower()} "
                f"BEFORE {op} ON events BEGIN SELECT RAISE(ABORT, 'critic audit append only'); END"
            )
        if os.name == "posix":
            path.chmod(0o600)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def _history(self) -> list[tuple]:
        rows = self.db.execute(
            "SELECT seq,kind,reference_id,key_id,generation,"
            "record_digest,prior_sha,event_sha FROM events ORDER BY seq"
        ).fetchall()
        if len(rows) > 30000:
            raise EvidenceError("critic review audit exceeds reviewed capacity")
        prev = "GENESIS"
        for index, row in enumerate(rows, 1):
            seq, kind, ref, key, revision, digest, prior, signed_hash = row
            if (seq != index or kind not in {
                "policy", "review", "revoked_key", "revoked_review"
            } or prior != prev or type(revision) is not int):
                raise EvidenceError("critic audit event chain invalid")
            body = canonical({
                "sequence": seq, "kind": kind, "reference_id": ref,
                "key_id": key, "generation": revision, "record_digest": digest,
            })
            expected = hashlib.sha256(prev.encode() + b"\n" + body).hexdigest()
            if signed_hash != expected:
                raise EvidenceError("critic review audit modified or corrupted")
            prev = signed_hash
        return rows

    def audit_status(self) -> dict[str, Any]:
        rows = self._history()
        return {
            "state": "LOCAL_CRITIC_AUDIT_UNANCHORED",
            "entries": len(rows),
            "head_sha256": rows[-1][-1] if rows else "GENESIS",
            "external_publication_authorized": False,
        }

    def _append(self, kind: str, identifier: str, key_id: str,
                revision: int, digest: str) -> None:
        rows = self._history()
        index = len(rows) + 1
        prev = rows[-1][-1] if rows else "GENESIS"
        payload = canonical({
            "sequence": index, "kind": kind, "reference_id": identifier,
            "key_id": key_id, "generation": revision, "record_digest": digest,
        })
        digest_record = hashlib.sha256(prev.encode() + b"\n" + payload).hexdigest()
        self.db.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",
            (index, kind, identifier, key_id, revision, digest, prev, digest_record),
        )

    def accept_policy(
        self, envelope: Mapping[str, Any], *, now: datetime | None = None,
    ) -> dict[str, Any]:
        policy = inspect_review_policy(envelope, now=now)
        digest = hashlib.sha256(
            POLICY_DOMAIN + canonical(policy)
        ).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self._history()
            previous = [x for x in rows if x[1] == "policy"]
            if previous and previous[-1][2] != policy["policy_id"]:
                raise EvidenceError("critic governance policy ID changed")
            revoked_keys = {x[2] for x in rows if x[1] == "revoked_key"}
            revoked_reviews = {x[2] for x in rows if x[1] == "revoked_review"}
            if (not revoked_keys <= set(policy["revoked_key_ids"]) or
                    not revoked_reviews <= set(policy["revoked_review_ids"])):
                raise EvidenceError("critic signer/review revocation rollback forbidden")
            if previous:
                last = previous[-1]
                if (policy["revision"] < last[4] or
                        policy["revision"] == last[4] and digest != last[5]):
                    raise EvidenceError("critic policy revision rollback/collision")
                if policy["revision"] == last[4]:
                    self.db.commit()
                    return {"state": "POLICY_ALREADY_ACTIVE", "external_publication_authorized": False}
            self._append("policy", policy["policy_id"], "governance-root",
                         policy["revision"], digest)
            for key in sorted(set(policy["revoked_key_ids"]) - revoked_keys):
                self._append("revoked_key", key, "governance-root",
                             policy["revision"], digest)
            for rid in sorted(set(policy["revoked_review_ids"]) - revoked_reviews):
                self._append("revoked_review", rid, "governance-root",
                             policy["revision"], digest)
            self.db.commit()
            return {"state": "POLICY_RECORDED_LOCAL_ONLY", "external_publication_authorized": False}
        except BaseException:
            self.db.rollback()
            raise

    def _policy_current(self, policy: Mapping[str, Any]) -> list[tuple]:
        rows = self._history()
        previous = [r for r in rows if r[1] == "policy"]
        digest = hashlib.sha256(POLICY_DOMAIN + canonical(policy)).hexdigest()
        if (not previous or previous[-1][4] != policy["revision"] or
                previous[-1][5] != digest):
            raise EvidenceError("critic current policy missing or superseded")
        return rows

    def accept_review(
        self, dossier: Mapping[str, Any], artifact_sha256: str,
        policy_envelope: Mapping[str, Any], review_envelope: Mapping[str, Any],
        *, artifact_pdf_path: Path | str, now: datetime | None = None,
    ) -> dict[str, Any]:
        reviewed = assess_signed_review(
            dossier, artifact_sha256, policy_envelope, review_envelope,
            artifact_pdf_path=artifact_pdf_path, now=now,
        )
        if reviewed["state"] == "BLOCK":
            return reviewed
        policy = inspect_review_policy(policy_envelope, now=now)
        rid = reviewed["review_id"]
        signature_digest = hashlib.sha256(
            REVIEW_DOMAIN + canonical(review_envelope["review"])
        ).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self._policy_current(policy)
            if any(x[1] == "review" and x[2] == rid for x in rows):
                raise EvidenceError("critic review replay identifier")
            self._append("review", rid, review_envelope["review"]["reviewer_key_id"],
                         policy["revision"], signature_digest)
            self.db.commit()
            return {
                "state": "REVIEW_ATTESTATION_RECORDED_LOCAL_ONLY",
                "review_id": rid, "artifact_sha256": artifact_sha256,
                "external_publication_authorized": False,
                "reviewer_independence_operationally_proven": False,
            }
        except BaseException:
            self.db.rollback()
            raise

    def review_status(
        self, review_id: str, policy_envelope: Mapping[str, Any],
        *, now: datetime | None = None,
    ) -> dict[str, Any]:
        rid = _id(review_id, "review ID")
        policy = inspect_review_policy(policy_envelope, now=now)
        rows = self._policy_current(policy)
        events = [r for r in rows if r[1] == "review" and r[2] == rid]
        if not events:
            state = "NOT_RECORDED"
        elif rid in policy["revoked_review_ids"] or events[-1][3] in policy["revoked_key_ids"]:
            state = "REVOKED"
        else:
            state = "SIGNED_ONLY_EXTERNAL_REVIEW_NOT_PROVEN"
        return {
            "state": state, "review_id": rid,
            "external_publication_authorized": False,
            "reviewer_independence_operationally_proven": False,
        }
