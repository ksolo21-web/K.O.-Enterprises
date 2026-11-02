"""All reviewer signatures are ephemeral synthetic keys; no professional attestation."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inspection_engine.core import DataError, sha256
from inspection_engine.m4_pipeline import (
    prepare_case, run_specialists, run_q02, run_q03, render_private_case
)
from inspection_engine.m4_human_review import (
    prepare_review_request, sign_review, verify_reviews, _digest
)
from inspection_engine.m4_review_ui import build_review_worksheet
from scripts.m4_review_cli import template


class HumanReviewTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        original = self.root / "source"
        original.mkdir()
        self.work = self.root / "workspace"
        photo = original / "synthetic.png"
        Image.new("RGB", (240, 160), "#344b61").save(photo)
        source = {
            "project_id": "M4-SYNTHETIC-HUMAN-GATE",
            "property": {
                "label": "Non-real synthetic fixture",
                "inspection_date": "2026-11-02", "synthetic": True
            },
            "media": [{
                "id": "P1", "kind": "photo", "path": "synthetic.png",
                "area": "exterior", "sha256": sha256(photo)
            }],
            "observations": [], "findings": [], "equipment": [], "limitations": [],
        }
        path = original / "case.json"
        path.write_text(json.dumps(source), encoding="utf-8")
        prepare_case(path, self.work)
        def writer(image, prompt):
            return {"candidates": [{
                "type": "potential_concern", "system": "exterior",
                "description": "Possibly dark synthetic rectangle",
                "status": "partially_observed", "location": "Fixture",
                "bbox": [.1, .1, .9, .9]
            }], "requests": []}
        def reviewer(image, prompt):
            return {"decision": "insufficient_evidence",
                    "reason": "Color chart cannot prove house defects",
                    "missing_evidence": "Real inspector observations"}
        def adjudicator(prompt, schema):
            packet = json.loads(prompt.split("LEDGER_PACKET_JSON: ", 1)[1])
            return {"decisions": [{
                "entry_id": r["entry_id"], "decision": "distinct",
                "related_ids": [], "reason": "Separate unverified synthetic entry",
                "evidence_gap": ""
            } for r in packet["queue"]["entries"]]}
        run_specialists(self.work, writer, provider_id="mock-writer")
        run_q02(self.work, reviewer, provider_id="mock-q02")
        run_q03(self.work, adjudicator, provider_id="mock-q03")
        render_private_case(self.work)
        self.keys = [Ed25519PrivateKey.generate() for _ in range(2)]
        self.ids = ["synthetic-inspector", "synthetic-qa"]
        self.roles = ["qualified_inspector", "independent_quality_reviewer"]
        registry = {"schema_version": 1, "reviewers": [
            {
                "reviewer_id": self.ids[i], "role": self.roles[i],
                "public_key_hex": self.keys[i].public_key().public_bytes(
                    ser.Encoding.Raw, ser.PublicFormat.Raw).hex(),
                "active": True
            } for i in range(2)]}
        self.trust = self.root / "trusted_reviewers.json"
        self.trust.write_text(json.dumps(registry), encoding="utf-8")
        self.private_keys = []
        for i, key in enumerate(self.keys):
            path = self.root / ("private_key_%d.pem" % i)
            path.write_bytes(key.private_bytes(
                ser.Encoding.PEM, ser.PrivateFormat.PKCS8, ser.NoEncryption()))
            os.chmod(path, 0o600)
            self.private_keys.append(path)
        prepare_review_request(self.work, self.trust)
        self.packet = json.loads((self.work / "review_request.json").read_text())

    def response(self, index):
        return {
            "request_digest": _digest(self.packet),
            "reviewer_id": self.ids[index],
            "role": self.roles[index],
            "note": "Unverified synthetic source: no real-world certification.",
            "items": [{
                "section": e["section"], "id": e["id"],
                "decision": "insufficient_evidence",
                "note": "Synthetic input requires qualified on-site evaluation"
            } for e in self.packet["items"]],
            "media": [{
                "id": m["id"], "decision": "not_reviewed", "note": ""
            } for m in self.packet["media"]],
            "systems": [{
                "system": system, "decision": "not_verified", "note": ""
            } for system in self.packet["systems"]],
        }

    def sign(self, index):
        return sign_review(self.work, self.trust, self.private_keys[index],
                           self.response(index))

    def test_two_distinct_key_verified_reviews_never_release(self):
        self.assertEqual(verify_reviews(self.work, self.trust)["status"], "HUMAN_REVIEW_INCOMPLETE")
        self.sign(0)
        self.assertEqual(verify_reviews(self.work, self.trust)["signatures_verified"], 1)
        self.sign(1)
        result = verify_reviews(self.work, self.trust)
        self.assertEqual(result["status"], "TWO_REGISTERED_SIGNATURES_VERIFIED")
        self.assertEqual(result["signatures_verified"], 2)
        self.assertFalse(result["professional_license_verified"])
        self.assertFalse(result["customer_release_allowed"])
        self.assertFalse(result["inspector_approved_for_release"])
        self.assertGreater(result["q03_held_entry_count"], 0)
        self.assertGreater(result["report_hold_count"], 0)
        self.assertEqual(self.sign(0)["status"], "REUSED")

    def test_missing_any_media_system_or_record_blocks_signature(self):
        for field in ("media", "systems", "items"):
            record = self.response(0)
            record[field].pop()
            with self.subTest(field=field), self.assertRaisesRegex(DataError, "Incomplete human review"):
                sign_review(self.work, self.trust, self.private_keys[0], record)
        self.assertFalse((self.work / "inspector_review_signed.json").exists())

    def test_incomplete_dispositions_and_unsigned_corrections_rejected(self):
        record = self.response(0)
        record["items"][0]["decision"] = ""
        with self.assertRaisesRegex(DataError, "explicitly choose"):
            sign_review(self.work, self.trust, self.private_keys[0], record)
        record = self.response(0)
        record["items"][0]["note"] = ""
        with self.assertRaisesRegex(DataError, "explicit explanation"):
            sign_review(self.work, self.trust, self.private_keys[0], record)

    def test_wrong_role_private_key_rejected(self):
        with self.assertRaisesRegex(DataError, "Private key does not match"):
            sign_review(self.work, self.trust, self.private_keys[1], self.response(0))

    def test_signature_tampering_fails_verification(self):
        self.sign(0)
        path = self.work / "inspector_review_signed.json"
        envelope = json.loads(path.read_text())
        envelope["payload"]["note"] = "Secretly edited review"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(DataError, "signature verification failed"):
            verify_reviews(self.work, self.trust)

    def test_pdf_tampering_fails_before_verification(self):
        self.sign(0)
        pdf = next((self.work / "option2_draft").glob("*.pdf"))
        pdf.write_bytes(pdf.read_bytes() + b"MODIFIED")
        with self.assertRaisesRegex(DataError, "PDF/receipt hash mismatch"):
            verify_reviews(self.work, self.trust)

    def test_key_registry_change_invalidates_package(self):
        self.sign(0)
        registry = json.loads(self.trust.read_text())
        registry["reviewers"][0]["active"] = False
        self.trust.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaisesRegex(DataError, "registry has changed"):
            verify_reviews(self.work, self.trust)

    def test_key_file_must_be_private(self):
        os.chmod(self.private_keys[0], 0o644)
        with self.assertRaisesRegex(DataError, "owner only"):
            self.sign(0)

    def test_reviewer_identity_cannot_equal_model_provider(self):
        registry = json.loads(self.trust.read_text())
        registry["reviewers"][0]["reviewer_id"] = "mock-q02"
        self.trust.write_text(json.dumps(registry))
        with self.assertRaisesRegex(DataError, "registry"):
            prepare_review_request(self.work, self.trust)

    def test_duplicate_signer_key_fails_distinctness(self):
        other = self.root / "duplicate_trust.json"
        registry = json.loads(self.trust.read_text())
        registry["reviewers"][1]["public_key_hex"] = registry["reviewers"][0]["public_key_hex"]
        other.write_text(json.dumps(registry))
        with self.assertRaisesRegex(DataError, "must differ"):
            prepare_review_request(self.work, other)

    def test_signed_review_cannot_be_replaced(self):
        self.sign(0)
        revised = self.response(0)
        revised["note"] = "Changed answer after signature"
        with self.assertRaisesRegex(DataError, "cannot replace"):
            sign_review(self.work, self.trust, self.private_keys[0], revised)

    def test_offline_worksheet_includes_source_image_and_all_checklists(self):
        result = build_review_worksheet(self.work)
        self.assertEqual(result["previewed_photos"], 1)
        page = Path(result["worksheet"])
        html = page.read_text(encoding="utf-8")
        self.assertIn('connect-src \'none\'', html)
        self.assertIn('data:image/jpeg;base64,', html)
        self.assertIn('Every record, media asset, and system', html)
        self.assertIn('"id":"P1"', html)
        self.assertIn('customer_release_allowed', html)
        self.assertEqual(page.stat().st_mode & 0o777, 0o600)
        self.assertEqual(build_review_worksheet(self.work)["status"], "REUSED")

    def test_worksheet_never_exfiltrates_and_escapes_script_breakout(self):
        from inspection_engine.m4_review_ui import HTML
        self.assertNotIn("fetch(", HTML)
        self.assertNotIn("XMLHttpRequest", HTML)
        self.assertNotIn("https://", HTML)
        self.assertIn("base-uri 'none'", HTML)
        self.assertIn('document.createElement', HTML)
        self.assertIn('textContent', HTML)

    def test_unsigned_template_does_not_preaccept_evidence(self):
        result = template(self.work, "qualified_inspector")
        content = json.loads(Path(result["template"]).read_text())
        self.assertEqual(content["request_digest"], _digest(self.packet))
        self.assertTrue(all(x["decision"] == "" for x in content["items"]))
        self.assertTrue(all(x["decision"] == "" for x in content["media"]))
        self.assertTrue(all(x["decision"] == "" for x in content["systems"]))
        self.assertEqual(template(self.work, "qualified_inspector")["status"], "REUSED")

    def test_worksheet_rejects_changed_photo_after_packet_created(self):
        photo = self.root / "source" / "synthetic.png"
        photo.write_bytes(b"tampered")
        with self.assertRaises((DataError, OSError)):
            build_review_worksheet(self.work)


if __name__ == "__main__":
    unittest.main()
