"""CE-1C3c prototype: one-request local Unix signer process.

This is a reference INTERPROCESS protocol, not a production signer service.
No TCP listener, online fetching, key generation, private-key export, source
authentication, or business release path. Root-signed policy and file hash
are checked again inside the signing process. All output is staging-only.
Production requires separate OS users, ACL, key vault and audit anchoring.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import os
import secrets
import socket
import struct
from pathlib import Path
from typing import Any, Mapping

from .approved_pdf_capture import StagedSource
from .capture_staging_signer import attest_local_staging
from .capture_trust import (
    StagingTrustLedger, verify_governance_policy, verify_staging_receipt,
)
from .policy import is_paused
from .source_provenance import EvidenceError

MAX_MESSAGE = 8192
TIMEOUT_SECONDS = 3
_STAGE_FIELDS = frozenset(f.name for f in dataclasses.fields(StagedSource))
_PROTOCOL_FIELDS = frozenset({"schema_version", "operation", "staged"})


def socket_path(
    repo_root: Path | str, *, shared_group_gid: int | None = None,
) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("signer root missing")
    if shared_group_gid is not None and (
        type(shared_group_gid) is not int or shared_group_gid < 0
    ):
        raise EvidenceError("invalid preprovisioned signer IPC group")
    path = root
    for name in ("state", "competitive_engine", "signer_ipc"):
        path = path / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise EvidenceError("signer IPC path unsafe")
        if shared_group_gid is None:
            path.mkdir(mode=0o700, exist_ok=True)
            if os.name == "posix":
                path.chmod(0o700)
        else:
            # The privileged installer, never this worker, creates 0710
            # group-traversable directories with no group write/world access.
            if not path.is_dir():
                raise EvidenceError("shared signer IPC path not provisioned")
            info = path.stat()
            perms = info.st_mode & 0o777
            if (info.st_gid != shared_group_gid or perms != 0o710
                    or (name == "signer_ipc" and info.st_uid != os.geteuid())):
                raise EvidenceError("shared signer IPC ownership or mode unsafe")
            if name == "signer_ipc" and not info.st_mode & 0o2000:
                raise EvidenceError("signer IPC directory must inherit configured group")
        if not path.resolve().is_relative_to(root):
            raise EvidenceError("signer IPC path escapes root")
    return path / "staging-signer.sock"


def _read_exact(conn: socket.socket, amount: int) -> bytes:
    chunks: list[bytes] = []
    while amount:
        piece = conn.recv(amount)
        if not piece:
            raise EvidenceError("signer message was truncated")
        chunks.append(piece)
        amount -= len(piece)
    return b"".join(chunks)


def _read_message(conn: socket.socket) -> dict[str, Any]:
    header = _read_exact(conn, 4)
    length = struct.unpack("!I", header)[0]
    if not 10 <= length <= MAX_MESSAGE:
        raise EvidenceError("signer input exceeds fixed protocol budget")
    raw = _read_exact(conn, length)
    def unique(pairs):
        record = {}
        for k, value in pairs:
            if k in record:
                raise EvidenceError("duplicate signer request key")
            record[k] = value
        return record
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             EvidenceError("nonfinite signer request")))
    except EvidenceError:
        # Preserve fail-closed schema/duplicate-key diagnostics instead of
        # accidentally concealing them as generic parse errors.
        raise
    except (UnicodeError, ValueError) as exc:
        raise EvidenceError("invalid signer request JSON") from exc
    if not isinstance(obj, dict) or set(obj) != _PROTOCOL_FIELDS:
        raise EvidenceError("signer request fields invalid")
    if obj["schema_version"] != "1.0" or obj["operation"] != "attest_staged":
        raise EvidenceError("unsupported signer operation")
    if not isinstance(obj["staged"], dict) or set(obj["staged"]) != _STAGE_FIELDS:
        raise EvidenceError("staged-source record fields invalid")
    return obj


def _send_message(conn: socket.socket, body: Mapping[str, Any]) -> None:
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
    if not 1 <= len(blob) <= MAX_MESSAGE:
        raise EvidenceError("signer response exceeds limit")
    conn.sendall(struct.pack("!I", len(blob)) + blob)


def _peer_uid(conn: socket.socket) -> int:
    if os.name != "posix" or not hasattr(socket, "SO_PEERCRED"):
        raise EvidenceError("OS peer credentials unavailable; signer disabled")
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                          struct.calcsize("3i"))
    _, uid, _ = struct.unpack("3i", raw)
    return uid


def serve_one(
    *,
    repo_root: Path | str,
    policy_envelope: Mapping[str, Any],
    signer: Any,
    key_id: str,
    allowed_client_uid: int,
    test_only_same_uid: bool = False,
    shared_group_gid: int | None = None,
) -> dict[str, Any]:
    """Process exactly one local IPC connection; no socket/TCP daemon.

    The same-UID test switch exists solely for offline CI. A secure production
    deployment MUST run the signer as a different restricted OS identity and
    deliberately authorize a less-privileged reader/client UID.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    root = Path(repo_root).resolve()
    if os.name != "posix" or not hasattr(socket, "SO_PEERCRED"):
        raise EvidenceError("Linux peer-credential support mandatory")
    if is_paused(root):
        raise EvidenceError("company emergency pause blocks signer")
    if type(allowed_client_uid) is not int or allowed_client_uid < 0:
        raise EvidenceError("invalid approved signer caller UID")
    if allowed_client_uid == os.geteuid() and not test_only_same_uid:
        raise EvidenceError("signer and capture client must have distinct OS identities")
    if not test_only_same_uid and shared_group_gid is None:
        raise EvidenceError("cross-UID signer requires preprovisioned private shared IPC group")
    if not isinstance(signer, Ed25519PrivateKey):
        raise EvidenceError("signer process private key unavailable")
    policy = verify_governance_policy(policy_envelope)
    trusted = [r for r in policy["trusted_keys"] if r["key_id"] == key_id]
    if (len(trusted) != 1 or key_id in policy["revoked_keys"]):
        raise EvidenceError("signing identity absent or revoked")
    if signer.public_key().public_bytes_raw() != base64.b64decode(
        trusted[0]["public_key_b64"], validate=True
    ):
        raise EvidenceError("injected signer key mismatches root-signed trust registry")

    with StagingTrustLedger(root, shared_parent_gid=shared_group_gid) as ledger:
        ledger.accept_policy(policy_envelope)
        addr = socket_path(root, shared_group_gid=shared_group_gid)
        if addr.is_symlink() or addr.exists():
            raise EvidenceError("existing signer socket refused; no replacement")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.bind(str(addr))
            try:
                if shared_group_gid is None:
                    addr.chmod(0o600)
                else:
                    # Only valid with a preprovisioned setgid directory.
                    # Always unlink on failure, including wrong socket group.
                    if addr.stat().st_gid != shared_group_gid:
                        raise EvidenceError("signer socket inherited wrong approved group")
                    addr.chmod(0o660)
                sock.listen(1)
                conn, _ = sock.accept()
                with conn:
                    conn.settimeout(TIMEOUT_SECONDS)
                    if _peer_uid(conn) != allowed_client_uid:
                        raise EvidenceError("unapproved local signer peer identity")
                    req = _read_message(conn)
                    if is_paused(root):
                        raise EvidenceError("company emergency pause blocks signer")
                    # Re-evaluate root governance at the actual signing boundary,
                    # not just at service startup.
                    active = verify_governance_policy(policy_envelope)
                    if key_id in active["revoked_keys"]:
                        raise EvidenceError("capture signer key revoked")
                    staged = StagedSource(**req["staged"])
                    rows = ledger._read()
                    next_seq = 1 + max(
                        (r[4] for r in rows if r[1] == "receipt" and r[3] == key_id),
                        default=0,
                    )
                    receipt = attest_local_staging(
                        repo_root=root, staged=staged, key_id=key_id,
                        receipt_id="receipt-" + secrets.token_hex(16),
                        sequence=next_seq, signer=signer,
                    )
                    verify_staging_receipt(receipt, active)
                    if is_paused(root):
                        raise EvidenceError("company pause activated during signing")
                    result = ledger.accept_receipt(receipt, policy_envelope)
                    # Do not return if the recorder cannot persist the receipt
                    # evidence. Audited receipts remain only staging assertions.
                    _send_message(conn, {
                        "status": "STAGING_ONLY_UNVERIFIED_ORIGIN",
                        "publication_authorized": False,
                        "original_issuer_authenticated": False,
                        "receipt": receipt,
                        "audit_head": ledger.audit()["head_sha256"],
                        "ledger_state": result["state"],
                    })
                    return {"state": "ONE_REQUEST_HANDLED", "publication_authorized": False}
            finally:
                try:
                    addr.unlink(missing_ok=True)
                except OSError:
                    pass


