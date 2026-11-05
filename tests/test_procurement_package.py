"""CE-1C offline package tests with genuinely parsed synthetic PDF files.

Every fixture is synthetic; no client file or copyrighted issuer tender is
added to public GitHub. Tests verify structural holds, not business advice.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject, DictionaryObject, NameObject,
)

from company_os.pdf_evidence import inspect_pdf_bytes
from company_os.procurement_package import assess_package


def make_pdf(text: str, *, scanned: bool = False, active: bool = False,
             pages: int = 1, encrypted: bool = False) -> bytes:
    """Create a real PDF with standard-14 Type1 text for test coverage."""
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if not scanned:
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            font_ref = writer._add_object(font)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({
                    NameObject("/F1"): font_ref,
                }),
            })
            safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content = DecodedStreamObject()
            content.set_data(
                ("BT /F1 12 Tf 72 710 Td (" + safe + ") Tj ET").encode("latin-1")
            )
            page[NameObject("/Contents")] = writer._add_object(content)
    if active:
        writer._root_object[NameObject("/OpenAction")] = DictionaryObject({
            NameObject("/S"): NameObject("/JavaScript"),
        })
    if encrypted:
        writer.encrypt("test-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ProcurementPackagePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.now = datetime(2026, 11, 5, 16, tzinfo=timezone.utc)
        self.proposal = "Current synthetic solicitation: bids due 2026-11-25T17:00:00+00:00."
        self.addendum = "Addendum 1 revises submissions: bids due 2026-11-27T18:00:00+00:00."
        self.attach = "The required contractor insurance attachment specifies a certificate."
        self.event = "Mandatory site walk on 2026-11-04T13:00:00+00:00."
        self.doc_text = {
            "solicitation": self.proposal + " " + self.event,
            "addendum-1": self.addendum,
            "attachment-1": self.attach,
        }
        self.originals = {
            "solicitation": make_pdf(self.doc_text["solicitation"]),
            "addendum-1": make_pdf(self.doc_text["addendum-1"]),
            "attachment-1": make_pdf(self.doc_text["attachment-1"]),
        }
        for ident, data in self.originals.items():
            (self.folder / (ident + ".pdf")).write_bytes(data)
        self.manifest = self.sample_manifest()
        self.save()

    def sample_manifest(self):
        docs = []
        for ident in ("solicitation", "addendum-1", "attachment-1"):
            docs.append({
                "id": ident, "filename": ident + ".pdf",
                "sha256": hashlib.sha256(self.originals[ident]).hexdigest(),
                "kind": ("addendum" if ident.startswith("addendum")
                         else "attachment" if ident.startswith("attachment")
                         else "solicitation"),
                "source_url": "https://issuer.example/" + ident + ".pdf",
                "issuer_reference": "Synthetic issued record " + ident,
                "observed_at": self.now.isoformat(),
                "sequence": 1 if ident == "addendum-1" else None,
            })
        return {
            "schema_version": "1.0", "package_id": "pkg-example",
            "issuer_name": "Synthetic Test Issuer",
            "issuer_url": "https://issuer.example/solicitations",
            "discovery": {
                "issuer_listing_checked_at": self.now.isoformat(),
                "issuer_listing_reference": "Synthetic index captured by test",
                "issuer_addenda_inventory_asserted_complete": True,
                "known_missing_records": [],
            },
            "documents": docs,
            "required_document_ids": [d["id"] for d in docs],
            "expected_addenda": 1,
            "evidence": [
                {
                    "id": "evidence-base", "topic": "submission.deadline",
                    "value": "2026-11-25T17:00:00+00:00",
                    "document_id": "solicitation", "page": 1,
                    "quote": self.proposal,
                },
                {
                    "id": "evidence-new", "topic": "submission.deadline",
                    "value": "2026-11-27T18:00:00+00:00",
                    "document_id": "addendum-1", "page": 1,
                    "quote": self.addendum,
                },
                {
                    "id": "evidence-attachment", "topic": "insurance.minimum",
                    "value": "certificate required",
                    "document_id": "attachment-1", "page": 1,
                    "quote": self.attach,
                },
                {
                    "id": "evidence-visit", "topic": "mandatory.site_visit",
                    "value": "2026-11-04T13:00:00+00:00",
                    "document_id": "solicitation", "page": 1,
                    "quote": self.event,
                },
            ],
            "resolutions": [
                {
                    "topic": "submission.deadline",
                    "selected_evidence_id": "evidence-new",
                    "reason": "Later numbered addendum replaces earlier date, pending issuer confirmation.",
                },
            ],
            "mandatory_events": [
                {
                    "id": "visit-1", "evidence_id": "evidence-visit",
                    "occurs_at": "2026-11-04T13:00:00+00:00",
                    "attendance": "confirmed", "waiver_evidence_id": None,
                },
            ],
            "client_eligibility": "unknown",
        }

    def save(self):
        (self.folder / "package.json").write_text(json.dumps(self.manifest), "utf-8")

    def evaluate(self):
        self.save()
        return assess_package(self.folder, now=self.now)

    def blocked(self, term: str):
        verdict = self.evaluate()
        self.assertEqual(verdict["status"], "BLOCK", verdict)
        self.assertFalse(verdict["publication_authorized"])
        self.assertIn(term.lower(), str(verdict["errors"]).lower())

    def test_full_synthetic_pdf_package_remains_on_independent_review_hold(self):
        outcome = self.evaluate()
        self.assertEqual(outcome["status"], "HOLD_INDEPENDENT_ISSUER_AND_CLIENT_REVIEW")
        self.assertFalse(outcome["publication_authorized"])
        self.assertEqual(outcome["addenda_count"], 1)
        self.assertEqual(len(outcome["documents"]), 3)
        self.assertEqual(outcome["evidence_count"], 4)
        self.assertEqual(outcome["documents"]["solicitation"]["page_count"], 1)
        self.assertEqual(
            outcome["resolved_topics_are_operator_assertions"]["submission.deadline"],
            "2026-11-27T18:00:00+00:00",
        )

    def test_real_pdf_is_parsed_and_text_has_matching_pages(self):
        record = inspect_pdf_bytes(self.originals["solicitation"])
        self.assertEqual(record["page_count"], 1)
        self.assertIn(self.event, record["pages"][0])
        self.assertEqual(record["pdf_sha256"],
                         hashlib.sha256(self.originals["solicitation"]).hexdigest())
        self.assertEqual(record["review_status"], "HOLD_FOR_INDEPENDENT_REVIEW")

    def test_missing_attachment_is_blocked(self):
        (self.folder / "attachment-1.pdf").unlink()
        self.blocked("missing")

    def test_excluding_required_attachment_from_inventory_is_blocked(self):
        self.manifest["required_document_ids"].remove("attachment-1")
        self.blocked("inventory")

    def test_extra_undeclared_required_document_is_blocked(self):
        self.manifest["required_document_ids"].append("unknown-document")
        self.blocked("inventory")

    def test_missing_addendum_sequence_is_blocked(self):
        self.manifest["expected_addenda"] = 2
        self.blocked("addendum")

    def test_negative_or_non_integer_addenda_count_blocked(self):
        for num in (-1, True, 1.0, "1"):
            with self.subTest(num=num):
                self.manifest["expected_addenda"] = num
                self.blocked("addenda")
        self.manifest["expected_addenda"] = 1

    def test_addendum_not_included_in_required_inventory_is_blocked(self):
        self.manifest["required_document_ids"].remove("addendum-1")
        self.blocked("inventory")

    def test_pdf_hash_tampering_detected_before_extraction(self):
        with (self.folder / "attachment-1.pdf").open("ab") as f:
            f.write(b"unsigned modifications")
        self.blocked("hash")

    def test_manifest_hash_tampering_detected(self):
        self.manifest["documents"][0]["sha256"] = "0" * 64
        self.blocked("hash")

    def test_encrypted_pdf_is_blocked(self):
        self.originals["attachment-1"] = make_pdf(self.attach, encrypted=True)
        raw = self.originals["attachment-1"]
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.blocked("extraction")

    def test_scanned_or_empty_pdf_is_blocked(self):
        raw = make_pdf(self.attach, scanned=True)
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.blocked("extraction")

    def test_active_pdf_actions_are_blocked(self):
        raw = make_pdf(self.attach, active=True)
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.blocked("extraction")

    def test_corrupt_pdf_with_valid_declared_hash_is_blocked(self):
        raw = b"%PDF-1.7\n" + b"not a real PDF record" * 15
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.blocked("extraction")

    def test_non_pdf_data_refused(self):
        with self.assertRaises(ValueError):
            inspect_pdf_bytes(b"not a pdf" * 100)

    def test_pdf_page_count_is_real_not_manually_assumed(self):
        raw = make_pdf(self.attach, pages=2)
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.evaluate()["documents"]["attachment-1"]["page_count"], 2)

    def test_oversized_pdf_is_blocked(self):
        raw = b"%PDF-1.7 " + b"0" * (4 * 1024 * 1024)
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.blocked("size")

    def test_symlink_external_pdf_is_rejected(self):
        other = self.folder.parent / (self.folder.name + "-private.pdf")
        other.write_bytes(self.originals["attachment-1"])
        self.addCleanup(lambda: other.unlink(missing_ok=True))
        (self.folder / "attachment-1.pdf").unlink()
        (self.folder / "attachment-1.pdf").symlink_to(other)
        self.blocked("unsafe")

    def test_relative_traversal_pdf_rejected(self):
        self.manifest["documents"][0]["filename"] = "../outside.pdf"
        self.blocked("relative")

    def test_invalid_pdf_filename_rejected(self):
        self.manifest["documents"][0]["filename"] = "a\\b.pdf"
        self.blocked("basename")

    def test_missing_original_quote_blocks(self):
        self.manifest["evidence"][0]["quote"] = "This quote is not present on page one of the file."
        self.blocked("quote")

    def test_duplicate_quote_on_page_is_ambiguous(self):
        duplicate = self.attach + " " + self.attach
        raw = make_pdf(duplicate)
        (self.folder / "attachment-1.pdf").write_bytes(raw)
        self.manifest["documents"][2]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.blocked("quote")

    def test_wrong_page_reference_blocks(self):
        self.manifest["evidence"][2]["page"] = 2
        self.blocked("page")

    def test_unknown_document_evidence_blocks(self):
        self.manifest["evidence"][2]["document_id"] = "unknown-doc"
        self.blocked("unknown original")

    def test_deadline_conflict_unresolved_blocks(self):
        self.manifest["resolutions"].clear()
        self.blocked("contradictory")

    def test_mistaken_resolution_reference_blocks(self):
        self.manifest["resolutions"][0]["selected_evidence_id"] = "evidence-attachment"
        self.blocked("resolution")

    def test_missing_deadline_evidence_blocks(self):
        # Keep every addendum quoted, but remove deadline-topic claims.
        for item in self.manifest["evidence"][:2]:
            item["topic"] = "addendum.note"
            item["value"] = "source quotation exists but no parsed deadline"
        self.manifest["resolutions"] = []
        self.blocked("deadline")

    def test_past_deadline_always_blocks(self):
        # Both the real parsed PDF and the manifest explicitly contain the
        # same expired deadline: this must reach the actual expiry guard.
        expired = "2026-11-01T17:00:00+00:00"
        original = "2026-11-27T18:00:00+00:00"
        altered_text = self.addendum.replace(original, expired)
        raw = make_pdf(altered_text)
        (self.folder / "addendum-1.pdf").write_bytes(raw)
        self.manifest["documents"][1]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.manifest["evidence"][1]["quote"] = altered_text
        self.manifest["evidence"][1]["value"] = expired
        self.blocked("deadline expired")

    def test_naive_deadline_value_blocks(self):
        self.manifest["evidence"][1]["value"] = "2026-11-27T17:00:00"
        self.blocked("timezone")

    def test_mandatory_event_missed_blocks(self):
        self.manifest["mandatory_events"][0]["attendance"] = "not_attended"
        self.blocked("mandatory event elapsed")

    def test_mandatory_event_unknown_after_passed_blocks(self):
        self.manifest["mandatory_events"][0]["attendance"] = "unknown"
        self.blocked("mandatory event elapsed")

    def test_waiver_without_original_page_evidence_blocks(self):
        self.manifest["mandatory_events"][0]["attendance"] = "waiver_claimed"
        self.blocked("waiver")

    def test_mandatory_event_unrelated_source_cannot_substitute(self):
        self.manifest["mandatory_events"][0]["evidence_id"] = "evidence-attachment"
        self.blocked("mandatory event")

    def test_client_eligibility_cannot_be_self_certified(self):
        self.manifest["client_eligibility"] = "qualified"
        self.blocked("eligibility")

    def test_missing_known_issuer_records_blocks(self):
        self.manifest["discovery"]["known_missing_records"] = ["addendum-2"]
        self.blocked("incomplete")

    def test_discovery_completeness_not_asserted_blocks(self):
        self.manifest["discovery"]["issuer_addenda_inventory_asserted_complete"] = False
        self.blocked("incomplete")

    def test_stale_issuer_listing_check_blocks(self):
        self.manifest["discovery"]["issuer_listing_checked_at"] = (
            self.now - timedelta(days=3)
        ).isoformat()
        self.blocked("listing check")

    def test_stale_document_source_blocks(self):
        self.manifest["documents"][0]["observed_at"] = (
            self.now - timedelta(days=15)
        ).isoformat()
        self.blocked("document observation")

    def test_future_observation_blocks(self):
        self.manifest["documents"][0]["observed_at"] = (
            self.now + timedelta(days=1)
        ).isoformat()
        self.blocked("document observation")

    def test_duplicate_json_manifest_keys_rejected(self):
        path = self.folder / "package.json"
        path.write_text('{"package_id":"one","package_id":"two"}')
        outcome = assess_package(self.folder, now=self.now)
        self.assertEqual(outcome["status"], "BLOCK")

    def test_unknown_manifest_key_rejected(self):
        self.manifest["pretend_approved"] = True
        self.blocked("package fields")

    def test_deadline_fabrication_is_blocked_even_with_matching_quote_id(self):
        # An arbitrary new future date must not be accepted solely because a
        # real issuer paragraph exists with a different date.
        self.manifest["evidence"][1]["value"] = "2027-12-25T18:00:00+00:00"
        self.blocked("literally supported")

    def test_event_time_fabrication_is_blocked(self):
        self.manifest["mandatory_events"][0]["occurs_at"] = "2026-11-04T14:00:00+00:00"
        self.blocked("literally supported")

    def test_selecting_older_deadline_against_addendum_is_blocked(self):
        self.manifest["resolutions"][0]["selected_evidence_id"] = "evidence-base"
        self.blocked("obsolete")

    def test_waiver_cannot_cite_unrelated_visit_passage(self):
        self.manifest["mandatory_events"][0]["attendance"] = "waiver_claimed"
        self.manifest["mandatory_events"][0]["waiver_evidence_id"] = "evidence-visit"
        self.blocked("waiver")

    def test_no_release_on_any_structural_success(self):
        verdict = self.evaluate()
        self.assertNotIn("APPROVED", verdict["status"])
        self.assertFalse(verdict["publication_authorized"])
        self.assertIn("independent", verdict["status"].lower())

    def test_issuer_url_must_be_canonical_https(self):
        self.manifest["issuer_url"] = "http://issuer.example/solicitations"
        self.blocked("HTTPS")

    def test_duplicate_evidence_ids_rejected(self):
        self.manifest["evidence"][1]["id"] = self.manifest["evidence"][0]["id"]
        self.blocked("duplicate evidence")

    def test_duplicated_documents_rejected(self):
        self.manifest["documents"][1]["id"] = self.manifest["documents"][0]["id"]
        self.blocked("duplicate document")

    def test_document_file_reuse_rejected(self):
        self.manifest["documents"][1]["filename"] = self.manifest["documents"][0]["filename"]
        self.blocked("reused")

    def test_invalid_required_ids_rejected(self):
        self.manifest["required_document_ids"] = ["../out"]
        self.blocked("required")

    def test_waiver_quoted_only_can_remain_on_hold(self):
        # A separately cited issuer statement is still only an operator claim.
        waiver_quote = "This issuer addendum states the mandatory site visit requirement is waived."
        self.addendum += " " + waiver_quote
        raw = make_pdf(self.addendum)
        (self.folder / "addendum-1.pdf").write_bytes(raw)
        self.manifest["documents"][1]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.manifest["evidence"].append({
            "id": "evidence-waiver", "topic": "mandatory.waiver",
            "value": "waiver stated", "document_id": "addendum-1", "page": 1,
            "quote": waiver_quote,
        })
        self.manifest["mandatory_events"][0]["attendance"] = "waiver_claimed"
        self.manifest["mandatory_events"][0]["waiver_evidence_id"] = "evidence-waiver"
        status = self.evaluate()
        self.assertTrue(status["status"].startswith("HOLD"), status)
        self.assertFalse(status["publication_authorized"])
        self.assertIn("MANDATORY_EVENT_STATUS_REQUIRES_ISSUER_CHECK",
                      status["mandatory_event_flags"])


if __name__ == "__main__":
    unittest.main()
