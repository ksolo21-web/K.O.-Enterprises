"""CE-1C3c Linux process-boundary tests with synthetic sources and keys only."""

from __future__ import annotations

import base64
import hashlib
import json
import multiprocessing
import os
import socket
import struct
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.approved_pdf_capture import StagedSource
from company_os.capture_signer_ipc import (
    MAX_MESSAGE, _read_message, _send_message, request_staging_signature,
    serve_one, socket_path,
)
from company_os.capture_trust import DOMAIN_POLICY, StagingTrustLedger, canonical
from company_os.source_provenance import EvidenceError
import test_procurement_package as fixture_support


def _run_child(queue, root, policy, key, key_id, uid, test_mode):
    """Invoked in a genuine child process, not a fake synchronous mock."""
    try:
        result = serve_one(
            repo_root=root, policy_envelope=policy, signer=key,
            key_id=key_id, allowed_client_uid=uid,
            test_only_same_uid=test_mode,
        )
        queue.put(("ok", result["state"]))
    except Exception as exc:
        queue.put(("blocked", type(exc).__name__ + ": " + str(exc)))


def _fake_local_socket(queue, root, reply):
    """Simulates a hostile local socket impersonator in an offline fixture."""
    try:
        location = socket_path(root)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(str(location))
            sock.listen(1)
            conn, _ = sock.accept()
            with conn:
                conn.recv(8192)
                _send_message(conn, reply)
        location.unlink(missing_ok=True)
        queue.put(("ok", "fake answered"))
    except Exception as exc:
        queue.put(("blocked", type(exc).__name__))


class SignerIpcProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "posix" or not hasattr(socket, "SO_PEERCRED"):
            raise unittest.SkipTest("real Unix SO_PEERCRED tests require Linux")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.root_key = Ed25519PrivateKey.generate()
        self.capture_key = Ed25519PrivateKey.generate()
        self.env = patch.dict(os.environ, {
            "COMPANY_OS_PAUSED": "0",
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64": base64.b64encode(
                self.root_key.public_key().public_bytes_raw()
            ).decode("ascii"),
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.policy = {
            "schema_version": "1.0", "policy_id": "ko-ipc-root-001",
            "revision": 1,
            "issued_at": (self.now-timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now+timedelta(days=1)).isoformat(),
            "trusted_keys": [{
                "key_id": "capture-ipc-001",
                "public_key_b64": base64.b64encode(
                    self.capture_key.public_key().public_bytes_raw()
                ).decode("ascii"),
                "roles": ["pdf", "listing"],
                "valid_from": (self.now-timedelta(days=1)).isoformat(),
                "valid_until": (self.now+timedelta(days=30)).isoformat(),
            }],
            "revoked_keys": [], "revoked_receipts": [],
            "approved_hosts": ["issuer.example"],
        }
        pdf = fixture_support.make_pdf(
            "Synthetic official looking text is NOT proof of real issuer origin."
        )
        folder = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"
        folder.mkdir(parents=True)
        (folder/"test-pdf.pdf").write_bytes(pdf)
        self.staged = StagedSource(
            package_id="test-package", document_id="test-pdf",
            file_name="test-pdf.pdf",
            source_url="https://issuer.example/test-pdf.pdf",
            observed_at=self.now.isoformat(),
            sha256=hashlib.sha256(pdf).hexdigest(),
            size_bytes=len(pdf), media_type="application/pdf",
            tls_peer_cert_sha256="b"*64,
            pinned_ip="93.184.216.34", tls_version="TLSv1.3",
            approved_source_permit_id="test-permit-001",
            reviewed_pdf_pages=1,
        )
        self.workers = []
        self.addCleanup(self._terminate_workers)

    def _terminate_workers(self):
        for process in self.workers:
            if process.is_alive():
                process.terminate()
            process.join(timeout=3)

    def signed_policy(self):
        return {
            "policy": self.policy.copy(),
            "signature": base64.b64encode(
                self.root_key.sign(DOMAIN_POLICY + canonical(self.policy))
            ).decode("ascii"),
        }

    def spawn(self, policy=None, key=None, uid=None, test_mode=True):
        queue = self.ctx.Queue()
        process = self.ctx.Process(target=_run_child, args=(
            queue, self.root, policy or self.signed_policy(),
            key or self.capture_key, "capture-ipc-001",
            os.geteuid() if uid is None else uid, test_mode,
        ))
        process.start()
        self.workers.append(process)
        addr = self.root/"state"/"competitive_engine"/"signer_ipc"/"staging-signer.sock"
        for _ in range(250):
            if addr.is_socket() or not process.is_alive():
                break
            time.sleep(0.01)
        return process, queue, addr

    def collect(self, process, queue):
        process.join(timeout=5)
        self.assertFalse(process.is_alive(), "signer process did not terminate")
        self.assertFalse(queue.empty(), "signer process did not provide status")
        return queue.get(timeout=2)

    def test_real_child_process_signs_only_unverified_local_staging(self):
        policy = self.signed_policy()
        process, queue, addr = self.spawn(policy)
        self.assertTrue(addr.is_socket(), "separate worker failed to bind IPC socket")
        result = request_staging_signature(
            self.root, self.staged, policy,
            expected_signer_uid=os.geteuid(), test_only_same_uid=True,
        )
        status = self.collect(process, queue)
        self.assertEqual(status, ("ok", "ONE_REQUEST_HANDLED"))
        self.assertFalse(addr.exists())
        self.assertEqual(result["status"], "STAGING_ONLY_UNVERIFIED_ORIGIN")
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["original_issuer_authenticated"])
        self.assertEqual(result["receipt"]["receipt"]["sha256"], self.staged.sha256)
        self.assertEqual(
            result["receipt"]["receipt"]["capture_method"],
            "local_staged_bytes_unverified",
        )
        with StagingTrustLedger(self.root) as audit:
            self.assertEqual(audit.audit()["events"], 2)
            self.assertEqual(result["audit_head"], audit.audit()["head_sha256"])

    def test_same_uid_signer_denied_without_explicit_test_mode(self):
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=self.capture_key, key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid(),
            )

    def test_same_uid_client_denied_without_explicit_test_mode(self):
        with self.assertRaises(EvidenceError):
            request_staging_signature(
                self.root, self.staged, self.signed_policy(),
                expected_signer_uid=os.geteuid(),
            )

    def test_root_emergency_pause_blocks_worker_before_binding_socket(self):
        (self.root/"PAUSE_AUTONOMY").write_text("paused")
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=self.capture_key, key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid(), test_only_same_uid=True,
            )
        self.assertFalse((self.root/"state"/"competitive_engine"/"signer_ipc").exists())

    def test_environment_pause_blocks_worker(self):
        os.environ["COMPANY_OS_PAUSED"] = "yes"
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=self.capture_key, key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid(), test_only_same_uid=True,
            )

    def test_wrong_private_key_cannot_bind_signer_socket(self):
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=Ed25519PrivateKey.generate(), key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid(), test_only_same_uid=True,
            )

    def test_revoked_key_cannot_bind_signer_socket(self):
        self.policy["revoked_keys"] = ["capture-ipc-001"]
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=self.capture_key, key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid(), test_only_same_uid=True,
            )

    def test_wrong_client_uid_rejected_by_actual_kernel_peer_check(self):
        # Same-UID disposable fixture still checks the kernel's *wrong client*
        # result. Production cross-UID mode is separately exercised in CI.
        process, queue, addr = self.spawn(uid=os.geteuid()+1, test_mode=True)
        self.assertTrue(addr.is_socket())
        with self.assertRaises((EvidenceError, OSError, ConnectionError)):
            request_staging_signature(
                self.root, self.staged, self.signed_policy(),
                expected_signer_uid=os.geteuid(), test_only_same_uid=True,
            )
        status = self.collect(process, queue)
        self.assertIn("unapproved local signer peer identity", status[1])

    def test_production_signer_refuses_missing_preprovisioned_group(self):
        # A different allowed UID is not enough. Without a protected shared
        # group/path, the signer must refuse before creating a socket.
        with self.assertRaises(EvidenceError):
            serve_one(
                repo_root=self.root, policy_envelope=self.signed_policy(),
                signer=self.capture_key, key_id="capture-ipc-001",
                allowed_client_uid=os.geteuid()+1,
                test_only_same_uid=False, shared_group_gid=None,
            )
        self.assertFalse(
            (self.root/"state"/"competitive_engine"/"signer_ipc").exists()
        )

    def test_corrupted_original_pdf_fails_without_receipt(self):
        process, queue, addr = self.spawn()
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"/"test-pdf.pdf"
        data=path.read_bytes()
        path.write_bytes(data[:-1]+bytes([data[-1]^1]))
        with self.assertRaises((EvidenceError, OSError, ConnectionError)):
            request_staging_signature(
                self.root,self.staged,self.signed_policy(),
                expected_signer_uid=os.geteuid(),test_only_same_uid=True,
            )
        self.assertIn("mismatched",str(self.collect(process,queue)).lower())
        with StagingTrustLedger(self.root) as audit:
            self.assertEqual(audit.audit()["events"],1)

    def test_request_with_duplicate_json_keys_rejected(self):
        process, queue, addr = self.spawn()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            conn.connect(str(addr))
            raw=b'{"schema_version":"1.0","schema_version":"1.0"}'
            conn.sendall(struct.pack("!I",len(raw))+raw)
        status=self.collect(process,queue)
        self.assertIn("duplicate signer request",status[1])

    def test_length_over_protocol_limit_refused(self):
        process, queue, addr=self.spawn()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            conn.connect(str(addr))
            conn.sendall(struct.pack("!I",MAX_MESSAGE+1))
        status=self.collect(process,queue)
        self.assertIn("exceeds fixed protocol budget",status[1])

    def test_no_long_lived_daemon_after_one_request(self):
        policy=self.signed_policy()
        process,queue,addr=self.spawn(policy)
        request_staging_signature(
            self.root,self.staged,policy,expected_signer_uid=os.geteuid(),
            test_only_same_uid=True,
        )
        self.assertEqual(self.collect(process,queue)[0],"ok")
        with self.assertRaises(OSError):
            request_staging_signature(
                self.root,self.staged,policy,
                expected_signer_uid=os.geteuid(),test_only_same_uid=True,
            )

    def test_fake_local_socket_cannot_forge_unverified_receipt(self):
        fake_response = {
            "status":"STAGING_ONLY_UNVERIFIED_ORIGIN",
            "publication_authorized":False,
            "original_issuer_authenticated":False,
            "ledger_state":"LOCAL_STAGING_RECEIPT_RECORDED_UNVERIFIED_ORIGIN",
            "audit_head":"0"*64,
            "receipt":{"receipt":{"fake":"original"},"signature":"A"*88},
        }
        queue=self.ctx.Queue()
        process=self.ctx.Process(target=_fake_local_socket,args=(queue,self.root,fake_response))
        process.start()
        self.workers.append(process)
        addr=self.root/"state"/"competitive_engine"/"signer_ipc"/"staging-signer.sock"
        for _ in range(250):
            if addr.is_socket() or not process.is_alive():
                break
            time.sleep(0.01)
        with self.assertRaises(EvidenceError):
            request_staging_signature(
                self.root,self.staged,self.signed_policy(),
                expected_signer_uid=os.geteuid(),test_only_same_uid=True,
            )
        self.assertEqual(self.collect(process,queue)[0],"ok")

    def test_no_external_tcp_or_source_fetch_in_signer_protocol(self):
        import company_os.capture_signer_ipc as module
        self.assertNotIn("AF_INET",module.serve_one.__code__.co_names)
        self.assertNotIn("requests",module.serve_one.__code__.co_names)
        self.assertNotIn("_download_https",module.serve_one.__code__.co_names)
        self.assertFalse(hasattr(module,"publish"))
        self.assertFalse(hasattr(module,"launch_business"))


if __name__ == "__main__":
    unittest.main()
