"""CE-1J: source-ledger/queue integration, all offline synthetic captures."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from company_os.competitive_source_binding import inspect_source_bindings
from company_os.competitive_work_queue import CompetitiveWorkQueue
from company_os.source_provenance import EvidenceError, SourceLedger
from test_competitive_engine_pipeline import synthetic_dossier


KIND = {
    "issuer_original": "issuer_primary",
    "vendor_original": "company_self_claim",
    "buyer_firsthand": "other",
    "secondary": "independent_secondary",
}


class ProvenanceBoundQueueTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict(os.environ, {
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "COMPANY_OS_PAUSED": "1",
        })
        env.start()
        self.addCleanup(env.stop)
        self.d = synthetic_dossier(self.now, 921)
        self.ledger = SourceLedger(self.root)
        self.addCleanup(self.ledger.close)
        self.bindings = {}
        for src in self.d["sources"]:
            rec = self.record(src)
            self.bindings[src["id"]] = rec.snapshot_id
        self.queue = CompetitiveWorkQueue(self.root)
        self.addCleanup(self.queue.close)

    def record(self, src, *, quote=None, raw=None, observed=None, complete=True):
        quote = src["excerpt"] if quote is None else quote
        raw = src["excerpt"].encode("utf-8") if raw is None else raw
        observed = self.now if observed is None else observed
        return self.ledger.capture(
            document_id=src["id"], url=src["url"],
            allowed_hosts=["issuer.example"],
            publisher=src["publisher"], title="Synthetic capture for " + src["id"],
            origin_id=src["origin_id"], source_kind=KIND[src["kind"]],
            acquisition_method="operator_supplied",
            acquisition_reference="offline-fixture-" + src["id"],
            rights_basis="public_access", observed_at=observed,
            raw=raw, media_type="text/plain", evidence_excerpt=quote,
            complete_document=complete, now=max(self.now, observed),
        )

    def submit(self, d=None, bindings=None):
        return self.queue.submit(
            self.d if d is None else d,
            source_bindings=self.bindings if bindings is None else bindings,
            now=self.now,
        )

    def complete(self, at=None):
        when = self.now if at is None else at
        lease = self.queue.lease(owner="test-worker", now=when)
        self.assertIsNotNone(lease)
        return self.queue.complete(
            job_id=lease["job_id"], owner=lease["owner"],
            generation=lease["generation"], now=when,
        )

    def test_all_captured_sources_queue_and_complete_on_internal_hold(self):
        self.assertEqual(self.submit()["state"], "QUEUED_INTERNAL_ONLY")
        receipt = self.queue.db.execute(
            "SELECT bindings_sha FROM source_bindings WHERE job_id=?",
            (self.d["dossier_id"],),
        ).fetchone()
        self.assertEqual(len(receipt[0]), 64)
        self.assertEqual(self.complete()["state"], "HELD")
        snap = self.queue.verified_snapshot(self.d["dossier_id"])
        self.assertEqual(snap["state"], "HELD_VERIFIED_DIGEST_ONLY")
        self.assertFalse(snap["publication_authorized"])

    def test_local_snapshot_integrity_is_hold_not_issuer_authentication(self):
        out = inspect_source_bindings(self.root, self.d, self.bindings, now=self.now)
        self.assertEqual(out["matched_sources"], len(self.d["sources"]))
        self.assertFalse(out["original_sources_independently_authenticated"])
        self.assertFalse(out["publication_authorized"])
        self.assertTrue(out["status"].startswith("HOLD_"))

    def test_missing_one_source_binding_fails_without_queued_job(self):
        bad = dict(self.bindings)
        bad.pop("sbuyer")
        with self.assertRaises(EvidenceError):
            self.submit(bindings=bad)
        self.assertEqual(self.queue.audit_status()["events"], 0)

    def test_unknown_snapshot_digest_fails(self):
        bad = dict(self.bindings)
        bad["sbuyer"] = "0" * 64
        with self.assertRaises(EvidenceError):
            self.submit(bindings=bad)

    def test_one_snapshot_cannot_be_claimed_by_two_local_source_ids(self):
        bad = dict(self.bindings)
        bad["sbuyer"] = bad["svendor1"]
        with self.assertRaises(EvidenceError):
            self.submit(bindings=bad)

    def test_source_original_bytes_hash_mismatch_blocks(self):
        self.d["sources"][0]["sha256"] = "f" * 64
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_source_claimed_excerpt_drift_blocks(self):
        self.d["sources"][0]["excerpt"] = "Fabricated excerpt not in recorded source"
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_source_publisher_drift_blocks(self):
        self.d["sources"][0]["publisher"] = "Different invented publisher"
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_source_origin_drift_blocks(self):
        self.d["sources"][0]["origin_id"] = "unrelated-actor"
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_source_timestamp_drift_blocks(self):
        self.d["sources"][0]["observed_at"] = (
            self.now - timedelta(hours=1)
        ).isoformat()
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_operator_cannot_inflate_local_record_to_signed_capture(self):
        self.d["sources"][0]["capture_type"] = "local_staging_receipt"
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_scope_of_licensing_cannot_be_inferred_from_public_record(self):
        self.d["sources"][0]["rights_basis"] = "owner_authorized"
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_queued_job_cannot_drop_its_binding_on_replay(self):
        self.submit()
        with self.assertRaises(EvidenceError):
            self.queue.submit(self.d, now=self.now)
        self.assertEqual(self.queue.audit_status()["events"], 1)

    def test_unbound_old_job_cannot_be_relabelled_as_bound(self):
        self.queue.submit(self.d, now=self.now)
        with self.assertRaises(EvidenceError):
            self.submit()

    def test_replay_with_altered_binding_refuses_same_job_id(self):
        self.submit()
        changed = dict(self.bindings)
        changed["sbuyer"] = "1" * 64
        with self.assertRaises(EvidenceError):
            self.submit(bindings=changed)

    def test_capture_revision_after_queueing_blocks_completion(self):
        self.submit()
        src = self.d["sources"][0]
        changed_text = "Revised synthetic source now changes what the provider offers"
        self.record(src, quote=changed_text, raw=changed_text.encode(),
                    observed=self.now + timedelta(seconds=1))
        self.assertEqual(
            self.complete(at=self.now + timedelta(seconds=2))["state"], "BLOCKED",
        )
        self.assertNotEqual(
            self.queue.status(self.d["dossier_id"])["state"], "HELD",
        )

    def test_capture_revision_after_hold_invalidates_held_snapshot(self):
        self.submit()
        self.assertEqual(self.complete()["state"], "HELD")
        src = self.d["sources"][0]
        changed_text = "Revised source after held analytical work was recorded"
        self.record(src, quote=changed_text, raw=changed_text.encode(),
                    observed=self.now + timedelta(seconds=1))
        with self.assertRaises(EvidenceError):
            self.queue.verified_snapshot(self.d["dossier_id"])

    def test_modified_binding_receipt_is_blocked_on_completion(self):
        self.submit()
        self.queue.db.execute(
            "UPDATE source_bindings SET bindings_sha=? WHERE job_id=?",
            ("0" * 64, self.d["dossier_id"]),
        )
        self.assertEqual(self.complete()["state"], "BLOCKED")

    def test_deleted_binding_row_cannot_downgrade_queued_job(self):
        self.submit()
        self.queue.db.execute(
            "DELETE FROM source_bindings WHERE job_id=?", (self.d["dossier_id"],),
        )
        self.assertEqual(self.complete()["state"], "BLOCKED")

    def test_deleted_binding_row_blocks_held_digest_access(self):
        self.submit()
        self.assertEqual(self.complete()["state"], "HELD")
        self.queue.db.execute(
            "DELETE FROM source_bindings WHERE job_id=?", (self.d["dossier_id"],),
        )
        with self.assertRaises(EvidenceError):
            self.queue.verified_snapshot(self.d["dossier_id"])

    def test_forged_binding_row_cannot_upgrade_legacy_internal_job(self):
        self.queue.submit(self.d, now=self.now)
        manifest = json.dumps(self.bindings, sort_keys=True, separators=(",", ":"))
        self.queue.db.execute(
            "INSERT INTO source_bindings VALUES(?,?,?,?)",
            (self.d["dossier_id"], manifest,
             hashlib.sha256(manifest.encode()).hexdigest(), "0"*64),
        )
        self.assertEqual(self.complete()["state"], "BLOCKED")

    def test_deleted_binding_row_cannot_silently_replay_as_unbound(self):
        self.submit()
        self.queue.db.execute(
            "DELETE FROM source_bindings WHERE job_id=?", (self.d["dossier_id"],),
        )
        with self.assertRaises(EvidenceError):
            self.queue.submit(self.d, now=self.now)

    def test_tampered_source_ledger_is_blocked_on_completion(self):
        self.submit()
        self.ledger.connection.execute("DROP TRIGGER events_no_update")
        self.ledger.connection.execute(
            "UPDATE events SET event_hash=? WHERE seq=1", ("0" * 64,)
        )
        self.ledger.connection.commit()
        self.assertEqual(self.complete()["state"], "BLOCKED")

    def test_missing_private_source_ledger_is_blocked(self):
        self.submit()
        self.ledger.close()
        (self.root / "state/competitive_engine/provenance.sqlite3").unlink()
        self.assertEqual(self.complete()["state"], "BLOCKED")

    def test_unbound_legacy_synthetic_queue_still_holds_not_releases(self):
        out = self.queue.submit(self.d, now=self.now)
        self.assertEqual(out["state"], "QUEUED_INTERNAL_ONLY")
        self.assertIsNone(self.queue.db.execute(
            "SELECT * FROM source_bindings WHERE job_id=?", (self.d["dossier_id"],)
        ).fetchone())
        self.assertEqual(self.complete()["state"], "HELD")
        self.assertFalse(self.queue.verified_snapshot(self.d["dossier_id"])["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
