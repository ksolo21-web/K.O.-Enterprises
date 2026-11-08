"""CE-1L issuer original PDF page signed critic receipt integration tests.

All signers, screenshots, publishers and PDF files are synthetic. No separate
reviewer was run; signed claims are not real visual/issuer authentication.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import os
import struct
import unittest
import zlib
from datetime import timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.competitive_source_page_review import (
    SOURCE_PAGE_REVIEW_DOMAIN, assess_signed_source_pdf_review,
    inspect_signed_source_pdf_review,
)
from company_os.competitive_critic_review import canonical
from company_os.source_provenance import EvidenceError
import test_competitive_pdf_source_handoff as original_fixture
import test_competitive_critic_review as critic_fixture


def synthetic_png(idx: int) -> bytes:
    """A valid small PNG synthetic placeholder, NOT a real PDF rendering."""
    def chunk(name: bytes, data: bytes) -> bytes:
        return (len(data).to_bytes(4, "big") + name + data +
                (zlib.crc32(name + data) & 0xffffffff).to_bytes(4, "big"))
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
    rgb = bytes([idx % 255, (idx * 13) % 255, (idx * 41) % 255]) * 64
    rows = (b"\x00" + rgb) * 64
    return header + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class SourcePageReviewTests(unittest.TestCase):
    def setUp(self):
        self.original = original_fixture.IssuerPdfHandoffTests(
            "test_signed_pdf_handoff_returns_hold_and_all_package_page_tasks"
        )
        self.original.setUp()
        self.addCleanup(self.original.doCleanups)
        self.critic = critic_fixture.CompetitiveCriticReviewTests(
            "test_all_twelve_signed_critic_checks_still_do_not_grant_authority"
        )
        self.critic.setUp()
        self.addCleanup(self.critic.doCleanups)
        self.now = self.original.now
        self.critic.dossier = self.original.d
        self.critic.review["author_id"] = self.original.d["author_id"]
        self.critic.review["venture_id"] = self.original.d["venture_id"]
        self.critic.review["dossier_id"] = self.original.d["dossier_id"]
        self.critic.review["dossier_sha256"] = hashlib.sha256(
            canonical(self.original.d)
        ).hexdigest()
        self.critic.review["completed_at"] = self.now.isoformat()
        self.critic.review["expires_at"] = (
            self.now + timedelta(minutes=30)
        ).isoformat()
        self.critic.review["source_inspections"] = [
            {
                "source_id": src["id"], "sha256": src["sha256"],
                "inspected_at": self.now.isoformat(),
                "method": "reviewer_claimed_original_review",
            } for src in self.original.d["sources"]
        ]
        handoff = self.original.handoff()
        self.handoff = handoff
        tasks = handoff["critic_worklist"]
        self.receipt = {
            "schema_version": "1.0", "receipt_id": "source-page-review-001",
            "review_id": self.critic.review["review_id"],
            "reviewer_id": self.critic.review["reviewer_id"],
            "reviewer_key_id": self.critic.review["reviewer_key_id"],
            "author_id": self.original.d["author_id"],
            "venture_id": self.original.d["venture_id"],
            "dossier_id": self.original.d["dossier_id"],
            "dossier_sha256": handoff["dossier_sha256"],
            "handoff_sha256": handoff["handoff_sha256"],
            "issuer_inventory_head_sha256": handoff["issuer_inventory_head_sha256"],
            "completed_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(minutes=30)).isoformat(),
            "source_inspections": [
                {
                    "source_id": src["source_id"],
                    "document_id": src["document_id"],
                    "original_pdf_sha256": src["original_pdf_sha256"],
                    "excerpt_sha256": src["excerpt_sha256"],
                    "exact_excerpt_page": src["exact_excerpt_page"],
                    "inspected_at": self.now.isoformat(),
                    "inspection_note": (
                        "Synthetic issuer PDF citation is mechanically linked; "
                        "no independent reviewer verified the meaning."
                    ),
                } for src in tasks["source_requirements"]
            ],
            "page_inspections": [],
            "critical_findings": 0, "unresolved_objections": [],
            "reviewer_notes": (
                "Synthetic signed source page metadata only: screenshot files "
                "are not verified renders and no real reviewer attended."
            ),
        }
        self.pngs = {}
        for idx, page in enumerate(tasks["all_issuer_pdf_pages"], 1):
            name = page["document_id"] + ":" + str(page["page_number"])
            png = synthetic_png(idx)
            self.pngs[name] = png
            self.receipt["page_inspections"].append({
                "document_id": page["document_id"],
                "document_sha256": page["document_sha256"],
                "page_number": page["page_number"],
                "extracted_text_sha256": page["extracted_text_sha256"],
                "screenshot_sha256": hashlib.sha256(png).hexdigest(),
                "inspected_at": self.now.isoformat(),
                "inspection_note": (
                    "Synthetic screenshot bytes attached for original-page "
                    "digest verification; genuine visual review pending."
                ),
            })

    def source_envelope(self, key=None):
        record = copy.deepcopy(self.receipt)
        return {
            "receipt": record,
            "signature": base64.b64encode(
                (key or self.critic.reviewer_key).sign(
                    SOURCE_PAGE_REVIEW_DOMAIN + canonical(record, 512000)
                )
            ).decode(),
        }

    def inspect(self, **updates):
        opts = {
            "staging_policy_envelope": self.original.fx.envelope(),
            "staging_trust_ledger": self.original.fx.trust,
            "critic_policy_envelope": self.critic.policy_envelope(),
            "report_review_envelope": self.critic.review_envelope(),
            "report_pdf_path": self.critic.pdf_path,
            "report_pdf_sha256": self.critic.artifact,
            "source_page_review_envelope": self.source_envelope(),
            "original_page_pngs": self.pngs,
            "now": self.now,
        }
        opts.update(updates)
        return inspect_signed_source_pdf_review(
            self.original.fx.root, self.original.d,
            self.original.fx.issuer, "pkg-one", self.original.mapping,
            **opts,
        )

    def assert_blocked(self, **updates):
        safe = assess_signed_source_pdf_review(
            self.original.fx.root, self.original.d,
            self.original.fx.issuer, "pkg-one", self.original.mapping,
            staging_policy_envelope=self.original.fx.envelope(),
            staging_trust_ledger=self.original.fx.trust,
            critic_policy_envelope=self.critic.policy_envelope(),
            report_review_envelope=updates.pop("report_review_envelope", self.critic.review_envelope()),
            report_pdf_path=self.critic.pdf_path,
            report_pdf_sha256=self.critic.artifact,
            source_page_review_envelope=updates.pop("source_page_review_envelope", self.source_envelope()),
            original_page_pngs=updates.pop("original_page_pngs", self.pngs),
            now=updates.pop("now", self.now),
            **updates,
        )
        self.assertEqual(safe["state"], "BLOCK", safe)
        self.assertFalse(safe["publication_authorized"])
        self.assertFalse(safe["independent_critic_approved"])
        return safe

    def test_signed_report_and_all_source_pages_stay_on_external_review_hold(self):
        result = self.inspect()
        self.assertEqual(
            result["state"],
            "HOLD_SIGNED_SOURCE_PAGE_METADATA_EXTERNAL_INDEPENDENCE_UNVERIFIED",
        )
        self.assertEqual(result["signed_sources_matched"], 1)
        self.assertEqual(result["signed_original_pdf_pages_matched"], 2)
        self.assertEqual(result["png_evidence_byte_hashes_matched"], 2)
        self.assertEqual(result["report_review_score_asserted"], 9.75)
        self.assertEqual(result["reported_checks_true"], 12)
        self.assertFalse(result["rendered_source_pages_independently_verified"])
        self.assertFalse(result["original_issuer_authenticated"])
        self.assertFalse(result["reviewer_independence_operationally_proven"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertFalse(result["publication_authorized"])

    def test_source_page_signature_tampering_blocks(self):
        env = self.source_envelope()
        env["signature"] = base64.b64encode(b"\x00" * 64).decode()
        self.assert_blocked(source_page_review_envelope=env)

    def test_source_page_signed_by_untrusted_key_blocks(self):
        self.assert_blocked(
            source_page_review_envelope=self.source_envelope(
                Ed25519PrivateKey.generate(),
            )
        )

    def test_source_receipt_wrong_handoff_digest_blocks(self):
        self.receipt["handoff_sha256"] = "0" * 64
        self.assert_blocked()

    def test_source_receipt_wrong_inventory_head_blocks(self):
        self.receipt["issuer_inventory_head_sha256"] = "0" * 64
        self.assert_blocked()

    def test_source_receipt_wrong_dossier_digest_blocks(self):
        self.receipt["dossier_sha256"] = "0" * 64
        self.assert_blocked()

    def test_report_review_wrong_signer_blocks(self):
        self.assert_blocked(
            report_review_envelope=self.critic.review_envelope(
                key=Ed25519PrivateKey.generate()
            )
        )

    def test_different_critic_reviewer_id_blocks(self):
        self.receipt["reviewer_id"] = "critic-unknown"
        self.assert_blocked()

    def test_self_review_author_identity_blocks(self):
        self.receipt["author_id"] = self.critic.review["reviewer_id"]
        self.assert_blocked()

    def test_source_receipt_wrong_report_review_id_blocks(self):
        self.receipt["review_id"] = "review-unrelated"
        self.assert_blocked()

    def test_original_page_missing_blocks(self):
        self.receipt["page_inspections"].pop()
        self.assert_blocked()

    def test_duplicate_original_page_blocks(self):
        self.receipt["page_inspections"].append(
            copy.deepcopy(self.receipt["page_inspections"][0])
        )
        self.assert_blocked()

    def test_changed_original_pdf_page_digest_blocks(self):
        self.receipt["page_inspections"][0]["document_sha256"] = "f" * 64
        self.assert_blocked()

    def test_changed_original_pdf_extracted_text_blocks(self):
        self.receipt["page_inspections"][0]["extracted_text_sha256"] = "f" * 64
        self.assert_blocked()

    def test_changed_input_png_bytes_blocks(self):
        key = next(iter(self.pngs))
        self.pngs[key] += b"modified"
        self.assert_blocked()

    def test_missing_input_png_bytes_blocks(self):
        self.pngs.pop(next(iter(self.pngs)))
        self.assert_blocked()

    def test_reused_png_under_second_pdf_page_blocks(self):
        first = self.receipt["page_inspections"][0]
        second = self.receipt["page_inspections"][1]
        second["screenshot_sha256"] = first["screenshot_sha256"]
        self.assert_blocked()

    def test_synthetic_jpeg_cannot_impersonate_png(self):
        key = next(iter(self.pngs))
        data = b"\xff\xd8" + b"x" * 150
        self.pngs[key] = data
        self.receipt["page_inspections"][0]["screenshot_sha256"] = hashlib.sha256(data).hexdigest()
        self.assert_blocked()

    def test_original_pdf_source_inspection_missing_blocks(self):
        self.receipt["source_inspections"] = []
        self.assert_blocked()

    def test_original_pdf_excerpt_sha_mismatch_blocks(self):
        self.receipt["source_inspections"][0]["excerpt_sha256"] = "0" * 64
        self.assert_blocked()

    def test_page_claim_cannot_move_to_other_original(self):
        self.receipt["source_inspections"][0]["document_id"] = "attachment"
        self.assert_blocked()

    def test_critic_report_score_nine_fails_strict_threshold(self):
        self.critic.review["score"] = 9.0
        self.assert_blocked()

    def test_missing_mandatory_report_check_blocks(self):
        one = next(iter(self.critic.review["checks"]))
        self.critic.review["checks"][one] = False
        self.assert_blocked()

    def test_revoked_source_receipt_blocks_even_with_valid_signature(self):
        self.critic.policy["revision"] = 2
        self.critic.policy["revoked_review_ids"] = ["source-page-review-001"]
        self.assert_blocked()

    def test_revoked_critic_key_blocks(self):
        self.critic.policy["revision"] = 2
        self.critic.policy["revoked_key_ids"] = ["critic-key-001"]
        self.assert_blocked()

    def test_report_pdf_changed_after_signing_blocks(self):
        self.critic.pdf_path.write_bytes(self.critic.pdf_path.read_bytes() + b"altered")
        self.assert_blocked()

    def test_staged_issuer_source_changed_after_review_blocks(self):
        path = self.original.fx.root / "state/competitive_engine/capture_staging/pkg-one/notice.pdf"
        path.write_bytes(path.read_bytes() + b"altered")
        self.assert_blocked()

    def test_stale_critic_receipt_blocks(self):
        self.receipt["completed_at"] = (self.now - timedelta(hours=2)).isoformat()
        self.assert_blocked()

    def test_unresolved_critic_original_page_objection_blocks(self):
        self.receipt["unresolved_objections"] = ["Unverified page image"]
        self.assert_blocked()

    def test_unexpected_extra_original_page_png_blocks(self):
        self.pngs["mystery:22"] = synthetic_png(73)
        self.assert_blocked()

    def test_no_live_network_or_release_interface_added(self):
        import company_os.competitive_source_page_review as component
        for name in ("publish", "send", "authorize", "launch", "fetch_source"):
            self.assertFalse(hasattr(component, name))


if __name__ == "__main__":
    unittest.main()
