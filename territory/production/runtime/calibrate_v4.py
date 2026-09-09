"""Structured scan calibration. Retains all v3 images and adds a new holdout.
Synthetic qualification is never permission to release a real territory card.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from calibrate import fixtures
from neural import infer, model_identity

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'top_edge': {'type': 'string', 'enum': ['continuous', 'white_gap', 'uncertain']},
        'right_edge': {'type': 'string', 'enum': ['continuous', 'white_gap', 'uncertain']},
        'bottom_edge': {'type': 'string', 'enum': ['continuous', 'white_gap', 'uncertain']},
        'left_edge': {'type': 'string', 'enum': ['continuous', 'white_gap', 'uncertain']},
        'label_collision': {'type': 'boolean'},
        'observation': {'type': 'string'},
    },
    'required': ['top_edge', 'right_edge', 'bottom_edge', 'left_edge', 'label_collision', 'observation'],
}
PROMPT = (
    'Read-only inspection of the supplied map pixels. There are two dark street names inside a green road loop. '
    'Inspect EACH of its four edges separately: top, right, bottom, left. For each edge report continuous when '
    'the green stroke is uninterrupted, white_gap when a white cut severs that stroke, or uncertain when you '
    'cannot determine it. Check the LEFT vertical edge as carefully as the other three; do not infer it from '
    'the top edge. Rounded corners are normal. Separately report label_collision true only if letters from '
    'the TWO DIFFERENT street names touch or overlap each other; overlapping bounding boxes alone are not '
    'a collision. Give one short observation describing actual visible evidence. Do not infer answers from '
    'filenames or from how often another answer occurred.'
)
EDGES = ('top_edge', 'right_edge', 'bottom_edge', 'left_edge')

def holdouts(folder: Path):
    font_path = next(p for p in (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                               Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')) if p.exists())
    out = []
    for i, (overlap, edge) in enumerate([(False, None), (True, 'bottom'), (False, 'right'), (True, None)]):
        im = Image.new('RGB', (672,448), 'white'); d = ImageDraw.Draw(im)
        x0,y0,x1,y1 = 64,62,605,384
        d.rounded_rectangle((x0,y0,x1,y1), radius=24, outline=(35,145,75), width=8)
        if edge == 'bottom': d.rectangle((409,y1-12,447,y1+4), fill='white')
        if edge == 'right': d.rectangle((x1-12,199,x1+4,238), fill='white')
        font = ImageFont.truetype(str(font_path), 34)
        d.text((151,148), 'Aspen Drive', font=font, fill=(28,28,28))
        d.text((188 if overlap else 151,159 if overlap else 236), 'Birch Avenue', font=font, fill=(28,28,28))
        name=hashlib.sha256(('v4-new-holdout-'+str(i)).encode()).hexdigest()[:16]
        path=folder/(name+'.png'); im.save(path)
        out.append({'file':path,'id':name,'split':'new_holdout',
                    'expected':{'label_collision':overlap,'broken_road':edge is not None}})
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    folder=args.out.parent/'v4-images'; cases=fixtures(folder)
    for c in cases: c['split']='retained_v3_regression'
    cases+=holdouts(folder)
    identity=model_identity(); records=[]
    report={'schema_version':4,'source_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
            'model_identity':identity,'program_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'required':len(cases),'cases':records,'real_card_qualification':False,'release_authorized':False}
    for case in cases:
        rec={'id':case['id'],'split':case['split'],'expected':case['expected'],
             'image_sha256':hashlib.sha256(case['file'].read_bytes()).hexdigest(),'passed':False}
        try:
            receipt=infer([case['file']],PROMPT,SCHEMA,identity=identity,max_tokens=320)
            result=receipt['result']; uncertain=any(result[e]=='uncertain' for e in EDGES)
            rec.update(receipt=receipt, interpreted={'label_collision':result['label_collision'],
                        'broken_road':any(result[e]=='white_gap' for e in EDGES)}, uncertain=uncertain)
            rec['passed']=not uncertain and rec['interpreted']==case['expected']
        except Exception as error: rec['error']=type(error).__name__+': '+str(error)
        records.append(rec)
        report.update(completed=len(records), passed=sum(x['passed'] for x in records),
                      synthetic_calibration_passed=len(records)==len(cases) and all(x['passed'] for x in records))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'id':rec['id'],'passed':rec['passed'],'error':rec.get('error')}),flush=True)
    return 0 if report['synthetic_calibration_passed'] else 2

if __name__=='__main__': raise SystemExit(main())
