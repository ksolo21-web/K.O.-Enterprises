"""V9 private media-grounded serious-defect benchmark CLI; NEVER publish.

Accepts separately frozen V8 bundles plus exact original-photo/video-frame
ledger and spatial crosswalks. External digest pins must have been secured by
an independent custodian before model label disclosure; local rehashing of the
same files does not prove independence. No network/model calls or key creation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from inspection_engine.serious_defect_benchmark import BenchmarkBlock
from inspection_engine.m4_media_grounding import score_media_grounded_safety_audit
from scripts.m4_safety_benchmark_cli import _private_json


def main(argv=None):
    p=argparse.ArgumentParser(
        description="M4 V9 local media-grounded severe-defect evaluation; NO customer release")
    files=("cases","predictions","human-matches","model-snapshot","adjudication-snapshot",
           "training-index","media-manifest","prediction-regions","label-regions","grounding-snapshot")
    pin_names=("case","model-snapshot","adjudication","training-index",
               "media-manifest","prediction-regions","label-regions","grounding-snapshot")
    for field in files:
        p.add_argument("--"+field,required=True,type=Path)
    for name in pin_names:
        p.add_argument("--externally-pinned-"+name+"-sha256",required=True,
                       help="SHA256 obtained through independent prior custody")
    args=p.parse_args(argv)
    try:
        data={name:_private_json(getattr(args,name.replace("-","_"))) for name in files}
        result=score_media_grounded_safety_audit(
            data["cases"],data["predictions"],data["human-matches"],
            data["model-snapshot"],data["adjudication-snapshot"],data["training-index"],
            data["media-manifest"],data["prediction-regions"],
            data["label-regions"],data["grounding-snapshot"],
            independent_case_pin_sha256=args.externally_pinned_case_sha256,
            independent_model_snapshot_pin_sha256=args.externally_pinned_model_snapshot_sha256,
            independent_adjudication_pin_sha256=args.externally_pinned_adjudication_sha256,
            independent_training_index_pin_sha256=args.externally_pinned_training_index_sha256,
            independent_media_manifest_pin_sha256=args.externally_pinned_media_manifest_sha256,
            independent_prediction_regions_pin_sha256=args.externally_pinned_prediction_regions_sha256,
            independent_label_regions_pin_sha256=args.externally_pinned_label_regions_sha256,
            independent_grounding_snapshot_pin_sha256=args.externally_pinned_grounding_snapshot_sha256,
        )
    except (BenchmarkBlock,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"MEDIA_GROUNDING_AUDIT_BLOCKED","reason":str(exc),
                          "customer_release_allowed":False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
