"""Schema-aware writer input compaction; no knowledge summarization or inference.

The authoritative response schema still travels unchanged to the provider.
Only JSON serialization and explicitly redundant operational metadata are reduced.
Legacy providers receive the original prompt. Unsupported schema evolution fails
closed instead of silently losing response guidance.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from .core import DataError

VERSION=1
TASK_METADATA={'catalog_sha256','policy_sha256','evidence_ids','evidence_snapshot'}
JSON_LABELS={'OBSERVATION_MEMORY_JSON','UNRECORDED_FEATURE_TASKS_JSON','ASSIGNED_COVERAGE_TASKS_JSON',
    'EVIDENCE_CONTEXT_JSON','MANDATORY_SCOPE','GOVERNED_MICHIGAN_SOURCE_PACKET_JSON','GOVERNED_CASE_RESEARCH_V6_JSON'}


def compact_json(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False)

def digest(value):return hashlib.sha256(compact_json(value).encode()).hexdigest()

def text_digest(value):return hashlib.sha256(value.encode()).hexdigest()


def schema_guide(schema):
    """Complete operational guidance for the supported specialist schema shape."""
    def require(condition):
        if not condition:raise DataError('Unsupported specialist schema shape for compact input')
    require(isinstance(schema,dict) and set(schema)=={'type','properties','required','additionalProperties'})
    require(schema['type']=='object' and schema['additionalProperties'] is False and set(schema['required'])=={'candidates','requests'})
    require(set(schema['properties'])=={'candidates','requests'})
    cand=schema['properties']['candidates'];req=schema['properties']['requests']
    for row in (cand,req):require(set(row)=={'type','maxItems','items'} and row['type']=='array' and set(row['items'])=={'anyOf'})
    variants=cand['items']['anyOf'];require(isinstance(variants,list) and bool(variants))
    common=None;systems={};pairs=set()
    for branch in variants:
        require(set(branch)=={'type','properties','required','additionalProperties'} and branch['type']=='object' and branch['additionalProperties'] is False)
        props=branch['properties'];kind=props.get('type',{}).get('enum');system=props.get('system',{}).get('enum')
        require(kind in (['feature'],['potential_concern']) and isinstance(system,list) and len(system)==1)
        require((system[0],kind[0]) not in pairs);pairs.add((system[0],kind[0]))
        require(props['type']=={'type':'string','enum':kind} and props['system']=={'type':'string','enum':system})
        base={'description','status','location','bbox'}
        require(set(props)==base|{'type','system'}|({'feature_code'} if kind==['feature'] else set()))
        require(set(branch['required'])=={'type','system','description','status'}|({'feature_code'} if kind==['feature'] else set()))
        selected={key:props[key] for key in base}
        if common is None:common=selected
        require(common==selected)
        if kind==['feature']:
            require(set(props['feature_code'])=={'type','enum'} and props['feature_code']['type']=='string')
            require(system[0] not in systems);systems[system[0]]=props['feature_code']['enum']
    require(pairs=={(s,k) for s in systems for k in ('feature','potential_concern')})
    for key in ('description','location'):
        require(set(common[key])=={'type','minLength','maxLength'} and common[key]['type']=='string')
    require(set(common['status'])=={'type','enum'} and common['status']['type']=='string')
    box=common['bbox'];require(set(box)=={'type','items','minItems','maxItems'} and box['type']=='array')
    require(box['minItems']==box['maxItems']==4 and box['items']=={'type':'number','minimum':0,'maximum':1})
    action_kinds=[];video_bounds=None
    for branch in req['items']['anyOf']:
        require(set(branch)=={'type','properties','required','additionalProperties'} and branch['type']=='object' and branch['additionalProperties'] is False)
        props=branch['properties'];kind=props.get('kind',{}).get('enum')
        require(kind in (['zoom'],['video_still']) and props['kind']=={'type':'string','enum':kind})
        require(kind[0] not in action_kinds);action_kinds.append(kind[0])
        if kind==['zoom']:
            require(set(props)=={'kind','bbox'} and props['bbox']==box and set(branch['required'])=={'kind','bbox'})
        else:
            number=props.get('timestamp_seconds',{})
            require(set(props)=={'kind','timestamp_seconds'} and set(branch['required'])=={'kind','timestamp_seconds'})
            require(set(number)=={'type','minimum','exclusiveMaximum'} and number['type']=='number')
            video_bounds=(number['minimum'],number['exclusiveMaximum'])
    require('zoom' in action_kinds)
    desc,loc=common['description'],common['location']
    guide=(f'OUTPUT_GUIDE: Full JSON schema is supplied separately as provider response-format. '
        f'Return only candidates (max {cand["maxItems"]}) and requests (max {req["maxItems"]}); arrays may be empty. '
        f'Candidate requires type,system,description ({desc["minLength"]}-{desc["maxLength"]} chars),'
        f'status ({"|".join(common["status"]["enum"])}). '
        'feature also requires feature_code from its delegated system map; potential_concern forbids feature_code. '
        f'Optional location is {loc["minLength"]}-{loc["maxLength"]} chars; optional bbox is four numbers 0..1 in current-view coordinates. '
        'Omit absent optional fields. Request requires kind=zoom plus bbox')
    if video_bounds is not None:guide+=f', or kind=video_still plus timestamp_seconds with {video_bounds[0]} <= t < {video_bounds[1]}'
    guide+='. No extra keys in response, candidates or requests.'
    return guide,systems


def project_task(task):
    if not isinstance(task,dict):raise DataError('Assigned task card must be an object')
    for field in ('id','task_sha256','instructions','scope','state','physical_check_required'):
        if field not in task:raise DataError('Incomplete assigned task card')
    # Unknown/new fields remain. Only this explicit operational metadata set drops.
    return {k:deepcopy(v) for k,v in task.items() if k not in TASK_METADATA}


def compact_writer_prompt(prompt,schema):
    if not isinstance(prompt,str) or len(prompt.encode())>100_000:raise DataError('Unbounded original writer input')
    try:guide,_=schema_guide(schema)
    except (TypeError,KeyError,IndexError,ValueError) as exc:raise DataError('Unsupported specialist schema shape') from exc
    rows=[];schema_count=0;labels_seen=set();task_receipt=None;json_before={};json_after={}
    for line in prompt.splitlines(keepends=True):
        body=line.rstrip('\r\n');ending=line[len(body):];label,separator,payload=body.partition(': ')
        is_json=label in JSON_LABELS or label.startswith('EXPERT_DOMAIN ')
        if label=='OUTPUT_JSON_SCHEMA':
            schema_count+=1
            try:original=json.loads(payload)
            except ValueError as exc:raise DataError('Invalid embedded specialist schema') from exc
            if original!=schema:raise DataError('Prompt schema differs from provider schema')
            rows.append(guide+ending)
            rows.append('PROVIDER_SCHEMA_SHA256: '+digest(schema)+ending)
            continue
        if separator and is_json:
            if label in labels_seen:raise DataError('Repeated structured input label')
            labels_seen.add(label)
            try:value=json.loads(payload)
            except ValueError as exc:raise DataError('Invalid structured writer input '+label) from exc
            json_before[label]=deepcopy(value)
            if label=='ASSIGNED_COVERAGE_TASKS_JSON':
                if not isinstance(value,list):raise DataError('Assigned task cards must be a list')
                canonical=value;value=[project_task(t) for t in canonical]
                task_receipt={'canonical_task_cards':deepcopy(canonical),'full_task_cards_sha256':digest(canonical),'prompt_task_cards_sha256':digest(value),
                    'omitted_operational_fields':sorted({k for t in canonical for k in t if k in TASK_METADATA})}
            json_after[label]=deepcopy(value);rows.append(label+': '+compact_json(value)+ending)
        else:rows.append(line)
    if schema_count!=1:raise DataError('Exactly one embedded schema required before compaction')
    result=''.join(rows)
    invariant_labels=[key for key in json_before if key!='ASSIGNED_COVERAGE_TASKS_JSON']
    if any(json_before[key]!=json_after[key] for key in invariant_labels):raise DataError('Structured knowledge/memory changed during compaction')
    receipt={'version':VERSION,'mode':'SCHEMA_AWARE_WRITER_COMPACT','original_prompt_sha256':text_digest(prompt),
        'prompt_sha256':text_digest(result),'provider_schema_sha256':digest(schema),
        'original_characters':len(prompt),'characters':len(result),'original_bytes':len(prompt.encode()),'bytes':len(result.encode()),
        'saved_bytes':len(prompt.encode())-len(result.encode()),'knowledge_memory_context_values_preserved':True,'task_instructions_preserved':True,
        'non_json_knowledge_text_preserved':True,'task_projection':task_receipt,
        'token_counts_measured':False,'latency_benchmarked':False,'observation_quality_benchmarked':False,
        'customer_release_allowed':False}
    return result,receipt
