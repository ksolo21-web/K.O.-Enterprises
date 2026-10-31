"""One exact synthetic exception to the pause; metadata checks never invoke a model."""
from __future__ import annotations
import hashlib,json,os,re,subprocess
from pathlib import Path
from inspection_engine.core import DataError
from inspection_engine.local_runtime import local_json

AUTH='OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A09'
APPROVAL='ventures/home-inspection/docs/ONE_TIME_SYNTHETIC_TRIAL_APPROVAL_2026-10-31_A09.md'
MODELS={
'qwen2.5vl:3b':'fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1',
'granite3.2-vision:2b':'3be41a661804ad72cd08269816c5a145f1df6479ad07e2b3a7e29dba575d2669',
'qwen2.5:7b':'845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e'}


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True,timeout=5).strip()


def verify_scope(root:Path,env:dict):
    expected={'GITHUB_REPOSITORY':'ksolo21-web/K.O.-Enterprises','GITHUB_REF':'refs/heads/home-inspection-development',
        'GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1','A09_REPOSITORY_VISIBILITY':'public'}
    if any(env.get(k)!=v for k,v in expected.items()):raise DataError('A09 event/repository/branch/attempt/visibility mismatch')
    if not (root/'PAUSE_AUTONOMY').is_file():raise DataError('Root pause must remain present')
    if git(root,'hash-object','PAUSE_AUTONOMY')!='37455fd13813683bb0169d36cb24b86a07094aa7':raise DataError('Root pause changed')
    document=(root/APPROVAL).read_text()
    if f'Authorization-ID: {AUTH}' not in document.splitlines():raise DataError('A09 authorization identity mismatch')
    if 'Authorization-Scope: one synthetic-only GitHub-hosted CPU reconciliation trial, no customers, no secrets, no deployment' not in document.splitlines():
        raise DataError('A09 authorization scope mismatch')
    matches=re.findall(r'^Source-Commit: ([0-9a-f]{40})$',document,re.M)
    if len(matches)!=1 or git(root,'rev-parse','HEAD^')!=matches[0]:raise DataError('A09 reviewed source parent mismatch')
    if git(root,'rev-parse','HEAD')!=env.get('GITHUB_SHA'):raise DataError('Checkout does not match triggering SHA')
    if git(root,'log','-1','--format=%B')!=f'trial(home-inspection): {AUTH}':raise DataError('A09 trigger message mismatch')
    if git(root,'diff-tree','--no-commit-id','--name-status','-r','HEAD').splitlines()!=['A\t'+APPROVAL]:
        raise DataError('Trigger must add one NEW authorization record; consumed records cannot be reused')
    parent_record=subprocess.run(['git','-C',str(root),'cat-file','-e','HEAD^:'+APPROVAL],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
    if parent_record.returncode==0:raise DataError('A09 authorization was already present in the parent')
    product=root/'ventures/home-inspection'
    if any((product/p).exists() for p in ('private_case','customer_data','client_data')):raise DataError('Unexpected customer evidence directory')
    return {'status':'ONE_EXACT_SYNTHETIC_EXCEPTION_VERIFIED','source_commit':matches[0],
        'trigger_commit':env['GITHUB_SHA'],'pause_preserved':True,'customer_release_allowed':False}


def check_resource_budget(free_disk,available_memory,total_memory):
    if free_disk<18*1024**3 or available_memory<10*1024**3 or total_memory<14*1024**3:
        raise DataError('A09 requires18GiB free disk,10GiB available and14GiB total RAM')
    return {'free_disk_bytes':free_disk,'available_memory_bytes':available_memory,'total_memory_bytes':total_memory,
        'three_model_layer_bytes':10321565265,'context_tokens_requested':16384,'max_loaded_models':1}


def verify_resources():
    import shutil
    values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))}
    return check_resource_budget(shutil.disk_usage(os.environ['RUNNER_TEMP']).free,values['MemAvailable'],values['MemTotal'])


def verify_models():
    inventory=local_json('GET','/api/tags').get('models')
    if not isinstance(inventory,list):raise DataError('Model inventory missing')
    rows={r.get('name'):r for r in inventory if isinstance(r,dict)}
    for name,value in MODELS.items():
        if rows.get(name,{}).get('digest')!=value:raise DataError('Pinned model digest mismatch: '+name)
    return {'models':[{'model':name,'digest':value,'role':'Q03_EVALUATION_CANDIDATE' if name=='qwen2.5:7b' else 'PREVIOUSLY_EXECUTED_VISION_MODEL'} for name,value in MODELS.items()],
        'promoted':False,'real_inference_completed':False,'customer_release_allowed':False}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--models',action='store_true');p.add_argument('--resources',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=verify_resources() if a.resources else verify_models() if a.models else verify_scope(Path.cwd().parents[1],os.environ)
    with a.out.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
