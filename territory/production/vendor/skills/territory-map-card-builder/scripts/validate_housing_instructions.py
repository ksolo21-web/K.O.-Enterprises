"""Require printed housing instructions to agree with the marked assignment.

The user-authorized precedence resolves obsolete housing exclusions; it never
expands assignment, work colors, inside-only sides or explicit map exclusions.
"""
import re
from datetime import date

TYPES={'single_family_homes','apartments','condominiums','townhomes','mobile_homes','other_residential'}
ALIASES={
 'single_family_homes':r'(?:single[- ]family(?:\s+(?:homes?|houses?|residences?))?|detached\s+(?:homes?|houses?)|houses?)',
 'apartments':r'(?:apartments?|apts?\.?)',
 'condominiums':r'(?:condominiums?|condos?)',
 'townhomes':r'(?:town\s?homes?|town\s?houses?)',
 'mobile_homes':r'(?:(?:mobile|manufactured)\s+homes?)',
 'other_residential':r'(?:other\s+(?:residential(?:\s+(?:types|properties|housing))?|residences|housing))'
}


def text(v):return isinstance(v,str) and bool(v.strip())

def normalized(v):return ' '.join(str(v).casefold().split())

def typed_list(value):return isinstance(value,list) and all(isinstance(v,str) and v in TYPES for v in value) and len(set(value))==len(value)


def printed_conflicts(instructions,assigned):
    """Conservative explicit-denial detection; independent semantic review remains mandatory."""
    out=[]
    for kind in assigned:
        alias=ALIASES[kind]
        prefix=r"\b(?:no|exclude|excluding|except|do\s+not\s+(?:work|visit)|don't\s+(?:work|visit))\s+(?:(?:any|all|the|these|of)\s+){0,3}"
        # Keep a denial with its housing list; do not reinterpret the standalone
        # red 'Do Not Work' legend as a housing exclusion elsewhere on the page.
        for clause in re.findall(prefix+r'[^\n.;:]{1,150}',instructions,flags=re.I):
            if re.search(r'\b'+alias+r'\b',clause,re.I):out.append(kind);break
        if kind!='single_family_homes' and re.search(r'\b(?:(?:single[- ]family\s+)?houses|(?<!mobile )(?<!manufactured )homes)\s+only\b|\bonly\s+(?:single[- ]family\s+)?(?:homes|houses)\b',instructions,re.I):
            out.append(kind)
    return sorted(set(out))


