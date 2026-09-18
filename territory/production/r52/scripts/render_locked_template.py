#!/usr/bin/env python3
import json, sys, hashlib, os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from territory_identity import derive

HERE=Path(__file__).resolve().parent
if (HERE/'references'/'R48-Canonical-Style-Tokens.json').exists():
    ROOT=HERE
elif (HERE.parent/'references'/'R48-Canonical-Style-Tokens.json').exists():
    ROOT=HERE.parent
else:
    ROOT=HERE
TOKENS_PATH=(ROOT/'references'/'R48-Canonical-Style-Tokens.json') if (ROOT/'references'/'R48-Canonical-Style-Tokens.json').exists() else (ROOT/'R48-Canonical-Style-Tokens.json')

def load_tokens(): return json.loads(TOKENS_PATH.read_text())
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find_fonts():
    candidates=[
      ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
      ('/usr/local/share/fonts/DejaVuSans.ttf','/usr/local/share/fonts/DejaVuSans-Bold.ttf')]
    for a,b in candidates:
        if Path(a).exists() and Path(b).exists():
            c=Path(a).with_name('DejaVuSansCondensed-Bold.ttf')
            if c.exists(): return a,b,str(c)
    raise SystemExit('R47 requires DejaVu Sans + Bold; font files not found in runtime')

def reg_fonts():
    a,b,c=find_fonts(); pdfmetrics.registerFont(TTFont('R47Sans',a)); pdfmetrics.registerFont(TTFont('R47SansBold',b)); pdfmetrics.registerFont(TTFont('R47IdBold',c))

def yb(page_h, top_y, h=0): return page_h-top_y-h

def draw_calendar(c,H,t):
    x=t['sidebar']['calendar']['x']; top=t['sidebar']['calendar']['top_y']; w=t['sidebar']['calendar']['w']; h=t['sidebar']['calendar']['h']
    y=yb(H,top,h); col=HexColor('#FFFFFF')
    c.setStrokeColor(col); c.setLineWidth(1); c.roundRect(x,y,w,h,2,stroke=1,fill=0)
    c.line(x,y+h-5,x+w,y+h-5); c.line(x+4,y+h+4,x+4,y+h-2); c.line(x+15,y+h+4,x+15,y+h-2)
    c.setFillColor(col)
    for dx in (4,9,14):
      for dy in (5,10): c.circle(x+dx,y+dy,0.6,stroke=0,fill=1)

def draw_compass(c,H,t):
    q=t['compass']; cx=q['center_x']; cy_top=q['center_y']; r=q['radius_pt']; cy=H-cy_top
    c.setStrokeColor(HexColor(t['palette']['text_primary'])); c.setLineWidth(.6); c.circle(cx,cy,r,stroke=1,fill=0)
    c.setFillColor(HexColor(t['palette']['compass_blue']))
    p=c.beginPath(); p.moveTo(cx,cy+r-2); p.lineTo(cx-4,cy); p.lineTo(cx,cy+2); p.lineTo(cx+4,cy); p.close(); c.drawPath(p,stroke=0,fill=1)
    c.setFont('R47Sans',q['north_label_size_pt']); c.setFillColor(HexColor(t['palette']['text_primary'])); c.drawCentredString(cx,cy-r+2,'N')

def resolve_identity(spec):
    ci=spec.get('card_identity')
    if not isinstance(ci,dict):
        raise SystemExit('R48 renderer requires card_identity; source/master label may not be used as rendered ID')
    d=derive(ci.get('base_number'),ci.get('card_class',''),ci.get('suffix',''))
    status=ci.get('identity_status')
    if spec.get('test_watermark'):
        if status not in ('verified','fixture_only'):
            raise SystemExit('R48 fixture identity_status must be verified or fixture_only')
    elif status!='verified':
        raise SystemExit('R48 production render requires verified card identity')
    if ci.get('display_id') not in (None,d['display_id']):
        raise SystemExit(f"card_identity.display_id must be {d['display_id']}")
    if ci.get('canonical_filename') not in (None,d['canonical_filename']):
        raise SystemExit(f"card_identity.canonical_filename must be {d['canonical_filename']}")
    out=dict(d); out['identity_status']=status; out['source_master_label']=spec.get('source_master_label')
    return out

