"""Resumable bounded build/repair/capture queue. Missing evidence never becomes a pass."""
from __future__ import annotations
import hashlib,json,re,shutil,time
from pathlib import Path
import engine,repair

class QueueError(engine.GateError):pass

def run(job:Path,output:Path,budget_seconds=1800) -> dict:
    engine.private_guard();integrity=engine.verify_skills();plan=engine.json_read(job/'job.json')
    if plan.get('schema_version')!=1 or isinstance(plan.get('schema_version'),bool):raise QueueError('unsupported job schema')
    cards=plan.get('cards')
    if not isinstance(cards,list) or not 1<=len(cards)<=100:raise QueueError('job requires 1-100 cards')
    ids=[c.get('id') for c in cards]
    if any(not isinstance(v,str) or not re.fullmatch(r'\d{3}[A-Za-z]*',v) for v in ids) or len(set(ids))!=len(ids):raise QueueError('invalid or duplicate territory identity')
    if output.exists():raise QueueError('fresh output required; checkpoints are inputs, not overwritten evidence')
    output.mkdir(parents=True);start=time.monotonic();records=[]
    def save():
        report={'schema_version':1,'job_sha256':engine.sha(job/'job.json'),'source_integrity':integrity,'cards':records,'required':len(cards),'processed':len(records),'released':sum(r['status']=='released' for r in records),'release_ready':False,'completion':'partial' if len(records)<len(cards) else 'processed_not_approved'}
        engine.json_write(output/'CHECKPOINT.json',report);return report
    for card in cards:
        if time.monotonic()-start>budget_seconds:break
        record={'id':card['id'],'status':'blocked','mandatory_review':'unverified'}
        folder=output/card['id'];folder.mkdir()
        try:
            recipe_path=engine.pinned(job,card['recipe']);action=card.get('action');candidate=folder/f"Territory - {card['id']}.pdf"
            if action=='build':record['build']=engine.build(recipe_path,candidate)
            elif action=='repair':
                result=repair.repair(recipe_path,folder/'rounds');record['repair']=result
                if result['selected'] is None:raise QueueError('authorized alternatives exhausted without a qualifying candidate')
                source=folder/'rounds'/result['selected']['file'];shutil.copyfile(source,candidate)
                if engine.sha(source)!=engine.sha(candidate):raise QueueError('candidate identity changed during final naming')
            else:raise QueueError('unsupported action; never execute code supplied inside a job')
            record['export']=engine.inspect_pdf(candidate)
            record['capture']=engine.capture(candidate,folder/'final-evidence')
            record['status']='candidate_requires_independent_review'
            record['mandatory_review']='exact original release gates plus qualified independent source/candidate review still required'
            # Model calibration does not qualify real cards. Do not forge the
            # original review report, skip geographic checks, or create releases.
        except Exception as error:
            # This detailed record remains inside the encrypted private result.
            record.update(status='blocked',error=type(error).__name__+': '+str(error))
        records.append(record);save()
    return save()
