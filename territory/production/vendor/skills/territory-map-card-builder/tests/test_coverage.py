"""Coverage-model and complete-inventory tests using synthetic source records."""
import copy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_project import semantic_validate, schema_validate


def fixture(network=False):
    data=json.loads((ROOT/'examples/territory-project.example.json').read_text())
    if network:
        data['boundary'].update(closed=None,no_self_intersections=None)
        coverage=data['coverage_review'];coverage['representation']='explicit_road_segment_assignment'
        coverage.pop('polygon_boundary',None)
        coverage['segment_assignments']=[dict(road_id=r['id'],source_feature_id=r['source_feature_id'],from_ref=f"{r['id']}:verified-start",to_ref=f"{r['id']}:verified-end",classification=r['classification'],work_rule=r['work_rule'],inside_side=r['inside_side'],verified=True,assignment_evidence='Synthetic source segment and side evidence') for r in data['roads'] if r['classification'] in ('interior','perimeter')]
    return data


def test_polygon_and_complete_network_pass_without_inventing_closure():
    for network in (False,True):
        data=fixture(network)
        assert not semantic_validate(data),semantic_validate(data)
        assert not schema_validate(data,ROOT/'schemas/territory-project.schema.json')


def test_all_representations_fail_closed_on_inventory_defects():
    mutations=['missing_inventory','missing_coverage','unresolved_candidate','unresolved_edge','unknown_property','partial_query','count_mismatch','dropped_feature','extra_feature','duplicate_feature','narrow_extent','wrong_crs','missing_source','missing_recency','missing_property','missing_assigned_road']
    for network in (False,True):
        for mutation in mutations:
            d=fixture(network);c=d['coverage_review'];i=d['current_inventory_review']
            if mutation=='missing_inventory':del d['current_inventory_review']
            elif mutation=='missing_coverage':del d['coverage_review']
            elif mutation=='unresolved_candidate':i['unresolved_candidates']=['Unresolved Cove Bay-like candidate']
            elif mutation=='unresolved_edge':c['unresolved_edges']=['Unresolved western edge']
            elif mutation=='unknown_property':i['feature_dispositions'][-1]['eligibility']='unknown'
            elif mutation=='partial_query':i['sources'][0]['complete']=False
            elif mutation=='count_mismatch':i['sources'][0]['returned_count']+=1
            elif mutation=='dropped_feature':i['feature_dispositions'].pop()
            elif mutation=='extra_feature':i['feature_dispositions'].append(dict(i['feature_dispositions'][0],feature_id='unqueried-feature'))
            elif mutation=='duplicate_feature':i['feature_dispositions'].append(copy.deepcopy(i['feature_dispositions'][0]))
            elif mutation=='narrow_extent':i['audit_extent']=dict(i['audit_extent'],bounds=[1,1,99,99])
            elif mutation=='wrong_crs':i['audit_extent']=dict(i['audit_extent'],crs='OTHER')
            elif mutation=='missing_source':i['sources']=[]
            elif mutation=='missing_recency':i['sources'][0].pop('source_recency')
            elif mutation=='missing_property':
                i['feature_dispositions']=i['feature_dispositions'][:-1]
                i['sources'][0]['retrieved_feature_ids'].pop();i['sources'][0]['returned_count']-=1
            elif mutation=='missing_assigned_road':
                i['feature_dispositions']=i['feature_dispositions'][1:]
                i['sources'][0]['retrieved_feature_ids'].pop(0);i['sources'][0]['returned_count']-=1
            assert semantic_validate(d),(network,mutation)


def test_network_assignment_requires_real_complete_segment_evidence():
    for mutation in ['hash','endpoint','side','rule','missing_segment','duplicate_segment','wrong_feature','invented_closure','vector_mode','unverified','unknown_id']:
        d=fixture(True);c=d['coverage_review'];a=c['segment_assignments']
        if mutation=='hash':c['source_sha256']='not-a-hash'
        elif mutation=='endpoint':a[0].pop('to_ref')
        elif mutation=='side':a[1]['inside_side']='unknown'
        elif mutation=='rule':a[1]['work_rule']='both_sides'
        elif mutation=='missing_segment':a.pop()
        elif mutation=='duplicate_segment':a.append(copy.deepcopy(a[0]))
        elif mutation=='wrong_feature':a[0]['source_feature_id']='fake'
        elif mutation=='invented_closure':d['boundary']['closed']=True
        elif mutation=='vector_mode':d['map_mode']=c['map_mode']='vector_rebuild'
        elif mutation=='unverified':a[0]['verified']=False
        elif mutation=='unknown_id':a[0]['road_id']='fake-road'
        assert semantic_validate(d),mutation


def test_open_polygon_still_fails_and_no_segment_escape_is_implicit():
    d=fixture();d['boundary']['closed']=False
    assert any('boundary.closed' in e for e in semantic_validate(d))
    d['coverage_review']['representation']='explicit_road_segment_assignment'
    assert semantic_validate(d)


def test_original_drawing_ids_can_bind_current_inventory_without_relabeling_geometry():
    d=fixture(True)
    road=d['roads'][0];original=road['source_feature_id']
    road['source_feature_id']='original-PDF-path'
    d['coverage_review']['segment_assignments'][0]['source_feature_id']='original-PDF-path'
    road['inventory_feature_refs']=[{'source_id':'test-source','feature_id':original}]
    assert not semantic_validate(d),semantic_validate(d)
    road['inventory_feature_refs'][0]['feature_id']='unretrieved'
    assert semantic_validate(d)


def test_verified_empty_property_query_is_not_assumed_from_road_query():
    d=fixture(True);i=d['current_inventory_review']
    i['feature_dispositions'].pop()
    i['sources'][0]['retrieved_feature_ids'].pop();i['sources'][0]['returned_count']-=1
    i['sources'].append(dict(i['sources'][0],id='property-query',feature_kind='property',returned_count=0,retrieved_feature_ids=[]))
    d['housing_instruction_review']['assigned_housing']=[]
    d['housing_instruction_review']['included_housing_types']=[]
    i['property_absence_evidence']='Synthetic full property query and source review found no property features in the bounded area'
    assert not semantic_validate(d),semantic_validate(d)
    i['sources'][-1]['complete']=False
    assert semantic_validate(d)
