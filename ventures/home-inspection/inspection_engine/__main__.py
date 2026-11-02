"""Home inspection prototype CLI. All media-processing commands are local only."""
from __future__ import annotations
from pathlib import Path
import argparse
import json
from .core import load_project, blockers, coverage, media_inventory, record_status, validate_project, DataError
from .report import build_pdf
from .learning import compare_to_human
from .capture import intake_files, video_frames, verify_custody
from .vision import analyze_media, analyze_zoom_views, ollama_local, apply_predictions
from .zoom import create_zoom_views, grid_regions, zoom_from_predictions
from .video_photos import capture_video_photos, verify_selected_photo_pixels
from .agents import plan_specialists, execute_specialists
from .critic import review_specialist_dossier, CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT
from .local_runtime import preflight_models
from .model_smoke import smoke_probe
from .adjudication import adjudicate,ollama_reasoner


def main():
    ap=argparse.ArgumentParser(description='Local inspection prototype; NEVER a substitute for field review')
    sub=ap.add_subparsers(dest='command',required=True)
    for op in ['report','audit','compare','intake','frames','video-photos','video-photo-audit','analyze','analyze-zoom','zoom','zoom-grid','zoom-proposals','apply','agents-plan','agents-run','agents-critic','agents-adjudicate']:
        cmd=sub.add_parser(op)
        cmd.add_argument('project',type=Path)
        if op=='report':cmd.add_argument('--out',type=Path,required=True)
        if op=='compare':cmd.add_argument('--human',type=Path,required=True)
        if op in {'intake','frames','video-photos','zoom','zoom-grid','zoom-proposals','apply'}:cmd.add_argument('--out-project',type=Path,required=True)
        if op=='intake':
            cmd.add_argument('--area',required=True)
            cmd.add_argument('--room',default='')
            cmd.add_argument('files',type=Path,nargs='+')
        if op=='frames':
            cmd.add_argument('--video-id',required=True)
            cmd.add_argument('--count',type=int,default=6)
        if op=='video-photo-audit':
            cmd.add_argument('--photo-ids',nargs='+',required=True)
        if op=='video-photos':
            cmd.add_argument('--video-id',required=True)
            selector=cmd.add_mutually_exclusive_group(required=True)
            selector.add_argument('--at',nargs='+',help='Selected timestamps: 12.5, 01:24.5, 00:01:24.5')
            selector.add_argument('--every-seconds',type=float,help='Capture regularly at this interval')
            cmd.add_argument('--max-photos',type=int,default=12)
            cmd.add_argument('--agent',default='inspector')
            cmd.add_argument('--note',default='Selected evidence from original video')
        if op in {'zoom','zoom-grid','zoom-proposals'}:
            cmd.add_argument('--media-id',required=True)
            cmd.add_argument('--agent',default='inspection-specialist')
        if op in {'zoom','zoom-grid'}:
            cmd.add_argument('--bbox',nargs=4,type=float,default=[0,0,1,1],
                             metavar=('LEFT','TOP','RIGHT','BOTTOM'))
            cmd.add_argument('--purpose',default='Evaluate a region at native source resolution')
        if op=='zoom-proposals':
            cmd.add_argument('--predictions',type=Path,required=True)
            cmd.add_argument('--margin',type=float,default=.12)
            cmd.add_argument('--include-features',action='store_true')
        if op=='zoom-grid':
            cmd.add_argument('--columns',type=int,default=2)
            cmd.add_argument('--rows',type=int,default=2)
            cmd.add_argument('--overlap',type=float,default=0.15)
        if op in {'analyze','analyze-zoom'}:
            cmd.add_argument('--model',required=True,help='Installed local Ollama vision model')
            if op=='analyze':cmd.add_argument('--media-ids',nargs='+',required=True)
            else:cmd.add_argument('--zoom-ids',nargs='+',required=True)
            cmd.add_argument('--out',type=Path,required=True)
        if op=='apply':cmd.add_argument('--predictions',type=Path,required=True)
        if op in {'agents-plan','agents-run'}:
            cmd.add_argument('--media-ids',nargs='+',required=True)
        if op=='agents-critic':
            cmd.add_argument('--dossier',type=Path,required=True)
            cmd.add_argument('--review-model',required=True,help='Separate, already-installed local Ollama vision model')
            cmd.add_argument('--out',type=Path,required=True)
        if op=='agents-adjudicate':
            cmd.add_argument('--technical-review',type=Path,required=True)
            cmd.add_argument('--reasoning-model',required=True,help='Separate already-installed local Q03 model')
            cmd.add_argument('--out',type=Path,required=True)
            cmd.add_argument('--out-project',type=Path,required=True)
        if op=='agents-run':
            cmd.add_argument('--model',required=True,help='Already-installed local Ollama vision model')
            cmd.add_argument('--out-project',type=Path,required=True)
            cmd.add_argument('--dossier',type=Path,required=True)
            cmd.add_argument('--lesson-store',type=Path);cmd.add_argument('--lesson-policy',type=Path)
            cmd.add_argument('--lesson-model-digest',help='Pinned installed model digest; lessons remain default-off')

    preflight=sub.add_parser('model-preflight', help='Read-only check for two installed local vision models')
    preflight.add_argument('--writer-model',required=True)
    preflight.add_argument('--review-model',required=True)
    smoke=sub.add_parser('model-smoke', help='ACTUAL image-conditioned synthetic test; local Ollama only')
    smoke.add_argument('--writer-model', required=True)
    smoke.add_argument('--review-model', required=True)
    smoke.add_argument('--out', type=Path, required=True, help='New local JSON record, refuse overwrite')
    args=ap.parse_args()
    if args.command == 'model-preflight':
        try:
            result=preflight_models(args.writer_model,args.review_model)
        except DataError as exc:
            print(json.dumps({'preflight':'BLOCKED','reason':str(exc),
                              'real_inference_completed':False,
                              'customer_release_allowed':False},indent=2))
            raise SystemExit(2) from None
        print(json.dumps(result,indent=2))
        return
    if args.command == 'model-smoke':
        if args.out.exists():
            raise SystemExit('Refusing to overwrite local smoke proof')
        try:
            result = smoke_probe(args.writer_model, args.review_model)
        except DataError as exc:
            result={'test':'SYNTHETIC_LIVE_VISION', 'status':'BLOCKED',
                    'reason':str(exc), 'actual_image_inference_completed':False,
                    'customer_release_allowed':False}
            print(json.dumps(result,indent=2))
            raise SystemExit(2) from None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
        if result['status'] != 'SYNTHETIC_VISION_PROBE_PASSED':
            raise SystemExit(3)
        return
    source=args.project.resolve();doc=load_project(source)
    root=source.parent
    if args.command=='report':
        build_pdf(doc,root,args.out)
        answer={'output':str(args.out),'release':record_status(doc),'blockers':len(blockers(doc))}
    elif args.command=='audit':
        answer={'release':record_status(doc),'coverage':coverage(doc),'blockers':blockers(doc),
                'media':media_inventory(doc,root),'custody_errors':verify_custody(doc,root)}
    elif args.command=='compare':
        human=json.loads(args.human.read_text(encoding='utf-8'))
        answer=compare_to_human(doc,human)
    elif args.command=='intake':
        _check_new_path(args.out_project,root)
        answer={'accepted':intake_files(doc,root,args.files,args.area,args.room)}
        _write_project(args.out_project,doc)
        answer['project']=str(args.out_project)
    elif args.command=='frames':
        _check_new_path(args.out_project,root)
        answer={'frames':video_frames(doc,root,args.video_id,args.count)}
        _write_project(args.out_project,doc)
        answer['project']=str(args.out_project)
    elif args.command=='video-photos':
        _check_new_path(args.out_project,root)
        answer={'saved_photos':capture_video_photos(doc,root,args.video_id,args.at,
                  args.every_seconds,args.max_photos,args.agent,args.note)}
        _write_project(args.out_project,doc)
        answer['project']=str(args.out_project)
    elif args.command=='video-photo-audit':
        answer={'audits':[verify_selected_photo_pixels(doc,root,photo_id) for photo_id in args.photo_ids]}
    elif args.command in {'zoom','zoom-grid','zoom-proposals'}:
        _check_new_path(args.out_project,root)
        if args.command=='zoom-proposals':
            suggestions=json.loads(args.predictions.read_text(encoding='utf8'))
            zooms=zoom_from_predictions(doc,root,suggestions,args.media_id,args.agent,
                                   args.margin,args.include_features)
        else:
            regions=([args.bbox] if args.command=='zoom' else
                     grid_regions(args.bbox,args.columns,args.rows,args.overlap))
            zooms=create_zoom_views(doc,root,args.media_id,regions,args.agent,args.purpose)
        _write_project(args.out_project,doc)
        answer={'project':str(args.out_project),'views':zooms,
                'note':'Native source pixels only; digital zoom cannot create missing detail'}
    elif args.command in {'analyze','analyze-zoom'}:
        if args.out.exists():ap.error('Refusing to overwrite existing predictions')
        provider=lambda data,prompt:ollama_local(data,prompt,args.model)
        if args.command=='analyze':
            answer=analyze_media(doc,root,args.media_ids,provider,provider_id=f'local-ollama:{args.model}')
        else:
            answer=analyze_zoom_views(doc,root,args.zoom_ids,provider,
                     provider_id=f'local-ollama-native-zoom:{args.model}')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
    elif args.command=='agents-plan':
        answer=plan_specialists(doc,args.media_ids)
    elif args.command=='agents-run':
        _check_new_path(args.out_project,root)
        _check_new_path(args.dossier,root)
        provider=lambda data,prompt,*,schema:ollama_local(data,prompt,args.model,schema=schema)
        if args.lesson_store is not None or args.lesson_policy is not None or args.lesson_model_digest is not None:
            if args.lesson_store is None or args.lesson_policy is None or args.lesson_model_digest is None:
                raise DataError('Learned lessons require store, pinned policy and model digest')
            from .vision import pinned_vision_provider
            provider=pinned_vision_provider(args.model,args.lesson_model_digest)
        reviewed,dossier=execute_specialists(doc,root,provider,media_ids=args.media_ids,provider_accepts_schema=True,
                                provider_id=f'local-ollama:{args.model}',lesson_store=args.lesson_store,lesson_policy=args.lesson_policy)
        # No project write if a control check fails. Review dossier can still be saved
        # separately by a bounded operator, but this command fails closed.
        if not all(row['passed'] for row in dossier['review'].values()):
            raise DataError('Specialist evidence/control review failed; no project committed')
        _write_project(args.out_project,reviewed)
        args.dossier.write_text(json.dumps(dossier,indent=2)+'\n',encoding='utf-8')
        answer={'project':str(args.out_project),'dossier':str(args.dossier),
                'work_orders':len(dossier['plan']['jobs']),'control_checks':dossier['review'],
                'customer_release_allowed':False}
    elif args.command=='agents-critic':
        if args.out.exists():raise DataError('Refusing to overwrite existing technical review')
        if args.out.resolve().parent!=root.resolve():
            raise DataError('Technical review must be stored beside the local project file')
        dossier=json.loads(args.dossier.read_text(encoding='utf-8'))
        reviewer_id=f'local-ollama:{args.review_model}'
        provider=lambda image,prompt:ollama_local(image,prompt,args.review_model,schema=CRITIC_SCHEMA,
                  system_prompt=CRITIC_SYSTEM_PROMPT)
        answer=review_specialist_dossier(doc,root,dossier,provider,
              reviewer_id='Q02',provider_id=reviewer_id)
        args.out.write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
        answer={'review_file':str(args.out),'summary':answer['decision_summary'],
                'human_approval_required':True,'customer_release_allowed':False}
    elif args.command=='agents-adjudicate':
        _check_new_path(args.out,root);_check_new_path(args.out_project,root)
        if args.out.resolve()==args.out_project.resolve():raise DataError('Q03 report and project paths must differ')
        technical=json.loads(args.technical_review.read_text(encoding='utf-8'))
        result=adjudicate(doc,root,technical,lambda prompt,schema:ollama_reasoner(prompt,schema,args.reasoning_model),
                          provider_id='local-ollama:'+args.reasoning_model)
        from copy import deepcopy
        reviewed=deepcopy(doc);reviewed['adjudication']=result
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        _write_project(args.out_project,reviewed)
        answer={'adjudication_file':str(args.out),'project':str(args.out_project),'status':result['status'],
                'held_entry_ids':result['held_entry_ids'],'customer_release_allowed':False}
    elif args.command=='apply':
        _check_new_path(args.out_project,root)
        preds=json.loads(args.predictions.read_text(encoding='utf-8'))
        doc=apply_predictions(doc,root,preds)
        _write_project(args.out_project,doc)
        answer={'project':str(args.out_project),'release':record_status(doc),
                'blockers':len(blockers(doc))}
    print(json.dumps(answer,indent=2))


def _check_new_path(path:Path, root:Path):
    if path.resolve().parent!=root.resolve():
        raise DataError('Output project must share input project directory for relative media paths')
    if path.exists():raise DataError('Refusing to overwrite existing project JSON')


def _write_project(path:Path,doc:dict):
    path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
