"""Offline v6 coverage audit and optional, local-only case verification plan.

No web calls, scheduled actions, PDF copying, customer media, or auto-approvals.
"""
from __future__ import annotations
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from inspection_engine.coverage_expansion import (
    CATALOGS, BASE, load_expansion, plan_municipal_verification,
    specialty_work_orders, ReferenceBlock)
from inspection_engine.coverage_expansion import lookup_indexed_model_manual
from inspection_engine.hazard_sweep import CATALOG, load_hazard_sweep,plan_hazard_sweep
from inspection_engine.sop_scope import audit_sop_scope


def audit(case=None):
    catalogs={name:load_expansion(name) for name in CATALOGS}
    hazards=load_hazard_sweep()
    s=audit_sop_scope()
    hashes={kind:hashlib.sha256((BASE/path).read_bytes()).hexdigest()
            for kind,path in CATALOGS.items()}
    hashes['critical_hazards']=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
    manual_index=BASE/'model_manual_index_v6.json'
    hashes['model_manual_index']=hashlib.sha256(manual_index.read_bytes()).hexdigest()
    exact_model_docs=json.loads(manual_index.read_text())['documents']
    municipal=catalogs['municipal']['locations']
    manufacturers=catalogs['manufacturers']['portals']
    supplemental=catalogs['specialties']['topics']
    result={'schema_version':6,'audit_date':date.today().isoformat(),
        'status':'KNOWLEDGE_GAPS_OPEN_NOT_CUSTOMER_RELEASE',
        'indexed_pilot_municipalities':len(municipal),
        'municipalities_with_all_amendments_verified':sum(r['verified_local_amendments'] for r in municipal),
        'case_specific_ahj_verifications':sum(r['verified_case_ahj'] for r in municipal),
        'manufacturer_official_portals':len(manufacturers),
        'exact_model_manuals_verified':sum(r['manuals_locally_verified'] for r in manufacturers),
        'manufacturer_model_listings_indexed':sum(len(x['models']) for x in exact_model_docs),
        'manufacturer_manual_titles_indexed':len(exact_model_docs),
        'supplemental_specialties_indexed':len(supplemental),
        'supplemental_specialties_operationally_inspected':0,
        'sop_unresolved_mapping_topics':len(s['unresolved_topics']),
        'hazard_systems_indexed':len(hazards['topics']),
        'actual_hazard_images_human_adjudicated':0,
        'licensed_full_copyrighted_text_ingested':0,
        'validated_all_defect_recognition':False,
        'source_file_sha256':hashes,
        'next_tasks':[
            'Have qualified reviewer check each local state/county/city authority and each discipline against official revised Statewide Jurisdiction List',
            'Capture dated, hashed private municipal amendment/permit records and resolve conflicts; do not infer applicability from city landing pages',
            'Tie rating-plate photos to exact-model manuals and serial/lot recall applicability before technical claims',
            'Add explicit inspector coverage and approved protocols for hearth, garage safety and separate commercial fire-life safety scope',
            'Obtain publisher-approved machine-use rights for protected standards where full text is necessary',
            'Collect consented qualified-expert-labeled real inspection cases and independently validate serious defects using locked holdouts'
        ],'customer_release_allowed':False}
    if case is not None:
        result['case_plan']=plan_municipal_verification(case)
        result['case_supplemental_tasks']=specialty_work_orders(case['building_type'])
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description='Knowledge coverage audit; never approves field release')
    p.add_argument('--case',type=Path,help='Private case metadata JSON (local use only)')
    p.add_argument('--out',type=Path,help='Write machine-readable JSON locally, do not commit real case data')
    args=p.parse_args(argv)
    try:
        case=json.loads(args.case.read_text()) if args.case else None
        result=audit(case)
    except (ReferenceBlock,ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'BLOCKED','error':str(exc),'customer_release_allowed':False},indent=2))
        return 2
    encoded=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if args.out:
        if args.out.exists():
            print(json.dumps({'status':'BLOCKED','error':'Refusing to overwrite prior audit'}))
            return 2
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(encoded)
    print(encoded)
    return 2  # gaps intentionally remain open

if __name__=='__main__':raise SystemExit(main())
