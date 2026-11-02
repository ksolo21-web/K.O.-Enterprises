"""Option 2 modern editorial inspection-report template.

Deterministic, photo-led report. Media captions indicate whether photographs are
illustrative. It does not infer defects from photographs or release inspections.
"""
from __future__ import annotations
import json
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas as cv
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from .core import SYSTEMS, blockers, coverage, detect_mode, record_status, safe_path
from .equipment import research_equipment

NAVY='#152A3C'; DARK='#223245'; MUTED='#5F7182'; LIGHT='#E4EBF0'; PALE='#F5F7F7'; SAND='#F2F0EA'; WHITE='#FFFFFF'; BRONZE='#B0916A'
W,H=letter; M=48; CW=W-2*M
FONT_REG='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
FONT_BOLD='/usr/share/fonts/truetype/lato/Lato-Bold.ttf'
FONT_LIGHT='/usr/share/fonts/truetype/lato/Lato-Light.ttf'
# Portable fallback: do not redistribute font files; use built-in PDF fonts
# when Lato is not installed on the host OS.
FONT_MAP={'Lato':'Helvetica','LatoB':'Helvetica-Bold','LatoL':'Helvetica'}
for n,p in [('Lato',FONT_REG),('LatoB',FONT_BOLD),('LatoL',FONT_LIGHT)]:
    if Path(p).is_file():
        if n not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(n,p))
        FONT_MAP[n]=n

def color(c,hex):c.setFillColor(HexColor(hex))
def box(c,x,y,w,h,fill): color(c,fill);c.rect(x,y,w,h,stroke=0,fill=1)
def line(c,x,y,xx,yy,co=LIGHT,th=.8):c.setStrokeColor(HexColor(co));c.setLineWidth(th);c.line(x,y,xx,yy)
def txt(c,t,x,y,font='Lato',size=10,co=DARK):
    color(c,co);c.setFont(FONT_MAP.get(font,font),size);c.drawString(x,y,str(t))
def right(c,t,x,y,font='Lato',size=10,co=DARK):
    color(c,co);c.setFont(FONT_MAP.get(font,font),size);c.drawRightString(x,y,str(t))
def wraps(s,font,sz,w):
    lines=[]
    for paragraph in str(s).split('\n'):
        words=paragraph.split(); acc=''
        for word in words:
            nxt=(acc+' '+word).strip()
            if acc and pdfmetrics.stringWidth(nxt,FONT_MAP.get(font,font),sz)>w:
                lines.append(acc);acc=word
            else:acc=nxt
        if acc: lines.append(acc)
    return lines

def para(c,s,x,y,maxw,sz=10,leading=15,co=DARK,font='Lato',maxlines=None):
    lines=wraps(s,font,sz,maxw)
    if maxlines is not None and len(lines)>maxlines:
        lines=lines[:maxlines]
        if lines: lines[-1]=(lines[-1][:max(0,len(lines[-1])-4)]+'...')
    for ln in lines:
        txt(c,ln,x,y,font,sz,co);y-=leading
    return y

def img(c,path,x,y,w,h):
    try:
        with Image.open(path) as p:
            p=ImageOps.exif_transpose(p).convert('RGB')
            pix=ImageOps.fit(p,(int(w*2),int(h*2)),method=Image.Resampling.LANCZOS,centering=(.5,.48))
            data=BytesIO();pix.save(data,format='JPEG',quality=83,optimize=True)
            data.seek(0)
            c.drawImage(ImageReader(data),x,y,width=w,height=h,mask='auto')
        return True
    except (OSError,ValueError):return False

