"""National inspection SOP coverage crosswalk; incomplete coverage must be visible."""
from __future__ import annotations
import copy,json
from pathlib import Path
from .descriptors import REQUIRED_FEATURES
from .knowledge_registry import ReferenceBlock

CATALOG=Path(__file__).resolve().parents[1]/'knowledge'/'sop_scope_crosswalk_v5.json'

def audit_sop_scope(data:dict|None=None)->dict:
    if data is None:data=json.loads(CATALOG.read_text())
    if not isinstance(data,dict) or data.get('schema_version')!=5 or not isinstance(data.get('topics'),list):
        raise ReferenceBlock('Invalid SOP scope inventory')
    topics=data['topics'];names=set();gaps=[];mapped=set()
    for row in topics:
        if not isinstance(row,dict) or not isinstance(row.get('topic'),str) or row['topic'] in names:
            raise ReferenceBlock('Invalid or duplicate SOP topic')
        names.add(row['topic'])
        systems=row.get('systems')
        if not isinstance(systems,list) or any(s not in REQUIRED_FEATURES for s in systems):
            raise ReferenceBlock('SOP inventory refers to nonexistent system')
        if row.get('mapping') not in {'present','partial','GAP','scope_dependent_gap','commercial_specialty_gap'}:
            raise ReferenceBlock('Invalid SOP coverage classification')
        if not isinstance(row.get('verification'),str) or not row['verification']:
            raise ReferenceBlock('Missing scope verification method')
        mapped.update(systems)
        if row['mapping']!='present':gaps.append({'topic':row['topic'],'mapping':row['mapping'],'next_action':row['verification']})
    if not set(REQUIRED_FEATURES).issubset(mapped):raise ReferenceBlock('Existing inspection system absent from SOP gap map')
    return {'status':'SOP_COVERAGE_INCOMPLETE' if gaps else 'MAPPING_COMPLETE_NOT_FIELD_VERIFIED',
            'topics_indexed':len(topics),'mapped_existing_systems':len(mapped),'unresolved_topics':gaps,
            'national_standard_compliance_certified':False,'customer_release_allowed':False}
