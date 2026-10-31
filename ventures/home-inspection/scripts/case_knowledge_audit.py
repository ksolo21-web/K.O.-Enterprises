"""Offline audit of a locally held Michigan case; never uploads source media."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from inspection_engine.case_verification import validate_case_context,evaluate_finding,coverage_gaps
from inspection_engine.michigan_authority import authority_digest
from inspection_engine.failure_modes import playbook_digest
from inspection_engine.source_of_truth import guidance_digest


def audit_case(case,findings,root):
    ctx=validate_case_context(case)
    if not isinstance(findings,list):raise ValueError('Findings must be a JSON list')
    rows=[{'finding_index':i,'system':f.get('system') if isinstance(f,dict) else None,
           'assessment':evaluate_finding(case,f,root)} for i,f in enumerate(findings)]
    coverage=coverage_gaps(case,[f for f in findings if isinstance(f,dict)])
    return {'schema_version':1,'case_id':case['case_id'], 'scope':'MI_CASE_LOCAL_REVIEW_ONLY',
        'selected_reference_candidates':ctx['candidate_code_index'],
        'findings':rows,'coverage':coverage,
        'source_sha256':{'michigan_codes':authority_digest(),'failure_modes':playbook_digest(),'system_guidance':guidance_digest()},
        'independent_authentication_complete':False,'qualified_inspector_release_required':True,
        'automated_code_violation_finding_allowed':False,'customer_release_allowed':False}


def main():
    p=argparse.ArgumentParser(description='Offline Michigan knowledge case audit; no customer-release authority')
    p.add_argument('case_json',type=Path);p.add_argument('findings_json',type=Path)
    p.add_argument('--case-root',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args()
    case=json.loads(args.case_json.read_text(encoding='utf-8'))
    findings=json.loads(args.findings_json.read_text(encoding='utf-8'))
    report=audit_case(case,findings,args.case_root)
    if args.out.exists():raise FileExistsError('Will not overwrite case evidence')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':'CASE_AUDIT_CREATED_REVIEW_PENDING','path':str(args.out),
                      'finding_count':len(report['findings']),'customer_release_allowed':False}))
if __name__=='__main__':main()
