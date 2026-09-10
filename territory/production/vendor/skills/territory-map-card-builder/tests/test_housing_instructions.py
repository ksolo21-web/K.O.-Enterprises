"""Concrete marked-condo versus homes-only conflicts and assignment exclusions."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_housing_instructions import validate_housing_instructions,printed_conflicts


def fixture(kind='single_family_homes'):
    project=json.loads((ROOT/'examples/territory-project.example.json').read_text())
    h=project['housing_instruction_review'];h['assigned_housing'][0]['housing_type']=kind;h['included_housing_types']=[kind]
    if kind!='single_family_homes':
        h['legacy_housing_exclusions']=[kind];h['rendered_instructions_text']='Work all residences within the marked assignment, including condos. Keep inside-only sides and map exclusions.'
        h['resolutions']=[dict(housing_type=kind,previous_instruction='Homes only',revised_instruction='Work all residences within the marked assignment, including condos.',assignment_evidence='Verified marked residence source and housing type',decision_ref='synthetic-user-decision')]
    return h,project['current_inventory_review']


def test_houses_and_every_assigned_residential_type_pass():
    for kind in ['single_family_homes','apartments','condominiums','townhomes','mobile_homes','other_residential']:
        h,i=fixture(kind);assert not validate_housing_instructions(h,i,'a'*64,h['rendered_instructions_text'])


def test_explicit_printed_denials_fail_even_when_metadata_claims_resolution():
    for kind,denial in [('apartments','No apartments'),('condominiums','No apartments or condos'),('townhomes','Exclude townhomes'),('mobile_homes','Do not work mobile homes'),('other_residential','Homes only'),('apartments','Only houses'),('condominiums','Homes only')]:
        h,i=fixture(kind);h['rendered_instructions_text']+='\n'+denial
        assert any('Actual printed' in e for e in validate_housing_instructions(h,i)),(kind,denial)
    assert not printed_conflicts('Work all marked apartments.\nDo Not Work\nRohr Rd',{'apartments'})


def test_missing_evidence_stale_text_or_scope_expansion_fails():
    for mutation in ['missing','decision','hash','resolution','printed','omitted','outside','side','color','exclusion','unresolved','type','decision_ref']:
        h,i=fixture('condominiums')
        if mutation=='missing':h=None
        elif mutation=='decision':h['user_decision'].pop('source_ref')
        elif mutation=='hash':h['assignment_source_sha256']='b'*64
        elif mutation=='resolution':h['resolutions']=[]
        elif mutation=='printed':h['resolutions'][0]['revised_instruction']='Unprinted changed instruction'
        elif mutation=='omitted':h['assigned_housing']=[]
        elif mutation=='outside':h['assigned_housing'][0]['feature_refs'][0]['feature_id']='outside-assignment'
        elif mutation=='side':h['inside_only_sides_preserved']=False
        elif mutation=='color':h['work_colors_preserved']=False
        elif mutation=='exclusion':h['map_exclusions_preserved']=False
        elif mutation=='unresolved':h['unresolved_conflicts']=['unresolved']
        elif mutation=='type':h['included_housing_types']=[]
        elif mutation=='decision_ref':h['resolutions'][0]['decision_ref']=''
        assert validate_housing_instructions(h,i,'a'*64),mutation
    h,i=fixture();assert validate_housing_instructions(h,i,'a'*64,'Different actual final text')


def test_other_territory_exclusion_needs_real_assignment_basis():
    h,i=fixture('apartments');f=copy.deepcopy(i['feature_dispositions'][-1]);f.update(feature_id='other-territory-complex',eligibility='ineligible',disposition='excluded');i['feature_dispositions'].append(f)
    record=dict(basis='assigned_other_territory',feature_refs=[dict(source_id=f['source_id'],feature_id=f['feature_id'])],evidence='Verified separate complex assignment; workable approach does not assign the complex.')
    h['excluded_property_review']=[record]
    assert not validate_housing_instructions(h,i)
    record['basis']='apartments_excluded';assert validate_housing_instructions(h,i)
    record['basis']='assigned_other_territory';record['evidence']='';assert validate_housing_instructions(h,i)
    h['excluded_property_review']=[];assert validate_housing_instructions(h,i)


def test_schema_housing_contract_is_at_project_root():
    from validate_project import schema_validate, semantic_validate
    schema=ROOT/'schemas/territory-project.schema.json'
    d=json.loads((ROOT/'examples/territory-project.example.json').read_text())
    assert not schema_validate(d,schema)
    contract=json.loads(schema.read_text())
    assert 'housing_instruction_review' in contract['required']
    assert contract['properties']['housing_instruction_review']['properties']['work_colors_preserved']=={'const':True}
    assert 'housing_instruction_review' not in contract['$defs']['auditExtent']['properties']
    d['housing_instruction_review']['work_colors_preserved']=False
    assert semantic_validate(d)
    try:import jsonschema
    except ImportError:return
    assert schema_validate(d,schema)
