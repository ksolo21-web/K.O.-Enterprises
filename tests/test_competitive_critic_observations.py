"""CE-1O reviewer observation intake tests: synthetic reviewer signatures ONLY.

No test assumes a real human/agent inspected actual issuer content. These
tests establish record completeness, signed metadata integrity and HOLD.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.competitive_critic_observations import (
    OBSERVATION_DOMAIN, MAX_SIGNED_OBSERVATIONS_BYTES,
    assess_signed_observation_receipt, build_pending_observation_worklist,
    inspect_signed_observation_receipt,
)
from company_os.competitive_critic_review import canonical
from company_os.source_provenance import EvidenceError
import test_competitive_critic_room as room_fixture
import test_competitive_critic_review as critic_fixture


class SignedObservationTests(unittest.TestCase):
    def setUp(self):
        self.room_fx = room_fixture.SealedCriticRoomTests(
            "test_complete_actual_PDF_page_packet_stays_reviewer_pending"
        )
        self.room_fx.setUp()
        self.addCleanup(self.room_fx.doCleanups)
        self.room = self.room_fx.stage(room="room-for-observations")
        self.path = Path(self.room["workroom"])
        self.digest = self.room["manifest_sha256"]
        self.packet = json.loads((self.path / "manifest.json").read_text("utf-8"))
        self.critic = critic_fixture.CompetitiveCriticReviewTests(
            "test_all_twelve_signed_critic_checks_still_do_not_grant_authority"
        )
        self.critic.setUp()
        self.addCleanup(self.critic.doCleanups)
        self.now = self.critic.now
        pending = build_pending_observation_worklist(
            self.path, expected_manifest_sha256=self.digest,
        )
        self.pending = pending
        dossier = self.packet["dossier"]
        self.receipt = {
            "schema_version": "1.0",
            "receipt_id": "obs-review-001",
            "reviewer_id": "critic-001",
            "reviewer_key_id": "critic-key-001",
            "author_id": dossier["author_id"],
            "venture_id": dossier["venture_id"],
            "dossier_id": dossier["dossier_id"],
            "dossier_sha256": self.packet["dossier_sha256"],
            "handoff_sha256": self.packet["handoff_sha256"],
            "issuer_inventory_head_sha256": self.packet["issuer_inventory_head_sha256"],
            "room_manifest_sha256": self.digest,
            "completed_at": self.now.isoformat(),
            "expires_at": (self.now+timedelta(minutes=30)).isoformat(),
            "page_observations": [{
                "file": row["file"],
                "png_sha256": row["png_sha256"],
                "observed_at": self.now.isoformat(),
                "visual_finding": "legible_reported",
                "visual_notes": (
                    "Synthetic reviewer entry only: the attached test PNG "
                    "digest matches the packet. No real reviewer saw it."
                ),
            } for row in pending["page_tasks"]],
            "claim_assessments": [{
                "claim_id": row["claim_id"],
                "source_ids_considered": list(row["source_ids_considered"]),
                "counter_source_ids_considered": list(row["counter_source_ids_considered"]),
                "issuer_citation_refs": copy.deepcopy(row["issuer_citation_refs"]),
                "assessed_at": self.now.isoformat(),
                "disposition": (
                    "packet_excerpt_located"
                    if row["issuer_citation_refs"] else "unverified"
                ),
                "reasoning": (
                    "Fictional test-only review assertion. Source packet "
                    "citations were matched by code; original factual truth "
                    "and independent inspection remain entirely unverified."
                ),
            } for row in pending["claim_tasks"]],
            "reviewer_summary": (
                "Synthetic reviewer assertions for cryptographic data-integrity "
                "testing only. No genuine external source truth, independent "
                "reviewer, visual inspection, or publication approval exists."
            ),
        }

    def signed(self, key=None):
        body = copy.deepcopy(self.receipt)
        signature = (key or self.critic.reviewer_key).sign(
            OBSERVATION_DOMAIN + canonical(body, MAX_SIGNED_OBSERVATIONS_BYTES)
        )
        return {"receipt": body, "signature": base64.b64encode(signature).decode("ascii")}

    def inspect(self, **overrides):
        args = {
            "now": self.now,
        }
        args.update(overrides)
        return inspect_signed_observation_receipt(
            self.path, self.digest, self.critic.policy_envelope(),
            self.signed(), **args,
        )

    def blocked(self, *, envelope=None, digest=None, policy=None, room=None, now=None):
        result = assess_signed_observation_receipt(
            self.path if room is None else room,
            self.digest if digest is None else digest,
            self.critic.policy_envelope() if policy is None else policy,
            self.signed() if envelope is None else envelope,
            now=self.now if now is None else now,
        )
        self.assertEqual(result["state"], "BLOCK", result)
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertFalse(result["production_engine_ready"])
        return result

    def test_pending_worklist_has_every_page_and_claim_unanswered(self):
        self.assertEqual(self.pending["state"], "PENDING_QUALIFIED_SEPARATE_REVIEWER_INPUT")
        self.assertEqual(self.pending["page_tasks_unanswered"], 2)
        self.assertEqual(
            self.pending["claim_tasks_unanswered"], len(self.packet["dossier"]["claims"]),
        )
        self.assertTrue(all(x["visual_finding"] is None for x in self.pending["page_tasks"]))
        self.assertTrue(all(x["disposition"] is None for x in self.pending["claim_tasks"]))
        self.assertFalse(self.pending["publication_authorized"])

    def test_signed_complete_synthetic_assertions_still_hold_unverified(self):
        result = self.inspect()
        self.assertEqual(
            result["state"],
            "HOLD_SIGNED_PAGE_AND_CLAIM_OBSERVATIONS_NOT_INDEPENDENTLY_VERIFIED",
        )
        self.assertEqual(result["all_original_pdf_pages_accounted_for"], 2)
        self.assertEqual(
            result["all_dossier_claims_accounted_for"], len(self.packet["dossier"]["claims"]),
        )
        self.assertGreater(result["claims_unverified"], 0)
        self.assertGreaterEqual(result["issuer_packet_citations_reported_located"], 1)
        self.assertFalse(result["reviewer_identity_operationally_independent"])
        self.assertFalse(result["actual_human_or_agent_visual_inspection_proven"])
        self.assertFalse(result["source_claim_truth_independently_verified"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertFalse(result["publication_authorized"])

    def test_signature_mutation_rejected(self):
        env = self.signed()
        env["signature"] = base64.b64encode(b"\x00" * 64).decode()
        self.blocked(envelope=env)

    def test_unapproved_signer_rejected(self):
        self.blocked(envelope=self.signed(Ed25519PrivateKey.generate()))

    def test_wrong_out_of_band_manifest_digest_rejected(self):
        self.blocked(digest="f"*64)

    def test_receipt_bound_to_other_workroom_rejected(self):
        self.receipt["room_manifest_sha256"] = "0"*64
        self.blocked()

    def test_receipt_bound_to_other_dossier_rejected(self):
        self.receipt["dossier_sha256"] = "0"*64
        self.blocked()

    def test_receipt_bound_to_other_handoff_rejected(self):
        self.receipt["handoff_sha256"] = "0"*64
        self.blocked()

    def test_receipt_bound_to_other_inventory_rejected(self):
        self.receipt["issuer_inventory_head_sha256"] = "0"*64
        self.blocked()

    def test_reviewer_cannot_equal_original_author(self):
        self.receipt["reviewer_id"] = self.packet["dossier"]["author_id"]
        self.blocked()

    def test_reviewer_scope_requires_exact_venture(self):
        self.critic.policy["reviewers"][0]["venture_ids"] = ["other-venture"]
        self.blocked()

    def test_expired_reviewer_key_rejected(self):
        self.critic.policy["revoked_key_ids"] = ["critic-key-001"]
        self.blocked()

    def test_revoked_observation_receipt_rejected(self):
        self.critic.policy["revoked_review_ids"] = ["obs-review-001"]
        self.blocked()

    def test_wrong_trusted_governance_root_rejected(self):
        key = Ed25519PrivateKey.generate()
        wrong = base64.b64encode(key.public_key().public_bytes_raw()).decode()
        with patch.dict(os.environ, {"KO_CRITIC_ROOT_PUBLIC_KEY_B64": wrong}):
            self.blocked()

    def test_one_original_pdf_page_missing_rejected(self):
        self.receipt["page_observations"].pop()
        self.blocked()

    def test_duplicate_page_hides_other_original_rejected(self):
        self.receipt["page_observations"][1] = copy.deepcopy(
            self.receipt["page_observations"][0]
        )
        self.blocked()

    def test_original_png_digest_substitution_rejected(self):
        self.receipt["page_observations"][0]["png_sha256"] = "0"*64
        self.blocked()

    def test_missing_visual_finding_rejected(self):
        self.receipt["page_observations"][0]["visual_finding"] = None
        self.blocked()

    def test_page_notes_must_be_substantive(self):
        self.receipt["page_observations"][0]["visual_notes"] = "Looks fine."
        self.blocked()

    def test_page_findings_may_raise_explicit_nonapproval_problems(self):
        self.receipt["page_observations"][0]["visual_finding"] = "unassessable"
        result = self.inspect()
        self.assertEqual(result["reported_page_problems"], 1)
        self.assertFalse(result["publication_authorized"])

    def test_page_observation_older_than_allowed_window_rejected(self):
        self.receipt["page_observations"][0]["observed_at"] = (
            self.now-timedelta(hours=3)
        ).isoformat()
        self.blocked()

    def test_one_of_all_dossier_claim_assessments_missing_rejected(self):
        self.receipt["claim_assessments"].pop()
        self.blocked()

    def test_duplicate_claim_hides_another_rejected(self):
        self.receipt["claim_assessments"][-1] = copy.deepcopy(
            self.receipt["claim_assessments"][0]
        )
        self.blocked()

    def test_claim_supporting_citation_cannot_be_dropped(self):
        item = next(x for x in self.receipt["claim_assessments"] if x["issuer_citation_refs"])
        item["issuer_citation_refs"] = []
        self.blocked()

    def test_claim_citation_original_image_digest_cannot_be_edited(self):
        item = next(x for x in self.receipt["claim_assessments"] if x["issuer_citation_refs"])
        item["issuer_citation_refs"][0]["png_sha256"] = "f"*64
        self.blocked()

    def test_counterevidence_source_ids_cannot_be_omitted(self):
        item = next(x for x in self.receipt["claim_assessments"] if x["counter_source_ids_considered"])
        item["counter_source_ids_considered"] = []
        self.blocked()

    def test_claim_source_order_and_identity_are_bound(self):
        item = self.receipt["claim_assessments"][0]
        item["source_ids_considered"] = ["counterfeit-source"]
        self.blocked()

    def test_nonissuer_source_only_cannot_claim_original_inspection(self):
        item = next(x for x in self.receipt["claim_assessments"] if not x["issuer_citation_refs"])
        item["disposition"] = "packet_excerpt_located"
        self.blocked()

    def test_claim_contradiction_is_reported_without_approval(self):
        self.receipt["claim_assessments"][0]["disposition"] = "contradiction_reported"
        result = self.inspect()
        self.assertEqual(result["claims_with_reported_contradictions"], 1)
        self.assertFalse(result["publication_authorized"])

    def test_claim_reasoning_must_be_substantive(self):
        self.receipt["claim_assessments"][0]["reasoning"] = "Good."
        self.blocked()

    def test_claim_assessment_time_outside_window_rejected(self):
        self.receipt["claim_assessments"][0]["assessed_at"] = (
            self.now-timedelta(hours=2)
        ).isoformat()
        self.blocked()

    def test_total_signed_observation_lifetime_must_be_short(self):
        self.receipt["expires_at"] = (self.now+timedelta(days=1)).isoformat()
        self.blocked()

    def test_critical_findings_cannot_be_added_as_authority_flag(self):
        self.receipt["publication_authorized"] = True
        self.blocked()

    def test_manifest_tampering_after_workroom_verification_blocks(self):
        manifest = self.path/"manifest.json"
        manifest.chmod(0o600)
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        manifest.chmod(0o400)
        self.blocked()

    def test_no_network_no_signing_key_no_authorize_method(self):
        import company_os.competitive_critic_observations as component
        for name in ("send", "publish", "launch", "sign_observations", "approve"):
            self.assertFalse(hasattr(component, name))


if __name__ == "__main__":
    unittest.main()
