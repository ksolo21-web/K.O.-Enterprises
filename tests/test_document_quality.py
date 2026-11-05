"""Synthetic-only QA gate tests. All dates/parties/claims are fictional."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from company_os.document_quality import CHECKS, audit_pack, payload_digest
from company_os.document_quality_batch import check_many

AS_OF = date(2026, 11, 5)
FACT = "A fictional municipal notice lists a November 30, 2026 response date."
ANNEX = f"# Synthetic evidence annex (not an actual procurement)\n\n- {FACT} [C-001] [S-001]\n"


def pack():
    return {
        "schema_version": "1.0", "business_line": "market_intelligence",
        "classification": "public_demo", "pack_id": "TEST-001",
        "title": "Synthetic internal test", "author": "test_author", "output_type": "test_fixture",
        "scope": "Synthetic fixture; never send to customers",
        "limitations": "Fictional issuer and deadline; does not identify a real solicitation",
        "prepared_at": "2026-11-05", "publication_authorization": False,
        "sources": [{"id": "S-001", "title": "Fictional issuer notice", "publisher": "Fictional Agency",
                     "url": "https://example.org/fictional-notice", "type": "primary", "access": "complete",
                     "checked_at": "2026-11-05", "verification": "verified",
                     "verification_method": "Synthetic fixture inspection", "record_reference": "fixture://issuer-001",
                     "evidence_excerpt": "Nov 30 response date",
                     "excerpt_sha256": hashlib.sha256(b"Nov 30 response date").hexdigest()}],
        "claims": [{"id": "C-001", "text": FACT, "kind": "fact", "risk": "deadline", "status": "verified",
                    "source_ids": ["S-001"], "verified_at": "2026-11-05",
                    "counterevidence_checked": True,
                    "evidence_reasoning": "Fictional exact-date match to synthetic issuer fixture",
                    "limitations": "Not real research"}],
        "opportunities": [],
        "deliverables": [{"path": "evidence.md", "sha256": hashlib.sha256(ANNEX.encode()).hexdigest()}],
    }


def reviewed(m):
    m["review"] = {"reviewer_id": "fixture_independent_reviewer", "reviewed_digest": payload_digest(m),
                   "decision": "approve", "reviewed_at": "2026-11-05", "quality_score": 10.0,
                   "checks": {c: True for c in CHECKS},
                   "notes": "Synthetic only: simulated reviewer input; not an external audit.",
                   "review_context": "Simulated independence in unit test only",
                   "visual_evidence": "Synthetic annex checked as plain text"}
    return m


class DocumentQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "evidence.md").write_text(ANNEX, encoding="utf-8")
        self.data = reviewed(pack())

    def check(self, data=None, files=None, public=False):
        if files:
            for name, content in files.items():
                (self.folder / name).write_bytes(content)
        (self.folder / "manifest.json").write_text(json.dumps(data if data is not None else self.data))
        return audit_pack(self.folder, AS_OF, public_repo=public)

    def assertBlocked(self, code, data=None, files=None, public=False):
        result = self.check(data, files, public)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(code, "\n".join(result["errors"]))

    def test_synthetic_fixture_passes_preflight_but_does_not_publish(self):
        result = self.check(public=True)
        self.assertEqual(result["status"], "PASS_REVIEWED_NOT_AUTHORIZED", result["errors"])
        self.assertEqual(result["errors"], [])

    def test_missing_critic_blocks(self):
        self.data.pop("review")
        self.assertBlocked("NO_REVIEW")

    def test_critic_cannot_be_author(self):
        self.data["review"]["reviewer_id"] = self.data["author"]
        self.assertBlocked("REVIEW_INDEPENDENCE")

    def test_critic_cannot_approve_old_version(self):
        self.data["limitations"] = "Changed, so critic approval must expire"
        self.assertBlocked("REVIEW_DIGEST")

    def test_critic_score_nine_is_not_a_pass(self):
        self.data["review"]["quality_score"] = 9.0
        self.assertBlocked("REVIEW_SCORE")

    def test_client_pack_requires_pdf(self):
        self.data["output_type"] = "client_delivery"
        self.assertBlocked("CLIENT_PDF")

    def test_critic_checklist_is_all_or_nothing(self):
        self.data["review"]["checks"]["numbers_and_tables"] = False
        self.assertBlocked("REVIEW_CHECK")

    def test_critic_review_expires(self):
        self.data["review"]["reviewed_at"] = "2026-10-22"
        self.assertBlocked("REVIEW_STALE")

    def test_source_excerpt_tamper_blocks(self):
        self.data["sources"][0]["evidence_excerpt"] = "Nov 15 response date"
        self.assertBlocked("SOURCE_EXCERPT_HASH")

    def test_reviewer_cannot_approve_before_evidence(self):
        self.data["review"]["reviewed_at"] = "2026-11-04"
        self.assertBlocked("REVIEW_CHRONOLOGY")

    def test_claim_incomplete_blocks(self):
        self.data["claims"][0]["status"] = "pending"
        self.assertBlocked("CLAIM_UNVERIFIED")

    def test_no_primary_for_deadline_blocks(self):
        self.data["sources"][0]["type"] = "secondary"
        self.assertBlocked("CRITICAL_PRIMARY")

    def test_stale_deadline_blocks(self):
        self.data["claims"][0]["verified_at"] = "2026-11-03"
        self.assertBlocked("CLAIM_STALE")

    def test_source_stale_blocks(self):
        self.data["sources"][0]["checked_at"] = "2026-09-01"
        self.assertBlocked("STALE_SOURCE")

    def test_source_missing_access_blocks(self):
        self.data["sources"][0]["access"] = "partial"
        self.assertBlocked("SOURCE_ACCESS")

    def test_source_unverified_blocks(self):
        self.data["sources"][0]["verification"] = "unverified"
        self.assertBlocked("SOURCE_VERIFY")

    def test_counter_evidence_not_reviewed_blocks(self):
        self.data["claims"][0]["counterevidence_checked"] = False
        self.assertBlocked("COUNTEREVIDENCE")

    def test_source_ids_with_nested_list_fail_closed(self):
        self.data["claims"][0]["source_ids"] = [["S-001"]]
        self.assertBlocked("CLAIM_SOURCES")

    def test_malformed_url_fails_closed(self):
        self.data["sources"][0]["url"] = "https://[invalid"
        self.assertBlocked("SOURCE_URL")

    def test_unknown_source_blocks(self):
        self.data["claims"][0]["source_ids"] = ["S-999"]
        self.assertBlocked("CLAIM_SOURCES")

    def test_claim_absent_from_annex_blocks(self):
        new = b"# no mapped claim\n"
        self.data["deliverables"][0]["sha256"] = hashlib.sha256(new).hexdigest()
        self.assertBlocked("ANNEX_MISSING", files={"evidence.md": new})

    def test_unknown_claim_marker_blocks(self):
        new = (ANNEX + "\nUndocumented assertion [C-999] [S-001]\n").encode()
        self.data["deliverables"][0]["sha256"] = hashlib.sha256(new).hexdigest()
        self.assertBlocked("ANNEX_UNKNOWN", files={"evidence.md": new})

    def test_document_modification_blocks(self):
        self.assertBlocked("DOCUMENT_HASH", files={"evidence.md": ANNEX.encode() + b"tamper"})

    def test_path_traversal_blocks(self):
        self.data["deliverables"][0]["path"] = "../evidence.md"
        self.assertBlocked("MISSING_DOC")

    def test_private_client_data_never_in_public_repo(self):
        self.data["classification"] = "client_confidential"
        self.assertBlocked("PUBLIC_DATA", public=True)

    def test_imperative_recommendation_blocks(self):
        self.data["claims"][0]["kind"] = "recommendation"
        self.assertBlocked("DIRECTIVE")

    def test_missed_walkthrough_must_be_no_go(self):
        self.data["opportunities"] = [{"id": "OP-001", "source_id": "S-001", "complete_documents_checked": True,
                                       "addenda_checked": True, "fit": "qualified", "client_eligibility": "confirmed",
                                       "eligibility_basis": "synthetic", "deadline": "2026-11-30",
                                       "mandatory_events": [{"name": "site tour", "status": "missed"}]}]
        self.assertBlocked("MISSED_EVENT")

    def test_unknown_eligibility_blocks_qualified(self):
        self.data["opportunities"] = [{"id": "OP-001", "source_id": "S-001", "complete_documents_checked": True,
                                       "addenda_checked": True, "fit": "qualified", "client_eligibility": "unknown",
                                       "deadline": "2026-11-30", "mandatory_events": []}]
        self.assertBlocked("CLIENT_FIT")

    def test_missing_addenda_blocks(self):
        self.data["opportunities"] = [{"id": "OP-001", "source_id": "S-001", "complete_documents_checked": True,
                                       "addenda_checked": False, "fit": "hold", "mandatory_events": []}]
        self.assertBlocked("OPPORTUNITY_DOCS")

    def test_expired_opportunity_blocks(self):
        self.data["opportunities"] = [{"id": "OP-001", "source_id": "S-001", "complete_documents_checked": True,
                                       "addenda_checked": True, "fit": "qualified", "client_eligibility": "confirmed",
                                       "eligibility_basis": "synthetic", "deadline": "2026-10-31", "mandatory_events": []}]
        self.assertBlocked("EXPIRED_OPPORTUNITY")

    def test_post_release_authorization_cannot_be_embedded(self):
        self.data["publication_authorization"] = True
        self.assertBlocked("PUBLICATION_AUTH")

    def test_detects_common_secret_pattern(self):
        secret = ANNEX + "\n-----BEGIN " + "PRIVATE KEY-----\nfake\n"
        self.data["deliverables"][0]["sha256"] = hashlib.sha256(secret.encode()).hexdigest()
        self.assertBlocked("POSSIBLE_SECRET", files={"evidence.md": secret.encode()})

    def test_corrupt_pdf_trailer_blocks(self):
        raw = b"%PDF-1.7\ncorrupted"
        self.data["deliverables"].append({"path": "report.pdf", "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertBlocked("PDF_STRUCTURE", files={"report.pdf": raw})

    def test_empty_or_invalid_manifest_fails_closed(self):
        (self.folder / "manifest.json").write_text("invalid json")
        result = audit_pack(self.folder, AS_OF)
        self.assertEqual(result["status"], "BLOCK")

    def test_future_source_date_rejected(self):
        self.data["sources"][0]["checked_at"] = "2026-11-06"
        self.assertBlocked("SOURCE_DATE")

    def test_missing_scope_rejected(self):
        self.data["scope"] = ""
        self.assertBlocked("METADATA")

    def test_file_name_with_unhashable_type_fails_closed(self):
        self.data["deliverables"][0]["path"] = ["evidence.md"]
        self.assertBlocked("MISSING_DOC")


class BatchTests(unittest.TestCase):
    def test_parallel_batch_scales_and_blocks_one_bad_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number in range(40):
                folder = root / f"pack-{number:03d}"
                folder.mkdir()
                (folder / "evidence.md").write_text(ANNEX)
                manifest = reviewed(pack())
                if number == 37:
                    manifest.pop("review")
                (folder / "manifest.json").write_text(json.dumps(manifest))
            result = check_many(root, as_of=AS_OF, workers=8, public_repo=True)
            self.assertEqual(result["status"], "BLOCK")
            self.assertEqual(result["total"], 40)
            self.assertEqual(result["passed"], 39)
            self.assertIn("NO_REVIEW", "\n".join(result["results"][37]["errors"]))

    def test_empty_batch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_many(Path(tmp))["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
