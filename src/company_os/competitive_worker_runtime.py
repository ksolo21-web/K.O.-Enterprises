"""CE-2B local bounded competitive queue runner and untrusted readiness probe.

Manual-only INTERNAL execution. Runs no source retrieval, send, release,
external API, autonomous schedule or business launch. The probe reports actual
local queue evidence but ALWAYS returns ready=False and is not signed by a
separate production monitor or genuinely independent reviewer.

The company-wide PAUSE_AUTONOMY remains active. No daemon/auto-start.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .competitive_work_queue import CompetitiveWorkQueue
from .source_provenance import EvidenceError
from .policy import ActionRequest, evaluate_action

MAX_CYCLE_JOBS = 100
MAX_CYCLE_SECONDS = 120
TELEMETRY_FILE = "worker_offline_telemetry.json"


def _when(value: datetime | None) -> datetime:
    moment = value if value is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise EvidenceError("worker cycle requires timezone-aware timestamp")
    return moment.astimezone(timezone.utc)


def _private_root(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("competitive worker root is unavailable")
    current = root
    for part in ("state", "competitive_engine", "work_queue"):
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise EvidenceError("competitive worker state path is unsafe")
        current.mkdir(mode=0o700, exist_ok=True)
        if not current.resolve().is_relative_to(root):
            raise EvidenceError("competitive worker state escapes private root")
        if os.name == "posix" and part == "work_queue":
            current.chmod(0o700)
            if current.stat().st_uid != os.geteuid():
                raise EvidenceError("worker does not own private queue state")
    return current


def _locked_file(path: Path):
    try:
        import fcntl
    except ImportError as exc:
        raise EvidenceError("Linux file-lock support unavailable") from exc
    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if path.is_symlink():
        raise EvidenceError("worker leader-lock symlink refused")
    fd = os.open(path, flags, 0o600)
    if os.name == "posix":
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o777 != 0o600:
            os.close(fd)
            raise EvidenceError("worker leader lock ownership or mode unsafe")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def _write_telemetry(folder: Path, data: dict[str, Any]) -> None:
    blob = json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    if len(blob) > 8192:
        raise EvidenceError("worker telemetry record exceeds reviewed size cap")
    target = folder / TELEMETRY_FILE
    if target.is_symlink():
        raise EvidenceError("worker telemetry destination is a symlink")
    temporary = folder / ("." + TELEMETRY_FILE + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        raise EvidenceError("worker telemetry temporary file already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = None
    try:
        fd = os.open(temporary, flags, 0o600)
        with os.fdopen(fd, "wb") as output:
            fd = None
            output.write(blob)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        if os.name == "posix":
            os.chmod(target, 0o600)
    finally:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def run_internal_cycle(
    repo_root: Path | str, *, worker_id: str = "offline-worker",
    max_jobs: int = 20, max_seconds: int = 60,
    now: datetime | None = None, scheduled: bool = False,
) -> dict[str, Any]:
    """Process a bounded finite batch of already-queued internal dossiers.

    Scheduled operation is categorically disabled in this prototype;
    production requires separately approved protected service supervision.
    """
    instant = _when(now)
    if scheduled:
        return {
            "state": "BLOCK_SCHEDULED_SERVICE_NOT_AUTHORIZED",
            "jobs_processed": 0, "production_ready": False,
            "publication_authorized": False,
        }
    if (type(max_jobs) is not int or not 1 <= max_jobs <= MAX_CYCLE_JOBS
            or type(max_seconds) is not int or not 1 <= max_seconds <= MAX_CYCLE_SECONDS):
        raise EvidenceError("worker cycle budget exceeds bounds")
    if (not isinstance(worker_id, str) or not 3 <= len(worker_id) <= 80
            or not all(ch.isascii() and (ch.isalnum() or ch in "-_") for ch in worker_id)):
        raise EvidenceError("invalid offline worker identity")
    internal = ActionRequest(
        action="internal_analysis", actor=worker_id,
        external=False, scheduled=False, reversible=True,
        estimated_cost_cents=0,
    )
    decision = evaluate_action(internal, repo_root=repo_root)
    if not decision.allowed:
        raise EvidenceError("company policy denied internal offline analysis")
    folder = _private_root(repo_root)
    lock = _locked_file(folder / "worker.lock")
    if lock is None:
        return {
            "state": "BUSY_ANOTHER_LOCAL_WORKER_OWNS_LEADER_LOCK",
            "jobs_processed": 0, "production_ready": False,
            "publication_authorized": False,
        }
    try:
        started = time.monotonic()
        stats = {"held": 0, "blocked": 0, "failed": 0}
        attempts = 0
        with CompetitiveWorkQueue(repo_root) as queue:
            while attempts < max_jobs and (time.monotonic() - started) < max_seconds:
                # Use an explicitly bounded lease longer than the total cycle.
                # A deliberately frozen simulated test clock never issues real
                # source or customer actions.
                leased = queue.lease(owner=worker_id, now=instant, seconds=MAX_CYCLE_SECONDS + 30)
                if leased is None:
                    break
                attempts += 1
                try:
                    result = queue.complete(
                        job_id=leased["job_id"], owner=worker_id,
                        generation=leased["generation"], now=instant,
                    )
                    stats["held" if result["state"] == "HELD" else "blocked"] += 1
                except (EvidenceError, ValueError, TypeError, OSError):
                    # Fail closed and bounded. Do not print private dossiers.
                    queue.fail(
                        job_id=leased["job_id"],owner=worker_id,
                        generation=leased["generation"],
                        reason_code="internal-evaluator-error",now=instant,
                    )
                    stats["failed"] += 1
            audit = queue.audit_status()
        telemetry = {
            "schema_version": "1.0",
            "state": "OFFLINE_INTERNAL_NOT_PRODUCTION_HEALTH",
            "observed_at": instant.isoformat(),
            "worker_id": worker_id,
            "jobs_processed": sum(stats.values()),
            "held": stats["held"], "blocked": stats["blocked"],
            "failed": stats["failed"],
            "queue_audit_head_sha256": audit["head_sha256"],
            "production_ready": False,
            "independent_critic_observed": False,
            "original_source_verification_observed": False,
            "publication_authorized": False,
        }
        _write_telemetry(folder, telemetry)
        return telemetry
    finally:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_UN)
        os.close(lock)


def probe_offline_worker(
    repo_root: Path | str, *, now: datetime | None = None,
) -> dict[str, Any]:
    """Report local telemetry validity while rejecting all live claims."""
    instant = _when(now)
    path = Path(repo_root).resolve() / "state" / "competitive_engine" / "work_queue" / TELEMETRY_FILE
    problems = [
        "no_protected_external_monitor",
        "no_authenticated_original_source_worker",
        "no_operational_independent_critic",
        "no_certified_no_bypass_release_controller",
    ]
    result = {
        "state": "NOT_PRODUCTION_READY",
        "ready": False,
        "publication_authorized": False,
        "reasons": problems,
    }
    if path.is_symlink() or not path.is_file():
        result["reasons"] = problems + ["offline_worker_telemetry_unavailable"]
        return result
    if not 50 <= path.stat().st_size <= 8192:
        result["reasons"] = problems + ["offline_worker_telemetry_invalid"]
        return result
    try:
        record = json.loads(path.read_text("utf-8"))
        observed = datetime.fromisoformat(record["observed_at"])
        if observed.tzinfo is None or not (
            timedelta(seconds=-30) <= instant-observed.astimezone(timezone.utc)
            <= timedelta(minutes=5)
        ):
            raise ValueError("telemetry heartbeat stale")
        if (record.get("state") != "OFFLINE_INTERNAL_NOT_PRODUCTION_HEALTH"
                or record.get("production_ready") is not False
                or record.get("publication_authorized") is not False
                or record.get("independent_critic_observed") is not False
                or record.get("original_source_verification_observed") is not False):
            raise ValueError("telemetry falsely asserts production health")
        digest = record.get("queue_audit_head_sha256")
        if (not isinstance(digest, str) or not (
            len(digest) == 64 or digest == "GENESIS"
        )):
            raise ValueError("telemetry queue audit head invalid")
        result["locally_observed_jobs"] = record["jobs_processed"]
        result["local_telemetry_record_present"] = True
    except (OSError, ValueError, TypeError, KeyError):
        result["reasons"] = problems + ["offline_worker_telemetry_invalid_or_stale"]
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Manual bounded internal competitive worker")
    parser.add_argument("repo_root")
    parser.add_argument("--jobs", type=int, default=20)
    parser.add_argument("--worker", default="offline-worker")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    value = (probe_offline_worker(args.repo_root) if args.probe_only else
             run_internal_cycle(args.repo_root,worker_id=args.worker,max_jobs=args.jobs))
    print(json.dumps(value, sort_keys=True))
    return 1  # NEVER treat a local worker execution as a production-ready go-live


if __name__ == "__main__":
    raise SystemExit(main())