def validate_housing_instructions(review,inventory,assignment_sha256=None,artifact_text=None):
    errors=[]
    if not isinstance(review,dict):return ['housing_instruction_review is required on every territory card']
    def check(value,message):
        if not value:errors.append(message)
    check(review.get('rule_precedence')=='marked_assignment_over_legacy_housing_exclusions','Housing precedence must follow marked assignment over obsolete housing exclusions')
    decision=review.get('user_decision',{})
    if not isinstance(decision,dict):decision={}
    try:date.fromisoformat(decision.get('date',''))
    except (ValueError,TypeError):errors.append('Housing user_decision.date must be an ISO date')
    for key in ('instruction','source_ref'):
        check(text(decision.get(key)),f'Housing user_decision.{key} must retain explicit user rule provenance')
    check(text(review.get('assignment_source_ref')),'Housing review needs assignment source reference')
    digest=review.get('assignment_source_sha256')
    check(isinstance(digest,str) and bool(re.fullmatch('[0-9a-fA-F]{64}',digest)),'Housing review needs original assignment SHA-256')
    if assignment_sha256 is not None:check(digest==assignment_sha256,'Housing assignment hash must match the actual coverage authority')
    for key in ('assignment_scope_preserved','work_colors_preserved','inside_only_sides_preserved','map_exclusions_preserved','instructions_review_completed'):
        check(review.get(key) is True,f'Housing review requires {key}; housing inclusion never expands or recolors assignment')
    check(review.get('unresolved_conflicts')==[],'Map-versus-housing-instructions conflicts must be an empty list')
    for key in ('legacy_instruction_evidence','evidence','rendered_instructions_text'):
        check(text(review.get(key)),f'housing_instruction_review.{key} is required')
    rendered=review.get('rendered_instructions_text','')
    if artifact_text is not None:check(normalized(rendered)==normalized(artifact_text),'Housing instruction review must bind all actual final-PDF extracted text, including work notes')
    inventory=inventory if isinstance(inventory,dict) else {}
    features=inventory.get('feature_dispositions',[])
    if not isinstance(features,list):features=[]
    assigned_properties={(f.get('source_id'),f.get('feature_id')) for f in features if isinstance(f,dict) and f.get('kind')=='property' and f.get('eligibility')=='eligible' and f.get('disposition') in ('matched','verified_addition')}
    records=review.get('assigned_housing')
    if not isinstance(records,list):records=[];errors.append('Housing review must enumerate assigned_housing evidence')
    assigned=set();bound=set()
    for i,record in enumerate(records):
        tag=f'assigned_housing[{i}]'
        if not isinstance(record,dict):errors.append(f'{tag} must be a housing evidence record');continue
        kind=record.get('housing_type')
        check(isinstance(kind,str) and kind in TYPES and kind not in assigned,f'{tag}.housing_type must be supported and unique')
        if isinstance(kind,str):assigned.add(kind)
        check(text(record.get('assignment_evidence')),f'{tag} requires verified housing-type and marked-assignment evidence')
        refs=record.get('feature_refs')
        if not isinstance(refs,list) or not refs:refs=[];errors.append(f'{tag} must bind eligible assigned property features')
        for ref in refs:
            if not isinstance(ref,dict) or not text(ref.get('source_id')) or not text(ref.get('feature_id')):
                errors.append(f'{tag} needs source_id/feature_id bindings');continue
            pair=(ref['source_id'],ref['feature_id'])
            check(pair in assigned_properties,f'{tag} references a property outside the eligible marked assignment')
            check(pair not in bound,f'{tag} duplicates a property housing assignment')
            bound.add(pair)
    check(bound==assigned_properties,'Housing evidence must cover every and only eligible assigned property disposition')
    excluded_properties={(f.get('source_id'),f.get('feature_id')) for f in features if isinstance(f,dict) and f.get('kind')=='property' and f.get('eligibility')=='ineligible'}
    excluded_records=review.get('excluded_property_review')
    if not isinstance(excluded_records,list):excluded_records=[];errors.append('Housing review requires excluded_property_review')
    excluded_bound=set()
    for i,record in enumerate(excluded_records):
        tag=f'excluded_property_review[{i}]'
        if not isinstance(record,dict):errors.append(f'{tag} must be an assignment/access exclusion record');continue
        check(record.get('basis') in ('map_exclusion','outside_assignment','inside_only_other_side','assigned_other_territory','access_rule','nonresidential'),f'{tag} needs an assignment/access basis; housing type alone cannot exclude marked residences')
        check(text(record.get('evidence')),f'{tag} requires independently verified exclusion/assignment evidence')
        refs=record.get('feature_refs')
        if not isinstance(refs,list) or not refs:refs=[];errors.append(f'{tag} must bind excluded property features')
        for ref in refs:
            if not isinstance(ref,dict) or not text(ref.get('source_id')) or not text(ref.get('feature_id')):
                errors.append(f'{tag} needs source_id/feature_id bindings');continue
            pair=(ref['source_id'],ref['feature_id'])
            check(pair in excluded_properties and pair not in excluded_bound,f'{tag} must uniquely bind actual excluded properties, never assigned work')
            excluded_bound.add(pair)
    check(excluded_bound==excluded_properties,'Housing evidence must retain every explicit excluded property and its assignment/access basis')
    included=review.get('included_housing_types');legacy=review.get('legacy_housing_exclusions')
    check(typed_list(included),'included_housing_types must be a unique supported-type list')
    check(typed_list(legacy),'legacy_housing_exclusions must be a unique supported-type list')
    included=set(included) if typed_list(included) else set();legacy=set(legacy) if typed_list(legacy) else set()
    check(assigned.issubset(included),'Printed instruction scope must include every housing type in the marked workable assignment')
    conflicts=printed_conflicts(str(rendered),assigned&TYPES)
    check(not conflicts,'Actual printed instructions exclude marked assigned housing types: '+', '.join(conflicts))
    resolutions=review.get('resolutions')
    if not isinstance(resolutions,list):resolutions=[];errors.append('Housing review requires resolutions, even when empty')
    resolved=set()
    for i,resolution in enumerate(resolutions):
        tag=f'housing resolutions[{i}]'
        if not isinstance(resolution,dict):errors.append(f'{tag} must be a resolution record');continue
        kind=resolution.get('housing_type')
        check(isinstance(kind,str) and kind in assigned&legacy and kind not in resolved,f'{tag} must resolve one actual legacy-versus-assignment conflict')
        if isinstance(kind,str):resolved.add(kind)
        for key in ('previous_instruction','revised_instruction','assignment_evidence','decision_ref'):
            check(text(resolution.get(key)),f'{tag}.{key} must retain instruction-change/assignment/user-decision evidence')
        revised=resolution.get('revised_instruction','')
        check(text(revised) and normalized(revised) in normalized(rendered),f'{tag}.revised_instruction must appear in actual printed instructions')
        inclusive=bool(re.search(r'\ball\b[^.;\n]{0,120}\b(?:residences|residential|housing types|homes)\b',str(revised),re.I))
        explicit=isinstance(kind,str) and kind in ALIASES and bool(re.search(r'\b'+ALIASES[kind]+r'\b',str(revised),re.I))
        check(inclusive or explicit,f'{tag} must explicitly include that housing type or all assigned residences')
    check(resolved==assigned&legacy,'Every assigned housing type excluded by legacy directions must have a documented printed resolution')
    return errors
