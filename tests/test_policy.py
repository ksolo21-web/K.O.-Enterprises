"""Fail-closed tests for pause and human-approval boundaries."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.errors import ValidationError
from company_os.policy import (
    ActionRequest,
    ApprovalClass,
    ApprovalRequired,
    PauseActive,
    classify_action,
    enforce_action,
    evaluate_action,
    is_paused,
)


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, {}, clear=True)
        self._env.start()
        self.addCleanup(self._env.stop)

    def _approved(
        self,
        action: str,
        approval_class: ApprovalClass,
        *,
        cost_cents: int = 0,
    ) -> dict[str, object]:
        return {
            "id": 17,
            "action": action,
            "approval_class": approval_class.value,
            "status": "approved",
            "estimated_cost_cents": cost_cents,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

    def test_repository_marker_pauses_external_and_scheduled_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")

            external = evaluate_action(
                ActionRequest(action="publish_authorized", external=True),
                repo_root=root,
            )
            scheduled = evaluate_action(
                ActionRequest(action="generate_report", scheduled=True),
                repo_root=root,
            )

        self.assertFalse(external.allowed)
        self.assertTrue(external.blocked_by_pause)
        self.assertFalse(scheduled.allowed)
        self.assertTrue(scheduled.blocked_by_pause)

    def test_pause_does_not_block_safe_internal_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
            decision = enforce_action(
                ActionRequest(action="write_code", reversible=True),
                repo_root=root,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(ApprovalClass.AUTO_ALLOWED, decision.approval_class)

    def test_environment_pause_is_an_independent_stop_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["COMPANY_OS_PAUSED"] = "yes"
            self.assertTrue(is_paused(directory))
            with self.assertRaises(PauseActive):
                enforce_action(
                    ActionRequest(action="call_approved_api", external=True),
                    approval=self._approved(
                        "call_approved_api", ApprovalClass.POLICY_GATED
                    ),
                    repo_root=directory,
                )

    def test_unknown_pause_environment_value_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["COMPANY_OS_PAUSED"] = "treu"
            self.assertTrue(is_paused(directory))

    def test_approval_never_overrides_active_pause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
            decision = evaluate_action(
                ActionRequest(
                    action="spend_money",
                    external=True,
                    estimated_cost_cents=500,
                ),
                approval=self._approved(
                    "spend_money",
                    ApprovalClass.CEO_APPROVAL_REQUIRED,
                    cost_cents=500,
                ),
                repo_root=root,
            )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.blocked_by_pause)
        self.assertIsNone(decision.approval_id)

    def test_pause_cannot_be_bypassed_by_omitting_external_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
            request = ActionRequest(
                action="spend_money",
                estimated_cost_cents=500,
                # Deliberately leave external=False to exercise fail-closed
                # classification rather than trusting a caller-controlled flag.
            )
            decision = evaluate_action(
                request,
                approval=self._approved(
                    "spend_money",
                    ApprovalClass.CEO_APPROVAL_REQUIRED,
                    cost_cents=500,
                ),
                repo_root=root,
            )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.blocked_by_pause)
        self.assertEqual(
            ApprovalClass.CEO_APPROVAL_REQUIRED,
            decision.approval_class,
        )
        self.assertIsNone(decision.approval_id)

    def test_spend_sensitive_data_and_irreversibility_force_ceo_gate(self) -> None:
        requests = (
            ActionRequest(action="internal_analysis", estimated_cost_cents=1),
            ActionRequest(action="internal_analysis", handles_sensitive_data=True),
            ActionRequest(action="internal_analysis", reversible=False),
            ActionRequest(action="internal_analysis", expands_permissions=True),
        )
        for request in requests:
            with self.subTest(request=request):
                self.assertEqual(
                    ApprovalClass.CEO_APPROVAL_REQUIRED,
                    classify_action(request),
                )

    def test_action_cost_requires_integer_cents(self) -> None:
        for invalid in (True, 1.5, "100"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    ActionRequest(
                        action="spend_money",
                        estimated_cost_cents=invalid,  # type: ignore[arg-type]
                    )

    def test_unknown_action_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            requests = (
                ActionRequest(action="do_something_new"),
                ActionRequest(action="do_something_new", external=True),
                ActionRequest(action="do_something_new", scheduled=True),
            )
            for request in requests:
                with self.subTest(request=request):
                    decision = evaluate_action(request, repo_root=directory)
                    self.assertFalse(decision.allowed)
                    self.assertTrue(decision.approval_required)
                    self.assertEqual(
                        ApprovalClass.CEO_APPROVAL_REQUIRED,
                        decision.approval_class,
                    )
                    with self.assertRaises(ApprovalRequired):
                        enforce_action(request, repo_root=directory)

    def test_requested_class_can_escalate_but_never_downgrade_policy(self) -> None:
        unknown_claiming_auto = ActionRequest(
            action="do_something_new",
            requested_class=ApprovalClass.AUTO_ALLOWED,
        )
        external_claiming_auto = ActionRequest(
            action="publish_authorized",
            external=True,
            requested_class=ApprovalClass.AUTO_ALLOWED,
        )
        internal_escalated = ActionRequest(
            action="internal_analysis",
            requested_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
        )

        self.assertEqual(
            ApprovalClass.CEO_APPROVAL_REQUIRED,
            classify_action(unknown_claiming_auto),
        )
        self.assertEqual(
            ApprovalClass.POLICY_GATED,
            classify_action(external_claiming_auto),
        )
        self.assertEqual(
            ApprovalClass.CEO_APPROVAL_REQUIRED,
            classify_action(internal_escalated),
        )

    def test_matching_unexpired_approval_covers_only_approved_cost(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = ActionRequest(
                action="spend_money",
                estimated_cost_cents=500,
            )
            approval = self._approved(
                "spend_money",
                ApprovalClass.CEO_APPROVAL_REQUIRED,
                cost_cents=500,
            )
            allowed = evaluate_action(request, approval=approval, repo_root=directory)
            over_limit = evaluate_action(
                ActionRequest(action="spend_money", estimated_cost_cents=501),
                approval=approval,
                repo_root=directory,
            )

        self.assertTrue(allowed.allowed)
        self.assertEqual(17, allowed.approval_id)
        self.assertFalse(over_limit.allowed)
        self.assertTrue(over_limit.approval_required)

    def test_expired_or_wrong_action_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = ActionRequest(action="spend_money", estimated_cost_cents=100)
            expired = self._approved(
                "spend_money",
                ApprovalClass.CEO_APPROVAL_REQUIRED,
                cost_cents=100,
            )
            expired["expires_at"] = (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            ).isoformat()
            wrong_action = self._approved(
                "purchase_domain",
                ApprovalClass.CEO_APPROVAL_REQUIRED,
                cost_cents=100,
            )

            self.assertFalse(
                evaluate_action(request, approval=expired, repo_root=directory).allowed
            )
            self.assertFalse(
                evaluate_action(
                    request, approval=wrong_action, repo_root=directory
                ).allowed
            )

    def test_malformed_approval_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = ActionRequest(action="spend_money", estimated_cost_cents=100)
            for field, malformed in (
                ("estimated_cost_cents", "not-an-integer"),
                ("estimated_cost_cents", True),
                ("estimated_cost_cents", 100.0),
                ("expires_at", "not-a-timestamp"),
                ("id", "not-an-id"),
                ("id", True),
            ):
                approval = self._approved(
                    "spend_money",
                    ApprovalClass.CEO_APPROVAL_REQUIRED,
                    cost_cents=100,
                )
                approval[field] = malformed
                with self.subTest(field=field):
                    decision = evaluate_action(
                        request,
                        approval=approval,
                        repo_root=directory,
                    )
                    self.assertFalse(decision.allowed)
                    self.assertTrue(decision.approval_required)


if __name__ == "__main__":
    unittest.main()
