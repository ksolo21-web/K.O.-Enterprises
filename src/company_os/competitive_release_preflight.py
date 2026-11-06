"""CE-4A: company-wide digest-bound release PRE-FLIGHT, deny-only.

Checks an exact venture/recipient/scope/cost/approval proposal against the
completed durable competitive queue, a rooted critic review, actual original
output PDF bytes and the global company policy. There are deliberately NO
send, publish, launch or deploy functions and NO success/ALLOW outcome.

Root PAUSE_AUTONOMY and PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False remain.
A signed reviewer assertion is not a genuinely separate source inspection.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .competitive_critic_audit import CriticReviewLedger
from .competitive_critic_review import assess_signed_review
from .competitive_evidence_engine import assess_competitive_dossier, canonical
from .competitive_launch_guard import (
    PRODUCTION_RELEASE_CONTROLLER_CERTIFIED, requires_competitive_engine,
    inspect_venture_launch_prerequisite,
)
from .competitive_work_queue import CompetitiveWorkQueue
from .policy import ActionRequest, approval_matches, classify_action, evaluate_action
from .source_provenance import EvidenceError

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_FIELDS = frozenset({
    "schema_version", "request_id", "action", "venture_id", "dossier_id",
    "dossier_sha256", "artifact_sha256", "review_id", "recipient_id",
    "client_scope_id", "privacy_review_id", "legal_review_id",
    "client_consent_id", "requested_at", "estimated_cost_cents",
})


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise EvidenceError("release request missing/invalid " + name)
    return value


def _stamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or len(value) > 48:
        raise EvidenceError("invalid release timestamp " + name)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid release timestamp " + name) from exc
    if result.tzinfo is None:
        raise EvidenceError("release timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise EvidenceError("release digest invalid " + name)
    return value


def inspect_release_proposal(
    proposal: Mapping[str, Any],
    dossier: Mapping[str, Any],
    artifact_pdf_path: Path | str,
    critic_policy: Mapping[str, Any],
    signed_review: Mapping[str, Any],
    queue: CompetitiveWorkQueue,
    critic_audit: CriticReviewLedger,
    *,
    approval: Mapping[str, Any] | None,
    repo_root: Path | str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate all available internal facts; ALWAYS deny production release."""
    try:
        return _inspect(
            proposal, dossier, artifact_pdf_path, critic_policy,
            signed_review, queue, critic_audit, approval=approval,
            repo_root=repo_root, now=now,
        )
    except (EvidenceError, OSError, TypeError, KeyError, ValueError,
            OverflowError, AttributeError) as exc:
        return _blocked(["invalid_or_unsafe_release_packet:" + str(exc)[:160]])


def _blocked(reasons: list[str], digest: str | None = None) -> dict[str, Any]:
    return {
        "status": "BLOCK", "release_authorized": False,
        "publication_authorized": False, "engine_production_accepted": False,
        "request_sha256": digest,
        "reasons": sorted(set(reasons)),
    }


