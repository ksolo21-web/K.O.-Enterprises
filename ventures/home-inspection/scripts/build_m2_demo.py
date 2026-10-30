"""Synthetic-only demonstration of source-pixel zoom into approved Option 2 report.

No computer vision model is invoked. Candidate text is a developer-authored fixture.
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from inspection_engine.core import load_project
from inspection_engine.zoom import create_zoom_views
from inspection_engine.vision import analyze_zoom_views,apply_predictions
from inspection_engine.report import build_pdf

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples'/'m1'
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)

def save(filename,object):
    Path(filename).write_text(json.dumps(object,indent=2)+'\n',encoding='utf8')

def main():
    doc=load_project(EX/'04_provisional_project.json')
    # Existing synthetic photo P0001 already registered with immutable SHA-256.
    # The first region covers roof/upper facade, then a tighter eave detail.
    regions=[[.17,.07,.82,.48],[.46,.21,.68,.41]]
    views=create_zoom_views(doc,EX,'P0001',regions,'roof-specialist',
                   'Review small roof details in the original synthetic image')
    save(EX/'05_native_zoom_project.json',doc)
    counter=iter(['roof','eave'])
    def fixture_provider(image,prompt):
        kind=next(counter)
        if kind=='roof':
            return {'candidates':[{'type':'feature','system':'roof','feature_code':'roof_covering',
                'description':'The illustrative close-up depicts dark overlapping roof-like bands. Actual roof covering and its condition are unverified.',
                'status':'partially_observed','location':'illustrated upper front elevation',
                'bbox':[.12,.10,.88,.80]}]}
        return {'candidates':[{'type':'potential_concern','system':'roof',
            'description':'A narrow dark line is visible in this illustration. This cannot establish a crack, separation, or defect at a real property.',
            'status':'partially_observed','location':'illustrated roof edge',
            'bbox':[.24,.3,.71,.67]}]}
    p=analyze_zoom_views(doc,EX,[x['id'] for x in views],fixture_provider,
                         'SYNTHETIC_MANUALLY_SCRIPTED_ZOOM_NOT_ACTUAL_AI')
    save(EX/'06_synthetic_zoom_predictions.json',p)
    applied=apply_predictions(doc,EX,p)
    save(EX/'07_zoom_review_project.json',applied)
    dest=OUT/'m2_option2_native_zoom_editorial.pdf'
    build_pdf(applied,EX,dest)
    # Side-by-side visual proof: no imported photo used for model performance claims.
    photo=next(x for x in doc['media'] if x['id']=='P0001')
    im=ImageOps.exif_transpose(Image.open(EX/photo['path'])).convert('RGB')
    w,h=1600,975
    canvas=Image.new('RGB',(w,h),'#eff2f4')
    d=ImageDraw.Draw(canvas)
    def font(size,bold=False):
        file=('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        return ImageFont.truetype(file,size)
    navy='#152f43'
    d.rectangle((0,0,w,115),fill=navy)
    d.text((55,30),'SOURCE PIXELS  /  SPECIALIST ZOOM',fill='#ffffff',font=font(31,True))
    d.text((55,75),'Synthetic image • no real property inspected • no live vision model used',
           fill='#cadbe5',font=font(16))
    original=im.copy();original.thumbnail((920,710))
    canvas.paste(original,(44,165))
    xscale=original.width/im.width;yscale=original.height/im.height
    for i,z in enumerate(views):
        box=z['pixel_bbox']
        d.rectangle((44+round(box[0]*xscale),165+round(box[1]*yscale),
                     44+round(box[2]*xscale),165+round(box[3]*yscale)),
                    outline=['#e8a54e','#2a8bb5'][i],width=5)
    d.text((48,132),'ORIGINAL IMAGE  /  1536 × 1024 pixels',fill=navy,font=font(17,True))
    d.text((47,915),'Colored rectangles locate the exact original areas.',fill='#455769',font=font(17))
    for i,z in enumerate(views):
        x=1045; y=159+i*380
        d.rectangle((x-14,y-14,1574,y+344),fill='white')
        with Image.open(EX/z['path']) as cimg:
            crop=cimg.copy()
        crop.thumbnail((500,264))
        canvas.paste(crop,(x,y+30))
        d.text((x,y),f'{z["id"]}  •  native {z["linear_zoom_equivalent"]}×',fill=navy,font=font(19,True))
        d.text((x,y+304),f'Actual crop: {z["crop_native_size"][0]} × {z["crop_native_size"][1]} source pixels',fill='#455769',font=font(15))
    canvas.save(OUT/'m2_zoom_overview.png')
    audit={'source_image':photo['id'],'views':[{'id':z['id'],'pixel_bbox':z['pixel_bbox'],
        'native_size':z['native_source_size'],'crop_size':z['crop_native_size'],
        'linear_zoom_equivalent':z['linear_zoom_equivalent'],
        'source_sha256':z['source_sha256'],'crop_sha256':z['sha256']} for z in views],
        'provider':'SCRIPTED DEMONSTRATION - NO MODEL',
        'report':str(dest.relative_to(ROOT)),'number_of_unverified_zoom_candidates':2,
        'review':'PENDING; NO PRODUCTION RELEASE'}
    save(OUT/'m2_zoom_demo_manifest.json',audit)
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
