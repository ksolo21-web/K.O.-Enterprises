"""CE-1C3e adversarial ORIGINAL PDF/listing journal tests; zero live fetching."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.approved_pdf_capture import StagedSource
from company_os.capture_staging_signer import attest_local_staging
from company_os.capture_trust import DOMAIN_POLICY, StagingTrustLedger, canonical
from company_os.issuer_inventory_journal import IssuerInventoryJournal
from company_os.source_provenance import EvidenceError

import test_procurement_package as synthetic_pdf

BASE = "https://issuer.example/"
LISTING = BASE + "contracts"


class IssuerInventoryJournalTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.issuer = "issuer-test"
        self.root_key = Ed25519PrivateKey.generate()
        self.permit_signer = Ed25519PrivateKey.generate()
        self.capture_signer = Ed25519PrivateKey.generate()
        env = patch.dict(os.environ, {
            "KO_SOURCE_PERMIT_PUBLIC_KEY_B64": base64.b64encode(
                self.permit_signer.public_key().public_bytes_raw()
            ).decode(),
            "KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64": base64.b64encode(
                self.root_key.public_key().public_bytes_raw()
            ).decode(),
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
        }, clear=False)
        env.start()
        self.addCleanup(env.stop)
        self.journal = IssuerInventoryJournal(self.root)
        self.addCleanup(self.journal.__exit__, None, None, None)
        self.trust = StagingTrustLedger(self.root)
        self.addCleanup(self.trust.close)
        self.policy = {
            "schema_version": "1.0", "policy_id": "ko-test-capture-policy",
            "revision": 1,
            "issued_at": (self.now-timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now+timedelta(days=1)).isoformat(),
            "trusted_keys": [{
                "key_id": "capture-signer-001",
                "public_key_b64": base64.b64encode(
                    self.capture_signer.public_key().public_bytes_raw()
                ).decode(),
                "roles": ["listing", "pdf"],
                "valid_from": (self.now-timedelta(days=1)).isoformat(),
                "valid_until": (self.now+timedelta(days=10)).isoformat(),
            }],
            "revoked_keys": [], "revoked_receipts": [],
            "approved_hosts": ["issuer.example"],
        }
        self.sequence = 0

    def envelope(self):
        body = json.loads(json.dumps(self.policy))
        return {
            "policy": body,
            "signature": base64.b64encode(
                self.root_key.sign(DOMAIN_POLICY + canonical(body))
            ).decode(),
        }

    def permit(self, staged, **alter):
        listing = staged.document_id == "issuer-listing"
        target = {
            "schema_version": "2.0" if listing else "3.0",
            "target_url": staged.source_url,
            "publisher": "Synthetic original issuer",
            "title": "Synthetic procurement item",
            "origin_id": "original-issuer-001", "source_kind": "issuer_primary",
            "rights_basis": "public_access", "approved_by": "synthetic-test-governance",
            "approved_at": (self.now-timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now+timedelta(minutes=30)).isoformat(),
            "permit_id": staged.approved_source_permit_id,
            "max_bytes": max(4096, staged.size_bytes+10),
        }
        if not listing:
            target["media_type"] = "application/pdf"
        target.update(alter)
        signed = json.dumps(target, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False).encode()
        return {
            "target": target,
            "signature": base64.b64encode(self.permit_signer.sign(signed)).decode(),
        }

    def stage(self, package="pkg-one", *, doc="issuer-listing",
              links=("notice", "attachment"), content=None, timestamp=None):
        folder = self.root/"state"/"competitive_engine"/"capture_staging"/package
        folder.mkdir(parents=True, exist_ok=True)
        listing = doc == "issuer-listing"
        filename = "issuer-listing.html" if listing else doc+".pdf"
        url = LISTING if listing else BASE + doc + ".pdf"
        if content is None:
            if listing:
                content = (
                    "<html><body><h1>Test issuer original document inventory</h1>" +
                    "".join(
                        "<a href='/" + name + ".pdf'>" + name + "</a>" for name in links
                    ) + "</body></html>"
                ).encode()
            else:
                content = synthetic_pdf.make_pdf(
                    "This synthetic notice and addendum requires human and original issuer review."
                    + (" " + doc)
                )
        path = folder/filename
        path.write_bytes(content)
        return StagedSource(
            package_id=package, document_id=doc, file_name=filename,
            source_url=url,
            observed_at=(timestamp or self.now).isoformat(),
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            media_type="text/html" if listing else "application/pdf",
            tls_peer_cert_sha256="b"*64,
            pinned_ip="93.184.216.34",
            tls_version="TLSv1.3",
            approved_source_permit_id="permit-"+doc,
            reviewed_pdf_pages=None if listing else 1,
        )

    def record(self, staged, *, permit=None, signed=False, issuer=None, now=None):
        actual_permit = permit if permit is not None else self.permit(staged)
        receipt = None
        policy = None
        trust = None
        if signed:
            policy = self.envelope()
            self.trust.accept_policy(policy, now=self.now)
            self.sequence += 1
            receipt = attest_local_staging(
                repo_root=self.root, staged=staged, key_id="capture-signer-001",
                receipt_id="receipt-event-%03d" % self.sequence,
                sequence=self.sequence, signer=self.capture_signer, signed_at=self.now,
            )
            self.trust.accept_receipt(receipt, policy, now=self.now)
            trust = self.trust
        return self.journal.record(
            issuer_id=issuer or self.issuer, staged=staged, permit=actual_permit,
            attestation=receipt, policy_envelope=policy,
            trust_ledger=trust, now=now or self.now,
        )

    def package(self, name="pkg-one", docs=("notice", "attachment"),
                links=None, *, signed=False, at=None):
        if at is not None:
            self.now = at
        listing = self.stage(name, links=docs if links is None else links,
                             timestamp=self.now)
        record = self.record(listing, signed=signed)
        for doc in docs:
            item = self.stage(name, doc=doc, timestamp=self.now)
            self.record(item, signed=signed)
        return listing, record

    def check(self, name="pkg-one", **kwargs):
        assessment_time = kwargs.pop("now", self.now)
        return self.journal.inspect_session(
            self.issuer, name, now=assessment_time, **kwargs,
        )

    def assert_block(self, name="pkg-one", fragment=None, **kwargs):
        outcome = self.check(name, **kwargs)
        self.assertEqual(outcome["status"], "BLOCK", outcome)
        self.assertFalse(outcome["publication_authorized"])
        if fragment:
            self.assertIn(fragment.lower(), str(outcome["errors"]).lower())
        return outcome

    def test_full_local_link_inventory_stays_on_issuer_review_hold(self):
        self.package()
        v = self.check()
        self.assertEqual(v["status"], "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW")
        self.assertEqual(v["pdf_links_matched"], 2)
        self.assertEqual(v["staging_attestations_currently_verified"], 0)
        self.assertFalse(v["original_issuer_authenticated"])
        self.assertFalse(v["publication_authorized"])

    def test_ledger_writes_private_hash_linked_records(self):
        self.package()
        audit = self.journal.audit()
        self.assertEqual(audit["events"], 3)
        self.assertEqual(len(audit["head_sha256"]), 64)
        self.assertEqual(audit["status"], "LOCAL_CHAIN_UNANCHORED_REVIEW_REQUIRED")
        if os.name == "posix":
            self.assertEqual(self.journal.path.stat().st_mode & 0o777, 0o600)

    def test_original_source_matches_exact_signed_permits(self):
        listing = self.stage()
        good = self.record(listing)
        self.assertEqual(good["state"], "LOCAL_CAPTURE_RECORDED_REVIEW_REQUIRED")
        self.assertEqual(good["staging_attestation"], "NOT_ATTESTED")
        self.assertFalse(good["original_issuer_authenticated"])

    def test_pdf_without_original_listing_refused(self):
        item = self.stage(doc="notice")
        with self.assertRaisesRegex(EvidenceError, "listing"):
            self.record(item)

    def test_pdf_not_linked_from_original_listing_refused(self):
        self.record(self.stage(links=("notice",)))
        with self.assertRaisesRegex(EvidenceError, "not in the original issuer listing"):
            self.record(self.stage(doc="unlisted"))

    def test_duplicate_record_same_package_blocks(self):
        original = self.stage()
        self.record(original)
        with self.assertRaisesRegex(EvidenceError, "replay"):
            self.record(original)

    def test_missing_pdf_link_blocks_session(self):
        self.record(self.stage())
        self.record(self.stage(doc="notice"))
        self.assert_block(fragment="incomplete")

    def test_pdf_file_changed_after_receipt_blocks(self):
        self.package()
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"pkg-one"/"notice.pdf"
        path.write_bytes(path.read_bytes()+b"unsigned addendum")
        self.assert_block(fragment="changed")

    def test_listing_file_changed_after_record_blocks(self):
        self.package()
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"pkg-one"/"issuer-listing.html"
        path.write_bytes(b"<html>alternative fabricated listing</html>")
        self.assert_block(fragment="changed")

    def test_journal_audit_detects_manual_sql_tamper(self):
        self.package()
        self.journal.db.execute("DROP TRIGGER deny_capture_update")
        self.journal.db.execute("UPDATE records SET event_sha='0' WHERE seq=1")
        with self.assertRaisesRegex(EvidenceError, "chain"):
            self.journal.audit()

    def test_audit_trigger_prevents_sql_update_and_delete(self):
        self.package()
        import sqlite3
        for sql in ("DELETE FROM records WHERE seq=1",
                    "UPDATE records SET event_sha='0' WHERE seq=1"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                self.journal.db.execute(sql)

    def test_permit_source_url_tampering_is_rejected(self):
        listing = self.stage()
        bad = self.permit(listing)
        bad["target"]["target_url"] = BASE+"different"
        with self.assertRaises(EvidenceError):
            self.record(listing, permit=bad)

    def test_valid_signature_for_wrong_url_is_not_borrowed(self):
        listing = self.stage()
        wrong = self.permit(listing, target_url=BASE+"different")
        with self.assertRaises(EvidenceError):
            self.record(listing, permit=wrong)

    def test_pdf_requires_v3_not_html_v2(self):
        self.record(self.stage())
        pdf = self.stage(doc="notice")
        with self.assertRaises(EvidenceError):
            self.record(pdf, permit=self.permit(pdf, schema_version="2.0", media_type="application/pdf"))

    def test_expired_or_future_signed_permit_fails_closed(self):
        listing = self.stage()
        for wrong in (
            self.permit(listing, expires_at=(self.now-timedelta(minutes=1)).isoformat()),
            self.permit(
                listing,
                approved_at=(self.now+timedelta(minutes=50)).isoformat(),
                expires_at=(self.now+timedelta(minutes=80)).isoformat(),
            ),
        ):
            with self.subTest(permit=wrong["target"]["approved_at"]):
                with self.assertRaises(EvidenceError):
                    self.record(listing, permit=wrong)

    def test_fake_authenticated_capture_claim_rejected(self):
        listing = self.stage()
        for altered in (
            replace(listing, original_issuer_authenticated=True),
            replace(listing, publication_authorized=True),
            replace(listing, capture_receipt_signed=True),
            replace(listing, state="ORIGINAL_ISSUER_AUTHENTICATED"),
        ):
            with self.subTest(altered=altered.state), self.assertRaises(EvidenceError):
                self.record(altered)

    def test_tampered_local_pdf_hash_rejected_at_record_time(self):
        self.record(self.stage())
        pdf = self.stage(doc="notice")
        with self.assertRaisesRegex(EvidenceError, "changed"):
            self.record(replace(pdf, sha256="f"*64))

    def test_symlinked_staged_pdf_rejected(self):
        self.record(self.stage())
        pdf = self.stage(doc="notice")
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"pkg-one"/"notice.pdf"
        other = self.root/"private.pdf"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaises(EvidenceError):
            self.record(pdf)

    def test_scanned_pdf_not_accepted_as_verified_document(self):
        self.record(self.stage())
        pdf = self.stage(doc="notice", content=synthetic_pdf.make_pdf(
            "unreadable", scanned=True))
        with self.assertRaises(EvidenceError):
            self.record(pdf)

    def test_cross_package_new_pdf_link_flagged_and_held(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        self.package(name="pkg-two", docs=("notice", "addendum"))
        v = self.check("pkg-two")
        self.assertEqual(v["status"], "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW")
        self.assertEqual(v["new_pdf_links_since_prior_listing"], [BASE+"addendum.pdf"])
        self.assertFalse(v["publication_authorized"])

    def test_missing_previous_issuer_pdf_link_blocks_until_reconciled(self):
        self.package(docs=("notice", "attachment"))
        self.now += timedelta(seconds=3)
        self.package(name="pkg-two", docs=("notice",))
        self.assert_block("pkg-two", fragment="removed earlier PDFs")

    def test_reused_listing_url_can_not_silently_change_issuer_binding(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        other_listing = self.stage("pkg-two", links=("notice",), timestamp=self.now)
        with self.assertRaisesRegex(EvidenceError, "listing URL changed"):
            self.record(replace(other_listing, source_url=BASE+"new-origin"))

    def test_new_package_capture_cannot_move_document_id_to_other_source(self):
        self.package(docs=("notice", "other"))
        self.now += timedelta(seconds=3)
        self.record(self.stage("pkg-two", links=("notice", "other"), timestamp=self.now))
        changed = self.stage("pkg-two", doc="notice", timestamp=self.now)
        with self.assertRaises(EvidenceError):
            self.record(replace(changed, source_url=BASE+"other.pdf"))

    def test_pdf_url_cannot_be_rekeyed_as_new_document_id_across_sessions(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        self.record(self.stage("pkg-two", links=("notice",), timestamp=self.now))
        renamed = self.stage("pkg-two", doc="renamed-notice", timestamp=self.now)
        with self.assertRaisesRegex(EvidenceError, "remapped"):
            self.record(replace(renamed, source_url=BASE+"notice.pdf"))

    def test_document_content_revision_flagged_not_silently_overwritten(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        self.record(self.stage("pkg-two",links=("notice",),timestamp=self.now))
        altered = self.stage("pkg-two",doc="notice",timestamp=self.now,
                             content=synthetic_pdf.make_pdf(
                                 "New original version of synthetic notice; review changed content."
                             ))
        self.record(altered)
        v = self.check("pkg-two")
        self.assertEqual(v["changed_document_ids_since_prior_capture"], ["notice"])
        self.assertEqual(v["status"], "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW")

    def test_missing_trusted_staging_receipt_blocks_strict_review(self):
        self.package()
        self.assert_block(fragment="lacks a signed staging receipt",
                          require_staging_attestations=True,
                          policy_envelope=self.envelope(), trust_ledger=self.trust)

    def test_all_signed_staging_receipts_still_cannot_certify_real_issuer(self):
        self.package(signed=True)
        v = self.check(require_staging_attestations=True,
                       policy_envelope=self.envelope(), trust_ledger=self.trust)
        self.assertEqual(v["status"], "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW")
        self.assertEqual(v["staging_attestations_currently_verified"], 3)
        self.assertFalse(v["original_issuer_authenticated"])
        self.assertFalse(v["publication_authorized"])

    def test_later_root_revocation_blocks_formerly_signed_session(self):
        self.package(signed=True)
        old = self.envelope()
        self.assertEqual(
            self.check(require_staging_attestations=True,
                       policy_envelope=old,trust_ledger=self.trust)["status"],
            "HOLD_INDEPENDENT_ISSUER_AND_CRITIC_REVIEW",
        )
        self.policy["revision"] = 2
        self.policy["revoked_keys"] = ["capture-signer-001"]
        new = self.envelope()
        self.trust.accept_policy(new, now=self.now)
        self.assert_block(
            fragment="revoked", require_staging_attestations=True,
            policy_envelope=new, trust_ledger=self.trust,
        )

    def test_expired_listing_or_untrusted_clock_blocks(self):
        self.package()
        self.assert_block(fragment="expired", now=self.now+timedelta(days=2))

    def test_repeated_package_id_cannot_replay_a_new_listing(self):
        self.package()
        self.now += timedelta(seconds=4)
        self.stage("pkg-one")
        with self.assertRaises(EvidenceError):
            self.record(self.stage("pkg-one"))

    def test_audit_chain_is_only_local_not_externally_immutable(self):
        self.package()
        state = self.journal.audit()
        self.assertFalse(state["original_issuer_authenticated"])
        self.assertFalse(state["publication_authorized"])
        self.assertIn("UNANCHORED", state["status"])

    def test_superseded_issuer_snapshot_cannot_be_considered_current(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        self.package(name="pkg-two", docs=("notice", "addendum"))
        self.assert_block("pkg-one", fragment="superseded")

    def test_package_id_cannot_belong_to_two_different_issuers(self):
        listing = self.stage()
        self.record(listing)
        with self.assertRaisesRegex(EvidenceError, "another issuer"):
            self.record(listing, issuer="other-issuer")

    def test_pdf_signed_permit_issuer_identity_mismatch_refused(self):
        self.record(self.stage())
        doc = self.stage(doc="notice")
        wrong = self.permit(doc, origin_id="other-authority")
        with self.assertRaisesRegex(EvidenceError, "issuer identity"):
            self.record(doc, permit=wrong)

    def test_listing_signed_permit_issuer_drift_across_sessions_refused(self):
        self.package(docs=("notice",))
        self.now += timedelta(seconds=3)
        listing = self.stage("pkg-two", links=("notice",))
        wrong = self.permit(listing, publisher="Impersonating another issuer")
        with self.assertRaisesRegex(EvidenceError, "identity differs"):
            self.record(listing, permit=wrong)

    def test_unapproved_cross_host_document_cannot_borrow_listing_identity(self):
        os.environ["KO_SOURCE_APPROVED_HOSTS"] = "issuer.example,other.example"
        cross = BASE.replace("issuer.example", "other.example") + "notice.pdf"
        listing = self.stage(links=("notice",), content=(
            "<html><body><h1>Alternate host PDF listing</h1>"
            "<a href='" + cross + "'>Not the same original issuer host</a></body></html>"
        ).encode())
        self.record(listing)
        doc = self.stage(doc="notice")
        altered = replace(doc, source_url=cross)
        with self.assertRaisesRegex(EvidenceError, "issuer identity/host"):
            self.record(altered)

    def test_intermediate_symlink_swap_refused_during_session_inspection(self):
        self.package(docs=("notice",))
        base = self.root/"state"/"competitive_engine"/"capture_staging"
        current = base/"pkg-one"
        moved = base/"moved-original"
        current.rename(moved)
        current.symlink_to(moved, target_is_directory=True)
        self.assert_block(fragment="path unsafe")

    def test_no_network_fetch_or_release_methods_in_journal(self):
        self.assertFalse(hasattr(self.journal,"fetch_url"))
        self.assertFalse(hasattr(self.journal,"publish"))
        self.assertFalse(hasattr(self.journal,"launch_business"))


if __name__ == "__main__":
    unittest.main()
