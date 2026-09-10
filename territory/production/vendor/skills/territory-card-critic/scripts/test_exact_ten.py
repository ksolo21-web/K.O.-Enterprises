#!/usr/bin/env python3
"""Replay the full gate using a real valid report and isolated mutations."""
import argparse,copy,json,shutil,tempfile
from pathlib import Path
from critic_evidence import gate
p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('review',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
original=json.loads(a.review.read_text());results=[]
with tempfile.TemporaryDirectory(prefix='territory-score-replay-') as tmp:
 root=Path(tmp)
 for source in a.review.parent.iterdir():
  if source.is_file(): (root/source.name).symlink_to(source.resolve())
 target=root/'mutated-review.json'
 cases=['accept_real_10','reject_9_99','reject_rounds_to_10','reject_missing_evidence']
 for name in cases:
  report=copy.deepcopy(original)
  if name=='reject_9_99':
   for category in report['categories'].values():category['score']=9.99
   report['overall_score']=9.99;report['release_ready']=False
  elif name=='reject_rounds_to_10':
   report['categories']['export']['score']=9.999
   report['overall_score']=10;report['release_ready']=False
  elif name=='reject_missing_evidence':
   report.pop('branch_color_review',None);report['overall_score']=8;report['release_ready']=False
  target.write_text(json.dumps(report));actual=gate(a.pdf,target)
  expected=name=='accept_real_10'
  results.append({'case':name,'expected_release_ready':expected,'actual':actual,'passed':actual['release_ready'] is expected})
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'source_report':str(a.review.resolve()),'source_pdf':str(a.pdf.resolve()),'results':results,'all_passed':all(x['passed'] for x in results)},indent=2)+'\n')
print(a.output.read_text());raise SystemExit(0 if all(x['passed'] for x in results) else 1)
