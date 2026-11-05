"""CE-1C3b offline signing/trust and replay tests; no real source authority."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.approved_pdf_capture import StagedSource
from company_os.capture_staging_signer import attest_local_staging
from company_os.capture_trust import (
    DOMAIN_POLICY, StagingTrustLedger, canonical, verify_governance_policy,
    verify_staging_receipt,
)
from company_os.source_provenance import EvidenceError
import test_procurement_package as fixture_support


class CaptureTrustTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.root_signer = Ed25519PrivateKey.generate()
        self.capture_signer = Ed25519PrivateKey.generate()
        root_public = base64.b64encode(
            self.root_signer.public_key().public_bytes_raw()
        ).decode("ascii")
        capture_public = base64.b64encode(
            self.capture_signer.public_key().public_bytes_raw()
        ).decode("ascii")
        self.env = patch.dict(os.environ, {
            "KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64": root_public,
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.policy = {
            "schema_version": "1.0",
            "policy_id": "ko-capture-authority-001",
            "revision": 1,
            "issued_at": (self.now - timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now + timedelta(days=1)).isoformat(),
            "trusted_keys": [{
                "key_id": "capture-issuer-001",
                "public_key_b64": capture_public,
                "roles": ["pdf", "listing"],
                "valid_from": (self.now - timedelta(days=1)).isoformat(),
                "valid_until": (self.now + timedelta(days=30)).isoformat(),
            }],
            "revoked_keys": [],
            "revoked_receipts": [],
            "approved_hosts": ["issuer.example"],
        }
        self.stage_dir = (
            self.root / "state" / "competitive_engine"
            / "capture_staging" / "example-package"
        )
        self.stage_dir.mkdir(parents=True)
        self.pdf = fixture_support.make_pdf(
            "Synthetic procurement PDF. All deadlines require separate issuer review."
        )
        (self.stage_dir / "example-document.pdf").write_bytes(self.pdf)
        self.staged = StagedSource(
            package_id="example-package",
            document_id="example-document",
            file_name="example-document.pdf",
            source_url="https://issuer.example/example-document.pdf",
            observed_at=self.now.isoformat(),
            sha256=hashlib.sha256(self.pdf).hexdigest(),
            size_bytes=len(self.pdf),
            media_type="application/pdf",
            tls_peer_cert_sha256="a" * 64,
            pinned_ip="93.184.216.34",
            tls_version="TLSv1.3",
            approved_source_permit_id="example-permit",
            reviewed_pdf_pages=1,
        )
        self.ledger = StagingTrustLedger(self.root)
        self.addCleanup(self.ledger.close)

    def envelope(self):
        return {
            "policy": json.loads(json.dumps(self.policy)),
            "signature": base64.b64encode(
                self.root_signer.sign(DOMAIN_POLICY + canonical(self.policy))
            ).decode("ascii"),
        }

    def receipt(self, *, seq=1, receipt_id="receipt-original-001",
                staged=None, signer=None, signed_at=None):
        return attest_local_staging(
            repo_root=self.root, staged=staged or self.staged,
            key_id="capture-issuer-001", receipt_id=receipt_id, sequence=seq,
            signer=signer or self.capture_signer,
            signed_at=signed_at or self.now,
        )

    def active(self):
        p = self.envelope()
        self.ledger.accept_policy(p, now=self.now)
        return p

    def test_staging_signer_returns_real_ed25519_signature_but_no_source_certification(self):
        env = self.receipt()
        payload = verify_staging_receipt(env, verify_governance_policy(self.envelope(), now=self.now),
                                         now=self.now)
        self.assertEqual(payload["capture_method"], "local_staged_bytes_unverified")
        self.assertFalse(payload["original_issuer_authenticated"])
        self.assertFalse(payload["publication_authorized"])
        self.assertFalse(hasattr(self.staged, "private_key"))
        self.assertNotIn("private_key", json.dumps(env))

    def test_policy_and_receipt_accepted_only_in_local_unverified_ledger(self):
        p = self.active()
        status = self.ledger.accept_receipt(self.receipt(), p, now=self.now)
        self.assertEqual(status["state"], "LOCAL_STAGING_RECEIPT_RECORDED_UNVERIFIED_ORIGIN")
        self.assertFalse(status["publication_authorized"])
        self.assertFalse(status["independent_critic_approved"])
        audit = self.ledger.audit()
        self.assertEqual(audit["events"], 2)
        self.assertEqual(audit["integrity"], "LOCAL_CHAIN_VALID_NOT_EXTERNALLY_ANCHORED")
        self.assertFalse(audit["publication_authorized"])

    def test_no_private_key_in_reader_environment(self):
        self.assertNotIn("KO_CAPTURE_SIGNER_PRIVATE_KEY_B64", os.environ)
        self.assertNotIn("KO_CAPTURE_GOV_ROOT_PRIVATE_KEY_B64", os.environ)

    def test_root_signature_tamper_rejected(self):
        p = self.envelope()
        p["policy"]["revision"] = 2
        with self.assertRaises(EvidenceError):
            verify_governance_policy(p, now=self.now)

    def test_unknown_root_public_key_rejected(self):
        os.environ["KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64"] = base64.b64encode(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        ).decode("ascii")
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_missing_trust_root_blocks(self):
        os.environ.pop("KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64")
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_expired_governance_policy_blocks(self):
        self.policy["expires_at"] = (self.now - timedelta(seconds=1)).isoformat()
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_policy_published_in_future_blocks(self):
        self.policy["issued_at"] = (self.now + timedelta(hours=1)).isoformat()
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_governance_policy_longer_than_7_days_blocks(self):
        self.policy["expires_at"] = (self.now + timedelta(days=8)).isoformat()
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_external_host_registry_mismatch_blocks(self):
        os.environ["KO_SOURCE_APPROVED_HOSTS"] = "different.example"
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_unsigned_or_extra_governance_fields_block(self):
        p = self.envelope()
        p["policy"]["allow_any_host"] = True
        with self.assertRaises(EvidenceError):
            verify_governance_policy(p, now=self.now)

    def test_forged_capture_signer_rejected(self):
        rogue = Ed25519PrivateKey.generate()
        receipt = self.receipt(signer=rogue)
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(receipt, self.policy, now=self.now)

    def test_altered_signed_receipt_payload_blocks(self):
        r = self.receipt()
        r["receipt"]["sha256"] = "0" * 64
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(r, self.policy, now=self.now)

    def test_revoked_capture_key_blocks(self):
        self.policy["revoked_keys"] = ["capture-issuer-001"]
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(self.receipt(), verify_governance_policy(self.envelope(), now=self.now),
                                   now=self.now)

    def test_revoked_capture_receipt_blocks(self):
        self.policy["revoked_receipts"] = ["receipt-original-001"]
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(self.receipt(), verify_governance_policy(self.envelope(), now=self.now),
                                   now=self.now)

    def test_key_role_narrowing_blocks_other_kind(self):
        self.policy["trusted_keys"][0]["roles"] = ["listing"]
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(self.receipt(), verify_governance_policy(self.envelope(), now=self.now),
                                   now=self.now)

    def test_key_validity_period_blocks_old_signatures(self):
        self.policy["trusted_keys"][0]["valid_from"] = (self.now + timedelta(hours=1)).isoformat()
        with self.assertRaises(EvidenceError):
            verify_staging_receipt(self.receipt(), verify_governance_policy(self.envelope(), now=self.now),
                                   now=self.now)

    def test_past_key_window_larger_than_one_year_blocks(self):
        self.policy["trusted_keys"][0]["valid_from"] = (
            self.now - timedelta(days=366)
        ).isoformat()
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_duplicate_or_unknown_signer_id_blocks(self):
        self.policy["trusted_keys"].append(dict(self.policy["trusted_keys"][0]))
        with self.assertRaises(EvidenceError):
            verify_governance_policy(self.envelope(), now=self.now)

    def test_repeated_receipt_id_is_replay(self):
        p = self.active()
        self.ledger.accept_receipt(self.receipt(), p, now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(self.receipt(), p, now=self.now)
        self.assertEqual(self.ledger.audit()["events"], 2)

    def test_changed_receipt_id_cannot_reset_sequence(self):
        p = self.active()
        self.ledger.accept_receipt(self.receipt(), p, now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(self.receipt(receipt_id="receipt-new-002"), p, now=self.now)

    def test_increased_sequence_with_distinct_receipt_allowed_but_never_approved(self):
        p = self.active()
        self.ledger.accept_receipt(self.receipt(), p, now=self.now)
        result = self.ledger.accept_receipt(
            self.receipt(seq=2, receipt_id="receipt-new-002"), p, now=self.now
        )
        self.assertEqual(self.ledger.audit()["events"], 3)
        self.assertFalse(result["publication_authorized"])

    def test_lower_revision_trust_policy_rollback_fails_closed(self):
        self.active()
        self.policy["revision"] = 2
        self.policy["revoked_receipts"] = ["receipt-original-001"]
        self.ledger.accept_policy(self.envelope(), now=self.now)
        self.policy["revision"] = 1
        self.policy["revoked_receipts"] = []
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.envelope(), now=self.now)
        self.assertEqual(self.ledger.audit()["events"], 3)

    def test_same_revision_changed_revocation_is_blocked(self):
        self.active()
        self.policy["revoked_receipts"] = ["receipt-original-001"]
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.envelope(), now=self.now)

    def test_revoked_receipt_cannot_be_unrevoked_in_new_signed_revision(self):
        self.active()
        self.policy["revision"] = 2
        self.policy["revoked_receipts"] = ["receipt-original-001"]
        self.ledger.accept_policy(self.envelope(), now=self.now)
        self.assertEqual(self.ledger.audit()["events"], 3)
        self.policy["revision"] = 3
        self.policy["revoked_receipts"] = []
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.envelope(), now=self.now)
        self.assertEqual(self.ledger.audit()["events"], 3)

    def test_compromised_key_cannot_be_reenabled_by_new_policy(self):
        self.active()
        self.policy["revision"] = 2
        self.policy["revoked_keys"] = ["capture-issuer-001"]
        self.ledger.accept_policy(self.envelope(), now=self.now)
        self.policy["revision"] = 3
        self.policy["revoked_keys"] = []
        with self.assertRaises(EvidenceError):
            self.ledger.accept_policy(self.envelope(), now=self.now)

    def test_tampered_revocation_event_detected_in_audit_chain(self):
        self.active()
        self.policy["revision"] = 2
        self.policy["revoked_keys"] = ["capture-issuer-001"]
        self.ledger.accept_policy(self.envelope(), now=self.now)
        self.ledger.db.execute("DROP TRIGGER block_event_update")
        self.ledger.db.execute(
            "UPDATE events SET reference_id='fake' WHERE kind='revoked_key'"
        )
        with self.assertRaises(EvidenceError):
            self.ledger.audit()

    def test_latest_policy_must_be_active_before_receipt(self):
        p = self.envelope()
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(self.receipt(), p, now=self.now)

    def test_old_policy_receipts_blocked_after_revocation_update(self):
        old = self.active()
        self.policy["revision"] = 2
        self.policy["revoked_keys"] = ["capture-issuer-001"]
        new = self.envelope()
        self.ledger.accept_policy(new, now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(self.receipt(), old, now=self.now)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(self.receipt(), new, now=self.now)

    def test_original_pdf_byte_change_blocks_signed_receipt_at_acceptance(self):
        p = self.active()
        receipt = self.receipt()
        (self.stage_dir/"example-document.pdf").write_bytes(self.pdf[:-1] + bytes([self.pdf[-1] ^ 1]))
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(receipt, p, now=self.now)
        self.assertEqual(self.ledger.audit()["events"], 1)

    def test_symlinked_staged_pdf_blocks(self):
        p = self.active()
        receipt = self.receipt()
        target = self.root/"private-sentinel"
        target.write_bytes(self.pdf)
        (self.stage_dir/"example-document.pdf").unlink()
        (self.stage_dir/"example-document.pdf").symlink_to(target)
        with self.assertRaises(EvidenceError):
            self.ledger.accept_receipt(receipt, p, now=self.now)

    def test_synthetic_listing_is_signed_only_as_unverified_staging(self):
        raw = (b"<html><body>Issuer listing from a synthetic fixture. "
               b"<a href='/example-document.pdf'>Original PDF</a></body></html>")
        (self.stage_dir/"issuer-listing.html").write_bytes(raw)
        staged = replace(
            self.staged, document_id="issuer-listing", file_name="issuer-listing.html",
            media_type="text/html", source_url="https://issuer.example/solicitations",
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw),
            reviewed_pdf_pages=None,
        )
        receipt = self.receipt(staged=staged)
        p = self.active()
        result = self.ledger.accept_receipt(receipt, p, now=self.now)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(receipt["receipt"]["role"], "listing")

    def test_forged_publication_flag_not_signed(self):
        fake = replace(self.staged, publication_authorized=True)
        with self.assertRaises(EvidenceError):
            self.receipt(staged=fake)

    def test_stage_wrong_size_or_hash_refused_before_signing(self):
        wrong = replace(self.staged, sha256="0" * 64)
        with self.assertRaises(EvidenceError):
            self.receipt(staged=wrong)
        wrong = replace(self.staged, size_bytes=500000)
        with self.assertRaises(EvidenceError):
            self.receipt(staged=wrong)

    def test_stage_filename_traversal_and_symlink_block(self):
        with self.assertRaises(EvidenceError):
            self.receipt(staged=replace(self.staged, file_name="../secret.pdf"))
        private = self.root/"sentinel"
        private.write_bytes(self.pdf)
        (self.stage_dir/"example-document.pdf").unlink()
        (self.stage_dir/"example-document.pdf").symlink_to(private)
        with self.assertRaises(EvidenceError):
            self.receipt()

    def test_unapproved_host_or_private_ip_refused(self):
        with self.assertRaises(EvidenceError):
            self.receipt(staged=replace(self.staged, source_url="https://evil.example/path.pdf"))
        with self.assertRaises(EvidenceError):
            self.receipt(staged=replace(self.staged, pinned_ip="10.0.0.1"))

    def test_stale_or_future_staging_refused(self):
        old = replace(self.staged, observed_at=(self.now-timedelta(hours=3)).isoformat())
        with self.assertRaises(EvidenceError):
            self.receipt(staged=old)
        future = replace(self.staged, observed_at=(self.now+timedelta(hours=1)).isoformat())
        with self.assertRaises(EvidenceError):
            self.receipt(staged=future)

    def test_non_signer_object_cannot_sign(self):
        with self.assertRaises(EvidenceError):
            self.receipt(signer=object())

    def test_invalid_metadata_never_signs(self):
        for bad in (
            replace(self.staged, media_type="text/html"),
            replace(self.staged, state="SOURCE_AUTHENTICATED"),
            replace(self.staged, original_issuer_authenticated=True),
        ):
            with self.subTest(bad=bad.media_type, state=bad.state), self.assertRaises(EvidenceError):
                self.receipt(staged=bad)

    def test_manual_database_modification_is_detected(self):
        self.active()
        self.ledger.db.execute("DROP TRIGGER block_event_update")
        self.ledger.db.execute("UPDATE events SET record_sha='0' WHERE seq=1")
        with self.assertRaises(EvidenceError):
            self.ledger.audit()

    def test_no_external_event_or_business_release_functions(self):
        self.assertFalse(hasattr(self.ledger, "publish"))
        self.assertFalse(hasattr(self.ledger, "fetch_url"))
        self.assertFalse(hasattr(self.ledger, "approve_venture"))
        self.assertFalse(self.ledger.audit()["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