def draw_shell(c,t,spec):
    W=t['page']['width_pt']; H=t['page']['height_pt']; p=t['palette']; sh=t['shell']; ty=t['type']
    c.setFillColor(HexColor(p['sidebar'])); s=sh['sidebar']; c.roundRect(s['x'],yb(H,s['y'],s['h']),s['w'],s['h'],s['radius'],stroke=0,fill=1)
    for name in ('map_panel','directions_panel'):
      r=sh[name]; c.setFillColor(HexColor(p['panel_fill'])); c.setStrokeColor(HexColor(p['panel_border'])); c.setLineWidth(.6); c.roundRect(r['x'],yb(H,r['y'],r['h']),r['w'],r['h'],r['radius'],stroke=1,fill=1)
    # sidebar dividers; locality-responsive locked variant
    c.setStrokeColor(HexColor(p['sidebar_divider'])); c.setLineWidth(.6)
    locality=str(spec.get('locality','[LOCALITY]'))
    # wrap locality before choosing locked variant
    words=locality.split(); loc_lines=[]; cur=''
    for w in words:
      test=(cur+' '+w).strip()
      if pdfmetrics.stringWidth(test,'R47Sans',ty['locality']['size_pt'])<=ty['locality']['max_width_pt']: cur=test
      else:
        if cur: loc_lines.append(cur)
        cur=w
    if cur: loc_lines.append(cur)
    variant='two_line_locality' if len(loc_lines)>1 else 'one_line_locality'
    v=t['sidebar']['variants'][variant]
    d=t['sidebar']['divider_1']; yy=H-v['divider_1_y']; c.line(d['x1'],yy,d['x2'],yy)
    d=t['sidebar']['divider_2']; yy=H-d['y']; c.line(d['x1'],yy,d['x2'],yy)
    # text helpers
    white=HexColor(p['text_white'])
    c.setFillColor(white); c.setFont('R47Sans',ty['territory_header']['size_pt']); c.drawString(28,H-55,'TERRITORY')
    ident=resolve_identity(spec); tid=ident['display_id']; idt=ty['territory_id']; fs=float(idt.get('default_size_pt',idt.get('size_pt',40)))
    while fs>idt.get('min_size_pt',28) and pdfmetrics.stringWidth(tid,'R47IdBold',fs)>idt.get('max_width_pt',117): fs-=0.5
    c.setFont('R47IdBold',fs); c.drawString(28,H-119,tid)
    c.setFont('R47Sans',ty['locality']['size_pt'])
    for i,line in enumerate(loc_lines[:2]): c.drawString(28,H-(147+i*15),line)
    c.setFont('R47SansBold',ty['legend_header']['size_pt']); c.drawString(28,H-(v['legend_header_top_y']+15),'LEGEND')
    for sw in t['sidebar']['swatches']:
      c.setFillColor(HexColor(sw['color'])); c.roundRect(sw['x'],yb(H,sw['top_y'],sw['h']),sw['w'],sw['h'],sw['radius'],stroke=0,fill=1)
      c.setFillColor(white); c.setFont('R47Sans',ty['legend_label']['size_pt']); c.drawString(56,H-(sw['label_top_y']+10),sw['name'])
    draw_calendar(c,H,t)
    c.setFillColor(white); c.setFont('R47SansBold',ty['updated_header']['size_pt']); c.drawString(28,H-439,'UPDATED')
    c.setFont('R47Sans',ty['updated_date']['size_pt']); c.drawString(28,H-457,spec.get('updated','[DATE]'))
    # car badge
    car=ROOT/t['directions']['car_badge_asset']
    if not car.exists(): car=ROOT/Path(t['directions']['car_badge_asset']).name
    cr=t['directions']['car_badge_rect']; c.drawImage(ImageReader(str(car)),cr['x'],yb(H,cr['y'],cr['h']),cr['w'],cr['h'],mask='auto')
    draw_compass(c,H,t)

