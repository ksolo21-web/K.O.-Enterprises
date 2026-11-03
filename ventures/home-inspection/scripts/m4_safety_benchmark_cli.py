"""Read-only M4 V8 frozen safety benchmark. Private, offline, never release.

Required SHA256 pins must be recorded by an independently governed process
before evaluation; rehashing these local files to supply pins is NOT a real
independent freeze. Do not commit private cases, photo names, source hashes,
human identities, or evaluation bundles to public GitHub.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspection_engine.m4_frozen_safety_audit import score_frozen_safety_audit
from inspection_engine.serious_defect_benchmark import BenchmarkBlock

MAX_BYTES=10_000_000


def _unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:
            raise BenchmarkBlock("Duplicate private audit JSON key: "+k)
        out[k]=v
    return out


def _reject_number(value):
    raise BenchmarkBlock("Nonstandard private audit number: "+value)


def _private_json(path: Path):
    if path.is_symlink():
        raise BenchmarkBlock("Private audit input cannot be a symlink")
    resolved=path.resolve(strict=True)
    if not resolved.is_file() or not 1<=resolved.stat().st_size<=MAX_BYTES:
        raise BenchmarkBlock("Private audit JSON must be a bounded regular file")
    if any((p/".git").exists() for p in (resolved.parent,*resolved.parents)):
        raise BenchmarkBlock("Private audit input must be outside Git")
    try:
        return json.loads(resolved.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique,
                          parse_constant=_reject_number)
    except BenchmarkBlock:
        raise
    except (OSError,ValueError,UnicodeError) as exc:
        raise BenchmarkBlock("Invalid private audit JSON document") from exc


def main(argv=None):
    parser=argparse.ArgumentParser(description="Private frozen serious-defect benchmark; no customer release")
    for name in ("cases","predictions","human-matches","model-snapshot",
                 "adjudication-snapshot","training-index"):
        parser.add_argument("--"+name,required=True,type=Path)
    for name in ("case","model-snapshot","adjudication","training-index"):
        parser.add_argument("--externally-pinned-"+name+"-sha256",required=True)
    a=parser.parse_args(argv)
    try:
        result=score_frozen_safety_audit(
            _private_json(a.cases),_private_json(a.predictions),
            _private_json(a.human_matches),_private_json(a.model_snapshot),
            _private_json(a.adjudication_snapshot),_private_json(a.training_index),
            independent_case_pin_sha256=a.externally_pinned_case_sha256,
            independent_model_snapshot_pin_sha256=a.externally_pinned_model_snapshot_sha256,
            independent_adjudication_pin_sha256=a.externally_pinned_adjudication_sha256,
            independent_training_index_pin_sha256=a.externally_pinned_training_index_sha256
        )
    except (BenchmarkBlock,ValueError,TypeError,OSError,KeyError) as exc:
        print(json.dumps({"status":"SAFETY_BENCHMARK_BLOCKED",
                          "reason":str(exc),"customer_release_allowed":False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
