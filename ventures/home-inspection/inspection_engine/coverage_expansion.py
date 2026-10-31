"""Michigan municipal + exact-model source intake and specialty coverage, v6.

Offline and fail-closed. An indexed URL, a file hash, or a manual match is not a
legal authority decision, code verdict, manufacturer approval, or inspection.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import re

from .knowledge_registry import ReferenceBlock

BASE = Path(__file__).resolve().parents[1] / 'knowledge'
CATALOGS = {'municipal': 'municipal_pilot_v6.json',
            'manufacturers': 'manufacturer_portals_v6.json',
            'specialties': 'specialty_playbooks_v6.json'}
SHA256 = re.compile(r'[a-f0-9]{64}\Z')
ID = re.compile(r'[A-Z][A-Z0-9_]{3,80}\Z')
TRUSTED_MUNICIPAL = {
 'MI_WAYNE_WESTLAND_CITY': ('Wayne','Westland','city','www.cityofwestland.com'),
 'MI_WAYNE_LIVONIA_CITY': ('Wayne','Livonia','city','livonia.gov'),
 'MI_WAYNE_DETROIT_CITY': ('Wayne','Detroit','city','detroitmi.gov'),
}
TRUSTED_MANUFACTURERS = {
 'A. O. Smith':'www.hotwater.com', 'Carrier':'www.carrier.com',
 'Goodman':'www.goodmanmfg.com','Rheem':'www.rheem.com',
}
FOUR_TRADES = ('building', 'electrical', 'mechanical', 'plumbing')
SCOPES = ('residential', 'commercial')


def _day(value):
    if not isinstance(value, str):
        raise ReferenceBlock('Expected canonical ISO date')
    try: d = date.fromisoformat(value)
    except ValueError as e: raise ReferenceBlock('Invalid ISO date') from e
    if d.isoformat() != value or d > date.today():
        raise ReferenceBlock('Non-canonical or future date')
    return d


def _web(url, host):
    if not isinstance(url, str): raise ReferenceBlock('Official URL must be text')
    u = urlsplit(url)
    if (u.scheme != 'https' or not u.hostname or u.hostname != host or u.username
            or u.password or u.port or u.fragment):
        raise ReferenceBlock('Official source host/URL mismatch')
    return url


def load_expansion(kind, path=None):
    if kind not in CATALOGS: raise ReferenceBlock('Unsupported knowledge catalog')
    raw = json.loads(Path(path or BASE / CATALOGS[kind]).read_text(encoding='utf-8'))
    validate_expansion(kind, raw)
    return raw


def validate_expansion(kind, data):
    if kind not in CATALOGS or not isinstance(data, dict) or data.get('schema_version') != 6:
        raise ReferenceBlock('Wrong knowledge schema')
    _day(data.get('reviewed_on'))
    if kind == 'municipal':
        state = data.get('state_authority', {})
        if state.get('id') != 'MI_LARA_BCC_AHJ_LIST': raise ReferenceBlock('Michigan state jurisdiction list required')
        _web(state.get('url'), 'www.michigan.gov')
        _day(state.get('published_revision'))
        rows=data.get('locations')
        if not isinstance(rows,list) or len(rows)<3:raise ReferenceBlock('Municipality pilot sources absent')
        ids=set(); keys=set()
        for row in rows:
            if not isinstance(row, dict) or not ID.fullmatch(row.get('id','')) or row['id'] in ids:
                raise ReferenceBlock('Invalid or duplicate municipality ID')
            ids.add(row['id'])
            if row['id'] not in TRUSTED_MUNICIPAL:
                raise ReferenceBlock('Municipality needs separately verified domain approval')
            if tuple(row.get(k) for k in ('county','municipality','type','publisher_host')) != TRUSTED_MUNICIPAL[row['id']]:
                raise ReferenceBlock('Municipality and official publisher identity mismatch')
            if row.get('county') not in ('Wayne', 'Oakland', 'Macomb', 'Kent', 'Ingham'):
                raise ReferenceBlock('Pilot county not reviewed')
            if not isinstance(row.get('municipality'),str) or not row['municipality'].strip() or row.get('type') not in ('city','township','village'):
                raise ReferenceBlock('Municipality identity incomplete')
            key=(row['county'].casefold(), row['municipality'].casefold(),row['type'])
            if key in keys: raise ReferenceBlock('Duplicate municipality and type')
            keys.add(key)
            for u in ('source_url','additional_url'):
                official_host=row.get('publisher_host')
                secondary_host='www.livonia.gov' if official_host=='livonia.gov' and u=='additional_url' else official_host
                _web(row.get(u),secondary_host)
            if not isinstance(row.get('source_scope'),str) or not row['source_scope'].strip():
                raise ReferenceBlock('Scope note required')
            for flag in ('verified_case_ahj','verified_local_amendments','applicable_to_exact_parcel','full_local_ordinance_text_embedded'):
                if row.get(flag) is not False:
                    raise ReferenceBlock('Source index may never self-certify municipal applicability/rights')
            if type(row.get('edition_conflict')) is not bool:raise ReferenceBlock('Conflict status must be explicit')
    elif kind == 'manufacturers':
        rows=data.get('portals')
        if not isinstance(rows,list) or not rows:raise ReferenceBlock('Missing manufacturer portals')
        brands=set()
        for row in rows:
            name=row.get('brand')
            if not isinstance(name,str) or name in brands:raise ReferenceBlock('Duplicate manufacturer')
            brands.add(name)
            if row.get('host') != TRUSTED_MANUFACTURERS.get(name):
                raise ReferenceBlock('Unreviewed manufacturer domain')
            _web(row.get('url'),row.get('host'))
            if not isinstance(row.get('systems'),list) or not set(row['systems']).issubset({'hvac','water_heating'}) or not row['systems']:
                raise ReferenceBlock('Unscoped manufacturer source')
            if not isinstance(row.get('document_types'),list) or not row['document_types']:
                raise ReferenceBlock('Document types required')
            if row.get('manuals_locally_verified') != 0:raise ReferenceBlock('Do not invent locally verified manuals')
    else:
        rows=data.get('topics')
        if not isinstance(rows,list) or len(rows)<3:raise ReferenceBlock('Missing specialist topics')
        ids=set()
        for row in rows:
            if not ID.fullmatch(row.get('id','')) or row['id'] in ids:raise ReferenceBlock('Duplicate specialty')
            ids.add(row['id'])
            if not isinstance(row.get('scope'),list) or not row['scope'] or not set(row['scope']).issubset(SCOPES):
                raise ReferenceBlock('Invalid specialty scope')
            url=row.get('sop_reference_url')
            host='www.nachi.org' if 'residential' in row['scope'] else 'store.astm.org'
            _web(url,host)
            for key in ('visual_cues','possible_causes','alternative_explanations','request_more_evidence','urgent_triggers','not_proven_by_photo'):
                if not isinstance(row.get(key),list) or not row[key] or any(not isinstance(x,str) or not x for x in row[key]):
                    raise ReferenceBlock('Specialty differential incomplete: '+key)
            if not isinstance(row.get('referral'),str) or 'PENDING' not in row.get('status','') and 'REQUIRES' not in row.get('status',''):
                raise ReferenceBlock('Specialty not marked pending')
    return True


def _case(case):
    if not isinstance(case,dict) or case.get('state') not in ('MI','Michigan') or case.get('building_type') not in SCOPES:
        raise ReferenceBlock('Case needs MI state and residential/commercial type')
    for key in ('county','municipality','municipality_type'):
        if not isinstance(case.get(key),str) or not case[key].strip(): raise ReferenceBlock('Case needs '+key)
    if case['municipality_type'] not in ('city','township','village'): raise ReferenceBlock('Unknown municipality class')
    _day(case.get('inspection_date'))


def plan_municipal_verification(case,*,catalog=None):
    _case(case)
    data=catalog if catalog is not None else load_expansion('municipal')
    validate_expansion('municipal',data)
    matches=[r for r in data['locations'] if (r['county'].casefold(),r['municipality'].casefold(),r['type']) ==
             (case['county'].casefold(),case['municipality'].casefold(),case['municipality_type'])]
    if len(matches)>1:raise ReferenceBlock('Ambiguous municipality')
    row=matches[0] if matches else None
    checks={trade:{'state':'AWAITING_CASE_AHJ_CONFIRMATION','authority_name':None,
                   'authority_receipt_sha256':None,'local_amendments_status':'NOT_VERIFIED'} for trade in FOUR_TRADES}
    tickets=[{'discipline':trade,'task':'Verify STATE/COUNTY/LOCAL on current LARA statewide list for exact parcel; confirm authority and permit/alteration history; obtain applicable text and amendments'} for trade in FOUR_TRADES]
    tickets += [{'discipline':'fire','task':'Confirm fire marshal and occupancy rules; separate from general building enforcement'},
                {'discipline':'zoning_property_maintenance','task':'Check official local ordinances, property maintenance, rental/occupancy rules, their amendments and effective dates'}]
    if row and row['edition_conflict']:
        tickets.append({'discipline':'conflicting_publications','task':'Older local page conflicts with newer city/state edition references: verify legal effective edition and construction/permit dates'})
    return {'status':'CASE_AHJ_AND_AMENDMENT_VERIFICATION_REQUIRED','jurisdiction_indexed':row is not None,
            'source_url':row['source_url'] if row else data['state_authority']['url'],
            'other_local_source':row['additional_url'] if row else None,'statewide_list_url':data['state_authority']['url'],
            'published_statewide_list_revision':data['state_authority']['published_revision'],
            'municipality_source_id':row['id'] if row else None,
            'edition_conflict_flag':bool(row and row['edition_conflict']),
            'ahj_by_discipline':checks,'verification_tickets':tickets,
            'all_municipal_amendments_verified':False,'code_violations_confirmed':False,
            'customer_release_allowed':False}


def validate_local_snapshot(path:Path,root:Path,receipt:dict,*,source_url:str):
    """Custody-only check for a private source snapshot. No automatic legal authority decision."""
    root=root.resolve(strict=True)
    raw=Path(path)
    if raw.is_symlink():raise ReferenceBlock('Snapshot may not be a symlink')
    p=raw.resolve(strict=True)
    if not p.is_relative_to(root) or not p.is_file():
        raise ReferenceBlock('Snapshot must remain inside private evidence root')
    if p.stat().st_size<30 or p.stat().st_size>10_000_000:
        raise ReferenceBlock('Snapshot outside permitted file size')
    if receipt.get('source_url')!=source_url or not source_url.startswith('https://'):
        raise ReferenceBlock('Snapshot URL differs from source record')
    if receipt.get('sha256')!=hashlib.sha256(p.read_bytes()).hexdigest():
        raise ReferenceBlock('Source snapshot hash mismatch')
    _day(receipt.get('retrieved_on'))
    if not isinstance(receipt.get('reviewer_id'),str) or not receipt['reviewer_id'].strip():
        raise ReferenceBlock('Human reviewer identity required')
    if receipt.get('legal_applicability_confirmed') is True or receipt.get('case_code_violation_confirmed') is True:
        raise ReferenceBlock('Snapshot alone cannot certify legal applicability or violation')
    return {'status':'SNAPSHOT_HASH_VERIFIED_NOT_LEGAL_APPLICABILITY',
            'source_sha256':receipt['sha256'],'source_url':source_url,
            'authenticated_government_copy':False,'human_AHJ_confirmation_required':True}


def compare_snapshots(old:dict,new:dict):
    for x in (old,new):
        if not isinstance(x,dict) or not isinstance(x.get('source_url'),str) or not SHA256.fullmatch(x.get('sha256','')):
            raise ReferenceBlock('Valid snapshot receipts required')
        _day(x.get('retrieved_on'))
    if old['source_url']!=new['source_url']:
        raise ReferenceBlock('Different URLs cannot be compared as a revision')
    changed=old['sha256']!=new['sha256']
    return {'source_url':old['source_url'],'content_changed':changed,
            'status':'REVIEW_REQUIRES_HUMAN_RECHECK' if changed else 'NO_HASH_CHANGE_NOT_FRESHNESS_PROOF',
            'code_applicability_reverified':False,'disallow_automatic_code_update':True}


def manufacturer_lookup(brand:str,model:str,system:str,*,catalog=None):
    data=catalog if catalog is not None else load_expansion('manufacturers')
    validate_expansion('manufacturers',data)
    if not isinstance(brand,str) or not isinstance(model,str) or '..' in model or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/ ._\-]{1,79}',model):
        raise ReferenceBlock('Exact photographed manufacturer and model required')
    rows=[r for r in data['portals'] if r['brand'].casefold()==brand.strip().casefold() and system in r['systems']]
    if len(rows)!=1:raise ReferenceBlock('Manufacturer and system portal not indexed')
    row=rows[0]
    return {'status':'EXACT_MODEL_MANUAL_LOOKUP_REQUIRED','brand':row['brand'],
            'pictured_model':model.strip(),'system':system,'official_portal_url':row['url'],
            'manual_file_verified':False,'applicable_revision_verified':False,
            'serial_or_lot_applicability_verified':False,'manufacturer_approved_cause':False,
            'customer_release_allowed':False}


def verify_model_manual_receipt(root:Path,manual:Path,receipt:dict,*,lookup:dict):
    if lookup.get('status')!='EXACT_MODEL_MANUAL_LOOKUP_REQUIRED' or receipt.get('brand')!=lookup.get('brand'):
        raise ReferenceBlock('Manual not tied to official manufacturer lookup')
    if receipt.get('model')!=lookup.get('pictured_model') or not receipt.get('rating_plate_image_sha256'):
        raise ReferenceBlock('Exact model and rating plate required, no guessed substitutions')
    if not SHA256.fullmatch(receipt['rating_plate_image_sha256']):
        raise ReferenceBlock('Invalid photographed rating plate hash')
    if receipt.get('portal_url')!=lookup['official_portal_url'] or not isinstance(receipt.get('revision'),str) or not receipt['revision'].strip():
        raise ReferenceBlock('Manufacturer origin/revision not verified')
    _day(receipt.get('reviewed_on'))
    if receipt.get('machine_full_text_ingest_authorized') is not False:
        raise ReferenceBlock('Do not assume publisher permission for full-text machine indexing')
    evidence=validate_local_snapshot(manual,root,{'source_url':receipt['portal_url'],
         'sha256':receipt.get('manual_sha256'), 'retrieved_on':receipt['reviewed_on'],
         'reviewer_id':receipt.get('reviewer_id'),'legal_applicability_confirmed':False},
         source_url=receipt['portal_url'])
    return {'status':'EXACT_MODEL_DOCUMENT_MATCH_PENDING_QUALIFIED_REVIEW',
            'manual_sha256':evidence['source_sha256'],'pictured_model':receipt['model'],
            'manufacturer_guidance_verified_for_installed_revision':False,
            'cause_or_code_compliance_confirmed':False, 'manual_full_text_embedded':False,
            'customer_release_allowed':False}


def specialty_work_orders(scope,existing_covered_topics=(),*,catalog=None):
    if scope not in SCOPES:raise ReferenceBlock('Residential/commercial SOP selection required')
    data=catalog if catalog is not None else load_expansion('specialties')
    validate_expansion('specialties',data)
    covered=set(existing_covered_topics)
    if any(not isinstance(t,str) for t in covered):raise ReferenceBlock('Invalid scope attestations')
    rows=[r for r in data['topics'] if scope in r['scope']]
    return {'scope':scope,'status':'SUPPLEMENTAL_TASKS_NEED_INSPECTOR_ASSIGNMENT',
            'tasks':[{'id':r['id'],'title':r['title'],'review_status':'PENDING' if r['id'] not in covered else 'CLAIMED_COVERAGE_REQUIRES_EVIDENCE',
                      'look_for':r['visual_cues'],'possible_mechanisms_not_diagnoses':r['possible_causes'],
                      'alternative_causes':r['alternative_explanations'],
                      'further_evidence':r['request_more_evidence'],'urgent_flags':r['urgent_triggers'],
                      'specialist_referral':r['referral'],'cannot_prove_from_photos':r['not_proven_by_photo'],
                      'reference_url':r['sop_reference_url']} for r in rows],
            'inspected_and_operationally_tested':False,'SOP_compliance_certified':False,
            'customer_release_allowed':False}


def case_knowledge_packet(case:dict,system:str,*,include_specialties=True)->str:
    """Compact informational packet; all original evidence gates still apply."""
    locality=plan_municipal_verification(case)
    packet={'schema':6,'kind':'CASE_RESEARCH_NOT_FACTUAL_VERDICT',
            'case_ahj':{'status':locality['status'],'edition_conflict_flag':locality['edition_conflict_flag'],
                        'source_url':locality['source_url'],'required_checks':list(FOUR_TRADES)},
            'never_assert':'code compliance, root cause, defect-free condition, or complete inspection based solely on photos',
            'release_authority':False}
    if include_specialties:
        relevant={'interior':('FIREPLACE_HEARTH','GARAGE_DOOR','COMMERCIAL_FIRE_LIFE_SAFETY'),
                  'electrical':('COMMERCIAL_FIRE_LIFE_SAFETY',)}.get(system,())
        packet['supplemental_work_orders']=[{'id':task['id'],
            'warning_signals':task['look_for'][:2],
            'human_follow_up_required':True} for task in specialty_work_orders(case['building_type'])['tasks']
            if task['id'] in relevant]
    from .hazard_sweep import load_hazard_sweep
    risk=next((r for r in load_hazard_sweep()['topics'] if r['system']==system),None)
    if risk:
        packet['serious_hazard_triage']={'id':risk['id'],'look_for':risk['signal'],
            'possible_cause_not_proven':risk['possible_mechanisms'],
            'alternative_explanation':risk['alternative_explanations'],
            'referral_to_consider':risk['referral']}
    return 'GOVERNED_CASE_RESEARCH_V6_JSON: '+json.dumps(packet,sort_keys=True,ensure_ascii=True)


def lookup_indexed_model_manual(brand:str, model:str, *,path=None)->dict:
    """Find exact official manufacturer listing, never presume a true installed match.

    A document number and model list are public index metadata, NOT actual manual
    text and NOT evidence that an appliance has a particular revision/serial.
    """
    data=json.loads(Path(path or BASE / 'model_manual_index_v6.json').read_text(encoding='utf-8'))
    if data.get('schema_version')!=6 or not isinstance(data.get('documents'),list):
        raise ReferenceBlock('Bad exact-model document index')
    _day(data.get('reviewed_on'))
    ids=set();found=[]
    for item in data['documents']:
        if item.get('id') in ids or not ID.fullmatch(item.get('id','')):
            raise ReferenceBlock('Invalid or duplicate model document')
        ids.add(item['id'])
        if item.get('publisher')!='A. O. Smith' or item.get('source_type')!='manufacturer_public_manual_listing':
            raise ReferenceBlock('Unverified manufacturer-index publisher')
        if item.get('manual_content_retrieved') is not False or item.get('full_text_machine_rights_verified') is not False or item.get('installed_product_match_verified') is not False:
            raise ReferenceBlock('Document index must not self-certify manual retrieval or rights')
        if not re.fullmatch(r'[0-9]{5,12}',item.get('document_number','')):
            raise ReferenceBlock('Invalid manufacturer document number')
        if not isinstance(item.get('models'),list) or not item['models'] or len(set(item['models']))!=len(item['models']):
            raise ReferenceBlock('Missing or duplicate model applicability')
        _web(item.get('official_index_url'),'www.hotwater.com')
        if not isinstance(item.get('title'),str) or not item['title'].strip():
            raise ReferenceBlock('Missing manufacturer document identity')
        if brand=='A. O. Smith' and model in item['models']:
            found.append({'index_id':item['id'],'manual_document_number':item['document_number'],
                          'official_index_url':item['official_index_url'],'title':item['title']})
    if len(found)>1:raise ReferenceBlock('Multiple manual identifiers match; human revision adjudication required')
    return {'status':'OFFICIAL_MODEL_LISTING_FOUND_MANUAL_NOT_VERIFIED' if found else 'EXACT_MODEL_NOT_IN_INDEX',
            'brand':brand,'model':model,'candidates':found,'manual_file_verified':False,
            'serial_or_revision_confirmed':False,'full_text_embedded':False,'customer_release_allowed':False}
