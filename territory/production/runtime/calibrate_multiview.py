"""Read-only multi-view critic calibration. Synthetic success is not card approval."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from calibrate import fixtures, SCHEMA
from neural import infer, model_identity

PROMPT = ('Inspect this evidence sheet. The upper image is the whole map. '
          'The next image is a close-up of its street names. The four lower strips '
          'show ALL FOUR sides of the green road loop; vertical sides were rotated '
          'to read horizontally. A white interruption INSIDE any green strip is a '
          'broken road; the normal ends of a crop are not breaks. Check EVERY strip. '
          'label_collision means that letters belonging to DIFFERENT street names '
          'touch or overlap. Look at the enlarged names, not the caption text. '
          'Judge both checks independently; do not assume that a sample is damaged. '
          'Describe actual visible evidence in observation, at most 30 words.')

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def evidence_sheet(path: Path, output: Path) -> dict:
    """Use the same content-independent crop method on positive and negative cases."""
    with Image.open(path) as opened:
        image = opened.convert('RGB')
    pixels = image.load()
    points = [(x,y) for y in range(image.height) for x in range(image.width)
              if pixels[x,y][1] > pixels[x,y][0]+30 and pixels[x,y][1] > pixels[x,y][2]+25]
    if not points:
        raise ValueError('No reviewable green drawing')
    xs,ys=zip(*points); left,top,right,bottom=min(xs),min(ys),max(xs)+1,max(ys)+1
    padding=16
    boxes=[(left-4,top-8,right+4,top+padding),
           (left-4,bottom-padding,right+4,bottom+8),
           (left-8,top+28,left+padding,bottom-28),
           (right-padding,top+28,right+8,bottom-28)]
    sheet=Image.new('RGB',(704,800),'white'); draw=ImageDraw.Draw(sheet)
    font=ImageFont.load_default(size=15)
    thumb=image.copy();thumb.thumbnail((500,310))
    sheet.paste(thumb,((704-thumb.width)//2,22))
    draw.text((12,3),'Whole map',fill='black',font=font)
    names=image.crop((left+50,top+45,right-40,bottom-45));names.thumbnail((650,195))
    draw.text((12,336),'Street-name close-up',fill='black',font=font)
    sheet.paste(names,((704-names.width)//2,358))
    provenance=[]
    for i,box in enumerate(boxes):
        crop=image.crop(box)
        if i>=2:crop=crop.transpose(Image.Transpose.ROTATE_90)
        ratio=min(640/crop.width,40/crop.height)
        crop=crop.resize((round(crop.width*ratio),round(crop.height*ratio)),Image.Resampling.NEAREST)
        y=560+i*58
        draw.text((12,y-16),('Top','Bottom','Left (rotated)','Right (rotated)')[i],fill='black',font=font)
        sheet.paste(crop,((704-crop.width)//2,y))
        provenance.append({'box':box,'rotation_degrees':90 if i>=2 else 0})
    output.parent.mkdir(parents=True,exist_ok=True);sheet.save(output)
    return {'source_sha256':digest(path),'sheet_sha256':digest(output),'crops':provenance}

def new_cases(folder: Path) -> list[dict]:
    """Newly authored holdouts; answers are kept out of the model prompt and image names."""
    folder.mkdir(parents=True,exist_ok=True)
    font_path=next(p for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                              Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')] if p.exists())
    result=[]
    for i in range(8):
        overlap=bool(i&1);broken=bool(i&2);variant=i//4
        image=Image.new('RGB',(672,448),'white');d=ImageDraw.Draw(image)
        box=(64,60,608,392);d.rounded_rectangle(box,radius=24,outline=(35,145,75),width=8)
        if broken:
            if variant==0:d.rectangle((382,380,419,398),fill='white')
            else:d.rectangle((598,172,615,207),fill='white')
        font=ImageFont.truetype(str(font_path),32)
        d.text((134,146),'Birch Drive' if variant==0 else 'Aspen Lane',font=font,fill=(28,28,28))
        d.text((170 if overlap else 134,157 if overlap else 226),'Spruce Road' if variant==0 else 'Elm Court',font=font,fill=(28,28,28))
        key=hashlib.sha256(f'multiview-heldout-20260909-{i}'.encode()).hexdigest()[:16]
        p=folder/(key+'.png');image.save(p)
        result.append({'id':key,'file':p,'expected':{'label_collision':overlap,'broken_road':broken},'split':'new_holdout'})
    return result

def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--split',choices=['regression','new_holdout'],default='regression')
    parser.add_argument('--fixtures-only',action='store_true');args=parser.parse_args()
    folder=args.out.parent/('multiview-'+args.split)
    cases=fixtures(folder) if args.split=='regression' else new_cases(folder)
    for case in cases:
        case['split']=args.split
        case['sheet']=folder/(case['id']+'-views.png')
        case['view_provenance']=evidence_sheet(case['file'],case['sheet'])
    if args.fixtures_only:
        print(json.dumps([{'id':c['id'],'sheet':str(c['sheet'])} for c in cases]));return 0
    identity=model_identity();records=[]
    for case in cases:
        record={k:case[k] for k in ['id','split','expected','view_provenance']}
        try:
            receipt=infer([case['sheet']],PROMPT,SCHEMA,identity=identity,max_tokens=256)
            record.update(receipt=receipt,passed=all(receipt['result'][k] is v for k,v in case['expected'].items()))
        except Exception as error:
            record.update(passed=False,error=type(error).__name__+': '+str(error))
        records.append(record)
        report={'schema_version':4,'source_commit':os.environ.get('GITHUB_SHA'),
                'run_id':os.environ.get('GITHUB_RUN_ID'),'split':args.split,'model_identity':identity,
                'program_sha256':digest(Path(__file__)),'completed':len(records),'required':len(cases),
                'passed':sum(r['passed'] for r in records),'cases':records,
                'synthetic_calibration_passed':len(records)==len(cases) and all(r['passed'] for r in records),
                'real_card_qualification':False,'release_authorized':False}
        args.out.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.out.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(args.out)
        print(json.dumps({'id':case['id'],'passed':record['passed']}),flush=True)
    return 0 if report['synthetic_calibration_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
