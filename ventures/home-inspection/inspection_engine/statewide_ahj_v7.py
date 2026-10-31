"""Offline bulk importer for the Michigan LARA Statewide Jurisdiction List.

Input is a human-reviewed structured transcription of the state directory,
not an automated extraction of copyrighted text or parcel-level AHJ approval.
No municipality is labelled verified merely because a row is imported.
"""
from __future__ import annotations
import csv
from datetime import date
from io import StringIO
from pathlib import Path
import hashlib
import re

TRADES=('building','electrical','mechanical','plumbing')
CLASSES=('city','township','village')
LEVELS=('STATE','COUNTY','LOCAL')
HEX=re.compile(r'[a-f0-9]{64}\Z')
FIELDS=('county','municipality','municipality_type','building','building_effective_date','electrical','electrical_effective_date','mechanical','mechanical_effective_date','plumbing','plumbing_effective_date','temporary_assistance_notes')

class AHJImportBlocked(ValueError): pass


def parse_verified_transcription(csv_text:str,*,state_source_sha256:str,source_revision:str,operator_id:str):
    if not isinstance(csv_text,str) or len(csv_text)>3_000_000 or not csv_text.strip():
        raise AHJImportBlocked('Nonempty bounded CSV transcription required')
    if not HEX.fullmatch(state_source_sha256):raise AHJImportBlocked('State source document SHA-256 missing')
    if not isinstance(operator_id,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{3,70}',operator_id):
        raise AHJImportBlocked('Named source reviewer required')
    try:d=date.fromisoformat(source_revision)
    except (TypeError,ValueError) as e:raise AHJImportBlocked('Official source revision date required') from e
    if d>date.today() or d.isoformat()!=source_revision:raise AHJImportBlocked('Future or noncanonical source revision')
    rdr=csv.DictReader(StringIO(csv_text))
    if tuple(rdr.fieldnames or ())!=FIELDS:raise AHJImportBlocked('Expected exact Michigan AHJ import columns')
    rows=[];seen=set()
    for item in rdr:
        if len(rows)>=2500:raise AHJImportBlocked('Jurisdiction import maximum exceeded')
        if None in item or any(not isinstance(item.get(f),str) or not item[f].strip() for f in ('county','municipality','municipality_type',*TRADES)):
            raise AHJImportBlocked('Incomplete municipality or trade authority')
        k=(item['county'].strip().casefold(),item['municipality'].strip().casefold(),item['municipality_type'].strip().casefold())
        if k in seen:raise AHJImportBlocked('Duplicate governmental unit')
        seen.add(k)
        if k[2] not in CLASSES:raise AHJImportBlocked('Unrecognized municipality type')
        trades={t:item[t].strip().upper() for t in TRADES}
        if not set(trades.values())<=set(LEVELS):raise AHJImportBlocked('Enforcement level must be state, county or local')
        dates={}
        for trade in TRADES:
            raw=item[trade+'_effective_date'].strip()
            if not raw:
                dates[trade]=None  # Source does not state a date: never infer one
                continue
            try: e=date.fromisoformat(raw)
            except (TypeError,ValueError) as ex:raise AHJImportBlocked('Invalid effective date for '+trade) from ex
            if e>date.today() or e.isoformat()!=raw:
                raise AHJImportBlocked('Future or noncanonical effective date for '+trade)
            dates[trade]=e.isoformat()
        assistance=item['temporary_assistance_notes'].strip()
        if len(assistance)>500:raise AHJImportBlocked('Assistance note too long')
        rows.append({'county':item['county'].strip(),'municipality':item['municipality'].strip(),
                     'municipality_type':k[2],'jurisdiction_levels':trades,
                     'effective_dates':dates,'temporary_assistance_notes':assistance,
                     'assistance_requires_individual_review':bool(assistance),
                     'status':'TRANSCRIBED_NOT_CASE_VERIFIED'})
    if not rows:raise AHJImportBlocked('No jurisdiction records')
    return {'status':'STATE_SOURCE_TRANSCRIPTION_PENDING_AHJ_RECONFIRMATION',
            'source_revision':source_revision,'source_sha256':state_source_sha256,
            'transcription_sha256':hashlib.sha256(csv_text.encode('utf-8')).hexdigest(),
            'operator_id':operator_id,'records':rows,'imported_units':len(rows),
            'separate_trades':list(TRADES),'parcel_level_authority_verified':False,
            'complete_michigan_coverage_verified':False,'customer_release_allowed':False}


def find_record(index:dict,case:dict):
    key=(str(case.get('county','')).casefold(),str(case.get('municipality','')).casefold(),str(case.get('municipality_type','')).casefold())
    matches=[r for r in index.get('records',[]) if
             (r['county'].casefold(),r['municipality'].casefold(),r['municipality_type'].casefold())==key]
    if len(matches)!=1:raise AHJImportBlocked('Case jurisdiction absent or ambiguous in transcribed directory')
    result=matches[0]
    return {'jurisdiction_levels':result['jurisdiction_levels'], 'effective_dates':result['effective_dates'],
            'temporary_assistance_requires_review':result['assistance_requires_individual_review'],
            'source_revision':index['source_revision'],
            'state_source_sha256':index['source_sha256'],
            'status':'ENFORCEMENT_LEVEL_LEAD_NEEDS_CURRENT_AUTHORITY_CONFIRMATION',
            'authority_names_authenticated':False,'case_code_compliance_verified':False}
