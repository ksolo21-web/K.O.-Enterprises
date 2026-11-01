"""Opt-in SYNTHETIC local writer -> Q02 -> Q03 -> held Option2 report.

No downloads, remote dispatch, arbitrary evidence input or customer release.
Use a fresh directory and already installed, evaluated, digest-distinct models.
Controlled provider injection exercises contracts, never counts as live proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time

from inspection_engine.adjudication import adjudicate,ollama_reasoner,validate_record,digest
from inspection_engine.core import DataError,load_project,blockers,record_status,sha256
from inspection_engine.local_runtime import local_json,validate_model_name,preflight_models
from inspection_engine.report import build_pdf
from .run_local_live_trial import run_trial


def _preflight(writer,reviewer,reasoner):
    preflight_models(writer,reviewer)
    inventory=local_json('GET','/api/tags').get('models',[])
    if not isinstance(inventory,list):raise DataError('Local model inventory must be a list')
    models={r.get('name'):r for r in inventory if isinstance(r,dict)}
    rows=[]
    for role,name in [('writer',writer),('Q02',reviewer),('Q03',reasoner)]:
        value=models.get(name,{}).get('digest')
        import re
        if not isinstance(value,str) or not re.fullmatch('[0-9a-fA-F]{64}',value):
            raise DataError('All three installed models require recorded SHA256 digests')
        rows.append({'role':role,'model':name,'digest':value.lower()})
    if len({r['digest'] for r in rows})!=3:raise DataError('Three distinct model digests required; aliases are insufficient')
    metadata=local_json('POST','/api/show',{'model':reasoner})
    capabilities=metadata.get('capabilities')
    if not isinstance(capabilities,list) or 'completion' not in capabilities:raise DataError('Q03 must advertise text completion')
    return rows


def run_reconciliation_trial(root,writer_model,reviewer_model,reasoning_model,*,
        writer=None,reviewer=None,reasoner=None,with_video=True,allow_local_inference=False,
        visual_first=False):
    root=Path(root).resolve()
    if root.exists():raise DataError('Refusing to overwrite an existing reconciliation trial')
    names=[validate_model_name(n) for n in (writer_model,reviewer_model,reasoning_model)]
    if len(set(names))!=3:raise DataError('Writer, Q02 and Q03 identifiers must all differ')
    slots=(writer,reviewer,reasoner)
    if any(x is not None for x in slots) and not all(callable(x) for x in slots):
        raise DataError('All providers must be real or all explicitly controlled in tests')
    live=all(x is None for x in slots)
    if live and allow_local_inference is not True:raise DataError('Explicit local synthetic inference opt-in required')
    metadata=_preflight(*names) if live else []
    # The separate opt-in path never changes legacy controlled-test calls.
    if type(visual_first) is not bool:raise DataError('Visual-first flag must be boolean')
    visual_opts={'visual_first':True} if visual_first else {}
    base=run_trial(root,writer_model,reviewer_model,writer=writer,reviewer=reviewer,with_video=with_video,scope='residential',**visual_opts)
    result={'schema_version':1,'source_media':'SYNTHETIC_ONLY','execution_kind':'local_ollama' if live else 'controlled_test',
        'models':metadata,'base_trial_status':base['status'],'q03_model':reasoning_model,
        'q03_provider_invoked':False,'q03_live_call_completed':False,'status':'BLOCKED',
        'call_budgets':{'writer_maximum':6,'Q02_maximum':48,'Q03_maximum':1,'automatic_retries':0},
        'full_milestone_2_approved':False,'field_accuracy_verified':False,'customer_release_allowed':False}
    try:
        if base['status']=='BLOCKED':raise DataError('Writer/Q02 trial blocked; inspect preserved base evidence')
        document=load_project(root/'staged_project.json')
        review=json.loads((root/'technical_review.json').read_text())
        provider='local-ollama:'+reasoning_model if live else 'controlled-test:'+reasoning_model
        def call(prompt,schema):
            request={'model':reasoning_model,'execution_kind':result['execution_kind'],'prompt':prompt,
                'prompt_sha256':digest(prompt),'schema':schema,'schema_sha256':digest(schema)}
            _write(root/'q03_request.json',request)
            started=time.monotonic();response={'execution_kind':result['execution_kind'],'model_output_is_untrusted':True}
            result['q03_provider_invoked']=True
            try:
                answer=ollama_reasoner(prompt,schema,reasoning_model,
                    response_audit=lambda value:response.update(transport_response_untrusted=value)) if live else reasoner(prompt,schema)
                response['structured_response_untrusted']=answer;response['status']='RETURNED_UNVALIDATED_DATA'
                result['q03_live_call_completed']=live
                return answer
            except (DataError,OSError,ValueError,TypeError,TimeoutError) as exc:
                response.update(status='PROVIDER_ERROR',error_type=type(exc).__name__,error=str(exc));raise
            finally:
                response['elapsed_seconds']=round(time.monotonic()-started,3)
                _write(root/'q03_response.json',response)
        adjudication=adjudicate(document,root,review,call,provider_id=provider)
        validate_record(document,adjudication)
        document['adjudication']=adjudication
        _write(root/'adjudication.json',adjudication);_write(root/'adjudicated_project.json',document)
        build_pdf(document,root,root/'held_report.pdf')
        proof=base.get('tool_review_evidence',{})
        tools=(base.get('autonomous_zoom_request_count',0)>0 and base.get('autonomous_video_still_count',0)>0)
        # Tool acceptance comes from the existing source/result/Q02 lineage checks, not counters alone.
        tool_verified=all(bool(proof.get(key)) for key in ('reviewed_zoom_ids','reviewed_video_still_ids',
            'temporally_distinct_reviewed_video_still_ids','visibly_changed_reviewed_video_still_ids'))
        result.update(status='SYNTHETIC_RECONCILIATION_COMPLETE_UNVERIFIED' if tools and tool_verified and base.get('proposals',0)>0
            else 'SYNTHETIC_RECONCILIATION_WITH_GAPS',
            q03_status=adjudication['status'],q03_decisions=len(adjudication['decisions']),
            held_entry_ids=adjudication['held_entry_ids'],report_status=record_status(document),
            report_blockers=blockers(document),report_sha256=sha256(root/'held_report.pdf'),
            tool_lineage_verified=tool_verified,tools_requested_and_executed=tools,
            workflow_contract_completed=True,independent_runtime_identity_verified=False)
    except (DataError,OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        result['reason']=str(exc)
    _write(root/'reconciliation_status.json',result)
    manifest={str(p.relative_to(root)):sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}
    _write(root/'reconciliation_manifest.json',{'files':manifest,'customer_release_allowed':False})
    return result


def _write(path,value):
    with path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser(description='Synthetic local three-model trial; no installation or release')
    p.add_argument('--writer-model',required=True);p.add_argument('--review-model',required=True)
    p.add_argument('--reasoning-model',required=True);p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--allow-local-inference',action='store_true');p.add_argument('--no-video',action='store_true')
    p.add_argument('--visual-first',action='store_true',help='Opt-in: bounded pixel stage with private deferred expert packet; not a field approval')
    a=p.parse_args()
    import signal
    if not hasattr(signal,'SIGALRM'):raise SystemExit('CLI requires an OS with SIGALRM for the 1800-second absolute deadline')
    def expired(signum,frame):raise TimeoutError('Synthetic reconciliation exceeded 1800-second absolute deadline; server cancellation is unverified')
    old_handler=signal.signal(signal.SIGALRM,expired);signal.alarm(1800)
    try:r=run_reconciliation_trial(a.out_dir,a.writer_model,a.review_model,a.reasoning_model,
        with_video=not a.no_video,allow_local_inference=a.allow_local_inference,visual_first=a.visual_first)
    except (DataError,OSError,ValueError,TypeError,TimeoutError) as exc:r={'status':'BLOCKED','reason':str(exc),'customer_release_allowed':False}
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,old_handler)
    print(json.dumps(r,indent=2))
    return 0 if r['status']=='SYNTHETIC_RECONCILIATION_COMPLETE_UNVERIFIED' else 2

if __name__=='__main__':raise SystemExit(main())