def fit_image(c,img_path,rect,H):
    from PIL import Image
    im=Image.open(img_path); iw,ih=im.size
    x0,y0,x1,y1=rect; rw=x1-x0; rh=y1-y0
    scale=min(rw/iw,rh/ih); w=iw*scale; h=ih*scale
    x=x0+(rw-w)/2; y_top=y0+(rh-h)/2; y=H-y_top-h
    c.drawImage(ImageReader(str(img_path)),x,y,w,h,mask='auto')
    return [x,y_top,x+w,y_top+h]

def draw_map(c,t,spec):
    H=t['page']['height_pt']; layout=spec.get('layout_mode','full_map'); src=spec.get('map_image')
    if src and not Path(src).is_absolute(): src=str(ROOT/src)
    if src:
      if layout=='split_detail':
        fit_image(c,src,t['layout_modes']['split_detail']['full_map_rect'],H)
        fit_image(c,src,t['layout_modes']['split_detail']['north_detail_rect'],H)
        fit_image(c,src,t['layout_modes']['split_detail']['south_detail_rect'],H)
        c.setStrokeColor(HexColor(t['palette']['panel_border'])); c.setLineWidth(.6)
        x=t['layout_modes']['split_detail']['divider_x']; c.line(x,H-20,x,H-365)
        y=t['layout_modes']['split_detail']['detail_divider_y']; c.line(357,H-y,748,H-y)
        c.setFillColor(HexColor(t['palette']['text_secondary'])); c.setFont('R47SansBold',7); c.drawString(180,H-30,'FULL MAP'); c.drawString(364,H-30,'NORTH DETAIL'); c.drawString(364,H-245,'SOUTH DETAIL')
      else: fit_image(c,src,t['layout_modes']['full_map']['map_rect'],H)
    if spec.get('test_watermark'):
      c.saveState(); c.setFillColor(HexColor('#536D7D')); c.setFillAlpha(.70); c.setFont('R47SansBold',15); c.translate(455,H-190); c.rotate(18); c.drawCentredString(0,0,'R48 TEMPLATE-FIT TEST - NOT FOR FIELD USE'); c.restoreState()

def draw_directions(c,t,spec):
    H=t['page']['height_pt']; p=t['palette']; x=t['directions']['text_x']; lines=spec.get('directions_lines') or ['Directions: R48 locked template fixture.','This is a layout stress test, not a field-use territory card.','Geography/work rules are not certified by this fixture.']
    c.setFillColor(HexColor(p['text_primary'])); size=t['type']['directions']['size_pt']; c.setFont('R47Sans',size)
    tops=[400,420,442]
    for i,line in enumerate(lines[:3]):
      if i==0 and line.startswith('Directions:'):
        c.setFont('R47SansBold',size); c.drawString(x,H-(tops[i]+10),'Directions:'); c.setFont('R47Sans',size); c.drawString(x+61,H-(tops[i]+10),line[len('Directions:'):].strip())
      else: c.drawString(x,H-(tops[i]+10),line)

def render(spec_path,out_path):
    t=load_tokens(); reg_fonts(); W=t['page']['width_pt']; H=t['page']['height_pt']; token_sha=sha256(TOKENS_PATH)
    spec=json.loads(Path(spec_path).read_text())
    ident=resolve_identity(spec)
    if not spec.get('test_watermark') and Path(out_path).name != ident['canonical_filename']:
        raise SystemExit(f"R48 production output filename must be exactly {ident['canonical_filename']}")
    c=canvas.Canvas(out_path,pagesize=(W,H),pageCompression=1)
    c.setTitle(f"Territory {ident['display_id']} - R48 Locked Template")
    c.setSubject(f"R48 locked canonical territory template; display_id={ident['display_id']}; canonical_filename={ident['canonical_filename']}; source_master_label={spec.get('source_master_label','')}; token_sha256={token_sha}")
    c.setKeywords(f"R48;territory-card;locked-template;card-display-id:{ident['display_id']};canonical-filename:{ident['canonical_filename']};token-sha256:{token_sha}")
    c.setCreator('R48 Locked Territory Renderer')
    c.setProducer('R48 Locked Territory Renderer')
    draw_shell(c,t,spec); draw_map(c,t,spec); draw_directions(c,t,spec); c.showPage(); c.save()
    return token_sha

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: render_locked_template.py SPEC.json OUT.pdf')
    print(render(sys.argv[1],sys.argv[2]))