def _inspect(
    proposal: Mapping[str, Any],
    dossier: Mapping[str, Any],
    artifact_pdf_path: Path | str,
    critic_policy: Mapping[str, Any],
    signed_review: Mapping[str, Any],
    queue: CompetitiveWorkQueue,
    critic_audit: CriticReviewLedger,
    *,
    approval: Mapping[str, Any] | None,
    repo_root: Path | str,
    now: datetime | None,
) -> dict[str, Any]:
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise EvidenceError("release inspection time must include timezone")
    current = current.astimezone(timezone.utc)
    if not isinstance(proposal, Mapping) or set(proposal) != _FIELDS:
        raise EvidenceError("release packet required fields missing or unexpected")
    raw = canonical(dict(proposal))
    request_digest = hashlib.sha256(raw).hexdigest()
    if proposal["schema_version"] != "1.0":
        raise EvidenceError("unsupported release packet version")
    for item in ("request_id", "venture_id", "dossier_id", "review_id", "recipient_id",
                 "client_scope_id", "privacy_review_id", "legal_review_id",
                 "client_consent_id"):
        _id(proposal[item], item)
    for item in ("dossier_sha256", "artifact_sha256"):
        _sha(proposal[item], item)
    action = proposal["action"]
    if not isinstance(action, str) or not _ID.fullmatch(action):
        raise EvidenceError("invalid release action identifier")
    if not requires_competitive_engine(action):
        raise EvidenceError("release action lacks company competitive engine gate")
    cost = proposal["estimated_cost_cents"]
    if type(cost) is not int or not 0 <= cost <= 10_000_000:
        raise EvidenceError("invalid bounded release cost")
    prepared = _stamp(proposal["requested_at"], "requested_at")
    if not timedelta(minutes=-2) <= current-prepared <= timedelta(hours=1):
        raise EvidenceError("release packet date stale or future")
    if proposal["venture_id"] != dossier.get("venture_id") or proposal["dossier_id"] != dossier.get("dossier_id"):
        raise EvidenceError("release venture or dossier reference mismatch")
    expected_digest = hashlib.sha256(canonical(dossier)).hexdigest()
    if expected_digest != proposal["dossier_sha256"]:
        raise EvidenceError("release dossier digest differs from current evidence")
    if not isinstance(queue, CompetitiveWorkQueue) or not isinstance(critic_audit, CriticReviewLedger):
        raise EvidenceError("release cannot use a fake work queue or critic ledger")
    snapshot = queue.verified_snapshot(proposal["dossier_id"])
    if snapshot["dossier_sha256"] != expected_digest:
        raise EvidenceError("release dossier is not the exact held queued work item")

    issues: list[str] = []
    comparison = assess_competitive_dossier(dossier, now=current)
    if comparison["status"] != "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW":
        issues.append("competitive_evidence_dossier_not_in_reviewable_state")

    review = assess_signed_review(
        dossier, proposal["artifact_sha256"], critic_policy, signed_review,
        artifact_pdf_path=artifact_pdf_path, now=current,
    )
    if review["state"] == "BLOCK":
        issues.append("signed_critic_review_invalid_or_outdated")
    else:
        if (review["review_id"] != proposal["review_id"] or
                review["artifact_sha256"] != proposal["artifact_sha256"] or
                review["dossier_sha256"] != expected_digest):
            issues.append("signed_review_not_bound_to_proposed_release")
        try:
            recorded = critic_audit.review_status(
                proposal["review_id"], critic_policy, now=current,
            )
            if recorded["state"] != "SIGNED_ONLY_EXTERNAL_REVIEW_NOT_PROVEN":
                issues.append("signed_critic_review_unrecorded_or_revoked")
        except (EvidenceError, TypeError, ValueError):
            issues.append("critic_review_audit_missing_or_untrusted")

    # A plain approval mapping is not a signed CEO identity assertion.
    # Require exact scope/digest/recipient fields even for internal review,
    # then STILL deny due to real production/reviewer/source blockers.
    if not isinstance(approval, Mapping):
        issues.append("exact_ceo_release_approval_not_present")
    elif any(
        approval.get(field) != proposal[referenced]
        for field, referenced in (
            ("venture_id", "venture_id"),
            ("dossier_sha256", "dossier_sha256"),
            ("artifact_sha256", "artifact_sha256"),
            ("recipient_id", "recipient_id"),
            ("client_scope_id", "client_scope_id"),
        )
    ):
        issues.append("ceo_approval_scope_or_digest_mismatch")
    else:
        request = ActionRequest(
            action=action, actor="ceo_release_preflight", external=True,
            estimated_cost_cents=cost, reversible=False, risk_level="high",
        )
        required_class = classify_action(request)
        matched, _ = approval_matches(approval, request, required_class)
        if not matched:
            issues.append("ceo_approval_metadata_invalid_or_expired")

    action_request = ActionRequest(
        action=action, actor="ceo_release_preflight", external=True,
        estimated_cost_cents=cost, reversible=False, risk_level="high",
    )
    decision = evaluate_action(action_request, approval=approval, repo_root=repo_root)
    if not decision.allowed:
        issues.append(
            "root_emergency_pause_active" if decision.blocked_by_pause else
            "competitive_engine_or_company_policy_blocked"
        )
    # These cannot be inferred from developer-generated signatures or mock
    # health. Actual independent operational demonstrations are mandatory.
    issues.extend([
        "original_issuer_and_competitor_sources_not_independently_authenticated",
        "real_independent_critic_inspection_not_operationally_proven",
        "client_consent_legal_and_privacy_references_not_externally_authenticated",
        "protected_no_bypass_release_controller_not_certified",
        "external_audit_and_ongoing_monitor_evidence_not_verified",
    ])
    if not PRODUCTION_RELEASE_CONTROLLER_CERTIFIED:
        issues.append("production_release_hard_lock_active")
    return _blocked(issues, request_digest)


