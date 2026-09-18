#!/usr/bin/env python3
import argparse,json,re,sys
from pathlib import Path
import fitz
from validate_territory_identity import validate_record

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('identity_json'); ap.add_argument('pdf'); ap.add_argument('--fixture',action='store_true'); a=ap.parse_args()
 data=json.loads(Path(a.identity_json).read_text()); r=validate_record(data,a.pdf,a.fixture); errs=list(r.get('errors',[])); exp=r.get('expected',{})
 try:
  d=fitz.open(a.pdf)
  if len(d)!=1: errs.append('PDF must be exactly one page')
  txt=d[0].get_text('text').splitlines()
  clean=[x.strip() for x in txt if x.strip()]
  if 'TERRITORY' not in clean: errs.append('visible TERRITORY header missing')
  else:
   i=clean.index('TERRITORY'); visible=clean[i+1] if i+1<len(clean) else ''
   if visible!=exp.get('display_id'): errs.append(f'visible card ID after TERRITORY must be {exp.get("display_id")!r}, got {visible!r}')
  src=str(data.get('source_master_label') or '')
  if src and src!=exp.get('display_id') and src in clean: errs.append('source_master_label appears as visible page text')
  meta=d.metadata or {}
  if exp.get('display_id') not in (meta.get('title') or ''): errs.append('PDF title metadata missing canonical display ID')
  if exp.get('canonical_filename') not in (meta.get('subject') or ''): errs.append('PDF subject metadata missing canonical filename')
 except Exception as e: errs.append(f'PDF inspection failed: {e}')
 out={'passed':not errs,'errors':errs,'expected':exp,'artifact':str(a.pdf)}; print(json.dumps(out,indent=2)); return 0 if out['passed'] else 1
if __name__=='__main__': raise SystemExit(main())