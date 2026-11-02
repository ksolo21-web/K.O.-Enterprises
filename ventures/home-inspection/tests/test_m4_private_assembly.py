"""Milestone 4 synthetic-only private draft integration regressions."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from inspection_engine.core import DataError
from inspection_engine.m4_assembly import assemble_private_draft


class M4DraftTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.photo = self.root / "field.png"
        Image.new("RGB", (180, 120), (80, 110, 130)).save(self.photo)
        source_hash = hashlib.sha256(self.photo.read_bytes()).hexdigest()
        self.doc = {
            "project_id": "M4-SYNTHETIC-01",
            "property": {
                "label": "Synthetic integration fixture - no real property",
                "inspection_date": "2026-11-02",
                "synthetic": True,
                "qualified_reviewer": None,
            },
            "media": [{
                "id": "P1", "kind": "photo", "path": "field.png",
                "area": "foundation", "sha256": source_hash,
                "caption": "Computer-generated fixture, not site evidence"
            }],
            "observations": [{
                "id": "O1", "system": "framing",
                "feature": "Concealed wall framing",
                "status": "unknown",
                "description": "The wall framing cannot be determined from this image.",
                "evidence_ids": [],
                "review": "review_pending",
                "evidence_class": "unresolved",
            }],
            "findings": [{
                "id": "F1", "system": "foundation",
                "location": "Illustrative interior",
                "severity": "further_evaluation",
                "condition": "Synthetic scenario has insufficient evidence to establish moisture condition.",
                "recommendation": "Qualified on-site evaluation required.",
                "evidence_ids": ["P1"],
                "review": "review_pending",
                "evidence_class": "probable",
            }],
            "equipment": [],
            "limitations": [{
                "id": "L1", "system": "framing",
                "description": "Framing concealed and no testing performed.",
                "evidence_ids": [],
                "evidence_class": "physical_test_required",
            }],
        }
        self.project = self.root / "case.json"
        self.out = self.root / "private"

    def save(self):
        self.project.write_text(json.dumps(self.doc), encoding="utf-8")

    def test_report_receipt_lossless_and_no_release(self):
        self.save()
        result = assemble_private_draft(self.project, self.out)
        self.assertFalse(result["reused"])
        pdf = Path(result["pdf"])
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertFalse(receipt["customer_release_allowed"])
        self.assertFalse(receipt["inspector_approved"])
        self.assertEqual(receipt["review"]["Q01"], "SOURCE_CUSTODY_VERIFIED")
        self.assertEqual(receipt["review"]["Q02"], "NOT_PROVIDED")
        self.assertEqual(receipt["review"]["Q03"], "NOT_PROVIDED")
        self.assertEqual([m["id"] for m in receipt["evidence"]["media"]], ["P1"])
        self.assertEqual(receipt["evidence"]["media"][0], self.doc["media"][0])
        self.assertEqual(next(r["source_record"] for r in receipt["evidence"]["records"]
                              if r["id"] == "F1"), self.doc["findings"][0])
        self.assertEqual({r["id"] for r in receipt["evidence"]["records"]},
                         {"O1", "F1", "L1"})
        self.assertEqual({r["evidence_class"] for r in receipt["evidence"]["records"]},
                         {"unresolved", "probable", "physical_test_required"})
        self.assertEqual(receipt["pdf_sha256"], hashlib.sha256(pdf.read_bytes()).hexdigest())
        self.assertGreater(result["holds"], 0)

    def test_reproducible_pdf_across_separate_private_runs(self):
        self.save()
        first = assemble_private_draft(self.project, self.out)
        second = assemble_private_draft(self.project, self.root / "private_again")
        self.assertEqual(Path(first["pdf"]).read_bytes(), Path(second["pdf"]).read_bytes())

    def test_option2_pdf_has_editorial_sections_and_draft_notice(self):
        from pypdf import PdfReader
        self.save()
        result = assemble_private_draft(self.project, self.out)
        reader = PdfReader(result["pdf"])
        self.assertGreaterEqual(len(reader.pages), 5)
        pages = "\\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Property condition", pages)
        self.assertIn("Condition & next steps", pages)
        self.assertIn("NOT RELEASED", pages)
        self.assertIn("Synthetic", pages)

    def test_q02_supplied_record_preserved_but_not_approved(self):
        self.save()
        record = {"project_id": self.doc["project_id"],
                  "state": "SECOND_PASS_COMPLETE_HUMAN_REVIEW_REQUIRED",
                  "items": [{"decision": "insufficient_evidence", "source_media_id": "P1"}]}
        result = assemble_private_draft(self.project, self.out, q02=record)
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["review_records"]["Q02"], record)
        self.assertEqual(receipt["review"]["Q02"], "ATTACHED_UNVALIDATED")
        self.assertFalse(receipt["customer_release_allowed"])

    def test_idempotent_same_source(self):
        self.save()
        first = assemble_private_draft(self.project, self.out)
        after = assemble_private_draft(self.project, self.out)
        self.assertTrue(after["reused"])
        self.assertEqual(first["pdf"], after["pdf"])
        self.assertFalse(after["customer_release_allowed"])

    def test_new_source_cannot_overwrite_old_report(self):
        self.save()
        assemble_private_draft(self.project, self.out)
        self.doc["property"]["label"] = "CHANGED - must require a fresh output folder"
        self.save()
        with self.assertRaisesRegex(DataError, "different inputs"):
            assemble_private_draft(self.project, self.out)

    def test_tampered_photo_rejected(self):
        self.save()
        self.photo.write_bytes(b"tampered source")
        with self.assertRaises((DataError, OSError)):
            assemble_private_draft(self.project, self.out)

    def test_unhashed_photo_rejected(self):
        del self.doc["media"][0]["sha256"]
        self.save()
        with self.assertRaisesRegex(DataError, "SHA-256"):
            assemble_private_draft(self.project, self.out)

    def test_falsely_direct_visibility_rejected(self):
        self.doc["observations"][0]["evidence_class"] = "directly_visible"
        self.save()
        with self.assertRaisesRegex(DataError, "Direct visibility"):
            assemble_private_draft(self.project, self.out)

    def test_no_spoofed_q03_approval(self):
        self.save()
        with self.assertRaisesRegex(DataError, "Q03 requires"):
            assemble_private_draft(self.project, self.out, q03={"role":"Q03"})
        with self.assertRaises((DataError, ValueError)):
            assemble_private_draft(self.project, self.out, q02={}, q03={"role":"Q03"})

    def test_unreviewed_video_is_preserved_as_gap(self):
        video = self.root / "unreviewed.mp4"
        video.write_bytes(b"synthetic-video-placeholder")
        self.doc["media"].append({
            "id": "V1", "kind": "video", "path": "unreviewed.mp4",
            "area": "roof", "sha256": hashlib.sha256(video.read_bytes()).hexdigest()
        })
        self.save()
        receipt_path = assemble_private_draft(self.project, self.out)["receipt"]
        receipt = json.loads(Path(receipt_path).read_text())
        self.assertEqual([m["id"] for m in receipt["evidence"]["media"]], ["P1", "V1"])
        self.assertIn("V1", [x["media_id"] for x in receipt["unrouted_evidence"]])
        self.assertFalse(receipt["customer_release_allowed"])


if __name__ == "__main__":
    unittest.main()
