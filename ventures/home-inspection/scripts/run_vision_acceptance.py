"""One-shot, local-only model acceptance evidence. Never approves field use.

No network downloads, hosted inference, customer data or report publication. The
only service contacted by production providers is Ollama on 127.0.0.1:11434.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from inspection_engine.core import DataError
from inspection_engine.local_runtime import preflight_models
from inspection_engine.model_smoke import smoke_probe
from scripts.run_local_live_trial import run_trial


def _write_json(path: Path, value: dict) -> None:
    if path.exists():
        raise DataError('Refusing to overwrite prior acceptance evidence')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n',encoding='utf-8')


def run_acceptance(root: Path, writer_model: str, review_model: str,
                   *, preflight=preflight_models, smoke=smoke_probe,
                   trial=run_trial, with_video: bool=True) -> dict:
    """Run real probes unless dependencies explicitly replaced for unit tests.

    A passing unit test never becomes a live acceptance result. Real gate requires
    four true image-conditioned probes and BOTH agent-selected zoom/still actions.
    """
    root = root.resolve()
    if root.exists():
        raise DataError('Refusing to overwrite existing acceptance directory')
    real=(preflight is preflight_models and smoke is smoke_probe and trial is run_trial)
    if writer_model == review_model:
        raise DataError('Writer and reviewer must have different model names')
    root.mkdir(parents=True)
    record={
        'schema_version':1,'started_utc':datetime.now(timezone.utc).isoformat(),
        'status':'BLOCKED','test_scope':'SYNTHETIC_ONLY',
        'writer_model':writer_model,'reviewer_model':review_model,
        'production_dependencies_used':real,
        'live_model_inference_verified':False,'live_specialist_tool_use_verified':False,
        'reviewer_visual_assessment_verified':False,
        'qualified_inspector_assessment_verified':False,
        'real_property_defect_accuracy_verified':False,
        'independent_reviewer_host_verified':False,
        'customer_release_allowed':False,
        'stage':'preflight'
    }
    try:
        registry=preflight(writer_model,review_model)
        record['preflight']=registry
        checks=registry.get('models')
        if not isinstance(checks,list) or len(checks)!=2 or not all(m.get('vision_capability_advertised') for m in checks):
            raise DataError('Preflight did not establish two vision-capable models')
        digests=[m.get('model_digest_sha256') for m in checks]
        if real and (not all(isinstance(d,str) and len(d)==64 for d in digests) or digests[0]==digests[1]):
            raise DataError('Two distinct model digests are required for an auditable live run')
        record['stage']='synthetic_image_probe'
        challenge=smoke(writer_model,review_model)
        _write_json(root/'image_probe.json',challenge)
        record['image_probe_status']=challenge.get('status')
        probes=challenge.get('models')
        if not isinstance(probes,list) or len(probes)!=4 or challenge.get('probes_per_model')!=2:
            raise DataError('Each vision model must analyze BOTH visual challenges')
        if not all(p.get('passed') is True for p in probes):
            raise DataError('At least one image-conditioned visual challenge failed')
        if real and (challenge.get('status')!='SYNTHETIC_VISION_PROBE_PASSED' or not challenge.get('actual_image_inference_executed')):
            raise DataError('Visual responses were not produced by the real local transport')
        record['live_model_inference_verified']=bool(real)
        record['stage']='specialist_review_trial'
        # run_trial creates its own directory, and in real mode owns the provider
        # instantiation. Never route synthetic sample images to external services.
        example_dir=root/'trial'
        report=trial(example_dir,writer_model,review_model,with_video=with_video)
        record['specialist_trial_status']=report.get('status')
        record['autonomous_zoom_request_count']=report.get('autonomous_zoom_request_count',0)
        record['autonomous_video_still_count']=report.get('autonomous_video_still_count',0)
        record['technical_review_items']=report.get('technical_review_items',0)
        record['reviewer_visual_assessment_verified']=bool(real and report.get('reviewer_model_calls_completed'))
        record['live_specialist_tool_use_verified']=bool(real and report.get('autonomous_zoom_request_count',0)>0 and
                                                       (not with_video or report.get('autonomous_video_still_count',0)>0))
        if report.get('status')!='SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED':
            raise DataError('Synthetic trial did not reach independent claim-review stage')
        if not report.get('technical_review_items',0):
            raise DataError('No candidate underwent Q02 visual review')
        if not record['autonomous_zoom_request_count']:
            raise DataError('Real specialist did not choose a native-pixel zoom')
        if with_video and not record['autonomous_video_still_count']:
            raise DataError('Real specialist did not select a saved video photograph')
        if not real:
            raise DataError('Scripted providers cannot satisfy the live-model acceptance gate')
        if not report.get('real_model_invocations_completed') or not report.get('reviewer_model_calls_completed'):
            raise DataError('Real writer and reviewer calls were not both completed')
        if not with_video:
            raise DataError('Full media gate requires video frame selection and extraction')
        record['status']='LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN'
        record['stage']='synthetic_gate_complete'
    except (DataError,OSError,RuntimeError,ValueError,TimeoutError) as exc:
        record['status']='BLOCKED'
        record['blocker']=str(exc)
    finally:
        record['artifact_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(root.rglob('*.json')) if p.name!='acceptance_status.json'}
        record['ended_utc']=datetime.now(timezone.utc).isoformat()
        _write_json(root/'acceptance_status.json',record)
    return record


def main():
    parser=argparse.ArgumentParser(description='Local image-conditioned model and tool-use acceptance trial')
    parser.add_argument('--writer-model',default='qwen2.5vl:3b')
    parser.add_argument('--review-model',default='granite3.2-vision:2b')
    parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--no-video',action='store_true',help='Diagnostic only: cannot pass full media gate')
    args=parser.parse_args()
    try:
        result=run_acceptance(args.out_dir,args.writer_model,args.review_model,with_video=not args.no_video)
    except DataError as exc:
        print(json.dumps({'status':'BLOCKED','blocker':str(exc),'customer_release_allowed':False},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN' else 2


if __name__=='__main__':
    sys.exit(main())
