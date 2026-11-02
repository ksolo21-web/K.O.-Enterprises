"""Quarantined version/evaluation/rollback PREPARATION. No activation mechanism.

All review identities and supplied evaluation counts remain unauthenticated.
These functions cannot approve learning, update prompts/weights or release work.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path

from .core import DataError, validate_project
from .capture import verify_custody
from .report_learning import record_corrections, validate_bundle, _bounded_source
from .report_review_queue import digest
from .study_registry import require_registered


def _hex(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _hashes(values):
    return (isinstance(values,list) and 1<=len(values)<=1000 and all(_hex(v) for v in values)
        and values==sorted(set(values)))


def _held(record,kind,sha_key):
    if not isinstance(record,dict):raise DataError('Quarantined record required')
    clean=deepcopy(record);sha=clean.pop(sha_key,None)
    if (sha!=digest(clean) or record.get('kind')!=kind
            or any(record.get(k) is not False for k in ('training_approved','customer_release_allowed','activated'))):
        raise DataError('Altered or activating lifecycle record')
    if kind=='M3_QUARANTINED_LEARNING_CANDIDATE_V7':
        expected={'schema_version','kind','case_id','partition','version','parent_candidate_sha256',
            'reference_bundle_sha256','source_sha256','reference_text_sha256','case_media_sha256',
            'project_sha256','correction_sha256','lesson_candidates','reviewer_credentials_authenticated','status',
            'training_approved','customer_release_allowed','activated','candidate_sha256'}
        if (set(record)!=expected or record.get('schema_version')!=1
                or record.get('reviewer_credentials_authenticated') is not False
                or record.get('status')!='QUARANTINED_VERSION_NOT_ACTIVATED'
                or record.get('partition') not in ('reference','training_candidate')
                or type(record.get('version')) is not int or record['version']<1
                or not isinstance(record.get('lesson_candidates'),list) or not record['lesson_candidates']
                or any(not isinstance(x,dict) or set(x)!={'entry_id','text','evidence_snapshot','status','training_approved'}
                    or x.get('training_approved') is not False
                    or x.get('status')!='HUMAN_DECLARED_CANDIDATE_EXTERNAL_REVIEW_PENDING' for x in record['lesson_candidates'])):
            raise DataError('Invalid or falsely authenticated candidate')
        if (not isinstance(record.get('case_id'),str) or not 1<=len(record['case_id'])<=100
                or not _hashes(record.get('case_media_sha256'))
                or any(not _hex(record.get(k)) for k in ('reference_bundle_sha256','source_sha256',
                    'reference_text_sha256','project_sha256','correction_sha256'))
                or (record['version']==1 and record['parent_candidate_sha256'] is not None)
                or (record['version']>1 and not _hex(record['parent_candidate_sha256']))
                or len(record['lesson_candidates'])>256):
            raise DataError('Malformed candidate identity/source/media inventory')
        seen=set()
        for lesson in record['lesson_candidates']:
            if (not isinstance(lesson['entry_id'],str) or not 1<=len(lesson['entry_id'])<=250
                    or lesson['entry_id'] in seen or not isinstance(lesson['text'],str)
                    or not lesson['text'].strip() or len(lesson['text'])>1000
                    or not isinstance(lesson['evidence_snapshot'],dict) or not 1<=len(lesson['evidence_snapshot'])<=16
                    or any(not isinstance(k,str) or not 1<=len(k)<=100 or not _hex(v)
                        or v not in record['case_media_sha256'] for k,v in lesson['evidence_snapshot'].items())):
                raise DataError('Malformed candidate lesson/evidence snapshot')
            seen.add(lesson['entry_id'])
    elif kind=='M3_FROZEN_EVALUATION_PLAN_V7':
        expected={'kind','candidate_sha256','holdouts','labels_authenticated','status',
            'training_approved','customer_release_allowed','activated','plan_sha256'}
        if (set(record)!=expected or record.get('labels_authenticated') is not False
                or record.get('status')!='FROZEN_PLAN_NO_EVALUATION_EXECUTED'
                or not isinstance(record.get('holdouts'),list) or not 1<=len(record['holdouts'])<=128):
            raise DataError('Invalid or falsely authenticated evaluation plan')
        if not _hex(record.get('candidate_sha256')):raise DataError('Invalid evaluation candidate hash')
        ids=set();sources=set();media=set()
        for row in record['holdouts']:
            if (not isinstance(row,dict) or set(row)!={'case_id','reference_bundle_sha256','source_sha256','project_sha256','case_media_sha256'}
                    or not isinstance(row['case_id'],str) or not 1<=len(row['case_id'])<=100
                    or row['case_id'] in ids or any(not _hex(row[k]) for k in ('reference_bundle_sha256','source_sha256','project_sha256'))
                    or row['source_sha256'] in sources or not _hashes(row['case_media_sha256'])
                    or media.intersection(row['case_media_sha256'])):
                raise DataError('Malformed or duplicate frozen holdout identity/media')
            ids.add(row['case_id']);sources.add(row['source_sha256']);media.update(row['case_media_sha256'])
    return record


def _seal(record,key):
    record.update(training_approved=False,customer_release_allowed=False,activated=False)
    record[key]=digest(record)
    return record


def _media(document,root):
    validate_project(document,Path(root))
    if verify_custody(document,Path(root)):raise DataError('Case media custody failed')
    values=[]
    for media in document['media']:
        sha=media.get('sha256')
        if not isinstance(sha,str) or len(sha)!=64:raise DataError('Case media hash required')
        values.append(sha)
    if not values:raise DataError('Learning preparation needs original case media')
    return sorted(set(values))


def build_candidate(document,root,bundle,registry,reference_path,comparison,corrections,*,version,parent=None):
    validate_bundle(bundle);require_registered(bundle,registry)
    if bundle['partition']=='locked_holdout':raise DataError('Holdout cannot supply a learning candidate')
    raw=_bounded_source(Path(reference_path))
    if hashlib.sha256(raw).hexdigest()!=bundle['source']['sha256']:raise DataError('Original reference changed')
    if type(version) is not int or version<1:raise DataError('Positive candidate version required')
    if parent is None:
        if version!=1:raise DataError('First candidate must be version one')
    else:
        _held(parent,'M3_QUARANTINED_LEARNING_CANDIDATE_V7','candidate_sha256')
        if parent['case_id']!=bundle['case_id'] or parent['partition']!=bundle['partition'] or version!=parent['version']+1:
            raise DataError('Candidate lineage/version mismatch')
    if not isinstance(corrections,dict):raise DataError('Fresh corrections required')
    decisions=[{k:v for k,v in d.items() if k!='evidence_snapshot'} for d in corrections.get('decisions',[])]
    expected=record_corrections(document,Path(root),bundle,comparison,decisions,
        reviewer_id=corrections.get('reviewer_id'),registry=registry)
    if corrections!=expected:raise DataError('Corrections stale, altered or incomplete')
    if not corrections['lesson_candidates']:raise DataError('No lesson candidates supplied')
    result={'schema_version':1,'kind':'M3_QUARANTINED_LEARNING_CANDIDATE_V7','case_id':bundle['case_id'],
        'partition':bundle['partition'],'version':version,'parent_candidate_sha256':parent['candidate_sha256'] if parent else None,
        'reference_bundle_sha256':bundle['bundle_sha256'],'source_sha256':bundle['source']['sha256'],
        'reference_text_sha256':bundle['text_sha256'],'case_media_sha256':_media(document,root),
        'project_sha256':digest(document),'correction_sha256':corrections['correction_sha256'],
        'lesson_candidates':deepcopy(corrections['lesson_candidates']),
        'reviewer_credentials_authenticated':False,'status':'QUARANTINED_VERSION_NOT_ACTIVATED'}
    if hashlib.sha256(_bounded_source(Path(reference_path))).hexdigest()!=bundle['source']['sha256']:
        raise DataError('Original reference changed during candidate preparation')
    result=_seal(result,'candidate_sha256')
    return _held(result,'M3_QUARANTINED_LEARNING_CANDIDATE_V7','candidate_sha256')


def freeze_evaluation(candidate,holdouts):
    _held(candidate,'M3_QUARANTINED_LEARNING_CANDIDATE_V7','candidate_sha256')
    if not isinstance(holdouts,list) or not 1<=len(holdouts)<=128:raise DataError('Bounded locked holdouts required')
    cases=[];ids=set();sources=set();texts=set();media_seen=set(candidate['case_media_sha256'])
    for item in holdouts:
        if not isinstance(item,dict) or set(item)!={'bundle','registry','document','root','reference_path'}:
            raise DataError('Holdout case source fields required')
        b=item['bundle'];validate_bundle(b);require_registered(b,item['registry'])
        if (b['partition']!='locked_holdout' or b['case_id']==candidate['case_id'] or b['case_id'] in ids
                or b['source']['sha256']==candidate['source_sha256'] or b['source']['sha256'] in sources
                or b['text_sha256']==candidate['reference_text_sha256'] or b['text_sha256'] in texts):
            raise DataError('Holdout identity/source/text leaks or duplicates training')
        if item['document'].get('project_id')!=b['case_id']:raise DataError('Holdout project/case mismatch')
        if hashlib.sha256(_bounded_source(Path(item['reference_path']))).hexdigest()!=b['source']['sha256']:
            raise DataError('Holdout original reference changed')
        media=set(_media(item['document'],item['root']))
        if media & media_seen:raise DataError('Original media reused between training or holdout cases')
        ids.add(b['case_id']);sources.add(b['source']['sha256']);texts.add(b['text_sha256']);media_seen|=media
        cases.append({'case_id':b['case_id'],'reference_bundle_sha256':b['bundle_sha256'],
            'source_sha256':b['source']['sha256'],'project_sha256':digest(item['document']),
            'case_media_sha256':sorted(media)})
    return _seal({'kind':'M3_FROZEN_EVALUATION_PLAN_V7','candidate_sha256':candidate['candidate_sha256'],
        'holdouts':cases,'labels_authenticated':False,'status':'FROZEN_PLAN_NO_EVALUATION_EXECUTED'},'plan_sha256')


def capture_evaluation(plan,results):
    _held(plan,'M3_FROZEN_EVALUATION_PLAN_V7','plan_sha256')
    if not isinstance(results,list) or len(results)!=len(plan['holdouts']):raise DataError('Every holdout needs exactly one result')
    ids={h['case_id'] for h in plan['holdouts']};seen=set();clean=[]
    for row in results:
        if not isinstance(row,dict) or set(row)!={'case_id','true_positives','false_positives','false_negatives','critical_false_negatives','review_record_sha256'}:
            raise DataError('Invalid evaluation result fields')
        case=row['case_id']
        if case not in ids or case in seen:raise DataError('Unknown/duplicate holdout result')
        seen.add(case)
        if any(type(row[k]) is not int or not 0<=row[k]<=100000 for k in ('true_positives','false_positives','false_negatives','critical_false_negatives')):
            raise DataError('Invalid evaluation counts')
        if row['critical_false_negatives']>row['false_negatives']:raise DataError('Critical misses exceed total misses')
        sha=row['review_record_sha256']
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise DataError('Review receipt hash required')
        clean.append(deepcopy(row))
    return _seal({'kind':'M3_UNVERIFIED_EVALUATION_CAPTURE_V7','plan_sha256':plan['plan_sha256'],
        'candidate_sha256':plan['candidate_sha256'],'results':clean,'labels_authenticated':False,
        'real_evaluation_execution_verified':False,'promotion_eligible':False,
        'status':'DECLARED_RESULTS_REQUIRE_AUTHENTICATION'},'evaluation_sha256')


def prepare_rollback(current,previous):
    _held(current,'M3_QUARANTINED_LEARNING_CANDIDATE_V7','candidate_sha256')
    _held(previous,'M3_QUARANTINED_LEARNING_CANDIDATE_V7','candidate_sha256')
    if (current['parent_candidate_sha256']!=previous['candidate_sha256']
            or current['case_id']!=previous['case_id'] or current['version']!=previous['version']+1):
        raise DataError('Rollback target is not the immediate predecessor')
    return _seal({'kind':'M3_QUARANTINED_ROLLBACK_PLAN_V7','from_candidate_sha256':current['candidate_sha256'],
        'to_candidate_sha256':previous['candidate_sha256'],'restored_candidate':deepcopy(previous),
        'runtime_changed':False,'status':'PLAN_ONLY_NO_ACTIVE_LEARNING_STATE'},'rollback_sha256')


def main(argv=None):
    import argparse
    from .report_review_queue import _read_json,_write_new
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('candidate')
    for key in ('project','reference','registry','source-reference','comparison','corrections'):
        c.add_argument('--'+key,type=Path,required=True)
    c.add_argument('--version',type=int,required=True);c.add_argument('--parent',type=Path)
    e=sub.add_parser('freeze-evaluation');e.add_argument('--candidate',type=Path,required=True);e.add_argument('--holdouts',type=Path,required=True)
    e=sub.add_parser('capture-evaluation');e.add_argument('--plan',type=Path,required=True);e.add_argument('--results',type=Path,required=True)
    e=sub.add_parser('rollback-plan');e.add_argument('--current',type=Path,required=True);e.add_argument('--previous',type=Path,required=True)
    for q in sub.choices.values():q.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='candidate':
            result=build_candidate(_read_json(a.project),a.project.parent,_read_json(a.reference),_read_json(a.registry),
                a.source_reference,_read_json(a.comparison),_read_json(a.corrections),version=a.version,
                parent=_read_json(a.parent) if a.parent else None)
        elif a.command=='freeze-evaluation':
            rows=_read_json(a.holdouts)
            if not isinstance(rows,list) or not 1<=len(rows)<=128:raise DataError('Invalid holdout path list')
            cases=[]
            for row in rows:
                if not isinstance(row,dict) or set(row)!={'reference','registry','project','source_reference'}:
                    raise DataError('Invalid holdout path fields')
                cases.append({'bundle':_read_json(Path(row['reference'])),'registry':_read_json(Path(row['registry'])),
                    'document':_read_json(Path(row['project'])),'root':Path(row['project']).parent,'reference_path':Path(row['source_reference'])})
            result=freeze_evaluation(_read_json(a.candidate),cases)
        elif a.command=='capture-evaluation':result=capture_evaluation(_read_json(a.plan),_read_json(a.results))
        else:result=prepare_rollback(_read_json(a.current),_read_json(a.previous))
        _write_new(a.out,result)
        print(__import__('json').dumps({'status':result['status'],'activated':False,'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,UnicodeError):
        print('{"status":"BLOCKED","activated":false,"training_approved":false,"customer_release_allowed":false}')
        return 2


if __name__=='__main__':raise SystemExit(main())
