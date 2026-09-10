#!/usr/bin/env python3
"""Run project and independent exact-10 critic gates; neither substitutes for the other."""
import argparse, json, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('project',type=Path);p.add_argument('pdf',type=Path)
p.add_argument('review',type=Path);p.add_argument('--critic-script',type=Path,required=True)
a=p.parse_args()
results=[]
for command in ([sys.executable,str(Path(__file__).with_name('validate_project.py')),str(a.project)], [sys.executable,str(a.critic_script),'gate',str(a.pdf),str(a.review)]):
 result=subprocess.run(command,capture_output=True,text=True)
 results.append({'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
report=json.loads(a.review.read_text())
scores=report.get('categories',{})
exact=all(type(scores.get(k,{}).get('score')) in (int,float) and scores[k]['score']==10 for k in ('preservation','geography','labels','template','export')) and report.get('overall_score')==10
ready=exact and all(x['returncode']==0 for x in results)
print(json.dumps({'release_ready':ready,'every_category_exactly_10':exact,'gates':results},indent=2))
sys.exit(0 if ready else 1)
