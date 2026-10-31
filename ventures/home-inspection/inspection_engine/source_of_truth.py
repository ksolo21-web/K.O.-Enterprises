"""Versioned, *offline* source-of-truth policy for inspection reference material.

Literature is never substituted for firsthand case evidence. This module does
not browse, detect defects, grant professional authority or release reports.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
import re
from urllib.parse import urlsplit


KNOWN_SYSTEMS = frozenset((
    'site','foundation','subfloor','framing','exterior','roof','attic',
    'interior','electrical','plumbing','water_heating','hvac','crawlspace'))
KNOWN_CLASSES = frozenset((
    'professional_standard','professional_standard_pending','government_explainer',
    'government_index','government_database','government_guidance',
    'manufacturer_primary'))
PURPOSES = frozenset((
    'inspection_scope','future_scope_reference','jurisdiction_context',
    'recall_lookup','moisture_context','specialist_testing','safety_referral',
    'manufacture_date_code','equipment_identification'))
PENDING = frozenset(('pending_effective_date','deprecated','superseded'))
TRUSTED_HOSTS = frozenset((
    'www.homeinspector.org','www.nachi.org','www.energycodes.gov',
    'www.cpsc.gov','www.epa.gov','www.cdc.gov','www.bradfordwhite.com',
    'www.rheem.com','www.carrier.com'))
OFFICIAL_PUBLISHER_HOSTS = {
    'American Society of Home Inspectors': 'www.homeinspector.org',
    'InterNACHI': 'www.nachi.org',
    'U.S. Department of Energy': 'www.energycodes.gov',
    'U.S. Consumer Product Safety Commission': 'www.cpsc.gov',
    'U.S. Environmental Protection Agency': 'www.epa.gov',
    'Centers for Disease Control and Prevention': 'www.cdc.gov',
    'Bradford White': 'www.bradfordwhite.com',
    'Rheem': 'www.rheem.com',
    'Carrier': 'www.carrier.com',
}
CATALOG = Path(__file__).resolve().parents[1] / 'knowledge' / 'source_registry_v2.json'
ID_RE = re.compile(r'[A-Z][A-Z0-9_]{2,59}\Z')
SHA_RE = re.compile(r'[0-9a-f]{64}\Z')


class KnowledgeError(ValueError):
    pass


def _parse_date(value: str) -> date:
    if not isinstance(value, str):
        raise KnowledgeError('Source date must be a YYYY-MM-DD string')
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise KnowledgeError('Invalid source review date') from exc
    if d.isoformat() != value:
        raise KnowledgeError('Source date must be canonical ISO format')
    return d


def validate_catalog(catalog: dict) -> dict:
    """Fail closed on broken provenance, inappropriate hosts, or weakened flags."""
    if not isinstance(catalog, dict) or catalog.get('schema_version') != 2:
        raise KnowledgeError('Unsupported knowledge schema version')
    items = catalog.get('source_records')
    if not isinstance(items, list) or not items or len(items) > 1000:
        raise KnowledgeError('Expected a bounded source registry')
    version=catalog.get('registry_version')
    if not isinstance(version,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.v\d+',version):
        raise KnowledgeError('Registry release date/version required')
    baseline=_parse_date(version.split('.v',1)[0])
    seen=set()
    for rec in items:
        if not isinstance(rec, dict):
            raise KnowledgeError('Source must be a record')
        sid=rec.get('id')
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid) or sid in seen:
            raise KnowledgeError('Duplicate or invalid immutable source ID')
        seen.add(sid)
        for key in ('title','publisher','verified_claim_note'):
            val=rec.get(key)
            if not isinstance(val, str) or not val.strip() or len(val)>700:
                raise KnowledgeError(f'Invalid {key} for {sid}')
        if rec.get('authority_class') not in KNOWN_CLASSES or rec.get('purpose') not in PURPOSES:
            raise KnowledgeError('Unknown source authority class or purpose')
        if rec.get('applicability_country') != 'US' or rec.get('jurisdiction') != 'national_reference_only':
            raise KnowledgeError('National references cannot self-claim local jurisdictional authority')
        if rec.get('status') not in ('active_reference','pending_effective_date','deprecated','superseded'):
            raise KnowledgeError('Source status not supported')
        if rec.get('authority_class')=='professional_standard_pending' and rec.get('status')!='pending_effective_date':
            raise KnowledgeError('Pending standard cannot be marked currently effective')
        systems=rec.get('systems')
        if (not isinstance(systems,list) or not systems or len(systems)!=len(set(systems))
            or not set(systems).issubset(KNOWN_SYSTEMS)):
            raise KnowledgeError('Source has unknown, duplicate or absent system tags')
        parsed=urlsplit(rec.get('url',''))
        if (parsed.scheme!='https' or parsed.netloc not in TRUSTED_HOSTS or not parsed.path
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise KnowledgeError('Source URL is not on an approved official HTTPS host')
        if OFFICIAL_PUBLISHER_HOSTS.get(rec.get('publisher')) != parsed.netloc:
            raise KnowledgeError('Official source publisher/domain do not match')
        reviewed=_parse_date(rec.get('last_reviewed'))
        if reviewed>baseline:
            raise KnowledgeError('Source review timestamp exceeds versioned catalog release date')
        if rec.get('review_method')!='public_official_webpage_read_no_immutable_snapshot':
            raise KnowledgeError('Source review method must be accurate')
        digest=rec.get('content_snapshot_sha256')
        if digest is not None and (not isinstance(digest,str) or not SHA_RE.fullmatch(digest)):
            raise KnowledgeError('Invalid snapshot SHA-256')
        for flag in ('may_prove_field_condition','may_prove_local_code_compliance','may_automatically_approve_report'):
            if rec.get(flag) is not False:
                raise KnowledgeError('Reference catalog may not grant observation, code or release authority')
    return copy.deepcopy(catalog)


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return validate_catalog(json.loads(CATALOG.read_text(encoding='utf-8')))


def reference_sources(systems, purpose: str | None=None, *, include_pending=False) -> list[dict]:
    """Rank *references*, not facts about a property. Never fetch external URLs."""
    if not isinstance(systems,(list,tuple)) or not systems or any(x not in KNOWN_SYSTEMS for x in systems):
        raise KnowledgeError('Reference request requires known inspection systems')
    if purpose is not None and purpose not in PURPOSES:
        raise KnowledgeError('Unknown reference purpose')
    if type(include_pending) is not bool:
        raise KnowledgeError('Invalid include_pending option')
    system_set=set(systems)
    candidates=[rec for rec in load_catalog()['source_records']
                if system_set.intersection(rec['systems'])
                and (purpose is None or rec['purpose']==purpose)
                and (include_pending or rec['status']=='active_reference')]
    weights={'manufacturer_primary':0,'government_guidance':1,'professional_standard':2,
             'government_database':3,'government_index':4,'government_explainer':5,
             'professional_standard_pending':6}
    return sorted(candidates,key=lambda x:(weights[x['authority_class']],x['id']))


def build_reference_brief(systems, limit: int=4) -> str:
    """Bounded prompt supplement to prevent unsupported appeals to generic sources."""
    if type(limit) is not int or not 1<=limit<=8:
        raise KnowledgeError('Reference limit must be 1-8')
    # Prefer a scope source plus up to three specialized primary references.
    refs=reference_sources(systems)
    scope=next((x for x in refs if x['id']=='ASHI_CURRENT_SOP'), None)
    ranked=[x for x in refs if x['id']!='ASHI_CURRENT_SOP']
    chosen=([scope] if scope is not None else [])+ranked[:limit-(scope is not None)]
    lines=['KNOWLEDGE_SOURCE_POLICY_V2: References are context, NEVER proof of what exists, '
           'what works, what is safe, hidden defects, adopted law, or manufacturer date. '
           'Observe pixels and source hashes only; disclose missing tests/access. '
           'All claims remain human-review-pending.']
    for item in chosen:
        lines.append(f"[{item['id']}] {item['purpose']} / {item['publisher']}: {item['url']}")
    lines.append('NO LIVE SOURCE LOOKUP WAS PERFORMED. A reference URL is not a verified case-specific result.')
    return '\n'.join(lines)


def assess_claim(claim: dict, *, case_evidence: dict | None=None,
                 jurisdiction_receipt: dict | None=None) -> dict:
    """Conservative auditable claim gate: never upgrades a claim to verified or release-ready.

    claim: {kind,system,source_ids,description}.
    case_evidence: {media_id,media_sha256,source_verified:True}, already
    checked by the calling evidence-custody subsystem.
    """
    base={'status':'BLOCKED','reason':'','human_review_required':True,
          'customer_release_allowed':False,'verified_defect':False,
          'code_compliance_verified':False,'reference_is_not_property_evidence':True}
    if not isinstance(claim,dict) or claim.get('system') not in KNOWN_SYSTEMS:
        return dict(base,reason='Unknown inspection system')
    kind=claim.get('kind')
    ids=claim.get('source_ids')
    if (not isinstance(ids,list) or not ids or len(ids)!=len(set(ids))
        or not all(isinstance(s,str) for s in ids)):
        return dict(base,reason='No distinct attributable reference IDs')
    indexed={r['id']:r for r in load_catalog()['source_records']}
    if any(i not in indexed for i in ids):
        return dict(base,reason='Unknown reference ID')
    selected=[indexed[i] for i in ids]
    if any(c['status']!='active_reference' for c in selected):
        return dict(base,reason='Pending, deprecated or superseded reference')
    if any(claim['system'] not in r['systems'] for r in selected):
        return dict(base,reason='Reference does not apply to the proposed inspection system')
    if kind=='code_compliance':
        # Jurisdiction receipts are a necessary input for future development,
        # not sufficient for automatic legal or technical approval.
        return dict(base,reason='Code finding requires verified locally adopted law, applicability and qualified professional review',
                    jurisdiction_receipt_supplied=isinstance(jurisdiction_receipt,dict))
    if kind=='installation_date':
        return dict(base,reason='Manufacture/serial records cannot establish installation date')
    if kind=='remaining_service_life':
        return dict(base,reason='Service life and future failures cannot be inferred from age or images')
    if kind=='recall_confirmed':
        return dict(base,reason='Recall API index is not an exact model/serial matching receipt or professional verification')
    if kind=='hazard_presence' and any(r['purpose']=='specialist_testing' for r in selected):
        return dict(base,reason='Image cannot substitute for required radon, lead or other specialized laboratory testing')
    if kind not in ('observed_feature','potential_concern','manufacture_date_code','scope_limitation','safety_referral'):
        return dict(base,reason='Unsupported claim kind')
    if kind in ('observed_feature','potential_concern','manufacture_date_code'):
        if (not isinstance(case_evidence,dict) or not isinstance(case_evidence.get('media_id'),str)
            or not SHA_RE.fullmatch(str(case_evidence.get('media_sha256','')))
            or case_evidence.get('source_verified') is not True):
            return dict(base,reason='Authenticated original case evidence required')
    if kind=='manufacture_date_code':
        manufacturer_sources=[r for r in selected if r['purpose']=='manufacture_date_code']
        if len(manufacturer_sources)!=1:
            return dict(base,reason='Exactly one matching primary manufacturer date-code reference required')
        # A manufacturer cannot be substituted by any other brand's code table.
        brand=str(claim.get('brand','')).strip().lower().replace('-', ' ')
        brand=' '.join(brand.split())
        matches={'bradford white':'BRADFORD_WHITE_DATE','rheem':'RHEEM_WATER_DATE'}
        if matches.get(brand)!=manufacturer_sources[0]['id']:
            return dict(base,reason='Brand and date-code source do not match an approved decoder')
        if claim['system']!='water_heating':
            return dict(base,reason='Date-code decoder is not applicable to this product category')
    if kind=='scope_limitation' and not any(r['purpose']=='inspection_scope' for r in selected):
        return dict(base,reason='Scope limitation requires an applicable current SOP reference')
    if kind=='safety_referral' and not any(r['purpose']=='safety_referral' for r in selected):
        return dict(base,reason='Safety referral must cite appropriate guidance; not a visual diagnosis')
    if kind in ('observed_feature','potential_concern') and not any(r['purpose']=='inspection_scope' for r in selected):
        return dict(base,reason='Current, applicable inspection scope reference required')
    status='CODE_ONLY_UNVERIFIED' if kind=='manufacture_date_code' else 'PROVISIONAL_HUMAN_REVIEW'
    return dict(base,status=status,reason='Attributed reference plus provisional evidence; not technically verified',
                references=ids,evidence_id=case_evidence.get('media_id') if case_evidence else None)


def catalog_digest() -> str:
    return hashlib.sha256(CATALOG.read_bytes()).hexdigest()

GUIDANCE = Path(__file__).resolve().parents[1] / 'knowledge' / 'system_guidance_v2.json'


@lru_cache(maxsize=1)
def load_guidance() -> dict:
    """Validate curated, non-diagnostic system guidance against the source registry."""
    data=json.loads(GUIDANCE.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=2:
        raise KnowledgeError('Unknown system guidance schema')
    entries=data.get('systems')
    if not isinstance(entries,dict) or set(entries)!=KNOWN_SYSTEMS:
        raise KnowledgeError('System guidance must cover exactly 13 known inspection systems')
    known_sources={s['id'] for s in load_catalog()['source_records']}
    for system,rec in entries.items():
        if not isinstance(rec,dict):raise KnowledgeError('Invalid system guidance entry')
        codes=rec.get('feature_codes')
        if (not isinstance(codes,list) or not codes or len(codes)!=len(set(codes))
            or not all(isinstance(c,str) and re.fullmatch('[a-z][a-z0-9_]{2,59}',c) for c in codes)):
            raise KnowledgeError('Invalid or duplicate system feature codes')
        for key in ('visible_observation_examples','not_established_from_photographs',
                    'safe_capture_and_review_guidance'):
            v=rec.get(key)
            if not isinstance(v,str) or not 12<=len(v)<=300:
                raise KnowledgeError('System guidance section missing or unsafe length')
        if rec.get('no_automatic_diagnosis') is not True or rec.get('requires_human_verification') is not True:
            raise KnowledgeError('System guidance cannot waive professional verification')
        refs=rec.get('reference_ids')
        if not isinstance(refs,list) or len(refs)!=len(set(refs)) or not refs or any(s not in known_sources for s in refs):
            raise KnowledgeError('System guidance references unknown sources')
    return copy.deepcopy(data)


def build_knowledge_brief(systems, *, limit: int=4) -> str:
    """Compact per-work-order context: named feature vocabulary + uncertainty rules."""
    if not isinstance(systems,(tuple,list)) or not systems or len(systems)>13 or any(s not in KNOWN_SYSTEMS for s in systems):
        raise KnowledgeError('Unknown system in reference request')
    guidance=load_guidance()['systems']
    lines=[build_reference_brief(systems,limit=limit)]
    for system in dict.fromkeys(systems):
        rule=guidance[system]
        lines.append(f'SYSTEM {system}: allowed feature codes {", ".join(rule["feature_codes"])}. '
                     f'Visible cues to document (NOT confirmed defects): {rule["visible_observation_examples"]}. '
                     f'Cannot establish visually: {rule["not_established_from_photographs"]}. '
                     f'Action: {rule["safe_capture_and_review_guidance"]}.')
    lines.append('Unobserved features are UNKNOWN, not defect-free. This is a visual-evidence prompt, not legal advice or a testing instrument.')
    return '\n'.join(lines)


def guidance_digest() -> str:
    return hashlib.sha256(GUIDANCE.read_bytes()).hexdigest()
