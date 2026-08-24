"""Integration tests for migrations, durable records, ledgers, and audit history."""

from __future__ import annotations

import sqlite3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from company_os.errors import ConflictError, StorageError, ValidationError
from company_os.policy import ApprovalClass
from company_os.scoring import (
    COMPONENT_WEIGHTS,
    MarketVoidInput,
    calculate_market_void_score,
    score_from_evidence,
)
from company_os.storage import MIGRATIONS, CompanyStore


class CompanyStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.root = Path(self.temp_directory.name)
        self.database = self.root / "nested" / "company.db"
        self.store = CompanyStore(self.database)
        self.addCleanup(self.store.close)

    def test_initialize_is_idempotent_and_migrations_are_recorded_once(self) -> None:
        first = self.store.initialize()
        second = self.store.initialize()

        expected_versions = [version for version, _name, _sql in MIGRATIONS]
        self.assertEqual(expected_versions, first["applied"])
        self.assertEqual([], second["applied"])
        self.assertEqual(expected_versions[-1], first["schema_version"])
        self.assertEqual(first["schema_version"], second["schema_version"])

        with closing(sqlite3.connect(self.database)) as connection:
            recorded = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertEqual([(version,) for version in expected_versions], recorded)
        self.assertTrue(
            {
                "opportunities",
                "evidence",
                "experiments",
                "approvals",
                "decisions",
                "costs",
                "revenues",
                "risks",
                "opportunity_scores",
                "audit_events",
            }.issubset(tables)
        )

    def test_concurrent_fresh_database_initialization_is_serialized(self) -> None:
        database = self.root / "concurrent" / "company.db"

        def initialize_once(_: int) -> int:
            store = CompanyStore(database)
            try:
                return int(store.initialize()["schema_version"])
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=8) as executor:
            versions = list(executor.map(initialize_once, range(8)))
        self.assertEqual([MIGRATIONS[-1][0]] * 8, versions)

    def test_concurrent_process_initialization_is_serialized(self) -> None:
        database = self.root / "multiprocess" / "company.db"
        source_root = Path(__file__).resolve().parents[1] / "src"
        script = (
            "from company_os.storage import CompanyStore; "
            f"store=CompanyStore({str(database)!r}); "
            "print(store.initialize()['schema_version']); store.close()"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)

        def initialize_process(_: int) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env=environment,
                timeout=45,
                check=False,
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(initialize_process, range(4)))
        for result in results:
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(str(MIGRATIONS[-1][0]), result.stdout.strip())

    def test_unknown_future_schema_version_fails_closed(self) -> None:
        self.store.initialize()
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) "
                "VALUES (999, 'future', '2099-01-01T00:00:00Z')"
            )
            connection.commit()

        with self.assertRaisesRegex(StorageError, "unsupported migration version"):
            self.store.initialize()

    def test_opportunity_evidence_and_score_round_trip(self) -> None:
        opportunity = self.store.create_opportunity(
            "Billing reconciliation gap",
            buyer="Small SaaS operators",
            budget_holder="Founder",
            entry_wedge="Read-only discrepancy report",
        )
        evidence_one = self.store.add_evidence(
            opportunity["id"],
            criterion="need_severity",
            claim="Operators repeatedly report costly reconciliation errors.",
            source_uri="https://evidence.test/operator-behavior",
            strength="strong",
            rating=0.8,
            confidence=0.9,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )
        self.store.add_evidence(
            opportunity["slug"],
            criterion="reachable_beachhead",
            claim="A permission-based operator community is reachable.",
            source_uri="https://evidence.test/channel",
            strength="moderate",
            rating=0.6,
            confidence=0.8,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )

        evidence = self.store.list_evidence(opportunity["id"])
        score = score_from_evidence(evidence)
        saved = self.store.save_score(
            opportunity["slug"],
            score,
            inputs={"evidence_ids": [row["id"] for row in evidence]},
            actor="test_suite",
        )

        self.assertEqual(evidence_one["opportunity_id"], opportunity["id"])
        self.assertEqual(2, len(evidence))
        self.assertEqual(score.final_score, saved["final_score"])
        self.assertEqual(
            sorted(row["id"] for row in evidence),
            sorted(saved["inputs"]["evidence_ids"]),
        )
        self.assertEqual(score.to_dict()["final_score"], saved["result"]["final_score"])

        reopened = CompanyStore(self.database)
        self.addCleanup(reopened.close)
        fetched = reopened.get_opportunity(opportunity["slug"])
        latest = reopened.latest_score(opportunity["id"])
        self.assertEqual(opportunity["id"], fetched["id"])
        self.assertEqual(score.final_score, fetched["latest_score"])
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(saved["id"], latest["id"])
        self.assertEqual(2, reopened.status(repo_root=self.root)["counts"]["evidence"])

    def test_evidence_requires_a_valid_revalidation_window(self) -> None:
        opportunity = self.store.create_opportunity("Evidence freshness test")
        common = {
            "criterion": "need_severity",
            "claim": "A time-bounded observation.",
            "source_uri": "https://evidence.test/freshness",
        }

        with self.assertRaisesRegex(ValidationError, "expires_at is required"):
            self.store.add_evidence(opportunity["id"], **common)
        with self.assertRaisesRegex(ValidationError, "cannot be in the future"):
            self.store.add_evidence(
                opportunity["id"],
                **common,
                observed_at="2999-01-01",
                expires_at="2999-02-01",
            )
        with self.assertRaisesRegex(ValidationError, "later than observed_at"):
            self.store.add_evidence(
                opportunity["id"],
                **common,
                observed_at="2026-08-24",
                expires_at="2026-08-24",
            )
        with self.assertRaisesRegex(ValidationError, "not boolean"):
            self.store.add_evidence(
                opportunity["id"],
                **common,
                rating=True,  # type: ignore[arg-type]
                observed_at="2026-08-24",
                expires_at="2099-01-01",
            )

    def test_opportunity_advancement_requires_latest_eligible_score(self) -> None:
        opportunity = self.store.create_opportunity("Governed status test")

        for status in ("validating", "selected", "building"):
            with self.subTest(status=status, score="missing"):
                with self.assertRaisesRegex(ConflictError, "latest Market Void score"):
                    self.store.set_opportunity_status(opportunity["id"], status)

        problem_evidence = self.store.add_evidence(
            opportunity["id"],
            criterion="need_severity",
            claim="A qualifying problem observation.",
            source_uri="https://problem.test/evidence",
            strength="strong",
            rating=0.8,
            confidence=0.8,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )
        reach_evidence = self.store.add_evidence(
            opportunity["id"],
            criterion="reachable_beachhead",
            claim="A qualifying permission-based path.",
            source_uri="https://reach.test/evidence",
            strength="moderate",
            rating=0.6,
            confidence=0.7,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )

        eligible = calculate_market_void_score(
            MarketVoidInput(
                need_severity=1,
                demand_acceleration=1,
                economic_commitment=1,
                supply_gap=1,
                incumbent_weakness=1,
                reachable_beachhead=1,
                sustainable_advantage=1,
                switching_feasibility=1,
                bootstrap_feasibility=1,
                recurring_revenue=1,
            )
        )
        self.store.save_score(
            opportunity["id"],
            eligible,
            inputs={
                "evidence_ids": [problem_evidence["id"], reach_evidence["id"]]
            },
        )
        for status in ("validating", "selected", "building"):
            with self.subTest(status=status, score="eligible"):
                updated = self.store.set_opportunity_status(opportunity["id"], status)
                self.assertEqual(status, updated["status"])

        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "UPDATE evidence SET expires_at = '2000-01-01T00:00:00Z' WHERE id = ?",
                (problem_evidence["id"],),
            )
            connection.commit()
        with self.assertRaisesRegex(ConflictError, "current, traceable evidence"):
            self.store.set_opportunity_status(opportunity["id"], "selected")

        self.store.save_score(opportunity["id"], score_from_evidence([]))
        with self.assertRaisesRegex(ConflictError, "latest Market Void score"):
            self.store.set_opportunity_status(opportunity["id"], "selected")

    def test_opportunity_creation_cannot_bypass_advancement_gates(self) -> None:
        for status in ("validating", "selected", "building", "launched"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(
                    ValidationError, "invalid initial opportunity status"
                ):
                    self.store.create_opportunity(
                        f"Creation bypass {status}", status=status
                    )

    def test_eligible_score_without_evidence_ids_cannot_advance_status(self) -> None:
        opportunity = self.store.create_opportunity("Untraceable score test")
        eligible = calculate_market_void_score(
            MarketVoidInput(**{name: 1 for name in COMPONENT_WEIGHTS})
        )
        self.store.save_score(opportunity["id"], eligible)

        with self.assertRaisesRegex(ConflictError, "current, traceable evidence"):
            self.store.set_opportunity_status(opportunity["id"], "validating")

    def test_launched_status_is_reserved_for_a_future_external_workflow(self) -> None:
        opportunity = self.store.create_opportunity("Launch status test")
        with self.assertRaisesRegex(ValidationError, "internal-only runtime"):
            self.store.set_opportunity_status(opportunity["id"], "launched")

    def test_approval_lifecycle_prevents_self_approval_and_redecision(self) -> None:
        decision_packet = {
            "exact_action": "spend_money",
            "why_now": "Run one capped validation test only if evidence justifies it.",
            "source_evidence": "test:approval-lifecycle",
            "resource_ceiling": "USD 25.00",
            "accounts_data_public_surfaces": "Synthetic test account only",
            "control_findings": "Test controls found no unresolved block.",
            "reversibility": "The test can be stopped before spend.",
            "success_threshold": "The exact approval record is accepted.",
            "kill_threshold": "Any scope or ceiling mismatch.",
            "monitoring": "Approval and audit ledgers.",
            "expiry": "2099-01-01T00:00:00Z",
            "consequence_of_rejection_or_delay": "The test remains held.",
        }
        requested = self.store.request_approval(
            action="spend_money",
            rationale="Run a capped validation test.",
            risk="medium",
            estimated_cost_cents=2500,
            approval_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
            requested_by="company_os",
            expires_at="2099-01-01",
            decision_packet=decision_packet,
        )
        self.assertEqual("pending", requested["status"])
        self.assertEqual(1, len(self.store.list_approvals("pending")))

        with self.assertRaises(ValidationError):
            self.store.decide_approval(
                requested["id"], decision="approved", decided_by="company_os"
            )

        approved = self.store.decide_approval(
            requested["id"],
            decision="approved",
            decided_by="kaleb_ceo",
            notes="Approved only up to the stated cap.",
        )
        self.assertEqual("approved", approved["status"])
        self.assertEqual("kaleb_ceo", approved["decided_by"])
        self.assertEqual(
            requested["id"],
            self.store.find_approval_for_action("SPEND_MONEY")["id"],
        )
        with self.assertRaises(ConflictError):
            self.store.decide_approval(
                requested["id"], decision="rejected", decided_by="Kaleb"
            )

        incomplete = self.store.request_approval(
            action="spend_money",
            rationale="A packetless CEO request must remain held.",
            approval_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
            requested_by="finance_controller",
            expires_at="2099-01-01",
        )
        with self.assertRaisesRegex(ConflictError, "complete valid owner decision packet"):
            self.store.decide_approval(
                incomplete["id"], decision="approved", decided_by="kaleb_ceo"
            )

        tampered_packet = dict(decision_packet)
        tampered_packet["exact_action"] = "purchase_domain"
        tampered = self.store.request_approval(
            action="purchase_domain",
            rationale="Packet digest tampering must fail closed.",
            approval_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
            requested_by="company_president",
            expires_at="2099-01-01",
            decision_packet=tampered_packet,
        )
        tampered_packet["why_now"] = "This text was changed after the request."
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "UPDATE approvals SET decision_packet_json = ? WHERE id = ?",
                (json.dumps(tampered_packet), tampered["id"]),
            )
            connection.commit()
        with self.assertRaisesRegex(ConflictError, "digest does not match"):
            self.store.decide_approval(
                tampered["id"], decision="approved", decided_by="kaleb_ceo"
            )

        rejected_request = self.store.request_approval(
            action="accept_contract",
            rationale="Evaluate a proposed vendor contract.",
            approval_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
            requested_by="legal_review",
            expires_at="2099-01-01",
        )
        rejected = self.store.decide_approval(
            rejected_request["id"], decision="rejected", decided_by="Kaleb"
        )
        self.assertEqual("rejected", rejected["status"])

    def test_approval_request_cannot_downgrade_the_policy_class(self) -> None:
        spend = self.store.request_approval(
            action="spend_money",
            rationale="Exercise downgrade protection.",
            estimated_cost_cents=1,
            approval_class=ApprovalClass.AUTO_ALLOWED,
            expires_at="2099-01-01",
        )
        unknown_external = self.store.request_approval(
            action="new_external_side_effect",
            rationale="Unknown actions must fail closed.",
            approval_class=ApprovalClass.POLICY_GATED,
            expires_at="2099-01-01",
        )

        self.assertEqual(
            ApprovalClass.CEO_APPROVAL_REQUIRED.value,
            spend["approval_class"],
        )
        self.assertEqual(
            ApprovalClass.CEO_APPROVAL_REQUIRED.value,
            unknown_external["approval_class"],
        )

    def test_approval_request_requires_a_future_expiry(self) -> None:
        with self.assertRaisesRegex(ValidationError, "expires_at is required"):
            self.store.request_approval(
                action="publish_authorized",
                rationale="Missing expiry must fail closed.",
            )
        with self.assertRaisesRegex(ValidationError, "must be in the future"):
            self.store.request_approval(
                action="publish_authorized",
                rationale="Expired request must fail closed.",
                expires_at="2000-01-01",
            )

    def test_elapsed_pending_approval_is_expired_and_audited(self) -> None:
        request = self.store.request_approval(
            action="publish_authorized",
            rationale="Exercise automatic expiry.",
            expires_at="2099-01-01",
        )
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "UPDATE approvals SET expires_at = '2000-01-01T00:00:00Z' WHERE id = ?",
                (request["id"],),
            )
            connection.commit()

        self.assertEqual([], self.store.list_approvals("pending"))
        expired = self.store.get_approval(request["id"])
        self.assertEqual("expired", expired["status"])
        self.assertIn(
            "approval.expired",
            {event["event_type"] for event in self.store.list_audit_events()},
        )

    def test_financial_amounts_require_non_negative_integer_cents(self) -> None:
        invalid_values = (True, 1.5, "100", -1, 9_223_372_036_854_775_808)
        for value in invalid_values:
            with self.subTest(value=value, ledger="cost"):
                with self.assertRaises(ValidationError):
                    self.store.record_cost(
                        amount_cents=value,  # type: ignore[arg-type]
                        description="Invalid cost",
                    )
            with self.subTest(value=value, ledger="revenue"):
                with self.assertRaises(ValidationError):
                    self.store.record_revenue(
                        amount_cents=value,  # type: ignore[arg-type]
                        description="Invalid revenue",
                    )
            with self.subTest(value=value, ledger="approval"):
                with self.assertRaises(ValidationError):
                    self.store.request_approval(
                        action="spend_money",
                        rationale="Invalid amount",
                        estimated_cost_cents=value,  # type: ignore[arg-type]
                    )
            with self.subTest(value=value, ledger="experiment"):
                opportunity = self.store.create_opportunity(
                    f"Invalid experiment amount {value!r}"
                )
                with self.assertRaises(ValidationError):
                    self.store.create_experiment(
                        opportunity["id"],
                        name="Invalid experiment",
                        hypothesis="Invalid fractional budget should fail.",
                        method="Unit test",
                        success_metric="Rejected",
                        kill_metric="Accepted",
                        planned_cost_cents=value,  # type: ignore[arg-type]
                    )

    def test_financial_summary_keeps_actuals_estimates_and_forecasts_separate(self) -> None:
        self.store.record_cost(
            amount_cents=1000,
            description="Possible validation tool",
            status="estimated",
        )
        self.store.record_cost(
            amount_cents=300,
            description="Incurred test cost",
            status="incurred",
            source_reference="receipt:test-incurred",
        )
        self.store.record_cost(
            amount_cents=200,
            description="Paid test cost",
            status="paid",
            source_reference="receipt:test-paid",
        )
        self.store.record_revenue(
            amount_cents=5000,
            description="Conservative forecast",
            entry_type="projection",
            status="projected",
        )
        self.store.record_revenue(
            amount_cents=700,
            description="Realized but uncleared sale",
            status="realized",
            external_reference="sale:test-realized",
        )
        self.store.record_revenue(
            amount_cents=800,
            description="Cleared sale",
            status="cleared",
            external_reference="sale:test-cleared",
        )
        self.store.record_revenue(
            amount_cents=100,
            description="Customer refund",
            entry_type="refund",
            status="realized",
            external_reference="refund:test-realized",
        )

        usd = self.store.financial_summary()["USD"]
        self.assertEqual(1500, usd["actual_revenue_cents"])
        self.assertEqual(800, usd["cleared_revenue_cents"])
        self.assertEqual(100, usd["refunds_cents"])
        self.assertEqual(500, usd["actual_costs_cents"])
        self.assertEqual(300, usd["incurred_costs_cents"])
        self.assertEqual(200, usd["paid_costs_cents"])
        self.assertEqual(1000, usd["estimated_costs_cents"])
        self.assertEqual(5000, usd["projected_revenue_cents"])
        self.assertEqual(500, usd["net_cash_contribution_cents"])

        with self.assertRaises(ValidationError):
            self.store.record_revenue(
                amount_cents=1,
                description="Invalid projection",
                entry_type="projection",
                status="realized",
            )

    def test_actual_ledgers_require_unique_source_evidence(self) -> None:
        with self.assertRaisesRegex(ValidationError, "source_reference is required"):
            self.store.record_cost(
                amount_cents=100,
                description="Unsupported actual cost",
                status="incurred",
            )
        with self.assertRaisesRegex(ValidationError, "external_reference is required"):
            self.store.record_revenue(
                amount_cents=100,
                description="Unsupported actual revenue",
                status="realized",
            )

        self.store.record_cost(
            amount_cents=100,
            description="Supported actual cost",
            status="paid",
            source_reference="receipt:unique",
        )
        with self.assertRaises(ConflictError):
            self.store.record_cost(
                amount_cents=100,
                description="Duplicate actual cost",
                status="paid",
                source_reference="receipt:unique",
            )

        self.store.record_revenue(
            amount_cents=100,
            description="Supported actual revenue",
            status="cleared",
            external_reference="sale:unique",
        )
        with self.assertRaises(ConflictError):
            self.store.record_revenue(
                amount_cents=100,
                description="Duplicate actual revenue",
                status="cleared",
                external_reference="sale:unique",
            )

        with self.assertRaisesRegex(ValidationError, "cost occurred_at cannot be"):
            self.store.record_cost(
                amount_cents=100,
                description="Future actual cost",
                status="incurred",
                source_reference="receipt:future",
                occurred_at="2999-01-01",
            )
        with self.assertRaisesRegex(ValidationError, "revenue/refund occurred_at cannot be"):
            self.store.record_revenue(
                amount_cents=100,
                description="Future actual revenue",
                status="realized",
                external_reference="sale:future",
                occurred_at="2999-01-01",
            )

    def test_financial_status_transitions_update_cash_truth_without_duplicates(self) -> None:
        cost = self.store.record_cost(
            amount_cents=250,
            description="Pending vendor charge",
            status="incurred",
            source_reference="receipt:lifecycle",
        )
        revenue = self.store.record_revenue(
            amount_cents=1000,
            description="Settling customer payment",
            status="realized",
            external_reference="sale:lifecycle",
        )
        before = self.store.financial_summary()["USD"]
        self.assertEqual(0, before["cleared_revenue_cents"])
        self.assertEqual(0, before["paid_costs_cents"])
        self.assertEqual(0, before["net_cash_contribution_cents"])

        settled_revenue = self.store.set_revenue_status(revenue["id"], "cleared")
        paid_cost = self.store.set_cost_status(cost["id"], "paid")
        after = self.store.financial_summary()["USD"]
        self.assertEqual("cleared", settled_revenue["status"])
        self.assertEqual("paid", paid_cost["status"])
        self.assertEqual(1000, after["cleared_revenue_cents"])
        self.assertEqual(250, after["paid_costs_cents"])
        self.assertEqual(750, after["net_cash_contribution_cents"])

        with self.assertRaises(ConflictError):
            self.store.set_revenue_status(revenue["id"], "realized")
        with self.assertRaises(ConflictError):
            self.store.set_cost_status(cost["id"], "incurred")

    def test_future_estimate_needs_actual_date_before_entering_cash_totals(self) -> None:
        estimate = self.store.record_cost(
            amount_cents=250,
            description="Future estimate",
            status="estimated",
            occurred_at="2999-01-01",
        )

        with self.assertRaisesRegex(ValidationError, "actual occurrence time"):
            self.store.set_cost_status(
                estimate["id"],
                "paid",
                source_reference="receipt:future-estimate",
            )
        self.assertEqual(
            0, self.store.financial_summary()["USD"]["paid_costs_cents"]
        )

        paid = self.store.set_cost_status(
            estimate["id"],
            "paid",
            source_reference="receipt:future-estimate",
            occurred_at="2026-08-24",
        )
        self.assertEqual("paid", paid["status"])
        self.assertEqual("2026-08-24T00:00:00Z", paid["occurred_at"])
        self.assertEqual(
            250, self.store.financial_summary()["USD"]["paid_costs_cents"]
        )

    def test_each_material_mutation_appends_a_valid_audit_event(self) -> None:
        opportunity = self.store.create_opportunity("Audit test")
        self.store.set_opportunity_status(opportunity["id"], "researching")
        self.store.record_decision(
            title="Continue research",
            decision="research",
            rationale="Evidence is not yet sufficient.",
            decided_by="test_suite",
            opportunity=opportunity["id"],
        )
        self.store.record_risk(
            category="evidence",
            title="Stale market signals",
            description="Evidence may expire before a test runs.",
            likelihood=3,
            impact=4,
            opportunity=opportunity["id"],
        )

        events = self.store.list_audit_events(limit=20)
        event_types = {event["event_type"] for event in events}
        self.assertTrue(
            {
                "opportunity.created",
                "opportunity.status_changed",
                "decision.recorded",
                "risk.recorded",
            }.issubset(event_types)
        )
        self.assertTrue(all(isinstance(event["details"], dict) for event in events))
        self.assertEqual((True, None), self.store.verify_audit_chain())

    def test_risk_ratings_require_bounded_integers(self) -> None:
        for likelihood, impact in ((True, 3), (3.0, 3), (3, 0), (3, 6)):
            with self.subTest(likelihood=likelihood, impact=impact):
                with self.assertRaises(ValidationError):
                    self.store.record_risk(
                        category="test",
                        title="Invalid rating",
                        description="Invalid risk ratings must fail.",
                        likelihood=likelihood,  # type: ignore[arg-type]
                        impact=impact,
                    )

    def test_audit_rows_cannot_be_updated_or_deleted(self) -> None:
        self.store.create_opportunity("Immutable audit test")
        with closing(sqlite3.connect(self.database)) as connection:
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "UPDATE audit_events SET action = 'rewritten' WHERE id = 1"
                )
            connection.rollback()
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute("DELETE FROM audit_events WHERE id = 1")
        self.assertEqual((True, None), self.store.verify_audit_chain())

    def test_audit_chain_detects_an_invalid_appended_event(self) -> None:
        self.store.create_opportunity("Tamper detection test")
        with closing(sqlite3.connect(self.database)) as connection:
            prior_hash = connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO audit_events(
                    event_type, actor, entity_type, entity_id, action, detail_json,
                    created_at, previous_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "invalid.append",
                    "tamper_test",
                    "audit",
                    "0",
                    "append",
                    "{}",
                    "2026-08-24T00:00:00Z",
                    prior_hash,
                    "0" * 64,
                ),
            )
            bad_id = cursor.lastrowid
            connection.commit()
        self.assertEqual((False, bad_id), self.store.verify_audit_chain())


if __name__ == "__main__":
    unittest.main()
