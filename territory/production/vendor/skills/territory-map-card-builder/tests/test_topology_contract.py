"""Binding tests for the typed topology report integration."""
import copy
import json
import sys
import tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
from topology_contract import validate_topology_review
from test_topology_patch import fixture
from validate_topology_patch import verify,sha
from topology_masks import transformed_source_parts


def test_actual_plan_report_artifact_and_independent_review_bindings():
    with tempfile.TemporaryDirectory() as tmp:
        p,plan=fixture(Path(tmp))
        report=verify(p['plan'],p['base'],p['patched'],p['baseline'],p['final'],Path(tmp)/'evidence')
        rp=Path(tmp)/'report.json';rp.write_text(json.dumps(report))
        kinds={o['id']:'native_topology_'+o['kind'] for o in plan['operations']}
        review={'plan_path':str(p['plan']),'plan_sha256':sha(p['plan']),'report_path':str(rp),'report_sha256':sha(rp),'independent_visual_review':{'independent':True,'source_plan_review_completed':True,'actual_size_review_completed':True,'paired_4x_review_completed':True,'no_visible_style_mismatch':True,'artifact_sha256':sha(p['final']),'plan_sha256':sha(p['plan']),'evidence':'Synthetic independent source-plan and actual-size/paired4x review'}}
        assert not validate_topology_review(review,sha(p['final']),kinds,sha(p['base'])),validate_topology_review(review,sha(p['final']),kinds,sha(p['base']))
        for defect in ['missing','stale_plan','stale_report','stale_artifact','wrong_masks','wrong_original','no_independence','no_source_review','no_4x_review','visual_mismatch']:
            candidate=copy.deepcopy(review);artifact=sha(p['final']);expected_kinds=kinds;original=sha(p['base'])
            if defect=='missing':candidate=None
            elif defect=='stale_plan':candidate['plan_sha256']='b'*64
            elif defect=='stale_report':candidate['report_sha256']='b'*64
            elif defect=='stale_artifact':artifact='b'*64
            elif defect=='wrong_masks':expected_kinds={'invented':'native_topology_addition'}
            elif defect=='wrong_original':original='b'*64
            elif defect=='no_independence':candidate['independent_visual_review']['independent']=False
            elif defect=='no_source_review':candidate['independent_visual_review']['source_plan_review_completed']=False
            elif defect=='no_4x_review':candidate['independent_visual_review']['paired_4x_review_completed']=False
            elif defect=='visual_mismatch':candidate['independent_visual_review']['no_visible_style_mismatch']=False
            assert validate_topology_review(candidate,artifact,expected_kinds,original),defect
        report['results'][0]['style_metrics']['median_width_delta_px']=1.26
        rp.write_text(json.dumps(report));review['report_sha256']=sha(rp)
        assert validate_topology_review(review,sha(p['final']),kinds,sha(p['base']))
    print('PASS typed report contract positive +11 stale/missing/incorrect evidence cases')


def test_multipart_report_cannot_omit_or_change_union_proofs():
    with tempfile.TemporaryDirectory() as tmp:
        p,plan=fixture(Path(tmp),multipart=True)
        report=verify(p['plan'],p['base'],p['patched'],p['baseline'],p['final'],Path(tmp)/'evidence')
        rp=Path(tmp)/'report.json';rp.write_text(json.dumps(report))
        review={'plan_path':str(p['plan']),'plan_sha256':sha(p['plan']),
            'report_path':str(rp),'report_sha256':sha(rp),
            'independent_visual_review':{'independent':True,'source_plan_review_completed':True,
                'actual_size_review_completed':True,'paired_4x_review_completed':True,
                'no_visible_style_mismatch':True,'artifact_sha256':sha(p['final']),
                'plan_sha256':sha(p['plan']),'evidence':'Synthetic exact multipart plan and paired crop review'}}
        kinds={o['id']:'native_topology_'+o['kind'] for o in plan['operations']}
        assert not validate_topology_review(review,sha(p['final']),kinds)
        cases=[
            ('parts',lambda r:r.update(mask_source_parts=[r['mask_source']])),
            ('envelope',lambda r:r.update(mask_source=[0,0,200,200])),
            ('guard',lambda r:r.update(mask_renderer_guard_2x_px=2)),
            ('missing_proof',lambda r:r.pop('isolated_delta_contained')),
            ('pixels',lambda r:r.update(isolated_pixels_changed_outside_mask=1)),
            ('boolean',lambda r:r.update(isolated_pixels_changed_outside_mask=False)),
            ('geometry',lambda r:r.update(added_length_outside_mask_source_pt=1)),
        ]
        for name,mutate in cases:
            candidate=copy.deepcopy(report);mutate(candidate['results'][0])
            rp.write_text(json.dumps(candidate));review['report_sha256']=sha(rp)
            assert validate_topology_review(review,sha(p['final']),kinds),name
        # A project's native operation mask must describe this exact transformed
        # union, not an enlarged envelope or a shifted collection of rectangles.
        rp.write_text(json.dumps(report));review['report_sha256']=sha(rp)
        parts=transformed_source_parts(plan['operations'][0],plan['source_to_final'])
        bounds=[min(v[0] for v in parts),min(v[1] for v in parts),
                max(v[2] for v in parts),max(v[3] for v in parts)]
        mask={'id':plan['operations'][0]['id'],'x':bounds[0],'y':bounds[1],
              'width':bounds[2]-bounds[0],'height':bounds[3]-bounds[1],'parts_final':parts}
        preservation={'approved_base_sha256':sha(p['base']),'correction_masks':[mask]}
        assert not validate_topology_review(review,sha(p['final']),kinds,
                                             project_preservation=preservation)
        for name,mutate in [
            ('missing_parts',lambda m:m.pop('parts_final')),
            ('reversed_parts',lambda m:m['parts_final'].reverse()),
            ('broad_envelope',lambda m:m.update(parts_final=[bounds])),
            ('shifted',lambda m:(m.update(x=m['x']+1),
                m.update(parts_final=[[x0+1,y0,x1+1,y1] for x0,y0,x1,y1 in m['parts_final']]))),
        ]:
            changed=copy.deepcopy(preservation);mutate(changed['correction_masks'][0])
            assert validate_topology_review(review,sha(p['final']),kinds,
                                            project_preservation=changed),name
    print('PASS multipart report contract +7 union-proof and +4 source-to-project mapping rejection cases')


if __name__=='__main__':
    test_actual_plan_report_artifact_and_independent_review_bindings()
    test_multipart_report_cannot_omit_or_change_union_proofs()
