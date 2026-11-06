"""CE-4A end-to-end denied release checks. No live sources or external actions."""

from __future__ import annotations

import copy
import hashlib
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_work_queue import CompetitiveWorkQueue
from company_os.competitive_release_preflight import (
    ReleaseAttemptLedger, inspect_release_proposal,
)
from company_os.source_provenance import EvidenceError
import test_competitive_critic_review as critic_fixtures


class CompetitiveReleasePreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = critic_fixtures.CompetitiveCriticReviewTests(
            "test_all_twelve_signed_critic_checks_still_do_not_grant_authority"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        self.root=f.root
        self.now=f.now
        self.dossier=copy.deepcopy(f.dossier)
        self.pdf_path=f.pdf_path
        self.review_policy=f.policy_envelope()
        self.signed_review=f.review_envelope()
        self.queue=CompetitiveWorkQueue(self.root)
        self.addCleanup(self.queue.close)
        self.refusals=ReleaseAttemptLedger(self.root)
        self.addCleanup(self.refusals.close)
        self.queue.submit(self.dossier,now=self.now)
        leased=self.queue.lease(owner="internal-analyst",now=self.now)
        self.queue.complete(job_id=leased["job_id"],owner=leased["owner"],
                            generation=leased["generation"],now=self.now)
        f.ledger.accept_policy(self.review_policy,now=self.now)
        f.ledger.accept_review(
            self.dossier,f.artifact,self.review_policy,self.signed_review,
            artifact_pdf_path=self.pdf_path,now=self.now,
        )
        self.packet={
            "schema_version":"1.0",
            "request_id":"launch-check-001",
            "action":"launch_business",
            "venture_id":self.dossier["venture_id"],
            "dossier_id":self.dossier["dossier_id"],
            "dossier_sha256":hashlib.sha256(
                __import__("company_os.competitive_evidence_engine",fromlist=["canonical"])
                .canonical(self.dossier)
            ).hexdigest(),
            "artifact_sha256":f.artifact,
            "review_id":self.signed_review["review"]["review_id"],
            "recipient_id":"synthetic-recipient",
            "client_scope_id":"synthetic-client-scope",
            "privacy_review_id":"claimed-privacy-signoff",
            "legal_review_id":"claimed-legal-signoff",
            "client_consent_id":"claimed-client-consent",
            "requested_at":self.now.isoformat(),
            "estimated_cost_cents":0,
        }
        self.approval={
            "id":21,"status":"approved","action":"launch_business",
            "approval_class":"ceo_approval_required","estimated_cost_cents":0,
            "expires_at":(self.now+timedelta(hours=1)).isoformat(),
            "venture_id":self.packet["venture_id"],
            "dossier_sha256":self.packet["dossier_sha256"],
            "artifact_sha256":self.packet["artifact_sha256"],
            "recipient_id":self.packet["recipient_id"],
            "client_scope_id":self.packet["client_scope_id"],
        }

    def result(self,*,packet=None,dossier=None,review=None,policy=None,
               approval=None,pdf=None,queue=None,critic_audit=None):
        return inspect_release_proposal(
            packet if packet is not None else self.packet,
            dossier if dossier is not None else self.dossier,
            pdf if pdf is not None else self.pdf_path,
            policy if policy is not None else self.review_policy,
            review if review is not None else self.signed_review,
            queue if queue is not None else self.queue,
            critic_audit if critic_audit is not None else self.fixture.ledger,
            approval=approval if approval is not None else self.approval,
            repo_root=self.root,now=self.now,
        )

    def assert_refused(self,contains=None,**kwargs):
        value=self.result(**kwargs)
        self.assertEqual(value["status"],"BLOCK",value)
        self.assertFalse(value["release_authorized"])
        self.assertFalse(value["publication_authorized"])
        self.assertFalse(value["engine_production_accepted"])
        if contains:
            self.assertIn(contains," ".join(value["reasons"]))
        return value

    def test_even_perfectly_signed_synthetic_release_is_denied(self):
        refusal=self.assert_refused("production_release_hard_lock_active")
        self.assertIn("root_emergency_pause_active",refusal["reasons"])
        self.assertIn("real_independent_critic_inspection_not_operationally_proven",refusal["reasons"])
        self.assertIn("original_issuer_and_competitor_sources_not_independently_authenticated",refusal["reasons"])
        self.assertEqual(len(refusal["request_sha256"]),64)

    def test_valid_queued_dossier_snapshot_bound_to_exact_digest(self):
        verified=self.queue.verified_snapshot(self.packet["dossier_id"])
        self.assertEqual(verified["state"],"HELD_VERIFIED_DIGEST_ONLY")
        self.assertEqual(verified["dossier_sha256"],self.packet["dossier_sha256"])
        self.assertFalse(verified["publication_authorized"])

    def test_release_after_pause_flag_off_still_blocked(self):
        os.environ["COMPANY_OS_PAUSED"]="0"
        out=self.assert_refused("production_release_hard_lock_active")
        self.assertNotIn("root_emergency_pause_active",out["reasons"])
        self.assertIn("competitive_engine_or_company_policy_blocked",out["reasons"])

    def test_root_pause_file_has_priority_even_with_environment_off(self):
        (self.root/"PAUSE_AUTONOMY").write_text("intentionally paused")
        os.environ["COMPANY_OS_PAUSED"]="0"
        self.assert_refused("root_emergency_pause_active")

    def test_competing_venture_id_cannot_borrow_another_release(self):
        changed={**self.packet,"venture_id":"contractor-operations"}
        self.assert_refused("invalid_or_unsafe_release_packet",packet=changed)

    def test_dossier_digest_edit_is_refused(self):
        changed=copy.deepcopy(self.dossier)
        changed["buyer_problem"]="Different buyer record after queue submission"
        changed_packet={**self.packet,"dossier_sha256":hashlib.sha256(
            __import__("company_os.competitive_evidence_engine",fromlist=["canonical"])
            .canonical(changed)).hexdigest()}
        self.assert_refused("invalid_or_unsafe_release_packet",
                            packet=changed_packet,dossier=changed)

    def test_missing_or_fake_queued_job_is_refused(self):
        self.packet["dossier_id"]="nonexistent-job"
        self.assert_refused("invalid_or_unsafe_release_packet")

    def test_queue_item_not_yet_held_cannot_be_released(self):
        other=copy.deepcopy(self.dossier)
        other["dossier_id"]="other-job"
        self.queue.submit(other,now=self.now)
        packet={**self.packet,"dossier_id":"other-job","dossier_sha256":hashlib.sha256(
            __import__("company_os.competitive_evidence_engine",fromlist=["canonical"])
            .canonical(other)).hexdigest()}
        self.assert_refused("invalid_or_unsafe_release_packet",packet=packet,dossier=other)

    def test_corrupted_analysis_sha_blocks_at_source(self):
        self.queue.db.execute("UPDATE jobs SET output_sha='0'")
        self.assert_refused("invalid_or_unsafe_release_packet")

    def test_corrupted_original_queue_input_blocks_at_source(self):
        self.queue.db.execute("UPDATE jobs SET payload='{}'")
        self.assert_refused("invalid_or_unsafe_release_packet")

    def test_changed_pdf_blocks_critic_even_with_valid_metadata(self):
        original=self.pdf_path.read_bytes()
        self.pdf_path.write_bytes(original[:-1]+bytes([original[-1]^1]))
        self.assert_refused("signed_critic_review_invalid_or_outdated")

    def test_wrong_artifact_digest_causes_packet_to_fail(self):
        changed={**self.packet,"artifact_sha256":"f"*64}
        self.assert_refused("signed_critic_review_invalid_or_outdated",packet=changed)

    def test_wrong_signed_reviewer_dossier_version_blocks(self):
        modified=copy.deepcopy(self.signed_review)
        modified["review"]["dossier_sha256"]="f"*64
        self.assert_refused("signed_critic_review_invalid_or_outdated",review=modified)

    def test_review_replayed_without_recorded_critic_audit_blocks(self):
        from company_os.competitive_critic_audit import CriticReviewLedger
        with tempfile.TemporaryDirectory() as fresh:
            audit=CriticReviewLedger(fresh)
            try:
                self.assert_refused("critic_review_audit_missing_or_untrusted",critic_audit=audit)
            finally:
                audit.close()

    def test_revoked_critic_review_blocks_correct_previous_digest(self):
        self.fixture.policy["revision"]=2
        self.fixture.policy["revoked_review_ids"]=[self.packet["review_id"]]
        new=self.fixture.policy_envelope()
        self.fixture.ledger.accept_policy(new,now=self.now)
        self.assert_refused("signed_critic_review_invalid_or_outdated",policy=new)

    def test_wrong_recipient_does_not_inherit_ceo_scope(self):
        changed={**self.packet,"recipient_id":"different-recipient"}
        self.assert_refused("ceo_approval_scope_or_digest_mismatch",packet=changed)

    def test_changed_client_scope_does_not_inherit_ceo_permission(self):
        changed={**self.packet,"client_scope_id":"changed-scope"}
        self.assert_refused("ceo_approval_scope_or_digest_mismatch",packet=changed)

    def test_authorization_missing_exact_approval_is_denied(self):
        out=inspect_release_proposal(
            self.packet,self.dossier,self.pdf_path,
            self.review_policy,self.signed_review,self.queue,self.fixture.ledger,
            approval=None,repo_root=self.root,now=self.now,
        )
        self.assertIn("exact_ceo_release_approval_not_present",out["reasons"])
        self.assertFalse(out["release_authorized"])

    def test_action_cost_mismatch_does_not_qualify_as_approval(self):
        changed={**self.packet,"estimated_cost_cents":499}
        self.assert_refused("ceo_approval_metadata_invalid_or_expired",packet=changed)

    def test_unguarded_unknown_release_action_is_rejected(self):
        changed={**self.packet,"action":"internal_analysis"}
        self.assert_refused("invalid_or_unsafe_release_packet",packet=changed)

    def test_valid_publish_like_alias_still_refused_by_policy(self):
        changed={**self.packet,"action":"publish_client_report"}
        approval={**self.approval,"action":"publish_client_report"}
        out=self.result(packet=changed,approval=approval)
        self.assertEqual(out["status"],"BLOCK")
        self.assertFalse(out["release_authorized"])

    def test_invalid_cost_type_rejected(self):
        changed={**self.packet,"estimated_cost_cents":True}
        self.assert_refused("invalid_or_unsafe_release_packet",packet=changed)

    def test_stale_or_future_release_packet_rejected(self):
        for time in (self.now-timedelta(hours=3),self.now+timedelta(hours=1)):
            changed={**self.packet,"requested_at":time.isoformat()}
            with self.subTest(when=time):
                self.assert_refused("invalid_or_unsafe_release_packet",packet=changed)

    def test_review_refusal_audit_records_no_customer_data(self):
        refusal=self.result()
        save=self.refusals.record_refusal(refusal,now=self.now)
        self.assertEqual(save["state"],"DENIAL_LOGGED_LOCALLY")
        data=self.refusals.audit()
        self.assertEqual(data["refusals"],1)
        self.assertFalse(data["publication_authorized"])
        blob=self.refusals.path.read_bytes()
        self.assertNotIn(b"synthetic-recipient",blob)
        self.assertNotIn(b"synthetic-client-scope",blob)

    def test_can_only_record_a_denial_not_approvals(self):
        with self.assertRaises(EvidenceError):
            self.refusals.record_refusal({
                "status":"ALLOW","release_authorized":True,
                "publication_authorized":True,"reasons":[],
            },now=self.now)

    def test_refusal_log_tamper_is_detected(self):
        self.refusals.record_refusal(self.result(),now=self.now)
        self.refusals.db.execute("DROP TRIGGER deny_release_update")
        self.refusals.db.execute("UPDATE refusals SET event_sha='0' WHERE seq=1")
        with self.assertRaises(EvidenceError):
            self.refusals.audit()

    def test_refusal_database_delete_and_update_prevented(self):
        self.refusals.record_refusal(self.result(),now=self.now)
        for sql in (
            "DELETE FROM refusals WHERE seq=1",
            "UPDATE refusals SET event_sha='0' WHERE seq=1",
        ):
            with self.subTest(sql=sql),self.assertRaises(sqlite3.DatabaseError):
                self.refusals.db.execute(sql)

    def test_release_controller_module_has_no_external_action_method(self):
        import company_os.competitive_release_preflight as module
        self.assertFalse(hasattr(module,"publish"))
        self.assertFalse(hasattr(module,"send_email"))
        self.assertFalse(hasattr(module,"launch_business"))
        self.assertFalse(hasattr(module,"deploy_competitive_engine"))

    def test_all_business_launch_aliases_in_gate_are_denied(self):
        for action in ("launch_business","launch_venture","launch_product",
                       "activate_business","publish_authorized","deploy_authorized",
                       "go_live_service","start_revenue_operations"):
            with self.subTest(action=action):
                changed={**self.packet,"action":action}
                result=self.result(packet=changed)
                self.assertEqual(result["status"],"BLOCK")
                self.assertFalse(result["publication_authorized"])


if __name__=="__main__":
    unittest.main()
