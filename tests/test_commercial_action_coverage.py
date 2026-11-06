"""CE-4B exact commercial action coverage and permanent development lock tests.

This suite tests an internal policy function, NOT actual enforcement across
external payment, web, advertising or connector services. Only an authenticated
host-side release controller can establish comprehensive no-bypass behavior.
"""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_launch_guard import (
    COMPETITIVE_ENGINE_BOOTSTRAP_ACTION,
    COMPETITIVE_ENGINE_GATED_ACTIONS,
    requires_competitive_engine,
)
from company_os.policy import ActionRequest, evaluate_action, ApprovalClass


NAMED_COMMERCIAL_ACTIONS = (
    "launch_business", "launch_venture", "launch_product",
    "activate_business", "activate_product", "activate_venture",
    "start_business", "open_business", "start_revenue_operations",
    "go_live_service", "deploy_authorized", "publish_authorized",
    "publish_regulated_claim", "publish_client_report",
    "send_client_report", "send_client_report_final",
    "send_sales_proposal", "send_sales_proposal_customer",
    "send_quote", "send_quote_for_installation",
    "send_marketing_email", "send_marketing_campaign",
    "post_social_ad", "post_social_announcement",
    "post_marketing_campaign", "advertise_business", "advertise_on_social",
    "promote_business_services", "solicit_customers", "solicit_leads",
    "create_checkout", "create_checkout_session",
    "create_payment_link", "create_payment_link_for_customer",
    "activate_checkout", "activate_checkout_gateway",
    "activate_subscription_service", "open_storefront", "open_storefront_online",
    "start_sales_campaign", "accept_new_order", "accept_new_order_online",
    "charge_new_customer", "charge_new_customer_subscription",
)

BOOTSTRAP_OR_CONTINUITY = (
    "deploy_competitive_engine",
    "research_public_source",
    "call_approved_api",
    "send_transactional_message",
    "predefined_refund",
    "write_code", "run_tests", "internal_analysis",
)


class CommercialActionCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {
            "COMPANY_OS_PAUSED": "0",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def approval(self, action):
        return {
            "id": 17, "status": "approved", "action": action,
            "approval_class": ApprovalClass.CEO_APPROVAL_REQUIRED.value,
            "estimated_cost_cents": 10_000_000,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

    def test_all_named_commercial_actions_are_gated_without_side_effect_flags(self):
        for action in NAMED_COMMERCIAL_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(requires_competitive_engine(action), action)
                # An untruthful caller says the action is not external. The
                # name still forces a missing-engine denial before CEO approval.
                request = ActionRequest(action=action, external=False)
                outcome = evaluate_action(
                    request, approval=self.approval(action), repo_root=self.root,
                )
                self.assertFalse(outcome.allowed)
                self.assertTrue(outcome.blocked_by_competitive_engine, action)

    def test_case_and_whitespace_cannot_evade_commercial_action_detection(self):
        for action in NAMED_COMMERCIAL_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(requires_competitive_engine("  " + action.upper() + " "))

    def test_action_gated_with_forged_auto_class(self):
        for action in ("send_marketing_email", "send_client_report", "charge_new_customer"):
            with self.subTest(action=action):
                request = ActionRequest(
                    action=action, requested_class=ApprovalClass.AUTO_ALLOWED,
                )
                decision = evaluate_action(request,repo_root=self.root)
                self.assertFalse(decision.allowed)
                self.assertTrue(decision.blocked_by_competitive_engine)

    def test_unknown_external_outbound_action_is_engine_gated(self):
        for action in ("email_new_client", "webhook_new_sales", "ship_goods",
                       "post_public_site_update", "brand_new_checkout_flow"):
            with self.subTest(action=action):
                request = ActionRequest(action=action, external=True)
                decision = evaluate_action(
                    request, approval=self.approval(action), repo_root=self.root,
                )
                self.assertFalse(decision.allowed)
                self.assertTrue(decision.blocked_by_competitive_engine)

    def test_unknown_internal_work_stays_ceo_gated_not_auto_approved(self):
        request = ActionRequest(action="unregistered_internal_function", external=False)
        decision = evaluate_action(request,repo_root=self.root)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertFalse(decision.blocked_by_competitive_engine)

    def test_explicit_bootstrap_and_continuity_do_not_deadlock_engine_setup(self):
        for action in BOOTSTRAP_OR_CONTINUITY:
            with self.subTest(action=action):
                self.assertFalse(requires_competitive_engine(action))

    def test_no_automatic_approval_for_existing_customer_messaging(self):
        decision = evaluate_action(
            ActionRequest(action="send_transactional_message",external=True),
            repo_root=self.root,
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertFalse(decision.blocked_by_competitive_engine)

    def test_no_automatic_approval_for_source_reader_bootstrap(self):
        decision = evaluate_action(
            ActionRequest(action="call_approved_api",external=True),
            repo_root=self.root,
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertFalse(decision.blocked_by_competitive_engine)

    def test_active_root_pause_blocks_even_explicit_bootstrap(self):
        (self.root/"PAUSE_AUTONOMY").write_text("intentionally paused\n")
        for action in ("deploy_competitive_engine", "send_transactional_message",
                       "call_approved_api", "send_marketing_email"):
            with self.subTest(action=action):
                decision = evaluate_action(
                    ActionRequest(action=action,external=True),
                    approval=self.approval(action),repo_root=self.root,
                )
                self.assertFalse(decision.allowed)
                self.assertTrue(decision.blocked_by_pause)

    def test_outbound_aliases_require_engine_not_just_ceo_approval(self):
        for action in ("post_social_ad", "send_quote", "create_payment_link",
                       "accept_new_order", "charge_new_customer"):
            with self.subTest(action=action):
                outcome = evaluate_action(
                    ActionRequest(action=action, external=True, risk_level="high"),
                    approval=self.approval(action), repo_root=self.root,
                )
                self.assertFalse(outcome.allowed)
                self.assertTrue(outcome.blocked_by_competitive_engine)

    def test_empty_future_health_does_not_unlock_any_commercial_action(self):
        for action in NAMED_COMMERCIAL_ACTIONS:
            with self.subTest(action=action):
                decision = evaluate_action(
                    ActionRequest(action=action),
                    approval=self.approval(action),
                    repo_root=self.root,
                )
                self.assertFalse(decision.allowed)
                self.assertTrue(decision.blocked_by_competitive_engine)

    def test_development_release_hardlock_is_literal_false_on_disk(self):
        root = Path(__file__).resolve().parents[1]
        source = (root/"src"/"company_os"/"competitive_launch_guard.py").read_text()
        module = ast.parse(source)
        values = [
            a.value.value
            for a in module.body
            if isinstance(a,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=="PRODUCTION_RELEASE_CONTROLLER_CERTIFIED"
                    for t in a.targets)
            and isinstance(a.value,ast.Constant)
        ]
        self.assertEqual(values,[False])

    def test_repository_emergency_marker_exists_in_source_tree(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root/"PAUSE_AUTONOMY").is_file())

    def test_company_policy_still_imports_and_checks_competitive_precondition(self):
        root = Path(__file__).resolve().parents[1]
        source=(root/"src"/"company_os"/"policy.py").read_text()
        self.assertIn("inspect_venture_launch_prerequisite",source)
        self.assertIn("unknown_outbound_action",source)
        self.assertIn("requires_competitive_engine(request.action)",source)

    def test_bootstrap_only_exact_named_exemption(self):
        self.assertEqual(COMPETITIVE_ENGINE_BOOTSTRAP_ACTION,"deploy_competitive_engine")
        for attempt in ("deploy_competitive_engine_extra",
                        "deploy_competitive_engine_production",
                        "deploy_commercial_engine"):
            with self.subTest(action=attempt):
                self.assertTrue(requires_competitive_engine(attempt))

    def test_known_action_registry_contains_commercial_customer_release(self):
        for action in ("send_client_report","send_sales_proposal","send_quote",
                       "create_checkout","create_payment_link","advertise_business"):
            self.assertIn(action,COMPETITIVE_ENGINE_GATED_ACTIONS)


if __name__=="__main__":
    unittest.main()
