"""Embedded, copyright-safe national inspection policy and Michigan-first expert retrieval.

A scoped knowledge packet is delivered to every technical specialist. It is
reference material, never inspection evidence, legal applicability, training
weights, proof of absence, or a substitute for a qualified human inspector.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
import copy
import hashlib
import json
import re

from .descriptors import REQUIRED_FEATURES
from .source_of_truth import KnowledgeError

CATALOG = Path(__file__).resolve().parents[1] / 'knowledge' / 'national_inspection_policy_v4.json'
HOSTS = {
    'www.nachi.org': 'InterNACHI',
    'www.homeinspector.org': 'ASHI',
    'store.astm.org': 'ASTM International',
    'www.michigan.gov': 'Michigan LARA',
    'www.cpsc.gov': 'U.S. Consumer Product Safety Commission',
    'www.epa.gov': 'U.S. Environmental Protection Agency',
    'www.cdc.gov': 'Centers for Disease Control and Prevention',
    'www.energycodes.gov': 'U.S. Department of Energy',
    'forthepro.bradfordwhite.com': 'Bradford White',
    'www.rheem.com': 'Rheem',
    'www.carrier.com': 'Carrier',
}
SOP_STATUS = {'active_reference','current_until_2026_12_31','future_2027_01_01',
              'optional_contract_framework','index_only','court_order_check_required',
              'reference_index_only','live_lookup_required','testing_required',
              'adoption_check_required','model_serial_check_required'}
ID_RE = re.compile(r'[A-Z][A-Z0-9_]{4,54}\Z')

def validate_policy(policy: dict) -> dict:
    if not isinstance(policy,dict) or policy.get('schema_version') != 4 or policy.get('territory') != 'Michigan, United States':
        raise KnowledgeError('Unsupported national/Michigan inspection policy')
    if policy.get('knowledge_is_not_property_evidence') is not True or policy.get('all_conditions_detected_guarantee') is not False:
        raise KnowledgeError('Knowledge cannot verify a property or guarantee detection')
    if date.fromisoformat(policy.get('edition','')) > date.today():
        raise KnowledgeError('Knowledge snapshot is from the future')
    rules = policy.get('general_rules')
    if not isinstance(rules,list) or len(rules)<8 or any(not isinstance(x,str) or not 35<=len(x)<=450 for x in rules):
        raise KnowledgeError('Inspection safety and reporting rules missing')
    sources=policy.get('sources')
    if not isinstance(sources,list) or len(sources)<12 or len(sources)>70:
        raise KnowledgeError('Insufficient bounded reference catalog')
    ids=set()
    for source in sources:
        if not isinstance(source,dict) or not isinstance(source.get('id'),str) or not ID_RE.fullmatch(source['id']) or source['id'] in ids:
            raise KnowledgeError('Invalid source identity')
        ids.add(source['id'])
        url=urlsplit(source.get('url',''))
        if url.scheme!='https' or url.username or url.password or url.port or url.query or url.fragment or HOSTS.get(url.hostname)!=source.get('publisher'):
            raise KnowledgeError('Reference URL and publisher mismatch')
        if source.get('status') not in SOP_STATUS or source.get('building_scope') not in ('residential','commercial','both'):
            raise KnowledgeError('Unknown applicability or legal status')
        if source.get('embedded_full_text') is not False:
            raise KnowledgeError('Unauthorized proprietary text must not be embedded')
        if not isinstance(source.get('use_limit'),str) or len(source['use_limit'])<40:
            raise KnowledgeError('Reference limitations must be explicit')
        if date.fromisoformat(source['retrieved_on'])>date.fromisoformat(policy['edition']):
            raise KnowledgeError('Source cannot claim future review')
    if not {'INT_NACHI_SOP','ASHI_SOP_CURRENT','ASHI_SOP_2027','ASTM_E2018_24','MI_CODE_BOOKS','MI_RES_STAY'}.issubset(ids):
        raise KnowledgeError('National and Michigan sources incomplete')
    scope=policy.get('scope')
    if not isinstance(scope,dict) or set(scope)!= {'residential','commercial'} or scope['residential'].get('effective_change')!='ASHI_SOP_2027':
        raise KnowledgeError('Incorrect national inspection scope transition')
    cards=policy.get('systems')
    if not isinstance(cards,list) or len(cards)!=len(REQUIRED_FEATURES):
        raise KnowledgeError('All building systems require embedded expert guidance')
    seen=set()
    for card in cards:
        if not isinstance(card,dict) or card.get('system') not in REQUIRED_FEATURES or card['system'] in seen:
            raise KnowledgeError('Invalid or duplicate system card')
        seen.add(card['system'])
        if card.get('feature_codes') != list(REQUIRED_FEATURES[card['system']]):
            raise KnowledgeError('Feature guide differs from validated engine vocabulary')
        for key in ('inspection_focus','example_sign','possible_mechanism','alternative_explanation','what_would_distinguish','serious_warning_cue','qualified_referral'):
            if not isinstance(card.get(key),str) or not 18<=len(card[key])<=450:
                raise KnowledgeError('Missing or unbounded building-science reasoning field: '+key)
        if (not isinstance(card.get('internachi_section_index'),list) or not card['internachi_section_index'] or
                any(not re.fullmatch(r'3\.(?:[1-9]|10)',part) for part in card['internachi_section_index'])):
            raise KnowledgeError('Residential SOP section index missing')
        if card.get('status')!='illustrative_nonexhaustive_training_context' or not isinstance(card.get('not_tested_by_photo'),list) or len(card['not_tested_by_photo'])<3:
            raise KnowledgeError('Card must mark uncertainty and photo limitations')
    return copy.deepcopy(policy)

@lru_cache(maxsize=1)
def _cached():
    return validate_policy(json.loads(CATALOG.read_text(encoding='utf-8')))

def load_policy():
    return copy.deepcopy(_cached())

def policy_digest():
    return hashlib.sha256(CATALOG.read_bytes()).hexdigest()

def active_sop_context(property_kind: str='unverified', as_of: str='2026-10-31', contracted_sop: str|None=None) -> dict:
    """National standards are voluntary/contractual, not adopted building code."""
    when=date.fromisoformat(as_of)
    if property_kind not in ('unverified','residential','commercial'):
        raise KnowledgeError('Unknown property scope')
    if contracted_sop not in (None,'INT_NACHI_SOP','ASHI_SOP_CURRENT','ASHI_SOP_2027','ASTM_E2018_24'):
        raise KnowledgeError('Unknown contracted standard')
    if property_kind=='unverified':
        return {'standard':'UNSELECTED','unverified':['building_use_and_occupancy','scope_agreement','inspector_credentials'],
                'commercial_pca_not_home_sop':True,'standard_compliance_certified':False}
    if property_kind=='residential':
        if contracted_sop=='ASTM_E2018_24':
            raise KnowledgeError('Commercial PCA cannot be silently substituted for residential home SOP')
        if contracted_sop=='ASHI_SOP_2027' and when < date(2027,1,1):
            raise KnowledgeError('ASHI 2027 standards are not yet effective on case date')
        if contracted_sop=='ASHI_SOP_CURRENT' and when >= date(2027,1,1):
            raise KnowledgeError('Outdated ASHI current reference cannot substitute for the effective 2027 edition')
        selected=contracted_sop or 'UNSELECTED'
        return {'standard':selected,'available_references':['INT_NACHI_SOP','ASHI_SOP_2027' if when>=date(2027,1,1) else 'ASHI_SOP_CURRENT'],
                'unverified':(['scope_agreement','inspector_credentials'] if not contracted_sop else ['inspector_credentials']),
                'standard_compliance_certified':False}
    if contracted_sop and contracted_sop!='ASTM_E2018_24':
        raise KnowledgeError('Residential SOP cannot be substituted for commercial PCA')
    return {'standard':contracted_sop or 'UNSELECTED', 'available_references':['ASTM_E2018_24'],
            'unverified':['scope_agreement','consultant_qualifications'],
            'standard_compliance_certified':False}

def build_inspection_knowledge_brief(systems, *, property_kind='unverified', inspection_date='2026-10-31', contracted_sop=None) -> str:
    """Fail-closed, structured internal reference text for one work order.

    All installed v2/v3 catalogs remain on disk. This includes only selected
    systems to fit local-model context, but *every* system has an embedded card.
    """
    if not isinstance(systems,(tuple,list)) or not systems or len(systems)>13 or len(systems)!=len(set(systems)) or any(s not in REQUIRED_FEATURES for s in systems):
        raise KnowledgeError('Invalid requested systems')
    context=active_sop_context(property_kind,inspection_date,contracted_sop)
    policy=load_policy(); cards={c['system']:c for c in policy['systems']}
    lines=['NATIONAL_INSPECTION_POLICY_V4 (internal knowledge, NOT case evidence):',
           'MANDATORY_SCOPE: '+json.dumps(context,sort_keys=True),
           'REPORT_STANDARD: Prioritize material observed deficiencies and significant safety/structural concerns; explain location, observed condition, significance and qualified follow-up. Record material inaccessible areas and tests not performed.',
           'REASONING_STANDARD: For any serious sign, consider competing causes, what evidence discriminates, and potential severity; NEVER state a hidden root cause as verified without independent tests. Preserve potential hazards for human escalation, never bury them.',
           'BOUNDARIES: A photo cannot establish complete defect coverage, code compliance, system life, energized test results, manufacturer recall status, radon level, gas/CO concentration or immunity from liability.',
           'STANDARDS_SCOPE: InterNACHI/ASHI residential SOP differs from contract-scoped ASTM E2018-24 commercial PCA; building codes are applicability references only, not automatically inspection findings.',
           'COVERAGE_EXCEPTION: Fireplace/hearth (InterNACHI 3.8) does NOT have a dedicated 13-system specialist yet. Flag for inspector triage; do not silently claim it was inspected.',
           'LEGAL_AND_COPYRIGHT: Full ICC/NFPA/ASTM code sections are not bundled. Use approved exact-source receipts with AHJ, effective edition and permit dates for any legal determination.',
           'ALL_FINDINGS_PENDING_QUALIFIED_INSPECTOR_REVIEW; NO CUSTOMER_RELEASE.']
    for system in systems:
        c=cards[system]
        lines.append('EXPERT_DOMAIN '+system.upper()+': '+json.dumps({k:c[k] for k in ('feature_codes','internachi_section_index','inspection_focus','example_sign','possible_mechanism','alternative_explanation','what_would_distinguish','serious_warning_cue','qualified_referral')},sort_keys=True))
    lines.append('REFERENCE_INDEX: '+','.join(s['id'] for s in policy['sources'] if s['building_scope'] in ('both',property_kind)))
    lines.append('POLICY_DIGEST_SHA256: '+policy_digest())
    return '\n'.join(lines)
