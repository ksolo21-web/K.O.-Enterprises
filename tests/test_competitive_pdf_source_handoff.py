"""CE-1K signed-staging PDF → exact issuer claim/page critic handoff tests.

All issuer names, approval signatures, web addresses and PDF bytes are
synthetic fixtures. No real issuer, independent critic, network or publication.
"""
from __future__ import annotations

import copy
import hashlib
import os
import unittest
from datetime import timedelta
from pathlib import Path

from company_os.competitive_pdf_source_handoff import inspect_issuer_pdf_handoff
from company_os.pdf_evidence import inspect_pdf_bytes
from company_os.source_provenance import EvidenceError
from test_competitive_comparator_attribution import attributed_dossier
from test_issuer_inventory_journal import IssuerInventoryJournalTests


class IssuerPdfHandoffTests(unittest.TestCase):
    def setUp(self):
        # Reuse the full real-bytes, permit, signed-staging and issuer journal
        # synthetic fixture without re-running its inherited test suite.
        self.fx = IssuerInventoryJournalTests(
            "test_full_local_link_inventory_stays_on_issuer_review_hold"
        )
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.package(signed=True)
        self.now = self.fx.now
        self.d = attributed_dossier(self.now)
        row = next(
            e for e in self.fx.journal._events()
            if e["package_id"] == "pkg-one" and e["document_id"] == "notice"
        )
        self.original = row
        path = self.fx.root / "state/competitive_engine/capture_staging/pkg-one/notice.pdf"
        text = inspect_pdf_bytes(path.read_bytes())["pages"][0]
        quote = "This synthetic notice and addendum requires human and original issuer review."
        self.assertIn(quote, text)
        self.source = {
            "id": "issuer-notice",
            "publisher": row["permit_publisher"],
            "origin_id": row["permit_origin_id"],
            "url": row["source_url"],
            "observed_at": row["observed_at"],
            "sha256": row["sha256"],
            "kind": "issuer_original", "grade": "B",
            "rights_basis": "public_access",
            "excerpt": quote,
            "capture_type": "local_staging_receipt",
            "applies_to_alternative_id": None,
        }
        self.d["sources"].append(self.source)
        buyer_claim = next(c for c in self.d["claims"] if c["id"] == "cbuyer")
        buyer_claim["source_ids"].append("issuer-notice")
        self.mapping = {"issuer-notice": "notice"}

    def handoff(self, *, mapping=None, dossier=None, **kwargs):
        options = {
            "policy_envelope": self.fx.envelope(),
            "trust_ledger": self.fx.trust,
            "now": self.now,
        }
        options.update(kwargs)
        return inspect_issuer_pdf_handoff(
            self.fx.root,
            self.d if dossier is None else dossier,
            self.fx.issuer, "pkg-one",
            self.mapping if mapping is None else mapping,
            **options,
        )

    def assert_rejected(self, **kwargs):
        with self.assertRaises(EvidenceError):
            self.handoff(**kwargs)

    def test_signed_pdf_handoff_returns_hold_and_all_package_page_tasks(self):
        result = self.handoff()
        self.assertEqual(result["status"], "HOLD_SIGNED_STAGING_PDF_CRITIC_HANDOFF")
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["original_issuer_authenticated"])
        self.assertFalse(result["independent_page_inspection_completed"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertEqual(result["referenced_issuer_sources"], 1)
        self.assertEqual(result["original_pdf_documents_in_package"], 2)
        self.assertGreaterEqual(result["all_pdf_pages_requiring_visual_inspection"], 2)
        task = result["critic_worklist"]["source_requirements"][0]
        self.assertEqual(task["original_pdf_sha256"], self.original["sha256"])
        self.assertEqual(task["exact_excerpt_page"], 1)
        self.assertIn("cbuyer", task["citing_claim_ids"])
        self.assertFalse(task["independent_source_inspection_completed"])

    def test_identical_bytes_and_state_yield_deterministic_handoff_digest(self):
        self.assertEqual(self.handoff()["handoff_sha256"], self.handoff()["handoff_sha256"])

    def test_unbound_issuer_source_is_rejected(self):
        self.assert_rejected(mapping={})

    def test_unknown_original_pdf_record_is_rejected(self):
        self.assert_rejected(mapping={"issuer-notice": "missing-document"})

    def test_html_issuer_listing_cannot_substitute_for_original_pdf(self):
        self.assert_rejected(mapping={"issuer-notice": "issuer-listing"})

    def test_generic_nonissuer_source_cannot_be_smuggled_in_mapping(self):
        self.assert_rejected(mapping={"issuer-notice": "notice", "cbuyer": "attachment"})

    def test_source_original_byte_sha_mismatch_blocks(self):
        self.source["sha256"] = "0" * 64
        self.assert_rejected()

    def test_excerpt_not_in_real_pdf_blocks(self):
        self.source["excerpt"] = "This synthetic source incorrectly claims a different procurement outcome."
        self.assert_rejected()

    def test_source_publisher_mismatch_blocks(self):
        self.source["publisher"] = "Fraudulent pretend agency"
        self.assert_rejected()

    def test_source_origin_mismatch_blocks(self):
        self.source["origin_id"] = "unrelated-issuer"
        self.assert_rejected()

    def test_source_url_mismatch_blocks(self):
        self.source["url"] = "https://issuer.example/attachment.pdf"
        self.assert_rejected()

    def test_source_observation_mismatch_blocks(self):
        self.source["observed_at"] = (self.now - timedelta(minutes=1)).isoformat()
        self.assert_rejected()

    def test_unsigned_operator_capture_label_blocks(self):
        self.source["capture_type"] = "operator_supplied"
        self.assert_rejected()

    def test_unreviewed_rights_claim_cannot_override_signed_permit(self):
        self.source["rights_basis"] = "owner_authorized"
        self.assert_rejected()

    def test_legacy_dossier_without_comparator_attribution_blocks(self):
        self.d["schema_version"] = "1.0"
        self.assert_rejected()

    def test_invented_review_authorization_remains_false(self):
        result = self.handoff()
        self.assertFalse(any(
            page["visual_page_inspection_completed"]
            for page in result["critic_worklist"]["all_issuer_pdf_pages"]
        ))
        self.assertFalse(result["independent_source_inspection_completed"])

    def test_missing_root_governed_trust_ledger_is_rejected(self):
        self.assert_rejected(trust_ledger=None)

    def test_missing_root_policy_envelope_is_rejected(self):
        self.assert_rejected(policy_envelope=None)

    def test_issuer_pdf_missing_after_capture_blocks(self):
        original = self.fx.root/"state/competitive_engine/capture_staging/pkg-one/notice.pdf"
        original.unlink()
        self.assert_rejected()

    def test_issuer_pdf_bytes_changed_after_capture_blocks(self):
        original = self.fx.root/"state/competitive_engine/capture_staging/pkg-one/notice.pdf"
        original.write_bytes(original.read_bytes()+b"altered-after-signing")
        self.assert_rejected()

    def test_revoked_staging_receipt_blocks_handoff(self):
        self.fx.policy["revision"] = 2
        self.fx.policy["revoked_receipts"] = ["receipt-event-002"]
        updated = self.fx.envelope()
        self.fx.trust.accept_policy(updated, now=self.now)
        self.assert_rejected(policy_envelope=updated)

    def test_superseded_issuer_listing_blocks_old_package(self):
        self.fx.package(
            name="pkg-two", docs=("notice", "attachment"), signed=True,
            at=self.now+timedelta(seconds=10),
        )
        self.assert_rejected(now=self.now+timedelta(seconds=12))

    def test_orphan_issuer_document_without_supporting_claim_blocks(self):
        buyer_claim = next(c for c in self.d["claims"] if c["id"] == "cbuyer")
        buyer_claim["source_ids"].remove("issuer-notice")
        self.assert_rejected()

    def test_critic_handoff_does_not_add_network_or_release_execution(self):
        from company_os import competitive_pdf_source_handoff as m
        for name in ("publish", "send", "approve", "fetch_and_capture", "launch"):
            self.assertFalse(hasattr(m, name))


if __name__ == "__main__":
    unittest.main()