class ReleaseAttemptLedger:
    """Records only REFUSED attempts, never a release token or action executor."""

    def __init__(self, repo_root: Path | str):
        import sqlite3
        self.root = Path(repo_root).resolve()
        if not self.root.is_dir():
            raise EvidenceError("release refusal audit root missing")
        folder = self.root
        for part in ("state", "competitive_engine", "release_attempts"):
            folder = folder / part
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                raise EvidenceError("release refusal audit storage path unsafe")
            folder.mkdir(mode=0o700, exist_ok=True)
            if not folder.resolve().is_relative_to(self.root):
                raise EvidenceError("release refusal audit escapes private root")
            if os.name == "posix" and part == "release_attempts":
                folder.chmod(0o700)
        self.path = folder / "denials.sqlite3"
        if self.path.is_symlink():
            raise EvidenceError("release refusal audit symlink forbidden")
        self.db = sqlite3.connect(str(self.path), timeout=8, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS refusals (
                seq INTEGER PRIMARY KEY, request_sha TEXT NOT NULL,
                reasons_sha TEXT NOT NULL, observed_at TEXT NOT NULL,
                previous_sha TEXT NOT NULL, event_sha TEXT NOT NULL
            )""")
        for op in ("UPDATE", "DELETE"):
            self.db.execute(
                f"CREATE TRIGGER IF NOT EXISTS deny_release_{op.lower()} "
                f"BEFORE {op} ON refusals BEGIN SELECT RAISE(ABORT,'refusal log append only'); END"
            )
        if os.name == "posix":
            self.path.chmod(0o600)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def audit(self) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT seq,request_sha,reasons_sha,observed_at,previous_sha,event_sha "
            "FROM refusals ORDER BY seq"
        ).fetchall()
        previous = "GENESIS"
        for index, (seq, rid, reasons, date, prior, digest) in enumerate(rows,1):
            raw = f"{seq}:{rid}:{reasons}:{date}".encode()
            expected = hashlib.sha256(previous.encode() + b"\n" + raw).hexdigest()
            if seq != index or prior != previous or digest != expected:
                raise EvidenceError("release refusal history has been altered")
            previous = digest
        return {
            "state": "LOCAL_REFUSAL_AUDIT_NOT_EXTERNAL_PROOF",
            "refusals": len(rows), "head_sha256": previous,
            "publication_authorized": False,
        }

    def record_refusal(
        self, decision: Mapping[str, Any], *, now: datetime | None = None,
    ) -> dict[str, Any]:
        if (not isinstance(decision, Mapping) or decision.get("status") != "BLOCK"
                or decision.get("publication_authorized") is not False
                or decision.get("release_authorized") is not False):
            raise EvidenceError("release audit may only record absolute refusals")
        request_sha = decision.get("request_sha256") or hashlib.sha256(
            b"invalid-request"
        ).hexdigest()
        _sha(request_sha, "refusal request")
        reasons = decision.get("reasons")
        if not isinstance(reasons, list) or not reasons or not all(
            isinstance(v, str) for v in reasons
        ):
            raise EvidenceError("release refusal has no safe reason codes")
        reason_sha = hashlib.sha256(canonical(reasons)).hexdigest()
        instant = now if now is not None else datetime.now(timezone.utc)
        if instant.tzinfo is None:
            raise EvidenceError("release refusal time must have timezone")
        observed_at = instant.astimezone(timezone.utc).isoformat()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self.audit()
            seq = rows["refusals"] + 1
            previous = rows["head_sha256"]
            raw = f"{seq}:{request_sha}:{reason_sha}:{observed_at}".encode()
            event_sha = hashlib.sha256(previous.encode() + b"\n" + raw).hexdigest()
            self.db.execute(
                "INSERT INTO refusals VALUES(?,?,?,?,?,?)",
                (seq, request_sha, reason_sha, observed_at, previous, event_sha),
            )
            self.db.commit()
            return {
                "state": "DENIAL_LOGGED_LOCALLY",
                "refusal_id": seq, "publication_authorized": False,
            }
        except BaseException:
            self.db.rollback()
            raise
