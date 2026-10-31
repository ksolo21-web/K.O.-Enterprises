"""Conservative, deterministic photo-inspection benchmark for human-annotated cases.

This measures exact issue-code and spatial agreement, not professional competence.
Only a qualified inspector can approve findings; these scores never release reports.
"""
from __future__ import annotations
from collections import Counter, deque
from pathlib import Path
from typing import Any
import math
from .core import DataError, validate_project, SYSTEM_NAME
from .capture import verify_custody

SEVERITIES = {'minor', 'moderate', 'major', 'safety'}
ISSUE_CODE_CHARS = frozenset('abcdefghijklmnopqrstuvwxyz0123456789._-')


def _string(value: Any, limit: int = 100) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise DataError('Invalid benchmark text')
    return value


def _bbox(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise DataError('Benchmark location requires a four-number bounding box')
    x0,y0,x1,y1 = map(float,value)
    if not 0 <= x0 < x1 <= 1 or not 0 <= y0 < y1 <= 1:
        raise DataError('Benchmark bounding box is outside normalized image')
    return x0,y0,x1,y1


def _iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    left, top, right, bottom = max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    intersection = max(0,right-left)*max(0,bottom-top)
    aa=(a[2]-a[0])*(a[3]-a[1]);bb=(b[2]-b[0])*(b[3]-b[1])
    return intersection/(aa+bb-intersection) if aa+bb>intersection else 0


def evaluate(document: dict, root: Path, ground_truth: dict, predictions: dict,
             *, minimum_cases: int = 10, iou_threshold: float = .25) -> dict:
    """Evaluate inspector-labeled *observable* concerns against coded predictions.

    Required codes must come from independently labeled real cases for the result
    to have meaning; fields alone cannot prove inspector credentials or independence.
    No free-text model descriptions are automatically treated as matching labels.
    """
    if type(minimum_cases) is not int or not 1 <= minimum_cases <= 10000:
        raise DataError('Minimum cases must be 1..10000')
    if type(iou_threshold) not in (float,int) or not .05 <= iou_threshold <= 1:
        raise DataError('Invalid overlap threshold')
    validate_project(document,root)
    custody=verify_custody(document,root)
    if custody: raise DataError('Cannot score altered evidence: '+custody[0])
    media={m['id']:m for m in document['media'] if m['kind']=='photo'}
    if ground_truth.get('project_id') != document['project_id'] or predictions.get('project_id') != document['project_id']:
        raise DataError('Benchmark project mismatch')
    if ground_truth.get('label_source') != 'independent_human_inspector':
        raise DataError('Ground truth must be inspector-labeled, not AI-generated')
    annotator=_string(ground_truth.get('annotator_id'))
    cases=ground_truth.get('reviewed_media_ids')
    if not isinstance(cases,list) or not cases or len(cases)!=len(set(cases)) or len(cases)>5000:
        raise DataError('Provide a nonempty unique list of fully reviewed photos')
    if any(mid not in media for mid in cases):
        raise DataError('Reviewed media not found in source project')
    if not isinstance(ground_truth.get('labels'),list) or len(ground_truth['labels'])>3000:
        raise DataError('Invalid ground truth label list')
    if not isinstance(predictions.get('proposals'),list) or len(predictions['proposals'])>3000:
        raise DataError('Invalid prediction list')
    if predictions.get('source') not in ('model_draft','human_blinded_replay'):
        raise DataError('Only pre-review draft model predictions can be scored')

    def parse(item, human: bool):
        if not isinstance(item,dict): raise DataError('Invalid benchmark record')
        mid=_string(item.get('media_id'))
        if mid not in cases: raise DataError('Label/proposal not in fully reviewed photo set')
        system=_string(item.get('system'),60)
        if system not in SYSTEM_NAME: raise DataError('Unknown inspection system')
        code=_string(item.get('issue_code'),100)
        if any(c not in ISSUE_CODE_CHARS for c in code): raise DataError('Issue code must be canonical lowercase dotted identifier')
        bbox=_bbox(item.get('bbox'))
        if human:
            severity=item.get('severity')
            if severity not in SEVERITIES: raise DataError('Invalid inspector severity')
        else:
            severity=None
            if item.get('source_sha256')!=media[mid]['sha256']:
                raise DataError('Prediction source hash mismatch')
        return {'media_id':mid,'system':system,'issue_code':code,'bbox':bbox,'severity':severity}

    truth=[parse(x,True) for x in ground_truth['labels']]
    proposed=[parse(x,False) for x in predictions['proposals']]
    if len({(x['media_id'],x['system'],x['issue_code'],x['bbox']) for x in truth})!=len(truth):
        raise DataError('Duplicate ground truth label')
    if len({(x['media_id'],x['system'],x['issue_code'],x['bbox']) for x in proposed})!=len(proposed):
        raise DataError('Duplicate identical proposal')
    # Maximum-cardinality one-to-one matching. A greedy choice of the highest
    # IoU can incorrectly count two genuine detections as one when regions
    # overlap. Prefer high-IoU edges, but use augmenting paths to maximize TP.
    edges = {i: [] for i in range(len(truth))}
    for i,g in enumerate(truth):
        for j,p in enumerate(proposed):
            if all(g[k]==p[k] for k in ('media_id','system','issue_code')):
                score = _iou(g['bbox'], p['bbox'])
                if score >= iou_threshold:
                    edges[i].append((score,j))
        edges[i].sort(key=lambda item: (-item[0],item[1]))
    adjacency={i:[j for _,j in pairs] for i,pairs in edges.items()}
    matched_prediction={}  # proposed index -> ground-truth index
    matched_ground={}      # ground-truth index -> proposed index
    for first in range(len(truth)):
        queue=deque([first]); visited_ground={first}; predecessor={}
        free_prediction=None
        while queue and free_prediction is None:
            i=queue.popleft()
            for j in adjacency[i]:
                if j in predecessor:
                    continue
                predecessor[j]=i
                if j not in matched_prediction:
                    free_prediction=j
                    break
                next_i=matched_prediction[j]
                if next_i not in visited_ground:
                    visited_ground.add(next_i)
                    queue.append(next_i)
        if free_prediction is not None:
            j=free_prediction
            while True:
                i=predecessor[j]
                previous_j=matched_ground.get(i)
                matched_prediction[j]=i
                matched_ground[i]=j
                if previous_j is None:
                    break
                j=previous_j
    matched_g=set(matched_ground)
    matched_p=set(matched_prediction)
    tp=len(matched_g);fp=len(proposed)-len(matched_p);fn=len(truth)-tp
    missed=Counter(x['severity'] for i,x in enumerate(truth) if i not in matched_g)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    enough=len(cases)>=minimum_cases
    return {'schema_version':1,'project_id':document['project_id'],
            'benchmark_status':'SYNTHETIC_OR_ATTESTED_LABELS_NOT_INDEPENDENTLY_VERIFIED',
            'annotator_id':annotator,'reviewed_photo_count':len(cases),
            'minimum_required_photos':minimum_cases,
            'sufficient_sample_size':enough,'tp':tp,'fp':fp,'fn':fn,
            'precision':round(precision,4),'recall':round(recall,4),
            'missed_by_severity':dict(sorted(missed.items())),
            'critical_misses':missed['major']+missed['safety'],
            'customer_release_allowed':False,
            'acceptance_status':'BLOCKED_REAL_WORLD_VALIDATION_REQUIRED',
            'limitations':[
               'Labels and inspector qualifications are asserted, not authenticated by this code.',
               'Exact category matching is not semantic understanding of free-text observations.',
               'Small or nonrepresentative data cannot establish real-world accuracy.',
               'Physical inspection and qualified human sign-off remain mandatory.'
            ]}
