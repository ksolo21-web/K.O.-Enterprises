"""Synthetic, secret-free smoke test of a real local vision model on a public runner.
This is not calibration or approval for real territory-card production.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request
from PIL import Image, ImageDraw, ImageFont

MODEL='qwen2.5vl:3b'
SCHEMA={'type':'object','properties':{
    'label_overlap':{'type':'boolean'},'road_gap':{'type':'boolean'},
    'observations':{'type':'array','items':{'type':'string'}}},
    'required':['label_overlap','road_gap','observations'],'additionalProperties':False}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('Loopback redirect is forbidden')

def request(endpoint,payload=None,timeout=240):
    url='http://127.0.0.1:11434'+endpoint
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=timeout) as response:
        raw=response.read(1000001)
    if len(raw)>1000000:raise RuntimeError('Oversized model response')
    return json.loads(raw)

def fixture(broken):
    image=Image.new('RGB',(640,400),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=24)
    draw.text((18,12),'SYNTHETIC TEST - NOT A TERRITORY',fill='black',font=ImageFont.load_default(size=18))
    draw.line((50,160,590,160),fill='green',width=8)
    draw.line((50,300,590,300),fill='red',width=8)
    if broken:
        draw.rectangle((275,150,365,171),fill='white')
        draw.text((170,90),'EXAMPLE ROAD',fill='black',font=font)
        draw.text((196,94),'SECOND LABEL',fill='black',font=font)
    else:
        draw.text((190,115),'EXAMPLE ROAD',fill='black',font=font)
        draw.text((180,255),'SECOND LABEL',fill='black',font=font)
    return image

def main():
    if os.environ.get('OLLAMA_NO_CLOUD')!='1':raise RuntimeError('Cloud must be disabled on server and client')
    tags=request('/api/tags',timeout=10)['models']
    entry=next((m for m in tags if m.get('name')==MODEL),None)
    if not entry or not entry.get('digest','').removeprefix('sha256:').startswith('fb90415cde1e'):
        raise RuntimeError('Unexpected local model identity; do not silently accept a changed tag')
    results=[]
    with tempfile.TemporaryDirectory() as directory:
        for broken in (False,True):
            path=Path(directory)/f'fixture-{int(broken)}.png'
            fixture(broken).save(path)
            payload={'model':MODEL,'stream':False,'format':SCHEMA,
                     'options':{'temperature':0,'num_ctx':4096,'num_predict':220},
                     'messages':[{'role':'user','content':
                        'Inspect this diagram visually. Determine whether separate black road-name labels overlap one another, and whether the upper green road has a visible gap. The lower red road is separate. Return the requested JSON and briefly describe what you actually see. Do not assign a territory-quality score.',
                        'images':[base64.b64encode(path.read_bytes()).decode()]}]}
            envelope=request('/api/chat',payload)
            if envelope.get('done') is not True:raise RuntimeError('Incomplete inference')
            answer=json.loads(envelope['message']['content'])
            import jsonschema
            jsonschema.validate(answer,SCHEMA)
            matched=answer['label_overlap'] is broken and answer['road_gap'] is broken
            results.append({'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'expected':{'label_overlap':broken,'road_gap':broken},
                            'actual':answer,'matched':matched,
                            'raw_response':envelope})
    report={'model':MODEL,'model_digest':entry['digest'],'inference_calls':len(results),
            'matched_cases':sum(r['matched'] for r in results),'cases':results,
            'territory_release_approved':False,'calibration_status':'synthetic_smoke_only'}
    print(json.dumps(report,indent=2))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as stream:
            stream.write(f"\n## Actual local vision smoke\n{report['matched_cases']}/2 synthetic cases matched their known defects.\n")
            stream.write('This is real local inference, not territory calibration, independent source auditing, or card approval.\n')
    return 0 if report['matched_cases']==2 else 2

if __name__=='__main__':raise SystemExit(main())
