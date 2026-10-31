"""Fail-closed Michigan source registry, rights permissions, AHJ and exact-claim receipts.

Official reference metadata and human-authored summaries are knowledge; they
are never themselves proof of a defect, code violation or verified recall.
No network, scraping, downloaded text, or automatic rights assumptions.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

CATALOG = Path(__file__).resolve().parents[1] / 'knowledge' / 'governed_sources_v5.json'
HEX = re.compile(r'[a-f0-9]{64}\Z')
CODE_ID = re.compile(r'[A-Z][A-Z0-9_]{4,64}\Z')
RIGHTS = {'government_reference','metadata_only','official_index_only','official_online_reference','licensed_local'}
SCOPE = {'residential','commercial'}
PUBLISHER_HOSTS = {
  'Michigan LARA': 'www.michigan.gov', 'ICC': 'www.iccsafe.org',
  'NFPA': 'www.nfpa.org', 'ASTM': 'store.astm.org',
  'InterNACHI': 'www.nachi.org','ASHI': 'www.homeinspector.org',
  'CPSC': 'www.cpsc.gov','Bradford White':'forthepro.bradfordwhite.com',
  'Rheem':'www.rheem.com','Carrier':'www.carrier.com','Goodman':'www.goodmanmfg.com'
}

class ReferenceBlock(ValueError):
    pass


def validate_registry(data):
    if not isinstance(data,dict) or data.get('schema_version')!=5 or data.get('jurisdiction')!='Michigan':
        raise ReferenceBlock('Invalid knowledge registry version or jurisdiction')
    try: reviewed=date.fromisoformat(data['reviewed_on'])
    except (KeyError,TypeError,ValueError) as e: raise ReferenceBlock('Missing registry review date') from e
    if reviewed>date.today():raise ReferenceBlock('Source review date is in the future')
    rows=data.get('sources');ids=set()
    if not isinstance(rows,list) or len(rows)<12:raise ReferenceBlock('Incomplete primary-source index')
    for s in rows:
        if not isinstance(s,dict):raise ReferenceBlock('Invalid reference entry')
        ident=s.get('id');pub=s.get('publisher');rights=s.get('rights')
        if not isinstance(ident,str) or not CODE_ID.fullmatch(ident) or ident in ids:
            raise ReferenceBlock('Source ID missing, duplicate, or invalid')
        ids.add(ident)
        u=urlsplit(s.get('url',''))
        if u.scheme!='https' or u.username or u.password or u.port or u.hostname!=PUBLISHER_HOSTS.get(pub):
            raise ReferenceBlock('Official publisher host mismatch')
        if rights not in RIGHTS or not s.get('status') or not isinstance(s.get('kind'),str):
            raise ReferenceBlock('Source rights/status incomplete')
        if not isinstance(s.get('systems'),list) or not s['systems'] or not set(s['scope']).issubset(SCOPE):
            raise ReferenceBlock('Source applicability incomplete')
        if rights=='licensed_local' and (not s.get('license_document_sha256') or not s.get('machine_use_permission')):
            raise ReferenceBlock('Do not embed proprietary text without explicit machine-use rights')
        if s.get('full_text_embedded',False) and rights!='licensed_local':
            raise ReferenceBlock('Full copyrighted text cannot be bundled under a metadata license')
    expected={'ICC_COPYRIGHT','NFPA_COPYRIGHT','ASTM_COPYRIGHT','MI_LARA_RULES','MI_STATEWIDE_AHJ_20261006','CPSC_RECALL_API','ASTM_E2018_24'}
    if not expected.issubset(ids):raise ReferenceBlock('Required source controls absent')
    coverage=data.get('local_coverage')
    if not isinstance(coverage,dict) or any(type(v)!=int or v<0 for v in coverage.values()):
        raise ReferenceBlock('Coverage counts must be honest nonnegative integers')
    return deepcopy(data)


def load_registry(path:Path|None=None):
    return validate_registry(json.loads(Path(path or CATALOG).read_text(encoding='utf-8')))


def prepare_case_research(case:dict, *, registry:dict|None=None)->dict:
    """Prepare tasks, NOT automatic declaration of jurisdiction/code applicability."""
    r=validate_registry(registry) if registry is not None else load_registry()
    if case.get('state') not in ('MI','Michigan') or case.get('building_type') not in SCOPE:
        raise ReferenceBlock('Case requires Michigan state and residential/commercial type')
    if not isinstance(case.get('county'),str) or not case['county'].strip() or not isinstance(case.get('municipality'),str) or not case['municipality'].strip():
        raise ReferenceBlock('County and municipality required for AHJ research')
    try: date.fromisoformat(case['inspection_date'])
    except (KeyError,TypeError,ValueError) as e:raise ReferenceBlock('Inspection date is required') from e
    scopes={case['building_type']}
    relevant=[s for s in r['sources'] if scopes.intersection(s['scope'])]
    return {'case_scope':case['building_type'], 'county':case['county'], 'municipality':case['municipality'],
            'source_index':[{'id':s['id'],'url':s['url'],'status':s['status'],'rights':s['rights']} for s in relevant],
            'ahj_disciplines':{k:'NOT_VERIFIED' for k in ('building','electrical','mechanical','plumbing')},
            'required_tasks':[
                'Match the property to the official statewide jurisdiction list and confirm each discipline with the enforcing authority',
                'Verify local ordinance amendments, zoning, occupancy and fire authority for the exact parcel',
                'Establish construction/alteration permit dates and the adopted edition applicable to that work',
                'Inspect original evidence and retain line-of-evidence hashes before making observations',
                'Match make/model/serial against the manufacturer instructions and recalls by exact identifiers',
                'Require qualified inspector review and referrals; do not state code violation or root cause from a photo'
            ],'case_code_compliance_verified':False,'customer_release_allowed':False}


def verify_provision_receipt(receipt:dict, case:dict, *,registry:dict|None=None)->dict:
    """Check source traceability; passing is NOT legal adjudication or a code verdict."""
    catalog=validate_registry(registry) if registry is not None else load_registry()
    byid={s['id']:s for s in catalog['sources']}
    sid=receipt.get('source_id')
    src=byid.get(sid)
    if not src or src['kind'] in ('copyright_terms','enforcement_directory','recall_database'):
        raise ReferenceBlock('Claim needs an applicable technical or legal source, not a rights/lookup page')
    if case.get('building_type') not in src['scope']:
        raise ReferenceBlock('Source does not apply to this building type')
    for field in ('edition','section','official_authority','jurisdiction_evidence_sha256','inspector_evidence_sha256','human_reviewer_id'):
        if not isinstance(receipt.get(field),str) or not receipt[field].strip():
            raise ReferenceBlock('Provision receipt missing '+field)
    for k in ('jurisdiction_evidence_sha256','inspector_evidence_sha256'):
        if not HEX.fullmatch(receipt[k]):raise ReferenceBlock('Invalid recorded SHA-256 for '+k)
    if receipt['jurisdiction_evidence_sha256'] != case.get('ahj_receipt_sha256'):
        raise ReferenceBlock('Jurisdiction authority document does not match this case')
    if receipt['inspector_evidence_sha256'] not in case.get('verified_media_sha256',[]):
        raise ReferenceBlock('Original inspection evidence not found in verified case manifest')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,70}',receipt['section']):
        raise ReferenceBlock('Section identifier invalid; exact text must be checked independently')
    expected_editions={'MI_RES_CODE_2015':'2015','MI_COMM_CODE_2021':'2021'}
    if sid in expected_editions and receipt['edition']!=expected_editions[sid]:
        raise ReferenceBlock('Edition differs from official source index; verify adoption timeline')
    if receipt.get('code_violation_confirmed') is True or receipt.get('root_cause_confirmed') is True:
        raise ReferenceBlock('No automatic code verdicts or proven root cause from a source receipt')
    return {'status':'PROVISION_RECEIPT_TRACEABLE_REVIEW_PENDING','source_id':sid,'case_evidence_sha256':receipt['inspector_evidence_sha256'],
            'section':receipt['section'],'edition':receipt['edition'],'scope_checked':True,
            'authority_adoption_confirmed':False,'legal_conclusion_approved':False,'customer_release_allowed':False}


def source_change_queue(old_digest:dict,new_digest:dict)->list[dict]:
    """Human-review queue for downloaded official snapshots; no network or automation."""
    if not isinstance(old_digest,dict) or not isinstance(new_digest,dict):raise ReferenceBlock('Digest maps required')
    tasks=[]
    for key,value in new_digest.items():
        if not isinstance(key,str) or not CODE_ID.fullmatch(key) or not isinstance(value,str) or not HEX.fullmatch(value):
            raise ReferenceBlock('Untrusted source snapshot digest')
        prev=old_digest.get(key)
        if prev is not None and (not isinstance(prev,str) or not HEX.fullmatch(prev)):
            raise ReferenceBlock('Untrusted prior snapshot digest')
        if prev!=value:tasks.append({'source_id':key,'status':'CHANGED_REVERIFY_BEFORE_USE','old_sha256':prev,'new_sha256':value})
    for key in old_digest.keys()-new_digest.keys():
        tasks.append({'source_id':key,'status':'MISSING_REVIEW','old_sha256':old_digest[key]})
    return sorted(tasks,key=lambda x:x['source_id'])


def case_agent_packet(case:dict, systems:list[str])->str:
    """Small, scoped, copyright-safe research packet; never raw copyrighted texts."""
    plan=prepare_case_research(case)
    if not isinstance(systems,list) or not systems or any(not isinstance(s,str) for s in systems):
        raise ReferenceBlock('Need delegated inspection systems')
    refs=load_registry()['sources']
    scoped=[{'id':s['id'],'status':s['status'],'rights':s['rights']} for s in refs
            if ('all' in s['systems'] or set(systems).intersection(s['systems'])) and case['building_type'] in s['scope']]
    return 'GOVERNED_MICHIGAN_SOURCE_PACKET_JSON: '+json.dumps({
      'knowledge_is_not_case_evidence':True,'county':plan['county'],'municipality':plan['municipality'],
      'building_type':case['building_type'],'references':scoped,
      'ahj_status':'UNVERIFIED','edition_status':'CASE_SPECIFIC_VERIFICATION_REQUIRED',
      'prohibited_inferences':['code compliant','code violation confirmed','root cause proven','no defects present','recall confirmed from appearance'],
      'required_review':'QUALIFIED_INSPECTOR','release_allowed':False},sort_keys=True)


def verify_manufacturer_manual_receipt(manual:dict, *, registry:dict|None=None)->dict:
    """Exact product match and license metadata. Never assume manuals cover all variants."""
    sources=(validate_registry(registry) if registry is not None else load_registry())['sources']
    allowed={s['publisher']:s for s in sources if s['kind']=='manufacturer_reference'}
    brand=manual.get('manufacturer')
    if brand not in allowed:raise ReferenceBlock('No verified manufacturer source for this brand')
    for key in ('exact_model','manual_revision','retrieved_on','reviewer_id','manual_sha256'):
        if not isinstance(manual.get(key),str) or not manual[key].strip():
            raise ReferenceBlock('Manufacturer manual receipt missing '+key)
    if not HEX.fullmatch(manual['manual_sha256']):raise ReferenceBlock('Manual snapshot digest invalid')
    try: date.fromisoformat(manual['retrieved_on'])
    except ValueError as e:raise ReferenceBlock('Invalid manual retrieval date') from e
    if manual['retrieved_on'] > date.today().isoformat():raise ReferenceBlock('Future manual retrieval date')
    # Model-specific and version-specific matching, not name-only guesses.
    if manual.get('pictured_rating_plate_model')!=manual['exact_model'] or manual.get('model_match_human_verified') is not True:
        raise ReferenceBlock('Manufacturer instructions not matched to the photographed model')
    if manual.get('installation_date_claim') or manual.get('warranty_active_claim'):
        raise ReferenceBlock('Manufacturer instructions cannot certify installation/warranty status')
    if manual.get('licensed_for_automated_full_text') is True and not (HEX.fullmatch(manual.get('license_sha256','')) and manual.get('machine_use_rights_granted') is True):
        raise ReferenceBlock('Full manual embedding requires explicit machine-use permission')
    return {'status':'MANUFACTURER_MANUAL_IDENTITY_CHECKED_HUMAN_REVIEW_PENDING',
            'manufacturer':brand,'model':manual['exact_model'], 'manual_revision':manual['manual_revision'],
            'manual_sha256':manual['manual_sha256'],
            'source_index_id':allowed[brand]['id'],'approved_for_copyrighted_full_text':False,
            'installation_date_confirmed':False,'defect_root_cause_confirmed':False,
            'customer_release_allowed':False}


def verify_recall_match(match:dict)->dict:
    """A CPSC result can prompt safety review, not automatic recall certification."""
    for key in ('recall_number','source_url','product_model','pictured_model','checked_on','reviewed_by'):
        if not isinstance(match.get(key),str) or not match[key].strip():
            raise ReferenceBlock('Recall verification receipt incomplete: '+key)
    u=urlsplit(match['source_url'])
    if u.scheme!='https' or u.hostname not in {'www.cpsc.gov','www.saferproducts.gov'}:
        raise ReferenceBlock('Official CPSC recall reference required')
    if match['pictured_model']!=match['product_model'] or match.get('model_match_verified') is not True:
        raise ReferenceBlock('Recall listing not tied to exact pictured product')
    try: checked=date.fromisoformat(match['checked_on'])
    except ValueError as e:raise ReferenceBlock('Invalid recall lookup date') from e
    if checked>date.today():raise ReferenceBlock('Future recall check')
    return {'status':'POTENTIAL_RECALL_MATCH_FOR_HUMAN_CONFIRMATION',
            'recall_number':match['recall_number'],'exact_model_matched':True,
            'serial_lot_range_confirmed':False,'recall_eligibility_confirmed':False,
            'qualified_review_required':True,'customer_release_allowed':False}


def safe_agent_reference_brief(property_context:dict,systems:list[str])->str:
    """Never drop original work orders because county or permit facts are missing.

    Instead make unverified AHJ explicit in the LLM context, with no code verdict.
    """
    if not isinstance(property_context,dict) or property_context.get('state') not in ('MI','Michigan'):
        return 'MICHIGAN_AHJ_REFERENCE_STATUS: NOT_APPLICABLE'
    building=property_context.get('building_type')
    scope={'residential_one_two_family':'residential',
           'residential':'residential', 'commercial':'commercial',
           'commercial_pca':'commercial','commercial_general':'commercial'}.get(building)
    if not scope or not property_context.get('county') or not property_context.get('municipality'):
        return ('MICHIGAN_AHJ_REFERENCE_STATUS: MISSING_CASE_FACTS; '
                'do not assert code compliance or a violation; obtain county, municipality, '
                'building type, permit/alteration history and correct enforcing agency')
    c={'state':'MI','county':property_context['county'],'municipality':property_context['municipality'],
       'building_type':scope,'inspection_date':property_context.get('inspection_date','')}
    try:
        original=case_agent_packet(c,systems)
        # Add the city/township/village case research only when the inspector
        # actually supplied that classification. Never silently invent "city".
        locality_type=property_context.get('municipality_type')
        if not locality_type:
            return original+'\nGOVERNED_CASE_RESEARCH_V6_STATUS: MISSING_MUNICIPALITY_TYPE; obtain verified legal locality class'
        from .coverage_expansion import case_knowledge_packet
        case_v6=dict(c,municipality_type=locality_type)
        try:return original+'\n'+case_knowledge_packet(case_v6,systems[0] if systems else 'site')
        except ReferenceBlock:
            return original+'\nGOVERNED_CASE_RESEARCH_V6_STATUS: CASE_LOCALITY_UNVERIFIED; request current AHJ records'
    except ReferenceBlock:
        return ('MICHIGAN_AHJ_REFERENCE_STATUS: UNVERIFIED_OR_INVALID_CASE; '
                'no code conclusion, request qualified authority review')
