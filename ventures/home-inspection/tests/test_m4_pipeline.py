"""Synthetic-only end-to-end tests of M4's resumable case stages.

All three role providers are different scripted callables. Nothing is inspected
or approved in the real world, and no model is downloaded or contacted.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from inspection_engine.core import DataError
from inspection_engine.m4_pipeline import (
    prepare_case, status_case, run_specialists, run_q02,
    run_q03, render_private_case,
)


class M4PipelineTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="m4_case_")
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.source_dir = self.base / "source_evidence"
        self.source_dir.mkdir()
        self.work = self.base / "private_run"
        self.photo = self.source_dir / "front.png"
        Image.new("RGB", (512, 320), (70, 90, 130)).save(self.photo)
        self.project = self.source_dir / "case.json"
        self.doc = {
            "project_id": "M4-CONTROLLED-001",
            "property": {
                "label": "Entirely synthetic, no address",
                "inspection_date": "2026-11-02",
                "synthetic": True, "qualified_reviewer": None
            },
            "media": [{
                "id": "P1", "kind": "photo", "path": "front.png",
                "area": "exterior", "sha256": self._digest(self.photo),
                "caption": "Solid-color computer fixture, not a building photograph"
            }],
            "observations": [], "findings": [], "equipment": [], "limitations": [],
        }
        self.doc_save()
        self.calls = {"writer": 0, "q02": 0, "q03": 0}

    def _digest(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def doc_save(self):
        self.project.write_text(json.dumps(self.doc), encoding="utf-8")

    def writer(self, image, prompt):
        self.calls["writer"] += 1
        self.assertIn("ROLE T03", prompt)
        return {
            "candidates": [{
                "type": "potential_concern", "system": "exterior",
                "description": "Possible discoloration in an illustrative wall area",
                "location": "Synthetic front facade",
                "status": "partially_observed", "bbox": [.1, .1, .8, .8],
            }],
            "requests": [],
        }

    def q02_provider(self, image, prompt):
        self.calls["q02"] += 1
        self.assertIn("UNTRUSTED HYPOTHESIS", prompt)
        return {
            "decision": "insufficient_evidence",
            "reason": "Synthetic pixels cannot confirm real wall conditions",
            "missing_evidence": "Real inspector viewing actual facade and source detail",
        }

    def q03_provider(self, prompt, schema):
        self.calls["q03"] += 1
        data = json.loads(prompt.split("LEDGER_PACKET_JSON: ", 1)[1])
        return {"decisions": [{
            "entry_id": row["entry_id"], "decision": "distinct",
            "related_ids": [],
            "reason": "Separate synthetic entry retained pending field inspection",
            "evidence_gap": "",
        } for row in data["queue"]["entries"]]}

    def pipeline_to(self, stage):
        prepare_case(self.project, self.work)
        if stage in ("specialists", "q02", "q03", "report"):
            run_specialists(self.work, self.writer, provider_id="scripted-writer")
        if stage in ("q02", "q03", "report"):
            run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        if stage in ("q03", "report"):
            run_q03(self.work, self.q03_provider, provider_id="scripted-q03")
        if stage == "report":
            return render_private_case(self.work)

    def test_full_pipeline_retains_traceability_and_review_holds(self):
        result = self.pipeline_to("report")
        self.assertEqual(result["stage"], "report")
        self.assertEqual(list(status_case(self.work)["completed"]),
                         ["specialists", "q02", "q03", "report"])
        self.assertEqual(self.calls, {"writer": 1, "q02": 1, "q03": 1})
        stage = json.loads((self.work / "staged_project.json").read_text())
        self.assertEqual(stage["findings"][0]["review"], "review_pending")
        self.assertEqual(stage["findings"][0]["evidence_ids"], ["P1"])
        q03 = json.loads((self.work / "adjudication.json").read_text())
        self.assertTrue(q03["held_entry_ids"])
        self.assertEqual(q03["status"], "ADJUDICATION_HOLD")
        draft = self.work / "option2_draft" / "M4-CONTROLLED-001_option2_PRIVATE_DRAFT.pdf"
        self.assertTrue(draft.read_bytes().startswith(b"%PDF"))
        audit = json.loads((self.work / "report_receipt.json").read_text())
        self.assertEqual(audit["draft_pdf_sha256"], self._digest(draft))
        self.assertFalse(audit["customer_release_allowed"])
        self.assertEqual(audit["Q03_status"], "ADJUDICATION_HOLD")
        from pypdf import PdfReader
        all_text = "\\n".join(page.extract_text() or "" for page in PdfReader(str(draft)).pages)
        self.assertIn("SOURCE EVIDENCE", all_text)
        self.assertIn("front.png", all_text)
        self.assertIn("P1", all_text)
        self.assertEqual(os.stat(draft).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.work).st_mode & 0o777, 0o700)

    def test_resume_from_completed_specialists_without_replaying(self):
        self.pipeline_to("specialists")
        self.assertEqual(self.calls["writer"], 1)
        self.assertEqual(prepare_case(self.project, self.work)["status"], "PREVIOUS_CHECKPOINT")
        with self.assertRaisesRegex(DataError, "already completed"):
            run_specialists(self.work, self.writer, provider_id="scripted-writer")
        self.assertEqual(self.calls["writer"], 1)
        run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        run_q03(self.work, self.q03_provider, provider_id="scripted-q03")
        render_private_case(self.work)
        self.assertFalse(status_case(self.work)["customer_release_allowed"])

    def test_precondition_stages_cannot_be_skipped(self):
        prepare_case(self.project, self.work)
        with self.assertRaisesRegex(DataError, "requires completed"):
            run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        with self.assertRaisesRegex(DataError, "requires completed"):
            run_q03(self.work, self.q03_provider, provider_id="scripted-q03")
        with self.assertRaisesRegex(DataError, "requires completed"):
            render_private_case(self.work)
        self.assertFalse((self.work / "in_flight.json").exists())

    def test_same_writer_and_q02_provider_is_rejected(self):
        self.pipeline_to("specialists")
        with self.assertRaisesRegex(DataError, "different provider"):
            run_q02(self.work, self.q02_provider, provider_id="scripted-writer")
        self.assertEqual(self.calls["q02"], 0)

    def test_same_q02_and_q03_provider_is_rejected(self):
        self.pipeline_to("q02")
        with self.assertRaisesRegex(DataError, "third distinct"):
            run_q03(self.work, self.q03_provider, provider_id="scripted-q02")
        self.assertEqual(self.calls["q03"], 0)

    def test_source_replacement_disables_resume(self):
        self.pipeline_to("specialists")
        self.doc["property"]["label"] = "Other source"
        self.doc_save()
        with self.assertRaisesRegex(DataError, "Source project changed"):
            run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        self.assertEqual(self.calls["q02"], 0)

    def test_media_tampering_disables_resume(self):
        self.pipeline_to("specialists")
        self.photo.write_bytes(b"tampered file")
        with self.assertRaises((DataError, ValueError)):
            run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        self.assertEqual(self.calls["q02"], 0)

    def test_saved_artifact_edit_disables_resume(self):
        self.pipeline_to("specialists")
        p = self.work / "specialist_dossier.json"
        p.write_text(p.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(DataError, "hash mismatch"):
            run_q02(self.work, self.q02_provider, provider_id="scripted-q02")
        self.assertEqual(self.calls["q02"], 0)

    def test_interrupted_stage_refuses_automatic_retry(self):
        prepare_case(self.project, self.work)
        def broken_writer(img, prompt):
            self.calls["writer"] += 1
            raise RuntimeError("simulated provider disconnect")
        with self.assertRaisesRegex(RuntimeError, "disconnect"):
            run_specialists(self.work, broken_writer, provider_id="scripted-writer")
        self.assertEqual(self.calls["writer"], 1)
        self.assertTrue(status_case(self.work)["in_flight"])
        with self.assertRaisesRegex(DataError, "manual audit"):
            run_specialists(self.work, self.writer, provider_id="scripted-writer")
        self.assertEqual(self.calls["writer"], 1)

    def test_unselected_video_remains_explicit_in_final_draft(self):
        movie = self.source_dir / "synthetic-video.mp4"
        movie.write_bytes(b"non-decodable synthetic placeholder")
        self.doc["media"].append({
            "id": "V1", "kind": "video", "path": movie.name,
            "area": "roof", "sha256": self._digest(movie),
        })
        self.doc_save()
        self.pipeline_to("report")
        receipt = json.loads(next((self.work / "option2_draft").glob("*.json")).read_text())
        self.assertIn("V1", [x["id"] for x in receipt["evidence"]["media"]])
        self.assertIn("V1", [x["media_id"] for x in receipt["unrouted_evidence"]])
        self.assertFalse(receipt["customer_release_allowed"])


if __name__ == "__main__":
    unittest.main()
