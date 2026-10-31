"""Read-only knowledge coverage and benchmark status; no network or external action."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from inspection_engine.knowledge_registry import load_registry,prepare_case_research
from inspection_engine.serious_defect_benchmark import score_serious_defects, BenchmarkBlock

def main(argv=None):
    p=argparse.ArgumentParser(description='Rights-aware Michigan inspection knowledge and holdout audit')
    p.add_argument('--case',type=Path)
    p.add_argument('--human-holdout',type=Path)
    p.add_argument('--detections',type=Path)
    args=p.parse_args(argv)
    catalog=load_registry()
    result={'schema_version':5,'source_index_count':len(catalog['sources']),
            'copyright_full_text_bundled':False,'catalog_coverage':catalog['local_coverage'],
            'full_statewide_municipal_provisions_complete':False,
            'all_manufacturer_manuals_complete':False,
            'all_real_defects_detectable':False,
            'licensed_full_text_complete':False,'serious_defect_field_validation_complete':False,
            'status':'RESEARCH_AND_EVIDENCE_INCOMPLETE','customer_release_allowed':False}
    if args.case:result['case_research']=prepare_case_research(json.loads(args.case.read_text()))
    if bool(args.human_holdout)!=bool(args.detections):p.error('Holdout and detection files must be supplied together')
    if args.human_holdout:
        try:result['benchmark']=score_serious_defects(json.loads(args.human_holdout.read_text()),json.loads(args.detections.read_text()))
        except BenchmarkBlock as exc:result['benchmark']={'status':'BLOCKED','reason':str(exc)}
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2 # never imply knowledge completeness or customer release
if __name__=='__main__':raise SystemExit(main())
