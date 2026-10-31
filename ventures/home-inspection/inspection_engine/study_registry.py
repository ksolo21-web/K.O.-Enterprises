"""Local partition ledger. Checksums detect changes, not malicious owner edits.

Every case, original source and extracted-text fingerprint has one permanent
partition. This is a local leakage safeguard, not authenticated data governance.
"""
from copy import deepcopy
from .core import DataError
from .report_learning import digest,HEX,PARTITIONS


def empty_registry():
    r={'schema_version':1,'case_partitions':{},'sources':{},'texts':{}}
    return dict(r,registry_sha256=digest(r))


def validate_registry(registry):
    if not isinstance(registry,dict):raise DataError('Study registry required')
    r=deepcopy(registry);stored=r.pop('registry_sha256',None)
    if stored!=digest(r) or set(r)!={'schema_version','case_partitions','sources','texts'} or r['schema_version']!=1:
        raise DataError('Invalid study registry checksum or schema')
    if any(not isinstance(r[k],dict) for k in ('case_partitions','sources','texts')):raise DataError('Invalid registry maps')
    if any(not isinstance(c,str) or not c or p not in PARTITIONS for c,p in r['case_partitions'].items()):raise DataError('Invalid case partition')
    for kind in ('sources','texts'):
        for key,row in r[kind].items():
            if (not isinstance(key,str) or not HEX.fullmatch(key) or not isinstance(row,dict)
                or set(row)!={'case_id','partition'} or row.get('partition') not in PARTITIONS
                or r['case_partitions'].get(row.get('case_id'))!=row['partition']):raise DataError('Invalid registry identity binding')
    if len(r['case_partitions'])>10_000 or len(r['sources'])>50_000 or len(r['texts'])>50_000:raise DataError('Study registry needs explicit batching')
    return registry


def binding(bundle):
    return {'case_id':bundle['case_id'],'partition':bundle['partition']}


def register_bundle(bundle,registry):
    from .report_learning import validate_bundle
    validate_bundle(bundle);validate_registry(registry)
    changed=deepcopy(registry);row=binding(bundle);case=bundle['case_id']
    if case in changed['case_partitions'] and changed['case_partitions'][case]!=row['partition']:
        raise DataError('Case partition is immutable; holdout cannot become training')
    for kind,key in [('sources',bundle['source']['sha256']),('texts',bundle['text_sha256'])]:
        old=changed[kind].get(key)
        if old is not None and old!=row:raise DataError('Source/text alias cannot change case identity or partition')
        changed[kind][key]=deepcopy(row)
    changed['case_partitions'][case]=row['partition']
    changed.pop('registry_sha256');changed['registry_sha256']=digest(changed)
    validate_registry(changed)
    return changed


def require_registered(bundle,registry):
    validate_registry(registry);row=binding(bundle)
    if (registry['case_partitions'].get(bundle['case_id'])!=row['partition']
        or registry['sources'].get(bundle['source']['sha256'])!=row
        or registry['texts'].get(bundle['text_sha256'])!=row):
        raise DataError('Reference is not registered to this case and immutable partition')
