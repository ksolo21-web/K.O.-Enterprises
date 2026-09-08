"""Repeat the retained blind smoke with full-page and close-up evidence.
The original failed fixtures and expected labels are not altered.
This still does not certify real territory-card quality.
"""
import base64
import hashlib
import io
import json
import os
import jsonschema
from PIL import Image
from vision_smoke import fixture, request, MODEL

DIGEST='fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1'
SCHEMA={'type':'object','properties':{
    'observations':{'type':'array','items':{'type':'string'}},
    'label_overlap':{'type':'boolean'},'road_gap':{'type':'boolean'}},
    'required':['observations','label_overlap','road_gap'],'additionalProperties':False}

def png(image):
    output=io.BytesIO();image.save(output,format='PNG');return output.getvalue()

def main():
    if os.environ.get('OLLAMA_NO_CLOUD')!='1':raise RuntimeError('Cloud disabled is required')
    entry=next((m for m in request('/api/tags',timeout=10)['models'] if m.get('name')==MODEL),None)
    if not entry or entry['digest'].removeprefix('sha256:')!=DIGEST:raise RuntimeError('Model identity changed')
    results=[]
    # Fixed crop locations and same processing for every case: no expected-answer hints.
    for broken in (False,True):
        image=fixture(broken)
        views=[image,image.crop((120,65,530,185)).resize((820,240),Image.Resampling.NEAREST),
               image.crop((120,215,530,325)).resize((820,220),Image.Resampling.NEAREST)]
        raw_views=[png(view) for view in views]
        payload={'model':MODEL,'stream':False,'format':SCHEMA,
                 'options':{'temperature':0,'num_ctx':8192,'num_predict':300},
                 'messages':[{'role':'user','content':
                   'Inspect the three actual images: one complete diagram, then its upper and lower close-ups. '
                   'First describe the black text arrangement and each colored horizontal line as observed. '
                   'Then decide whether distinct black road-name labels overlap in the same space, and whether '
                   'the green horizontal line is continuous or interrupted by a white gap. '
                   'A gap means a visible break in the line, not the vertical distance to the red line. '
                   'Do not assume clean or defective. Base each answer on visible pixels. Return only the schema.',
                   'images':[base64.b64encode(raw).decode() for raw in raw_views]}]}
        envelope=request('/api/chat',payload,timeout=360)
        if not envelope.get('done'):raise RuntimeError('Incomplete inference')
        answer=json.loads(envelope['message']['content']);jsonschema.validate(answer,SCHEMA)
        matched=answer['label_overlap'] is broken and answer['road_gap'] is broken
        results.append({'fixture_sha256':hashlib.sha256(raw_views[0]).hexdigest(),
                        'views_sha256':[hashlib.sha256(raw).hexdigest() for raw in raw_views],
                        'expected':{'label_overlap':broken,'road_gap':broken},
                        'actual':answer,'matched':matched,'raw_response':envelope})
        print(json.dumps(results[-1],indent=2),flush=True)
    count=sum(case['matched'] for case in results)
    report={'model':MODEL,'model_digest':DIGEST,'cases':results,'matched_cases':count,
            'territory_release_approved':False,'status':'synthetic_closeup_smoke_only'}
    print(json.dumps(report,indent=2),flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as stream:
            stream.write(f'## Local vision with close-ups\n{count}/2 retained cases matched. No real territory approved.\n')
    return 0 if count==2 else 2

if __name__=='__main__':raise SystemExit(main())
