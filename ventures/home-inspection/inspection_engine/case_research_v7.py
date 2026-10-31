"""Offline Michigan inspection research: bounded retrieval, citation receipts, and review.

No copyrighted standard extraction, network, scraping, verdict, or customer release.
A catalog entry is a RESEARCH LEAD, not a confirmed legal rule at a parcel.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import re

REGISTRY = Path(__file__).resolve().parents[1] / 'knowledge' / 'official_access_v7.json'
HEX = re.compile(r'[0-9a-f]{64}\Z')
DISCIPLINES = ('building','electrical','mechanical','plumbing')
HOSTS = {'ICC':'codes.iccsafe.org','NFPA':'www.nfpa.org','ASTM':'www.astm.org',
         'ANSI':'ibr.ansi.org','Michigan LARA':None,'CPSC':'www.cpsc.gov',
         'Westland':'www.cityofwestland.com','Westland Municode':'library.municode.com',
         'Livonia':'www.ci.livonia.mi.us','Detroit':'detroitmi.gov'}
ALLOW_LARA = {'www.michigan.gov','ars.apps.lara.state.mi.us'}
EXPECTED_PATHS = {
 'ICC_DIGITAL_BASIC':'/',
 'NFPA_FREE_VIEW':'/for-professionals/codes-and-standards',
 'ASTM_IBR_READING':'/standards-and-solutions/standards-and-publications/reading-room',
 'ASTM_E2018_24_INDEX':'/standards/e2018',
 'ANSI_IBR':'/',
 'MI_BCC_CODES':'/lara/bureau-list/bcc/rules-acts',
 'MI_BCC_OPEN_RULES':'/lara/bureau-list/bcc/rules-acts/rules/currently-open',
 'MI_BCC_JURISDICTIONS':'/lara/bureau-list/bcc',
 'MI_ADMIN_RULES':'/AdminCode/DeptBureauAdminCode',
 'CPSC_RECALL_API':'/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information',
 'WESTLAND_BUILDING':'/194/Building-Division',
 'WESTLAND_ORDINANCES':'/mi/westland',
 'LIVONIA_INSPECTIONS':'/',
 'DETROIT_CODES':'/departments/buildings-safety-engineering-and-environmental-department-bseed/bseed-divisions/construction-inspection/building-codes-ordinances-and-acts',
}
SCOPES = {'residential','commercial'}

class KnowledgeBlocked(ValueError):
    pass


def day(x):
    if not isinstance(x,str):raise KnowledgeBlocked('Canonical ISO date required')
    try:d=date.fromisoformat(x)
    except ValueError as exc:raise KnowledgeBlocked('Invalid calendar date') from exc
    if d.isoformat()!=x or d>date.today():raise KnowledgeBlocked('Future/noncanonical date')
    return d


def registry_validate(data):
    if not isinstance(data,dict) or data.get('schema_version')!=7 or data.get('state')!='MI':
        raise KnowledgeBlocked('Invalid Michigan v7 source registry')
    day(data.get('reviewed_on'))
    sources=data.get('sources')
    if not isinstance(sources,list) or len(sources)<12:raise KnowledgeBlocked('Expected a curated source registry')
    keys=set()
    known_identity={
      'ICC_DIGITAL_BASIC':'ICC','NFPA_FREE_VIEW':'NFPA','ASTM_IBR_READING':'ASTM',
      'ASTM_E2018_24_INDEX':'ASTM','ANSI_IBR':'ANSI','MI_BCC_CODES':'Michigan LARA',
      'MI_BCC_OPEN_RULES':'Michigan LARA','MI_BCC_JURISDICTIONS':'Michigan LARA',
      'MI_ADMIN_RULES':'Michigan LARA','CPSC_RECALL_API':'CPSC',
      'WESTLAND_BUILDING':'Westland','WESTLAND_ORDINANCES':'Westland Municode',
      'LIVONIA_INSPECTIONS':'Livonia','DETROIT_CODES':'Detroit'}
    for row in sources:
        if not isinstance(row,dict):raise KnowledgeBlocked('Invalid source row')
        name=row.get('id');publisher=row.get('publisher')
        if not isinstance(name,str) or not re.fullmatch('[A-Z][A-Z0-9_]{5,55}',name) or name in keys:
            raise KnowledgeBlocked('Invalid or duplicate source identifier')
        keys.add(name)
        if publisher not in HOSTS or name not in known_identity or known_identity[name]!=publisher:
            raise KnowledgeBlocked('Publisher/source identity must be approved')
        url=row.get('url')
        if not isinstance(url,str):raise KnowledgeBlocked('Missing official URL')
        parsed=urlsplit(url)
        expected=(ALLOW_LARA if publisher=='Michigan LARA' else
                  {'www.astm.org','store.astm.org'} if publisher=='ASTM' else {HOSTS[publisher]})
        if (parsed.scheme!='https' or parsed.hostname not in expected or parsed.username or parsed.password
            or parsed.port or parsed.fragment or parsed.path.startswith('//')
            or parsed.path not in {EXPECTED_PATHS[name],EXPECTED_PATHS[name].rstrip('/')+'/'}):
            raise KnowledgeBlocked('Publisher and official host do not match')
        if row.get('embedding') not in {'metadata_only','public_factual_metadata'}:
            raise KnowledgeBlocked('Read-only access cannot grant embedded full text')
        if row.get('access') not in {'read_only_online','federal_ibr_reading_room','public_metadata','official_public','official_link_reference'}:
            raise KnowledgeBlocked('Unreviewed access mode')
        if not isinstance(row.get('scope'),list) or not row['scope'] or not set(row['scope'])<=SCOPES:
            raise KnowledgeBlocked('Source scope missing')
        if type(row.get('edition_must_be_verified')) is not bool:
            raise KnowledgeBlocked('Edition verification flag required')
        if not isinstance(row.get('note'),str) or not row['note']:
            raise KnowledgeBlocked('Source limitations required')
    for required in ('ICC_DIGITAL_BASIC','NFPA_FREE_VIEW','ASTM_IBR_READING','MI_BCC_JURISDICTIONS','MI_BCC_OPEN_RULES','CPSC_RECALL_API'):
        if required not in keys:raise KnowledgeBlocked('Required authoritative source missing: '+required)
    municipalities=data.get('pilot_municipalities')
    if not isinstance(municipalities,list):raise KnowledgeBlocked('Municipality register missing')
    seen=set()
    for m in municipalities:
        key=(m.get('county'),m.get('municipality'),m.get('municipality_type'))
        if key in seen:raise KnowledgeBlocked('Duplicate local identity')
        seen.add(key)
        if not m.get('source_ids') or not set(m['source_ids'])<=keys:raise KnowledgeBlocked('Missing local references')
        if m.get('four_trade_ahj_verified') is not False or m.get('all_amendments_verified') is not False:
            raise KnowledgeBlocked('Pilot sources cannot self-certify full jurisdiction')
    for k in ('licensed_full_text_embedded','complete_michigan_municipalities_verified','professionally_adjudicated_field_cases'):
        if data.get(k)!=0:raise KnowledgeBlocked('Catalog cannot claim unproven complete coverage')
    return data


def registry_load(path=None):
    return registry_validate(json.loads(Path(path or REGISTRY).read_text(encoding='utf-8')))


def case_research(case,*,registry=None):
    """A per-property task list; no case-level code conclusion."""
    r=registry_validate(registry) if registry is not None else registry_load()
    if not isinstance(case,dict) or case.get('state') not in ('MI','Michigan'):
        raise KnowledgeBlocked('Michigan case required')
    if case.get('building_type') not in SCOPES:raise KnowledgeBlocked('Residential/commercial scope required')
    for field in ('county','municipality','municipality_type'):
        if not isinstance(case.get(field),str) or not case[field].strip():raise KnowledgeBlocked('Missing '+field)
    if case['municipality_type'] not in ('city','township','village'):
        raise KnowledgeBlocked('Unresolved legal municipality type')
    day(case.get('inspection_date'))
    exact=next((m for m in r['pilot_municipalities'] if
                (m['county'].casefold(),m['municipality'].casefold(),m['municipality_type'])==
                (case['county'].casefold(),case['municipality'].casefold(),case['municipality_type'])),None)
    essentials={'ICC_DIGITAL_BASIC','NFPA_FREE_VIEW','ASTM_IBR_READING','MI_BCC_OPEN_RULES','MI_BCC_JURISDICTIONS','MI_ADMIN_RULES','CPSC_RECALL_API'}
    essentials|=set(exact['source_ids'] if exact else ())
    reference={s['id']:s for s in r['sources']}
    sources=[{'id':key,'url':reference[key]['url'],'limit':reference[key]['note'],'access':reference[key]['access']}
             for key in sorted(essentials)]
    reqs=[{'discipline':k,'authority_status':'UNVERIFIED','authority_name':None,
           'authority_source_sha256':None,'amendments':'NOT_COMPLETE','adopted_edition':'UNVERIFIED'} for k in DISCIPLINES]
    return {'status':'RESEARCH_TASKS_OPEN','scope':case['building_type'],
            'locality':{'county':case['county'],'municipality':case['municipality'],'municipality_type':case['municipality_type'],
                        'indexed_official_city_sources':bool(exact)},
            'enforcement':reqs,'official_sources':sources,
            'tasks':['Confirm local/county/state AHJ separately for each discipline, including effective date and temporary assistance',
                     'Check enacted ordinances, amendments and pending changes against current government record and municipal clerk',
                     'Verify building use/occupancy, permit/construction/alteration date and operative edition before any provision comparison',
                     'Match rating-plate make, full model, serial/lot, manual revision and exact affected recall range',
                     'Link every material finding to original hashed visual evidence and unresolved alternatives',
                     'Escalate safety concerns, gaps, and specialist referrals to the qualified reviewer'],
            'code_compliance_verified':False,'all_hazards_found':False,'report_releasable':False}


def metadata_receipt(source_id:str, raw_bytes:bytes, seen_on:str, *, reviewer_id:str, content_rights:str):
    """Local offline observation of a document: digest only; do not publish its text."""
    r=registry_load();byid={x['id']:x for x in r['sources']}
    if source_id not in byid:raise KnowledgeBlocked('Unrecognized source')
    day(seen_on)
    if not isinstance(raw_bytes,bytes) or not raw_bytes or len(raw_bytes)>100_000_000:
        raise KnowledgeBlocked('Missing or excessive local review material')
    if not isinstance(reviewer_id,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{3,70}',reviewer_id):
        raise KnowledgeBlocked('Auditable reviewer identifier required')
    if content_rights not in ('read_only_verified_manually','public_government_record','licensed_machine_use_verified'):
        raise KnowledgeBlocked('Unreviewed document rights')
    if content_rights=='licensed_machine_use_verified':
        raise KnowledgeBlocked('Separate publisher-specific written rights and private document audit required')
    return {'source_id':source_id,'reviewed_on':seen_on,'reviewer_id':reviewer_id,
            'sha256':hashlib.sha256(raw_bytes).hexdigest(),'size_bytes':len(raw_bytes),
            'rights':content_rights,'full_text_retained_in_public_repo':False,
            'applicability_verified':False,'customer_release_allowed':False}


def compare_receipts(old:dict,new:dict):
    for r in (old,new):
        if not isinstance(r,dict) or not HEX.fullmatch(r.get('sha256','')):
            raise KnowledgeBlocked('Receipts need real SHA-256')
        day(r.get('reviewed_on'))
    if old.get('source_id')!=new.get('source_id') or old.get('reviewed_on')>new.get('reviewed_on'):
        raise KnowledgeBlocked('Mismatched source or nonmonotonic review history')
    changed=old['sha256']!=new['sha256']
    return {'source_id':old['source_id'],'changed':changed,
            'review_status':'REVERIFY_EDITION_AMENDMENTS_AND_AHJ' if changed else 'UNCHANGED_BYTES_NOT_PROOF_OF_CURRENT_ADOPTION',
            'automatic_legal_update_applied':False,'qualified_review_required':True}


def verify_case_provision(claim,case,*,registry=None):
    """Traceability check only. Cannot issue legal/code violation verdicts."""
    registry=registry_validate(registry) if registry is not None else registry_load()
    lookups={s['id']:s for s in registry['sources']}
    if not isinstance(claim,dict):raise KnowledgeBlocked('Claim must be a record')
    source=lookups.get(claim.get('source_id'))
    if not source or source['category'] not in {'government_rules','municipal_ordinances'}:
        raise KnowledgeBlocked('Exact provision needs enacted law/rules, not a viewer, draft, portal or index')
    if case.get('building_type') not in source['scope']:
        raise KnowledgeBlocked('Wrong building type')
    if claim.get('discipline') not in DISCIPLINES:raise KnowledgeBlocked('Invalid enforcing discipline')
    for key in ('edition','section','ahj_name','jurisdiction_document_sha256','evidence_sha256','reviewer_id'):
        if not isinstance(claim.get(key),str) or not claim[key].strip():raise KnowledgeBlocked('Missing '+key)
    for key in ('evidence_sha256','jurisdiction_document_sha256'):
        if not HEX.fullmatch(claim[key]):raise KnowledgeBlocked('Invalid evidence/authority SHA256')
    if claim['jurisdiction_document_sha256']!=case.get('ahj_receipt_sha256'):
        raise KnowledgeBlocked('Enforcement authority not verified for case')
    if claim['evidence_sha256'] not in case.get('verified_media_sha256',[]):
        raise KnowledgeBlocked('Claim lacks original hashed case evidence')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,69}',claim['section']):
        raise KnowledgeBlocked('Section number not a bounded reference')
    if claim.get('automated_violation_confirmed') or claim.get('root_cause_confirmed'):
        raise KnowledgeBlocked('Automated conclusions forbidden')
    return {'status':'SOURCE_AND_MEDIA_TRACEABLE_HUMAN_PROVISION_REVIEW_REQUIRED',
            'section':claim['section'],'edition':claim['edition'],'authority_verified_by_software':False,
            'qualified_inspector_decision_required':True,'customer_release_allowed':False}


def agent_brief_v7(case,systems):
    """Bounded policy context, not proprietary standard text or invented legal findings."""
    try:p=case_research(case)
    except KnowledgeBlocked as e:return 'KNOWLEDGE_V7: BLOCKED_CASE_METADATA '+str(e)+'; no legal conclusion permitted.'
    state={x['discipline']:x['authority_status'] for x in p['enforcement']}
    return ('KNOWLEDGE_V7_REFERENCE_POLICY: official online code reading is not permission to embed, scrape or reproduce full text. '
            'Never assert a code violation, safety guarantee, actual root cause, or recall applicability from a link. '
            'CASE_SCOPE='+p['scope']+'; AHJ_STATUS='+json.dumps(state,sort_keys=True)+'; '
            'SYSTEMS='+json.dumps([x for x in systems if isinstance(x,str)])+'; '
            'REQUIRE: source edition and exact section, date of construction/alteration, official jurisdiction receipt, '
            'hashed photo/video evidence, alternative explanations, severity and human technical review. '
            'Unknown or dangerous conditions must remain open and be promptly escalated. '
            'Internal technical analysis is not verbatim customer-report content.')
