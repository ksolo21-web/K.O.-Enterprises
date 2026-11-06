"""Root-run disposable CI cross-UID security exercise; never production.

Requires a disposable GitHub Linux runner, CI=true and explicit test opt-in.
Uses ephemeral NUMERIC UIDs/GID without creating OS accounts. No network,
real issuer files, real deployment keys, launch or other external action.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.approved_pdf_capture import StagedSource
from company_os.capture_trust import DOMAIN_POLICY, canonical

SIGNER_UID = 53011
CAPTURE_UID = 53012
UNKNOWN_UID = 53013
SHARED_GID = 53010


def write_secure(path: Path, data: bytes, uid: int, gid: int, mode: int) -> None:
    path.write_bytes(data)
    os.chown(path, uid, gid)
    os.chmod(path, mode)


def directory(path: Path, uid: int, gid: int, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chown(path, uid, gid)
    os.chmod(path, mode)


def drop_identity(uid: int):
    def before():
        os.setgroups([SHARED_GID])
        os.setgid(SHARED_GID)
        os.setuid(uid)
    return before


def child_command(uid: int, argv: list[str], *, env: dict[str, str]):
    return subprocess.Popen(
        [sys.executable, *argv], text=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, preexec_fn=drop_identity(uid),
        cwd=os.environ["KO_CE_CROSS_UID_TEST_ROOT"],
    )


def invoke_client(root: Path, staged_path: Path, policy_path: Path, *, uid: int):
    return child_command(uid, [
        os.environ["KO_CE_CROSS_UID_CLIENT_SCRIPT"], "--client", str(root),
        str(staged_path), str(policy_path),
    ], env=child_env())


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["COMPANY_OS_PAUSED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.environ["KO_CE_CROSS_UID_CODE_ROOT"]
    return env


def run_client(root: Path, staged_path: Path, policy_path: Path) -> int:
    from company_os.capture_signer_ipc import request_staging_signature
    staged = StagedSource(**json.loads(staged_path.read_text("utf-8")))
    policy = json.loads(policy_path.read_text("utf-8"))
    try:
        response = request_staging_signature(
            root, staged, policy, expected_signer_uid=SIGNER_UID,
        )
        receipt = response["receipt"]["receipt"]
        if (receipt["capture_method"] != "local_staged_bytes_unverified"
                or receipt["original_issuer_authenticated"] is not False
                or response["publication_authorized"] is not False):
            return 3
        print("cross-UID authenticated staging-only reply verified")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("cross-UID client correctly blocked: " + type(exc).__name__)
        return 2


def run_key_probe(key_path: Path) -> int:
    try:
        with key_path.open("rb") as stream:
            stream.read(1)
        print("BAD: capture UID can read signing key")
        return 4
    except PermissionError:
        print("capture UID cannot read signer-owned private key")
        return 0


def wait_for_socket(addr: Path, proc: subprocess.Popen) -> None:
    for _ in range(300):
        if addr.is_socket():
            return
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1)
            raise AssertionError(
                "signer terminated before listening: " + out[:200] + " " + err[:200]
            )
        time.sleep(.01)
    proc.kill()
    proc.communicate()
    raise AssertionError("signer did not bind within bounded CI test")


def run_scenario(
    root: Path, key_path: Path, policy_path: Path, stage_path: Path, *,
    caller_uid: int = CAPTURE_UID, expect_success: bool = True,
) -> None:
    argv = [
        "-m", "company_os.capture_signer_host",
        "--repo-root", str(root),
        "--key-file", str(key_path),
        "--policy-file", str(policy_path),
        "--key-id", "ci-ephemeral-key-001",
        "--client-uid", str(CAPTURE_UID),
        "--ipc-gid", str(SHARED_GID),
    ]
    signer = child_command(SIGNER_UID, argv, env=child_env())
    addr = root/"state"/"competitive_engine"/"signer_ipc"/"staging-signer.sock"
    wait_for_socket(addr, signer)
    client = invoke_client(root, stage_path, policy_path, uid=caller_uid)
    client_out, client_err = client.communicate(timeout=8)
    signer_out, signer_err = signer.communicate(timeout=8)
    if expect_success:
        assert client.returncode == 0, (client.returncode, client_out, client_err[:350])
        assert signer.returncode == 0, (signer.returncode, signer_out, signer_err[:350])
        assert "staging-only" in signer_out, signer_out
        assert "staging-only" in client_out, client_out
    else:
        assert client.returncode != 0, "unapproved peer unexpectedly authenticated"
        assert signer.returncode != 0, "signer unexpectedly approved unapproved peer"
    assert not addr.exists(), "one-shot signer left stale socket"
    print("PASS: " + ("real distinct-UID signed staging" if expect_success else "unauthorized UID blocked"))


def main() -> int:
    if not (
        sys.platform.startswith("linux") and os.geteuid() == 0
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("KO_CE_CROSS_UID_TEST") == "1"
    ):
        raise SystemExit("refusing cross-UID exercise outside opted-in disposable CI")
    # Neither numeric UID is a real account or is introduced into /etc/passwd.
    for uid in (SIGNER_UID, CAPTURE_UID, UNKNOWN_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            continue
        raise AssertionError("ephemeral test UID collides with existing host account")

    with tempfile.TemporaryDirectory(prefix="ko-ci-uid-", dir="/tmp") as temp:
        # Only synthetic shared group can traverse otherwise-0700 tempfile.
        os.chown(temp, 0, SHARED_GID)
        os.chmod(temp, 0o710)
        os.environ["KO_CE_CROSS_UID_TEST_ROOT"] = temp
        # Never change the checkout's file/directory permissions. Numeric UIDs
        # cannot traverse /home/runner; copy only nonsecret Python source into
        # root-controlled, group-readable ephemeral test storage.
        runtime = Path(temp)/"verified-public-code"
        package = runtime/"company_os"
        shutil.copytree(Path.cwd()/"src"/"company_os", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for p in (runtime, *package.rglob("*"), package):
            if p.is_dir():
                os.chown(p, 0, SHARED_GID)
                os.chmod(p, 0o750)
            elif p.is_file():
                os.chown(p, 0, SHARED_GID)
                os.chmod(p, 0o640)
        copy_script = Path(temp)/"cross_uid_client.py"
        shutil.copyfile(Path(__file__), copy_script)
        os.chown(copy_script, 0, SHARED_GID)
        os.chmod(copy_script, 0o640)
        os.environ["KO_CE_CROSS_UID_CODE_ROOT"] = str(runtime)
        os.environ["KO_CE_CROSS_UID_CLIENT_SCRIPT"] = str(copy_script)

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_procurement_package import make_pdf
        root = Path(temp)/"synthetic-project"
        directory(root, 0, SHARED_GID, 0o710)
        state = root/"state"
        parent = state/"competitive_engine"
        directory(state, 0, SHARED_GID, 0o710)
        directory(parent, 0, SHARED_GID, 0o710)
        directory(parent/"signer_ipc", SIGNER_UID, SHARED_GID, 0o2710)
        directory(parent/"trust", SIGNER_UID, SHARED_GID, 0o700)
        directory(parent/"capture_staging", CAPTURE_UID, SHARED_GID, 0o750)
        pkg = parent/"capture_staging"/"ci-package"
        directory(pkg, CAPTURE_UID, SHARED_GID, 0o750)

        original = make_pdf(
            "Synthetic issued procurement evidence only; not an actual issuer claim."
        )
        pdf = pkg/"ci-pdf.pdf"
        write_secure(pdf, original, CAPTURE_UID, SHARED_GID, 0o640)
        observed = datetime.now(timezone.utc).replace(microsecond=0)
        staged = StagedSource(
            package_id="ci-package", document_id="ci-pdf", file_name="ci-pdf.pdf",
            source_url="https://issuer.example/ci-pdf.pdf",
            observed_at=observed.isoformat(),
            sha256=hashlib.sha256(original).hexdigest(),
            size_bytes=len(original), media_type="application/pdf",
            tls_peer_cert_sha256="a"*64, pinned_ip="93.184.216.34",
            tls_version="TLSv1.3", approved_source_permit_id="ci-permit-001",
            reviewed_pdf_pages=1,
        )
        stage_path = parent/"staged.json"
        write_secure(
            stage_path, json.dumps(staged.unsigned_metadata()).encode(),
            CAPTURE_UID, SHARED_GID, 0o640,
        )

        signing = Ed25519PrivateKey.generate()
        root_key = Ed25519PrivateKey.generate()
        pubkey = base64.b64encode(signing.public_key().public_bytes_raw()).decode()
        os.environ["KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64"] = base64.b64encode(
            root_key.public_key().public_bytes_raw()
        ).decode()
        os.environ["KO_SOURCE_APPROVED_HOSTS"] = "issuer.example"
        policy = {
            "schema_version": "1.0", "policy_id": "ci-root-policy-001",
            "revision": 1,
            "issued_at": (observed-timedelta(minutes=1)).isoformat(),
            "expires_at": (observed+timedelta(days=1)).isoformat(),
            "trusted_keys": [{
                "key_id": "ci-ephemeral-key-001", "public_key_b64": pubkey,
                "roles": ["pdf"],
                "valid_from": (observed-timedelta(days=1)).isoformat(),
                "valid_until": (observed+timedelta(days=30)).isoformat(),
            }],
            "revoked_keys": [], "revoked_receipts": [],
            "approved_hosts": ["issuer.example"],
        }
        signed_policy = {
            "policy": policy,
            "signature": base64.b64encode(
                root_key.sign(DOMAIN_POLICY+canonical(policy))
            ).decode(),
        }
        policy_path = parent/"policy.json"
        write_secure(policy_path, json.dumps(signed_policy).encode(), 0, SHARED_GID, 0o640)

        secret_root = Path(temp)/"signer-secrets"
        directory(secret_root, SIGNER_UID, SIGNER_UID, 0o700)
        key_path = secret_root/"ed25519-raw-seed.bin"
        write_secure(key_path, signing.private_bytes_raw(), SIGNER_UID, SIGNER_UID, 0o400)
        probe = child_command(
            CAPTURE_UID, [os.environ["KO_CE_CROSS_UID_CLIENT_SCRIPT"], "--key-probe", str(key_path)],
            env=child_env(),
        )
        out, err = probe.communicate(timeout=5)
        assert probe.returncode == 0, (out,err[:200])
        print("PASS: capture UID denied private signer key")

        run_scenario(root,key_path,policy_path,stage_path)
        run_scenario(root,key_path,policy_path,stage_path,
                     caller_uid=UNKNOWN_UID,expect_success=False)

        # Insecure key mode must block BEFORE a listening socket exists.
        key_path.chmod(0o644)
        insecure = child_command(SIGNER_UID, [
            "-m", "company_os.capture_signer_host",
            "--repo-root", str(root), "--key-file", str(key_path),
            "--policy-file", str(policy_path), "--key-id", "ci-ephemeral-key-001",
            "--client-uid", str(CAPTURE_UID), "--ipc-gid", str(SHARED_GID),
        ], env=child_env())
        _, err = insecure.communicate(timeout=6)
        assert insecure.returncode != 0, "world-readable signer key was accepted"
        assert not (parent/"signer_ipc"/"staging-signer.sock").exists()
        print("PASS: unsafe signer key permissions fail closed")

        key_path.chmod(0o400)
        write_secure(root/"PAUSE_AUTONOMY", b"intentionally paused\n", 0, SHARED_GID, 0o640)
        paused = child_command(SIGNER_UID, [
            "-m", "company_os.capture_signer_host",
            "--repo-root", str(root), "--key-file", str(key_path),
            "--policy-file", str(policy_path), "--key-id", "ci-ephemeral-key-001",
            "--client-uid", str(CAPTURE_UID), "--ipc-gid", str(SHARED_GID),
        ], env=child_env())
        paused.communicate(timeout=6)
        assert paused.returncode != 0, "paused signer started"
        assert not (parent/"signer_ipc"/"staging-signer.sock").exists()
        print("PASS: shared-tree emergency stop blocks real cross-UID signer")

    print("CE-1C3d real Linux distinct-UID offline checks passed, NOT issuer verified")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--client":
        raise SystemExit(run_client(Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4])))
    if len(sys.argv) > 1 and sys.argv[1] == "--key-probe":
        raise SystemExit(run_key_probe(Path(sys.argv[2])))
    raise SystemExit(main())
