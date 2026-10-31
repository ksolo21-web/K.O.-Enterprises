"""Michigan-first versioned code applicability context; NEVER declares a violation.

Codebook indexes tell what is presently listed, not the exact provision that
applied to work on a particular property. Jurisdiction, permits, scope, code
sections, and qualified professional review are separate mandatory evidence.
"""
from __future__ import annotations
from datetime import date
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
from urllib.parse import urlsplit
from .source_of_truth import KNOWN_SYSTEMS, KnowledgeError

REGISTRY = Path(__file__).resolve().parents[1]/'knowledge'/'michigan_code_authorities_v1.json'
DISCIPLINES={'building','rehabilitation','electrical','plumbing','mechanical','energy'}
SCOPES={'residential_one_two_family','commercial_general','existing_rehabilitation','both_electrical_specific'}
STATUSES={'current_state_listing','stayed_not_effective'}
STATE_HOST='www.michigan.gov'


def _iso(value):
    if not isinstance(value,str): raise KnowledgeError('Missing ISO date')
    try:
        parsed=date.fromisoformat(value)
    except ValueError as exc:raise KnowledgeError('Invalid ISO date') from exc
    if parsed.isoformat()!=value:raise KnowledgeError('Noncanonical date')
    return parsed


def validate_authorities(data):
    if not isinstance(data,dict) or data.get('schema_version')!=1 or data.get('territory')!='Michigan, United States':
        raise KnowledgeError('Not the approved Michigan authority registry')
    snapshot=_iso(data.get('snapshot_date'))
    records=data.get('sources')
    if not isinstance(records,list) or not 8<=len(records)<=50:raise KnowledgeError('Bounded code catalog required')
    seen=set()
    for s in records:
        if not isinstance(s,dict) or not isinstance(s.get('id'),str) or not s['id'].startswith('MI_') or s['id'] in seen:
            raise KnowledgeError('Invalid or duplicate Michigan authority ID')
        seen.add(s['id'])
        if s.get('discipline') not in DISCIPLINES or s.get('building_scope') not in SCOPES or s.get('status') not in STATUSES:
            raise KnowledgeError('Unknown code discipline, building scope, or status')
        if not isinstance(s.get('edition'),str) or s['edition'] not in ('2015','2021','2023'):
            raise KnowledgeError('Code edition unrecognized')
        url=urlsplit(s.get('authority_url',''))
        if url.scheme!='https' or url.netloc!=STATE_HOST or not url.path.startswith('/lara/') or url.query or url.fragment:
            raise KnowledgeError('Only LARA primary authority URLs permitted')
        if not isinstance(s.get('notes'),str) or len(s['notes'])<25:
            raise KnowledgeError('Source scope/limitations required')
        if s['status']=='stayed_not_effective':
            if s.get('effective_from') is not None:raise KnowledgeError('Stayed code cannot have effective start')
        elif _iso(s.get('effective_from'))>snapshot:
            raise KnowledgeError('Future effective code wrongly marked current')
    required={'MI_RES_2015','MI_RES_2021_STAYED','MI_BUILDING_2021','MI_ELECTRICAL_2023','MI_COMM_ENERGY_2021'}
    if not required.issubset(seen):raise KnowledgeError('Core Michigan legal status records missing')
    lookup=data.get('jurisdiction_lookup')
    if not isinstance(lookup,dict) or lookup.get('must_verify_for_case') is not True or set(lookup.get('disciplines',[]))!={'building','electrical','mechanical','plumbing'}:
        raise KnowledgeError('Authority-having-jurisdiction controls missing')
    u=urlsplit(lookup.get('url',''))
    if u.scheme!='https' or u.netloc!=STATE_HOST or not u.path.startswith('/lara/'):
        raise KnowledgeError('Jurisdiction list must be primary state source')
    return copy.deepcopy(data)


@lru_cache(maxsize=1)
def _cached():
    return validate_authorities(json.loads(REGISTRY.read_text(encoding='utf-8')))


def load_authorities():return copy.deepcopy(_cached())


def authority_digest():return hashlib.sha256(REGISTRY.read_bytes()).hexdigest()


def applicable_references(*,building_type,inspection_date,work_type='visual_inspection'):
    """Return candidate indexes; NOT verified applicability for this construction."""
    when=_iso(inspection_date)
    if building_type not in ('residential_one_two_family','commercial_general'):
        raise KnowledgeError('Verify actual residential/commercial occupancy classification')
    if work_type not in ('visual_inspection','new_construction','alteration','repair','existing_rehabilitation'):
        raise KnowledgeError('Unknown construction/inspection work type')
    records=load_authorities()['sources']
    candidate=[];excluded=[]
    for s in records:
        valid_scope=(s['building_scope']==building_type or s['building_scope']=='both_electrical_specific' or
                     (s['building_scope']=='existing_rehabilitation' and work_type=='existing_rehabilitation'))
        if not valid_scope:continue
        if s['status']=='stayed_not_effective' or (s['effective_from'] and _iso(s['effective_from'])>when):
            excluded.append(s['id']);continue
        candidate.append({'id':s['id'],'discipline':s['discipline'],'edition':s['edition'],
                          'authority_url':s['authority_url'],'state_listing_only':True})
    return {'candidate_references':candidate,'excluded_reference_ids':excluded,
            'applicability_verified':False,'ahj_verified':False,'governing_permit_edition_verified':False,
            'exact_provision_verified':False,'court_order_status_must_be_rechecked':True,
            'reason':'Candidate statewide code indexes only; local AHJ, actual work/permit date, amendments and section receipts missing.'}


def build_michigan_brief(systems,inspection_date,building_type='unverified'):
    """Context-bound expert prompt, never smuggling a code finding into an agent."""
    if not isinstance(systems,(tuple,list)) or not systems or any(s not in KNOWN_SYSTEMS for s in systems):
        raise KnowledgeError('Invalid inspection systems for Michigan knowledge brief')
    if building_type not in ('residential_one_two_family','commercial_general'):
        return ('MICHIGAN_SOURCE_POLICY: State recorded as Michigan, but building occupancy is not verified. '
                'Do not select the residential/commercial code edition. Request building classification, '
                'work/permit dates, AHJ by discipline, adopted amendments and exact provision receipts. '
                'Document only visible evidence as pending review.')
    ref=applicable_references(building_type=building_type,inspection_date=inspection_date)
    sysdiscipline={'electrical':'electrical','plumbing':'plumbing','water_heating':'plumbing','hvac':'mechanical'}
    wanted={sysdiscipline.get(s,'building') for s in systems}|{'energy'}
    selected=[r for r in ref['candidate_references'] if r['discipline'] in wanted]
    codes=', '.join(f"{r['id']} ({r['edition']})" for r in selected)
    return ('MICHIGAN_SOURCE_POLICY: State LARA listings, as of 2026-10-31; do not assert current status without checking. '
            f'Candidate reference indexes for the assigned systems: {codes or "none"}. '
            'Residential 2021/energy 2021 proposals were subject to a 2025 court order: NOT automatically effective. '
            'Exact section text, governing permit edition, amendments and municipal AHJ are UNVERIFIED. '
            'Never declare CODE VIOLATION, compliant, installation era, structural cause or hidden defect from photographs. '
            'Record symptoms, alternatives, missing measurements and a qualified evaluation referral. '
            'All references must be checked against the real case and remain pending human review.')
