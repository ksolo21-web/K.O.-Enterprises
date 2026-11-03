"""V7 synthetic-only trust log and case-level governance acceptance.

Two ephemeral trustee keys and a third witness key; all organization identities
are fabricated, never enrolled with a real issuer or external witness.
"""
from __future__ import annotations

from datetime import date
import copy
import hashlib
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inspection_engine.core import DataError, sha256
from inspection_engine.m4_human_review import _digest, _bytes
from inspection_engine.m4_governance_history import (
    verify_governance_history, governed_issuer_evidence_preflight, ZERO_HASH
)
import test_m4_issuer_receipts as issuer_tests


class M4GovernanceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.v6 = issuer_tests.M4IssuerReceiptTests(
            "test_two_synthetic_source_receipts_pass_only_internal_custody")
        self.v6.setUp()
        self.addCleanup(self.v6.doCleanups)
        self.b = self.v6
        self.now = date(2026, 11, 3)
        self.trustees = [Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()]
        self.witness_key = Ed25519PrivateKey.generate()
        self.root = self.b.b.f.root
        self.history_path = self.root / "independently_governed_history.json"
        self.witness_path = self.root / "independent_witness_checkpoint.json"
        self.genesis = {
            "schema_version": 1,
            "trust_domain": "M4_PRIVATE_INSPECTION_REVIEW",
            "jurisdiction": "US-MI",
            "customer_release_allowed": False,
            "trustees": [
                {"trustee_id": "synthetic-governor-%d" % i,
                 "organization_id": "IndependentTrustOrg%d" % i,
                 "public_key_hex": self.pub(self.trustees[i])}
                for i in range(2)
            ]
        }
        self.witness_id = "synthetic-witness"
        self.witness_org = "SyntheticWitnessOrg"
        self.genesis_pin = _digest(self.genesis)
        self.reason = hashlib.sha256(b"SYNTHETIC reason and evidence checked by 2 auditors").hexdigest()
        self.effective = "2026-11-03"
        self.enrolled = {
            "subject_id": self.b.root_data["issuer_verifier_id"],
            "subject_public_key_hex": self.b.root_data["public_key_hex"],
            "subject_organization_id": self.b.root_data["organization_id"],
            "subject_registry_sha256": sha256(self.b.verifier_root)
        }
        self.events = []
        self.append_event("enroll_issuer_verifier", nonce="aa" * 16)
        self.save()

    def pub(self, key):
        return key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def append_event(self, action, *, nonce, subject=None, effective="2026-11-03"):
        p = {
            "schema_version": 1,
            "event_sequence": len(self.events) + 1,
            "previous_event_sha256": _digest(self.events[-1]) if self.events else ZERO_HASH,
            "action": action,
            **(subject or self.enrolled),
            "effective_on": effective,
            "nonce_hex": nonce,
            "reason_sha256": self.reason,
            "customer_release_allowed": False
        }
        envelope = {
            "schema_version": 1,
            "payload": p,
            "signatures": [
                {"trustee_id": self.genesis["trustees"][i]["trustee_id"],
                 "signature_hex": self.trustees[i].sign(_bytes(p)).hex()}
                for i in range(2)
            ]
        }
        self.events.append(envelope)
        return envelope

    def resign_event(self, index):
        ev = self.events[index]
        ev["signatures"] = [
            {"trustee_id": self.genesis["trustees"][i]["trustee_id"],
             "signature_hex": self.trustees[i].sign(_bytes(ev["payload"])).hex()}
            for i in range(2)
        ]

    def save(self, *, recompute_head=True, recompute_witness=True):
        if recompute_head:
            self.head_pin = _digest(self.events[-1])
        self.b.b._save(self.history_path, {
            "schema_version": 1, "genesis": self.genesis, "events": self.events
        })
        if recompute_witness:
            payload = {
                "schema_version": 1,
                "witness_id": self.witness_id,
                "witness_organization_id": self.witness_org,
                "witness_public_key_hex": self.pub(self.witness_key),
                "genesis_sha256": self.genesis_pin,
                "head_sha256": self.head_pin,
                "event_sequence": len(self.events),
                "latest_event_date": self.events[-1]["payload"]["effective_on"],
                "witnessed_on": "2026-11-03",
                "valid_until": "2026-11-04",
                "customer_release_allowed": False
            }
            self.witness_payload = payload
            self.save_witness()

    def save_witness(self):
        self.b.b._save(self.witness_path, {
            "schema_version": 1, "payload": self.witness_payload,
            "signature_hex": self.witness_key.sign(_bytes(self.witness_payload)).hex(),
            "key_algorithm": "Ed25519"
        })

    def verify(self, **kwargs):
        return verify_governance_history(
            self.history_path, self.witness_path,
            independently_pinned_genesis_sha256=kwargs.get("genesis", self.genesis_pin),
            independently_pinned_head_sha256=kwargs.get("head", self.head_pin),
            independently_pinned_witness_public_key_hex=kwargs.get(
                "witness", self.pub(self.witness_key)),
            minimum_event_sequence=kwargs.get("min_seq", 1),
            as_of=kwargs.get("as_of", self.now)
        )

    def check_case(self, **kwargs):
        return governed_issuer_evidence_preflight(
            self.b.b.f.work, self.b.b.f.trust, self.b.b.officers,
            self.b.b.qualification_file, self.b.b.revocation_file,
            self.b.b.evidence_root, self.b.verifier_root, self.b.envelope,
            self.b.store, self.history_path, self.witness_path,
            independently_pinned_genesis_sha256=kwargs.get("genesis", self.genesis_pin),
            independently_pinned_head_sha256=kwargs.get("head", self.head_pin),
            independently_pinned_witness_public_key_hex=kwargs.get(
                "witness", self.pub(self.witness_key)),
            minimum_event_sequence=kwargs.get("min_seq", 1),
            minimum_revocation_sequence=kwargs.get("rev_seq", 17),
            as_of=kwargs.get("as_of", self.now)
        )

    def test_valid_synthetic_governance_and_v6_still_never_authorizes_release(self):
        result = self.check_case()
        self.assertEqual(result["governance_event_sequence"], 1)
        self.assertEqual(result["status"], "V7_OFFLINE_GOVERNED_ISSUER_EVIDENCE_CUSTODY_ONLY")
        self.assertTrue(result["witness_signature_and_history_verified"])
        for field in ("out_of_band_pins_independently_proven",
                      "real_verifier_identity_authenticated",
                      "professional_certification_issuer_authenticity_verified",
                      "professional_release_authorized", "customer_release_allowed"):
            self.assertFalse(result[field])

    def test_history_verifier_reports_witness_and_active_registry(self):
        report = self.verify()
        self.assertEqual(len(report["active_verifiers"]), 1)
        self.assertEqual(report["active_verifiers"][0]["registry_sha256"], sha256(self.b.verifier_root))
        self.assertFalse(report["external_pin_origin_independently_authenticated"])
        self.assertFalse(report["customer_release_allowed"])

    def test_missing_governance_second_signature_fails(self):
        self.events[0]["signatures"].pop()
        self.save(recompute_head=True, recompute_witness=True)
        with self.assertRaisesRegex(DataError, "Both independent governance signatures"):
            self.verify()

    def test_wrong_governor_signature_blocks(self):
        self.events[0]["signatures"][0]["signature_hex"] = "ab" * 64
        self.save()
        with self.assertRaisesRegex(DataError, "Invalid signed trust history"):
            self.verify()

    def test_duplicate_governor_signature_id_blocks(self):
        self.events[0]["signatures"][1]["trustee_id"] = self.events[0]["signatures"][0]["trustee_id"]
        self.save()
        with self.assertRaisesRegex(DataError, "duplicated"):
            self.verify()

    def test_no_events_fails_closed(self):
        self.events.clear()
        self.b.b._save(self.history_path, {
            "schema_version": 1, "genesis": self.genesis, "events": self.events
        })
        with self.assertRaisesRegex(DataError, "bounded nonempty"):
            self.verify()

    def test_reordered_or_missing_event_sequence_rejected(self):
        self.events[0]["payload"]["event_sequence"] = 2
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "Missing or reordered"):
            self.verify()

    def test_tamper_even_with_new_synthetic_signatures_rejected_by_external_head(self):
        old_head = self.head_pin
        self.events[0]["payload"]["reason_sha256"] = hashlib.sha256(b"altered").hexdigest()
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "independently pinned head"):
            self.verify(head=old_head)

    def test_truncation_rejected_using_external_checkpoint(self):
        self.append_event("revoke_issuer_verifier", nonce="bb" * 16)
        self.save()
        pinned = self.head_pin
        self.events.pop()
        self.save(recompute_head=False, recompute_witness=False)
        with self.assertRaisesRegex(DataError, "independently pinned head"):
            self.verify(head=pinned)

    def test_minimum_governance_sequence_detects_rollback(self):
        with self.assertRaisesRegex(DataError, "truncated, stale"):
            self.verify(min_seq=2)

    def test_bad_previous_event_hash_blocks_even_if_resigned(self):
        self.append_event("revoke_issuer_verifier", nonce="bb" * 16)
        self.events[1]["payload"]["previous_event_sha256"] = "f" * 64
        self.resign_event(1)
        self.save()
        with self.assertRaisesRegex(DataError, "Governance chain broken"):
            self.verify()

    def test_revoked_verifier_stays_blocked_even_with_valid_old_v6_receipts(self):
        self.append_event("revoke_issuer_verifier", nonce="bb" * 16)
        self.save()
        report = self.verify(min_seq=2)
        self.assertEqual(report["active_verifiers"], [])
        with self.assertRaisesRegex(DataError, "no active witnessed governance enrollment"):
            self.check_case(min_seq=2)

    def test_reenrollment_of_same_identity_after_revocation_blocked(self):
        self.append_event("revoke_issuer_verifier", nonce="bb" * 16)
        self.append_event("enroll_issuer_verifier", nonce="cc" * 16)
        self.save()
        with self.assertRaisesRegex(DataError, "cannot be re-enrolled"):
            self.verify()

    def test_reused_governance_nonce_blocks(self):
        self.append_event("revoke_issuer_verifier", nonce="aa" * 16)
        self.save()
        with self.assertRaisesRegex(DataError, "reused governance signing challenge"):
            self.verify()

    def test_governance_event_may_not_claim_customer_release(self):
        self.events[0]["payload"]["customer_release_allowed"] = True
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "unsupported fields or release claim"):
            self.verify()

    def test_event_in_future_blocks(self):
        self.events[0]["payload"]["effective_on"] = "2026-11-04"
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "future dated"):
            self.verify()

    def test_two_governors_cannot_share_organization(self):
        self.genesis["trustees"][1]["organization_id"] = self.genesis["trustees"][0]["organization_id"]
        self.genesis_pin = _digest(self.genesis)
        self.save()
        with self.assertRaisesRegex(DataError, "independent governance trustee identities"):
            self.verify()

    def test_witness_not_allowed_to_be_governor(self):
        self.witness_org = self.genesis["trustees"][1]["organization_id"]
        self.save()
        with self.assertRaisesRegex(DataError, "witness cannot be a governance trustee"):
            self.verify()

    def test_wrong_witness_public_key_pin_blocks(self):
        with self.assertRaisesRegex(DataError, "independent witness key pin"):
            self.verify(witness="e" * 64)

    def test_tampered_signed_witness_blocks(self):
        report = json.loads(self.witness_path.read_text())
        report["payload"]["event_sequence"] = 900
        self.b.b._save(self.witness_path, report)
        with self.assertRaisesRegex(DataError, "Invalid signed trust history"):
            self.verify()

    def test_validly_signed_but_mismatched_witness_head_blocks(self):
        self.witness_payload["head_sha256"] = "e" * 64
        self.save_witness()
        with self.assertRaisesRegex(DataError, "Witness not bound"):
            self.verify()

    def test_stale_witness_blocks(self):
        with self.assertRaisesRegex(DataError, "Witness not current"):
            self.verify(as_of=date(2026, 11, 6))

    def test_witness_signer_org_overlaps_issuer_verifier(self):
        self.witness_org = self.enrolled["subject_organization_id"]
        self.save()
        with self.assertRaisesRegex(DataError, "Active verifier overlaps"):
            self.verify()

    def test_governance_trustee_overlap_with_reviewer_org_blocks_composed_gate(self):
        self.genesis["trustees"][0]["organization_id"] = "SyntheticIndependentQA"
        self.genesis_pin = _digest(self.genesis)
        self.save()
        with self.assertRaisesRegex(DataError, "cannot overlap review"):
            self.check_case()

    def test_governance_trustee_overlap_with_officer_key_blocks_composed_gate(self):
        self.genesis["trustees"][1]["public_key_hex"] = self.b.b._pub(1)
        self.genesis_pin = _digest(self.genesis)
        # Invalid trustee signature would fail first; instead sign with the
        # actual V5 officer key to ensure the real role-collision gate runs.
        self.trustees[1] = self.b.b.officer_keys[1]
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "cannot overlap review"):
            self.check_case()

    def test_issuer_registry_hash_must_match_governed_event(self):
        self.events[0]["payload"]["subject_registry_sha256"] = hashlib.sha256(b"wrong").hexdigest()
        self.resign_event(0)
        self.save()
        with self.assertRaisesRegex(DataError, "not governed"):
            self.check_case()

    def test_history_and_witness_files_cannot_be_inside_case_workspace(self):
        copy_path = self.b.b.f.work / "untrusted_history.json"
        copy_path.write_bytes(self.history_path.read_bytes())
        with self.assertRaisesRegex(DataError, "may not be kept in case"):
            governed_issuer_evidence_preflight(
                self.b.b.f.work, self.b.b.f.trust, self.b.b.officers,
                self.b.b.qualification_file, self.b.b.revocation_file,
                self.b.b.evidence_root, self.b.verifier_root, self.b.envelope,
                self.b.store, copy_path, self.witness_path,
                independently_pinned_genesis_sha256=self.genesis_pin,
                independently_pinned_head_sha256=self.head_pin,
                independently_pinned_witness_public_key_hex=self.pub(self.witness_key),
                minimum_event_sequence=1,
                minimum_revocation_sequence=17, as_of=self.now
            )

    def test_bad_root_pin_blocks_even_valid_local_governance(self):
        with self.assertRaisesRegex(DataError, "pinned genesis differs"):
            self.verify(genesis="e" * 64)

    def test_non_integer_minimum_sequence_fails_closed(self):
        with self.assertRaisesRegex(DataError, "minimum governance sequence"):
            self.verify(min_seq=True)


if __name__ == "__main__":
    unittest.main()
