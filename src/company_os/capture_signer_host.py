"""CE-1C3d guarded host entrypoint for a SEPARATELY provisioned local signer.

Unlike a Python import or same-user fork, this host refuses a root identity,
same-UID clients, insecure key files and missing protected Unix group paths.
It still signs ONLY unverified staged bytes. An actual production system would
need stronger isolated custody, a supervised service, audit anchors, and
independent proof of original issuer capture. No key-generation or activation.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any

from .capture_signer_ipc import serve_one
from .capture_trust import verify_governance_policy
from .policy import is_paused
from .source_provenance import EvidenceError

MAX_POLICY_BYTES = 16384


def _load_private_signer(key_path: Path | str, repo_root: Path | str) -> Any:
    """Open a signer-owned 0400 raw Ed25519 seed outside the repository.

    Never search env vars or allow an application to supply key bytes in IPC.
    This disk-key path is a deployment reference, NOT an HSM or KMS.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise EvidenceError("Ed25519 dependency unavailable") from exc
    source = Path(key_path)
    root = Path(repo_root).resolve()
    if source.is_symlink() or not source.is_file():
        raise EvidenceError("signer key path missing or symlinked")
    source = source.resolve()
    if source.is_relative_to(root):
        raise EvidenceError("private signer key cannot reside in project repository")
    parent = source.parent
    info = parent.stat()
    if (info.st_uid != os.geteuid() or (info.st_mode & 0o777) != 0o700
            or parent.is_symlink()):
        raise EvidenceError("signer secret parent must be signer-owned 0700")
    before = source.stat()
    if (before.st_uid != os.geteuid()
            or (before.st_mode & 0o777) != 0o400
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1 or before.st_size != 32):
        raise EvidenceError("signer secret must be signer-owned regular 0400 raw seed")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(source, flags)
    try:
        after = os.fstat(fd)
        if ((after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
                or (after.st_mode & 0o777) != 0o400
                or after.st_uid != os.geteuid() or after.st_size != 32):
            raise EvidenceError("signer secret file changed while opening")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(33)
        if len(raw) != 32:
            raise EvidenceError("signer secret seed length invalid")
        return Ed25519PrivateKey.from_private_bytes(raw)
    finally:
        os.close(fd)


def _load_policy(path: Path | str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise EvidenceError("signed signer policy unavailable")
    if not 100 <= target.stat().st_size <= MAX_POLICY_BYTES:
        raise EvidenceError("signed signer policy size invalid")
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise EvidenceError("duplicate key in signer policy")
            result[k] = v
        return result
    try:
        obj = json.loads(
            target.read_text(encoding="utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                EvidenceError("nonfinite signer policy")),
        )
    except (OSError, ValueError, UnicodeError) as exc:
        raise EvidenceError("signed signer policy invalid") from exc
    if not isinstance(obj, dict):
        raise EvidenceError("signed signer policy must be an object")
    verify_governance_policy(obj)
    return obj


def run_host(
    *,
    repo_root: Path | str,
    key_file: Path | str,
    policy_file: Path | str,
    key_id: str,
    client_uid: int,
    shared_gid: int,
) -> dict[str, Any]:
    """One-shot read-only signing reference; no startup under the pause."""
    root = Path(repo_root).resolve()
    if is_paused(root):
        raise EvidenceError("company emergency pause blocks isolated signer")
    if os.name != "posix" or os.geteuid() == 0:
        raise EvidenceError("isolated signer host requires unprivileged Linux UID")
    if type(client_uid) is not int or client_uid in (0, os.geteuid()):
        raise EvidenceError("capture client must be a distinct nonroot UID")
    if type(shared_gid) is not int or shared_gid <= 0:
        raise EvidenceError("isolated signer requires a nonroot shared IPC group")
    policy = _load_policy(policy_file)
    signer = _load_private_signer(key_file, root)
    return serve_one(
        repo_root=root, policy_envelope=policy, signer=signer, key_id=key_id,
        allowed_client_uid=client_uid, shared_group_gid=shared_gid,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline one-request guarded signer host")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--policy-file", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--client-uid", required=True, type=int)
    parser.add_argument("--ipc-gid", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        run_host(
            repo_root=args.repo_root, key_file=args.key_file,
            policy_file=args.policy_file, key_id=args.key_id,
            client_uid=args.client_uid, shared_gid=args.ipc_gid,
        )
    except (EvidenceError, OSError, TypeError, ValueError):
        # Do not print secret paths, policy payload, source bytes, or traceback.
        print("signer refused or could not complete protected one-shot request")
        return 2
    print("staging-only unverified local attestation completed; no issuer certification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
