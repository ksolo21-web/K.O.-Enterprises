"""Operator-invoked offline research/audit; no scheduled web crawling or customer uploads.

Run from the home-inspection project directory:
  python -m scripts.knowledge_watch_v7 audit
  python -m scripts.knowledge_watch_v7 case --input /PRIVATE/case_metadata.json
  python -m scripts.knowledge_watch_v7 diff --before /PRIVATE/receipt1.json --after /PRIVATE/receipt2.json
  python -m scripts.knowledge_watch_v7 benchmark --cases /PRIVATE/cases.json --predictions /PRIVATE/predictions.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from inspection_engine.case_research_v7 import registry_load, case_research, compare_receipts, KnowledgeBlocked
from inspection_engine.field_validation_v7 import evaluation_summary
from inspection_engine.statewide_ahj_v7 import parse_verified_transcription, AHJImportBlocked
from inspection_engine.coverage_expansion import lookup_indexed_model_manual


def audit():
    cat=registry_load()
    return {'schema_version':7,'status':'REQUIRES_EXTERNAL_EVIDENCE',
            'official_access_endpoints':len(cat['sources']),
            'verified_municipality_pilot_entries':len(cat['pilot_municipalities']),
            'fully_verified_michigan_jurisdictions':cat['complete_michigan_municipalities_verified'],
            'licensed_copyrighted_full_text_embedded':cat['licensed_full_text_embedded'],
            'professionally_adjudicated_field_cases':cat['professionally_adjudicated_field_cases'],
            'external_sources_automatically_scraped':0,
            'state_specific_applicability_confirmed':False,
            'mandatory_remaining_work':[
              'Review current Michigan LARA four-discipline jurisdiction directory per locality and date',
              'Review enacted city ordinances and amendments against municipal clerk / AHJ',
              'Secure explicit publisher permission before any full copyrighted machine ingestion',
              'Verify full make/model/serial and actual document revision against photographed equipment',
              'Collect consented independent professional holdouts and authenticate qualifications',
              'Validate critical and major misses and customer-facing release with qualified inspector'],
            'company_autonomy_paused':(Path(__file__).resolve().parents[3]/'PAUSE_AUTONOMY').is_file(),
            'customer_release_allowed':False}


def _read(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>8_000_000:
        raise KnowledgeBlocked('Unsafe or excessive operator-provided record')
    return json.loads(p.read_text(encoding='utf-8'))


def main(argv=None):
    p=argparse.ArgumentParser(description='Offline verified knowledge and field benchmark checkpoint')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('audit')
    case=sub.add_parser('case');case.add_argument('--input',required=True)
    diff=sub.add_parser('diff');diff.add_argument('--before',required=True);diff.add_argument('--after',required=True)
    bm=sub.add_parser('benchmark');bm.add_argument('--cases',required=True);bm.add_argument('--predictions',required=True)
    bm.add_argument('--signed-protocol',required=False)
    imp=sub.add_parser('ahj-import');imp.add_argument('--csv',required=True)
    imp.add_argument('--source-sha256',required=True);imp.add_argument('--revision',required=True)
    imp.add_argument('--operator-id',required=True)
    man=sub.add_parser('manual-index');man.add_argument('--brand',required=True);man.add_argument('--model',required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='audit':result=audit()
        elif args.command=='case':result=case_research(_read(args.input))
        elif args.command=='diff':result=compare_receipts(_read(args.before),_read(args.after))
        elif args.command=='benchmark':result=evaluation_summary(_read(args.cases),_read(args.predictions),_read(args.signed_protocol) if args.signed_protocol else None)
        elif args.command=='manual-index':result=lookup_indexed_model_manual(args.brand,args.model)
        elif args.command=='ahj-import':
            p=Path(args.csv)
            if p.is_symlink() or p.stat().st_size>3_000_000:raise KnowledgeBlocked('Invalid locality transcription file')
            imported=parse_verified_transcription(p.read_text(encoding='utf-8'),state_source_sha256=args.source_sha256,
                source_revision=args.revision,operator_id=args.operator_id)
            result={k:imported[k] for k in ('status','imported_units','source_revision','source_sha256','transcription_sha256','parcel_level_authority_verified','complete_michigan_coverage_verified','customer_release_allowed')}
        else:raise KnowledgeBlocked('Unknown audit mode')
    except (KnowledgeBlocked,AHJImportBlocked,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        result={'status':'BLOCKED','error':str(exc),'customer_release_allowed':False}
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['status'] not in ('BLOCKED',) and args.command in ('case','diff','manual-index','ahj-import') else 2

if __name__=='__main__':raise SystemExit(main())
