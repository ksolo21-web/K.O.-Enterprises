"""Fail-closed CE-1C3d signer-host unit tests with synthetic ephemeral keys."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.capture_signer_host import _load_private_signer, run_host
from company_os.capture_trust import DOMAIN_POLICY, canonical
from company_os.source_provenance import EvidenceError


class RestrictedSignerHostTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name)
        self.root = self.temp/"private-workspace"
        self.root.mkdir()
        self.secrets = self.temp/"isolated-secrets"
        self.secrets.mkdir(mode=0o700)
        self.signer = Ed25519PrivateKey.generate()
        self.keyfile = self.secrets/"raw-seed.bin"
        self.keyfile.write_bytes(self.signer.private_bytes_raw())
        self.keyfile.chmod(0o400)
        self.root_key = Ed25519PrivateKey.generate()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.policy = {
            "schema_version": "1.0", "policy_id": "test-guarded-signer-001",
            "revision": 1, "issued_at": (now-timedelta(minutes=1)).isoformat(),
            "expires_at": (now+timedelta(days=1)).isoformat(),
            "approved_hosts": ["issuer.example"],
            "trusted_keys": [{
                "key_id": "guarded-signer-001",
                "public_key_b64": base64.b64encode(
                    self.signer.public_key().public_bytes_raw()
                ).decode(),
                "roles": ["pdf"],
                "valid_from": (now-timedelta(days=1)).isoformat(),
                "valid_until": (now+timedelta(days=20)).isoformat(),
            }],
            "revoked_keys": [], "revoked_receipts": [],
        }
        self.policyfile = self.root/"policy.json"
        self.save_policy()
        self.env = patch.dict(os.environ, {
            "COMPANY_OS_PAUSED": "0",
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
            "KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64": base64.b64encode(
                self.root_key.public_key().public_bytes_raw()
            ).decode(),
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.kwargs = {
            "repo_root": self.root, "key_file": self.keyfile,
            "policy_file": self.policyfile, "key_id": "guarded-signer-001",
            "client_uid": os.geteuid()+1,
            "shared_gid": max(1, os.getegid()),
        }

    def save_policy(self):
        envelope = {
            "policy": self.policy,
            "signature": base64.b64encode(
                self.root_key.sign(DOMAIN_POLICY+canonical(self.policy))
            ).decode(),
        }
        self.policyfile.write_text(json.dumps(envelope))

    def test_owned_strict_key_loads_only_an_external_32_byte_seed(self):
        loaded = _load_private_signer(self.keyfile, self.root)
        self.assertEqual(
            loaded.public_key().public_bytes_raw(),
            self.signer.public_key().public_bytes_raw(),
        )

    def test_guarded_host_validates_then_hands_off_to_explicit_ipc(self):
        with patch("company_os.capture_signer_host.serve_one", return_value={
            "state": "ONE_REQUEST_HANDLED", "publication_authorized": False,
        }) as server:
            result = run_host(**self.kwargs)
        self.assertFalse(result["publication_authorized"])
        args = server.call_args.kwargs
        self.assertEqual(args["allowed_client_uid"], self.kwargs["client_uid"])
        self.assertEqual(args["shared_group_gid"], self.kwargs["shared_gid"])
        self.assertEqual(
            args["signer"].public_key().public_bytes_raw(),
            self.signer.public_key().public_bytes_raw(),
        )
        self.assertNotIn("test_only_same_uid", args)

    def test_root_user_must_not_host_private_signer(self):
        with patch("company_os.capture_signer_host.os.geteuid", return_value=0):
            with self.assertRaises(EvidenceError):
                run_host(**self.kwargs)

    def test_same_user_capture_and_signer_not_accepted(self):
        self.kwargs["client_uid"] = os.geteuid()
        with self.assertRaises(EvidenceError):
            run_host(**self.kwargs)

    def test_paused_repository_blocks_before_secret_read(self):
        (self.root/"PAUSE_AUTONOMY").write_text("paused")
        with patch("company_os.capture_signer_host._load_private_signer") as load:
            with self.assertRaises(EvidenceError):
                run_host(**self.kwargs)
            load.assert_not_called()

    def test_environment_pause_blocks_before_secret_read(self):
        os.environ["COMPANY_OS_PAUSED"] = "1"
        with self.assertRaises(EvidenceError):
            run_host(**self.kwargs)

    def test_missing_signed_policy_fails_closed(self):
        self.policyfile.unlink()
        with self.assertRaises(EvidenceError):
            run_host(**self.kwargs)

    def test_invalid_policy_signature_fails_closed(self):
        self.policy["trusted_keys"][0]["roles"] = ["pdf", "listing"]
        # Deliberately do NOT re-sign altered policy on disk.
        data = json.loads(self.policyfile.read_text())
        data["policy"]["revision"] = 12
        self.policyfile.write_text(json.dumps(data))
        with self.assertRaises(EvidenceError):
            run_host(**self.kwargs)

    def test_key_inside_repository_is_refused_even_when_permissions_strict(self):
        inside = self.root/"key-secrets"
        inside.mkdir(mode=0o700)
        path = inside/"raw-seed.bin"
        path.write_bytes(self.signer.private_bytes_raw())
        path.chmod(0o400)
        with self.assertRaises(EvidenceError):
            _load_private_signer(path, self.root)

    def test_signing_key_mode_0644_is_refused(self):
        self.keyfile.chmod(0o644)
        with self.assertRaises(EvidenceError):
            _load_private_signer(self.keyfile, self.root)

    def test_signer_secret_directory_must_remain_0700(self):
        self.secrets.chmod(0o750)
        with self.assertRaises(EvidenceError):
            _load_private_signer(self.keyfile, self.root)

    def test_signing_key_symlink_is_refused(self):
        alias = self.secrets/"alias.bin"
        alias.symlink_to(self.keyfile)
        with self.assertRaises(EvidenceError):
            _load_private_signer(alias, self.root)

    def test_signing_key_hardlink_is_refused(self):
        alias = self.secrets/"hardlink.bin"
        os.link(self.keyfile, alias)
        with self.assertRaises(EvidenceError):
            _load_private_signer(self.keyfile, self.root)

    def test_wrong_raw_seed_size_is_refused(self):
        self.keyfile.chmod(0o600)
        self.keyfile.write_bytes(b"x"*31)
        self.keyfile.chmod(0o400)
        with self.assertRaises(EvidenceError):
            _load_private_signer(self.keyfile, self.root)

    def test_invalid_client_uid_and_shared_group_refused(self):
        for uid, gid in (
            (0, self.kwargs["shared_gid"]),
            (self.kwargs["client_uid"], 0),
            (self.kwargs["client_uid"], "bad"),
        ):
            with self.subTest(uid=uid, gid=gid), self.assertRaises(EvidenceError):
                run_host(**(self.kwargs | {"client_uid":uid, "shared_gid":gid}))

    def test_policy_duplicate_json_keys_refused(self):
        self.policyfile.write_text(
            '{"schema_version":"1.0","schema_version":"1.0"}'
        )
        with self.assertRaises(EvidenceError):
            run_host(**self.kwargs)


if __name__ == "__main__":
    unittest.main()
