"""CE-1G adversarial tests for exact comparator-to-source attribution.

All data are fictional and operator supplied; no network, release or real
independent critic is simulated or authorized.
"""
from __future__ import annotations

import copy
import hashlib
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from company_os.competitive_evidence_engine import assess_competitive_dossier
from test_competitive_engine_pipeline import synthetic_dossier


def attributed_dossier(now):
    dossier = synthetic_dossier(now, 751)
    dossier["schema_version"] = "1.1"
    # Three generic research sources remain for buyer-value, contrary and
    # delivery-cost hypotheses. They cannot authenticate vendor performance.
    dossier["sources"] = [
        s for s in dossier["sources"]
        if s["id"] in ("svendor2", "sbuyer", "scounter")
    ]
    for source in dossier["sources"]:
        source["applies_to_alternative_id"] = None
    dossier["claims"] = [
        c for c in dossier["claims"]
        if c["id"] in ("cbuyer", "ccounter", "ccost")
    ]
    for claim in dossier["claims"]:
        claim["applies_to_alternative_id"] = None

    def source(sid, subject, kind, origin):
        excerpt = "Synthetic source describing " + sid + " for " + subject
        return {
            "id": sid,
            "publisher": "Synthetic " + origin,
            "origin_id": origin,
            "url": "https://issuer.example/" + sid,
            "observed_at": now.isoformat(),
            "sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
            "kind": kind,
            "grade": "B",
            "rights_basis": "public_access",
            "excerpt": excerpt,
            "capture_type": "operator_supplied",
            "applies_to_alternative_id": subject,
        }

    def claim(cid, subject, classification, evidence, counter):
        return {
            "id": cid,
            "text": "Synthetic claim limited to comparator " + subject,
            "source_ids": evidence,
            "counter_source_ids": counter,
            "classification": classification,
            "materiality": "standard",
            "fact_key": cid,
            "observed_value": "fictional operator statement",
            "limitations": "Not independently authenticated or fit for publication",
            "applies_to_alternative_id": subject,
        }

    for idx, alternative in enumerate(dossier["alternatives"], 1):
        aid = alternative["id"]
        for sid, kind, origin in (
            (f"vendor-{idx}", "vendor_original", f"vendor-origin-{idx}"),
            (f"buyer-{idx}", "buyer_firsthand", f"buyer-origin-{idx}"),
            (f"secondary-{idx}", "secondary", f"secondary-origin-{idx}"),
            (f"counter-{idx}", "vendor_original", f"counter-origin-{idx}"),
        ):
            dossier["sources"].append(source(sid, aid, kind, origin))
        strength = f"strength-{idx}"
        weakness = f"weakness-{idx}"
        dossier["claims"].append(claim(
            strength, aid, "strength", [f"vendor-{idx}"], [],
        ))
        dossier["claims"].append(claim(
            weakness, aid, "weakness",
            [f"buyer-{idx}", f"secondary-{idx}"], [f"counter-{idx}"],
        ))
        alternative["strength_claim_ids"] = [strength]
        alternative["weakness_claim_ids"] = [weakness]
    return dossier


class ComparatorAttributionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.env = patch.dict(os.environ, {
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "COMPANY_OS_PAUSED": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.dossier = attributed_dossier(self.now)

    def assess(self, dossier=None):
        return assess_competitive_dossier(
            self.dossier if dossier is None else dossier, now=self.now,
        )

    def assert_blocked(self):
        report = self.assess()
        self.assertEqual(report["status"], "BLOCK", report)
        self.assertFalse(report["publication_authorized"])

    def test_distinct_comparator_source_chain_remains_only_internal_hold(self):
        result = self.assess()
        self.assertEqual(
            result["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW",
        )
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["original_sources_independently_authenticated"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertNotIn("legacy_comparator_attribution_unverified", result["issues"])

    def test_legacy_dossier_is_explicitly_flagged_as_unattributed(self):
        legacy = synthetic_dossier(self.now, 752)
        result = self.assess(legacy)
        self.assertEqual(
            result["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW",
        )
        self.assertIn("legacy_comparator_attribution_unverified", result["issues"])
        self.assertFalse(result["publication_authorized"])

    def test_one_vendor_claim_cannot_support_three_different_competitors(self):
        self.dossier["alternatives"][1]["strength_claim_ids"] = ["strength-1"]
        self.assert_blocked()

    def test_one_weakness_cannot_be_reused_for_another_competitor(self):
        self.dossier["alternatives"][2]["weakness_claim_ids"] = ["weakness-1"]
        self.assert_blocked()

    def test_strength_source_from_another_vendor_is_blocked(self):
        self.dossier["claims"][3]["source_ids"] = ["vendor-2"]
        self.assert_blocked()

    def test_weakness_evidence_must_match_competitor(self):
        self.dossier["claims"][4]["source_ids"] = ["buyer-2", "secondary-1"]
        self.assert_blocked()

    def test_counterexample_must_match_competitor(self):
        self.dossier["claims"][4]["counter_source_ids"] = ["counter-2"]
        self.assert_blocked()

    def test_missing_competitor_claim_subject_is_blocked(self):
        self.dossier["claims"][3]["applies_to_alternative_id"] = None
        self.assert_blocked()

    def test_missing_competitor_source_subject_is_blocked(self):
        for source in self.dossier["sources"]:
            if source["id"] == "vendor-1":
                source["applies_to_alternative_id"] = None
        self.assert_blocked()

    def test_unknown_claim_subject_is_blocked(self):
        self.dossier["claims"][3]["applies_to_alternative_id"] = "unregistered-firm"
        self.assert_blocked()

    def test_unknown_source_subject_is_blocked(self):
        for source in self.dossier["sources"]:
            if source["id"] == "vendor-1":
                source["applies_to_alternative_id"] = "unregistered-firm"
        self.assert_blocked()

    def test_competitor_strength_requires_vendor_original(self):
        self.dossier["claims"][3]["source_ids"] = ["buyer-1"]
        self.assert_blocked()

    def test_claim_subject_may_not_be_an_untrusted_list(self):
        self.dossier["claims"][3]["applies_to_alternative_id"] = ["alternative-1"]
        self.assert_blocked()

    def test_old_schema_cannot_smuggle_v11_attribution_fields(self):
        old = synthetic_dossier(self.now, 753)
        old["sources"][0]["applies_to_alternative_id"] = "alternative-1"
        result = self.assess(old)
        self.assertEqual(result["status"], "BLOCK")

    def test_v11_missing_subject_field_is_blocked(self):
        del self.dossier["claims"][3]["applies_to_alternative_id"]
        self.assert_blocked()

    def test_v11_extra_unregistered_field_is_blocked(self):
        self.dossier["sources"][0]["verified_by_issuer"] = True
        self.assert_blocked()

    def test_same_source_url_reassigned_to_second_competitor_blocks(self):
        vendor_one = next(s for s in self.dossier["sources"] if s["id"] == "vendor-1")
        vendor_two = next(s for s in self.dossier["sources"] if s["id"] == "vendor-2")
        vendor_two["url"] = vendor_one["url"]
        self.assert_blocked()

    def test_same_source_bytes_reassigned_to_second_competitor_blocks(self):
        vendor_one = next(s for s in self.dossier["sources"] if s["id"] == "vendor-1")
        vendor_two = next(s for s in self.dossier["sources"] if s["id"] == "vendor-2")
        vendor_two["sha256"] = vendor_one["sha256"]
        self.assert_blocked()

    def test_generic_buyer_claim_cannot_cite_named_vendor_source(self):
        claim = next(c for c in self.dossier["claims"] if c["id"] == "cbuyer")
        claim["source_ids"] = ["vendor-1"]
        self.assert_blocked()

    def test_generic_cost_claim_cannot_cite_named_vendor_source(self):
        claim = next(c for c in self.dossier["claims"] if c["id"] == "ccost")
        claim["source_ids"] = ["vendor-2"]
        self.assert_blocked()

    def test_generic_contrary_claim_cannot_cite_named_counterexample(self):
        claim = next(c for c in self.dossier["claims"] if c["id"] == "ccounter")
        claim["source_ids"] = ["counter-1"]
        self.assert_blocked()

    def test_named_cost_claim_accepts_matching_source_but_not_publication(self):
        claim = next(c for c in self.dossier["claims"] if c["id"] == "ccost")
        claim["applies_to_alternative_id"] = "alternative-1"
        claim["source_ids"] = ["vendor-1"]
        report = self.assess()
        self.assertEqual(report["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW")
        self.assertFalse(report["publication_authorized"])

    def test_named_cost_claim_rejects_other_vendor_source(self):
        claim = next(c for c in self.dossier["claims"] if c["id"] == "ccost")
        claim["applies_to_alternative_id"] = "alternative-1"
        claim["source_ids"] = ["vendor-2"]
        self.assert_blocked()

    def test_rival_buyer_statement_cannot_substitute_for_own_paid_pilot(self):
        self.dossier["advantages"][0]["buyer_payment_evidence_ids"] = ["buyer-1"]
        self.assert_blocked()

    def test_generic_record_cannot_reuse_named_vendor_url(self):
        generic = next(s for s in self.dossier["sources"] if s["id"] == "svendor2")
        named = next(s for s in self.dossier["sources"] if s["id"] == "vendor-1")
        generic["url"] = named["url"]
        self.assert_blocked()

    def test_generic_record_cannot_reuse_named_vendor_digest(self):
        generic = next(s for s in self.dossier["sources"] if s["id"] == "svendor2")
        named = next(s for s in self.dossier["sources"] if s["id"] == "vendor-1")
        generic["sha256"] = named["sha256"]
        self.assert_blocked()

    def test_named_vendor_cannot_reuse_generic_record_url(self):
        generic = next(s for s in self.dossier["sources"] if s["id"] == "svendor2")
        named = next(s for s in self.dossier["sources"] if s["id"] == "vendor-1")
        named["url"] = generic["url"]
        self.assert_blocked()

    def test_advantage_cannot_support_claim_about_uncompared_vendor(self):
        self.dossier["advantages"][0]["support_claim_ids"].append("strength-3")
        self.assert_blocked()

    def test_advantage_cannot_hide_uncompared_vendor_in_counter_claim(self):
        self.dossier["advantages"][0]["contrary_claim_ids"].append("weakness-3")
        self.assert_blocked()

    def test_advantage_can_use_named_claim_for_compared_vendor(self):
        self.dossier["advantages"][0]["support_claim_ids"].append("strength-1")
        report = self.assess()
        self.assertEqual(report["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW")
        self.assertFalse(report["publication_authorized"])

    def test_same_fact_key_with_different_vendors_is_not_a_contradiction(self):
        first = next(c for c in self.dossier["claims"] if c["id"] == "strength-1")
        second = next(c for c in self.dossier["claims"] if c["id"] == "strength-2")
        first["fact_key"] = second["fact_key"] = "shared-feature"
        first["observed_value"] = "present"
        second["observed_value"] = "absent"
        report = self.assess()
        self.assertEqual(report["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW")
        self.assertFalse(any(s.startswith("contradictory_unreconciled_values") for s in report["issues"]))

    def test_conflicting_values_about_same_vendor_still_block(self):
        first = next(c for c in self.dossier["claims"] if c["id"] == "strength-1")
        second = next(c for c in self.dossier["claims"] if c["id"] == "weakness-1")
        second["fact_key"] = first["fact_key"]
        second["observed_value"] = "incompatible-value"
        report = self.assess()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn(
            "contradictory_unreconciled_values:alternative-1:strength-1",
            report["issues"],
        )

    def test_attributed_data_does_not_change_global_release_controls(self):
        from company_os.competitive_launch_guard import (
            PRODUCTION_RELEASE_CONTROLLER_CERTIFIED,
        )
        self.assertIs(PRODUCTION_RELEASE_CONTROLLER_CERTIFIED, False)
        self.assertFalse(self.assess()["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
