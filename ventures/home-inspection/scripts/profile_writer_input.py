"""Profile a saved writer request OFFLINE. No model/API invocation or token estimate."""
from copy import deepcopy
import argparse,json,shutil,hashlib
from pathlib import Path
from inspection_engine.core import DataError,sha256,safe_path
from inspection_engine.input_compaction import compact_writer_prompt,digest,text_digest


def profile_request(request_path,out_dir):
    request_path=Path(request_path);out_dir=Path(out_dir)
    if out_dir.exists() or out_dir.is_symlink():raise DataError('Refusing to overwrite an input profile')
    if request_path.is_symlink() or not request_path.is_file():raise DataError('Saved request must be a regular local file')
    with request_path.open('rb') as stream:raw=stream.read(200_001)
    if len(raw)>200_000:raise DataError('Saved request exceeds200KB limit')
    record=json.loads(raw)
    if record.get('role')!='writer':raise DataError('Writer request required')
    image_name=record.get('image_path')
    if not isinstance(image_name,str) or Path(image_name).name!=image_name:raise DataError('Expected saved image filename only')
    image=safe_path(request_path.resolve().parent,image_name)
    if not image.is_file() or image.is_symlink() or image.stat().st_size>20_000_000:raise DataError('Invalid saved input image')
    if sha256(image)!=record.get('image_sha256'):raise DataError('Saved input image hash mismatch')
    if text_digest(record['prompt'])!=record.get('prompt_sha256') or digest(record['generation_schema'])!=record.get('generation_schema_sha256'):
        raise DataError('Saved request prompt/schema hash mismatch')
    prompt,receipt=compact_writer_prompt(record['prompt'],record['generation_schema'])
    fields={'role','model','image_path','image_sha256','prompt','prompt_sha256','generation_schema','generation_schema_sha256'}
    updated={k:deepcopy(v) for k,v in record.items() if k in fields}
    updated.update(prompt=prompt,prompt_sha256=text_digest(prompt),execution_kind='OFFLINE_NOT_EXECUTED',
        model_invocations=0,source_request_sha256=hashlib.sha256(raw).hexdigest(),
        source_request_metadata={k:deepcopy(v) for k,v in record.items() if k not in fields})
    receipt.update(source_request_sha256=hashlib.sha256(raw).hexdigest(),model=record['model'],
        image_sha256=record['image_sha256'],image_bytes_unchanged=True,response_schema_unchanged=True,
        model_invocations=0,source_request_unchanged=True)
    out_dir.mkdir(parents=True,mode=0o700)
    shutil.copyfile(image,out_dir/image_name)
    if sha256(out_dir/image_name)!=record['image_sha256']:raise DataError('Copied input image changed')
    for name,value in [('optimized_request.json',updated),('input_profile.json',receipt)]:
        with (out_dir/name).open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser(description='Offline writer input profiler; no inference')
    p.add_argument('--request',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    try:r=profile_request(a.request,a.out_dir)
    except (DataError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'model_invocations':0}));return 2
    print(json.dumps({k:v for k,v in r.items() if k!='task_projection'},indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
