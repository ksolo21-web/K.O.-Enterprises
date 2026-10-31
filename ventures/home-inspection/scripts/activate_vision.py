"""Explicit, local-only Ollama activation and real vision acceptance runner.

No auto-downloads, no public deployment, no customer media. Operator must use
--start-server and/or --download-models to authorize those respective effects.
Every result is a diagnostic/evidence record, never a customer release approval.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from inspection_engine.core import DataError
from inspection_engine.local_runtime import local_json, preflight_models, validate_model_name
from scripts.run_vision_acceptance import run_acceptance

MODELS = ('qwen2.5vl:3b','granite3.2-vision:2b')


def _on_loopback_only() -> None:
    host = os.environ.get('OLLAMA_HOST', '127.0.0.1:11434')
    if host not in ('127.0.0.1:11434','http://127.0.0.1:11434'):
        raise DataError('OLLAMA_HOST must be exactly 127.0.0.1:11434 (no public binding)')


def machine_status(*, executable_lookup=shutil.which, disk_usage=shutil.disk_usage) -> dict:
    """Collect read-only prerequisite facts; recommendations are not acceptance."""
    _on_loopback_only()
    ollama=executable_lookup('ollama')
    ffmpeg=executable_lookup('ffmpeg')
    py_ok=sys.version_info >= (3, 12)
    try:
        import PIL
        import reportlab
        import pypdf
        deps=True
    except ImportError:
        deps=False
    memory_gib=None
    meminfo=Path('/proc/meminfo')
    if meminfo.is_file():
        try:
            for line in meminfo.read_text().splitlines():
                if line.startswith('MemTotal:'):
                    memory_gib=round(int(line.split()[1])/1024/1024,1)
                    break
        except (OSError,ValueError):
            pass
    try:
        disk_free_gib=round(disk_usage(Path.cwd()).free/2**30,1)
    except OSError:
        disk_free_gib=None
    return {
        'python_supported':py_ok,'python_version':sys.version.split()[0],
        'ollama_binary_found':bool(ollama),'ffmpeg_found':bool(ffmpeg),
        'project_dependencies_found':deps,'system_ram_gib':memory_gib,
        'free_disk_gib':disk_free_gib,
        'ram_caution':bool(memory_gib is not None and memory_gib < 12),
        'disk_caution':bool(disk_free_gib is not None and disk_free_gib < 9),
        'model_weights_downloaded':False,'live_inference_verified':False,
        'customer_release_allowed':False,
    }


def _server_ready() -> bool:
    try:
        data=local_json('GET','/api/tags',timeout=2)
        return isinstance(data.get('models'),list)
    except DataError:
        return False


def _begin_server(binary:str, log_path:Path) -> subprocess.Popen:
    env=os.environ.copy()
    env['OLLAMA_HOST']='127.0.0.1:11434'
    # Do not inherit stdio; server may live beyond the activation command.
    with log_path.open('ab') as logfile:
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
        return subprocess.Popen([binary,'serve'],env=env,stdin=subprocess.DEVNULL,
                stdout=logfile,stderr=subprocess.STDOUT,
                creationflags=flags,start_new_session=(os.name!='nt'))


def _write(path:Path, value:dict) -> None:
    if path.exists():
        raise DataError('Refusing to overwrite activation evidence')
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def activate(root:Path,writer_model:str=MODELS[0],reviewer_model:str=MODELS[1],
             *,start_server:bool=False,download_models:bool=False,
             run_live_gate:bool=False, runner=run_acceptance,
             status_fn=machine_status, ready_fn=_server_ready,
             start_fn=_begin_server, pull_fn=subprocess.run,
             preflight_fn=preflight_models, sleep_fn=time.sleep) -> dict:
    """Deterministically blocks on absent prerequisites; no simulated pass claims."""
    _on_loopback_only()
    writer_model=validate_model_name(writer_model)
    reviewer_model=validate_model_name(reviewer_model)
    if writer_model==reviewer_model:
        raise DataError('Writer/reviewer model identifiers must differ')
    root=root.resolve()
    if root.exists():raise DataError('Refusing to overwrite prior activation record')
    root.mkdir(parents=True)
    record={
        'schema_version':1,'started_utc':datetime.now(timezone.utc).isoformat(),
        'status':'BLOCKED','stage':'prerequisites','writer_model':writer_model,
        'reviewer_model':reviewer_model,'operator_authorized_server_start':start_server,
        'operator_authorized_model_downloads':download_models,
        'operator_authorized_live_trial':run_live_gate,
        'model_inference_verified':False,'field_accuracy_verified':False,
        'customer_release_allowed':False,
        'server_process_started':False,'model_downloads_performed':[],
    }
    try:
        info=status_fn()
        record['machine']=info
        if not info['python_supported']:
            raise DataError('Python 3.12+ required')
        if not info['project_dependencies_found']:
            raise DataError('Install the three packages in requirements.txt')
        if not info['ollama_binary_found']:
            raise DataError('Ollama is not installed; download from https://ollama.com/download')
        if run_live_gate and not info['ffmpeg_found']:
            raise DataError('FFmpeg is required for the full video trial')
        binary=shutil.which('ollama')
        if not binary:raise DataError('Ollama binary not found')
        record['stage']='local_server'
        if not ready_fn():
            if not start_server:
                raise DataError('Ollama server is not running; rerun with --start-server')
            proc=start_fn(binary,root/'ollama_server.log')
            record['server_process_started']=True
            record['server_process_id']=proc.pid
            for i in range(25):
                if ready_fn():break
                if proc.poll() is not None:
                    raise DataError('Ollama server exited during startup; inspect ollama_server.log')
                sleep_fn(.4)
            if not ready_fn():
                raise DataError('Ollama server did not become ready on 127.0.0.1:11434')
        record['stage']='models'
        if download_models:
            for name in (writer_model,reviewer_model):
                result=pull_fn([binary,'pull',name],check=False,timeout=1800)
                if result.returncode!=0:
                    raise DataError('Model download failed: '+name)
                record['model_downloads_performed'].append(name)
        models=preflight_fn(writer_model,reviewer_model)
        record['preflight']=models
        record['stage']='ready_for_live_trial'
        record['status']='LOCAL_MODELS_READY_FIELD_VALIDATION_OPEN'
        if run_live_gate:
            record['stage']='live_gate'
            result=runner(root/'acceptance',writer_model,reviewer_model)
            record['acceptance_status']=result.get('status')
            # Only real production dependency executions are eligible for this claim.
            record['model_inference_verified']=bool(runner is run_acceptance and result.get('production_dependencies_used') and
                result.get('live_model_inference_verified') and
                result.get('live_specialist_tool_use_verified') and
                result.get('reviewer_visual_assessment_verified') and
                result.get('status')=='LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN')
            if not record['model_inference_verified']:
                record['status']='BLOCKED'
                record['blocker']='Live vision acceptance did not pass; inspect acceptance/acceptance_status.json'
            else:
                record['status']='LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN'
            record['stage']='live_gate_complete'
    except (DataError, OSError, subprocess.SubprocessError, ValueError, TimeoutError) as exc:
        record['status']='BLOCKED'
        record['blocker']=str(exc)
    finally:
        record['ended_utc']=datetime.now(timezone.utc).isoformat()
        _write(root/'activation_status.json',record)
    return record


def main() -> int:
    p=argparse.ArgumentParser(description='Local Ollama activation; customer release always blocked')
    p.add_argument('--out-dir',type=Path,required=True,help='New directory for proof; never overwrites')
    p.add_argument('--writer-model',default=MODELS[0]);p.add_argument('--review-model',default=MODELS[1])
    p.add_argument('--start-server',action='store_true',help='Explicitly authorize starting an installed Ollama server')
    p.add_argument('--download-models',action='store_true',help='Explicitly authorize public model downloads')
    p.add_argument('--run-live-gate',action='store_true',help='Explicitly run the real synthetic inference trial')
    args=p.parse_args()
    try:
        result=activate(args.out_dir,args.writer_model,args.review_model,start_server=args.start_server,
                        download_models=args.download_models,run_live_gate=args.run_live_gate)
    except DataError as e:
        print(json.dumps({'status':'BLOCKED','blocker':str(e),'customer_release_allowed':False},indent=2));return 2
    print(json.dumps(result,indent=2));return 0 if result['status']!='BLOCKED' else 2

if __name__=='__main__':sys.exit(main())
