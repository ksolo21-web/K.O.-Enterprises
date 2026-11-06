"""CE-2B manual worker lifecycle, lock, audit and NOT-READY probe tests."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_worker_runtime import (
    probe_offline_worker, run_internal_cycle,
)
from company_os.competitive_work_queue import CompetitiveWorkQueue
from company_os.source_provenance import EvidenceError
import test_competitive_engine_pipeline as fixture_support


class OfflineWorkerRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.now=datetime.now(timezone.utc).replace(microsecond=0)
        env=patch.dict(os.environ,{
            "KO_SOURCE_APPROVED_HOSTS":"issuer.example",
            "COMPANY_OS_PAUSED":"1",
        },clear=False)
        env.start()
        self.addCleanup(env.stop)
        self.queue=CompetitiveWorkQueue(self.root)
        self.addCleanup(self.queue.close)
        self.telemetry_path=(
            self.root/"state"/"competitive_engine"/"work_queue"/"worker_offline_telemetry.json"
        )

    def seed(self,n=3):
        for i in range(1,n+1):
            out=self.queue.submit(fixture_support.synthetic_dossier(self.now,i),now=self.now)
            self.assertEqual(out["state"],"QUEUED_INTERNAL_ONLY")

    def run(self, **kwargs):
        return run_internal_cycle(self.root,now=self.now,**kwargs)

    def test_manual_worker_processes_three_jobs_only_into_review_holds(self):
        self.seed()
        result=self.run(worker_id="manual-ci-worker")
        self.assertEqual(result["jobs_processed"],3)
        self.assertEqual(result["held"],3)
        self.assertEqual(result["blocked"],0)
        self.assertEqual(result["state"],"OFFLINE_INTERNAL_NOT_PRODUCTION_HEALTH")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["publication_authorized"])
        for i in range(1,4):
            self.assertEqual(self.queue.status(f"test-dossier-{i:04d}")["state"],"HELD")

    def test_company_pause_allows_only_explicitly_manual_internal_analysis(self):
        (self.root/"PAUSE_AUTONOMY").write_text("intentionally paused")
        self.seed(1)
        manual=self.run()
        self.assertEqual(manual["held"],1)
        self.assertFalse(manual["production_ready"])

    def test_scheduled_work_is_refused_under_emergency_pause(self):
        self.seed(1)
        outcome=self.run(scheduled=True)
        self.assertEqual(outcome["state"],"BLOCK_SCHEDULED_SERVICE_NOT_AUTHORIZED")
        self.assertEqual(outcome["jobs_processed"],0)
        self.assertFalse(self.telemetry_path.exists())
        self.assertEqual(self.queue.status("test-dossier-0001")["state"],"QUEUED")

    def test_scheduled_work_stays_refused_even_after_pause_env_off(self):
        os.environ["COMPANY_OS_PAUSED"]="0"
        self.seed(1)
        value=self.run(scheduled=True)
        self.assertFalse(value["production_ready"])
        self.assertFalse(self.telemetry_path.exists())

    def test_empty_queue_has_no_implicitly_live_heartbeat(self):
        result=self.run()
        self.assertEqual(result["jobs_processed"],0)
        self.assertFalse(result["independent_critic_observed"])
        self.assertFalse(result["original_source_verification_observed"])
        probe=probe_offline_worker(self.root,now=self.now)
        self.assertFalse(probe["ready"])
        self.assertEqual(probe["locally_observed_jobs"],0)

    def test_real_local_probe_never_claims_production_readiness(self):
        self.seed(1)
        self.run()
        probe=probe_offline_worker(self.root,now=self.now)
        self.assertEqual(probe["state"],"NOT_PRODUCTION_READY")
        self.assertFalse(probe["ready"])
        self.assertFalse(probe["publication_authorized"])
        self.assertTrue(probe["local_telemetry_record_present"])
        self.assertIn("no_operational_independent_critic",probe["reasons"])

    def test_missing_telemetry_is_explicitly_not_ready(self):
        probe=probe_offline_worker(self.root,now=self.now)
        self.assertFalse(probe["ready"])
        self.assertIn("offline_worker_telemetry_unavailable",probe["reasons"])

    def test_stale_telemetry_is_explicitly_not_ready(self):
        self.seed(1)
        self.run()
        probe=probe_offline_worker(self.root,now=self.now+timedelta(minutes=8))
        self.assertFalse(probe["ready"])
        self.assertIn("offline_worker_telemetry_invalid_or_stale",probe["reasons"])

    def test_future_telemetry_is_not_ready(self):
        self.seed(1)
        self.run()
        probe=probe_offline_worker(self.root,now=self.now-timedelta(hours=1))
        self.assertFalse(probe["ready"])

    def test_malicious_production_ready_flag_cannot_elevate_probe(self):
        self.seed(1)
        self.run()
        record=json.loads(self.telemetry_path.read_text())
        record["production_ready"]=True
        self.telemetry_path.write_text(json.dumps(record))
        probe=probe_offline_worker(self.root,now=self.now)
        self.assertFalse(probe["ready"])
        self.assertIn("offline_worker_telemetry_invalid_or_stale",probe["reasons"])

    def test_malicious_independent_critic_claim_cannot_elevate_probe(self):
        self.seed(1)
        self.run()
        record=json.loads(self.telemetry_path.read_text())
        record["independent_critic_observed"]=True
        self.telemetry_path.write_text(json.dumps(record))
        self.assertFalse(probe_offline_worker(self.root,now=self.now)["ready"])

    def test_telemetry_symlink_is_refused(self):
        self.seed(1)
        self.run()
        alias=self.telemetry_path.with_suffix(".saved")
        self.telemetry_path.rename(alias)
        self.telemetry_path.symlink_to(alias)
        probe=probe_offline_worker(self.root,now=self.now)
        self.assertFalse(probe["ready"])

    def test_single_leader_lock_refuses_second_manual_runner(self):
        folder=self.telemetry_path.parent
        fd=os.open(folder/"worker.lock",os.O_RDWR|os.O_CREAT,0o600)
        self.addCleanup(os.close,fd)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.addCleanup(fcntl.flock,fd,fcntl.LOCK_UN)
        self.seed(1)
        result=self.run()
        self.assertEqual(result["state"],"BUSY_ANOTHER_LOCAL_WORKER_OWNS_LEADER_LOCK")
        self.assertEqual(self.queue.status("test-dossier-0001")["state"],"QUEUED")

    def test_leader_lock_symlink_is_refused(self):
        folder=self.telemetry_path.parent
        target=folder/"dangerous"
        target.write_text("sentinel")
        (folder/"worker.lock").symlink_to(target)
        self.seed(1)
        with self.assertRaises(EvidenceError):
            self.run()
        self.assertEqual(target.read_text(),"sentinel")

    def test_invalid_worker_identity_and_job_budget_rejected(self):
        for kwargs in (
            {"worker_id":"../evil"},
            {"worker_id":"x"},
            {"max_jobs":0},
            {"max_jobs":True},
            {"max_jobs":101},
            {"max_seconds":121},
            {"max_seconds":False},
        ):
            with self.subTest(kwargs=kwargs),self.assertRaises(EvidenceError):
                self.run(**kwargs)

    def test_batch_size_limits_and_resume_preserve_all_jobs(self):
        self.seed(13)
        first=self.run(max_jobs=5)
        self.assertEqual(first["held"],5)
        second=self.run(max_jobs=8)
        self.assertEqual(second["held"],8)
        third=self.run()
        self.assertEqual(third["jobs_processed"],0)
        self.assertEqual(self.queue.audit_status()["events"],39)
        self.assertEqual(self.queue.status("test-dossier-0013")["state"],"HELD")

    def test_worker_can_recover_expired_lease_but_not_steal_live_lease(self):
        self.seed(1)
        original=self.queue.lease(owner="crashed-worker",now=self.now,seconds=10)
        first=self.run()
        self.assertEqual(first["jobs_processed"],0)
        later=run_internal_cycle(self.root,now=self.now+timedelta(seconds=11))
        self.assertEqual(later["held"],1)
        self.assertEqual(self.queue.status(original["job_id"])["generation"],2)

    def test_old_source_dossier_can_only_end_blocked(self):
        self.seed(1)
        later=run_internal_cycle(self.root,now=self.now+timedelta(days=32))
        self.assertEqual(later["blocked"],1)
        self.assertEqual(self.queue.status("test-dossier-0001")["state"],"BLOCKED")
        self.assertFalse(later["publication_authorized"])

    def test_100_dossier_runner_with_one_blocked_at_intake(self):
        accepted=0
        for i in range(1,101):
            candidate=fixture_support.synthetic_dossier(self.now,i)
            if i==58:
                candidate["sources"][0]["url"]="http://untrusted.invalid/original"
            submission=self.queue.submit(candidate,now=self.now)
            if i==58:
                self.assertEqual(submission["state"],"BLOCK_INVALID_DOSSIER")
            else:
                self.assertEqual(submission["state"],"QUEUED_INTERNAL_ONLY")
                accepted+=1
        self.assertEqual(accepted,99)
        result=self.run(max_jobs=100,max_seconds=120)
        self.assertEqual(result["held"],99)
        self.assertEqual(result["jobs_processed"],99)
        self.assertFalse(result["production_ready"])
        self.assertEqual(self.queue.audit_status()["events"],297)
        self.assertEqual(self.queue.status("test-dossier-0058")["state"],"NOT_FOUND")

    def test_worker_has_no_external_source_or_release_operation(self):
        import company_os.competitive_worker_runtime as w
        self.assertFalse(hasattr(w,"fetch_and_capture"))
        self.assertFalse(hasattr(w,"publish"))
        self.assertFalse(hasattr(w,"deploy"))
        self.assertFalse(hasattr(w,"send_email"))


if __name__=="__main__":
    unittest.main()