def page(c,pn,section,synthetic):
    if pn>1:
        box(c,0,H-12,W,12,NAVY)
        txt(c,'PROPERTY CONDITION  /  RESIDENTIAL INSPECTION',M,H-44,'LatoB',8.6,NAVY)
        right(c,f'{section.upper()}  /  {pn:02}',W-M,H-44,'Lato',8.5,MUTED)
        line(c,M,H-56,W-M,H-56)
    line(c,M,50,W-M,50)
    txt(c,'OPTION 02  |  EDITORIAL REPORT STANDARD',M,33,'LatoB',7.5,MUTED)
    right(c,'ILLUSTRATIVE SAMPLE  •  NOT A FIELD INSPECTION' if synthetic else 'DRAFT  •  REVIEW REQUIRED',W-M,33,'Lato',7.5,MUTED)
    right(c,f'{pn:02}',W-M,66,'LatoB',8,NAVY)

def header(c,index,title,sub):
    txt(c,index.upper(),M,676,'LatoB',8.7,BRONZE)
    txt(c,title,M,633,'LatoL',30,NAVY)
    para(c,sub,M,605,CW,10,15,MUTED)

def label(c,s,x,y):txt(c,s.upper(),x,y,'LatoB',8.0,MUTED)

def datum(c,x,y,heading,value,w):
    label(c,heading,x,y)
    return para(c,value,x,y-20,w,11,16,DARK,'LatoB',maxlines=2)

def _ledger_lines(value, max_width, font='Lato', size=9):
    """Wrap every word, including unbroken model output; never ellipse ledger text."""
    out=[]
    for paragraph in str(value).split('\n'):
        if not paragraph.strip():
            out.append('')
            continue
        line=''
        for word in paragraph.split():
            while pdfmetrics.stringWidth(word,FONT_MAP[font],size)>max_width:
                # Split a single overlong token at the last fitting character.
                i=1
                while i<len(word) and pdfmetrics.stringWidth(word[:i+1],FONT_MAP[font],size)<=max_width:
                    i+=1
                if line:out.append(line);line=''
                out.append(word[:i]);word=word[i:]
            trial=(line+' '+word).strip()
            if line and pdfmetrics.stringWidth(trial,FONT_MAP[font],size)>max_width:
                out.append(line);line=word
            else:line=trial
        if line:out.append(line)
    return out


def _needs_complete_appendix(doc):
    """Enable full records for field cases and synthetic examples exceeding synopsis."""
    if not doc.get('property',{}).get('synthetic',False):
        return True
    findings=doc.get('findings',[])
    if len(findings)>1:return True
    if findings and (len(wraps(findings[0].get('condition',''),'Lato',10,CW-50))>4 or
                     len(wraps(findings[0].get('recommendation',''),'Lato',9.5,CW-50))>2):return True
    equip=doc.get('equipment',[])
    if len(equip)>4:return True
    observations=doc.get('observations',[])
    visible=('foundation','subfloor','framing','roof','exterior','interior')
    for system in visible:
        entries=[o for o in observations if o.get('system')==system]
        if len(entries)>1:return True
        if entries and len(wraps(entries[0].get('description',''),'Lato',9.6,218))>4:return True
    if any(o.get('system') not in visible for o in observations):return True
    limits=doc.get('limitations',[])
    if len(limits)>4:return True
    if any(len(wraps(x.get('description',''),'Lato',9.5,CW-35))>2 for x in limits):return True
    model_items=[x for key in ('findings','observations') for x in doc.get(key,[]) if x.get('model_proposal')]
    if any(len(wraps(x.get('description',x.get('condition','')),'Lato',9.1,CW-232))>9 for x in model_items):return True
    return False

