"""Opt-in live writer -> evidence actions -> separate Q02 model on synthetic media.

This exercises real Ollama model calls if installed. Never sends customer media,
never edits the original branch, and never authorizes a customer report. Any
model producing invalid/unsubstantiated output causes a BLOCKED trial record.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from PIL import Image
import subprocess
from pathlib import Path
import sys

from inspection_engine.core import DataError, sha256, blockers
from inspection_engine.capture import video_frames, probe_video
from inspection_engine.agents import execute_specialists, SPECIALIST_SCHEMA
from inspection_engine.critic import review_specialist_dossier, CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT
from inspection_engine.vision import ollama_local
from inspection_engine.local_runtime import preflight_models
from scripts.generate_public_fixtures import generate


def _distinct_video_sample_frames(first: Path, second: Path) -> bool:
    """Confirm video actually varies; a repeated still is not temporal evidence.

    This only tests the synthetic trial challenge, not property defects or model
    interpretation. Downsampling avoids false differences from JPEG compression.
    """
    with Image.open(first) as a, Image.open(second) as b:
        pixels_a = a.convert('RGB').resize((80, 48), Image.Resampling.BOX).tobytes()
        pixels_b = b.convert('RGB').resize((80, 48), Image.Resampling.BOX).tobytes()
    different = sum(sum(abs(pixels_a[i+j]-pixels_b[i+j]) for j in range(3)) > 90
                    for i in range(0, len(pixels_a), 3))
    return different >= 20


def run_trial(root:Path,writer_model:str,reviewer_model:str,*,writer=None,reviewer=None,with_video=True)->dict:
    """Writes only synthetic evidence and explicitly unapproved trial JSON under root."""
    root=root.resolve()
    if root.exists():
        raise DataError('Refusing to overwrite an existing live-trial directory')
    # Only the real provider path requires a running model. Injection is tests only.
    live=writer is None and reviewer is None
    if (writer is None)!=(reviewer is None):
        raise DataError('Both provider slots must be real or both explicitly supplied in tests')
    if live:
        preflight_models(writer_model,reviewer_model)
        writer=lambda image,prompt:ollama_local(image,prompt,writer_model,timeout=180,schema=SPECIALIST_SCHEMA)
        reviewer=lambda image,prompt:ollama_local(image,prompt,reviewer_model,timeout=180,
                    schema=CRITIC_SCHEMA,system_prompt=CRITIC_SYSTEM_PROMPT)
    if writer_model==reviewer_model:raise DataError('Writer/reviewer model identifiers must differ')
    root.mkdir(parents=True)
    record={'status':'STARTED','project_id':'SYNTHETIC-M2-LIVE-TRIAL',
            'started_utc':datetime.now(timezone.utc).isoformat(),
            'writer_model':writer_model,'reviewer_model':reviewer_model,
            'source_media':'SYNTHETIC_ONLY','real_model_invocations_requested':live,
            'real_model_invocations_completed':False,'customer_release_allowed':False,
            'independent_agent_host_verified':False,'field_accuracy_verified':False}
    try:
        generate(root,video=with_video)
        image=root/'examples/demo_exterior.png'
        media=[{'id':'P0001','kind':'photo','path':'examples/demo_exterior.png',
                'area':'exterior','sha256':sha256(image)}]
        if with_video:
            video=root/'examples/v05_photo_from_video/synthetic_moving_house_view.mp4'
            media.append({'id':'V0001','kind':'video',
                'path':'examples/v05_photo_from_video/synthetic_moving_house_view.mp4',
                'area':'exterior','sha256':sha256(video),'capture':probe_video(video)})
        project={'project_id':'SYNTHETIC-M2-LIVE-TRIAL',
                 'property':{'label':'Synthetic house drawing - not real evidence',
                             'inspection_date':'2026-10-30','synthetic':True},
                 'media':media,'observations':[],'findings':[],'equipment':[],'limitations':[]}
        selected=['P0001']
        if with_video:
            frames=video_frames(project,root,'V0001',max_frames=2)
            distinct=_distinct_video_sample_frames(root/frames[0]['path'],root/frames[1]['path'])
            record['video_content_variation_verified']=distinct
            if not distinct:
                raise DataError('Synthetic video has no material change between sampled moments')
            selected.append(frames[0]['id'])
        staged,dossier=execute_specialists(project,root,writer,media_ids=selected,
                            provider_id='local-ollama:'+writer_model if live else 'controlled-test:'+writer_model)
        (root/'staged_project.json').write_text(json.dumps(staged,indent=2)+'\n')
        (root/'specialist_dossier.json').write_text(json.dumps(dossier,indent=2)+'\n')
        record.update({'specialist_work_orders':len(dossier['plan']['jobs']),
                       'proposals':len(dossier['proposals']),
                       'evidence_tool_requests':dossier['tool_requests'],
                       'q01_q02_control_contracts':dossier['review'],
                       'sampled_video_frames':sum(x.get('derived_from_id')=='V0001' for x in project['media']),
                       'video_sampling_is_exhaustive':False})
        if dossier['proposals']:
            reviewed=review_specialist_dossier(staged,root,dossier,reviewer,
                        reviewer_id='Q02',provider_id='local-ollama:'+reviewer_model if live else 'controlled-test:'+reviewer_model)
            (root/'technical_review.json').write_text(json.dumps(reviewed,indent=2)+'\n')
            record['technical_review_items']=len(reviewed['items'])
            record['review_decisions']=reviewed['decision_summary']
        else:
            record['technical_review_items']=0
            record['review_note']='No model-generated candidate: separate claim-specific review cannot execute'
        record['status']='SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED' if record['technical_review_items'] else 'INCOMPLETE_NO_REVIEWABLE_CLAIM'
        record['real_model_invocations_completed']=bool(live and record['technical_review_items'])
        record['writer_model_calls_completed']=live
        record['reviewer_model_calls_completed']=bool(live and record['technical_review_items'])
        record['inspection_accuracy_verified']=False
        record['autonomous_zoom_request_count']=sum(x.get('kind')=='zoom' and x.get('status')=='EXECUTED' for x in dossier['tool_requests'])
        record['autonomous_video_still_count']=sum(x.get('kind')=='video_still' and x.get('status')=='EXECUTED' for x in dossier['tool_requests'])
        record['limitations']='Synthetic image test does not establish home defect accuracy, reliable autonomous tool requests, independent host identities, or inspector signoff.'
    except (DataError, OSError, RuntimeError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        record['status']='BLOCKED'
        record['error']=str(exc)
    finally:
        (root/'trial_status.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description='Real local Ollama trial on synthetic image and video ONLY')
    p.add_argument('--writer-model',default='qwen2.5vl:3b')
    p.add_argument('--review-model',default='granite3.2-vision:2b')
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--no-video',action='store_true',help='Only run a synthetic image (FFmpeg not needed)')
    args=p.parse_args()
    try: result=run_trial(args.out_dir,args.writer_model,args.review_model,with_video=not args.no_video)
    except DataError as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'customer_release_allowed':False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED' else 2

if __name__=='__main__':sys.exit(main())
