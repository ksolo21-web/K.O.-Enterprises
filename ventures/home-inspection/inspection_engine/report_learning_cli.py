"""Explicit local study commands. Outputs must be new, private case files."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from .core import DataError,validate_project
from .report_learning import import_reference,prepare_comparison,record_corrections
from .study_registry import empty_registry,register_bundle,validate_registry


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>5_000_000:
        raise DataError('Study JSON must be a regular local file below 5MB')
    with path.open('rb') as stream:raw=stream.read(5_000_001)
    if len(raw)>5_000_000:raise DataError('Study JSON exceeds 5MB limit')
    return json.loads(raw.decode('utf-8'))


def _write_new(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description='Local unverified report study; never automatic training')
    commands=parser.add_subparsers(dest='command',required=True)
    imp=commands.add_parser('import');imp.add_argument('source',type=Path)
    imp.add_argument('--case-id',required=True);imp.add_argument('--partition',choices=['reference','training_candidate','locked_holdout'],required=True)
    imp.add_argument('--authorized-use',action='store_true');imp.add_argument('--consented',action='store_true')
    for op in ('compare','correct'):
        p=commands.add_parser(op);p.add_argument('project',type=Path);p.add_argument('--reference',type=Path,required=True)
        if op=='compare':p.add_argument('--annotations',type=Path,required=True)
        else:
            p.add_argument('--comparison',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True)
            p.add_argument('--reviewer-id',required=True)
    for p in (imp,*[commands.choices[x] for x in ('compare','correct')]):
        p.add_argument('--out',type=Path,required=True)
        p.add_argument('--registry',type=Path,required=True,help='Same private registry for all study cases')
    args=parser.parse_args()
    try:
        if args.out.is_symlink() or args.out.exists():raise DataError('Refusing to overwrite existing study output')
        if args.registry.resolve()==args.out.resolve():raise DataError('Registry and output paths must differ')
        if args.registry.is_symlink():raise DataError('Registry may not be a symlink')
        registry=_read(args.registry) if args.registry.exists() else empty_registry()
        validate_registry(registry)
        if args.command=='import':
            result=import_reference(args.source,case_id=args.case_id,partition=args.partition,
                authorized_use=args.authorized_use,consented=args.consented)
            changed_registry=register_bundle(result,registry)
        else:
            document=validate_project(_read(args.project),args.project.resolve().parent);bundle=_read(args.reference)
            if args.command=='compare':result=prepare_comparison(document,bundle,_read(args.annotations),registry=registry)
            else:result=record_corrections(document,args.project.resolve().parent,bundle,_read(args.comparison),
                _read(args.decisions),reviewer_id=args.reviewer_id,registry=registry)
        # Exclusive output creation; import holds a same-registry lock and checks for races.
        if args.command=='import':
            lock=args.registry.with_name(args.registry.name+'.lock')
            with lock.open('x'):
                try:
                    current=_read(args.registry) if args.registry.exists() else empty_registry()
                    if current!=registry:raise DataError('Study registry changed concurrently; retry import')
                    _write_new(args.out,result)
                    try:
                        fd,name=tempfile.mkstemp(prefix='.study-',dir=args.registry.parent)
                        try:
                            with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(json.dumps(changed_registry,indent=2)+'\n')
                            os.replace(name,args.registry)
                        finally:
                            if os.path.exists(name):os.unlink(name)
                    except Exception:
                        args.out.unlink();raise
                finally:lock.unlink()
        else:_write_new(args.out,result)
    except (DataError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'training_approved':False,'customer_release_allowed':False}))
        raise SystemExit(2) from None
    print(json.dumps({'status':result.get('status',result.get('kind')),'output':str(args.out),
        'training_approved':False,'customer_release_allowed':False}))


if __name__=='__main__':main()
