#!/usr/bin/env python3
"""R52 Fixer Advisor.

The advisor never edits the PDF and never passes a card.  It converts an
Enforcer Critic failure plus an explicitly bounded repair proposal into the only
repair plan the Builder is allowed to execute.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from pathlib import Path
import engine

REVISION = "segment-role-whole-label-2026-09-13-r52"

class AdvisorError(engine.GateError):
    pass

def _rect(value):
    if not isinstance(value, list) or len(value) != 4:
        raise AdvisorError("each approved mask must be [x0,y0,x1,y1]")
    vals=[]
    for x in value:
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
            raise AdvisorError("mask coordinates must be finite numbers")
        vals.append(float(x))
    if vals[2] <= vals[0] or vals[3] <= vals[1]:
        raise AdvisorError("repair mask is empty or inverted")
    return vals

def advise(request_path: Path, output: Path) -> dict:
    engine.private_guard()
    policy = engine.verify_skills().get("r52", {})
    if policy.get("revision") != REVISION:
        raise AdvisorError("active R52 policy is unavailable")
    if output.exists():
        raise AdvisorError("fresh fixer-advice output required")
    request = engine.json_read(request_path)
    root = request_path.parent
    if request.get("schema_version") != 1 or request.get("kind") != "territory_fixer_request":
        raise AdvisorError("unsupported fixer-advisor request")
    candidate = engine.pinned(root, request.get("candidate"))
    enforcer_path = engine.pinned(root, request.get("enforcer_verdict"))
    enforcer = engine.json_read(enforcer_path)
    if enforcer.get("kind") != "territory_enforcer_critic" or enforcer.get("passed") is not False:
        raise AdvisorError("Fixer Advisor requires an actual failed Enforcer Critic verdict")
    if enforcer.get("artifact_sha256") != engine.sha(candidate):
        raise AdvisorError("failed Enforcer verdict is stale for this candidate")
    if enforcer.get("r52_revision") != REVISION:
        raise AdvisorError("failed Enforcer verdict was not produced under R52")
    if not enforcer.get("findings"):
        raise AdvisorError("no Enforcer findings are available to diagnose")
    scope = request.get("repair_scope")
    if not isinstance(scope, dict) or scope.get("type") != "label_only":
        raise AdvisorError("current Fixer Advisor authorizes bounded label-only repairs")
    masks = [_rect(x) for x in scope.get("approved_masks", [])]
    labels = scope.get("labels")
    if not masks or not isinstance(labels, list) or not 1 <= len(labels) <= 12:
        raise AdvisorError("bounded masks and 1-12 label repairs are required")
    seen=set()
    for i,label in enumerate(labels):
        if not isinstance(label,dict):
            raise AdvisorError(f"labels[{i}] must be an object")
        for key in ("label_id","street","navigation_role","segment_id","source_evidence","road_id","text","old_box","font_resource","font_size","road_polyline","placements"):
            if not label.get(key) and key not in ("font_size",):
                raise AdvisorError(f"labels[{i}] missing {key}")
        lid=str(label.get("label_id",""))
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", lid) or lid in seen:
            raise AdvisorError("label_id must be unique and stable")
        seen.add(lid)
        if not isinstance(label.get("placements"),list) or not label["placements"]:
            raise AdvisorError("Fixer Advisor requires explicit bounded placement alternatives")
        if len(label["placements"]) > 8:
            raise AdvisorError("too many repair alternatives for one label")
        for placement in label["placements"]:
            if placement.get("kind") not in ("direct","curved"):
                raise AdvisorError("current vector repair engine supports direct/curved label repairs only")
    advice = {
        "schema_version": 1,
        "kind": "territory_fixer_advice",
        "advisor_role": "fixer_advisor",
        "r52_revision": REVISION,
        "source": request["candidate"],
        "source_sha256": engine.sha(candidate),
        "enforcer_verdict": request["enforcer_verdict"],
        "enforcer_verdict_sha256": engine.sha(enforcer_path),
        "diagnosed_findings": list(enforcer.get("findings", [])),
        "mode": "approved_vector_label_revision",
        "approved_masks": masks,
        "labels": labels,
        "repair_authorized": True,
        "release_authorized": False,
        "builder_may_execute_only_this_scope": True,
        "enforcer_recheck_required": True,
    }
    engine.json_write(output, advice)
    return advice

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("request",type=Path);ap.add_argument("output",type=Path)
    args=ap.parse_args()
    try:
        print(json.dumps(advise(args.request,args.output),indent=2))
        return 0
    except (AdvisorError,engine.GateError,KeyError,ValueError,OSError) as exc:
        print(json.dumps({"repair_authorized":False,"release_authorized":False,"error":str(exc)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
