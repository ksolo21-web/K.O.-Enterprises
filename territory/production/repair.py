"""Bounded vector-label repair. Original geometry and source files remain immutable.
The numeric critic measures actual rendered glyphs; it is not a visual/model approval.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
from pathlib import Path
import tempfile
import fitz
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,binary_dilation
import engine

MAX_ALTERNATIVES=64
SCALE=2
class RepairError(engine.GateError):pass

def number(x,lo,hi):
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or not lo<=x<=hi:raise RepairError('number outside bounds')
    return float(x)

def points(values):
    if not isinstance(values,list) or not 2<=len(values)<=1000:raise RepairError('a bounded approved polyline is required')
    result=[]
    for p in values:
        if not isinstance(p,list) or len(p)!=2:raise RepairError('invalid point')
        result.append((number(p[0],0,4000),number(p[1],0,4000)))
    if any(math.dist(a,b)<1e-5 for a,b in zip(result,result[1:])):raise RepairError('degenerate polyline')
    return result

def positions(poly,advances,start):
    lengths=[math.dist(a,b) for a,b in zip(poly,poly[1:])];total=sum(lengths)
    cursor=number(start,0,total)
    if cursor+sum(advances)>total:raise RepairError('label does not fit the supplied curve')
    result=[]
    for advance in advances:
        probe=cursor;index=0
        while index<len(lengths)-1 and probe>lengths[index]:probe-=lengths[index];index+=1
        a,b=poly[index:index+2];t=probe/lengths[index]
        result.append(((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),-math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))))
        cursor+=advance
    return result

def pixels(page,scale=2):
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
    return np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3).copy()

def colored(a):
    x=a.astype(np.int16)
    return (x.max(2)-x.min(2)>60)&(x.min(2)<220)

def font_from_source(doc,page,name):
    found=[f for f in page.get_fonts() if f[4]==name]
    if len(found)!=1:raise RepairError('approved font resource is not unique in source')
    xref,ext,kind,base,resource,*_=found[0]
    if any(s in base.lower() for s in ('bold','black','semibold')):raise RepairError('bold label font is forbidden')
    raw=doc.extract_font(xref)[3] if xref else b''
    aliases={'Helvetica':'helv','Times-Roman':'tiro','Courier':'cour'}
    if raw:return fitz.Font(fontbuffer=raw),raw,None
    if base not in aliases:raise RepairError('source font cannot be reproduced without substitution')
    return fitz.Font(fontname=aliases[base]),None,aliases[base]

def install_font(page,raw,alias):
    if raw:page.insert_font(fontname='RepairFont',fontbuffer=raw);return 'RepairFont'
    return alias

def label_overlay(size,text,placement,font_info,font_size):
    font,raw,alias=font_info
    if any(not font.has_glyph(ord(c)) for c in text if not c.isspace()):raise RepairError('source font lacks a requested glyph')
    advances=[font.glyph_advance(ord(c))*font_size for c in text]
    if placement.get('kind')=='curved':
        poses=positions(points(placement.get('baseline_curve')),advances,placement.get('start',0))
    elif placement.get('kind')=='direct':
        value=placement.get('baseline')
        if not isinstance(value,list) or len(value)!=2:raise RepairError('invalid baseline')
        angle=number(placement.get('angle',0),-180,180);x=number(value[0],0,size[0]);y=number(value[1],0,size[1])
        poses=[]
        for advance in advances:
            poses.append(((x,y),angle));x+=advance*math.cos(math.radians(angle));y-=advance*math.sin(math.radians(angle))
    else:raise RepairError('unsupported placement')
    d=fitz.open();p=d.new_page(width=size[0],height=size[1]);name=install_font(p,raw,alias)
    for char,(xy,angle) in zip(text,poses):
        p.insert_text(xy,char,fontname=name,fontsize=font_size,color=(0,0,0),morph=(fitz.Point(*xy),fitz.Matrix(angle)))
    ink=pixels(p).min(2)<180
    return d,ink,poses

def allowed_mask(shape,rectangles,scale):
    mask=np.zeros(shape,dtype=bool)
    for r in rectangles:
        x0,y0,x1,y1=r
        # Only pixels fully inside an approved rectangle are authorized.
        a,b,c,d=math.ceil(x0*scale),math.ceil(y0*scale),math.floor(x1*scale),math.floor(y1*scale)
        mask[b:d,a:c]=True
    return mask

def invariant_check(source:Path,candidate:Path,masks:list) -> dict:
    with fitz.open(source) as a,fitz.open(candidate) as b:
        if len(a)!=1 or len(b)!=1 or tuple(a[0].rect)!=tuple(b[0].rect):raise RepairError('page identity changed')
        evidence=[]
        for scale in (1,2,4):
            before,after=pixels(a[0],scale),pixels(b[0],scale)
            allowed=allowed_mask(before.shape[:2],masks,scale)
            changed=np.any(before!=after,axis=2)
            outside=int(np.count_nonzero(changed&~allowed))
            road_change=int(np.count_nonzero(changed&(colored(before)|colored(after))))
            evidence.append({'scale':scale,'changed_outside_masks':outside,'changed_colored_ink':road_change})
            if outside or road_change:raise RepairError('repair changed pixels outside authorization or changed colored ink')
    engine.inspect_pdf(candidate)
    return {'kind':'deterministic_invariant_check','views':evidence,'visual_approval':False}

def repair(recipe_path:Path,outdir:Path) -> dict:
    engine.private_guard();engine.verify_skills()
    if outdir.exists():raise RepairError('fresh repair directory required')
    recipe=engine.json_read(recipe_path);root=recipe_path.parent
    if recipe.get('mode')!='approved_vector_label_revision':raise RepairError('unsupported repair mode')
    source=engine.pinned(root,recipe['source']);source_hash=engine.sha(source)
    masks=[tuple(engine.rect(r)) for r in recipe.get('approved_masks',[])]
    labels=recipe.get('labels')
    if not masks or not isinstance(labels,list) or not 1<=len(labels)<=12:raise RepairError('explicit masks and 1-12 label repairs required')
    choices=[v.get('placements',[]) for v in labels]
    if any(not 1<=len(c)<=MAX_ALTERNATIVES for c in choices) or math.prod(map(len,choices))>MAX_ALTERNATIVES:raise RepairError('repair search exceeds bounded authorized alternatives')
    doc=fitz.open(source)
    if len(doc)!=1:raise RepairError('one-page source required')
    page=doc[0];size=(page.rect.width,page.rect.height)
    if size[0]>1600 or size[1]>1600:raise RepairError('page exceeds review memory bound')
    if any(not page.rect.contains(fitz.Rect(m)) for m in masks):raise RepairError('mask outside page')
    source_pixels=pixels(page);fonts=[];boxes=[]
    for label in labels:
        box=engine.rect(label['old_box']);text=label.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>120:raise RepairError('invalid label text')
        if not any(fitz.Rect(m).contains(box) for m in masks):raise RepairError('original label not contained by an approved mask')
        actual=page.get_textbox(box).replace('\n','').strip()
        if actual!=text.strip():raise RepairError('source text does not exactly match; raster/outlines require an approved editable source')
        if any(box.intersects(other) for other in boxes):raise RepairError('overlapping removal boxes need explicit source repair')
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line.get('spans',[]):
                    for char in span.get('chars',[]):
                        cr=fitz.Rect(char['bbox'])
                        if cr.intersects(box) and not box.contains(cr):raise RepairError('partial glyph removal is not authorized')
        fonts.append(font_from_source(doc,page,label['font_resource']));boxes.append(box)
        number(label['font_size'],7,24)
        if not isinstance(label.get('road_id'),str) or not label['road_id']:raise RepairError('assigned road identity required')
        points(label['road_polyline'])
    for box in boxes:page.add_redact_annot(box,fill=False,cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    clean=doc.tobytes(garbage=4,deflate=True);doc.close()
    with fitz.open(stream=clean,filetype='pdf') as blank:
        clean_pixels=pixels(blank[0]);existing=(clean_pixels.max(2)<150)
    authorized=allowed_mask(source_pixels.shape[:2],masks,SCALE)
    outdir.mkdir(parents=True);rounds=[];best=None
    for index,selected in enumerate(itertools.product(*choices)):
        record={'round':index+1,'status':'rejected','reasons':[],'visual_approval':False}
        overlays=[];occupied=np.zeros(existing.shape,dtype=bool);cost=0.0
        try:
            for label,placement,font_info in zip(labels,selected,fonts):
                overlay,ink,poses=label_overlay(size,label['text'],placement,font_info,label['font_size']);overlays.append(overlay)
                if np.any(ink&~authorized):raise RepairError('new glyphs leave approved masks')
                if np.any(binary_dilation(ink,iterations=2)&(occupied|existing)):raise RepairError('new label collides with existing ink or another label')
                road=Image.new('1',(existing.shape[1],existing.shape[0]));draw=ImageDraw.Draw(road)
                line=points(label['road_polyline']);draw.line([(round(x*SCALE),round(y*SCALE)) for x,y in line],fill=1,width=round(number(label.get('road_width',4),1,15)*SCALE)+4)
                assigned=np.asarray(road,dtype=bool)&colored(source_pixels)
                if not np.any(assigned):raise RepairError('assigned road guide has no source road ink')
                distance=distance_transform_edt(~assigned);gaps=[]
                for char,(xy,angle) in zip(label['text'],poses):
                    if char.isspace():continue
                    glyph,mask,_=label_overlay(size,char,{'kind':'direct','baseline':list(xy),'angle':angle},font_info,label['font_size']);glyph.close()
                    if not np.any(mask):raise RepairError('missing rendered glyph')
                    gaps.append(float(distance[mask].min()))
                if min(gaps)<2 or max(gaps)>15 or max(gaps)-min(gaps)>8:raise RepairError('rendered glyph-to-road gap outside 2-15 pixels or excessive spread')
                cost+=sum((g-6)**2 for g in gaps)/len(gaps);occupied|=ink
            target=outdir/f'candidate-{index+1:03}.pdf'
            with fitz.open(stream=clean,filetype='pdf') as candidate:
                for overlay in overlays:candidate[0].show_pdf_page(candidate[0].rect,overlay,0)
                candidate.save(target,garbage=4,deflate=True)
            check=invariant_check(source,target,masks)
            record.update(status='candidate',file=target.name,sha256=engine.sha(target),cost=cost,invariants=check)
            if best is None or cost<best['cost']:best=record.copy()
        except (RepairError,engine.GateError) as error:record['reasons'].append(str(error))
        finally:
            for overlay in overlays:overlay.close()
        rounds.append(record)
        engine.json_write(outdir/'repair-ledger.json',{'source_sha256':source_hash,'recipe_sha256':engine.sha(recipe_path),'rounds':rounds,'selected':best,'release_ready':False})
    if engine.sha(source)!=source_hash:raise RepairError('immutable source identity changed')
    return {'rounds':len(rounds),'candidates':sum(r['status']=='candidate' for r in rounds),'selected':best,'release_ready':False,'independent_visual_review_required':True}
