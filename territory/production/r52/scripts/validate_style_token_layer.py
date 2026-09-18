#!/usr/bin/env python3
import json,sys,hashlib,re
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[1]
TOK=ROOT/'references'/'R48-Canonical-Style-Tokens.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb8(c): return tuple(round(x*255) for x in c) if c else None
def near_rect(a,b,tol=2): return max(abs(a[i]-b[i]) for i in range(4))<=tol

def main(pdf):
 t=json.loads(TOK.read_text()); h=sha(TOK); d=fitz.open(pdf); errs=[]; checks={}
 checks['one_page']=len(d)==1
 if not checks['one_page']: errs.append('must be one page'); return {'passed':False,'checks':checks,'errors':errs}
 p=d[0]; checks['page_size']=abs(p.rect.width-t['page']['width_pt'])<=.5 and abs(p.rect.height-t['page']['height_pt'])<=.5
 if not checks['page_size']: errs.append('page size != locked tokens')
 meta=d.metadata or {}; provenance=h in (meta.get('subject','')+meta.get('keywords','')) and meta.get('producer') in ('R47 Locked Territory Renderer','R48 Locked Territory Renderer')
 checks['token_provenance']=provenance
 if not provenance: errs.append('missing exact R47 token provenance')
 drawings=p.get_drawings(); targets={
  'sidebar':[9,9,155,472], 'map_panel':[164,9,759,375], 'directions_panel':[164,385,759,472]
 }
 for name,r in targets.items():
  found=False
  for q in drawings:
   rr=list(q['rect'])
   if near_rect(rr,r,2): found=True; break
  checks[name]=found
  if not found: errs.append(f'missing {name} geometry')
 # palette checks
 expected={'sidebar':(16,33,43),'yellow':(255,220,24),'green':(81,199,43),'red':(255,20,53)}
 actual=[]
 for q in drawings:
  if q.get('fill'): actual.append(rgb8(q['fill']))
 checks['sidebar_fill']=expected['sidebar'] in actual
 checks['legend_swatches']=all(expected[k] in actual for k in ('yellow','green','red'))
 if not checks['sidebar_fill']: errs.append('sidebar fill token mismatch')
 if not checks['legend_swatches']: errs.append('legend swatch token mismatch')
 # font family check for shell text
 spans=[]
 for b in p.get_text('dict')['blocks']:
  for line in b.get('lines',[]):
   for s in line['spans']:
    if s['text'].strip(): spans.append(s)
 shell_names={'TERRITORY','LEGEND','UPDATED','Work Inside Only','Work Both Sides','Do Not Work'}
 shell=[s for s in spans if s['text'].strip() in shell_names]
 checks['dejavu_shell_font']=bool(shell) and all(s['font'].startswith('DejaVuSans') for s in shell)
 if not checks['dejavu_shell_font']: errs.append('new-output shell font is not locked DejaVu Sans')
 # R47 locked territory-ID box / font: no wrapping, no sidebar widening, minimum 28pt.
 id_candidates=[]
 for s in spans:
  x0,y0,x1,y1=s['bbox']
  txt=s['text'].strip()
  if x0>=24 and x1<=151 and 60<=y0<=130 and txt not in shell_names:
   if s.get('size',0)>=27: id_candidates.append(s)
 id_span=max(id_candidates,key=lambda z:z.get('size',0),default=None)
 checks['territory_id_locked_box']=bool(id_span) and id_span['font'].startswith('DejaVuSansCondensed-Bold') and id_span['size']>=27.9 and id_span['bbox'][0]>=27 and id_span['bbox'][2]<=145.5
 if not checks['territory_id_locked_box']: errs.append('territory ID must fit locked x=28..145 box in DejaVuSansCondensed-Bold at >=28pt')
 # Locality may use exactly one of two locked variants; never three+ lines.
 loc=[]
 for s in spans:
  x0,y0,x1,y1=s['bbox']
  txt=s['text'].strip()
  if 24<=x0<=45 and 125<=y0<=165 and txt not in {'LEGEND'} and s.get('size',0)<20:
   if txt and txt not in shell_names: loc.append(s)
 # dedupe any accidental extraction duplicates by rounded bbox/text
 uniq=[]; seen=set()
 for s in loc:
  key=(s['text'].strip(),tuple(round(v,1) for v in s['bbox']))
  if key not in seen: seen.add(key); uniq.append(s)
 loc=uniq
 checks['locality_locked_variant']=1<=len(loc)<=2 and all(s['font'].startswith('DejaVuSans') for s in loc)
 if not checks['locality_locked_variant']: errs.append('locality must use locked one-line or two-line variant')
 return {'passed':not errs,'artifact_sha256':sha(pdf),'token_sha256':h,'checks':checks,'errors':errs}
if __name__=='__main__':
 if len(sys.argv)!=2: raise SystemExit('usage: validate_style_token_layer.py FINAL.pdf')
 r=main(sys.argv[1]); print(json.dumps(r,indent=2)); raise SystemExit(0 if r['passed'] else 1)