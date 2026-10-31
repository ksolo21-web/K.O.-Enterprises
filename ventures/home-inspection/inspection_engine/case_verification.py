"""Case-specific evidence and Michigan law gate. Never auto-approves inspections.

Model text, reviewer labels, and reference URLs are untrusted inputs. This
module checks file custody, legal applicability preconditions and completeness,
not whether a picture truly proves a crack or whether a code section was met.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import re
from .descriptors import REQUIRED_FEATURES
from .michigan_authority import load_authorities, applicable_references, authority_digest
from .source_of_truth import KnowledgeError

SHA = re.compile('[0-9a-f]{64}\\Z')
SAFE_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\\Z')
SECTION = re.compile('[A-Za-z0-9][A-Za-z0-9.()/_-]{0,75}\\Z')
CLAIMS={'visual_observation','potential_defect','cause_hypothesis','code_violation','recall_applicability','condition_clear'}
DANGEROUS=['guaranteed safe','no issues','code compliant','no defects','cause confirmed','fully compliant','100% safe']


def _hash_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _date(value):
    try:
        if not isinstance(value,str):raise ValueError('date not str')
        d=date.fromisoformat(value)
        if value!=d.isoformat():raise ValueError('noncanonical')
        return d
    except ValueError as exc:raise KnowledgeError('Invalid inspection / receipt date') from exc


def validate_case_context(case):
    if not isinstance(case,dict) or not isinstance(case.get('case_id'),str) or not SAFE_ID.fullmatch(case['case_id']):
        raise KnowledgeError('Stable case identifier required')
    if case.get('state')!='MI':raise KnowledgeError('Case must explicitly identify Michigan as state')
    when=_date(case.get('inspection_date'))
    if not isinstance(case.get('county'),str) or not case['county'].strip() or len(case['county'])>80:
        raise KnowledgeError('Michigan county required')
    if not isinstance(case.get('municipality'),str) or not case['municipality'].strip() or len(case['municipality'])>100:
        raise KnowledgeError('Actual city/township/village required for AHJ resolution')
    building_type=case.get('building_type')
    if building_type not in ('residential_one_two_family','commercial_general'):
        raise KnowledgeError('Building type / occupancy must be classified before selecting code scope')
    if case.get('work_type') not in ('visual_inspection','new_construction','alteration','repair','existing_rehabilitation'):
        raise KnowledgeError('Actual construction/inspection work type required')
    if not isinstance(case.get('media'),list) or not case['media']:
        raise KnowledgeError('Evidence register required')
    ids=set()
    for m in case['media']:
        if not isinstance(m,dict) or not isinstance(m.get('id'),str) or not SAFE_ID.fullmatch(m['id']) or m['id'] in ids:
            raise KnowledgeError('Duplicate/malformed evidence ID')
        ids.add(m['id'])
        if not isinstance(m.get('path'),str) or not m['path'] or not SHA.fullmatch(str(m.get('sha256',''))):
            raise KnowledgeError('Evidence path and original hash required')
    ahj=case.get('ahj',{})
    if not isinstance(ahj,dict):raise KnowledgeError('AHJ entries must be a record')
    for disc,receipt in ahj.items():
        if disc not in ('building','electrical','mechanical','plumbing') or not isinstance(receipt,dict):
            raise KnowledgeError('Unknown discipline/AHJ entry')
        if receipt.get('authority_level') not in ('state','county','local'):
            raise KnowledgeError('Unrecognized enforcing-agency level')
        if not isinstance(receipt.get('agency_name'),str) or not receipt['agency_name'].strip():
            raise KnowledgeError('Enforcing-agency identity required')
        if _date(receipt.get('checked_at'))>when:
            raise KnowledgeError('Future AHJ verification cannot support past inspection')
        if not str(receipt.get('source_url','')).startswith('https://'):
            raise KnowledgeError('AHJ receipt needs direct official source URL')
    return {'inspection_date':when,'building_type':building_type,'work_type':case['work_type'],
            'candidate_code_index':applicable_references(building_type=building_type,inspection_date=case['inspection_date'],
                                                            work_type=case['work_type'])}


def _evidence_receipt(case,root,evidence_ids):
    if not isinstance(evidence_ids,list) or not evidence_ids or len(evidence_ids)!=len(set(evidence_ids)):
        return False,'At least one unique original source evidence ID required',[]
    known={m['id']:m for m in case['media']}
    root=Path(root).resolve(strict=True)
    verified=[]
    for eid in evidence_ids:
        m=known.get(eid)
        if not m:return False,'Unknown evidence ID',verified
        p=(root/m['path']).resolve(strict=False)
        if not p.is_relative_to(root) or not p.is_file() or p.is_symlink():
            return False,'Evidence path escapes case root or missing file',verified
        if p.suffix.lower() not in ('.jpg','.jpeg','.png','.webp','.mp4','.mov'):
            return False,'Unsupported source evidence format',verified
        cap=500*1024*1024 if p.suffix.lower() in ('.mp4','.mov') else 35*1024*1024
        if p.stat().st_size>cap:return False,'Evidence exceeds bounded size',verified
        if _hash_file(p)!=m['sha256']:
            return False,'Original evidence SHA-256 mismatch',verified
        verified.append({'id':eid,'sha256':m['sha256']})
    return True,'Original evidence hashes match',verified


def _source_provisions(finding,case,chosen):
    """Receipt structural check; source wording and local adoption remain human reviewed."""
    receipts=finding.get('provision_receipts',[])
    if not isinstance(receipts,list) or not receipts:return ['Exact adopted code provision receipt is missing']
    index={x['id']:x for x in load_authorities()['sources']}
    blockers=[]
    ids=set()
    for r in receipts:
        if not isinstance(r,dict):blockers.append('Malformed provision receipt');continue
        sid=r.get('authority_id')
        if sid not in index or sid not in chosen:blockers.append('Code provision authority is not a candidate for this case');continue
        if sid in ids:blockers.append('Duplicate source authority receipt')
        ids.add(sid)
        if not isinstance(r.get('section'),str) or not SECTION.fullmatch(r['section']):
            blockers.append('Precise section identifier is required')
        if r.get('source_url') != index[sid]['authority_url']:
            blockers.append('Provision receipt source does not match approved state index')
        if not isinstance(r.get('edition'),str) or r['edition']!=index[sid]['edition']:
            blockers.append('Provision receipt edition mismatch')
        if not isinstance(r.get('original_provision_text_confirmed_by'),str) or not r['original_provision_text_confirmed_by'].strip():
            blockers.append('Human source-text verification identity required')
        # A raw human name/claim does not authenticate the professional reviewer.
        if r.get('original_provision_review_authenticated') is not True:
            blockers.append('Source text review must be authenticated externally')
    return blockers


def evaluate_finding(case:dict,finding:dict,root:Path)->dict:
    """Fail-closed structured finding decision. Never returns an approved defect."""
    result={'status':'BLOCKED','blockers':[],'evidence_receipts':[],
            'review_receipt_status':'MISSING', 'qualified_review_required':True,
            'authority_registry_sha256':authority_digest(),
            'cause_established':False,'code_violation_verified':False,
            'qualified_review_authenticated':False,'customer_release_allowed':False}
    try:
        ctx=validate_case_context(case)
    except (KnowledgeError,TypeError,ValueError) as exc:
        result['blockers'].append(str(exc));return result
    if not isinstance(finding,dict) or finding.get('claim_type') not in CLAIMS:
        result['blockers'].append('Unknown claim type');return result
    system=finding.get('system')
    if system not in REQUIRED_FEATURES:
        result['blockers'].append('Unrecognized inspection system');return result
    feature=finding.get('feature_code')
    if feature not in REQUIRED_FEATURES[system]:
        result['blockers'].append('Feature code not in delegated system');return result
    symptom=finding.get('observed_symptom')
    if not isinstance(symptom,str) or not 8<=len(symptom)<=500:
        result['blockers'].append('Specific bounded observed symptom required');return result
    if any(x in symptom.lower() for x in DANGEROUS):
        result['blockers'].append('Absolute safety/compliance or unverified cause assertion');return result
    try:
        ok,message,receipts=_evidence_receipt(case,root,finding.get('evidence_ids'))
    except (OSError,ValueError) as exc:
        ok=False;message='Evidence file could not be read or resolved';receipts=[]
    result['evidence_receipts']=receipts
    if not ok:result['blockers'].append(message);return result
    review=finding.get('qualified_review_receipt')
    if isinstance(review,dict) and review.get('decision') in ('approve','reject','needs_more_evidence'):
        result['review_receipt_status']='SUBMITTED_BUT_AUTHENTICATION_UNVERIFIED'
        # Never treat a self-asserted review signature as independently authenticated.
        if review['decision']=='reject':
            result['blockers'].append('Reviewer-reported rejection requires independent adjudication')
    cause=finding.get('cause_assessment')
    if not isinstance(cause,dict) or cause.get('status') not in ('unknown','hypotheses_only'):
        result['blockers'].append('Cause assessment must be unknown or hypotheses_only')
    else:
        hypotheses=cause.get('hypotheses',[])
        if not isinstance(hypotheses,list) or len(hypotheses)>5:
            result['blockers'].append('Cause hypotheses must be bounded')
        elif any(not isinstance(c,dict) or not str(c.get('possible_mechanism','')).strip() or
                 not str(c.get('verification_needed','')).strip() or
                 not isinstance(c.get('alternative_explanation'),str) or not c['alternative_explanation'].strip()
                 for c in hypotheses):
            result['blockers'].append('Each candidate cause needs mechanism, alternative and verifying action')
        if finding['claim_type']=='cause_hypothesis' and not hypotheses:
            result['blockers'].append('Causal claim requires at least one testable alternative hypothesis')
    if finding['claim_type']=='condition_clear':
        result['blockers'].append('Absence of defect cannot be established by limited visual coverage')
    if finding['claim_type']=='recall_applicability':
        result['blockers'].append('Exact brand/model/serial and recall case match not implemented')
    if finding['claim_type']=='code_violation':
        discipline=finding.get('code_discipline')
        if discipline not in ('building','electrical','plumbing','mechanical','energy','rehabilitation'):
            result['blockers'].append('Code discipline and applicable work type missing')
        if not case.get('ahj',{}).get('building'):
            result['blockers'].append('Building AHJ receipt required')
        if discipline in ('electrical','plumbing','mechanical') and not case.get('ahj',{}).get(discipline):
            result['blockers'].append('Trade-specific AHJ receipt required')
        if not case.get('permit_history_verified'):
            result['blockers'].append('Permit and construction history must establish governing edition')
        if not case.get('local_amendments_verified'):
            result['blockers'].append('Local amendments and effective rules need independent verification')
        chosen={s['id'] for s in ctx['candidate_code_index']['candidate_references']
                if discipline==s['discipline'] or (discipline=='building' and s['discipline']=='building')}
        result['blockers'] += _source_provisions(finding,case,chosen)
        if not result['blockers']:
            result['status']='CODE_CANDIDATE_FOR_QUALIFIED_REVIEW'
            result['blockers'].append('Technical facts, enacted provision applicability and reviewer identity still require independent professional authentication')
    else:
        if not result['blockers']:
            result['status']='EVIDENCE_LINKED_REVIEW_PENDING'
            result['blockers'].append('An intact file is not proof that the model interpreted its pixels correctly')
    return result


def coverage_gaps(case,observations):
    """No unobserved feature silently becomes 'safe' or 'inspected'."""
    validate_case_context(case)
    known={m['id'] for m in case['media']}
    observed={}
    for obs in observations:
        if not isinstance(obs,dict) or obs.get('system') not in REQUIRED_FEATURES:continue
        if (obs.get('feature_code') in REQUIRED_FEATURES[obs['system']]
            and obs.get('evidence_ids') and all(i in known for i in obs['evidence_ids'])):
            observed.setdefault(obs['system'],set()).add(obs['feature_code'])
    missing={s:sorted(set(features)-observed.get(s,set())) for s,features in REQUIRED_FEATURES.items()}
    return {'required_feature_count':sum(map(len,REQUIRED_FEATURES.values())),
            'documented_feature_count':sum(len(x) for x in observed.values()),
            'unverified_features':missing,'no_defect_absence_inferred':True,
            'qualified_inspector_release_required':True}
