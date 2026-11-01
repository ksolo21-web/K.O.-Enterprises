"""A10 fixed nonce for changed-input evaluation; no authority or deadline expansion."""
import argparse,json,os
from pathlib import Path
from .a09_scope import verify_scope,verify_models,verify_resources
from inspection_engine.input_compaction import VERSION

AUTH='OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A10'
APPROVAL='ventures/home-inspection/docs/ONE_TIME_SYNTHETIC_TRIAL_APPROVAL_2026-10-31_A10.md'


def scope(root,env):
    result=verify_scope(root,env,auth_id=AUTH,approval_path=APPROVAL)
    result['writer_input_compaction_version']=VERSION
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--models',action='store_true');p.add_argument('--resources',action='store_true')
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=verify_resources() if a.resources else verify_models() if a.models else scope(Path.cwd().parents[1],os.environ)
    with a.out.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