def _full_record_appendix(c, doc, synthetic, next_page, *, include_source_evidence=False):
    """Lossless plain-language record ledger; pages expand with input rather than truncating.

    The photo-led five-page design is retained as a visual synopsis. Every source
    record appears in this separately paginated technical disclosure appendix.
    Neither editorial cards nor image previews are authoritative complete text.
    """
    groups=[]
    if include_source_evidence:
        # Enumerate every original and derived media object, including unassigned
        # footage. These pages disclose records; they do not imply visual review.
        for media in doc.get('media', []):
            fields=[(str(key).upper(), json.dumps(value, sort_keys=True,
                     ensure_ascii=True)) for key, value in sorted(media.items())]
            groups.append(('SOURCE EVIDENCE', str(media.get('id', 'unassigned')), fields))
        for zoom in doc.get('zoom_views', []):
            fields=[(str(key).upper(), json.dumps(value, sort_keys=True,
                     ensure_ascii=True)) for key, value in sorted(zoom.items())]
            groups.append(('NATIVE CROP RECORD', str(zoom.get('id', 'unassigned')), fields))
    for entry in doc.get('findings',[]):
        groups.append(('FINDING',str(entry.get('id','unassigned')),[
            ('SYSTEM',entry.get('system','unknown')),
            ('LOCATION',entry.get('location','unknown')),
            ('SEVERITY',entry.get('severity','not assigned')),
            ('CONDITION',entry.get('condition','')),
            ('RECOMMENDATION',entry.get('recommendation','')),
            ('EVIDENCE IDS',', '.join(map(str,entry.get('evidence_ids',[]))) or 'None'),
            ('REVIEW',entry.get('review','pending'))]))
    for entry in doc.get('observations',[]):
        groups.append(('PROPERTY FEATURE',str(entry.get('id','unassigned')),[
            ('SYSTEM',entry.get('system','unknown')),
            ('FEATURE',entry.get('feature','')),
            ('STATUS',entry.get('status','unknown')),
            ('DESCRIPTION',entry.get('description','')),
            ('EVIDENCE IDS',', '.join(map(str,entry.get('evidence_ids',[]))) or 'None'),
            ('REVIEW',entry.get('review','pending'))]))
    for entry in doc.get('equipment',[]):
        groups.append(('EQUIPMENT',str(entry.get('id','unassigned')),[
            ('SYSTEM',entry.get('system','unknown')),
            ('MANUFACTURER',entry.get('brand','Not recorded')),
            ('MODEL',entry.get('model','Not recorded')),
            ('SERIAL',entry.get('serial','Not recorded')),
            ('EVIDENCE IDS',', '.join(map(str,entry.get('evidence_ids',[]))) or 'None')]))
    for entry in doc.get('limitations',[]):
        groups.append(('LIMITATION',str(entry.get('id','unassigned')),[
            ('SYSTEM',entry.get('system','unknown')),
            ('DESCRIPTION',entry.get('description','')),
            ('EVIDENCE IDS',', '.join(map(str,entry.get('evidence_ids',[]))) or 'None')]))
    for status in coverage(doc):
        groups.append(('SYSTEM COVERAGE',str(status.get('system','unknown')),[
            ('SYSTEM',status.get('title',status.get('system','unknown'))),
            ('COVERAGE STATUS',status.get('status','not verified')),
            ('MISSING FEATURES',', '.join(map(str,status.get('missing_features',[]))) or 'None recorded')]))
    if not groups:return next_page

    page_no=next_page
    y=548
    def new_page():
        nonlocal page_no,y
        page(c,page_no,'complete record',synthetic)
        header(c,'APPENDIX / COMPLETE RECORD','Full inspection record',
             'Complete unabridged findings, property descriptions, equipment records, limitations and coverage status.')
        y=546
        page_no+=1

    new_page()
    for typ,item_id,fields in groups:
        # Keep each record visibly distinct; do not artificially clip long prose.
        if y<132:
            c.showPage();new_page()
        box(c,M,y-2,CW,1,BRONZE)
        y-=23
        heading=f'{typ}  /  {item_id}'
        for title_line in _ledger_lines(heading,CW-12,'LatoB',10):
            if y<109:
                c.showPage();new_page()
            txt(c,title_line,M+10,y,'LatoB',10,NAVY)
            y-=16
        for field,value in fields:
            if y<109:
                c.showPage();new_page()
                txt(c,f'{typ}  /  {item_id}  (CONTINUED)',M+10,y,'LatoB',9,NAVY)
                y-=19
            txt(c,str(field),M+12,y,'LatoB',8,MUTED)
            y-=15
            for body_line in _ledger_lines(value,CW-26,'Lato',9):
                if y<96:
                    c.showPage();new_page()
                    txt(c,f'{typ}  /  {item_id}  (CONTINUED)',M+10,y,'LatoB',9,NAVY)
                    y-=19
                txt(c,body_line,M+16,y,'Lato',9,DARK)
                y-=13
            y-=7
        y-=16
    c.showPage()
    return page_no

