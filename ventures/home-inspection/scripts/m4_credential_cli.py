"""Operator-only fail-closed M4 credential preflight; no case release command.

Requires separately enrolled human and officer public keys, independently
verified real qualification evidence, and a trusted EXTERNAL monotonic revocation
watermark. It checks local signed data; it cannot independently prove licensure.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from inspection_engine.core import DataError
from inspection_engine.m4_credential_gate import professional_review_preflight


def main(argv=None):
    p=argparse.ArgumentParser(
        description="M4 Michigan qualification preflight, never customer release")
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--reviewer-trust",type=Path,required=True)
    p.add_argument("--officer-registry",type=Path,required=True)
    p.add_argument("--qualification-attestation",type=Path,required=True)
    p.add_argument("--revocation-attestation",type=Path,required=True)
    p.add_argument("--proof-root",type=Path,required=True)
    p.add_argument("--trusted-revocation-sequence",type=int,required=True,
                   help="Monotonic minimum from an independent authoritative registry, not a user guess")
    a=p.parse_args(argv)
    try:
        result=professional_review_preflight(
            a.workspace,a.reviewer_trust,a.officer_registry,
            a.qualification_attestation,a.revocation_attestation,a.proof_root,
            minimum_revocation_sequence=a.trusted_revocation_sequence)
    except (DataError,OSError,TypeError,ValueError,KeyError) as exc:
        print(json.dumps({"status":"CREDENTIAL_PRECHECK_BLOCKED",
                          "reason":str(exc),
                          "customer_release_allowed":False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