def request_staging_signature(
    repo_root: Path | str,
    staged: StagedSource,
    policy_envelope: Mapping[str, Any],
    *,
    expected_signer_uid: int,
    test_only_same_uid: bool = False,
) -> dict[str, Any]:
    """Unprivileged IPC client; checks peer UID, root policy and signed bytes.

    SAME UID is rejected in production mode. Passing test_only_same_uid=True
    verifies only the local protocol for tests, not real deployment isolation.
    """
    if not isinstance(staged, StagedSource):
        raise EvidenceError("unrecognized staging request data")
    if type(expected_signer_uid) is not int or expected_signer_uid < 0:
        raise EvidenceError("expected signer OS UID missing")
    if expected_signer_uid == os.geteuid() and not test_only_same_uid:
        raise EvidenceError("expected signer UID must be separately restricted")
    if is_paused(repo_root):
        raise EvidenceError("company emergency pause blocks signer client")
    verified_policy = verify_governance_policy(policy_envelope)
    addr = (Path(repo_root).resolve() / "state" / "competitive_engine"
            / "signer_ipc" / "staging-signer.sock")
    if addr.is_symlink():
        raise EvidenceError("signer IPC socket symlink refused")
    body = {
        "schema_version": "1.0", "operation": "attest_staged",
        "staged": dataclasses.asdict(staged),
    }
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(TIMEOUT_SECONDS)
        conn.connect(str(addr))
        if _peer_uid(conn) != expected_signer_uid:
            raise EvidenceError("unexpected signer process identity")
        _send_message(conn, body)
        response = _read_message_response(conn)
    if (response.get("status") != "STAGING_ONLY_UNVERIFIED_ORIGIN"
            or response.get("publication_authorized") is not False
            or response.get("original_issuer_authenticated") is not False):
        raise EvidenceError("signer did not return a safe unverified result")
    receipt = verify_staging_receipt(response.get("receipt"), verified_policy)
    expected = {
        "package_id": staged.package_id,
        "document_id": staged.document_id,
        "source_url": staged.source_url,
        "sha256": staged.sha256,
        "bytes_received": staged.size_bytes,
        "media_type": staged.media_type,
        "permit_id": staged.approved_source_permit_id,
        "pinned_ip": staged.pinned_ip,
        "tls_peer_cert_sha256": staged.tls_peer_cert_sha256,
    }
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise EvidenceError("signed staging response does not match requested original file")
    if response.get("ledger_state") != "LOCAL_STAGING_RECEIPT_RECORDED_UNVERIFIED_ORIGIN":
        raise EvidenceError("signer did not confirm staging-only local audit")
    if not isinstance(response.get("audit_head"), str) or len(response["audit_head"]) != 64:
        raise EvidenceError("signer audit hash unavailable")
    return response


def _read_message_response(conn: socket.socket) -> dict[str, Any]:
    header = _read_exact(conn, 4)
    size = struct.unpack("!I", header)[0]
    if not 10 <= size <= MAX_MESSAGE:
        raise EvidenceError("signer response size invalid")
    try:
        body = json.loads(_read_exact(conn, size).decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise EvidenceError("signer response invalid") from exc
    if not isinstance(body, dict):
        raise EvidenceError("signer response is not an object")
    return body
