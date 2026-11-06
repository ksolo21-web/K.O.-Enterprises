"""CE-3A cryptographic critic-review adversarial tests. All identities synthetic."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.competitive_critic_review import (
    POLICY_DOMAIN, REVIEW_DOMAIN, assess_signed_review,
    canonical, inspect_review_policy, inspect_signed_critic_review,
)
from company_os.competitive_critic_audit import CriticReviewLedger
from company_os.competitive_launch_guard import REQUIRED_CRITIC_CHECKS
from company_os.source_provenance import EvidenceError
import test_competitive_engine_pipeline as fixture_support


class CompetitiveCriticReviewTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dossier = fixture_support.synthetic_dossier(self.now)
        self.artifact = hashlib.sha256(b"synthetic PDF generated in offline test").hexdigest()
        self.root_key = Ed25519PrivateKey.generate()
        self.reviewer_key = Ed25519PrivateKey.generate()
        self.environment = patch.dict(os.environ, {
            "KO_CRITIC_ROOT_PUBLIC_KEY_B64": base64.b64encode(
                self.root_key.public_key().public_bytes_raw()
            ).decode(),
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "COMPANY_OS_PAUSED": "1",
        }, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.policy = {
            "schema_version": "1.0",
            "policy_id": "ko-critic-auth-001", "revision": 1,
            "issued_at": (self.now-timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now+timedelta(days=1)).isoformat(),
            "reviewers": [{
                "reviewer_id": "critic-001", "key_id": "critic-key-001",
                "public_key_b64": base64.b64encode(
                    self.reviewer_key.public_key().public_bytes_raw()
                ).decode(),
                "venture_ids": ["market-intelligence"],
                "valid_from": (self.now-timedelta(days=1)).isoformat(),
                "valid_until": (self.now+timedelta(days=20)).isoformat(),
            }],
            "revoked_key_ids": [], "revoked_review_ids": [],
        }
        self.review = {
            "schema_version": "1.0",
            "review_id": "review-001",
            "reviewer_id": "critic-001", "reviewer_key_id": "critic-key-001",
            "author_id": self.dossier["author_id"],
            "venture_id": self.dossier["venture_id"],
            "dossier_id": self.dossier["dossier_id"],
            "dossier_sha256": hashlib.sha256(
                canonical(self.dossier)
            ).hexdigest(),
            "artifact_sha256": self.artifact,
            "completed_at": self.now.isoformat(),
            "expires_at": (self.now+timedelta(minutes=30)).isoformat(),
            "score": 9.75,
            "checks": {c: True for c in REQUIRED_CRITIC_CHECKS},
            "source_inspections": [{
                "source_id": row["id"], "sha256": row["sha256"],
                "inspected_at": self.now.isoformat(),
                "method": "reviewer_claimed_original_review",
            } for row in self.dossier["sources"]],
            "page_inspections": [{
                "document_sha256": self.artifact, "page_number": 1,
                "screenshot_sha256": "a"*64,
            }, {
                "document_sha256": self.artifact, "page_number": 2,
                "screenshot_sha256": "b"*64,
            }],
            "critical_findings": 0,
            "unresolved_objections": [],
            "reviewer_notes": (
                "These are synthetic reviewer assertions; no real original "
                "source, rendered PDF, or independent human was inspected."
            ),
            "independent_identity_attested": True,
        }
        self.ledger = CriticReviewLedger(self.root)
        self.addCleanup(self.ledger.close)

    def policy_envelope(self):
        policy = copy.deepcopy(self.policy)
        return {
            "policy": policy,
            "signature": base64.b64encode(
                self.root_key.sign(POLICY_DOMAIN + canonical(policy))
            ).decode(),
        }

    def review_envelope(self, key=None):
        review = copy.deepcopy(self.review)
        return {
            "review": review,
            "signature": base64.b64encode(
                (key or self.reviewer_key).sign(REVIEW_DOMAIN + canonical(review))
            ).decode(),
        }

    def assess(self, *, report=None, policy=None, dossier=None, artifact=None):
        return assess_signed_review(
            dossier or self.dossier, artifact or self.artifact,
            policy or self.policy_envelope(),
            report or self.review_envelope(), now=self.now,
        )

    def assert_block(self, phrase=None, **kwargs):
        verdict=self.assess(**kwargs)
        self.assertEqual(verdict["state"],"BLOCK",verdict)
        self.assertFalse(verdict["external_publication_authorized"])
        if phrase:
            self.assertIn(phrase.lower(),str(verdict["errors"]).lower())
        return verdict

    def test_all_twelve_signed_critic_checks_still_do_not_grant_authority(self):
        verdict=self.assess()
        self.assertEqual(
            verdict["state"],"SIGNED_REVIEW_METADATA_VALID_EXTERNAL_INDEPENDENCE_UNVERIFIED"
        )
        self.assertFalse(verdict["original_source_truth_independently_verified"])
        self.assertFalse(verdict["reviewer_independence_operationally_proven"])
        self.assertFalse(verdict["external_publication_authorized"])
        self.assertFalse(verdict["production_engine_ready"])
        self.assertEqual(verdict["mandatory_checks_true"],12)
        self.assertEqual(verdict["signed_source_inspections"],5)
        self.assertEqual(verdict["reviewer_claimed_visual_pages"],2)

    def test_wrong_root_key_rejected(self):
        os.environ["KO_CRITIC_ROOT_PUBLIC_KEY_B64"] = base64.b64encode(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        ).decode()
        self.assert_block("signature")

    def test_missing_independent_root_key_rejected(self):
        os.environ.pop("KO_CRITIC_ROOT_PUBLIC_KEY_B64")
        self.assert_block()

    def test_tampered_root_policy_rejected(self):
        p=self.policy_envelope()
        p["policy"]["revision"]=2
        self.assert_block(report=self.review_envelope(),policy=p)

    def test_rogue_critic_private_key_rejected(self):
        rogue=Ed25519PrivateKey.generate()
        self.assert_block(report=self.review_envelope(rogue))

    def test_tampered_signed_reviewer_payload_rejected(self):
        r=self.review_envelope()
        r["review"]["score"]=10.0
        self.assert_block(report=r)

    def test_author_cannot_sign_self_review(self):
        self.review["reviewer_id"] = self.dossier["author_id"]
        self.assert_block("unknown")

    def test_reviewer_and_author_must_be_distinct(self):
        self.dossier["author_id"]="critic-001"
        self.review["author_id"]="critic-001"
        self.review["dossier_sha256"]=hashlib.sha256(canonical(self.dossier)).hexdigest()
        self.assert_block("self-review")

    def test_score_exactly_nine_is_not_a_pass(self):
        self.review["score"]=9.0
        self.assert_block("greater than 9.0")

    def test_boolean_score_is_invalid(self):
        self.review["score"]=True
        self.assert_block("greater than 9.0")

    def test_score_above_ten_is_invalid(self):
        self.review["score"]=10.01
        self.assert_block("greater than 9.0")

    def test_one_of_twelve_missing_blocks(self):
        self.review["checks"].pop("visual_pages")
        self.assert_block("twelve")

    def test_any_failed_mandatory_check_blocks(self):
        self.review["checks"]["privacy"]=False
        self.assert_block("twelve")

    def test_critical_findings_block_even_ten_score(self):
        self.review["score"]=10.0
        self.review["critical_findings"]=1
        self.assert_block("findings")

    def test_unresolved_objection_blocks(self):
        self.review["unresolved_objections"]=["unresolved PDF contradiction"]
        self.assert_block("objections")

    def test_missing_source_review_record_blocks(self):
        self.review["source_inspections"].pop()
        self.assert_block("cover exact")

    def test_source_hash_mismatch_blocks(self):
        self.review["source_inspections"][0]["sha256"]="f"*64
        self.assert_block("cover exact")

    def test_claimed_source_method_not_authentic_for_this_schema(self):
        self.review["source_inspections"][0]["method"]="automatic_verified_issuer"
        self.assert_block("method")

    def test_older_source_inspection_is_invalid(self):
        self.review["source_inspections"][0]["inspected_at"]=(
            self.now-timedelta(hours=2)
        ).isoformat()
        self.assert_block("inspection")

    def test_report_edit_invalidates_review_digest(self):
        mutated_artifact=hashlib.sha256(b"edited PDF after review").hexdigest()
        self.assert_block("another report",artifact=mutated_artifact)

    def test_dossier_edit_invalidates_review(self):
        changed=copy.deepcopy(self.dossier)
        changed["buyer_problem"]="Changed customer hypothesis after review"
        self.assert_block("another report",dossier=changed)

    def test_expired_review_blocks(self):
        self.review["expires_at"]=(self.now-timedelta(seconds=1)).isoformat()
        self.assert_block("stale")

    def test_stale_review_blocks(self):
        self.review["completed_at"]=(self.now-timedelta(hours=2)).isoformat()
        self.assert_block("stale")

    def test_reviewer_venture_outside_approved_scope_blocks(self):
        self.policy["reviewers"][0]["venture_ids"]=["contractor-operations"]
        self.assert_block("unauthorized venture")

    def test_revoked_reviewer_key_blocks(self):
        self.policy["revoked_key_ids"]=["critic-key-001"]
        self.assert_block("revoked")

    def test_revoked_review_id_blocks(self):
        self.policy["revoked_review_ids"]=["review-001"]
        self.assert_block("revoked")

    def test_incomplete_visual_page_inspection_blocks(self):
        self.review["page_inspections"]=self.review["page_inspections"][1:]
        self.assert_block("every page")

    def test_duplicate_visual_page_blocks(self):
        self.review["page_inspections"][1]["page_number"]=1
        self.assert_block("duplicate")

    def test_wrong_pdf_page_digest_blocks(self):
        self.review["page_inspections"][0]["document_sha256"]="f"*64
        self.assert_block("different output")

    def test_missing_reviewer_reasoning_blocks(self):
        self.review["reviewer_notes"]="great"
        self.assert_block("reasoning")

    def test_critic_current_policy_can_be_recorded_with_no_release(self):
        result=self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.assertEqual(result["state"],"POLICY_RECORDED_LOCAL_ONLY")
        self.assertFalse(result["external_publication_authorized"])

    def test_critic_review_registered_only_as_local_attestation(self):
        p=self.policy_envelope()
        self.ledger.accept_policy(p,now=self.now)
        r=self.ledger.accept_review(self.dossier,self.artifact,p,self.review_envelope(),now=self.now)
        self.assertEqual(r["state"],"REVIEW_ATTESTATION_RECORDED_LOCAL_ONLY")
        self.assertFalse(r["external_publication_authorized"])
        self.assertEqual(self.ledger.audit_status()["entries"],2)
        self.assertEqual(
            self.ledger.review_status("review-001",p,now=self.now)["state"],
            "SIGNED_ONLY_EXTERNAL_REVIEW_NOT_PROVEN",
        )

    def test_cannot_accept_same_review_id_twice(self):
        p=self.policy_envelope()
        self.ledger.accept_policy(p,now=self.now)
        self.ledger.accept_review(self.dossier,self.artifact,p,self.review_envelope(),now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_review(self.dossier,self.artifact,p,self.review_envelope(),now=self.now)

    def test_review_cannot_be_accepted_without_active_policy(self):
        with self.assertRaises(EvidenceError):
            self.ledger.accept_review(self.dossier,self.artifact,
                                      self.policy_envelope(),self.review_envelope(),now=self.now)

    def test_policy_rollback_and_revision_collision_block(self):
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.policy["revision"]=2
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.policy["revision"]=1
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.policy["revision"]=2
        self.policy["revoked_review_ids"]=["review-001"]
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.policy_envelope(),now=self.now)

    def test_reviewer_key_revocation_is_permanent_across_policy_versions(self):
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.policy["revision"]=2
        self.policy["revoked_key_ids"]=["critic-key-001"]
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.policy["revision"]=3
        self.policy["revoked_key_ids"]=[]
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.policy_envelope(),now=self.now)

    def test_reviewer_review_revocation_changes_status(self):
        original=self.policy_envelope()
        self.ledger.accept_policy(original,now=self.now)
        self.ledger.accept_review(self.dossier,self.artifact,original,self.review_envelope(),now=self.now)
        self.policy["revision"]=2
        self.policy["revoked_review_ids"]=["review-001"]
        updated=self.policy_envelope()
        self.ledger.accept_policy(updated,now=self.now)
        self.assertEqual(
            self.ledger.review_status("review-001",updated,now=self.now)["state"],
            "REVOKED",
        )

    def test_old_policy_cannot_revalidate_revoked_review(self):
        old=self.policy_envelope()
        self.ledger.accept_policy(old,now=self.now)
        self.policy["revision"]=2
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.review_status("review-001",old,now=self.now)

    def test_local_review_audit_tamper_detected(self):
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        self.ledger.db.execute("DROP TRIGGER deny_critic_update")
        self.ledger.db.execute("UPDATE events SET event_sha='0' WHERE seq=1")
        with self.assertRaises(EvidenceError):
            self.ledger.audit_status()

    def test_sql_update_and_delete_denied(self):
        self.ledger.accept_policy(self.policy_envelope(),now=self.now)
        for command in (
            "DELETE FROM events WHERE seq=1",
            "UPDATE events SET key_id='other' WHERE seq=1",
        ):
            with self.subTest(sql=command),self.assertRaises(sqlite3.DatabaseError):
                self.ledger.db.execute(command)

    def test_local_critic_audit_database_symlink_rejected(self):
        self.ledger.close()
        original=self.ledger.path
        other=original.with_suffix(".saved")
        original.rename(other)
        original.symlink_to(other)
        with self.assertRaises(EvidenceError):
            CriticReviewLedger(self.root)

    def test_public_reader_module_has_no_private_key_issuance(self):
        from company_os import competitive_critic_review as verifier
        self.assertFalse(hasattr(verifier,"sign_review"))
        self.assertFalse(hasattr(verifier,"publish"))
        self.assertFalse(hasattr(verifier,"start_business"))


if __name__=="__main__":
    unittest.main()
