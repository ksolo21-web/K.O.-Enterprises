"""Adversarial unit tests using synthetic public metadata only."""
import copy
import unittest
from datetime import date
from company_os.document_quality import REVIEW_CHECKS, evaluate

TODAY = date(2026, 11, 5)


def fixture():
    return {
        "pack_id": "SYNTHETIC-001", "business_unit": "market_intelligence",
        "data_class": "public", "author_id": "analyst-1", "as_of": "2026-11-05",
        "client_context": {"sector": "maintenance contractor", "region": "Southeast Michigan",
                           "constraints": "Synthetic company with limited staff capacity"},
        "document": {
            "summary": "This is a synthetic case for deterministic testing of quality metadata.",
            "scope": "Only fictional eligibility scenarios and invented events are covered here.",
            "method": "The sample uses two independent hypothetical public references as fixtures.",
            "findings": "A fictional procurement opportunity may involve an attendance requirement.",
            "countercase": "The attendance condition could make the opportunity impractical for some firms.",
            "limitations": "These example URLs are not real evidence and must not be issued to customers.",
        },
        "sources": [
            {"id": "S1", "url": "https://example.org/issuer", "publisher": "Example issuer",
             "kind": "issuer", "observed_on": "2026-11-05",
             "excerpt": "Fictitious issuer text to test metadata validation."},
            {"id": "S2", "url": "https://example.net/reference", "publisher": "Example context",
             "kind": "original", "observed_on": "2026-11-05",
             "excerpt": "Independent fabricated test metadata only; not research."},
        ],
        "claims": [
            {"id": "C1", "text": "This hypothetical issuer has an attendance requirement.",
             "importance": "critical", "topic": "procurement", "source_ids": ["S1", "S2"],
             "fact_checked": True, "counter_evidence": "resolved"},
        ],
        "options": [
            {"text": "One option could be to investigate any attendance exemption before proceeding.",
             "tradeoff": "The exemption may not exist and exploring it takes time.",
             "claim_ids": ["C1"]},
        ],
        "critic": {
            "reviewer_id": "critic-2", "reviewed_on": "2026-11-05",
            "score": 9.5, "evidence_ref": "review/sample-001.json",
            "checks": {key: True for key in REVIEW_CHECKS},
        },
    }


class DocumentQualityTests(unittest.TestCase):
    def check(self, mutation=None):
        case = fixture()
        if mutation:
            mutation(case)
        return evaluate(case, today=TODAY)

    def codes(self, mutation):
        return {x["code"] for x in self.check(mutation)["failures"]}

    def test_clean_metadata_still_not_publishable(self):
        result = self.check()
        self.assertEqual(result["status"], "READY_FOR_OWNER_APPROVAL")
        self.assertFalse(result["can_publish"])
        self.assertEqual(result["failures"], [])

    def test_no_auto_authorization(self):
        self.assertFalse(self.check(lambda x: x.update(release_authorization="yes"))["can_publish"])

    def test_missing_evidence(self):
        self.assertIn("MISSING_CITATION", self.codes(lambda x: x["claims"][0].update(source_ids=[])))

    def test_broken_citation(self):
        self.assertIn("BROKEN_CITATION", self.codes(lambda x: x["claims"][0].update(source_ids=["nope"])))

    def test_unresolved_counter_evidence(self):
        self.assertIn("CLAIM_UNCHECKED", self.codes(lambda x: x["claims"][0].update(counter_evidence="open")))

    def test_critical_independence(self):
        self.assertIn("CRITICAL_CORROBORATION", self.codes(lambda x: x["sources"][1].update(url="https://example.org/second")))

    def test_primary_evidence(self):
        def f(x):
            x["sources"][0]["kind"] = "secondary"
            x["sources"][1]["kind"] = "secondary"
        self.assertIn("PRIMARY_EVIDENCE", self.codes(f))

    def test_procurement_issuer(self):
        self.assertIn("OFFICIAL_ISSUER", self.codes(lambda x: x["sources"][0].update(kind="secondary")))

    def test_procurement_freshness(self):
        self.assertIn("STALE_PROCUREMENT", self.codes(lambda x: x["sources"][0].update(observed_on="2026-11-02")))

    def test_prescriptive_option(self):
        self.assertIn("PRESCRIPTIVE_LANGUAGE", self.codes(lambda x: x["options"][0].update(text="You must purchase this specific service immediately.")))

    def test_actual_requirement_not_misrepresented(self):
        self.assertEqual("READY_FOR_OWNER_APPROVAL", self.check(lambda x: x["claims"][0].update(text="The hypothetical issuer requires mandatory attendance."))["status"])

    def test_review_threshold_strict(self):
        self.assertIn("REVIEW_SCORE", self.codes(lambda x: x["critic"].update(score=9.0)))

    def test_reviewer_same_as_author(self):
        self.assertIn("REVIEWER_NOT_INDEPENDENT", self.codes(lambda x: x["critic"].update(reviewer_id="analyst-1")))

    def test_missing_render_review(self):
        self.assertIn("CRITIC_INCOMPLETE", self.codes(lambda x: x["critic"]["checks"].update(rendered_pages=False)))

    def test_secret_detector(self):
        self.assertIn("POSSIBLE_SECRET", self.codes(lambda x: x["document"].update(findings="ghp_" + "T"*30)))

    def test_private_data_blocked(self):
        self.assertIn("PRIVATE_DATA", self.codes(lambda x: x.update(data_class="client_confidential")))

    def test_stale_as_of(self):
        self.assertIn("STALE_REPORT", self.codes(lambda x: x.update(as_of="2026-10-01")))

    def test_missing_section(self):
        self.assertIn("DOCUMENT_SECTION", self.codes(lambda x: x["document"].update(findings="None")))

    def test_unedited_fixture(self):
        case = fixture()
        original = copy.deepcopy(case)
        evaluate(case, today=TODAY)
        self.assertEqual(case, original)

    def test_invalid_input(self):
        self.assertEqual("HOLD", evaluate([], today=TODAY)["status"])


if __name__ == "__main__":
    unittest.main()
