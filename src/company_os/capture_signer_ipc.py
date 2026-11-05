"""CE-1C3c prototype: one-request local Unix signer process.

This is a reference INTERPROCESS protocol, not a production signer service.
No TCP listener, online fetching, key generation, private-key export, source
authentication, or business release path. Root-signed policy and file hash
are checked again inside the signing process. All output is staging-only.
Production requires separate OS users, ACL, key vault and audit anchoring.
"""

from __future__ import annotations

import dataclasses
import json
import os
import secrets
import socket
import stat
import struct
from datetime import datetime, timezone
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


def socket_path(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise EvidenceError("signer root missing")
    path = root
    for name in ("state", "competitive_engine", "signer_ipc"):
        path = path / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise EvidenceError("signer IPC path unsafe")
        path.mkdir(mode=0o700, exist_ok=True)
        if not path.resolve().is_relative_to(root):
            raise EvidenceError("signer IPC path escapes root")
        if os.name == "posix":
            path.chmod(0o700)
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
    if not isinstance(signer, Ed25519PrivateKey):
        raise EvidenceError("signer process private key unavailable")
    policy = verify_governance_policy(policy_envelope)
    trusted = [r for r in policy["trusted_keys"] if r["key_id"] == key_id]
    if (len(trusted) != 1 or key_id in policy["revoked_keys"]):
        raise EvidenceError("signing identity absent or revoked")
    if signer.public_key().public_bytes_raw() != __import__("base64").b64decode(
        trusted[0]["public_key_b64"], validate=True
    ):
        raise EvidenceError("injected signer key mismatches root-signed trust registry")

    with StagingTrustLedger(root) as ledger:
        ledger.accept_policy(policy_envelope)
        addr = socket_path(root)
        if addr.is_symlink() or addr.exists():
            raise EvidenceError("existing signer socket refused; no replacement")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.bind(str(addr))
            addr.chmod(0o600)
            sock.listen(1)
            try:
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
    repo_root: Path | str, staged: StagedSource,
) -> dict[str, Any]:
    """Unprivileged local IPC client. It has zero key or approval controls."""
    if not isinstance(staged, StagedSource):
        raise EvidenceError("unrecognized staging request data")
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
        _send_message(conn, body)
        response = _read_message_response(conn)
    if (response.get("status") != "STAGING_ONLY_UNVERIFIED_ORIGIN"
            or response.get("publication_authorized") is not False
            or response.get("original_issuer_authenticated") is not False):
        raise EvidenceError("signer did not return a safe unverified result")
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
