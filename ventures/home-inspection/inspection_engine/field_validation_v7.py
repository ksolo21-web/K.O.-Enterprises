"""Independent professional field-benchmark intake and conservative score gate.

Must not synthesize case labels, assume qualification, or infer recall/defect truth.
No private customer media, labels, address or identity is stored in the public source.
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
import re

from .serious_defect_benchmark import score_serious_defects, BenchmarkBlock, METRIC_REVIEW_PENDING

HEX = re.compile(r'[0-9a-f]{64}\Z')
REQUIRED_SCOPE = ('residential','commercial')

class CohortBlocked(ValueError): pass


def validate_protocol(protocol:dict):
    if not isinstance(protocol,dict) or protocol.get('version')!=7:
        raise CohortBlocked('Locked v7 protocol required')
    if protocol.get('consent_required') is not True or protocol.get('qualified_inspector_signature_required') is not True:
        raise CohortBlocked('Consent and qualified signoff required')
    if protocol.get('independent_label_review_required') is not True:
        raise CohortBlocked('Independent adjudication required')
    if protocol.get('holdout_locked_before_inference') is not True or protocol.get('training_case_exclusion') is not True:
        raise CohortBlocked('Leakage prevention required')
    if protocol.get('min_real_cases')!=100 or protocol.get('min_critical')!=30:
        raise CohortBlocked('Pilot minimums changed without review')
    for key in ('protocol_sha256','protocol_owner_signature_sha256'):
        if not HEX.fullmatch(protocol.get(key,'')):
            raise CohortBlocked('Signed immutable study protocol not available')
    return True


def prepare_qualification_check(cases:list[dict]):
    """Inspection credentials can only be independently checked by a real operator."""
    if not isinstance(cases,list):raise CohortBlocked('Field cases must be a list')
    rows=[]
    for c in cases:
        if not isinstance(c,dict):raise CohortBlocked('Invalid case')
        if not isinstance(c.get('case_id'),str) or not c['case_id']:
            raise CohortBlocked('Case identifier missing')
        labeler=c.get('qualified_labeler_id'); adjudicator=c.get('independent_adjudicator_id')
        if not labeler or not adjudicator or labeler==adjudicator:
            raise CohortBlocked('Two independent individuals required')
        rows.append({'case_id':c['case_id'], 'scope':c.get('scope'),
                     'labeler_qualification':'EXTERNAL_VERIFICATION_REQUIRED',
                     'adjudicator_qualification':'EXTERNAL_VERIFICATION_REQUIRED',
                     'consent_provenance':'OPERATOR_EVIDENCE_REQUIRED',
                     'result':'NOT_READY_FOR_PRODUCTION'})
    return rows


def evaluation_summary(cases:list[dict],detections:list[dict],protocol:dict|None=None):
    """Always outputs no-release state. If provenance absent, no performance claim."""
    if protocol is None:
        return {'status':'BLOCKED','blockers':['Signed study protocol and actual qualified holdout absent'],
                'field_detection_accuracy_verified':False,'customer_release_allowed':False}
    try:
        validate_protocol(protocol)
        # Existing evaluator implements label status, real consent, training overlap,
        # distinct inspector/adjudicator, scope and one-to-one matched detections.
        score=score_serious_defects(cases,detections)
    except (CohortBlocked,BenchmarkBlock,KeyError,TypeError,ValueError) as e:
        return {'status':'BLOCKED','blockers':[str(e)],'field_detection_accuracy_verified':False,
                'customer_release_allowed':False}
    return {'status':'ADJUDICATION_EVIDENCE_AUDIT_REQUIRED'
            if score['status']==METRIC_REVIEW_PENDING and score['metric_thresholds_met'] is True else 'BLOCKED',
            'scoring':score,'identity_and_qualification_independently_authenticated':False,
            'field_detection_accuracy_verified':False,'customer_release_allowed':False,
            'next_required_evidence':['Secure underlying consent and inspection-case provenance',
                'External credential check for each inspector/adjudicator',
                'Blind evaluation reproducibility review and independent safety critic',
                'Qualified professional approval, insurance/legal review before production']}
