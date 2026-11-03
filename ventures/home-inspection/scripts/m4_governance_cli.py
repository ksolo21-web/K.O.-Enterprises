"""M4 V7 read-only governance history verification; no trust-key generation.

Root genesis, latest head hash, witness public key and event watermarks MUST
originate from a separately governed source of trust, never copied from the
same local history bundle to make the check pass. All inputs stay private.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspection_engine.core import DataError
from inspection_engine.m4_governance_history import (
    verify_governance_history, governed_issuer_evidence_preflight
)


def main(argv=None):
    p=argparse.ArgumentParser(description="V7 offline governance verification; NO customer release")
    sub=p.add_subparsers(dest="command",required=True)
    for operation in ("history", "case"):
        cmd=sub.add_parser(operation)
        cmd.add_argument("--governance-history",type=Path,required=True)
        cmd.add_argument("--independent-witness",type=Path,required=True)
        cmd.add_argument("--pinned-genesis-sha256",required=True)
        cmd.add_argument("--pinned-head-sha256",required=True)
        cmd.add_argument("--pinned-witness-public-key-hex",required=True)
        cmd.add_argument("--minimum-event-sequence",type=int,required=True)
        if operation=="case":
            for key in (
                "workspace", "reviewer-trust", "officer-registry",
                "qualification-attestation", "revocation-attestation",
                "proof-root", "issuer-verifier-registry", "issuer-receipts",
                "issuer-capture-root"
            ):
                cmd.add_argument("--"+key,type=Path,required=True)
            cmd.add_argument("--minimum-revocation-sequence",type=int,required=True)
    args=p.parse_args(argv)
    pins=dict(
        independently_pinned_genesis_sha256=args.pinned_genesis_sha256,
        independently_pinned_head_sha256=args.pinned_head_sha256,
        independently_pinned_witness_public_key_hex=args.pinned_witness_public_key_hex,
        minimum_event_sequence=args.minimum_event_sequence
    )
    try:
        if args.command=="history":
            result=verify_governance_history(
                args.governance_history,args.independent_witness,**pins)
        else:
            result=governed_issuer_evidence_preflight(
                args.workspace,args.reviewer_trust,args.officer_registry,
                args.qualification_attestation,args.revocation_attestation,
                args.proof_root,args.issuer_verifier_registry,
                args.issuer_receipts,args.issuer_capture_root,
                args.governance_history,args.independent_witness,
                minimum_revocation_sequence=args.minimum_revocation_sequence,**pins)
    except (DataError,TypeError,ValueError,KeyError,OSError) as exc:
        print(json.dumps({"status":"GOVERNANCE_PREFLIGHT_BLOCKED","reason":str(exc),
                          "customer_release_allowed":False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
