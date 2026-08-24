"""Bounded autonomous company-cycle integration tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from pathlib import Path

from company_os.autonomy import AutonomousCompany, ROLE_TO_CODEX_AGENT
from company_os.corporate import CorporateOperations
from company_os.errors import ConflictError
from company_os.policy import ApprovalRequired, PauseActive
from company_os.storage import CompanyStore


class AutonomousCompanyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.repo_root = Path(self.temp_directory.name)
        (self.repo_root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
        self.store = CompanyStore(":memory:")
        self.addCleanup(self.store.close)
        self.operations = CorporateOperations(self.store)
        self.company = AutonomousCompany(
            self.operations, repo_root=str(self.repo_root)
        )

    def test_internal_cycle_bootstraps_plans_executes_integrity_and_dispatches(self) -> None:
        result = self.company.run_cycle(mode="internal")

        self.assertEqual("awaiting_workers", result["cycle"]["status"])
        self.assertEqual("succeeded", result["summary"]["integrity_check_status"])
        self.assertEqual(7, result["summary"]["planned_work_items"])
        self.assertEqual(2, result["summary"]["dispatchable_work_items"])
        self.assertEqual(0, result["summary"]["external_effects_executed"])
        self.assertEqual(0, result["summary"]["owner_attention_items"])
        self.assertEqual(3, result["operations"]["active_objectives"])
        self.assertEqual(
            {"ready": 2, "succeeded": 1, "waiting_dependency": 5},
            result["operations"]["queue"],
        )

    def test_pause_blocks_scheduled_and_external_cycles_but_not_manual_internal(self) -> None:
        with self.assertRaises(PauseActive):
            self.company.run_cycle(mode="internal", scheduled=True)
        with self.assertRaises(PauseActive):
            self.company.run_cycle(mode="external", scheduled=False)
        result = self.company.run_cycle(mode="simulation", scheduled=False, max_work_items=1)
        self.assertEqual("succeeded", result["summary"]["integrity_check_status"])

    def test_scheduled_internal_cycle_requires_and_accepts_matching_approval(self) -> None:
        (self.repo_root / "PAUSE_AUTONOMY").unlink()
        with patch.dict("os.environ", {"COMPANY_OS_PAUSED": "0"}):
            with self.assertRaises(ApprovalRequired):
                self.company.run_cycle(mode="internal", scheduled=True)
            approval = self.store.request_approval(
                action="internal_analysis",
                rationale="Authorize one bounded scheduled internal operating cycle.",
                risk="Local internal records only.",
                approval_class="policy_gated",
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                requested_by="test-requester",
            )
            self.store.decide_approval(
                approval["id"],
                decision="approved",
                decided_by="test-owner",
                notes="Synthetic test approval.",
            )
            result = self.company.run_cycle(
                mode="internal",
                scheduled=True,
                approval_id=approval["id"],
                max_work_items=1,
            )
            self.assertEqual(1, result["cycle"]["scheduled"])
            self.assertEqual(0, result["summary"]["external_effects_executed"])

    def test_non_executive_cannot_trigger_presidential_workflow(self) -> None:
        with self.assertRaises(ConflictError):
            self.company.run_cycle(triggered_by_worker="software_engineer")
        self.assertEqual([], self.operations.list_objectives())
        self.assertEqual([], self.operations.list_work())

    def test_invalid_audit_chain_halts_before_planning_or_dispatch(self) -> None:
        self.operations.bootstrap_organization(actor="test")
        with self.store._connection() as connection:
            prior_hash = connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO audit_events(
                    event_type, actor, entity_type, entity_id, action, detail_json,
                    created_at, previous_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "invalid.append",
                    "tamper-test",
                    "audit",
                    "0",
                    "append",
                    "{}",
                    "2026-08-24T00:00:00Z",
                    prior_hash,
                    "0" * 64,
                ),
            )
            connection.commit()
        result = self.company.run_cycle(max_work_items=3)
        self.assertEqual("failed", result["cycle"]["status"])
        self.assertTrue(result["summary"]["halted_by_integrity_gate"])
        self.assertEqual(0, result["summary"]["planned_work_items"])
        self.assertEqual(0, result["dispatch"]["dispatchable_count"])
        self.assertEqual(1, result["operations"]["open_incidents"])

    def test_unhandled_cycle_error_is_fenced_as_failed(self) -> None:
        with patch.object(
            self.operations,
            "recover_expired_leases",
            side_effect=RuntimeError("synthetic worker recovery failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.company.run_cycle(max_work_items=1)
        with self.store._connection() as connection:
            cycles = connection.execute(
                "SELECT status, completed_at FROM operating_cycles ORDER BY id"
            ).fetchall()
        self.assertEqual(1, len(cycles))
        self.assertEqual("failed", cycles[0]["status"])
        self.assertIsNotNone(cycles[0]["completed_at"])

    def test_cycle_hard_limit_bounds_new_work(self) -> None:
        result = self.company.run_cycle(max_work_items=2)
        cycle_work = self.operations.list_work(cycle_id=result["cycle"]["id"], limit=100)
        self.assertEqual(2, len(cycle_work))
        self.assertEqual(1, result["summary"]["planned_work_items"])
        self.assertEqual(1, result["summary"]["dispatchable_work_items"])

    def test_repeated_cycle_reconciles_instead_of_duplicating_weekly_work(self) -> None:
        first = self.company.run_cycle()
        first_count = len(self.operations.list_work(limit=1000))
        second = self.company.run_cycle()
        second_count = len(self.operations.list_work(limit=1000))

        self.assertEqual(first_count + 1, second_count)  # one fresh integrity check
        self.assertEqual(0, second["summary"]["planned_work_items"])
        self.assertEqual(7, second["summary"]["reconciled_portfolio_work_items"])
        self.assertEqual(
            first["summary"]["dispatchable_work_items"],
            second["summary"]["dispatchable_work_items"],
        )

    def test_completed_standing_objective_rolls_forward_without_key_collision(self) -> None:
        self.company.run_cycle(max_work_items=1)
        original = next(
            row
            for row in self.operations.list_objectives()
            if row["objective_key"] == "company.validate-first-demand"
        )
        key_result = self.operations.get_objective(original["id"])["key_results"][0]
        self.operations.update_key_result(
            key_result["id"],
            current_value=1,
            evidence_reference="test:accepted-validation-recommendation",
            actor_worker="strategy_portfolio_chief",
        )
        self.operations.set_objective_status(
            original["id"],
            status="achieved",
            rationale="The standing target was achieved and should roll forward.",
            actor_worker="strategy_portfolio_chief",
        )

        result = self.company.run_cycle(max_work_items=2)
        active_keys = {
            row["objective_key"]
            for row in self.operations.list_objectives(status="active")
        }
        self.assertIn("company.validate-first-demand.v2", active_keys)
        self.assertEqual("awaiting_workers", result["cycle"]["status"])

    def test_cancelled_standing_objective_requires_an_explicit_new_mandate(self) -> None:
        self.company.run_cycle(max_work_items=1)
        objective = next(
            row
            for row in self.operations.list_objectives()
            if row["objective_key"] == "company.validate-first-demand"
        )
        self.operations.set_objective_status(
            objective["id"],
            status="cancelled",
            rationale="The objective owner explicitly stopped this mandate.",
            actor_worker="strategy_portfolio_chief",
        )
        with self.assertRaisesRegex(ConflictError, "explicit new mandate"):
            self.company.run_cycle(max_work_items=1)
        keys = {row["objective_key"] for row in self.operations.list_objectives()}
        self.assertNotIn("company.validate-first-demand.v2", keys)
        with self.store._connection() as connection:
            latest = connection.execute(
                "SELECT status FROM operating_cycles ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertEqual("failed", latest["status"])

    def test_cycle_coordinator_is_singleton_and_stale_runs_are_recovered(self) -> None:
        self.operations.bootstrap_organization(actor="test")
        first = self.operations.create_cycle(
            cycle_key="test-running-cycle",
            mode="internal",
            triggered_by_worker="company_president",
        )
        with self.assertRaisesRegex(ConflictError, "already running"):
            self.operations.create_cycle(
                cycle_key="test-overlapping-cycle",
                mode="internal",
                triggered_by_worker="company_president",
            )
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE operating_cycles SET started_at = ? WHERE id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(hours=2))
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                    first["id"],
                ),
            )
        self.assertEqual(
            1,
            self.operations.recover_stale_cycles(
                actor_worker="sre_operator", max_age_seconds=3600
            ),
        )
        replacement = self.operations.create_cycle(
            cycle_key="test-replacement-cycle",
            mode="internal",
            triggered_by_worker="company_president",
        )
        self.assertEqual("running", replacement["status"])

    def test_existing_opportunity_gets_independent_stage_work_not_auto_launch(self) -> None:
        opportunity = self.store.create_opportunity(
            "Specific test buyer pain",
            description="A candidate, not validated demand.",
            buyer="Specific buyer",
            budget_holder="Specific budget owner",
            actor="test",
        )
        result = self.company.run_cycle()
        work = self.operations.list_work(cycle_id=result["cycle"]["id"], limit=100)
        opportunity_work = [
            item for item in work if item["opportunity_id"] == opportunity["id"]
        ]
        self.assertEqual(4, len(opportunity_work))
        self.assertEqual(
            {
                "evidence_refresh",
                "counter_thesis",
                "opportunity_control_screen",
                "validation_plan",
            },
            {item["task_type"] for item in opportunity_work},
        )
        self.assertEqual("candidate", self.store.get_opportunity(opportunity["id"])["status"])
        self.assertTrue(all(item["external_effect"] == 0 for item in work))

    def test_dispatch_uses_only_configured_project_agent_names(self) -> None:
        result = self.company.run_cycle()
        configured = {
            "president",
            "portfolio_lead",
            "opportunity_intelligence",
            "validation_red_team",
            "product_engineer",
            "commercial_operator",
            "finance_controller",
            "trust_officer",
            "quality_reliability",
            "internal_auditor",
        }
        self.assertTrue(set(ROLE_TO_CODEX_AGENT.values()) <= configured)
        dispatched = {
            item["codex_agent"]
            for rows in result["dispatch"]["departments"].values()
            for item in rows
        }
        self.assertTrue(dispatched <= configured)

    def test_integrity_work_has_independent_acceptance_evidence(self) -> None:
        result = self.company.run_cycle(max_work_items=1)
        work = self.operations.list_work(cycle_id=result["cycle"]["id"], limit=10)
        self.assertEqual(1, len(work))
        integrity = self.operations.get_work(work[0]["id"])
        self.assertEqual("succeeded", integrity["status"])
        self.assertEqual("sre_operator", integrity["assigned_worker_key"])
        self.assertEqual("internal_auditor", integrity["reviewer_role_key"])
        self.assertEqual("ok", integrity["result"]["sqlite_quick_check"])
        self.assertTrue(integrity["result"]["audit_chain_valid"])

    def test_repeated_integrity_checks_do_not_game_worker_performance(self) -> None:
        for _ in range(6):
            self.company.run_cycle(max_work_items=1)
        sre = next(
            row
            for row in self.operations.performance_report()
            if row["worker_key"] == "sre_operator"
        )
        self.assertEqual(0, sre["sample_size"])
        self.assertEqual("insufficient_sample", sre["performance_state"])


if __name__ == "__main__":
    unittest.main()
