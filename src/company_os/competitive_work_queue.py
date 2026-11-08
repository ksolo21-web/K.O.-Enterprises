"""CE-2A: durable offline competitive dossier jobs with leases and audit chain.

This queue never contacts the network, starts a service, signs health,
releases client artifacts, sends communications, publishes reports or spends.
It is deliberately safe internal development under PAUSE_AUTONOMY, but still
NOT a production host/monitor. Jobs always terminate as HELD or BLOCKED.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .competitive_evidence_engine import (
    assess_competitive_dossier, canonical as canonical_dossier,
)
from .source_provenance import EvidenceError
from .competitive_source_binding import canonical_bindings, inspect_source_bindings

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
MAX_ATTEMPTS = 3
MAX_JOBS = 5000
MAX_LEASE_SECONDS = 900


def _id(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise EvidenceError("invalid queue " + what)
    return value


def _when(value: datetime | None) -> datetime:
    instant = value if value is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise EvidenceError("queue requires timezone-aware UTC clock")
    return instant.astimezone(timezone.utc)


def _stamp(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("queue timestamp malformed") from exc
    if d.tzinfo is None:
        raise EvidenceError("queue timestamp timezone absent")
    return d.astimezone(timezone.utc)


def _canon(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise EvidenceError("queue event JSON malformed") from exc


class CompetitiveWorkQueue:
    """One local private SQLite database, not a production distributed queue."""

    def __init__(self, repo_root: Path | str) -> None:
        root = Path(repo_root).resolve()
        self.root = root
        if not root.is_dir():
            raise EvidenceError("queue project root unavailable")
        folder = root
        for part in ("state", "competitive_engine", "work_queue"):
            folder = folder / part
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                raise EvidenceError("queue storage path unsafe")
            folder.mkdir(mode=0o700, exist_ok=True)
            if not folder.resolve().is_relative_to(root):
                raise EvidenceError("queue path escaped private project root")
            if os.name == "posix" and part == "work_queue":
                folder.chmod(0o700)
                if folder.stat().st_uid != os.geteuid():
                    raise EvidenceError("queue directory not owned by local worker")
        self.path = folder / "work.sqlite3"
        if self.path.is_symlink():
            raise EvidenceError("queue database cannot be symlink")
        self.db = sqlite3.connect(str(self.path), timeout=8, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=8000")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_sha TEXT NOT NULL,
                state TEXT NOT NULL, attempts INTEGER NOT NULL, generation INTEGER NOT NULL,
                created_at TEXT NOT NULL, available_at TEXT NOT NULL,
                lease_owner TEXT, lease_until TEXT,
                output_sha TEXT, output TEXT, last_error TEXT
            )""")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS source_bindings (
                job_id TEXT PRIMARY KEY,
                bindings_json TEXT NOT NULL,
                bindings_sha TEXT NOT NULL,
                initial_ledger_head_sha TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )""")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, record TEXT NOT NULL,
                prior_sha TEXT NOT NULL, event_sha TEXT NOT NULL
            )""")
        for verb in ("UPDATE", "DELETE"):
            self.db.execute(
                "CREATE TRIGGER IF NOT EXISTS events_append_only_" + verb.lower()
                + " BEFORE " + verb + " ON events "
                + "BEGIN SELECT RAISE(ABORT,'queue event history append-only'); END"
            )
        if os.name == "posix":
            self.path.chmod(0o600)

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def close(self):
        self.db.close()

    def _audit(self) -> list[dict[str, Any]]:
        records = self.db.execute(
            "SELECT seq,record,prior_sha,event_sha FROM events ORDER BY seq"
        ).fetchall()
        if len(records) > 60_000:
            raise EvidenceError("queue event log exceeds reviewed limit")
        output: list[dict[str, Any]] = []
        prev = "GENESIS"
        for index, (seq, raw, prior, digest) in enumerate(records, 1):
            try:
                data = json.loads(raw)
            except (ValueError, TypeError) as exc:
                raise EvidenceError("queue audit event corrupt") from exc
            if (seq != index or prior != prev or not isinstance(data, dict)
                    or _canon(data).decode() != raw
                    or data.get("sequence") != index
                    or data.get("publication_authorized") is not False
                    or digest != hashlib.sha256(
                        prev.encode() + b"\n" + raw.encode()
                    ).hexdigest()):
                raise EvidenceError("queue append-only integrity mismatch")
            prev = digest
            output.append(data)
        return output

    def _append(self, event: str, job_id: str, when: datetime,
                generation: int, metadata: str = "") -> None:
        current = self._audit()
        seq = len(current) + 1
        prev = self.db.execute(
            "SELECT event_sha FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prior = prev[0] if prev else "GENESIS"
        data = {
            "sequence": seq, "event": event, "job_id": job_id,
            "generation": generation, "at": when.isoformat(),
            # No customer details, dossier contents or credentials in logs.
            "metadata": metadata[:80], "publication_authorized": False,
        }
        raw = _canon(data).decode()
        digest = hashlib.sha256(prior.encode() + b"\n" + raw.encode()).hexdigest()
        self.db.execute(
            "INSERT INTO events VALUES(?,?,?,?)", (seq, raw, prior, digest)
        )

    def audit_status(self) -> dict[str, Any]:
        events = self._audit()
        return {
            "state": "LOCAL_UNANCHORED_AUDIT_ONLY",
            "events": len(events),
            "head_sha256": self.db.execute(
                "SELECT event_sha FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()[0] if events else "GENESIS",
            "publication_authorized": False,
        }

    def submit(
        self, dossier: Mapping[str, Any], *, now: datetime | None = None,
        source_bindings: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        moment = _when(now)
        result = assess_competitive_dossier(dossier, now=moment)
        if result["status"] == "BLOCK":
            return {
                "state": "BLOCK_INVALID_DOSSIER",
                "issues": result["issues"],
                "publication_authorized": False,
            }
        # CE-1J is explicit opt-in for *internal* provenance-bound work.
        # Old synthetic queue fixtures remain unbound and never releaseable.
        binding_data = None
        binding_sha = None
        ledger_head = None
        if source_bindings is not None:
            proof = inspect_source_bindings(self.root, dossier, source_bindings, now=moment)
            binding_data = canonical_bindings(dict(source_bindings))
            binding_sha = proof["bindings_sha256"]
            ledger_head = proof["ledger_head_sha256"]
        ident = _id(dossier["dossier_id"], "job identifier")
        blob = canonical_dossier(dossier).decode("utf-8")
        digest = hashlib.sha256(blob.encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            count = self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            existing = self.db.execute(
                "SELECT payload_sha,state FROM jobs WHERE id=?", (ident,)
            ).fetchone()
            if existing:
                if existing[0] != digest:
                    raise EvidenceError("job ID reused for different dossier content")
                prior_binding = self.db.execute(
                    "SELECT bindings_sha FROM source_bindings WHERE job_id=?", (ident,)
                ).fetchone()
                if ((prior_binding is None) != (binding_sha is None)
                        or (prior_binding is not None and prior_binding[0] != binding_sha)):
                    raise EvidenceError("existing queued job cannot switch provenance bindings")
                self.db.commit()
                return {
                    "state": "IDEMPOTENT_EXISTING_" + existing[1],
                    "job_id": ident, "publication_authorized": False,
                }
            if count >= MAX_JOBS:
                raise EvidenceError("private local queue capacity exceeded")
            self.db.execute(
                "INSERT INTO jobs(id,payload,payload_sha,state,attempts,generation,"
                "created_at,available_at) VALUES(?,?,?,?,?,?,?,?)",
                (ident, blob, digest, "QUEUED", 0, 0,
                 moment.isoformat(), moment.isoformat()),
            )
            if binding_data is not None:
                self.db.execute(
                    "INSERT INTO source_bindings VALUES(?,?,?,?)",
                    (ident, binding_data, binding_sha, ledger_head),
                )
            self._append("submitted_bound" if binding_data is not None else "submitted",
                         ident, moment, 0,
                         binding_sha if binding_sha is not None else digest)
            self.db.commit()
            return {
                "state": "QUEUED_INTERNAL_ONLY",
                "job_id": ident, "publication_authorized": False,
            }
        except BaseException:
            self.db.rollback()
            raise

    def lease(
        self, *, owner: str, now: datetime | None = None,
        seconds: int = 120,
    ) -> dict[str, Any] | None:
        worker = _id(owner, "worker identity")
        instant = _when(now)
        if type(seconds) is not int or not 10 <= seconds <= MAX_LEASE_SECONDS:
            raise EvidenceError("queue worker lease TTL out of bounds")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self.db.execute("""
                SELECT id, state, attempts, generation, available_at, lease_until
                FROM jobs WHERE state IN ('QUEUED','LEASED')
                ORDER BY created_at,id
            """).fetchall()
            selection = None
            for ident, state, attempts, generation, available, lease_end in rows:
                if state == "LEASED" and lease_end is not None and _stamp(lease_end) > instant:
                    continue
                if state == "QUEUED" and _stamp(available) > instant:
                    continue
                if attempts >= MAX_ATTEMPTS:
                    self.db.execute(
                        "UPDATE jobs SET state='DEAD',lease_owner=NULL,lease_until=NULL "
                        "WHERE id=?", (ident,)
                    )
                    self._append("dead_attempts_exhausted", ident, instant, generation)
                    continue
                selection = (ident, attempts, generation)
                break
            if selection is None:
                self.db.commit()
                return None
            ident, attempts, generation = selection
            new_generation = generation + 1
            self.db.execute("""
                UPDATE jobs SET state='LEASED',attempts=?,generation=?,
                    lease_owner=?,lease_until=? WHERE id=?
            """, (attempts+1, new_generation, worker,
                  (instant+timedelta(seconds=seconds)).isoformat(), ident))
            self._append("leased", ident, instant, new_generation, worker)
            row = self.db.execute(
                "SELECT payload,payload_sha FROM jobs WHERE id=?", (ident,)
            ).fetchone()
            if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                raise EvidenceError("queued payload digest invalid")
            dossier = json.loads(row[0])
            self.db.commit()
            return {
                "state": "LEASED_INTERNAL_ONLY", "job_id": ident,
                "owner": worker, "generation": new_generation, "dossier": dossier,
                "publication_authorized": False,
            }
        except BaseException:
            self.db.rollback()
            raise

    def _check_lease(
        self, job_id: str, owner: str, generation: int, instant: datetime,
    ) -> tuple:
        if type(generation) is not int or generation < 1:
            raise EvidenceError("lease generation invalid")
        row = self.db.execute("""
            SELECT state,generation,lease_owner,lease_until,payload,payload_sha,attempts
            FROM jobs WHERE id=?
        """, (job_id,)).fetchone()
        if (not row or row[0] != "LEASED" or row[1] != generation
                or row[2] != owner or row[3] is None
                or _stamp(row[3]) <= instant):
            raise EvidenceError("invalid or expired lease; stale worker cannot commit")
        if hashlib.sha256(row[4].encode()).hexdigest() != row[5]:
            raise EvidenceError("leased source dossier was altered")
        return row

    def complete(
        self, *, job_id: str, owner: str, generation: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        ident, worker, instant = _id(job_id, "job id"), _id(owner, "worker"), _when(now)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(ident, worker, generation, instant)
            dossier = json.loads(row[4])
            report = assess_competitive_dossier(dossier, now=instant)
            receipt = self.db.execute(
                "SELECT bindings_json,bindings_sha FROM source_bindings WHERE job_id=?",
                (ident,),
            ).fetchone()
            if receipt:
                try:
                    bound_json, bound_sha = receipt
                    manifest = json.loads(bound_json)
                    if (canonical_bindings(manifest) != bound_json
                            or hashlib.sha256(bound_json.encode()).hexdigest() != bound_sha):
                        raise EvidenceError("queue source binding record no longer canonical")
                    if not any(
                        item["event"] == "submitted_bound"
                        and item["job_id"] == ident and item["metadata"] == bound_sha
                        for item in self._audit()
                    ):
                        raise EvidenceError("source binding no longer matches queue audit")
                    proof = inspect_source_bindings(
                        self.root, dossier, manifest, now=instant,
                    )
                    if proof["dossier_sha256"] != row[5]:
                        raise EvidenceError("source binding no longer matches queued dossier")
                except (EvidenceError, ValueError, TypeError, KeyError, OSError):
                    # A changed, expired or deleted source must not quietly
                    # complete as a held, valid internal result.
                    report = {
                        "status": "BLOCK", "issues": ["provenance_binding_not_current"],
                        "publication_authorized": False,
                        "original_sources_independently_authenticated": False,
                    }
            if report["status"] not in ("BLOCK", "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW"):
                raise EvidenceError("competitive evaluator produced unauthorized state")
            outcome = "BLOCKED" if report["status"] == "BLOCK" else "HELD"
            output = _canon(report).decode()
            digest = hashlib.sha256(output.encode()).hexdigest()
            self.db.execute(
                "UPDATE jobs SET state=?,output=?,output_sha=?,lease_owner=NULL,"
                "lease_until=NULL WHERE id=?",
                (outcome, output, digest, ident),
            )
            self._append("completed_" + outcome.lower(), ident, instant,
                         generation, digest)
            self.db.commit()
            return {
                "state": outcome, "job_id": ident, "result_sha256": digest,
                "publication_authorized": False,
            }
        except BaseException:
            self.db.rollback()
            raise

    def fail(
        self, *, job_id: str, owner: str, generation: int,
        reason_code: str, now: datetime | None = None,
        retry_seconds: int = 20,
    ) -> dict[str, Any]:
        ident, worker, instant = _id(job_id, "job"), _id(owner, "worker"), _when(now)
        reason = _id(reason_code, "failure reason")
        if type(retry_seconds) is not int or not 10 <= retry_seconds <= 3600:
            raise EvidenceError("invalid retry delay")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self._check_lease(ident, worker, generation, instant)
            state = "DEAD" if row[6] >= MAX_ATTEMPTS else "QUEUED"
            self.db.execute(
                "UPDATE jobs SET state=?,available_at=?,lease_owner=NULL,"
                "lease_until=NULL,last_error=? WHERE id=?",
                (state, (instant+timedelta(seconds=retry_seconds)).isoformat(),
                 reason, ident),
            )
            self._append("failed_" + state.lower(), ident, instant, generation, reason)
            self.db.commit()
            return {
                "state": state, "job_id": ident, "publication_authorized": False,
            }
        except BaseException:
            self.db.rollback()
            raise

    def verified_snapshot(self, job_id: str) -> dict[str, Any]:
        """Verify persisted queued dossier/result hashes before release review.

        Delivers NO work product or private client data, only verified digests.
        A malicious edit of either SQLite payload or held output is detected.
        """
        ident = _id(job_id, "job")
        self._audit()
        row = self.db.execute(
            "SELECT state,payload,payload_sha,output,output_sha FROM jobs WHERE id=?",
            (ident,),
        ).fetchone()
        if not row:
            raise EvidenceError("release dossier not found in private work queue")
        state, payload, payload_sha, output, output_sha = row
        if hashlib.sha256(payload.encode()).hexdigest() != payload_sha:
            raise EvidenceError("queued dossier payload changed after submission")
        if state != "HELD" or not output or not output_sha:
            raise EvidenceError("queued dossier has no completed held review")
        if hashlib.sha256(output.encode()).hexdigest() != output_sha:
            raise EvidenceError("held evaluator result changed after completion")
        try:
            parsed = json.loads(output)
            dossier = json.loads(payload)
        except ValueError as exc:
            raise EvidenceError("held dossier JSON invalid") from exc
        if (parsed.get("status") != "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW"
                or parsed.get("publication_authorized") is not False
                or parsed.get("dossier_sha256") != payload_sha
                or dossier.get("dossier_id") != ident):
            raise EvidenceError("held job output is not bound to original dossier")
        return {
            "state": "HELD_VERIFIED_DIGEST_ONLY",
            "job_id": ident, "dossier_sha256": payload_sha,
            "analysis_sha256": output_sha,
            "publication_authorized": False,
        }

    def status(self, job_id: str) -> dict[str, Any]:
        ident = _id(job_id, "job")
        row = self.db.execute(
            "SELECT state,attempts,generation,output_sha FROM jobs WHERE id=?",
            (ident,),
        ).fetchone()
        if row is None:
            return {"state": "NOT_FOUND", "publication_authorized": False}
        return {
            "job_id": ident, "state": row[0], "attempts": row[1],
            "generation": row[2], "result_sha256": row[3],
            "publication_authorized": False,
        }
