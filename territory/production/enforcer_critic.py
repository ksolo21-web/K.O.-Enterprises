#!/usr/bin/env python3
"""R52 Enforcer Critic.

Read-only release authority for the automated pipeline.  The Enforcer never
edits a card and never proposes repairs.  It independently applies the R52
evidence gates to the exact saved PDF and, when configured, requires the
separate local visual critic to have passed the same exact candidate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import engine

REVISION = "segment-role-whole-label-2026-09-13-r52"

class EnforcerError(engine.GateError):
    pass

def _run_validator(script: Path, args: list[str], cwd: Path) -> dict:
    result=engine.run_checked([engine.sys.executable,str(script),*args],cwd=cwd,timeout=120)
    payload=None
    if result["stdout"].strip():
        try: payload=json.loads(result["stdout"])
        except json.JSONDecodeError: payload=None
    return {"returncode":result["returncode"],"payload":payload,"stdout":result["stdout"][-2000:],"stderr":result["stderr"][-2000:]}

def enforce(job_path: Path, output: Path) -> dict:
    engine.private_guard()
    integrity=engine.verify_skills()
    if output.exists():
        raise EnforcerError("fresh Enforcer Critic verdict required")
    job=engine.json_read(job_path);root=job_path.parent
    if job.get("schema_version")!=1 or job.get("kind")!="territory_enforcer_review":
        raise EnforcerError("unsupported Enforcer Critic job")
    pdf=engine.pinned(root,job.get("candidate"))
    review=engine.pinned(root,job.get("internal_review"))
    engine.inspect_pdf(pdf)
    review_data=engine.json_read(review)
    findings=[];checks={}
    artifact=engine.sha(pdf)
    if review_data.get("artifact_sha256")!=artifact:
        findings.append("internal review is not bound to the exact candidate PDF")
    try:
        engine.score_guard(review_data)
        checks["strict_score_floor"]=True
    except engine.GateError as exc:
        checks["strict_score_floor"]=False;findings.append(str(exc))
    r52_root=engine.ROOT/"r52";scripts=r52_root/"scripts"
    parity=_run_validator(scripts/"validate_internal_reviewer_parity.py",[str(review)],review.parent)
    checks["internal_reviewer_parity"]=parity["returncode"]==0
    if not checks["internal_reviewer_parity"]:
        errs=(parity.get("payload") or {}).get("errors") or [parity["stdout"] or parity["stderr"]]
        findings.extend("R52 parity: "+str(x) for x in errs if x)
    nav=_run_validator(scripts/"validate_label_navigation_contract.py",[str(review),"--pdf",str(pdf)],review.parent)
    checks["label_navigation"]=nav["returncode"]==0
    if not checks["label_navigation"]:
        errs=(nav.get("payload") or {}).get("errors") or [nav["stdout"] or nav["stderr"]]
        findings.extend("R52 navigation: "+str(x) for x in errs if x)
    independent_required=job.get("independent_visual_required",True)
    checks["independent_visual_required"]=independent_required
    independent=None
    if independent_required:
        try:
            ipath=engine.pinned(root,job.get("independent_review"))
            independent=engine.json_read(ipath)
            bound=independent.get("artifact_sha256")==artifact
            passing=independent.get("kind")=="independent_territory_card_review" and independent.get("release_candidate") is True and float(independent.get("minimum_score",0))>9.0
            checks["independent_visual"]=bool(bound and passing)
            if not bound: findings.append("independent critic is not bound to the exact candidate PDF")
            if not passing: findings.append("independent critic did not pass every required R52 visual/coverage check strictly >9.0")
        except (engine.GateError,KeyError,TypeError,ValueError) as exc:
            checks["independent_visual"]=False;findings.append("independent critic evidence unavailable: "+str(exc))
    else:
        checks["independent_visual"]=True
    passed=not findings and all(v is True for k,v in checks.items() if k!="independent_visual_required")
    verdict={
        "schema_version":1,
        "kind":"territory_enforcer_critic",
        "critic_role":"enforcer_critic",
        "r52_revision":REVISION,
        "artifact_sha256":artifact,
        "review_sha256":engine.sha(review),
        "policy_integrity":integrity.get("r52"),
        "checks":checks,
        "findings":findings,
        "passed":passed,
        "release_gate_eligible":passed,
        "builder_cannot_override":True,
        "fixer_advisor_may_recommend":not passed,
        "edits_performed":0,
    }
    engine.json_write(output,verdict)
    return verdict

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("job",type=Path);ap.add_argument("output",type=Path)
    args=ap.parse_args()
    try:
        verdict=enforce(args.job,args.output);print(json.dumps(verdict,indent=2));return 0 if verdict["passed"] else 1
    except (EnforcerError,engine.GateError,KeyError,ValueError,OSError) as exc:
        print(json.dumps({"passed":False,"release_gate_eligible":False,"error":str(exc)}));return 2

if __name__=="__main__":
    raise SystemExit(main())
