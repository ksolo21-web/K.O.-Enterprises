"""Tests for deterministic autonomous-runtime rules."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from company_os.errors import ConflictError, ValidationError
from company_os.runtime import (
    AcceptanceStatus,
    ContainmentAction,
    CycleLimitName,
    CycleLimits,
    CycleRequest,
    CycleUsage,
    DependencyDisposition,
    FailureKind,
    FailureReport,
    IncidentSeverity,
    IncidentSignal,
    LeaseProof,
    LeaseRecord,
    LeaseValidationReason,
    QueueCandidate,
    ReviewRecord,
    ReviewVerdict,
    RetryAction,
    TaskDependency,
    TaskState,
    apply_cycle_request,
    classify_incident,
    containment_for,
    decide_retry,
    evaluate_cycle_admission,
    evaluate_dependencies,
    evaluate_task_transition,
    evaluate_work_acceptance,
    next_lease_epoch,
    order_ready_tasks,
    require_task_transition,
    retry_backoff_seconds,
    validate_lease,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 24, 16, 0, tzinfo=UTC)


class TaskLifecycleTests(unittest.TestCase):
    def test_lifecycle_allows_recovery_review_and_terminal_paths(self) -> None:
        legal_paths = (
            (TaskState.PROPOSED, TaskState.WAITING_DEPENDENCY),
            (TaskState.WAITING_DEPENDENCY, TaskState.READY),
            (TaskState.READY, TaskState.LEASED),
            (TaskState.LEASED, TaskState.READY),
            (TaskState.LEASED, TaskState.RUNNING),
            (TaskState.RUNNING, TaskState.REVIEW),
            (TaskState.REVIEW, TaskState.SUCCEEDED),
            (TaskState.RUNNING, TaskState.RETRY_WAIT),
            (TaskState.RETRY_WAIT, TaskState.READY),
        )
        for current, target in legal_paths:
            with self.subTest(current=current, target=target):
                decision = evaluate_task_transition(current, target)
                self.assertTrue(decision.allowed)
                self.assertTrue(decision.changed)

    def test_replayed_transition_is_an_idempotent_noop(self) -> None:
        decision = evaluate_task_transition("running", TaskState.RUNNING)
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.changed)

    def test_illegal_shortcut_and_terminal_revival_fail_closed(self) -> None:
        for current, target in (
            (TaskState.READY, TaskState.SUCCEEDED),
            (TaskState.RUNNING, TaskState.READY),
            (TaskState.SUCCEEDED, TaskState.READY),
            (TaskState.CANCELLED, TaskState.PROPOSED),
        ):
            with self.subTest(current=current, target=target):
                decision = evaluate_task_transition(current, target)
                self.assertFalse(decision.allowed)
                with self.assertRaises(ConflictError):
                    require_task_transition(current, target)

    def test_unknown_state_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            evaluate_task_transition("invented", "ready")


class DependencyTests(unittest.TestCase):
    def test_no_dependencies_and_all_successful_dependencies_are_ready(self) -> None:
        self.assertTrue(evaluate_dependencies([]).ready)
        decision = evaluate_dependencies(
            [
                TaskDependency("research", TaskState.SUCCEEDED),
                TaskDependency("security", "succeeded"),
            ]
        )
        self.assertEqual(DependencyDisposition.READY, decision.disposition)

    def test_nonterminal_dependencies_wait_in_stable_order(self) -> None:
        decision = evaluate_dependencies(
            [
                TaskDependency("z-task", TaskState.RUNNING),
                TaskDependency("a-task", TaskState.REVIEW),
                TaskDependency("done", TaskState.SUCCEEDED),
            ]
        )
        self.assertEqual(DependencyDisposition.WAITING, decision.disposition)
        self.assertEqual(("a-task", "z-task"), decision.waiting_task_ids)

    def test_any_required_terminal_failure_blocks_but_optional_failure_does_not(self) -> None:
        blocked = evaluate_dependencies(
            [
                TaskDependency("optional", TaskState.DEAD_LETTER, required=False),
                TaskDependency("cancelled", TaskState.CANCELLED),
                TaskDependency("failed", TaskState.FAILED),
            ]
        )
        self.assertEqual(DependencyDisposition.BLOCKED, blocked.disposition)
        self.assertEqual(("cancelled", "failed"), blocked.blocking_task_ids)
        self.assertTrue(
            evaluate_dependencies(
                [TaskDependency("optional", TaskState.FAILED, required=False)]
            ).ready
        )

    def test_duplicate_required_dependency_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate required"):
            evaluate_dependencies(
                [
                    TaskDependency("same", TaskState.RUNNING),
                    TaskDependency("same", TaskState.SUCCEEDED),
                ]
            )


class PriorityOrderingTests(unittest.TestCase):
    @staticmethod
    def candidate(
        task_id: str,
        *,
        priority: int = 0,
        available_offset: int = -10,
        created_offset: int = -100,
        deadline_offset: int | None = None,
        state: TaskState = TaskState.READY,
    ) -> QueueCandidate:
        return QueueCandidate(
            task_id=task_id,
            state=state,
            priority=priority,
            available_at=NOW + timedelta(seconds=available_offset),
            created_at=NOW + timedelta(seconds=created_offset),
            deadline_at=(
                NOW + timedelta(seconds=deadline_offset)
                if deadline_offset is not None
                else None
            ),
        )

    def test_order_is_priority_then_deadline_then_availability_age_and_id(self) -> None:
        candidates = [
            self.candidate("low", priority=1, deadline_offset=-20),
            self.candidate("no-deadline", priority=5),
            self.candidate("later-deadline", priority=5, deadline_offset=60),
            self.candidate("earlier-deadline", priority=5, deadline_offset=30),
            self.candidate("top", priority=9),
        ]
        ordered = order_ready_tasks(reversed(candidates), now=NOW)
        self.assertEqual(
            ("top", "earlier-deadline", "later-deadline", "no-deadline", "low"),
            tuple(item.task_id for item in ordered),
        )

    def test_future_and_nonready_tasks_are_not_returned(self) -> None:
        ordered = order_ready_tasks(
            [
                self.candidate("ready"),
                self.candidate("future", available_offset=1),
                self.candidate("leased", state=TaskState.LEASED),
            ],
            now=NOW,
        )
        self.assertEqual(("ready",), tuple(item.task_id for item in ordered))

    def test_ties_use_task_id_and_duplicate_candidates_fail_closed(self) -> None:
        first = self.candidate("a")
        second = self.candidate("b")
        self.assertEqual(
            ("a", "b"),
            tuple(item.task_id for item in order_ready_tasks([second, first], now=NOW)),
        )
        with self.assertRaisesRegex(ValidationError, "duplicate queue candidate"):
            order_ready_tasks([first, first], now=NOW)

    def test_naive_timestamps_and_boolean_priorities_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "timezone-aware"):
            self.candidate("bad").__class__(
                task_id="bad",
                state=TaskState.READY,
                priority=1,
                available_at=datetime(2026, 1, 1),
                created_at=NOW,
            )
        with self.assertRaisesRegex(ValidationError, "priority"):
            QueueCandidate("bad", TaskState.READY, True, NOW, NOW)  # type: ignore[arg-type]


class LeaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lease = LeaseRecord(
            task_id="task-1",
            owner_id="worker-a",
            token="secret-token",
            epoch=4,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=5),
        )

    def test_exact_unexpired_fenced_lease_is_valid(self) -> None:
        result = validate_lease(
            self.lease,
            LeaseProof("WORKER-A", "secret-token", 4),
            now=NOW + timedelta(minutes=1),
        )
        self.assertTrue(result.valid)
        self.assertEqual(LeaseValidationReason.VALID, result.reason)

    def test_owner_token_epoch_and_expiry_each_fail_closed(self) -> None:
        cases = (
            (LeaseProof("worker-b", "secret-token", 4), NOW, LeaseValidationReason.OWNER_MISMATCH),
            (LeaseProof("worker-a", "wrong-token", 4), NOW, LeaseValidationReason.TOKEN_MISMATCH),
            (LeaseProof("worker-a", "secret-token", 3), NOW, LeaseValidationReason.EPOCH_MISMATCH),
            (
                LeaseProof("worker-a", "secret-token", 4),
                self.lease.expires_at,
                LeaseValidationReason.EXPIRED,
            ),
        )
        for proof, now, reason in cases:
            with self.subTest(reason=reason):
                result = validate_lease(self.lease, proof, now=now)
                self.assertFalse(result.valid)
                self.assertEqual(reason, result.reason)

    def test_lease_window_and_epochs_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValidationError, "later"):
            LeaseRecord("task", "worker", "token", 1, NOW, NOW)
        self.assertEqual(1, next_lease_epoch(0))
        with self.assertRaises(ValidationError):
            next_lease_epoch(True)  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            next_lease_epoch(9_223_372_036_854_775_807)


class RetryTests(unittest.TestCase):
    def test_backoff_is_deterministic_capped_and_keyed(self) -> None:
        first = retry_backoff_seconds(3, jitter_key="task-1")
        self.assertEqual(first, retry_backoff_seconds(3, jitter_key="task-1"))
        self.assertNotEqual(first, retry_backoff_seconds(3, jitter_key="task-2"))
        self.assertLessEqual(
            retry_backoff_seconds(10_000, cap_seconds=100, jitter_key="task"), 100
        )
        self.assertEqual(
            40,
            retry_backoff_seconds(
                3, base_seconds=10, cap_seconds=100, jitter_ratio=0, jitter_key="task"
            ),
        )

    def test_retryable_failure_obeys_budget_and_retry_after_minimum(self) -> None:
        retry = decide_retry(
            FailureReport(FailureKind.RATE_LIMITED, retry_after_seconds=5000),
            attempts_completed=1,
            max_attempts=3,
            jitter_key="task",
        )
        self.assertEqual(RetryAction.RETRY, retry.action)
        self.assertEqual(5000, retry.delay_seconds)
        exhausted = decide_retry(
            FailureReport(FailureKind.TRANSIENT),
            attempts_completed=3,
            max_attempts=3,
        )
        self.assertEqual(RetryAction.DEAD_LETTER, exhausted.action)

    def test_unknown_external_outcome_always_reconciles_before_retry(self) -> None:
        decision = decide_retry(
            FailureReport(FailureKind.TIMEOUT, external_outcome_unknown=True),
            attempts_completed=99,
            max_attempts=1,
        )
        self.assertEqual(RetryAction.RECONCILE, decision.action)
        self.assertIsNone(decision.delay_seconds)

    def test_policy_and_access_failures_block_without_burning_retries(self) -> None:
        for kind in (
            FailureKind.POLICY_DENIED,
            FailureKind.AUTHENTICATION,
            FailureKind.PERMISSION,
        ):
            with self.subTest(kind=kind):
                self.assertEqual(
                    RetryAction.BLOCKED,
                    decide_retry(
                        FailureReport(kind), attempts_completed=1, max_attempts=5
                    ).action,
                )

    def test_invalid_invariant_unknown_and_cancelled_are_never_retried(self) -> None:
        for kind in (
            FailureKind.INVALID_INPUT,
            FailureKind.INVARIANT,
            FailureKind.UNKNOWN,
        ):
            with self.subTest(kind=kind):
                self.assertEqual(
                    RetryAction.DEAD_LETTER,
                    decide_retry(
                        FailureReport(kind), attempts_completed=1, max_attempts=5
                    ).action,
                )
        self.assertEqual(
            RetryAction.CANCEL,
            decide_retry(
                FailureReport(FailureKind.CANCELLED),
                attempts_completed=1,
                max_attempts=5,
            ).action,
        )

    def test_retry_inputs_reject_booleans_nan_and_invalid_ranges(self) -> None:
        for call in (
            lambda: retry_backoff_seconds(True),  # type: ignore[arg-type]
            lambda: retry_backoff_seconds(1, base_seconds=31, cap_seconds=30),
            lambda: retry_backoff_seconds(1, jitter_ratio=float("nan")),
            lambda: decide_retry(
                FailureReport(FailureKind.TRANSIENT),
                attempts_completed=0,
                max_attempts=1,
            ),
            lambda: FailureReport(FailureKind.TRANSIENT, retry_after_seconds=True),  # type: ignore[arg-type]
        ):
            with self.subTest(call=call):
                with self.assertRaises(ValidationError):
                    call()


class AcceptanceTests(unittest.TestCase):
    def test_required_independent_roles_must_all_approve(self) -> None:
        pending = evaluate_work_acceptance(
            producer_id="builder",
            reviews=[ReviewRecord("security-1", "security", "approved")],
            required_roles=["security", "compliance"],
        )
        self.assertEqual(AcceptanceStatus.PENDING, pending.status)
        self.assertEqual(("compliance",), pending.missing_roles)

        accepted = evaluate_work_acceptance(
            producer_id="builder",
            reviews=[
                ReviewRecord("security-1", "security", ReviewVerdict.APPROVED),
                ReviewRecord("legal-1", "compliance", ReviewVerdict.APPROVED),
            ],
            required_roles=["SECURITY", "compliance"],
        )
        self.assertTrue(accepted.accepted)
        self.assertEqual(AcceptanceStatus.ACCEPTED, accepted.status)

    def test_producer_and_prohibited_actor_cannot_accept_work(self) -> None:
        for reviewer in ("BUILDER", "commander"):
            with self.subTest(reviewer=reviewer):
                decision = evaluate_work_acceptance(
                    producer_id="builder",
                    prohibited_reviewer_ids=["Commander"],
                    reviews=[ReviewRecord(reviewer, "qa", "approved")],
                )
                self.assertFalse(decision.accepted)
                self.assertEqual(AcceptanceStatus.INVALID, decision.status)

    def test_rejection_overrides_approval_and_changes_block_acceptance(self) -> None:
        rejected = evaluate_work_acceptance(
            producer_id="builder",
            reviews=[
                ReviewRecord("qa", "qa", "approved"),
                ReviewRecord("security", "security", "rejected"),
            ],
        )
        self.assertEqual(AcceptanceStatus.REJECTED, rejected.status)
        changes = evaluate_work_acceptance(
            producer_id="builder",
            reviews=[ReviewRecord("qa", "qa", "changes_requested")],
        )
        self.assertEqual(AcceptanceStatus.CHANGES_REQUIRED, changes.status)

    def test_duplicate_reviewer_and_missing_independent_review_fail_closed(self) -> None:
        duplicate = evaluate_work_acceptance(
            producer_id="builder",
            reviews=[
                ReviewRecord("QA", "qa", "approved"),
                ReviewRecord("qa", "security", "approved"),
            ],
        )
        self.assertEqual(AcceptanceStatus.INVALID, duplicate.status)
        no_review = evaluate_work_acceptance(producer_id="builder", reviews=[])
        self.assertEqual(AcceptanceStatus.PENDING, no_review.status)

    def test_internal_work_can_explicitly_disable_independent_review(self) -> None:
        decision = evaluate_work_acceptance(
            producer_id="builder", reviews=[], independent_review_required=False
        )
        self.assertTrue(decision.accepted)


class IncidentTests(unittest.TestCase):
    def test_worst_signal_determines_severity(self) -> None:
        self.assertEqual(
            IncidentSeverity.SEV0,
            classify_incident(
                [IncidentSignal.QUALITY_REVIEW_FAILURE, IncidentSignal.POLICY_BYPASS]
            ),
        )
        self.assertEqual(
            IncidentSeverity.SEV2,
            classify_incident(
                [IncidentSignal.MISSED_OPERATIONAL_SLO, IncidentSignal.QUALITY_REVIEW_FAILURE]
            ),
        )

    def test_sev0_contains_globally_preserves_evidence_and_notifies_ceo(self) -> None:
        plan = containment_for([IncidentSignal.AUDIT_INTEGRITY_FAILURE])
        self.assertEqual(IncidentSeverity.SEV0, plan.severity)
        self.assertEqual("global", plan.stop_scope)
        self.assertTrue(plan.notify_ceo)
        self.assertIn(ContainmentAction.ACTIVATE_GLOBAL_PAUSE, plan.actions)
        self.assertIn(ContainmentAction.PRESERVE_EVIDENCE, plan.actions)

    def test_ambiguous_effect_opens_scope_and_requires_reconciliation(self) -> None:
        plan = containment_for([IncidentSignal.AMBIGUOUS_EXTERNAL_EFFECT])
        self.assertEqual(IncidentSeverity.SEV1, plan.severity)
        self.assertEqual("affected_scope", plan.stop_scope)
        self.assertIn(ContainmentAction.OPEN_SCOPE_CIRCUIT, plan.actions)
        self.assertIn(ContainmentAction.RECONCILE_EXTERNAL_EFFECT, plan.actions)

    def test_operational_incidents_remain_in_department(self) -> None:
        sev2 = containment_for([IncidentSignal.DEAD_LETTER])
        self.assertFalse(sev2.notify_ceo)
        self.assertIn(ContainmentAction.QUARANTINE_TASK, sev2.actions)
        sev3 = containment_for([IncidentSignal.ISOLATED_RETRYABLE_FAILURE])
        self.assertEqual(IncidentSeverity.SEV3, sev3.severity)
        self.assertFalse(sev3.notify_ceo)
        self.assertIn(ContainmentAction.RETRY_BOUNDED, sev3.actions)

    def test_empty_or_unknown_incident_signal_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            classify_incident([])
        with self.assertRaises(ValidationError):
            containment_for(["invented"])


class CycleLimitTests(unittest.TestCase):
    def test_default_cycle_allows_internal_zero_cost_work_and_blocks_external(self) -> None:
        limits = CycleLimits()
        internal = evaluate_cycle_admission(limits, CycleUsage(), CycleRequest())
        self.assertTrue(internal.allowed)
        external = evaluate_cycle_admission(
            limits,
            CycleUsage(),
            CycleRequest(external_effects=1),
        )
        self.assertFalse(external.allowed)
        self.assertEqual((CycleLimitName.EXTERNAL_EFFECTS,), external.exhausted)

    def test_exact_limits_are_allowed_but_the_next_unit_is_denied(self) -> None:
        limits = CycleLimits(
            max_task_starts=2,
            max_task_creations=2,
            max_external_effects=1,
            max_reserved_cost_cents=100,
            max_wall_seconds=10,
            max_task_depth=2,
            max_children_per_task=2,
        )
        at_limit = apply_cycle_request(
            limits,
            CycleUsage(task_starts=1),
            CycleRequest(
                task_starts=1,
                task_creations=2,
                external_effects=1,
                reserved_cost_cents=100,
                estimated_wall_seconds=10,
                task_depth=2,
                children_for_parent=2,
            ),
        )
        self.assertEqual(2, at_limit.task_starts)
        denied = evaluate_cycle_admission(limits, at_limit, CycleRequest())
        self.assertFalse(denied.allowed)
        self.assertIn(CycleLimitName.TASK_STARTS, denied.exhausted)
        self.assertIn(CycleLimitName.WALL_TIME, denied.exhausted)

    def test_all_exceeded_limits_are_reported_in_stable_order(self) -> None:
        limits = CycleLimits(
            max_task_starts=0,
            max_task_creations=0,
            max_external_effects=0,
            max_reserved_cost_cents=0,
            max_wall_seconds=1,
            max_task_depth=0,
            max_children_per_task=0,
        )
        decision = evaluate_cycle_admission(
            limits,
            CycleUsage(elapsed_seconds=1),
            CycleRequest(
                task_starts=1,
                task_creations=1,
                external_effects=1,
                reserved_cost_cents=1,
                estimated_wall_seconds=1,
                task_depth=1,
                children_for_parent=1,
            ),
        )
        self.assertEqual(
            (
                CycleLimitName.TASK_STARTS,
                CycleLimitName.TASK_CREATIONS,
                CycleLimitName.EXTERNAL_EFFECTS,
                CycleLimitName.RESERVED_COST,
                CycleLimitName.WALL_TIME,
                CycleLimitName.TASK_DEPTH,
                CycleLimitName.CHILD_FANOUT,
            ),
            decision.exhausted,
        )

    def test_apply_is_atomic_on_denial(self) -> None:
        usage = CycleUsage(task_starts=1)
        with self.assertRaises(ConflictError):
            apply_cycle_request(
                CycleLimits(max_task_starts=1), usage, CycleRequest(task_starts=1)
            )
        self.assertEqual(1, usage.task_starts)

    def test_limits_reject_boolean_negative_nan_and_zero_wall_budget(self) -> None:
        factories = (
            lambda: CycleLimits(max_task_starts=True),  # type: ignore[arg-type]
            lambda: CycleLimits(max_task_depth=-1),
            lambda: CycleLimits(max_wall_seconds=float("nan")),
            lambda: CycleLimits(max_wall_seconds=0),
            lambda: CycleUsage(elapsed_seconds=float("inf")),
            lambda: CycleRequest(reserved_cost_cents=True),  # type: ignore[arg-type]
        )
        for factory in factories:
            with self.subTest(factory=factory):
                with self.assertRaises(ValidationError):
                    factory()


if __name__ == "__main__":
    unittest.main()
