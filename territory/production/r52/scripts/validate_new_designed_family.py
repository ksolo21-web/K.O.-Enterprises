#!/usr/bin/env python3
import argparse, json, math, hashlib, os, sys
import fitz

PAGE=(768.0,480.5)
BOXES={
  "sidebar": (9.0,9.0,155.0,472.0),
  "map_panel": (164.0,9.0,759.0,375.0),
  "directions_panel": (164.0,385.0,759.0,472.0),
}
PALETTE={"yellow":(255,220,24),"green":(81,199,43),"red":(255,20,53)}
SIDEBAR_DARK=(16,33,43)
PANEL_BORDER=(214,224,228)


def rgb255(c):
    if c is None: return None
    return tuple(int(round(v*255)) for v in c)

def dist(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def rect_tuple(r): return (r.x0,r.y0,r.x1,r.y1)
def rect_close(r, exp, tol=2.0): return all(abs(a-b)<=tol for a,b in zip(rect_tuple(r),exp))

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for ch in iter(lambda:f.read(1<<20),b''): h.update(ch)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--json-out')
    args=ap.parse_args()
    pdf=args.pdf
    doc=fitz.open(pdf)
    findings=[]; checks={}
    checks['one_page']=len(doc)==1
    if len(doc)!=1:
        findings.append(f'Expected 1 page, found {len(doc)}')
    page=doc[0]
    checks['page_size'] = abs(page.rect.width-PAGE[0])<=0.5 and abs(page.rect.height-PAGE[1])<=0.5
    if not checks['page_size']: findings.append(f'Page size {page.rect.width:.2f}x{page.rect.height:.2f}, expected 768x480.5')
    drawings=page.get_drawings()
    # geometry candidates by exact-ish bounding rects
    for key,exp in BOXES.items():
        cands=[d for d in drawings if rect_close(d['rect'],exp,2.0)]
        checks[key+'_geometry']=bool(cands)
        if not cands: findings.append(f'Missing canonical {key} geometry near {exp}')
    # Sidebar dark fill
    sidebar=[d for d in drawings if rect_close(d['rect'],BOXES['sidebar'],2.0) and d.get('fill')]
    checks['sidebar_dark_fill']=any(dist(rgb255(d['fill']),SIDEBAR_DARK)<=5 for d in sidebar)
    if not checks['sidebar_dark_fill']: findings.append('Sidebar fill is not canonical dark family near #10212B')
    # palette swatches
    swatches=[]
    for d in drawings:
        r=d['rect']; fill=rgb255(d.get('fill'))
        if fill and 24<=r.x0<=32 and 44<=r.x1<=52 and 190<=r.y0<=310 and 17<=r.width<=23 and 17<=r.height<=23:
            swatches.append((r,fill))
    for name,target in PALETTE.items():
        ok=any(dist(fill,target)<=3 for r,fill in swatches)
        checks['swatch_'+name]=ok
        if not ok: findings.append(f'Missing canonical {name} legend swatch {target}')
    # text spans
    spans=[]
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l.get('spans',[]):
                t=s.get('text','').strip()
                if t: spans.append(s)
    def span_match(text, xmin,xmax,ymin,ymax,size_min=None,size_max=None,bold=None):
        for s in spans:
            if s['text'].strip().upper()==text.upper():
                x0,y0,x1,y1=s['bbox']
                if not (xmin<=x0<=xmax and ymin<=y0<=ymax): continue
                if size_min is not None and s['size']<size_min: continue
                if size_max is not None and s['size']>size_max: continue
                if bold is True and 'Bold' not in s['font']: continue
                if bold is False and 'Bold' in s['font']: continue
                return True
        return False
    required=[
      ('territory_header', span_match('TERRITORY',24,36,32,48,11,13.5,False)),
      ('legend_header', span_match('LEGEND',24,36,150,180,10,13.5,True)),
      ('legend_inside', span_match('Work Inside Only',52,62,192,210,8.8,10.2,False)),
      ('legend_both', span_match('Work Both Sides',52,62,236,254,8.8,10.2,False)),
      ('legend_dnw', span_match('Do Not Work',52,62,280,298,8.8,10.2,False)),
      ('updated_header', span_match('UPDATED',24,36,416,434,9,11.5,True)),
    ]
    for k,v in required:
        checks[k]=v
        if not v: findings.append('Missing/misplaced canonical text: '+k)
    # territory id: one large bold span in sidebar
    id_ok=False; locality_ok=False; date_ok=False
    for s in spans:
        x0,y0,x1,y1=s['bbox']; size=s['size']; txt=s['text'].strip()
        if 24<=x0<=36 and 58<=y0<=92 and 35<=size<=43 and 'Bold' in s['font'] and txt.upper()!='TERRITORY': id_ok=True
        if 24<=x0<=36 and 118<=y0<=145 and 10.5<=size<=13.8 and txt.upper() not in ('LEGEND','TERRITORY'): locality_ok=True
        if 24<=x0<=36 and 435<=y0<=455 and 9.5<=size<=12.5 and any(ch.isdigit() for ch in txt): date_ok=True
    checks['territory_id_hierarchy']=id_ok
    checks['locality_hierarchy']=locality_ok
    checks['updated_date']=date_ok
    if not id_ok: findings.append('No canonical large bold territory ID in sidebar')
    if not locality_ok: findings.append('No canonical locality text in sidebar')
    if not date_ok: findings.append('No canonical updated date in sidebar')
    # Directions label in lower panel. Released references contain both a standard
    # icon+text start near x=226 and an approved compact detail variant near x=185.
    dir_ok=False
    for s in spans:
        txt=s['text'].strip()
        if txt.lower().startswith('directions:'):
            x0,y0,x1,y1=s['bbox']
            if 180<=x0<=238 and 390<=y0<=418 and 8.0<=s['size']<=10.2:
                dir_ok=True
    checks['directions_label']=dir_ok
    if not dir_ok: findings.append('Directions text not in canonical lower-panel region/style band')
    # Size gate
    size=os.path.getsize(pdf)
    checks['under_300k']=size<300000
    if not checks['under_300k']: findings.append(f'PDF size {size} >= 300000 bytes')
    passed=all(checks.values())
    report={
      'schema_version':1,
      'contract':'New-Designed-Card-Family-Contract-R45',
      'artifact':os.path.abspath(pdf),
      'artifact_sha256':sha256(pdf),
      'bytes':size,
      'checks':checks,
      'findings':findings,
      'pass':passed,
      'scope_note':'Deterministic shell check only; visual family resemblance, map truth, labels and geography require critic review.'
    }
    out=json.dumps(report,indent=2)
    print(out)
    if args.json_out:
        with open(args.json_out,'w') as f: f.write(out+'\n')
    sys.exit(0 if passed else 2)

if __name__=='__main__': main()