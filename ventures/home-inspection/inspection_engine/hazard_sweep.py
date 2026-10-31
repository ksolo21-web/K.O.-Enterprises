"""Cross-system safety sweep: missing observations are never negative findings."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
from .coverage_expansion import ReferenceBlock, _day
from .descriptors import REQUIRED_FEATURES

CATALOG=Path(__file__).resolve().parents[1] / 'knowledge' / 'critical_hazard_sweep_v6.json'


def load_hazard_sweep(path=None):
    obj=json.loads(Path(path or CATALOG).read_text(encoding='utf-8'))
    if not isinstance(obj,dict) or obj.get('schema_version')!=6:raise ReferenceBlock('Hazard schema mismatch')
    _day(obj.get('reviewed_on'))
    topics=obj.get('topics')
    if not isinstance(topics,list) or len(topics)<13:raise ReferenceBlock('Insufficient system coverage')
    seen=set();names=set()
    for row in topics:
        if not isinstance(row,dict) or row.get('system') not in REQUIRED_FEATURES or row.get('system') in seen:
            raise ReferenceBlock('Hazard scope missing or duplicated')
        seen.add(row['system'])
        if row.get('id') in names or not row.get('id'):raise ReferenceBlock('Duplicate hazard ID')
        names.add(row['id'])
        for key in ('signal','possible_mechanisms','alternative_explanations','verification','referral'):
            if not isinstance(row.get(key),str) or not row[key]:raise ReferenceBlock('Missing differential hazard field')
        if row.get('not_a_confirmed_defect') is not True:
            raise ReferenceBlock('Hazard guides must not imply a confirmed defect')
    if seen!=set(REQUIRED_FEATURES):raise ReferenceBlock('Hazard sweep does not cover all existing systems')
    return obj


def plan_hazard_sweep(system_evidence:dict, *,source=None):
    """E.g. {electrical: {'status':'not_observed', 'media_ids':[]}}.

    Even if some evidence exists, the hazard is unassessed until a qualified
    inspector verifies a specific check. A model may only propose follow-ups.
    """
    catalog=source if source is not None else load_hazard_sweep()
    if not isinstance(system_evidence,dict) or any(k not in REQUIRED_FEATURES for k in system_evidence):
        raise ReferenceBlock('Invalid evidence coverage keys')
    rows=[]
    for h in catalog['topics']:
        info=system_evidence.get(h['system'],{})
        if not isinstance(info,dict):raise ReferenceBlock('Invalid system evidence entry')
        ids=info.get('media_ids',[])
        if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids):
            raise ReferenceBlock('Evidence IDs must be explicit')
        status=info.get('status','not_observed')
        if status not in ('not_observed','partial','inspector_evaluated'):
            raise ReferenceBlock('Invalid system coverage state')
        checked=(status=='inspector_evaluated' and info.get('qualified_human_review') is True and bool(ids))
        rows.append({'system':h['system'],'hazard_id':h['id'],
                     'assessment_status':'INSPECTOR_CHECK_RECORDED_HAZARD_NOT_RULED_OUT' if checked else 'HUMAN_ASSESSMENT_MISSING',
                     'source_media_ids':ids,'visible_warning_signals':h['signal'],
                     'possible_causes_not_confirmed':h['possible_mechanisms'],
                     'other_possible_explanations':h['alternative_explanations'],
                     'recommended_evidence':h['verification'],
                     'specialist_to_consider':h['referral'],
                     'verified_absence_of_hazard':False})
    return {'status':'SAFETY_SWEEP_REVIEW_REQUIRED','tasks':rows,
            'systems_needing_assessment':sum(x['assessment_status']=='HUMAN_ASSESSMENT_MISSING' for x in rows),
            'guarantee_no_missed_defects':False,'production_approved':False}
