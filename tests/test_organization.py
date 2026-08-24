"""Tests for the immutable company hierarchy and control separation."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, fields, replace

from company_os.errors import ValidationError
from company_os.organization import (
    DEPARTMENTS,
    ROLES,
    WORKERS,
    DepartmentSpec,
    RoleSpec,
    WorkerSpec,
    can_block,
    can_command,
    can_review,
    department_by_slug,
    escalation_route,
    reporting_chain,
    role_by_key,
    separation_of_duties_satisfied,
    validate_blueprint,
    worker_by_key,
    worker_reporting_chain,
)


class OrganizationBlueprintTests(unittest.TestCase):
    def test_blueprint_has_complete_but_bounded_roster(self) -> None:
        expected_roles = {
            "owner_ceo",
            "company_president",
            "chief_of_staff",
            "strategy_portfolio_chief",
            "opportunity_intelligence_lead",
            "market_researcher",
            "market_structure_analyst",
            "validation_lead",
            "counter_thesis_analyst",
            "product_technology_chief",
            "product_manager",
            "software_architect",
            "software_engineer",
            "qa_reliability_lead",
            "revenue_chief",
            "growth_strategist",
            "content_operator",
            "sales_partnerships_lead",
            "customer_success_lead",
            "finance_controller",
            "risk_legal_chief",
            "legal_compliance_officer",
            "security_privacy_officer",
            "people_agent_ops_chief",
            "operations_analytics_chief",
            "data_analyst",
            "sre_operator",
            "internal_auditor",
        }

        self.assertEqual(12, len(DEPARTMENTS))
        self.assertEqual(expected_roles, {role.role_key for role in ROLES})
        self.assertEqual(len(ROLES), len(WORKERS))
        self.assertTrue(validate_blueprint())

    def test_specs_expose_stable_persistence_fields(self) -> None:
        self.assertTrue(
            {
                "slug",
                "name",
                "mission",
                "parent_slug",
                "executive_role_key",
                "service_level_cycles",
                "wip_limit",
            }.issubset({item.name for item in fields(DepartmentSpec)})
        )
        self.assertTrue(
            {
                "role_key",
                "department_slug",
                "title",
                "reports_to_role_key",
                "authority_level",
                "worker_type",
                "mandate",
                "capabilities",
                "kpis",
                "max_active_work",
                "independent_control",
            }.issubset({item.name for item in fields(RoleSpec)})
        )
        self.assertEqual(
            {
                "worker_key",
                "display_name",
                "role_key",
                "manager_worker_key",
                "worker_type",
                "status",
                "capacity_units",
                "quality_floor",
            },
            {item.name for item in fields(WorkerSpec)},
        )

    def test_specs_and_collection_fields_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            role_by_key("software_engineer").title = "Changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            role_by_key("software_engineer").capabilities[0] = "changed"  # type: ignore[index]
        self.assertIsInstance(DEPARTMENTS, tuple)
        self.assertIsInstance(ROLES, tuple)
        self.assertIsInstance(WORKERS, tuple)

    def test_helpers_resolve_stable_keys_and_fail_on_unknown_keys(self) -> None:
        self.assertEqual(
            "strategy_portfolio_chief",
            department_by_slug("strategy-portfolio").executive_role_key,
        )
        self.assertEqual("Chief of Staff", role_by_key("chief_of_staff").title)
        self.assertEqual("Kaleb", worker_by_key("kaleb_ceo").display_name)
        with self.assertRaisesRegex(KeyError, "unknown department"):
            department_by_slug("missing")
        with self.assertRaisesRegex(KeyError, "unknown role"):
            role_by_key("missing")
        with self.assertRaisesRegex(KeyError, "unknown worker"):
            worker_by_key("missing")

    def test_reporting_chain_is_strict_and_reaches_the_human_owner(self) -> None:
        self.assertEqual(
            ("product_technology_chief", "company_president", "owner_ceo"),
            reporting_chain("software_engineer"),
        )
        self.assertEqual(
            (
                "software_engineer",
                "product_technology_chief",
                "company_president",
                "owner_ceo",
            ),
            reporting_chain("software_engineer", include_self=True),
        )
        self.assertEqual(
            ("product_technology_chief", "company_president", "kaleb_ceo"),
            worker_reporting_chain("software_engineer"),
        )
        self.assertEqual((), reporting_chain("owner_ceo"))
        self.assertEqual((), worker_reporting_chain("kaleb_ceo"))

    def test_command_authority_follows_reporting_lines_not_peer_status(self) -> None:
        self.assertTrue(can_command("owner_ceo", "internal_auditor"))
        self.assertTrue(can_command("company_president", "finance_controller"))
        self.assertTrue(
            can_command("product_technology_chief", "software_engineer")
        )
        self.assertFalse(can_command("product_technology_chief", "growth_strategist"))
        self.assertFalse(can_command("software_architect", "software_engineer"))
        self.assertFalse(can_command("software_engineer", "product_manager"))
        self.assertFalse(can_command("company_president", "company_president"))
        self.assertFalse(can_command("company_president", "owner_ceo"))

    def test_administrative_command_does_not_remove_independent_stop_rights(self) -> None:
        self.assertTrue(can_command("company_president", "finance_controller"))
        self.assertTrue(can_block("finance_controller", "budget"))
        self.assertTrue(can_block("qa_reliability_lead", "release"))
        self.assertTrue(can_block("risk_legal_chief", "risk"))
        self.assertTrue(can_block("security_privacy_officer", "privacy"))
        self.assertTrue(can_block("internal_auditor", "audit"))
        self.assertFalse(can_block("revenue_chief", "claims"))
        self.assertFalse(can_block("finance_controller", "legal"))
        self.assertFalse(can_block("risk_legal_chief", ""))

    def test_general_review_requires_a_manager_and_never_allows_self_review(self) -> None:
        self.assertTrue(
            can_review("product_technology_chief", "software_engineer")
        )
        self.assertFalse(can_review("software_engineer", "product_manager"))
        self.assertFalse(can_review("software_engineer", "software_engineer"))
        self.assertFalse(can_review("revenue_chief", "software_engineer"))

    def test_control_review_requires_distinct_qualified_independent_role(self) -> None:
        self.assertTrue(
            separation_of_duties_satisfied(
                "content_operator", "legal_compliance_officer", "claims"
            )
        )
        self.assertTrue(
            separation_of_duties_satisfied(
                "validation_lead",
                "counter_thesis_analyst",
                "opportunity_advancement",
            )
        )
        self.assertTrue(
            can_review(
                "qa_reliability_lead",
                "software_engineer",
                "release",
                independent=True,
            )
        )
        self.assertFalse(
            separation_of_duties_satisfied(
                "growth_strategist", "content_operator", "claims"
            )
        )
        self.assertFalse(
            separation_of_duties_satisfied(
                "risk_legal_chief", "risk_legal_chief", "risk"
            )
        )

    def test_control_escalation_can_bypass_the_profit_chain(self) -> None:
        self.assertEqual(
            ("risk_legal_chief", "owner_ceo"),
            escalation_route("legal_compliance_officer"),
        )
        self.assertEqual(("owner_ceo",), escalation_route("finance_controller"))
        self.assertEqual(("owner_ceo",), escalation_route("qa_reliability_lead"))
        self.assertEqual(
            ("opportunity_intelligence_lead", "company_president", "owner_ceo"),
            escalation_route("market_researcher"),
        )


class OrganizationValidationTests(unittest.TestCase):
    def test_duplicate_department_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate department"):
            validate_blueprint(DEPARTMENTS + (DEPARTMENTS[0],), ROLES, WORKERS)

    def test_role_reporting_cycle_is_rejected(self) -> None:
        roles = tuple(
            replace(role, reports_to_role_key="software_engineer")
            if role.role_key == "product_technology_chief"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(ValidationError, "role reporting cycle"):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)

    def test_unknown_role_manager_is_rejected(self) -> None:
        roles = tuple(
            replace(role, reports_to_role_key="missing_role")
            if role.role_key == "software_engineer"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(ValidationError, "unknown manager"):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)

    def test_department_executive_must_report_to_president(self) -> None:
        roles = tuple(
            replace(role, reports_to_role_key="owner_ceo")
            if role.role_key == "revenue_chief"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(
            ValidationError, "revenue_chief must report to company_president"
        ):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)

    def test_independent_control_needs_matching_review_and_block_capability(self) -> None:
        roles = tuple(
            replace(
                role,
                capabilities=tuple(
                    item for item in role.capabilities if item != "review:audit"
                ),
            )
            if role.role_key == "internal_auditor"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(ValidationError, "lacks review/block capability"):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)

    def test_missing_independent_control_domain_is_rejected(self) -> None:
        roles = tuple(
            replace(
                role,
                independent_control=False,
                block_domains=(),
                escalation_role_key=None,
            )
            if role.role_key == "security_privacy_officer"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(ValidationError, "lacks independent control"):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)

    def test_worker_manager_must_match_role_hierarchy(self) -> None:
        workers = tuple(
            replace(worker, manager_worker_key="company_president")
            if worker.worker_key == "software_engineer"
            else worker
            for worker in WORKERS
        )
        with self.assertRaisesRegex(ValidationError, "manager does not match"):
            validate_blueprint(DEPARTMENTS, ROLES, workers)

    def test_worker_and_role_type_must_match(self) -> None:
        workers = tuple(
            replace(worker, worker_type="human")
            if worker.worker_key == "software_engineer"
            else worker
            for worker in WORKERS
        )
        with self.assertRaisesRegex(ValidationError, "type does not match"):
            validate_blueprint(DEPARTMENTS, ROLES, workers)

    def test_worker_quality_floor_is_bounded(self) -> None:
        workers = tuple(
            replace(worker, quality_floor=1.01)
            if worker.worker_key == "software_engineer"
            else worker
            for worker in WORKERS
        )
        with self.assertRaisesRegex(ValidationError, "quality floor"):
            validate_blueprint(DEPARTMENTS, ROLES, workers)

    def test_capabilities_must_be_an_immutable_tuple(self) -> None:
        roles = tuple(
            replace(role, capabilities=["software:implement"])  # type: ignore[arg-type]
            if role.role_key == "software_engineer"
            else role
            for role in ROLES
        )
        with self.assertRaisesRegex(ValidationError, "immutable capabilities"):
            validate_blueprint(DEPARTMENTS, roles, WORKERS)


if __name__ == "__main__":
    unittest.main()
