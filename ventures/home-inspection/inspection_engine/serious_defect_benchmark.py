"""Blind, real-case serious-defect evaluation; fail closed on label provenance.

This evaluates model predictions against qualified, human-adjudicated holdout
observations. It neither trains models nor implies exhaustive defect detection.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date
import hashlib
import re

HEX = re.compile(r'[0-9a-f]{64}\Z')
SEVERITY = {'critical','major','moderate','minor'}
SYSTEMS = {'site','foundation','subfloor','framing','exterior','roof','attic','interior',
           'electrical','plumbing','water_heating','hvac','crawlspace'}

class BenchmarkBlock(ValueError): pass


def validate_real_holdout(cases: list[dict], detections:list[dict]) -> None:
    if not isinstance(cases,list) or not cases:raise BenchmarkBlock('Real inspector-labeled cases required')
    if not isinstance(detections,list):raise BenchmarkBlock('Detections list required')
    known=set(); labels=set()
    for c in cases:
        if not isinstance(c,dict) or not isinstance(c.get('case_id'),str) or c['case_id'] in known:
            raise BenchmarkBlock('Unique labeled case IDs required')
        known.add(c['case_id'])
        if c.get('synthetic') is not False or c.get('consented_for_evaluation') is not True:
            raise BenchmarkBlock('Real, specifically consented evaluation cases required')
        if not HEX.fullmatch(c.get('evidence_sha256','')):
            raise BenchmarkBlock('Holdout evidence file checksum required')
        if c.get('partition')!='locked_holdout' or c.get('training_overlap') is not False:
            raise BenchmarkBlock('Evaluation cannot use training or unlocked cases')
        labeler=c.get('qualified_labeler_id');adjudicator=c.get('independent_adjudicator_id')
        if not isinstance(labeler,str) or not isinstance(adjudicator,str) or not labeler.strip() or not adjudicator.strip() or labeler==adjudicator:
            raise BenchmarkBlock('Qualified independent review identities required')
        if c.get('scope') not in {'residential','commercial'} or c.get('jurisdiction')!='MI':
            raise BenchmarkBlock('Michigan inspection scope required')
        if not isinstance(c.get('labels'),list):raise BenchmarkBlock('Human adjudicated labels required')
        for l in c['labels']:
            if not isinstance(l,dict) or l.get('status')!='adjudicated' or l.get('severity') not in SEVERITY or l.get('system') not in SYSTEMS:
                raise BenchmarkBlock('Unreviewed defect label or invalid system/severity')
            lid=l.get('label_id')
            if not isinstance(lid,str) or (c['case_id'],lid) in labels:
                raise BenchmarkBlock('Duplicate or invalid label ID')
            labels.add((c['case_id'],lid))
    seen=set()
    for d in detections:
        if not isinstance(d,dict) or d.get('case_id') not in known:
            raise BenchmarkBlock('Unmatched case detection')
        key=(d['case_id'],d.get('prediction_id'))
        if not isinstance(d.get('prediction_id'),str) or key in seen:
            raise BenchmarkBlock('Prediction ID collision')
        seen.add(key)
        if d.get('system') not in SYSTEMS:
            raise BenchmarkBlock('Invalid predicted system')
        if d.get('matched_label_id') is not None and (d['case_id'],d['matched_label_id']) not in labels:
            raise BenchmarkBlock('Prediction matched nonexistent label')
        if d.get('human_match_verified') not in (True,False):
            raise BenchmarkBlock('Human matching decision required')
    # Every accepted one-to-one match must be independently reviewed.
    matched=[]
    for d in detections:
        if d.get('matched_label_id') is not None and d.get('human_match_verified') is True:
            matched.append((d['case_id'],d['matched_label_id']))
    if len(matched)!=len(set(matched)):
        raise BenchmarkBlock('A true defect can be counted once only')


def score_serious_defects(cases:list[dict], detections:list[dict]) ->dict:
    """Critical misses are explicit failures; no synthetic proxy earns approval."""
    validate_real_holdout(cases,detections)
    case_by_id={c['case_id']:c for c in cases}
    label_by_key={(c['case_id'],l['label_id']):l for c in cases for l in c['labels']}
    accepted={(d['case_id'],d['matched_label_id']) for d in detections
              if d.get('matched_label_id') is not None and d['human_match_verified'] is True
              and d['system']==label_by_key[(d['case_id'],d['matched_label_id'])]['system']}
    misses=[]; per_system=defaultdict(lambda:{'total':0,'detected':0,'critical':0,'critical_missed':0})
    for key,l in label_by_key.items():
        row=per_system[l['system']];row['total']+=1
        if l['severity']=='critical':row['critical']+=1
        if key in accepted:row['detected']+=1
        else:
            misses.append({'case_id':key[0], 'label_id':key[1], 'system':l['system'],'severity':l['severity']})
            if l['severity']=='critical':row['critical_missed']+=1
    false_positives=[]
    for d in detections:
        key=(d['case_id'],d.get('matched_label_id'))
        if key not in accepted:false_positives.append({'case_id':d['case_id'],'prediction_id':d['prediction_id'],'system':d['system']})
    critical_total=sum(l['severity']=='critical' for l in label_by_key.values())
    critical_missed=[m for m in misses if m['severity']=='critical']
    major_missed=[m for m in misses if m['severity']=='major']
    distinct_systems={l['system'] for l in label_by_key.values()}
    # Initial benchmark minimums are quality gates for a PILOT, not universal claims.
    cohort_adequate=(len(cases)>=100 and critical_total>=30 and distinct_systems==SYSTEMS
                     and len({case_by_id[cid]['scope'] for cid in case_by_id})==2)
    critical_recall=(critical_total-len(critical_missed))/critical_total if critical_total else None
    match_precision=len(accepted)/(len(accepted)+len(false_positives)) if accepted or false_positives else None
    pass_gate=(cohort_adequate and critical_total>0 and not critical_missed
               and not major_missed and match_precision is not None and match_precision>=0.95)
    return {'status':'PILOT_HOLDOUT_GATE_PASSED_FIELD_VALIDATION_OPEN' if pass_gate else 'BLOCKED',
            'cases':len(cases),'human_adjudicated_defects':len(label_by_key),
            'critical_defects':critical_total,'critical_recall':critical_recall,
            'critical_misses':critical_missed,'major_misses':major_missed,
            'all_misses':misses,'unmatched_or_unverified_predictions':false_positives,
            'human_verified_precision':match_precision,'per_system':dict(sorted(per_system.items())),
            'minimum_cohort_met':cohort_adequate,'unrepresented_systems':sorted(SYSTEMS-distinct_systems),
            'label_source':'QUALIFIED_INDEPENDENT_HUMAN',
            'guarantee_all_real_defects_found':False,'production_release_allowed':False}
