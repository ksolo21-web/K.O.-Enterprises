"""M4 issuer-source custody preflight; read-only, always private.

Call only after signed human review and M4 V5 credential preflight. The
independently_pinned_registry_sha256 MUST come from a separately controlled
trust enrollment process, not the current issuer verifier registry itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspection_engine.core import DataError
from inspection_engine.m4_issuer_receipts import issuer_evidence_preflight


def main(argv=None):
    p=argparse.ArgumentParser(description="M4 V6 issuer receipts preflight — NEVER customer release")
    for name in (
        "workspace", "reviewer-trust", "officer-registry", "qualification-attestation",
        "revocation-attestation", "proof-root", "issuer-verifier-registry",
        "issuer-receipts", "issuer-capture-root"
    ):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--independently-pinned-registry-sha256",required=True,
                   help="SHA256 from separately governed authority enrollment; not self-chosen")
    p.add_argument("--trusted-revocation-sequence",required=True,type=int,
                   help="Monotonic minimum supplied by a separately trusted registry")
    args=p.parse_args(argv)
    try:
        result=issuer_evidence_preflight(
            args.workspace,args.reviewer_trust,args.officer_registry,
            args.qualification_attestation,args.revocation_attestation,args.proof_root,
            args.issuer_verifier_registry,args.issuer_receipts,args.issuer_capture_root,
            independently_pinned_registry_sha256=args.independently_pinned_registry_sha256,
            minimum_revocation_sequence=args.trusted_revocation_sequence
        )
    except (DataError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"ISSUER_CUSTODY_PREFLIGHT_BLOCKED",
                          "reason":str(exc),"customer_release_allowed":False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
