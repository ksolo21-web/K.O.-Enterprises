"""Real PDF/hash/report gate tests with explicitly synthetic geography evidence."""
import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from critic_evidence import capture, gate


def coverage_fixture(network=False):
    extent={'crs':'SYNTHETIC:test','bounds':[0,0,100,100],'evidence':'Synthetic full assignment and edge extent'}
    coverage={'representation':'explicit_road_segment_assignment' if network else 'closed_polygon','map_mode':'preserve_supplied_map','source_ref':'Synthetic original assignment','source_sha256':'a'*64,'geometry_verified':True,'full_coverage_resolved':True,'audit_extent':extent,'edges_reviewed':True,'edge_evidence':'Synthetic verified edges','unresolved_edges':[]}
    if network:
        coverage['segment_assignments']=[{'road_id':'road-1','source_feature_id':'source-road','from_ref':'source-junction-A','to_ref':'source-junction-B','classification':'interior','work_rule':'both_sides','inside_side':'not_applicable','verified':True,'assignment_evidence':'Synthetic original explicit road assignment'}]
    else:
        coverage['polygon_boundary']={'closed':True,'no_self_intersections':True,'geometry_verified':True}
    inventory={'check_date':'2026-09-06','full_boundary_and_edges_checked':True,'source_retrieval_complete':True,'relevant_property_eligibility_resolved':True,'unresolved_discrepancies':[],'unresolved_candidates':[],'evidence':'Synthetic inventory fixture, not a real geographic audit','audit_extent':extent,'sources':[{'id':'source','url':'https://example.invalid/inventory','retrieved_at':'2026-09-06','source_recency':'Unknown; synthetic fixture','query':'Synthetic complete extent and edges','retrieval_evidence':'Synthetic ID/count reconciliation','complete':True,'returned_count':2,'retrieved_feature_ids':['source-road','source-property']}],'feature_dispositions':[{'source_id':'source','feature_id':'source-road','kind':'road','location':'Synthetic within assignment','disposition':'matched','eligibility':'not_applicable','assignment_evidence':'Synthetic road assignment','evidence':'Synthetic source evidence'},{'source_id':'source','feature_id':'source-property','kind':'property','location':'Synthetic assigned frontage','disposition':'matched','eligibility':'eligible','assignment_evidence':'Synthetic property assignment','evidence':'Synthetic source evidence'}]}
    return coverage,inventory


def review_fixture():
    roads=[]
    for n in (1,2):
        rid=f'road-{n}'
        roads.append({'canonical_road_id':rid,'name':f'Major Road {n}',
            'identity_verified':True,'road_ids':[rid],'label_ids':[f'label-{n}'],
            'visible':True,'readable_at_output_size':True,
            'major_qualification':{'class':'arterial','evidence':'Synthetic test arterial'},
            'source_evidence':[{'url':'https://example.invalid/synthetic','retrieved_at':'2026-09-06','feature_ids':[rid],'evidence':'Synthetic feature/name/class/junction evidence; not real geography'}],
            'drawing_evidence':'page-1-1x.png synthetic line','label_evidence':'page-1-2x.png synthetic label',
            'approach':{'road_ids':[rid,'territory-road'],'connected':True,'geometry_verified':True,'drawn':True,'evidence':'Synthetic connected junction'}})
    return {'actual_size_review_completed':True,'closeup_review_completed':True,
            'distinct_physical_roads_verified':True,'directions_reference_both':True,
            'directions_text':'Use Major Road 1 and Major Road 2.','roads':roads}


