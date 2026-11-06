"""CE-1F / CE-2A competitive evaluation and durable queue regression suite."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_evidence_engine import assess_competitive_dossier, evaluate_file
from company_os.competitive_work_queue import CompetitiveWorkQueue
from company_os.source_provenance import EvidenceError


def synthetic_dossier(now: datetime, n: int = 1) -> dict:
    def source(ident, origin, kind, grade, text):
        return {
            "id": ident, "publisher": "SYNTHETIC " + origin,
            "origin_id": origin, "url": "https://issuer.example/" + ident,
            "observed_at": now.isoformat(), "sha256": hashlib.sha256(
                text.encode()
            ).hexdigest(),
            "kind": kind, "grade": grade, "rights_basis": "public_access",
            "excerpt": text, "capture_type": "operator_supplied",
        }
    def claim(ident, category, sid, fact, value, *, counter=None,
              material="standard"):
        return {
            "id": ident, "text": "Synthetic claim: " + ident + " is not verified",
            "source_ids": sid, "counter_source_ids": counter or [],
            "classification": category, "materiality": material,
            "fact_key": fact, "observed_value": value,
            "limitations": "Synthetic local operator claims, not independent facts",
        }
    return {
        "schema_version": "1.0", "dossier_id": f"test-dossier-{n:04d}",
        "venture_id": "market-intelligence",
        "author_id": "synthetic-analyst",
        "prepared_at": now.isoformat(),
        "buyer_segment": "Southeast Michigan facility contractors",
        "buyer_problem": "Synthetic contractors lack timely source verification",
        "geography": "Southeast Michigan",
        "limitations": "Entirely fictional example for offline governance testing",
        "sources": [
            source("svendor1", "vendor-one", "vendor_original", "A",
                   "Provider claims an original source feature is offered"),
            source("svendor2", "vendor-two", "vendor_original", "B",
                   "Another provider describes a competing package offering"),
            source("sbuyer", "buyer-one", "buyer_firsthand", "B",
                   "Buyer reports a synthetic document review problem today"),
            source("sindependent", "review-one", "secondary", "B",
                   "Independent synthetic observation repeats document difficulty"),
            source("scounter", "vendor-three", "vendor_original", "C",
                   "Counterexample claims incumbent supports new changes"),
        ],
        "claims": [
            claim("cstrength", "strength", ["svendor1"], "strength-feature", "provided"),
            claim("cweakness", "weakness", ["sbuyer", "sindependent"], "weakness-lag",
                  "reported", counter=["scounter"]),
            claim("cbuyer", "buyer_value", ["sbuyer"], "buyer-need", "perceived"),
            claim("ccounter", "contrary", ["scounter"], "counter-case", "supported"),
            claim("ccost", "cost", ["svendor2"], "cost-basis", "estimated"),
        ],
        "alternatives": [
            {
                "id": f"alternative-{idx}", "name": f"Fictional provider {idx}",
                "offering_tier": "Small facility contractor",
                "buyer_segment": "Southeast Michigan facility contractors",
                "geography": "Southeast Michigan",
                "strength_claim_ids": ["cstrength"],
                "weakness_claim_ids": ["cweakness"],
            }
            for idx in range(1, 4)
        ],
        "advantages": [{
            "id": "advantage-one",
            "buyer_outcome": "Reduce synthetic sourcing errors",
            "compared_alternative_ids": ["alternative-1", "alternative-2"],
            "support_claim_ids": ["cbuyer"],
            "contrary_claim_ids": ["ccounter"],
            "expected_price_cents": 25000,
            "estimated_delivery_cost_cents": 11500,
            "buyer_payment_state": "paid_pilot_reported",
            "buyer_payment_evidence_ids": ["sbuyer"],
            "switching_friction": "Customers may prefer incumbent bundled tools",
        }],
    }


class CompetitiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.env = patch.dict(os.environ, {
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "COMPANY_OS_PAUSED": "1",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.d = synthetic_dossier(self.now)

    def check(self, data=None):
        return assess_competitive_dossier(data or self.d, now=self.now)

    def test_complete_dossier_can_only_be_held_for_real_independent_critic(self):
        result = self.check()
        self.assertEqual(result["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW")
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["original_sources_independently_authenticated"])
        self.assertFalse(result["paid_demand_independently_verified"])
        self.assertFalse(result["independent_critic_approved"])
        self.assertEqual(result["alternatives_compared"], 3)
        self.assertEqual(result["advantage_hypotheses"], 1)

    def test_same_dossier_digest_is_deterministic(self):
        self.assertEqual(self.check()["dossier_sha256"], self.check()["dossier_sha256"])

    def test_older_source_held_or_blocked(self):
        self.d["sources"][0]["observed_at"] = (self.now-timedelta(days=31)).isoformat()
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_future_source_rejected(self):
        self.d["sources"][0]["observed_at"] = (self.now+timedelta(hours=1)).isoformat()
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_wrong_source_host_rejected(self):
        self.d["sources"][0]["url"] = "https://untrusted.example/fake"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_no_source_host_registry_fails_closed(self):
        del os.environ["KO_SOURCE_APPROVED_HOSTS"]
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_unsupported_source_authentication_claim_rejected(self):
        self.d["sources"][0]["capture_type"] = "independently_verified_original_issuer"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_missing_source_original_hash_rejected(self):
        self.d["sources"][0]["sha256"] = "not-an-original-hash"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_duplicate_claim_rejected(self):
        self.d["claims"].append(copy.deepcopy(self.d["claims"][0]))
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_missing_registered_claim_source_blocks(self):
        self.d["claims"][0]["source_ids"] = ["does-not-exist"]
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_two_competitors_not_a_balanced_comparison(self):
        self.d["alternatives"].pop()
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_comparator_wrong_geography_not_like_for_like(self):
        self.d["alternatives"][1]["geography"] = "New York"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_competitor_strength_cannot_use_weakness_claim(self):
        self.d["alternatives"][0]["strength_claim_ids"] = ["cweakness"]
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_unsupported_weakness_with_one_origin_blocks(self):
        for s in self.d["sources"]:
            if s["id"] == "sindependent":
                s["origin_id"] = "buyer-one"
        v = self.check()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("weakness_lacks_independent_corrob:cweakness", v["issues"])

    def test_competitor_weakness_without_counterevidence_blocks(self):
        self.d["claims"][1]["counter_source_ids"] = []
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_hypothetical_grade_d_cannot_upgrade_weakness(self):
        self.d["sources"][2]["grade"] = "D"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_contradictory_values_same_fact_key_block(self):
        self.d["claims"][4]["fact_key"] = "weakness-lag"
        self.d["claims"][4]["observed_value"] = "no reported lag"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_negative_contribution_margin_blocks(self):
        self.d["advantages"][0]["estimated_delivery_cost_cents"] = 50000
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_bool_is_not_valid_money(self):
        self.d["advantages"][0]["expected_price_cents"] = True
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_unsupported_customer_payment_claim_blocks(self):
        self.d["advantages"][0]["buyer_payment_state"] = "verified_payment"
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_operator_claimed_paid_pilot_without_evidence_is_flagged(self):
        self.d["advantages"][0]["buyer_payment_evidence_ids"] = []
        result = self.check()
        self.assertEqual(result["status"], "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW")
        self.assertIn("reported_paid_pilot_without_firsthand_evidence:advantage-one", result["issues"])
        self.assertFalse(result["paid_demand_independently_verified"])

    def test_missing_paid_demand_is_explicitly_flagged(self):
        self.d["advantages"][0]["buyer_payment_state"] = "untested"
        result = self.check()
        self.assertIn("no_paid_pilot_independently_authenticated", result["issues"])

    def test_material_claim_requires_original_source(self):
        self.d["claims"][1]["materiality"] = "deadline"
        self.d["claims"][1]["source_ids"] = ["sindependent"]
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_material_source_older_than_a_day_is_flagged(self):
        self.d["claims"][0]["materiality"] = "financial"
        self.d["sources"][0]["observed_at"] = (self.now-timedelta(days=2)).isoformat()
        result = self.check()
        self.assertIn("material_claim_source_older_than_one_day:cstrength", result["issues"])

    def test_extra_hidden_claim_field_blocked(self):
        self.d["claims"][0]["guarantee"] = True
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_expired_dossier_timestamp_blocks(self):
        self.d["prepared_at"] = (self.now-timedelta(days=2)).isoformat()
        self.assertEqual(self.check()["status"], "BLOCK")

    def test_naive_asof_time_blocks(self):
        self.assertEqual(
            assess_competitive_dossier(self.d, now=datetime(2026,11,5))["status"],
            "BLOCK",
        )

    def test_duplicate_json_fields_rejected_from_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"dossier.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
            self.assertEqual(evaluate_file(path, now=self.now)["status"], "BLOCK")

    def test_nan_json_fields_rejected_from_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"dossier.json"
            path.write_text('{"schema_version": NaN}')
            self.assertEqual(evaluate_file(path, now=self.now)["status"], "BLOCK")

    def test_file_path_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"source.json"
            source.write_text(json.dumps(self.d))
            alias = Path(folder)/"alias.json"
            alias.symlink_to(source)
            self.assertEqual(evaluate_file(alias, now=self.now)["status"], "BLOCK")

    def test_no_api_fetch_or_business_release(self):
        from company_os import competitive_evidence_engine as e
        self.assertFalse(hasattr(e, "publish"))
        self.assertFalse(hasattr(e, "launch_venture"))
        self.assertFalse(hasattr(e, "fetch_and_capture"))


class CompetitiveQueueTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "COMPANY_OS_PAUSED": "1",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.q = CompetitiveWorkQueue(self.root)
        self.addCleanup(self.q.close)

    def submit(self, n=1):
        return self.q.submit(synthetic_dossier(self.now, n), now=self.now)

    def test_normal_internal_job_stays_held_after_execution(self):
        self.assertEqual(self.submit()["state"], "QUEUED_INTERNAL_ONLY")
        lease = self.q.lease(owner="worker-one", now=self.now)
        self.assertEqual(lease["state"], "LEASED_INTERNAL_ONLY")
        self.assertEqual(lease["generation"], 1)
        done = self.q.complete(job_id=lease["job_id"],owner=lease["owner"],
                               generation=lease["generation"],now=self.now)
        self.assertEqual(done["state"], "HELD")
        self.assertFalse(done["publication_authorized"])
        self.assertEqual(self.q.status("test-dossier-0001")["state"], "HELD")
        self.assertEqual(self.q.audit_status()["events"], 3)

    def test_paused_company_permits_internal_tests_not_publication(self):
        (self.root/"PAUSE_AUTONOMY").write_text("intentionally paused")
        self.submit()
        lease = self.q.lease(owner="worker-one",now=self.now)
        result = self.q.complete(job_id=lease["job_id"],owner=lease["owner"],
                                 generation=1,now=self.now)
        self.assertFalse(result["publication_authorized"])

    def test_reusing_same_job_id_and_content_idempotent(self):
        self.submit()
        prior = self.submit()
        self.assertEqual(prior["state"], "IDEMPOTENT_EXISTING_QUEUED")
        self.assertEqual(self.q.audit_status()["events"],1)

    def test_reusing_job_id_with_changed_payload_fails(self):
        self.submit()
        revised = synthetic_dossier(self.now)
        revised["buyer_problem"] = "A different synthetic buyer episode"
        with self.assertRaises(EvidenceError):
            self.q.submit(revised,now=self.now)

    def test_bad_dossier_fails_before_queue(self):
        invalid = synthetic_dossier(self.now, 18)
        invalid["alternatives"].pop()
        out=self.q.submit(invalid,now=self.now)
        self.assertEqual(out["state"],"BLOCK_INVALID_DOSSIER")
        self.assertEqual(self.q.audit_status()["events"],0)

    def test_second_worker_cannot_lease_active_job(self):
        self.submit()
        self.q.lease(owner="worker-one",now=self.now)
        self.assertIsNone(self.q.lease(owner="worker-two",now=self.now))

    def test_crashed_job_recovered_after_lease_timeout(self):
        self.submit()
        old=self.q.lease(owner="worker-one",now=self.now,seconds=12)
        self.assertIsNone(self.q.lease(owner="worker-two",now=self.now+timedelta(seconds=11)))
        newer=self.q.lease(owner="worker-two",now=self.now+timedelta(seconds=13))
        self.assertEqual(newer["generation"],2)
        with self.assertRaises(EvidenceError):
            self.q.complete(job_id=old["job_id"],owner=old["owner"],
                            generation=old["generation"],now=self.now+timedelta(seconds=13))
        done=self.q.complete(job_id=newer["job_id"],owner=newer["owner"],
                             generation=newer["generation"],now=self.now+timedelta(seconds=13))
        self.assertEqual(done["state"],"HELD")

    def test_wrong_worker_and_generation_cannot_complete(self):
        self.submit()
        lease=self.q.lease(owner="worker-one",now=self.now)
        for owner,generation in [("worker-two",1),("worker-one",2)]:
            with self.subTest(owner=owner,generation=generation),self.assertRaises(EvidenceError):
                self.q.complete(job_id=lease["job_id"],owner=owner,generation=generation,now=self.now)

    def test_expired_worker_cannot_commit(self):
        self.submit()
        lease=self.q.lease(owner="worker-one",now=self.now,seconds=10)
        with self.assertRaises(EvidenceError):
            self.q.complete(job_id=lease["job_id"],owner=lease["owner"],
                            generation=1,now=self.now+timedelta(seconds=11))

    def test_retry_backoff_then_dead_letter_after_three_attempts(self):
        self.submit()
        for n in range(1,4):
            when=self.now+timedelta(seconds=n*50)
            lease=self.q.lease(owner="worker-one",now=when,seconds=10)
            self.assertEqual(lease["generation"],n)
            failure=self.q.fail(job_id=lease["job_id"],owner=lease["owner"],
                                generation=n,reason_code="worker-fault",
                                now=when,retry_seconds=10)
            self.assertEqual(failure["state"],"DEAD" if n==3 else "QUEUED")
        self.assertIsNone(self.q.lease(owner="worker-two",
                                      now=self.now+timedelta(seconds=300)))

    def test_invalid_lease_ttl_refused(self):
        self.submit()
        for secs in (0,True,10000):
            with self.assertRaises(EvidenceError):
                self.q.lease(owner="worker-one",seconds=secs,now=self.now)

    def test_unknown_completion_refused(self):
        with self.assertRaises(EvidenceError):
            self.q.complete(job_id="missing-job",owner="worker-one",
                            generation=1,now=self.now)

    def test_poison_payload_modification_prevents_lease(self):
        self.submit()
        self.q.db.execute("UPDATE jobs SET payload='{}'")
        with self.assertRaises(EvidenceError):
            self.q.lease(owner="worker-one",now=self.now)
        self.assertEqual(self.q.audit_status()["events"],1)

    def test_hash_chain_sql_tamper_detected(self):
        self.submit()
        self.q.db.execute("DROP TRIGGER events_append_only_update")
        self.q.db.execute("UPDATE events SET event_sha='0' WHERE seq=1")
        with self.assertRaises(EvidenceError):
            self.q.audit_status()

    def test_append_only_triggers_reject_update_and_delete(self):
        self.submit()
        for sql in ("DELETE FROM events WHERE seq=1",
                    "UPDATE events SET event_sha='0' WHERE seq=1"):
            with self.subTest(sql=sql),self.assertRaises(sqlite3.DatabaseError):
                self.q.db.execute(sql)

    def test_database_symlink_refused(self):
        self.q.close()
        self.addCleanup(lambda:None)
        path=self.q.path
        actual=path.with_suffix(".saved")
        path.rename(actual)
        path.symlink_to(actual)
        with self.assertRaises(EvidenceError):
            CompetitiveWorkQueue(self.root)

    def test_100_dossier_dry_run_with_one_deliberate_defect(self):
        count_accepted=0
        for n in range(1,101):
            candidate=synthetic_dossier(self.now,n)
            if n==37:
                candidate["alternatives"]=[]
            out=self.q.submit(candidate,now=self.now)
            if n==37:
                self.assertEqual(out["state"],"BLOCK_INVALID_DOSSIER")
            else:
                self.assertEqual(out["state"],"QUEUED_INTERNAL_ONLY")
                count_accepted+=1
        self.assertEqual(count_accepted,99)
        finished=0
        while True:
            job=self.q.lease(owner="worker-one",now=self.now)
            if job is None:
                break
            outcome=self.q.complete(job_id=job["job_id"],owner=job["owner"],
                                    generation=job["generation"],now=self.now)
            self.assertEqual(outcome["state"],"HELD")
            self.assertFalse(outcome["publication_authorized"])
            finished+=1
        self.assertEqual(finished,99)
        self.assertEqual(self.q.audit_status()["events"],297)
        self.assertEqual(self.q.status("test-dossier-0037")["state"],"NOT_FOUND")
        self.assertEqual(self.q.status("test-dossier-0100")["state"],"HELD")
        self.assertFalse(self.q.audit_status()["publication_authorized"])


if __name__=="__main__":
    unittest.main()
