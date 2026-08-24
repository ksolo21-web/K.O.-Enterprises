"""Deterministic rules for the durable company runtime.

This module deliberately contains no persistence, network, subprocess, or
clock-reading code.  Callers supply durable records and the current time, apply
the returned decisions transactionally, and record the result in the audit
trail.  Keeping these rules pure makes scheduler and worker recovery behavior
repeatable in tests and across separate processes.
"""

from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable, Sequence

from .errors import ConflictError, ValidationError


class TaskState(StrEnum):
    PROPOSED = "proposed"
    WAITING_DEPENDENCY = "waiting_dependency"
    WAITING_POLICY = "waiting_policy"
    READY = "ready"
    LEASED = "leased"
    RUNNING = "running"
    REVIEW = "review"
    RETRY_WAIT = "retry_wait"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATES = frozenset(
    {
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.DEAD_LETTER,
        TaskState.CANCELLED,
    }
)


TASK_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.PROPOSED: frozenset(
        {
            TaskState.WAITING_DEPENDENCY,
            TaskState.WAITING_POLICY,
            TaskState.READY,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.WAITING_DEPENDENCY: frozenset(
        {
            TaskState.WAITING_POLICY,
            TaskState.READY,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.WAITING_POLICY: frozenset(
        {TaskState.WAITING_DEPENDENCY, TaskState.READY, TaskState.CANCELLED}
    ),
    TaskState.READY: frozenset(
        {TaskState.WAITING_POLICY, TaskState.LEASED, TaskState.CANCELLED}
    ),
    # Returning a lease to READY is the crash-recovery path.  A fenced lease
    # check must protect the durable update that applies this transition.
    TaskState.LEASED: frozenset(
        {
            TaskState.READY,
            TaskState.RUNNING,
            TaskState.RETRY_WAIT,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.RUNNING: frozenset(
        {
            TaskState.REVIEW,
            TaskState.RETRY_WAIT,
            TaskState.FAILED,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.REVIEW: frozenset(
        {
            TaskState.SUCCEEDED,
            TaskState.RETRY_WAIT,
            TaskState.FAILED,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.RETRY_WAIT: frozenset(
        {
            TaskState.READY,
            TaskState.WAITING_POLICY,
            TaskState.BLOCKED,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.BLOCKED: frozenset(
        {
            TaskState.WAITING_POLICY,
            TaskState.READY,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.SUCCEEDED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.DEAD_LETTER: frozenset(),
    TaskState.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class TaskTransitionDecision:
    allowed: bool
    current: TaskState
    target: TaskState
    changed: bool
    reason: str


def _task_state(value: TaskState | str, *, name: str) -> TaskState:
    try:
        return TaskState(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"unknown {name}: {value}") from exc


def evaluate_task_transition(
    current: TaskState | str, target: TaskState | str
) -> TaskTransitionDecision:
    """Evaluate a durable task transition.

    Repeating the current state is an allowed no-op.  This makes replay of a
    command idempotent without permitting an otherwise illegal state jump.
    """

    normalized_current = _task_state(current, name="current task state")
    normalized_target = _task_state(target, name="target task state")
    if normalized_current is normalized_target:
        return TaskTransitionDecision(
            allowed=True,
            current=normalized_current,
            target=normalized_target,
            changed=False,
            reason="the transition is an idempotent no-op",
        )
    if normalized_target in TASK_TRANSITIONS[normalized_current]:
        return TaskTransitionDecision(
            allowed=True,
            current=normalized_current,
            target=normalized_target,
            changed=True,
            reason="the transition is allowed by the task lifecycle",
        )
    return TaskTransitionDecision(
        allowed=False,
        current=normalized_current,
        target=normalized_target,
        changed=False,
        reason=f"task cannot transition from {normalized_current.value} to {normalized_target.value}",
    )


def require_task_transition(current: TaskState | str, target: TaskState | str) -> None:
    """Raise when ``current -> target`` is not a legal task transition."""

    decision = evaluate_task_transition(current, target)
    if not decision.allowed:
        raise ConflictError(decision.reason)


class DependencyDisposition(StrEnum):
    READY = "ready"
    WAITING = "waiting"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class TaskDependency:
    task_id: str
    state: TaskState | str
    required: bool = True

    def __post_init__(self) -> None:
        _require_identifier("dependency task_id", self.task_id)
        _task_state(self.state, name="dependency task state")
        if type(self.required) is not bool:
            raise ValidationError("dependency required must be boolean")


@dataclass(frozen=True, slots=True)
class DependencyDecision:
    disposition: DependencyDisposition
    waiting_task_ids: tuple[str, ...] = ()
    blocking_task_ids: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.disposition is DependencyDisposition.READY


def evaluate_dependencies(dependencies: Iterable[TaskDependency]) -> DependencyDecision:
    """Return whether all required dependencies completed successfully.

    Optional dependencies are informational and never hold or block the task.
    Duplicate dependency identifiers fail closed because conflicting snapshots
    must be reconciled before scheduling.
    """

    required: dict[str, TaskState] = {}
    for dependency in dependencies:
        if not isinstance(dependency, TaskDependency):
            raise ValidationError("dependencies must contain TaskDependency records")
        if not dependency.required:
            continue
        task_id = dependency.task_id.strip()
        if task_id in required:
            raise ValidationError(f"duplicate required dependency: {task_id}")
        required[task_id] = _task_state(dependency.state, name="dependency task state")

    blocking = tuple(
        sorted(task_id for task_id, state in required.items() if state in TERMINAL_TASK_STATES and state is not TaskState.SUCCEEDED)
    )
    if blocking:
        return DependencyDecision(
            disposition=DependencyDisposition.BLOCKED,
            blocking_task_ids=blocking,
        )
    waiting = tuple(
        sorted(task_id for task_id, state in required.items() if state is not TaskState.SUCCEEDED)
    )
    if waiting:
        return DependencyDecision(
            disposition=DependencyDisposition.WAITING,
            waiting_task_ids=waiting,
        )
    return DependencyDecision(disposition=DependencyDisposition.READY)


def _aware_utc(name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _require_identifier(name: str, value: object) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValidationError(f"{name} must not be empty")
    return text


@dataclass(frozen=True, slots=True)
class QueueCandidate:
    task_id: str
    state: TaskState | str
    priority: int
    available_at: datetime
    created_at: datetime
    deadline_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_identifier("task_id", self.task_id)
        _task_state(self.state, name="queue task state")
        if type(self.priority) is not int:
            raise ValidationError("priority must be an integer")
        if abs(self.priority) > 1_000_000:
            raise ValidationError("priority must be between -1000000 and 1000000")
        _aware_utc("available_at", self.available_at)
        _aware_utc("created_at", self.created_at)
        if self.deadline_at is not None:
            _aware_utc("deadline_at", self.deadline_at)


def priority_key(candidate: QueueCandidate) -> tuple[object, ...]:
    """Return a stable queue key: priority, deadline, availability, age, ID."""

    if not isinstance(candidate, QueueCandidate):
        raise ValidationError("candidate must be a QueueCandidate")
    deadline = (
        _aware_utc("deadline_at", candidate.deadline_at)
        if candidate.deadline_at is not None
        else datetime.max.replace(tzinfo=timezone.utc)
    )
    return (
        -candidate.priority,
        candidate.deadline_at is None,
        deadline,
        _aware_utc("available_at", candidate.available_at),
        _aware_utc("created_at", candidate.created_at),
        candidate.task_id,
    )


def order_ready_tasks(
    candidates: Iterable[QueueCandidate], *, now: datetime
) -> tuple[QueueCandidate, ...]:
    """Filter currently runnable tasks and return deterministic lease order."""

    current = _aware_utc("now", now)
    ready: list[QueueCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, QueueCandidate):
            raise ValidationError("candidates must contain QueueCandidate records")
        task_id = candidate.task_id.strip()
        if task_id in seen:
            raise ValidationError(f"duplicate queue candidate: {task_id}")
        seen.add(task_id)
        if (
            _task_state(candidate.state, name="queue task state") is TaskState.READY
            and _aware_utc("available_at", candidate.available_at) <= current
        ):
            ready.append(candidate)
    return tuple(sorted(ready, key=priority_key))


@dataclass(frozen=True, slots=True)
class LeaseRecord:
    task_id: str
    owner_id: str
    token: str
    epoch: int
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _require_identifier("lease task_id", self.task_id)
        _require_identifier("lease owner_id", self.owner_id)
        token = _require_identifier("lease token", self.token)
        if token != self.token:
            raise ValidationError("lease token must not have surrounding whitespace")
        if type(self.epoch) is not int or self.epoch < 1:
            raise ValidationError("lease epoch must be a positive integer")
        issued = _aware_utc("lease issued_at", self.issued_at)
        expires = _aware_utc("lease expires_at", self.expires_at)
        if expires <= issued:
            raise ValidationError("lease expires_at must be later than issued_at")


@dataclass(frozen=True, slots=True)
class LeaseProof:
    owner_id: str
    token: str
    epoch: int

    def __post_init__(self) -> None:
        _require_identifier("lease proof owner_id", self.owner_id)
        token = _require_identifier("lease proof token", self.token)
        if token != self.token:
            raise ValidationError("lease proof token must not have surrounding whitespace")
        if type(self.epoch) is not int or self.epoch < 1:
            raise ValidationError("lease proof epoch must be a positive integer")


class LeaseValidationReason(StrEnum):
    VALID = "valid"
    OWNER_MISMATCH = "owner_mismatch"
    TOKEN_MISMATCH = "token_mismatch"
    EPOCH_MISMATCH = "epoch_mismatch"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class LeaseValidation:
    valid: bool
    reason: LeaseValidationReason


def next_lease_epoch(current_epoch: int) -> int:
    if type(current_epoch) is not int or current_epoch < 0:
        raise ValidationError("current lease epoch must be a non-negative integer")
    if current_epoch >= 9_223_372_036_854_775_807:
        raise ValidationError("current lease epoch exceeds the durable integer range")
    return current_epoch + 1


def validate_lease(
    lease: LeaseRecord, proof: LeaseProof, *, now: datetime
) -> LeaseValidation:
    """Validate owner, token, epoch, and expiry for a fenced durable update."""

    if not isinstance(lease, LeaseRecord) or not isinstance(proof, LeaseProof):
        raise ValidationError("lease and proof must be LeaseRecord and LeaseProof values")
    current = _aware_utc("now", now)
    if lease.owner_id.casefold() != proof.owner_id.casefold():
        return LeaseValidation(False, LeaseValidationReason.OWNER_MISMATCH)
    if lease.epoch != proof.epoch:
        return LeaseValidation(False, LeaseValidationReason.EPOCH_MISMATCH)
    if not hmac.compare_digest(lease.token, proof.token):
        return LeaseValidation(False, LeaseValidationReason.TOKEN_MISMATCH)
    if _aware_utc("lease expires_at", lease.expires_at) <= current:
        return LeaseValidation(False, LeaseValidationReason.EXPIRED)
    return LeaseValidation(True, LeaseValidationReason.VALID)


class FailureKind(StrEnum):
    TRANSIENT = "transient"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    POLICY_DENIED = "policy_denied"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    INVALID_INPUT = "invalid_input"
    INVARIANT = "invariant"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class RetryAction(StrEnum):
    RETRY = "retry"
    RECONCILE = "reconcile"
    BLOCKED = "blocked"
    DEAD_LETTER = "dead_letter"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class FailureReport:
    kind: FailureKind | str
    external_outcome_unknown: bool = False
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        try:
            FailureKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"unknown failure kind: {self.kind}") from exc
        if type(self.external_outcome_unknown) is not bool:
            raise ValidationError("external_outcome_unknown must be boolean")
        if self.retry_after_seconds is not None and (
            type(self.retry_after_seconds) is not int or self.retry_after_seconds < 0
        ):
            raise ValidationError("retry_after_seconds must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class RetryDecision:
    action: RetryAction
    reason: str
    delay_seconds: int | None = None


def retry_backoff_seconds(
    attempt_number: int,
    *,
    base_seconds: int = 30,
    cap_seconds: int = 3_600,
    jitter_ratio: float = 0.20,
    jitter_key: str = "company_os",
) -> int:
    """Return capped exponential backoff with stable hash-derived jitter."""

    if type(attempt_number) is not int or attempt_number < 1:
        raise ValidationError("attempt_number must be a positive integer")
    if type(base_seconds) is not int or base_seconds < 0:
        raise ValidationError("base_seconds must be a non-negative integer")
    if type(cap_seconds) is not int or cap_seconds < 0:
        raise ValidationError("cap_seconds must be a non-negative integer")
    if base_seconds > cap_seconds:
        raise ValidationError("base_seconds must not exceed cap_seconds")
    if isinstance(jitter_ratio, bool):
        raise ValidationError("jitter_ratio must be a number from 0 to 1")
    try:
        normalized_jitter = float(jitter_ratio)
    except (TypeError, ValueError) as exc:
        raise ValidationError("jitter_ratio must be a number from 0 to 1") from exc
    if not math.isfinite(normalized_jitter) or not 0.0 <= normalized_jitter <= 1.0:
        raise ValidationError("jitter_ratio must be a number from 0 to 1")
    normalized_key = _require_identifier("jitter_key", jitter_key)
    if base_seconds == 0 or cap_seconds == 0:
        return 0

    # Avoid constructing an enormous integer for a corrupt attempt counter.
    exponent = min(attempt_number - 1, 62)
    unjittered = min(cap_seconds, base_seconds * (1 << exponent))
    digest = hashlib.sha256(
        f"{normalized_key}\x00{attempt_number}".encode("utf-8")
    ).digest()
    unit = int.from_bytes(digest[:8], "big") / ((1 << 64) - 1)
    factor = (1.0 - normalized_jitter) + (2.0 * normalized_jitter * unit)
    jittered = int(round(unjittered * factor))
    return max(1, min(cap_seconds, jittered))


def decide_retry(
    failure: FailureReport,
    *,
    attempts_completed: int,
    max_attempts: int,
    base_seconds: int = 30,
    cap_seconds: int = 3_600,
    jitter_ratio: float = 0.20,
    jitter_key: str = "company_os",
) -> RetryDecision:
    """Classify a failure without risking duplicate external effects."""

    if not isinstance(failure, FailureReport):
        raise ValidationError("failure must be a FailureReport")
    if type(attempts_completed) is not int or attempts_completed < 1:
        raise ValidationError("attempts_completed must be a positive integer")
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValidationError("max_attempts must be a positive integer")

    kind = FailureKind(failure.kind)
    if failure.external_outcome_unknown:
        return RetryDecision(
            RetryAction.RECONCILE,
            "the external outcome is unknown; reconcile before any resend",
        )
    if kind in {FailureKind.POLICY_DENIED, FailureKind.AUTHENTICATION, FailureKind.PERMISSION}:
        return RetryDecision(
            RetryAction.BLOCKED,
            "authority or access must change before the work can resume",
        )
    if kind is FailureKind.CANCELLED:
        return RetryDecision(RetryAction.CANCEL, "the work was deliberately cancelled")
    if kind in {FailureKind.INVALID_INPUT, FailureKind.INVARIANT, FailureKind.UNKNOWN}:
        return RetryDecision(
            RetryAction.DEAD_LETTER,
            "the failure is not safe to retry automatically",
        )
    if attempts_completed >= max_attempts:
        return RetryDecision(
            RetryAction.DEAD_LETTER,
            "the retry budget is exhausted",
        )

    delay = retry_backoff_seconds(
        attempts_completed,
        base_seconds=base_seconds,
        cap_seconds=cap_seconds,
        jitter_ratio=jitter_ratio,
        jitter_key=jitter_key,
    )
    if failure.retry_after_seconds is not None:
        # Retry-After is an external minimum and may intentionally exceed the
        # ordinary local backoff cap.
        delay = max(delay, failure.retry_after_seconds)
    return RetryDecision(
        RetryAction.RETRY,
        "the failure is transient and remains within the retry budget",
        delay_seconds=delay,
    )


class ReviewVerdict(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    reviewer_id: str
    reviewer_role: str
    verdict: ReviewVerdict | str

    def __post_init__(self) -> None:
        _require_identifier("reviewer_id", self.reviewer_id)
        _require_identifier("reviewer_role", self.reviewer_role)
        try:
            ReviewVerdict(self.verdict)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"unknown review verdict: {self.verdict}") from exc


class AcceptanceStatus(StrEnum):
    ACCEPTED = "accepted"
    PENDING = "pending"
    CHANGES_REQUIRED = "changes_required"
    REJECTED = "rejected"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class AcceptanceDecision:
    accepted: bool
    status: AcceptanceStatus
    reason: str
    missing_roles: tuple[str, ...] = ()


def evaluate_work_acceptance(
    *,
    producer_id: str,
    reviews: Iterable[ReviewRecord],
    required_roles: Iterable[str] = (),
    prohibited_reviewer_ids: Iterable[str] = (),
    independent_review_required: bool = True,
) -> AcceptanceDecision:
    """Enforce independent acceptance and required control-function reviews."""

    producer = _require_identifier("producer_id", producer_id).casefold()
    if type(independent_review_required) is not bool:
        raise ValidationError("independent_review_required must be boolean")
    prohibited = {producer}
    for reviewer_id in prohibited_reviewer_ids:
        prohibited.add(_require_identifier("prohibited reviewer_id", reviewer_id).casefold())
    normalized_required = {
        _require_identifier("required reviewer role", role).casefold() for role in required_roles
    }

    normalized_reviews: list[tuple[str, str, ReviewVerdict]] = []
    seen_reviewers: set[str] = set()
    for review in reviews:
        if not isinstance(review, ReviewRecord):
            raise ValidationError("reviews must contain ReviewRecord values")
        reviewer = review.reviewer_id.strip().casefold()
        if reviewer in seen_reviewers:
            return AcceptanceDecision(
                False,
                AcceptanceStatus.INVALID,
                f"reviewer {review.reviewer_id.strip()} submitted more than one review",
            )
        seen_reviewers.add(reviewer)
        if reviewer in prohibited:
            return AcceptanceDecision(
                False,
                AcceptanceStatus.INVALID,
                "a producer or otherwise prohibited actor cannot accept the work",
            )
        normalized_reviews.append(
            (reviewer, review.reviewer_role.strip().casefold(), ReviewVerdict(review.verdict))
        )

    if any(verdict is ReviewVerdict.REJECTED for _reviewer, _role, verdict in normalized_reviews):
        return AcceptanceDecision(False, AcceptanceStatus.REJECTED, "an independent reviewer rejected the work")
    if any(
        verdict is ReviewVerdict.CHANGES_REQUESTED
        for _reviewer, _role, verdict in normalized_reviews
    ):
        return AcceptanceDecision(
            False,
            AcceptanceStatus.CHANGES_REQUIRED,
            "an independent reviewer requested changes",
        )

    approved_roles = {
        role
        for _reviewer, role, verdict in normalized_reviews
        if verdict is ReviewVerdict.APPROVED
    }
    missing = tuple(sorted(normalized_required - approved_roles))
    if missing:
        return AcceptanceDecision(
            False,
            AcceptanceStatus.PENDING,
            "required control-function approval is missing",
            missing_roles=missing,
        )
    if independent_review_required and not any(
        verdict is ReviewVerdict.APPROVED for _reviewer, _role, verdict in normalized_reviews
    ):
        return AcceptanceDecision(
            False,
            AcceptanceStatus.PENDING,
            "at least one independent approval is required",
        )
    return AcceptanceDecision(
        True,
        AcceptanceStatus.ACCEPTED,
        "all required independent reviews approved the work",
    )


class IncidentSignal(StrEnum):
    UNAUTHORIZED_FINANCIAL_EFFECT = "unauthorized_financial_effect"
    SECRET_EXPOSURE = "secret_exposure"
    AUDIT_INTEGRITY_FAILURE = "audit_integrity_failure"
    POLICY_BYPASS = "policy_bypass"
    UNCONTAINED_PUBLIC_IMPACT = "uncontained_public_impact"
    AMBIGUOUS_EXTERNAL_EFFECT = "ambiguous_external_effect"
    REPEATED_CONNECTOR_FAILURE = "repeated_connector_failure"
    MATERIAL_DATA_RISK = "material_data_risk"
    BACKUP_RESTORE_FAILURE = "backup_restore_failure"
    DEAD_LETTER = "dead_letter"
    REPEATED_WORKER_FAILURE = "repeated_worker_failure"
    MISSED_OPERATIONAL_SLO = "missed_operational_slo"
    ISOLATED_RETRYABLE_FAILURE = "isolated_retryable_failure"
    QUALITY_REVIEW_FAILURE = "quality_review_failure"


class IncidentSeverity(StrEnum):
    SEV0 = "sev0"
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"


_SIGNAL_SEVERITY: dict[IncidentSignal, IncidentSeverity] = {
    IncidentSignal.UNAUTHORIZED_FINANCIAL_EFFECT: IncidentSeverity.SEV0,
    IncidentSignal.SECRET_EXPOSURE: IncidentSeverity.SEV0,
    IncidentSignal.AUDIT_INTEGRITY_FAILURE: IncidentSeverity.SEV0,
    IncidentSignal.POLICY_BYPASS: IncidentSeverity.SEV0,
    IncidentSignal.UNCONTAINED_PUBLIC_IMPACT: IncidentSeverity.SEV0,
    IncidentSignal.AMBIGUOUS_EXTERNAL_EFFECT: IncidentSeverity.SEV1,
    IncidentSignal.REPEATED_CONNECTOR_FAILURE: IncidentSeverity.SEV1,
    IncidentSignal.MATERIAL_DATA_RISK: IncidentSeverity.SEV1,
    IncidentSignal.BACKUP_RESTORE_FAILURE: IncidentSeverity.SEV1,
    IncidentSignal.DEAD_LETTER: IncidentSeverity.SEV2,
    IncidentSignal.REPEATED_WORKER_FAILURE: IncidentSeverity.SEV2,
    IncidentSignal.MISSED_OPERATIONAL_SLO: IncidentSeverity.SEV2,
    IncidentSignal.ISOLATED_RETRYABLE_FAILURE: IncidentSeverity.SEV3,
    IncidentSignal.QUALITY_REVIEW_FAILURE: IncidentSeverity.SEV3,
}

_SEVERITY_RANK = {
    IncidentSeverity.SEV0: 0,
    IncidentSeverity.SEV1: 1,
    IncidentSeverity.SEV2: 2,
    IncidentSeverity.SEV3: 3,
}


class ContainmentAction(StrEnum):
    ACTIVATE_GLOBAL_PAUSE = "activate_global_pause"
    STOP_EXTERNAL_EFFECTS = "stop_external_effects"
    OPEN_SCOPE_CIRCUIT = "open_scope_circuit"
    QUARANTINE_TASK = "quarantine_task"
    REVOKE_ACTIVE_LEASES = "revoke_active_leases"
    PRESERVE_EVIDENCE = "preserve_evidence"
    RECONCILE_EXTERNAL_EFFECT = "reconcile_external_effect"
    OPEN_INCIDENT = "open_incident"
    NOTIFY_CEO = "notify_ceo"
    ROUTE_DEPARTMENT = "route_department"
    RETRY_BOUNDED = "retry_bounded"
    RECORD_DIAGNOSTIC = "record_diagnostic"


@dataclass(frozen=True, slots=True)
class ContainmentPlan:
    severity: IncidentSeverity
    actions: tuple[ContainmentAction, ...]
    stop_scope: str
    notify_ceo: bool


def _normalize_incident_signals(
    signals: Iterable[IncidentSignal | str],
) -> frozenset[IncidentSignal]:
    normalized: set[IncidentSignal] = set()
    for signal in signals:
        try:
            normalized.add(IncidentSignal(signal))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"unknown incident signal: {signal}") from exc
    if not normalized:
        raise ValidationError("at least one incident signal is required")
    return frozenset(normalized)


def classify_incident(signals: Iterable[IncidentSignal | str]) -> IncidentSeverity:
    normalized = _normalize_incident_signals(signals)
    return min((_SIGNAL_SEVERITY[signal] for signal in normalized), key=_SEVERITY_RANK.__getitem__)


def containment_for(signals: Iterable[IncidentSignal | str]) -> ContainmentPlan:
    """Return only safe, reversible containment actions for the worst signal."""

    normalized = _normalize_incident_signals(signals)
    severity = min(
        (_SIGNAL_SEVERITY[signal] for signal in normalized), key=_SEVERITY_RANK.__getitem__
    )
    if severity is IncidentSeverity.SEV0:
        actions = (
            ContainmentAction.ACTIVATE_GLOBAL_PAUSE,
            ContainmentAction.STOP_EXTERNAL_EFFECTS,
            ContainmentAction.REVOKE_ACTIVE_LEASES,
            ContainmentAction.PRESERVE_EVIDENCE,
            ContainmentAction.OPEN_INCIDENT,
            ContainmentAction.NOTIFY_CEO,
        )
        return ContainmentPlan(severity, actions, "global", True)
    if severity is IncidentSeverity.SEV1:
        action_list = [
            ContainmentAction.OPEN_SCOPE_CIRCUIT,
            ContainmentAction.REVOKE_ACTIVE_LEASES,
            ContainmentAction.PRESERVE_EVIDENCE,
        ]
        if IncidentSignal.AMBIGUOUS_EXTERNAL_EFFECT in normalized:
            action_list.append(ContainmentAction.RECONCILE_EXTERNAL_EFFECT)
        action_list.extend(
            [ContainmentAction.OPEN_INCIDENT, ContainmentAction.NOTIFY_CEO]
        )
        return ContainmentPlan(severity, tuple(action_list), "affected_scope", True)
    if severity is IncidentSeverity.SEV2:
        return ContainmentPlan(
            severity,
            (
                ContainmentAction.QUARANTINE_TASK,
                ContainmentAction.REVOKE_ACTIVE_LEASES,
                ContainmentAction.PRESERVE_EVIDENCE,
                ContainmentAction.OPEN_INCIDENT,
                ContainmentAction.ROUTE_DEPARTMENT,
            ),
            "task",
            False,
        )
    return ContainmentPlan(
        severity,
        (
            ContainmentAction.RECORD_DIAGNOSTIC,
            ContainmentAction.RETRY_BOUNDED,
            ContainmentAction.ROUTE_DEPARTMENT,
        ),
        "none",
        False,
    )


def _non_negative_integer(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{name} must be a non-negative integer")
    if value > 9_223_372_036_854_775_807:
        raise ValidationError(f"{name} exceeds the durable integer range")
    return value


def _non_negative_number(name: str, value: float) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a finite non-negative number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a finite non-negative number") from exc
    if not math.isfinite(result) or result < 0:
        raise ValidationError(f"{name} must be a finite non-negative number")
    return result


@dataclass(frozen=True, slots=True)
class CycleLimits:
    max_task_starts: int = 20
    max_task_creations: int = 50
    max_external_effects: int = 0
    max_reserved_cost_cents: int = 0
    max_wall_seconds: float = 900.0
    max_task_depth: int = 4
    max_children_per_task: int = 5

    def __post_init__(self) -> None:
        for name in (
            "max_task_starts",
            "max_task_creations",
            "max_external_effects",
            "max_reserved_cost_cents",
            "max_task_depth",
            "max_children_per_task",
        ):
            _non_negative_integer(name, getattr(self, name))
        normalized_wall_seconds = _non_negative_number(
            "max_wall_seconds", self.max_wall_seconds
        )
        if normalized_wall_seconds <= 0:
            raise ValidationError("max_wall_seconds must be greater than zero")
        object.__setattr__(self, "max_wall_seconds", normalized_wall_seconds)


@dataclass(frozen=True, slots=True)
class CycleUsage:
    task_starts: int = 0
    task_creations: int = 0
    external_effects: int = 0
    reserved_cost_cents: int = 0
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "task_starts",
            "task_creations",
            "external_effects",
            "reserved_cost_cents",
        ):
            _non_negative_integer(name, getattr(self, name))
        object.__setattr__(
            self,
            "elapsed_seconds",
            _non_negative_number("elapsed_seconds", self.elapsed_seconds),
        )


@dataclass(frozen=True, slots=True)
class CycleRequest:
    task_starts: int = 1
    task_creations: int = 0
    external_effects: int = 0
    reserved_cost_cents: int = 0
    estimated_wall_seconds: float = 0.0
    task_depth: int = 0
    children_for_parent: int = 0

    def __post_init__(self) -> None:
        for name in (
            "task_starts",
            "task_creations",
            "external_effects",
            "reserved_cost_cents",
            "task_depth",
            "children_for_parent",
        ):
            _non_negative_integer(name, getattr(self, name))
        object.__setattr__(
            self,
            "estimated_wall_seconds",
            _non_negative_number(
                "estimated_wall_seconds", self.estimated_wall_seconds
            ),
        )


class CycleLimitName(StrEnum):
    TASK_STARTS = "task_starts"
    TASK_CREATIONS = "task_creations"
    EXTERNAL_EFFECTS = "external_effects"
    RESERVED_COST = "reserved_cost"
    WALL_TIME = "wall_time"
    TASK_DEPTH = "task_depth"
    CHILD_FANOUT = "child_fanout"


@dataclass(frozen=True, slots=True)
class CycleAdmission:
    allowed: bool
    exhausted: tuple[CycleLimitName, ...]
    reason: str


def evaluate_cycle_admission(
    limits: CycleLimits, usage: CycleUsage, request: CycleRequest
) -> CycleAdmission:
    """Fail closed when current or requested work reaches any cycle bound."""

    if not isinstance(limits, CycleLimits):
        raise ValidationError("limits must be CycleLimits")
    if not isinstance(usage, CycleUsage):
        raise ValidationError("usage must be CycleUsage")
    if not isinstance(request, CycleRequest):
        raise ValidationError("request must be CycleRequest")

    exhausted: list[CycleLimitName] = []
    if usage.task_starts + request.task_starts > limits.max_task_starts:
        exhausted.append(CycleLimitName.TASK_STARTS)
    if usage.task_creations + request.task_creations > limits.max_task_creations:
        exhausted.append(CycleLimitName.TASK_CREATIONS)
    if usage.external_effects + request.external_effects > limits.max_external_effects:
        exhausted.append(CycleLimitName.EXTERNAL_EFFECTS)
    if usage.reserved_cost_cents + request.reserved_cost_cents > limits.max_reserved_cost_cents:
        exhausted.append(CycleLimitName.RESERVED_COST)
    proposed_elapsed = usage.elapsed_seconds + request.estimated_wall_seconds
    requests_work = any(
        (
            request.task_starts,
            request.task_creations,
            request.external_effects,
            request.reserved_cost_cents,
            request.estimated_wall_seconds,
        )
    )
    if proposed_elapsed > limits.max_wall_seconds or (
        requests_work and usage.elapsed_seconds >= limits.max_wall_seconds
    ):
        exhausted.append(CycleLimitName.WALL_TIME)
    if request.task_depth > limits.max_task_depth:
        exhausted.append(CycleLimitName.TASK_DEPTH)
    if request.children_for_parent > limits.max_children_per_task:
        exhausted.append(CycleLimitName.CHILD_FANOUT)

    if exhausted:
        return CycleAdmission(
            False,
            tuple(exhausted),
            "cycle limit exceeded: " + ", ".join(item.value for item in exhausted),
        )
    return CycleAdmission(True, (), "the requested work is within every cycle limit")


def apply_cycle_request(
    limits: CycleLimits, usage: CycleUsage, request: CycleRequest
) -> CycleUsage:
    """Return updated usage or raise without partially consuming a cycle."""

    decision = evaluate_cycle_admission(limits, usage, request)
    if not decision.allowed:
        raise ConflictError(decision.reason)
    return CycleUsage(
        task_starts=usage.task_starts + request.task_starts,
        task_creations=usage.task_creations + request.task_creations,
        external_effects=usage.external_effects + request.external_effects,
        reserved_cost_cents=usage.reserved_cost_cents + request.reserved_cost_cents,
        elapsed_seconds=usage.elapsed_seconds + request.estimated_wall_seconds,
    )


__all__: Sequence[str] = (
    "AcceptanceDecision",
    "AcceptanceStatus",
    "ContainmentAction",
    "ContainmentPlan",
    "CycleAdmission",
    "CycleLimitName",
    "CycleLimits",
    "CycleRequest",
    "CycleUsage",
    "DependencyDecision",
    "DependencyDisposition",
    "FailureKind",
    "FailureReport",
    "IncidentSeverity",
    "IncidentSignal",
    "LeaseProof",
    "LeaseRecord",
    "LeaseValidation",
    "LeaseValidationReason",
    "QueueCandidate",
    "ReviewRecord",
    "ReviewVerdict",
    "RetryAction",
    "RetryDecision",
    "TASK_TRANSITIONS",
    "TERMINAL_TASK_STATES",
    "TaskDependency",
    "TaskState",
    "TaskTransitionDecision",
    "apply_cycle_request",
    "classify_incident",
    "containment_for",
    "decide_retry",
    "evaluate_cycle_admission",
    "evaluate_dependencies",
    "evaluate_task_transition",
    "evaluate_work_acceptance",
    "next_lease_epoch",
    "order_ready_tasks",
    "priority_key",
    "require_task_transition",
    "retry_backoff_seconds",
    "validate_lease",
)
