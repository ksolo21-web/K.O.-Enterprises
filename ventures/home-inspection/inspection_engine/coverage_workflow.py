"""Assigned safety/specialty work, bound to the existing evidence/review ledger.

Tasks are not findings. Visual review never completes a physical safety test.
Required tasks are rebuilt from scope, catalogs and case media, not model output.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import re

from .core import DataError,SYSTEM_NAME
from .coverage_expansion import specialty_work_orders
from .hazard_sweep import load_hazard_sweep

SPECIALTY_AREAS={
    'FIREPLACE_HEARTH':{'fireplace','hearth','chimney'},
    'GARAGE_DOOR':{'garage','garage_door'},
    'COMMERCIAL_FIRE_LIFE_SAFETY':{'commercial_fire','commercial_egress','life_safety'},
}
AREA_ALIASES={area:('interior',) for areas in SPECIALTY_AREAS.values() for area in areas}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def inspection_scope(document):
    prop=document['property']
    aliases={'residential':'residential','residential_one_two_family':'residential',
             'commercial':'commercial','commercial_general':'commercial','commercial_pca':'commercial'}
    building=aliases.get(prop.get('building_type'))
    declared=prop.get('inspection_scope')
    if declared not in (None,'unverified','residential','commercial'):
        raise DataError('Unknown inspection scope')
    if declared in ('residential','commercial') and building and declared!=building:
        raise DataError('Inspection scope conflicts with building type')
    if prop.get('building_type') not in (None,'unverified',*aliases):
        raise DataError('Building type requires explicit supported scope classification')
    return building or (declared if declared in ('residential','commercial') else None)


def build_work_orders(document):
    """Canonical whole-case plan. A missing photo is an open assigned task."""
    from .agents import SYSTEM_OWNER,AREA_SYSTEMS
    scope=inspection_scope(document)
    if scope is None:raise DataError('Explicit residential/commercial scope required for coverage work')
    photos=[m for m in document['media'] if m['kind']=='photo']
    hazards=load_hazard_sweep();specialties=specialty_work_orders(scope)
    from .inspection_policy import policy_digest
    policy_sha=policy_digest()
    tasks=[]
    for row in hazards['topics']:
        system=row['system']
        evidence=[m['id'] for m in photos if system in AREA_SYSTEMS.get(m.get('area'),())]
        tasks.append({'id':'HAZARD:'+system,'kind':'hazard_sweep','system':system,
            'assigned_to':SYSTEM_OWNER[system],'title':SYSTEM_NAME[system]+' visual hazard and coverage check',
            'instructions':deepcopy(row),'evidence_ids':evidence})
    for row in specialties['tasks']:
        evidence=[m['id'] for m in photos if m.get('area') in SPECIALTY_AREAS[row['id']]]
        tasks.append({'id':'SPECIALTY:'+row['id'],'kind':'specialty','system':'interior',
            'assigned_to':'T05','title':row['title'],'instructions':deepcopy(row),'evidence_ids':evidence})
    media={m['id']:m for m in document['media']}
    for task in tasks:
        task.update(scope=scope,project_id=document['project_id'],
                    catalog_sha256=digest(task['instructions']),policy_sha256=policy_sha,
                    inspection_date=document['property'].get('inspection_date'),physical_check_required=True,
                    state='OPEN_INSPECTOR_FOLLOWUP_REQUIRED' if task['evidence_ids'] else 'EVIDENCE_MISSING')
        task['evidence_snapshot']={ident:{'sha256':media[ident].get('sha256'),
            'source_video_id':media[ident].get('derived_from_id'),
            'source_video_sha256':media.get(media[ident].get('derived_from_id'),{}).get('sha256'),
            'timestamp_seconds':media[ident].get('timestamp_seconds')} for ident in task['evidence_ids']}
        task['task_sha256']=digest(task)
    return {'version':1,'scope':scope,'project_id':document['project_id'],'tasks':tasks,
            'plan_sha256':digest(tasks),'tasks_are_findings':False,'customer_release_allowed':False}


def task_ids_for(document,system,evidence_id):
    if inspection_scope(document) is None:return []
    return [t['id'] for t in build_work_orders(document)['tasks']
            if t['system']==system and evidence_id in t['evidence_ids']]


def attach_plan(document):
    changed=deepcopy(document)
    changed['coverage_work_orders']=build_work_orders(changed)
    tasks=changed['coverage_work_orders']['tasks']
    for section in ('observations','findings'):
        for claim in changed[section]:
            claim['coverage_task_ids']=sorted(t['id'] for t in tasks if t['system']==claim['system']
                and set(t['evidence_ids']) & set(claim['evidence_ids']))
    return changed


def ledger_tasks(document):
    if inspection_scope(document) is None:return []
    plan=build_work_orders(document)
    return [{'entry_id':'coverage:'+task['id'],'type':'coverage_task','system':task['system'],
        'feature_code':None,'description':task['title'],'location':'Whole-case '+task['scope']+' scope',
        'bbox':None,'evidence_ids':list(task['evidence_ids']),'zoom_view_ids':[],
        'review':'review_pending','origin':'coverage_work_order','component_id':None,
        'task_id':task['id'],'task_sha256':task['task_sha256'],'task_state':task['state'],
        'assigned_to':task['assigned_to'],'physical_check_required':True} for task in plan['tasks']]


def task_dispositions(document,technical_review):
    """Verify actual per-task/per-photo Q02 records; absence is not a model review."""
    if inspection_scope(document) is None:return {}
    plan=build_work_orders(document);items=technical_review.get('coverage_items',[])
    if not isinstance(items,list) or any(not isinstance(i,dict) for i in items):
        raise DataError('Q02 coverage review records must be a list of objects')
    result={}
    for task in plan['tasks']:
        ident='coverage:'+task['id']
        if not task['evidence_ids']:
            result[ident]=[{'decision':'insufficient_evidence',
                'reason':'Assigned coverage work has no case photo evidence',
                'missing_evidence':'Capture safely accessible views and obtain qualified inspector coverage',
                'review_kind':'DETERMINISTIC_MISSING_EVIDENCE_NOT_MODEL_REVIEW'}]
            continue
        matched=[]
        for media_id in task['evidence_ids']:
            expected_hash=task['evidence_snapshot'][media_id]['sha256']
            if not isinstance(expected_hash,str) or not re.fullmatch('[0-9a-f]{64}',expected_hash):
                raise DataError('Coverage reviews require recorded evidence hashes')
            matches=[i for i in items if i.get('task_id')==task['id']
                     and i.get('task_sha256')==task['task_sha256'] and i.get('source_media_id')==media_id
                     and i.get('source_sha256')==expected_hash and i.get('review_kind')=='MODEL_VISUAL_TASK_REVIEW']
            if len(matches)!=1:raise DataError('Every coverage task/photo needs one source-matched Q02 assessment')
            item=matches[0]
            from .critic import _review_response
            clean=_review_response({key:item.get(key) for key in ('decision','reason','missing_evidence')})
            matched.append(dict(clean,review_kind='MODEL_VISUAL_TASK_REVIEW'))
        result[ident]=matched
    expected_pairs={(t['id'],ident) for t in plan['tasks'] for ident in t['evidence_ids']}
    if any((i.get('task_id'),i.get('source_media_id')) not in expected_pairs for i in items):
        raise DataError('Unknown task/photo in Q02 coverage review')
    return result


def report_holds(document):
    has_model=bool(document.get('agent_workflow')) or any(i.get('model_proposal') for s in ('observations','findings') for i in document[s])
    if not has_model and 'coverage_work_orders' not in document:return []
    try:scope=inspection_scope(document)
    except DataError:return ['Coverage work scope is invalid or conflicting']
    if scope is None:return ['Inspection scope and assigned hazard/specialty work plan require confirmation']
    expected=build_work_orders(document)
    holds=[]
    if document.get('coverage_work_orders')!=expected:
        holds.append('Assigned coverage work plan is missing or stale')
    holds.extend(f"Coverage {t['id']}: "+('source views missing; ' if not t['evidence_ids'] else '')+
                 'qualified inspector checks remain open' for t in expected['tasks'])
    return holds
