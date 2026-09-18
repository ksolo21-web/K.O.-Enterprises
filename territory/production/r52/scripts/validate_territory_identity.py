#!/usr/bin/env python3
import argparse,json,re,sys
from pathlib import Path
from territory_identity import derive,looks_like_master_alias

def validate_record(data, actual_filename=None, allow_fixture=False):
    errs=[]
    src=str(data.get('source_master_label') or '').strip()
    ci=data.get('card_identity')
    if not src: errs.append('source_master_label required as separate source alias')
    if not isinstance(ci,dict): return {'passed':False,'errors':errs+['card_identity object required']}
    try: exp=derive(ci.get('base_number'),ci.get('card_class',''),ci.get('suffix',''))
    except Exception as e: return {'passed':False,'errors':errs+[str(e)]}
    for k in ('base_number','card_class','suffix','display_id','canonical_filename'):
        if ci.get(k)!=exp[k]: errs.append(f'card_identity.{k} mismatch: expected {exp[k]!r}, got {ci.get(k)!r}')
    disp=str(ci.get('display_id') or '')
    if looks_like_master_alias(disp) or '-' in disp: errs.append('visible display_id may not use master-map/hyphen notation')
    if disp.startswith('R'): errs.append('visible display_id may not use R residential prefix')
    status=ci.get('identity_status')
    if allow_fixture:
        if status not in ('verified','fixture_only'): errs.append('fixture identity_status must be verified or fixture_only')
    elif status!='verified': errs.append('field-use identity_status must be verified')
    if actual_filename is not None and not allow_fixture:
        if Path(actual_filename).name!=exp['canonical_filename']: errs.append(f'actual filename must be exactly {exp["canonical_filename"]!r}')
    return {'passed':not errs,'errors':errs,'expected':exp,'source_master_label':src}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('identity_json'); ap.add_argument('--actual-filename'); ap.add_argument('--fixture',action='store_true')
    a=ap.parse_args(); data=json.loads(Path(a.identity_json).read_text()); r=validate_record(data,a.actual_filename,a.fixture); print(json.dumps(r,indent=2)); return 0 if r['passed'] else 1
if __name__=='__main__': raise SystemExit(main())