def build_pdf(document:dict,project_dir:Path,target:Path,*,include_evidence_register:bool=False):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    prop=document['property'];synthetic=bool(prop.get('synthetic'))
    photos=[]
    for m in document.get('media',[]):
        if m.get('kind')=='photo':
            try:
                p=safe_path(project_dir,m['path'])
                if p.is_file(): photos.append((p,m))
            except (OSError,ValueError):pass
    hero=photos[0] if photos else None
    c=cv.Canvas(str(target),pagesize=letter, pageCompression=1, invariant=1)
    c.setTitle('Residential Property Condition Report - Option 2 Editorial Draft')
    c.setAuthor('Inspection Engine - Design Demonstration')
    # page 1: cover
    box(c,0,H-15,W,15,NAVY)
    txt(c,'RESIDENTIAL  /  PROPERTY INSPECTION',M,H-64,'LatoB',9,NAVY)
    right(c,'REPORT  •  001',W-M,H-64,'Lato',8.7,MUTED)
    txt(c,'Property condition',M,H-128,'LatoL',33,NAVY)
    txt(c,'inspection report',M,H-167,'LatoL',33,NAVY)
    box(c,M,H-181,76,3,BRONZE)
    txt(c,prop.get('label','Residential property'),M,H-209,'Lato',12,MUTED)
    photo_y=197; photo_h=359
    if not hero or not img(c,hero[0],M,photo_y,CW,photo_h):
        box(c,M,photo_y,CW,photo_h,PALE)
        txt(c,'PROPERTY PHOTOGRAPH',M+25,photo_y+photo_h/2,'LatoB',11,MUTED)
        txt(c,'No property image supplied',M+25,photo_y+photo_h/2-23,'Lato',10,MUTED)
    box(c,M,photo_y,CW,49,NAVY)
    txt(c,'A CLEARER VIEW OF THE HOME',M+19,photo_y+30,'LatoB',10,WHITE)
    txt(c,'Property features  /  Condition notes  /  Visual evidence',M+19,photo_y+12,'Lato',8.3,'#DBE5EB')
    label(c,'INSPECTION DATE',M,164)
    txt(c,prop.get('inspection_date','Not recorded'),M,145,'LatoB',10,NAVY)
    label(c,'PREPARED FOR',M+186,164)
    txt(c,'Design review / demonstration',M+186,145,'LatoB',10,NAVY)
    label(c,'STATUS',M+398,164)
    txt(c,'NOT RELEASED',M+398,145,'LatoB',10,NAVY)
    txt(c,'Visual style: original, spacious, photography-led editorial design',M,98,'Lato',9,MUTED)
    page(c,1,'cover',synthetic)
    c.showPage()
    # page 2: overview
    page(c,2,'overview',synthetic)
    header(c,'01 / Executive overview','An informed first look','An easy-to-read summary of what was documented, what still needs confirmation, and the scope of the review.')
    box(c,M,390,244,175,PALE)
    txt(c,'THE PROPERTY AT A GLANCE',M+16,537,'LatoB',9,NAVY)
    para(c,'The report records property characteristics even when no defect has been identified. Unseen or unverified elements remain clearly marked rather than guessed.',M+16,506,212,10.2,16,DARK)
    txt(c,'RECORDED FINDINGS',M+16,422,'LatoB',8,MUTED)
    txt(c,str(len(document.get('findings',[]))),M+16,395,'LatoL',26,NAVY)
    txt(c,'OPEN REVIEW GATES',M+126,422,'LatoB',8,MUTED)
    txt(c,str(len(blockers(document))),M+126,395,'LatoL',26,NAVY)
    if hero:img(c,hero[0],M+258,390,258,175)
    else:box(c,M+258,390,258,175,LIGHT)
    txt(c,'WHAT THIS REPORT DOES',M,357,'LatoB',11,NAVY)
    line(c,M,345,W-M,345)
    summary=[('01','Documented features','Construction, building support, exterior envelope and equipment.'),('02','Condition observations','Traceable findings and recommendations where evidence supports them.'),('03','Unverified details','Clear gaps for structures, equipment labels, inaccessible areas and systems.')]
    for i,(num,name,desc) in enumerate(summary):
        y=316-79*i
        txt(c,num,M,y,'LatoB',11,BRONZE)
        txt(c,name,M+37,y,'LatoB',11,NAVY)
        para(c,desc,M+37,y-19,CW-37,10,15,MUTED,maxlines=2)
        line(c,M,y-58,W-M,y-58)
    box(c,M,79,CW,40,SAND)
    txt(c,'SCOPE NOTE',M+15,103,'LatoB',8,BRONZE)
    txt(c,'Photos alone do not establish that every component was inspected.',M+101,103,'Lato',9.2,NAVY)
    c.showPage()
    # page 3: house description
    page(c,3,'construction',synthetic)
    header(c,'02 / Property profile','How the home is built','The baseline matters. A complete report describes major structural and building features - not just problems.')
    focus=[('FOUNDATION', 'foundation'),('FLOOR PLATFORM / SUBFLOOR','subfloor'),('STRUCTURAL FRAMING','framing'),('ROOF ASSEMBLY','roof'),('EXTERIOR ENCLOSURE','exterior'),('INTERIOR FINISHES','interior')]
    obs=document.get('observations',[])
    for i,(heading,system) in enumerate(focus):
        x=M+(i%2)*266; top=547-(i//2)*153
        box(c,x,top-129,250,126,PALE if i%2==0 else SAND)
        txt(c,f'{i+1:02}',x+15,top-23,'LatoB',9,BRONZE)
        txt(c,heading,x+47,top-23,'LatoB',9.2,NAVY)
        entries=[o for o in obs if o.get('system')==system]
        if entries:
            for o in entries[:1]:
                st=o.get('status','unknown').replace('_',' ').upper()
                txt(c,st,x+15,top-48,'LatoB',8,MUTED)
                para(c,o.get('description','Not documented'),x+15,top-67,218,9.6,14,DARK,maxlines=4)
        else:
            txt(c,'NOT DOCUMENTED',x+15,top-48,'LatoB',8,MUTED)
            para(c,'Further observation needed before a reliable description can be made.',x+15,top-67,218,9.6,14,DARK,maxlines=4)
    txt(c,'Illustrative property data is clearly distinguished from verified field observations.',M,94,'Lato',9,MUTED)
    c.showPage()
    # page 4: systems and equipment
    page(c,4,'systems',synthetic)
    header(c,'03 / Mechanical systems','Equipment & major systems','Names, model numbers and manufacturing dates belong in a clear evidence-backed equipment record.')
    cols=[M,M+113,M+223,M+343];y=546
    for lab,x in zip(['SYSTEM','MANUFACTURER','MODEL / SERIAL','MFG DATE'],cols): label(c,lab,x,y)
    line(c,M,y-13,W-M,y-13,NAVY,1.2)
    for e in document.get('equipment',[])[:4]:
        y-=75
        info=research_equipment(e.get('brand',''),e.get('serial',''),prop.get('inspection_date','2026-10-30'))
        txt(c,e.get('system','').replace('_',' ').title()[:17],cols[0],y,'LatoB',10,NAVY)
        para(c,e.get('brand','Not recorded'),cols[1],y,102,9.2,13,DARK,maxlines=2)
        para(c,(e.get('model','')+' / '+e.get('serial','')).strip(' /'),cols[2],y,111,8.6,12,DARK,maxlines=3)
        date=info.get('manufacturer_date') or 'Unverified'
        if info.get('candidates') and len(info['candidates'])>1:date='Ambiguous code'
        para(c,date,cols[3],y,164,9,13,NAVY,maxlines=2)
        line(c,M,y-51,W-M,y-51)
    # A separate band beneath the equipment rows prevents overlapping content.
    box(c,M,197,CW,95,PALE)
    txt(c,'DATE INTERPRETATION',M+16,270,'LatoB',9,NAVY)
    para(c,'A manufacturing date is not an installation date. A serial number must match the correct manufacturer and date-code era, then be checked against the equipment label or manufacturer records.',M+16,248,CW-32,9.8,14,DARK,maxlines=4)
    txt(c,'DOCUMENTED COVERAGE',M,176,'LatoB',10,NAVY)
    line(c,M,165,W-M,165)
    systems=coverage(document)
    for i,s in enumerate(systems[:8]):
        x=M if i<4 else M+264; yy=149-(i%4)*20
        txt(c,s.get('title',str(s.get('system','system')))[:27],x,yy,'Lato',9,DARK)
        right(c,s.get('status','unknown').replace('_',' ')[:18],x+239,yy,'LatoB',8.3,MUTED)
    c.showPage()
    # page 5: findings, process and limitations
    page(c,5,'observations',synthetic)
    header(c,'04 / Observations','Condition & next steps','Findings are documented alongside the applicable evidence, limitations and professional recommendations.')
    f=document.get('findings',[])
    if f:
        item=f[0]
        box(c,M,376,CW,183,PALE)
        box(c,M,376,5,183,BRONZE)
        txt(c,'ILLUSTRATIVE CONDITION NOTE  /  '+item.get('id','F01'),M+22,533,'LatoB',8.5,BRONZE)
        txt(c,item.get('system','').replace('_',' ').title()+'  /  '+item.get('location','Not recorded'),M+22,506,'LatoB',13,NAVY)
        para(c,item.get('condition',''),M+22,477,CW-50,10,15,DARK,maxlines=4)
        txt(c,'RECOMMENDED FOLLOW-UP',M+22,414,'LatoB',8.5,MUTED)
        para(c,item.get('recommendation',''),M+22,396,CW-50,9.5,14,DARK,maxlines=2)
    txt(c,'LIMITATIONS & UNVERIFIED AREAS',M,345,'LatoB',11,NAVY)
    line(c,M,334,W-M,334)
    y=311
    for n,lim in enumerate(document.get('limitations',[])[:4]):
        txt(c,f'{n+1:02}',M,y,'LatoB',9,BRONZE)
        y2=para(c,lim.get('description','Not specified'),M+35,y,CW-35,9.5,14,DARK,maxlines=2)
        y=min(y-53,y2-17)
    box(c,M,99,CW,89,NAVY)
    txt(c,'RELEASE & PROFESSIONAL REVIEW',M+18,161,'LatoB',9,'#DCE9F0')
    para(c,'This is a design demonstration. Inspector verification, original field photographs, full system coverage and final sign-off have not been established.',M+18,139,CW-36,9.5,15,WHITE,maxlines=3)
    c.showPage()
    # Photo/video interpretation appendix. Unlike the five-page overview, every
    # provisional model item receives an individually evidence-linked entry.
    model_items = ([('feature', item) for item in document.get('observations',[])
                    if item.get('model_proposal')]
                   +[('concern', item) for item in document.get('findings',[])
                     if item.get('model_proposal')])
    evidence={item['id']:item for item in document.get('media',[])}
    zoom_evidence={item['id']:item for item in document.get('zoom_views',[])}
    for offset in range(0,len(model_items),2):
        pn=6+offset//2
        page(c,pn,'evidence review',synthetic)
        header(c,'APPENDIX / '+str(pn-5).zfill(2),'Visual evidence review',
               'Provisional notes matched to source images. These are not confirmed conditions or verified inspection results.')
        for slot,(kind,item) in enumerate(model_items[offset:offset+2]):
            top=555-slot*240
            box(c,M,top-218,CW,218,PALE if slot==0 else SAND)
            box(c,M,top-218,4,218,BRONZE)
            ref_ids=item.get('evidence_ids',[])
            medi=evidence.get(ref_ids[0],{}) if ref_ids else {}
            media_path=None
            try:
                if medi.get('kind')=='photo':media_path=safe_path(project_dir,medi.get('path'))
            except (OSError,ValueError):pass
            zoom_ref=(item.get('zoom_view_ids') or [None])[0]
            zoom=zoom_evidence.get(zoom_ref) if zoom_ref else None
            detail_path=None
            if zoom:
                try:
                    detail_path=safe_path(project_dir,zoom['path'])
                except (OSError,ValueError):pass
            if detail_path and media_path:
                # Keep source context adjacent to close-up, not a free-floating crop.
                ok_context=img(c,media_path,M+12,top-159,88,141)
                ok_detail=img(c,detail_path,M+109,top-159,88,141)
                if ok_context and ok_detail:
                    txt(c,'CONTEXT',M+13,top-172,'LatoB',7.3,MUTED)
                    txt(c,'NATIVE DETAIL',M+110,top-172,'LatoB',7.3,MUTED)
                else:
                    box(c,M+12,top-170,185,154,LIGHT)
                    txt(c,'IMAGE UNAVAILABLE',M+25,top-86,'LatoB',9,MUTED)
            elif media_path:
                if not img(c,media_path,M+12,top-170,185,154):
                    box(c,M+12,top-170,185,154,LIGHT)
                    txt(c,'IMAGE UNAVAILABLE',M+25,top-86,'LatoB',9,MUTED)
            else:
                box(c,M+12,top-170,185,154,LIGHT)
                txt(c,'IMAGE UNAVAILABLE',M+25,top-86,'LatoB',9,MUTED)
            x=M+212;wid=CW-232
            txt(c,('VISIBLE FEATURE' if kind=='feature' else 'POTENTIAL CONCERN')+
                '  /  '+str(item.get('id','')),x,top-25,'LatoB',9,BRONZE)
            system=item.get('system','').replace('_',' ').title()
            para(c,system+'  •  '+str(item.get('location','Unspecified')),x,top-47,wid,10,13,NAVY,'LatoB',maxlines=2)
            statement=item.get('description',item.get('condition',''))
            para(c,statement,x,top-78,wid,9.1,12.8,DARK,maxlines=9)
            stamp=' / '.join(ref_ids[:3])
            if medi.get('derived_from_id'):
                stamp+=f"  •  Video {medi['derived_from_id']} at {medi.get('timestamp_seconds',0):.2f}s"
            if zoom:
                stamp+=f"  /  ZOOM {zoom['id']} ~{zoom['linear_zoom_equivalent']:g}x SOURCE PIXELS"
            para(c,'SOURCE  '+stamp,M+15,top-189,CW-28,8.2,11,MUTED,maxlines=2)
            txt(c,'NOT REVIEWED OR APPROVED',x,top-164,'LatoB',8.3,BRONZE)
        c.showPage()
    # Selected full-resolution video stills are report-worthy photographic
    # evidence, not just transient sampling frames. A dedicated gallery keeps
    # the source video ID and capture time prominent and avoids misleading the
    # reader into thinking the image was captured as an independent camera shot.
    selected=[m for m in document.get('media',[])
              if m.get('capture_origin')=='selected_video_still']
    preceding=5+(len(model_items)+1)//2
    for offset in range(0,len(selected),2):
        pn=preceding+1+offset//2
        page(c,pn,'video photographs',synthetic)
        header(c,'PHOTO APPENDIX / '+str(offset//2+1).zfill(2),
               'Photographs from video',
               'Selected full-frame photographs captured from the original inspection video. Each is traceable to the source recording.')
        for slot,m in enumerate(selected[offset:offset+2]):
            top=551-slot*245
            box(c,M,top-217,CW,217,PALE if slot==0 else SAND)
            box(c,M,top-217,4,217,BRONZE)
            path=None
            try:path=safe_path(project_dir,m['path'])
            except (ValueError,OSError):pass
            if path and img(c,path,M+12,top-169,253,154):
                pass
            else:
                box(c,M+12,top-169,253,154,LIGHT)
                txt(c,'PHOTO UNAVAILABLE',M+24,top-94,'LatoB',9,MUTED)
            x=M+281
            txt(c,'VIDEO-DERIVED PHOTOGRAPH  /  '+m['id'],x,top-25,'LatoB',8.2,BRONZE)
            para(c,m.get('area','').replace('_',' ').title(),x,top-52,215,13,17,NAVY,'LatoB',maxlines=2)
            label(c,'SOURCE VIDEO',x,top-93)
            txt(c,str(m.get('derived_from_id','Unknown')),x,top-110,'LatoB',10,DARK)
            label(c,'EXACT FRAME TIME',x,top-135)
            txt(c,f"{m.get('timestamp_seconds',0):.3f} seconds",x,top-152,'LatoB',10,NAVY)
            dims=m.get('native_frame_size',['?','?'])
            txt(c,f"{dims[0]} x {dims[1]} native px / no AI enlargement",M+13,top-194,'Lato',8.5,MUTED)
            txt(c,'UNREVIEWED SOURCE EVIDENCE',x,top-194,'LatoB',8.1,BRONZE)
        c.showPage()
    # M4 private-only photo gallery: every original standalone photo gets a
    # labeled evidence page even when no model claim was assigned to it.
    # Other renderer entry points retain their approved five-page synopsis.
    gallery=[m for m in document.get('media',[])
             if m.get('kind')=='photo' and m.get('capture_origin')!='selected_video_still'] if include_evidence_register else []
    first_gallery_page=preceding+1+(len(selected)+1)//2
    for offset in range(0,len(gallery),2):
        pn=first_gallery_page+offset//2
        page(c,pn,'original photography',synthetic)
        header(c,'PHOTO APPENDIX / '+str(offset//2+1).zfill(2),
               'Original source photographs',
               'Unreviewed and provisional evidence photographs. The source registry provides full provenance and original hashes.')
        for slot,m in enumerate(gallery[offset:offset+2]):
            top=549-slot*240
            box(c,M,top-216,CW,216,PALE if slot==0 else SAND)
            box(c,M,top-216,4,216,BRONZE)
            try:
                original=safe_path(project_dir,m.get('path',''))
                if not img(c,original,M+12,top-171,250,158):
                    raise OSError('image could not be drawn')
            except (OSError,ValueError):
                box(c,M+12,top-171,250,158,LIGHT)
                txt(c,'IMAGE UNAVAILABLE',M+22,top-93,'LatoB',9,MUTED)
            x=M+275
            txt(c,'ORIGINAL PHOTO / '+str(m.get('id','')),x,top-26,'LatoB',9,BRONZE)
            para(c,str(m.get('area','unknown')).replace('_',' ').title(),
                 x,top-54,215,11.5,15,NAVY,'LatoB',maxlines=2)
            para(c,m.get('caption','No caption supplied'),x,top-89,212,9.0,12.5,DARK,
                 maxlines=3)
            para(c,'SHA256 '+str(m.get('sha256','UNHASHED'))[:18]+'...',x,top-156,214,
                 8.2,10,MUTED,maxlines=2)
            txt(c,'NOT CERTIFIED / NOT RELEASED',x,top-194,'LatoB',8.1,BRONZE)
        c.showPage()
    # Mandatory complete ledger. The fixed editorial synopsis may use preview
    # ellipses; the exhaustive ledger below never truncates supplied records.
    if include_evidence_register or _needs_complete_appendix(document):
        _full_record_appendix(c,document,synthetic,
                              first_gallery_page+(len(gallery)+1)//2,
                              include_source_evidence=include_evidence_register)
    c.save()
    return target
