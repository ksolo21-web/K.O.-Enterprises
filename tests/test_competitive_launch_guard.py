"""Adversarial tests for the mandatory, signed competitive-engine launch gate."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_launch_guard import (
    REQUIRED_CRITIC_CHECKS,
    REQUIRED_LIVE_CHECKS,
    inspect_competitive_readiness,
    requires_competitive_engine,
)
from company_os.policy import (
    ActionRequest, ApprovalClass, PauseActive, PolicyViolation,
    enforce_action, evaluate_action,
)

HEALTH_KEY = "test-engine-key-" + "h" * 48
CRITIC_KEY = "test-critic-key-" + "c" * 48


class CompetitiveLaunchGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "state" / "competitive_engine" / "readiness.json"
        self.file.parent.mkdir(parents=True)
        self.time = datetime.now(timezone.utc).replace(microsecond=0)
        self.env = patch.dict(
            os.environ,
            {
                "COMPANY_OS_PAUSED": "0",
                "KO_COMPETITIVE_ENGINE_HEALTH_KEY": HEALTH_KEY,
                "KO_COMPETITIVE_CRITIC_HEALTH_KEY": CRITIC_KEY,
                "KO_COMPETITIVE_READINESS_PATH": str(self.file),
            },
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def payload(self) -> dict:
        n = self.time
        return {
            "schema_version": "1.0",
            "engine_id": "ko-competitive-engine",
            "cycle_id": "cycle-001",
            "revision": "abc123def456",
            "producer_id": "protected-live-service-a",
            "reviewer_id": "independent-review-service-b",
            "environment": "production",
            "state": "live_healthy",
            "observed_at": (n - timedelta(seconds=30)).isoformat(),
            "expires_at": (n + timedelta(minutes=4)).isoformat(),
            "sources_verified_at": (n - timedelta(hours=1)).isoformat(),
            "critic_reviewed_at": (n - timedelta(minutes=20)).isoformat(),
            "live_checks": {name: True for name in REQUIRED_LIVE_CHECKS},
            "critic_checks": {name: True for name in REQUIRED_CRITIC_CHECKS},
            "critic_score": 9.5,
            "critical_findings_open": 0,
            "verified_primary_source_count": 12,
            "completed_comparison_count": 3,
        }

    def write_signed(self, payload: dict | None = None) -> dict:
        payload = self.payload() if payload is None else payload
        signed = json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode()
        envelope = {
            "payload": payload,
            "engine_signature": hmac.new(
                HEALTH_KEY.encode(), signed, hashlib.sha256
            ).hexdigest(),
            "critic_signature": hmac.new(
                CRITIC_KEY.encode(), signed, hashlib.sha256
            ).hexdigest(),
        }
        self.file.write_text(json.dumps(envelope), encoding="utf-8")
        return envelope

    def approved(self, action: str, cls: str = "ceo_approval_required") -> dict:
        return {
            "id": 7, "action": action, "approval_class": cls,
            "status": "approved", "estimated_cost_cents": 0,
            "expires_at": (self.time + timedelta(hours=1)).isoformat(),
        }

    def test_missing_health_blocks_every_kind_of_business_launch(self):
        for action in (
            "launch_business", "launch_venture", "launch_product",
            "activate_business", "start_revenue_operations",
            "deploy_authorized", "publish_authorized",
            "publish_regulated_claim", "go_live_service", "launch_new_vertical",
        ):
            with self.subTest(action=action):
                decision = evaluate_action(
                    ActionRequest(action=action),
                    approval=self.approved(action, (
                        "policy_gated" if action in ("deploy_authorized", "publish_authorized")
                        else "ceo_approval_required"
                    )),
                    repo_root=self.root,
                )
                self.assertFalse(decision.allowed)
                self.assertTrue(decision.blocked_by_competitive_engine)
                self.assertIn("health", decision.reason)
                with self.assertRaises(PolicyViolation):
                    enforce_action(ActionRequest(action=action), repo_root=self.root)

    def test_signed_current_health_and_ceo_approval_allows_launch_preflight(self):
        self.write_signed()
        health = inspect_competitive_readiness(self.root, now=self.time)
        self.assertTrue(health.ready, health.reasons)
        blocked = evaluate_action(
            ActionRequest(action="launch_business"),
            approval=self.approved("launch_business"),
            repo_root=self.root,
        )
        self.assertFalse(blocked.allowed)
        self.assertTrue(blocked.blocked_by_competitive_engine)
        self.assertIn("production_release_controller_not_certified", blocked.reason)
        # Simulates FUTURE certified controller only; not production authority.
        with patch("company_os.competitive_launch_guard.PRODUCTION_RELEASE_CONTROLLER_CERTIFIED", True):
            decision = evaluate_action(
                ActionRequest(action="launch_business"),
                approval=self.approved("launch_business"),
                repo_root=self.root,
            )
        self.assertTrue(decision.allowed)
        self.assertEqual(7, decision.approval_id)

    def test_healthy_engine_does_not_grant_authority(self):
        self.write_signed()
        # Simulate a separately certified release controller in isolation.
        # Without this simulation, the stronger development hard stop wins.
        with patch("company_os.competitive_launch_guard.PRODUCTION_RELEASE_CONTROLLER_CERTIFIED", True):
            decision = evaluate_action(
                ActionRequest(action="launch_business"), repo_root=self.root
            )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)

    def test_emergency_pause_overrides_signed_health_and_approval(self):
        self.write_signed()
        (self.root / "PAUSE_AUTONOMY").write_text("pause\n")
        decision = evaluate_action(
            ActionRequest(action="launch_business"),
            approval=self.approved("launch_business"), repo_root=self.root
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.blocked_by_pause)
        with self.assertRaises(PauseActive):
            enforce_action(
                ActionRequest(action="launch_business"),
                approval=self.approved("launch_business"), repo_root=self.root,
            )

    def test_engine_bootstrap_has_no_circular_engine_dependency(self):
        self.assertFalse(requires_competitive_engine("deploy_competitive_engine"))
        request = ActionRequest(action="deploy_competitive_engine")
        decision = evaluate_action(
            request, approval=self.approved("deploy_competitive_engine"),
            repo_root=self.root,
        )
        self.assertTrue(decision.allowed)
        (self.root / "PAUSE_AUTONOMY").write_text("paused\n")
        self.assertTrue(evaluate_action(
            request, approval=self.approved("deploy_competitive_engine"),
            repo_root=self.root,
        ).blocked_by_pause)

    def test_internal_work_not_blocked_by_engine(self):
        self.assertTrue(enforce_action(
            ActionRequest(action="write_code"), repo_root=self.root
        ).allowed)

    def test_missing_keys_or_same_key_fails_closed(self):
        self.write_signed()
        del os.environ["KO_COMPETITIVE_CRITIC_HEALTH_KEY"]
        self.assertFalse(inspect_competitive_readiness(self.root, now=self.time).ready)
        os.environ["KO_COMPETITIVE_CRITIC_HEALTH_KEY"] = HEALTH_KEY
        self.assertFalse(inspect_competitive_readiness(self.root, now=self.time).ready)

    def test_signature_tampering_is_detected(self):
        envelope = self.write_signed()
        envelope["payload"]["critical_findings_open"] = 0
        envelope["payload"]["completed_comparison_count"] = 900
        self.file.write_text(json.dumps(envelope))
        result = inspect_competitive_readiness(self.root, now=self.time)
        self.assertFalse(result.ready)
        self.assertIn("engine_attestation_signature_invalid", result.reasons)

    def test_forged_critic_signature_is_blocked(self):
        envelope = self.write_signed()
        envelope["critic_signature"] = envelope["engine_signature"]
        self.file.write_text(json.dumps(envelope))
        result = inspect_competitive_readiness(self.root, now=self.time)
        self.assertIn("critic_attestation_signature_invalid", result.reasons)

    def test_duplicate_json_keys_blocked(self):
        self.file.write_text(
            '{"payload":{},"payload":{},"engine_signature":"x","critic_signature":"y"}'
        )
        result = inspect_competitive_readiness(self.root, now=self.time)
        self.assertIn("health_record_invalid", result.reasons)

    def test_malformed_or_oversized_health_blocked(self):
        for content in ("broken", "{" + " " * 70_000 + "}"):
            with self.subTest(length=len(content)):
                self.file.write_text(content)
                self.assertFalse(inspect_competitive_readiness(
                    self.root, now=self.time
                ).ready)

    def test_stale_heartbeat_is_blocked(self):
        p = self.payload()
        p["observed_at"] = (self.time - timedelta(minutes=6)).isoformat()
        self.write_signed(p)
        self.assertIn("heartbeat_missing_or_stale", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_future_heartbeat_is_blocked(self):
        p = self.payload()
        p["observed_at"] = (self.time + timedelta(hours=1)).isoformat()
        self.write_signed(p)
        self.assertIn("heartbeat_missing_or_stale", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_expired_record_is_blocked(self):
        p = self.payload()
        p["expires_at"] = (self.time - timedelta(seconds=1)).isoformat()
        self.write_signed(p)
        self.assertIn("health_expired_or_overlong", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_overlong_expiry_is_blocked(self):
        p = self.payload()
        p["expires_at"] = (self.time + timedelta(days=365)).isoformat()
        self.write_signed(p)
        self.assertIn("health_expired_or_overlong", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_stale_original_source_check_is_blocked(self):
        p = self.payload()
        p["sources_verified_at"] = (self.time - timedelta(days=2)).isoformat()
        self.write_signed(p)
        self.assertIn("source_verification_stale", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_stale_independent_critic_is_blocked(self):
        p = self.payload()
        p["critic_reviewed_at"] = (self.time - timedelta(hours=4)).isoformat()
        self.write_signed(p)
        self.assertIn("independent_review_stale", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_incomplete_live_check_is_blocked(self):
        p = self.payload()
        p["live_checks"]["monitor_probe_passed"] = False
        self.write_signed(p)
        self.assertIn("live_mandatory_checks_incomplete", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_all_critic_checks_are_mandatory(self):
        p = self.payload()
        p["critic_checks"].pop("visual_pages")
        self.write_signed(p)
        self.assertIn("critic_mandatory_checks_incomplete", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_score_must_be_strictly_above_nine(self):
        for score in (9, 9.0, 11.0, False, "9.8"):
            with self.subTest(score=score):
                p = self.payload()
                p["critic_score"] = score
                self.write_signed(p)
                self.assertIn("critic_score_below_strict_threshold", inspect_competitive_readiness(
                    self.root, now=self.time
                ).reasons)

    def test_open_critical_finding_always_blocks(self):
        p = self.payload()
        p["critical_findings_open"] = 1
        self.write_signed(p)
        self.assertIn("open_or_unknown_critical_findings", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_missing_actual_source_and_comparison_blocks(self):
        for field in ("verified_primary_source_count", "completed_comparison_count"):
            p = self.payload()
            p[field] = 0
            self.write_signed(p)
            self.assertFalse(inspect_competitive_readiness(
                self.root, now=self.time
            ).ready)

    def test_self_review_is_disallowed_even_if_signed(self):
        p = self.payload()
        p["reviewer_id"] = p["producer_id"]
        self.write_signed(p)
        self.assertIn("self_review_not_accepted", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_development_health_is_not_production(self):
        p = self.payload()
        p["environment"] = "test"
        self.write_signed(p)
        self.assertIn("engine_not_live_in_production", inspect_competitive_readiness(
            self.root, now=self.time
        ).reasons)

    def test_publish_authorization_needs_competitive_gate_and_approval(self):
        self.write_signed()
        action = "publish_authorized"
        blocked = evaluate_action(
            ActionRequest(action=action),
            approval=self.approved(action, "policy_gated"),
            repo_root=self.root,
        )
        self.assertFalse(blocked.allowed)
        self.assertTrue(blocked.blocked_by_competitive_engine)
        # Simulate a certified external release controller in isolation.
        with patch("company_os.competitive_launch_guard.PRODUCTION_RELEASE_CONTROLLER_CERTIFIED", True):
            decision = evaluate_action(
                ActionRequest(action=action),
                approval=self.approved(action, "policy_gated"),
                repo_root=self.root,
            )
        self.assertTrue(decision.allowed)

    def test_launch_action_synonyms_are_gated_without_external_flag(self):
        for action in (
            "launch_business", "go_live_marketplace", "deploy_product",
            "publish_offer", "start_revenue_cycle", "activate_venture",
        ):
            self.assertTrue(requires_competitive_engine(action))

    def test_health_check_does_not_create_state_or_make_network_request(self):
        result = inspect_competitive_readiness(self.root, now=self.time)
        self.assertFalse(result.ready)
        self.assertFalse(self.file.exists())


if __name__ == "__main__":
    unittest.main()
