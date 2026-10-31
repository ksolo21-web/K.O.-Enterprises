"""One pinned synthetic A07 request, with a diagnostic-only absolute deadline.

No tool execution, review, retry, model install, customer input or release. This
does not change the application's 180-second transport limit. Run only inside
the separately authorized one-time CPU diagnostic.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import threading
import time

from inspection_engine.agents import ROLE_BY_ID, _provider_envelope, specialist_schema
from inspection_engine.core import DataError
from inspection_engine.local_runtime import local_json, MAX_REQUEST_BYTES
from inspection_engine.vision import SYSTEM_PROMPT, MAX_MODEL_REPLY

PORT=11434
MODEL='qwen2.5vl:3b'
DIGEST='fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1'
SOURCE_SHA256='a1532266e23d880b156c8cd18f0024eecc7745c5a88f40454f72356555a7b7b2'
SOURCE=Path(__file__).resolve().parents[1]/'docs/evidence/A07_FIRST_WRITER_FAILURE.json'
FIELDS={'model','created_at','response','done','done_reason','error','total_duration',
        'load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def replay_payload():
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise DataError('Pinned synthetic replay document changed')
    source=json.loads(raw);request=source['request']
    image=base64.b64decode(source['input_image_base64'],validate=True)
    if hashlib.sha256(image).hexdigest()!=request['image_sha256']:
        raise DataError('Replay image hash mismatch')
    if hashlib.sha256(request['prompt'].encode()).hexdigest()!=request['prompt_sha256']:
        raise DataError('Replay prompt hash mismatch')
    schema=request['generation_schema']
    if hashlib.sha256(canonical(schema)).hexdigest()!=request['generation_schema_sha256']:
        raise DataError('Replay schema hash mismatch')
    if schema!=specialist_schema(['exterior']) or request['model']!=MODEL:
        raise DataError('Replay must match current exterior schema and pinned writer')
    return {'model':MODEL,'prompt':request['prompt'],'system':SYSTEM_PROMPT,
            'images':[source['input_image_base64']],'format':schema,'stream':False,
            'options':{'temperature':0},'keep_alive':0},request


def verify_writer():
    inventory=local_json('GET','/api/tags')
    matches=[m for m in inventory.get('models',[]) if isinstance(m,dict) and m.get('name')==MODEL]
    if len(matches)!=1 or matches[0].get('digest')!=DIGEST:
        raise DataError('Pinned writer model digest not installed')
    info=local_json('POST','/api/show',{'model':MODEL})
    if not isinstance(info.get('capabilities'),list) or 'vision' not in info['capabilities']:
        raise DataError('Pinned writer does not advertise vision')
    return {'model':MODEL,'digest':DIGEST,'advertised_vision':True,
            'metadata_is_not_inference':True}


def diagnostic_generate(payload,*,deadline_seconds=600,response_audit=None):
    """One fixed loopback request; watchdog stops even slow header/body drips."""
    if type(deadline_seconds) is not int or not 1<=deadline_seconds<=600:
        raise DataError('Diagnostic deadline must be 1-600 seconds')
    if response_audit is not None and not callable(response_audit):
        raise DataError('Diagnostic response audit must be callable')
    encoded=json.dumps(payload,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    if len(encoded)>MAX_REQUEST_BYTES:raise DataError('Diagnostic request exceeds limit')
    conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=deadline_seconds)
    expired=threading.Event();original_socket=[None]
    started=time.monotonic()
    audit={'http_status':None,'received_bytes':0,'body_complete':False}
    body_hash=hashlib.sha256()

    def expire():
        expired.set()
        active=original_socket[0] or conn.sock
        if active is not None:
            try:active.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        conn.close()

    watchdog=threading.Timer(deadline_seconds,expire);watchdog.daemon=True;watchdog.start()
    try:
        conn.request('POST','/api/generate',encoded,{'Content-Type':'application/json','Accept':'application/json'})
        original_socket[0]=conn.sock
        response=conn.getresponse()
        audit['http_status']=response.status
        chunks=[];size=0
        while True:
            chunk=response.read1(min(16384,MAX_MODEL_REPLY+1-size))
            if expired.is_set() or time.monotonic()-started>=deadline_seconds:
                raise TimeoutError('Absolute diagnostic deadline expired')
            if not chunk:
                # read1() can reach EOF without raising IncompleteRead, even
                # while a declared Content-Length remains. Valid JSON alone
                # must not turn a truncated HTTP body into completed evidence.
                if response.length is not None and response.length>0:
                    audit['declared_bytes_remaining']=response.length
                    raise DataError('Diagnostic HTTP body truncated before declared length')
                break
            chunks.append(chunk);size+=len(chunk);body_hash.update(chunk);audit['received_bytes']=size
            if size>MAX_MODEL_REPLY:raise DataError('Diagnostic response exceeds limit')
        raw=b''.join(chunks)
        audit['body_complete']=True
        try:
            value=json.loads(raw)
            audit['json_type']=type(value).__name__
            if isinstance(value,dict):
                audit['transport_response_untrusted']={k:v for k,v in value.items() if k in FIELDS}
                audit['omitted_fields']=sorted(set(value)-FIELDS)
        except (ValueError,UnicodeError) as exc:
            audit['parse_error_type']=type(exc).__name__
            value=None
        if response.status!=200:raise DataError(f'Diagnostic HTTP status {response.status}; no redirect or retry')
        if value is None:raise DataError('Diagnostic response is invalid JSON; digest retained')
        if not isinstance(value,dict):raise DataError('Diagnostic response must be an object')
        return value,body_hash.hexdigest()
    except (OSError,http.client.HTTPException) as exc:
        if expired.is_set() or isinstance(exc,TimeoutError):
            raise TimeoutError('Absolute diagnostic deadline expired before a completed response') from exc
        raise DataError('Diagnostic transport failed before a completed response') from exc
    finally:
        watchdog.cancel();conn.close()
        audit.update(body_sha256=body_hash.hexdigest(),elapsed_seconds=round(time.monotonic()-started,3))
        if response_audit is not None:response_audit(audit)


def run(root:Path,*,deadline_seconds=600):
    if type(deadline_seconds) is not int or not 1<=deadline_seconds<=600:
        raise DataError('Diagnostic deadline must be 1-600 seconds')
    root.mkdir(parents=True,exist_ok=False)
    result={'status':'STARTED','scope':'ONE_PINNED_SYNTHETIC_REQUEST',
            'deadline_seconds':deadline_seconds,'customer_release_allowed':False,
            'tools_executed':0,'Q02_calls':0,'completed_model_response':False,
            'specialist_contract_validated':False,'field_accuracy_verified':False}
    started=time.monotonic()
    try:
        payload,request=replay_payload()
        write(root/'request.json',{'source_sha256':SOURCE_SHA256,'payload':payload,
            'payload_sha256':hashlib.sha256(json.dumps(payload,separators=(',',':'),ensure_ascii=True).encode()).hexdigest(),
            'image_sha256':request['image_sha256'],'prompt_sha256':request['prompt_sha256'],
            'schema_sha256':request['generation_schema_sha256']})
        write(root/'runtime.json',{'cpu_count':os.cpu_count(),
            'cpu_affinity_count':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
            'python':os.sys.version,'clock':'monotonic','endpoint':'127.0.0.1:11434'})
        write(root/'model_identity.json',verify_writer())
        print('A08: one exact pinned synthetic generation request started',flush=True)
        value,body_hash=diagnostic_generate(payload,deadline_seconds=deadline_seconds,
                                          response_audit=lambda record:write(root/'http_response.json',record))
        write(root/'response.json',{'body_sha256':body_hash,
              'transport_response_untrusted':{k:v for k,v in value.items() if k in FIELDS},
              'omitted_fields':sorted(set(value)-FIELDS)})
        if value.get('done') is not True or 'error' in value or value.get('done_reason')!='stop':
            raise DataError('Diagnostic generation not successfully completed with stop')
        result['completed_model_response']=True
        answer=json.loads(value['response'])
        candidates,requests=_provider_envelope(answer,ROLE_BY_ID['T03'],{'id':'P0001','area':'exterior'},systems=['exterior'])
        for action in requests:
            if action['kind']!='zoom':raise DataError('Standalone replay cannot request a video still')
            left,top,right,bottom=action['bbox']
            if (right-left)*(bottom-top)>=0.98:raise DataError('Unchanged zoom request rejected')
        result.update(status='ISOLATED_WRITER_CONTRACT_PASSED_M2_OPEN',
                      specialist_contract_validated=True,candidate_count=len(candidates),
                      proposed_actions_not_executed=requests)
    except (DataError,OSError,ValueError,KeyError,TypeError,http.client.HTTPException) as exc:
        causes=[];cause=exc.__cause__
        while cause is not None and len(causes)<4:
            causes.append(type(cause).__name__);cause=cause.__cause__
        result.update(status='BLOCKED',error_type=type(exc).__name__,error=str(exc),cause_types=causes)
    finally:
        result['elapsed_seconds']=round(time.monotonic()-started,3)
        result['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(root.glob('*.json'))}
        write(root/'status.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',required=True,type=Path)
    parser.add_argument('--deadline-seconds',type=int,default=600)
    args=parser.parse_args()
    result=run(args.out_dir,deadline_seconds=args.deadline_seconds)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['specialist_contract_validated'] else 2


if __name__=='__main__':raise SystemExit(main())
