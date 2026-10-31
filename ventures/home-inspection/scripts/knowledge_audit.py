"""Offline source-of-truth audit: no network, inspection or code approval."""
import argparse
from datetime import date
import json
from pathlib import Path
from inspection_engine.source_of_truth import (KNOWN_SYSTEMS, catalog_digest,
                                               load_catalog, reference_sources)


def audit(today:date|None=None):
    today=today or date.today()
    sources=load_catalog()['source_records']
    covered=sorted(set().union(*(set(s['systems']) for s in sources)))
    age={s['id']:(today-date.fromisoformat(s['last_reviewed'])).days for s in sources}
    return {'schema_version':1,'catalog_digest_sha256':catalog_digest(),
            'run_date':today.isoformat(),'source_count':len(sources),
            'all_systems_covered':set(covered)==KNOWN_SYSTEMS,
            'system_count':len(covered),'system_source_counts':{
                system:len(reference_sources([system])) for system in sorted(KNOWN_SYSTEMS)},
            'active_reference_count':sum(s['status']=='active_reference' for s in sources),
            'pending_effective_date':sorted(s['id'] for s in sources if s['status']=='pending_effective_date'),
            'older_than_180_days':sorted(sid for sid,days in age.items() if days>180),
            'pages_archived_with_verified_hashes':sum(bool(s['content_snapshot_sha256']) for s in sources),
            'live_web_validation_performed':False,
            'field_accuracy_verified':False,'local_code_compliance_verified':False,
            'customer_release_allowed':False}


def main():
    p=argparse.ArgumentParser(description='Offline versioned inspection reference audit')
    p.add_argument('--output',type=Path,help='JSON report path; refuses to overwrite')
    args=p.parse_args()
    data=audit()
    result=json.dumps(data,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as f: f.write(result)
    print(result,end='')

if __name__=='__main__':main()