def test_gate_blocks_fake_or_missing_second_major_road():
    import fitz
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);pdf=root/'synthetic.pdf'
        with fitz.open() as doc:
            page=doc.new_page(width=300,height=200)
            page.insert_text((20,20),'Synthetic gate fixture: Major Road 1 and Major Road 2')
            page.draw_line((20,40),(220,40));page.draw_line((100,40),(100,170))
            doc.save(pdf)
        manifest=capture(pdf,root/'round')
        report={'artifact_sha256':manifest['artifact_sha256'],'critic_independent':True,
                'categories':{k:{'score':10,'reason':'Synthetic gate contract test'} for k in ['preservation','geography','labels','template','export']},
                'screenshots_inspected':manifest['screenshots'],
                'label_clutter_review':{'actual_size_review_completed':True,'closeup_review_completed':True,'remaining_avoidable_clusters':0,'evidence':'Synthetic screenshots'},
                'current_inventory_review':{'check_date':'2026-09-06','full_boundary_and_edges_checked':True,'source_retrieval_complete':True,'relevant_property_eligibility_resolved':True,'unresolved_discrepancies':[],'evidence':'Synthetic contract test'},
                'card_content_review':{'source_or_audit_lines_absent':True,'evidence':'Synthetic contract test'},
                'major_crossroad_review':review_fixture(),
                'blockers':[],'unverified':[],'overall_score':10,'release_ready':True,'topology_mask_kinds':{}}
        report['coverage_review'],report['current_inventory_review']=coverage_fixture()
        with fitz.open(pdf) as document:
            actual_text = "\n".join(page.get_text() for page in document)
        report['housing_instruction_review']={
            'rule_precedence':'marked_assignment_over_legacy_housing_exclusions',
            'user_decision':{'date':'2026-09-06','instruction':'Include assigned housing types within existing marked scope.','source_ref':'synthetic-user-decision'},
            'assignment_source_ref':'Synthetic original assignment','assignment_source_sha256':'a'*64,
            'assigned_housing':[{'housing_type':'single_family_homes','feature_refs':[{'source_id':'source','feature_id':'source-property'}],'assignment_evidence':'Synthetic verified house and marked frontage'}],
            'included_housing_types':['single_family_homes'],'legacy_housing_exclusions':[],
            'legacy_instruction_evidence':'Synthetic navigation directions exclude no assigned housing type.',
            'resolutions':[],'rendered_instructions_text':actual_text,'unresolved_conflicts':[],
            'assignment_scope_preserved':True,'work_colors_preserved':True,'inside_only_sides_preserved':True,
            'map_exclusions_preserved':True,'instructions_review_completed':True,
            'excluded_property_review':[],'evidence':'Synthetic independent map and full-page instruction review'}
        path=root/'round/review.json'
        path.write_text(json.dumps(report));result=gate(pdf,path)
        assert result['release_ready'] is True, result
        mutations=['missing','one','alias','feature_reuse','minor','no_source','floating','unreadable','disconnected','missing_directions','false_independence','missing_topology_inventory','typed_topology_without_evidence']
        for mutation in mutations:
            candidate=copy.deepcopy(report);r=candidate['major_crossroad_review'];road=r['roads'][1]
            if mutation=='missing': del candidate['major_crossroad_review']
            elif mutation=='one': r['roads'].pop()
            elif mutation=='alias': road['canonical_road_id']=r['roads'][0]['canonical_road_id']
            elif mutation=='feature_reuse': road['source_evidence']=copy.deepcopy(r['roads'][0]['source_evidence'])
            elif mutation=='minor': road['major_qualification']['class']='residential'
            elif mutation=='no_source': road['source_evidence']=[]
            elif mutation=='floating': road['road_ids']=[]
            elif mutation=='unreadable': road['readable_at_output_size']=False
            elif mutation=='disconnected': road['approach']['connected']=False
            elif mutation=='missing_directions': r['directions_text']='Use Major Road 1.'
            elif mutation=='false_independence': r['distinct_physical_roads_verified']=False
            elif mutation=='missing_topology_inventory': del candidate['topology_mask_kinds']
            elif mutation=='typed_topology_without_evidence': candidate['topology_mask_kinds']={'unreviewed-addition':'native_topology_addition'}
            path.write_text(json.dumps(candidate));result=gate(pdf,path)
            assert result['release_ready'] is False and result['overall_score']<=8 and result['errors'], (mutation,result)
        coverage_mutations=['missing_coverage','missing_inventory','unresolved_edge','unresolved_candidate','unknown_property','partial_query','count_mismatch','dropped_feature','extra_feature','narrow_extent','bad_hash','missing_endpoint','missing_segment','bad_source_binding']
        for network in (False,True):
            candidate=copy.deepcopy(report)
            candidate['coverage_review'],candidate['current_inventory_review']=coverage_fixture(network)
            path.write_text(json.dumps(candidate));result=gate(pdf,path)
            assert result['release_ready'],result
            for mutation in coverage_mutations:
                bad=copy.deepcopy(candidate);c=bad['coverage_review'];i=bad['current_inventory_review']
                if mutation=='missing_coverage':del bad['coverage_review']
                elif mutation=='missing_inventory':del bad['current_inventory_review']
                elif mutation=='unresolved_edge':c['unresolved_edges']=['Unresolved western edge']
                elif mutation=='unresolved_candidate':i['unresolved_candidates']=['Unresolved Cove Bay-like property/access']
                elif mutation=='unknown_property':i['feature_dispositions'][-1]['eligibility']='unknown'
                elif mutation=='partial_query':i['sources'][0]['complete']=False
                elif mutation=='count_mismatch':i['sources'][0]['returned_count']=3
                elif mutation=='dropped_feature':i['feature_dispositions'].pop()
                elif mutation=='extra_feature':i['feature_dispositions'].append(dict(i['feature_dispositions'][0],feature_id='extra'))
                elif mutation=='narrow_extent':i['audit_extent']=dict(i['audit_extent'],bounds=[1,1,99,99])
                elif mutation=='bad_hash':c['source_sha256']='invalid'
                elif mutation=='missing_endpoint':
                    if not network:c['polygon_boundary']['closed']=False
                    else:c['segment_assignments'][0].pop('to_ref')
                elif mutation=='missing_segment':
                    if not network:c.pop('polygon_boundary')
                    else:c['segment_assignments']=[]
                elif mutation=='bad_source_binding':
                    if not network:c['polygon_boundary']['geometry_verified']=False
                    else:c['segment_assignments'][0]['source_feature_id']='not-retrieved'
                path.write_text(json.dumps(bad));result=gate(pdf,path)
                assert not result['release_ready'] and result['overall_score']<=8 and result['errors'],(network,mutation,result)
        housing_mutations=['missing','stale_actual_text','user_provenance','omitted_property','outside_assignment','other_side','map_exclusion','missing_resolution']
        for mutation in housing_mutations:
            bad=copy.deepcopy(report);h=bad['housing_instruction_review']
            if mutation=='missing':del bad['housing_instruction_review']
            elif mutation=='stale_actual_text':h['rendered_instructions_text']='Different final PDF instructions'
            elif mutation=='user_provenance':h['user_decision']['source_ref']=''
            elif mutation=='omitted_property':h['assigned_housing']=[]
            elif mutation=='outside_assignment':h['assigned_housing'][0]['feature_refs'][0]['feature_id']='outside'
            elif mutation=='other_side':h['inside_only_sides_preserved']=False
            elif mutation=='map_exclusion':h['map_exclusions_preserved']=False
            elif mutation=='missing_resolution':h['legacy_housing_exclusions']=['single_family_homes']
            path.write_text(json.dumps(bad));result=gate(pdf,path)
            assert not result['release_ready'] and result['overall_score']<=8 and result['errors'],(mutation,result)
        print('PASS 8 real-PDF housing negatives: cap 8/release false')
        print(f'PASS real-PDF critic gate: polygon/network positives, {len(mutations)} crossroad and {2*len(coverage_mutations)} coverage/inventory negatives cap at 8 and block release')


if __name__=='__main__':
    test_gate_blocks_fake_or_missing_second_major_road()
