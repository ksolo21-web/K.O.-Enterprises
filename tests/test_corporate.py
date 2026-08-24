"""Executable corporate hierarchy and durable work integration tests."""

from __future__ import annotations

import sqlite3
import math
import unittest
from datetime import datetime, timedelta, timezone

from company_os.corporate import CorporateOperations, DecisionClass
from company_os.errors import ConflictError
from company_os.storage import CompanyStore


class CorporateOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = CompanyStore(":memory:")
        self.addCleanup(self.store.close)
        self.operations = CorporateOperations(self.store)
        self.bootstrap = self.operations.bootstrap_organization(actor="test-bootstrap")
        self.objective = self.operations.create_objective(
            objective_key="company.test-suite",
            title="Exercise the corporate controls",
            owner_role_key="product_technology_chief",
            commanded_by_worker="company_president",
        )

    def _work(self, **overrides: object) -> dict[str, object]:
        values: dict[str, object] = {
            "work_key": "test.work",
            "commanded_by_worker": "company_president",
            "assigned_role_key": "software_engineer",
            "reviewer_role_key": "product_technology_chief",
            "task_type": "software_change",
            "title": "Implement one bounded change",
            "description": "Implement the accepted work order only.",
            "acceptance_criteria": "Tests pass and an independent reviewer accepts the result.",
            "objective_id": self.objective["id"],
        }
        values.update(overrides)
        return self.operations.create_work(**values)  # type: ignore[arg-type]

    def test_blueprint_bootstrap_is_complete_idempotent_and_audited(self) -> None:
        self.assertEqual(
            {"departments": 12, "roles": 28, "workers": 28}, self.bootstrap
        )
        second = self.operations.bootstrap_organization(actor="test-bootstrap")
        self.assertEqual(self.bootstrap, second)
        snapshot = self.operations.organization_snapshot()
        self.assertEqual(12, len(snapshot["departments"]))
        self.assertEqual(28, len(snapshot["roles"]))
        self.assertEqual(28, len(snapshot["workers"]))
        self.assertTrue(
            any(
                event["event_type"] == "organization.bootstrapped"
                for event in self.store.list_audit_events()
            )
        )

    def test_bootstrap_does_not_reactivate_a_suspended_worker(self) -> None:
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE workers SET status = 'disabled' WHERE worker_key = 'software_engineer'"
            )
        self.operations.bootstrap_organization(actor="test-bootstrap")
        worker = next(
            row
            for row in self.operations.organization_snapshot()["workers"]
            if row["worker_key"] == "software_engineer"
        )
        self.assertEqual("disabled", worker["status"])

    def test_persisted_chain_allows_downward_but_denies_lateral_commands(self) -> None:
        self.assertTrue(
            self.operations.command_authorized("company_president", "software_engineer")
        )
        self.assertTrue(
            self.operations.command_authorized(
                "product_technology_chief", "software_engineer"
            )
        )
        self.assertFalse(
            self.operations.command_authorized(
                "opportunity_intelligence_lead", "software_engineer"
            )
        )
        self.assertFalse(
            self.operations.command_authorized("software_engineer", "software_engineer")
        )
        with self.assertRaises(ConflictError):
            self._work(commanded_by_worker="software_engineer")
        with self.assertRaises(ConflictError):
            self.operations.create_objective(
                objective_key="invalid.lateral",
                title="Invalid lateral objective",
                owner_role_key="software_engineer",
                commanded_by_worker="opportunity_intelligence_lead",
            )

    def test_objective_is_commanded_and_duplicate_key_fails(self) -> None:
        objective = self.operations.create_objective(
            objective_key="company.test-objective",
            title="Test the corporate command path",
            owner_role_key="product_technology_chief",
            commanded_by_worker="company_president",
            priority=80,
        )
        self.assertEqual("product-technology", objective["department_slug"])
        with self.assertRaises(ConflictError):
            self.operations.create_objective(
                objective_key="company.test-objective",
                title="Duplicate",
                owner_role_key="product_technology_chief",
                commanded_by_worker="company_president",
            )

    def test_objective_key_results_require_evidence_before_closure(self) -> None:
        key_result = self.operations.create_key_result(
            self.objective["id"],
            result_key="accepted-work",
            description="Produce five independently accepted substantive outcomes.",
            metric_name="accepted_substantive_work",
            baseline=0,
            target=5,
            unit="outcomes",
            actor_worker="product_technology_chief",
        )
        with self.assertRaises(ConflictError):
            self.operations.set_objective_status(
                self.objective["id"],
                status="achieved",
                rationale="Target not reached.",
                actor_worker="product_technology_chief",
            )
        achieved = self.operations.update_key_result(
            key_result["id"],
            current_value=5,
            evidence_reference="test:five-independent-acceptances",
            actor_worker="product_technology_chief",
        )
        self.assertEqual("achieved", achieved["status"])
        objective = self.operations.set_objective_status(
            self.objective["id"],
            status="achieved",
            rationale="Every evidence-backed key result reached its target.",
            actor_worker="product_technology_chief",
        )
        self.assertEqual("achieved", objective["status"])
        self.assertEqual(
            key_result["id"],
            self.operations.get_objective(self.objective["id"])["key_results"][0]["id"],
        )

        with self.assertRaisesRegex(ConflictError, "terminal objectives"):
            self.operations.set_objective_status(
                self.objective["id"],
                status="active",
                rationale="Terminal objectives must roll to a new version.",
                actor_worker="product_technology_chief",
            )

        with self.assertRaises(ConflictError):
            self.operations.update_key_result(
                key_result["id"],
                current_value=4,
                evidence_reference="test:attempted-terminal-regression",
                actor_worker="product_technology_chief",
            )

    def test_key_results_and_metrics_reject_non_finite_values(self) -> None:
        for invalid in (math.nan, math.inf, -math.inf):
            with self.subTest(create_key_result=invalid):
                with self.assertRaisesRegex(Exception, "finite"):
                    self.operations.create_key_result(
                        self.objective["id"],
                        result_key=f"invalid-{invalid}",
                        description="Reject a non-finite measurement.",
                        metric_name="invalid_measurement",
                        baseline=0,
                        target=invalid,
                        unit="tests",
                        actor_worker="product_technology_chief",
                    )
            with self.subTest(record_metric=invalid):
                with self.assertRaisesRegex(Exception, "finite"):
                    self.operations.record_metric(
                        metric_name="invalid_measurement",
                        metric_type="actual",
                        value=invalid,
                        unit="tests",
                        source_reference="test:invalid",
                        evidence_type="automated_test",
                    )

        key_result = self.operations.create_key_result(
            self.objective["id"],
            result_key="finite-update",
            description="Only accept finite progress.",
            metric_name="finite_progress",
            baseline=0,
            target=1,
            unit="tests",
            actor_worker="product_technology_chief",
        )
        with self.assertRaisesRegex(Exception, "finite"):
            self.operations.update_key_result(
                key_result["id"],
                current_value=math.nan,
                evidence_reference="test:invalid",
                actor_worker="product_technology_chief",
            )

    def test_closing_objective_cancels_queued_work_and_prevents_claim(self) -> None:
        work = self._work(work_key="test.objective-close")
        key_result = self.operations.create_key_result(
            self.objective["id"],
            result_key="closure-gate",
            description="Reach the objective's evidence-backed completion gate.",
            metric_name="closure_gate",
            baseline=0,
            target=1,
            unit="gate",
            actor_worker="product_technology_chief",
        )
        self.operations.update_key_result(
            key_result["id"],
            current_value=1,
            evidence_reference="test:closure-gate",
            actor_worker="product_technology_chief",
        )
        self.operations.set_objective_status(
            self.objective["id"],
            status="achieved",
            rationale="All completion evidence is present.",
            actor_worker="product_technology_chief",
        )
        self.assertEqual("cancelled", self.operations.get_work(work["id"])["status"])
        self.assertIsNone(self.operations.claim_work(worker_key="software_engineer"))

    def test_cancelling_objective_fences_in_flight_work_immediately(self) -> None:
        work = self._work(
            work_key="test.objective-cancel-running",
            assigned_worker_key="software_engineer",
        )
        claimed = self.operations.claim_work(worker_key="software_engineer")
        running = self.operations.start_work(
            work["id"],
            worker_key="software_engineer",
            lease_token=claimed["lease_token"],
            lease_epoch=claimed["lease_epoch"],
        )
        self.operations.set_objective_status(
            self.objective["id"],
            status="cancelled",
            rationale="Owner of the objective issued an immediate internal stop.",
            actor_worker="product_technology_chief",
        )
        cancelled = self.operations.get_work(work["id"])
        self.assertEqual("cancelled", cancelled["status"])
        self.assertGreater(cancelled["lease_epoch"], running["lease_epoch"])
        with self.assertRaises(ConflictError):
            self.operations.submit_work(
                work["id"],
                worker_key="software_engineer",
                lease_token=running["lease_token"],
                lease_epoch=running["lease_epoch"],
                result={"artifact": "must not be accepted after cancellation"},
            )

    def test_prohibited_cash_and_misclassified_external_work_fail_closed(self) -> None:
        audit_before = len(self.store.list_audit_events())
        for overrides in (
            {"decision_class": DecisionClass.PROHIBITED},
            {"estimated_cost_cents": 1},
            {"external_effect": True},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ConflictError):
                    self._work(**overrides)

        self.assertGreater(len(self.store.list_audit_events()), audit_before)
        self.assertEqual(1, self.operations.operations_summary()["open_incidents"])

        gated = self._work(
            work_key="test.owner-reserved",
            decision_class=DecisionClass.OWNER_RESERVED,
            estimated_cost_cents=100,
            external_effect=True,
        )
        self.assertEqual("waiting_policy", gated["status"])

    def test_high_and_critical_risk_work_cannot_be_downgraded(self) -> None:
        for risk_level in ("high", "critical"):
            with self.subTest(risk_level=risk_level):
                with self.assertRaises(ConflictError):
                    self._work(
                        work_key=f"test.risk.{risk_level}",
                        risk_level=risk_level,
                        decision_class=DecisionClass.WORK_EXECUTION,
                    )
        reserved = self._work(
            work_key="test.risk.reserved",
            risk_level="critical",
            decision_class=DecisionClass.OWNER_RESERVED,
        )
        self.assertEqual("waiting_policy", reserved["status"])

        with self.assertRaisesRegex(ConflictError, "Company President"):
            self._work(
                work_key="test.executive-authority-denied",
                commanded_by_worker="product_technology_chief",
                decision_class=DecisionClass.EXECUTIVE_PORTFOLIO,
            )
        executive = self._work(
            work_key="test.executive-authority-president",
            commanded_by_worker="company_president",
            decision_class=DecisionClass.EXECUTIVE_PORTFOLIO,
        )
        self.assertEqual("ready", executive["status"])

    def test_exact_ceo_approval_releases_only_bound_internal_work(self) -> None:
        work = self._work(
            work_key="test.owner-approved-internal",
            decision_class=DecisionClass.OWNER_RESERVED,
            risk_level="high",
            estimated_cost_cents=100,
        )
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        owner_packet = {
            "exact_action": f"authorize_work:{work['work_key']}",
            "why_now": "The bounded internal control task is ready.",
            "source_evidence": "test:owner-approved-work",
            "resource_ceiling": "USD 1.00 maximum",
            "accounts_data_public_surfaces": "No external accounts, data, or public surfaces",
            "control_findings": "Internal-only and held for the exact owner decision.",
            "reversibility": "Work may be cancelled before acceptance.",
            "success_threshold": "Independent reviewer accepts the bounded result.",
            "kill_threshold": "Any scope, cost, or authority mismatch.",
            "monitoring": "Lease, audit, and independent acceptance events.",
            "expiry": expiry.isoformat(),
            "consequence_of_rejection_or_delay": "Work remains safely held.",
        }
        approval = self.store.request_approval(
            action=f"authorize_work:{work['work_key']}",
            rationale="Authorize this exact bounded internal work order.",
            risk="high",
            estimated_cost_cents=100,
            approval_class="ceo_approval_required",
            requested_by="company_president",
            expires_at=expiry.isoformat(),
            decision_packet=owner_packet,
        )
        self.store.decide_approval(
            approval["id"],
            decision="approved",
            decided_by="kaleb_ceo",
            notes="Approved only within the recorded ceiling.",
        )
        authorized = self.operations.authorize_internal_work(
            work["id"], approval_id=approval["id"], actor_worker="company_president"
        )
        self.assertEqual("ready", authorized["status"])
        self.assertEqual(approval["id"], authorized["approval_id"])
        claimed = self.operations.claim_work(worker_key="software_engineer")
        self.assertEqual(work["id"], claimed["id"])
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE approvals SET expires_at = ? WHERE id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    approval["id"],
                ),
            )
        with self.assertRaisesRegex(ConflictError, "no longer active"):
            self.operations.start_work(
                work["id"],
                worker_key="software_engineer",
                lease_token=claimed["lease_token"],
                lease_epoch=claimed["lease_epoch"],
            )
        with self.store._transaction() as connection:
            connection.execute(
                """
                UPDATE work_items
                SET status = 'ready', lease_owner = NULL, lease_token = NULL,
                    lease_expires_at = NULL
                WHERE id = ?
                """,
                (work["id"],),
            )
        self.assertIsNone(
            self.operations.claim_work(worker_key="software_engineer")
        )

    def test_work_idempotency_and_dependencies_are_durable(self) -> None:
        first = self._work(work_key="test.first")
        replay = self._work(work_key="test.first")
        self.assertEqual(first["id"], replay["id"])
        with self.assertRaises(ConflictError):
            self._work(work_key="test.first", title="Different hidden scope")
        dependent = self._work(
            work_key="test.dependent", dependencies=(first["id"],)
        )
        self.assertEqual("waiting_dependency", dependent["status"])
        self.assertEqual(
            [{"depends_on_work_id": first["id"], "failure_policy": "block"}],
            self.operations.get_work(dependent["id"])["dependencies"],
        )

    def test_continue_dependency_releases_after_terminal_upstream_failure(self) -> None:
        upstream = self._work(work_key="test.continue.upstream")
        dependent = self._work(
            work_key="test.continue.dependent", dependencies=(upstream["id"],)
        )
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE work_items SET status = 'failed' WHERE id = ?", (upstream["id"],)
            )
            connection.execute(
                """
                UPDATE work_dependencies SET failure_policy = 'continue'
                WHERE work_id = ? AND depends_on_work_id = ?
                """,
                (dependent["id"], upstream["id"]),
            )
        self.assertEqual(
            1, self.operations.release_ready_work(actor_worker="company_president")
        )
        self.assertEqual("ready", self.operations.get_work(dependent["id"])["status"])

    def test_waiting_cycle_reconciles_after_all_scoped_work_is_terminal(self) -> None:
        cycle = self.operations.create_cycle(
            cycle_key="test-cycle",
            mode="internal",
            triggered_by_worker="company_president",
        )
        work = self._work(
            work_key="test.cycle-work",
            cycle_id=cycle["id"],
            assigned_worker_key="software_engineer",
        )
        self.operations.finish_cycle(
            cycle["id"],
            status="awaiting_workers",
            summary={"dispatched": 1},
            actor_worker="company_president",
        )
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE work_items SET status = 'succeeded' WHERE id = ?", (work["id"],)
            )
        self.assertEqual(
            1, self.operations.reconcile_cycles(actor_worker="company_president")
        )
        with self.store._connection() as connection:
            reconciled = connection.execute(
                "SELECT status, completed_at FROM operating_cycles WHERE id = ?",
                (cycle["id"],),
            ).fetchone()
        self.assertEqual("completed", reconciled["status"])
        self.assertIsNotNone(reconciled["completed_at"])

    def test_lease_fencing_submission_and_independent_acceptance(self) -> None:
        work = self._work(assigned_worker_key="software_engineer")
        claimed = self.operations.claim_work(worker_key="software_engineer")
        self.assertEqual(work["id"], claimed["id"])
        self.assertTrue(claimed["lease_token"].startswith("lease_"))
        with self.assertRaises(ConflictError):
            self.operations.start_work(
                work["id"],
                worker_key="software_engineer",
                lease_token="wrong",
                lease_epoch=claimed["lease_epoch"],
            )
        running = self.operations.start_work(
            work["id"],
            worker_key="software_engineer",
            lease_token=claimed["lease_token"],
            lease_epoch=claimed["lease_epoch"],
        )
        submitted = self.operations.submit_work(
            running["id"],
            worker_key="software_engineer",
            lease_token=running["lease_token"],
            lease_epoch=running["lease_epoch"],
            result={"artifact": "bounded change", "tests": "passed"},
        )
        self.assertEqual("review", submitted["status"])
        with self.assertRaises(ConflictError):
            self.operations.review_work(
                submitted["id"],
                reviewer_worker_key="software_engineer",
                decision="accept",
                notes="self review",
            )
        with self.assertRaisesRegex(ConflictError, "quality score"):
            self.operations.review_work(
                submitted["id"],
                reviewer_worker_key="product_technology_chief",
                decision="accept",
                notes="quality is below the assignment floor",
                quality_score=0.1,
            )
        accepted = self.operations.review_work(
            submitted["id"],
            reviewer_worker_key="product_technology_chief",
            decision="accept",
            notes="acceptance criteria verified",
            quality_score=0.95,
        )
        self.assertEqual("succeeded", accepted["status"])
        self.assertIsNotNone(accepted["accepted_at"])

    def test_rejected_work_retries_and_then_dead_letters(self) -> None:
        work = self._work(assigned_worker_key="software_engineer", max_attempts=1)
        claimed = self.operations.claim_work(worker_key="software_engineer")
        running = self.operations.start_work(
            work["id"],
            worker_key="software_engineer",
            lease_token=claimed["lease_token"],
            lease_epoch=claimed["lease_epoch"],
        )
        submitted = self.operations.submit_work(
            running["id"],
            worker_key="software_engineer",
            lease_token=running["lease_token"],
            lease_epoch=running["lease_epoch"],
            result={"tests": "failed"},
        )
        rejected = self.operations.review_work(
            submitted["id"],
            reviewer_worker_key="product_technology_chief",
            decision="reject",
            notes="acceptance criteria failed",
        )
        self.assertEqual("dead_letter", rejected["status"])

    def test_expired_lease_is_recovered_with_fencing_epoch_preserved(self) -> None:
        work = self._work(assigned_worker_key="software_engineer")
        claimed = self.operations.claim_work(worker_key="software_engineer")
        expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE work_items SET lease_expires_at = ? WHERE id = ?",
                (expired, work["id"]),
            )
        recovered = self.operations.recover_expired_leases(actor_worker="sre_operator")
        self.assertEqual(1, recovered)
        row = self.operations.get_work(work["id"])
        self.assertEqual("retry_wait", row["status"])
        self.assertEqual(claimed["lease_epoch"], row["lease_epoch"])

    def test_only_independent_controls_can_record_control_reviews(self) -> None:
        work = self._work()
        with self.assertRaisesRegex(Exception, "SHA-256 artifact digest"):
            self.operations.record_control_review(
                reviewer_worker_key="internal_auditor",
                control_domain="audit",
                status="passed",
                finding="A pass cannot exist before an artifact.",
                work_id=work["id"],
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            )
        with self.assertRaises(ConflictError):
            self.operations.record_control_review(
                reviewer_worker_key="software_engineer",
                control_domain="quality",
                status="blocked",
                finding="not independent",
                work_id=work["id"],
            )
        review = self.operations.record_control_review(
            reviewer_worker_key="internal_auditor",
            control_domain="audit",
            status="blocked",
            finding="command and evidence paths verified",
            work_id=work["id"],
        )
        self.assertEqual("blocked", review["status"])

    def test_unresolved_control_block_vetoes_manager_acceptance(self) -> None:
        work = self._work(assigned_worker_key="software_engineer")
        claimed = self.operations.claim_work(worker_key="software_engineer")
        running = self.operations.start_work(
            work["id"],
            worker_key="software_engineer",
            lease_token=claimed["lease_token"],
            lease_epoch=claimed["lease_epoch"],
        )
        submitted = self.operations.submit_work(
            running["id"],
            worker_key="software_engineer",
            lease_token=running["lease_token"],
            lease_epoch=running["lease_epoch"],
            result={"artifact": "candidate"},
        )
        self.operations.record_control_review(
            reviewer_worker_key="qa_reliability_lead",
            control_domain="quality",
            status="blocked",
            severity="critical",
            finding="Acceptance evidence is incomplete.",
            work_id=work["id"],
        )
        with self.assertRaises(ConflictError):
            self.operations.review_work(
                submitted["id"],
                reviewer_worker_key="product_technology_chief",
                decision="accept",
                notes="manager approval cannot overrule a control block",
                quality_score=1.0,
            )
        submission_digest = self.operations.get_work(work["id"])["submission_digest"]
        with self.assertRaisesRegex(ConflictError, "does not match"):
            self.operations.record_control_review(
                reviewer_worker_key="qa_reliability_lead",
                control_domain="quality",
                status="passed",
                finding="This digest belongs to a different artifact.",
                work_id=work["id"],
                artifact_digest="0" * 64,
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            )
        old_pass = self.operations.record_control_review(
            reviewer_worker_key="qa_reliability_lead",
            control_domain="quality",
            status="passed",
            finding="An old remediation review was once valid.",
            work_id=work["id"],
            artifact_digest=submission_digest,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE control_reviews SET expires_at = ? WHERE id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    old_pass["id"],
                ),
            )
        with self.assertRaisesRegex(ConflictError, "quality=expired"):
            self.operations.review_work(
                submitted["id"],
                reviewer_worker_key="product_technology_chief",
                decision="accept",
                notes="an expired control pass cannot authorize acceptance",
                quality_score=1.0,
            )
        self.operations.record_control_review(
            reviewer_worker_key="qa_reliability_lead",
            control_domain="quality",
            status="passed",
            finding="Fresh remediation and acceptance evidence verified.",
            work_id=work["id"],
            artifact_digest=submission_digest,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        accepted = self.operations.review_work(
            submitted["id"],
            reviewer_worker_key="product_technology_chief",
            decision="accept",
            notes="fresh independent pass resolves the block",
            quality_score=1.0,
        )
        self.assertEqual("succeeded", accepted["status"])

    def test_escalations_route_upward_and_owner_attention_is_reserved(self) -> None:
        escalation = self.operations.create_escalation(
            raised_by_worker="software_engineer",
            routed_to_role_key="product_technology_chief",
            decision_class=DecisionClass.DEPARTMENT_OPERATION,
            reason_code="scope_conflict",
            title="Clarify bounded technical scope",
            context="Two acceptance clauses conflict.",
            recommendation="Use the safer narrower clause.",
            safe_default="Stop only the conflicting work.",
        )
        self.assertEqual(0, escalation["owner_attention"])
        with self.assertRaises(ConflictError):
            self.operations.create_escalation(
                raised_by_worker="software_engineer",
                routed_to_role_key="owner_ceo",
                decision_class=DecisionClass.DEPARTMENT_OPERATION,
                reason_code="skip_chain",
                title="Invalid direct escalation",
                context="Routine work cannot skip management.",
                recommendation="Route to the department manager.",
                safe_default="Hold the affected work only.",
            )
        owner_packet = {
            "exact_action": "Keep the future connector disabled.",
            "why_now": "A standing authority envelope was proposed.",
            "source_evidence": "test:authority-envelope-review",
            "resource_ceiling": "USD 0 and no connector calls",
            "accounts_data_public_surfaces": "No accounts, data, or public surfaces",
            "control_findings": "Internal audit requires continued containment.",
            "reversibility": "Fully reversible because no activation occurs.",
            "success_threshold": "Connector remains disabled.",
            "kill_threshold": "Any attempted connector invocation.",
            "monitoring": "Audit the pause and connector configuration.",
            "expiry": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
            "consequence_of_rejection_or_delay": "Safe default remains paused.",
        }
        with self.assertRaisesRegex(Exception, "complete owner packet"):
            self.operations.create_escalation(
                raised_by_worker="internal_auditor",
                routed_to_role_key="owner_ceo",
                decision_class=DecisionClass.OWNER_RESERVED,
                reason_code="incomplete_packet",
                title="Incomplete owner decision",
                context="This must fail closed.",
                recommendation="Remain paused.",
                safe_default="Remain paused.",
            )
        owner = self.operations.create_escalation(
            raised_by_worker="internal_auditor",
            routed_to_role_key="owner_ceo",
            decision_class=DecisionClass.OWNER_RESERVED,
            reason_code="authority_envelope",
            title="Owner decision required",
            context="A future external account would need a standing grant.",
            recommendation="Keep the connector disabled.",
            safe_default="Remain paused.",
            owner_packet=owner_packet,
        )
        self.assertEqual(1, owner["owner_attention"])
        self.assertEqual(1, len(self.operations.list_escalations(owner_attention=True)))
        resolved = self.operations.resolve_escalation(
            owner["id"],
            actor_worker="kaleb_ceo",
            decision="resolved",
            resolution="Keep the future connector disabled pending a scoped grant.",
        )
        self.assertEqual("resolved", resolved["status"])
        self.assertEqual([], self.operations.list_escalations(owner_attention=True, status="routed"))

    def test_metric_incident_and_operating_summary_keep_truth_types(self) -> None:
        metric = self.operations.record_metric(
            metric_name="autonomous_completion_rate",
            metric_type="actual",
            value=0.0,
            unit="ratio",
            source_reference="test:empty-baseline",
            evidence_type="test_observation",
        )
        self.assertEqual("actual", metric["metric_type"])
        incident = self.operations.open_incident(
            incident_key="test-incident",
            severity="sev1",
            title="Ambiguous external effect",
            description="Synthetic test incident only.",
            affected_scope="test connector",
            owner_role_key="operations_analytics_chief",
            opened_by_worker="sre_operator",
            containment="Connector quarantined.",
        )
        self.assertEqual(1, incident["ceo_notification_required"])
        summary = self.operations.operations_summary()
        self.assertEqual(1, summary["open_incidents"])

    def test_work_events_are_append_only(self) -> None:
        self._work()
        with self.store._connection() as connection:
            event_id = connection.execute("SELECT id FROM work_events LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE work_events SET event_type = 'tampered' WHERE id = ?",
                    (event_id,),
                )


if __name__ == "__main__":
    unittest.main()
