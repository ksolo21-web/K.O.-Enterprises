"""Report gate for typed topology edits; does not waive existing-path repairs."""
import hashlib
import json
import math
from pathlib import Path
from preservation_authority_contract import validate_preservation_authorities
from mixed_chain_contract import validate_mixed_chain
from shared_junction_contract import validate_pair_report
from topology_masks import source_mask_parts, final_mask_parts, transformed_source_parts

LIMITS={'median_width_delta_px':1.25,'maximum_color_delta_rgb':18.0,'edge_softness_delta_px':0.85,'texture_delta':2.5,'unexpected_status_pixel_count':0}
KINDS={'native_topology_addition':'addition','native_topology_removal':'removal'}


def file_record(record):
    if not isinstance(record,dict):return False
    if not isinstance(record.get('path'),str):return False
    path=Path(record['path'])
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==record.get('sha256')


def validate_topology_review(review,artifact_sha256,mask_kinds=None,original_assignment_sha256=None,source_class=None,project_preservation=None):
    errors=[]
    if review is None and not mask_kinds:return errors
    if not isinstance(review,dict):return ['topology_patch_review is required for every typed native topology mask']
    def check(value,message):
        if not value:errors.append(message)
    def load_bound(prefix):
        record={'path':review.get(prefix+'_path',''),'sha256':review.get(prefix+'_sha256')}
        if not file_record(record):
            errors.append(f'topology_patch_review.{prefix} file/hash mismatch');return {}
        try:
            value=json.loads(Path(record['path']).read_text())
            if not isinstance(value,dict):raise ValueError('not an object')
            return value
        except (ValueError,OSError):errors.append(f'Invalid topology {prefix} JSON');return {}
    report=load_bound('report');plan=load_bound('plan')
    stage_artifact_hash=artifact_sha256
    if review.get('mixed_chain_review') is not None:
        chain_errors,stage_artifact_hash=validate_mixed_chain(review['mixed_chain_review'],artifact_sha256,original_assignment_sha256,
            {'path':review.get('report_path'),'sha256':review.get('report_sha256')},
            {'path':review.get('plan_path'),'sha256':review.get('plan_sha256')},project_preservation)
        errors.extend(chain_errors)
    check(bool(stage_artifact_hash) and report.get('artifact_sha256')==stage_artifact_hash,'Topology report must bind the current final or exact explicit mixed-chain native stage')
    check(report.get('schema_version')=='native-topology-report-1' and report.get('status')=='PASS','Topology report must pass the native topology gate')
    check(report.get('plan_sha256')==review.get('plan_sha256'),'Topology report/plan hash mismatch')
    if source_class is not None:
        check(report.get('source_class')==source_class and plan.get('source_class')==source_class,'Topology source classification differs from project authority')
    if original_assignment_sha256 is not None:
        check(report.get('original_assignment_sha256')==original_assignment_sha256,'Topology original assignment hash differs from project coverage source')
    errors.extend(validate_preservation_authorities(review, plan, report, artifact_sha256,
        original_assignment_sha256, project_preservation))
    for key in ('original_to_base_drawing_identity_verified','native_operations_verified','no_other_native_path_or_style_changes','actual_final_transformed_geometry_verified','expected_final_render_identical','deletion_deltas_verified'):
        check(report.get(key) is True,f'Topology report requires {key}')
    check(type(report.get('pixels_changed_outside_declared_masks')) is int and report.get('pixels_changed_outside_declared_masks')==0,'Topology pixels outside declared masks must equal 0')
    errors.extend(validate_pair_report(plan,report))
    operations=plan.get('operations',[]);results=report.get('results',[])
    if not isinstance(operations,list):operations=[]
    if not isinstance(results,list):results=[]
    expected={o.get('id'):o.get('kind') for o in operations if isinstance(o,dict)}
    actual={r.get('mask_id'):r for r in results if isinstance(r,dict)}
    check(bool(expected) and len(expected)==len(operations)==len(results)==len(actual) and set(expected)==set(actual),'Topology result IDs must exactly cover every declared operation')
    if mask_kinds is not None:
        check(expected=={k:KINDS.get(v) for k,v in mask_kinds.items()},'Typed correction masks must exactly match topology operation IDs/kinds')
    for operation in operations:
        if not isinstance(operation,dict) or 'mask_source_parts' not in operation:continue
        key=operation.get('id');result=actual.get(key,{})
        try:
            parts=source_mask_parts(operation)
        except ValueError as exc:
            errors.append(f'{key}: invalid multipart topology mask: {exc}');continue
        preservation=project_preservation if isinstance(project_preservation,dict) else review.get('preservation_authorities')
        if isinstance(preservation,dict):
            masks=preservation.get('correction_masks',[])
            found=[m for m in masks if isinstance(m,dict) and m.get('id')==key] if isinstance(masks,list) else []
            check(len(found)==1,f'{key}: multipart native operation must identify one project correction mask')
            if len(found)==1:
                mask=found[0]
                try:
                    final_parts=final_mask_parts(mask)
                    expected_parts=transformed_source_parts(operation,plan.get('source_to_final',{}))
                    matches=(len(final_parts)==len(expected_parts) and all(
                        all(math.isclose(a,b,rel_tol=0,abs_tol=1e-9) for a,b in zip(left,right))
                        for left,right in zip(final_parts,expected_parts)))
                    check('parts_final' in mask and matches,
                          f'{key}: project parts_final must equal exact ordered source parts transformed to final PDF points')
                    if 'mask_source_parts' in mask:
                        check(mask['mask_source_parts']==parts,f'{key}: project source parts differ from native plan')
                except (TypeError,ValueError,AttributeError) as exc:
                    errors.append(f'{key}: invalid project multipart mask: {exc}')
        check(result.get('mask_source')==operation.get('mask_source') and result.get('mask_source_parts')==parts,
              f'{key}: topology report must bind exact ordered mask parts and envelope')
        check(type(result.get('mask_renderer_guard_2x_px')) is int and result.get('mask_renderer_guard_2x_px')==1,
              f'{key}: multipart mask renderer guard must remain one 2x pixel')
        check(result.get('isolated_delta_contained') is True,f'{key}: isolated native multipart delta containment is required')
        count=result.get('isolated_pixels_changed_outside_mask')
        check(type(count) is int and count==0,f'{key}: isolated rendered pixels outside multipart union must equal 0')
        for metric in ('added_length_outside_mask_source_pt','removed_length_outside_mask_source_pt'):
            value=result.get(metric)
            check(type(value) in (int,float) and math.isfinite(value) and value==0,
                  f'{key}: {metric} must equal 0')
    for key,result in actual.items():
        check(result.get('passed') is True and result.get('kind')==expected.get(key),f'{key}: invalid topology result')
        count=result.get('expected_occurrences')
        check(type(count) is int and count>0 and result.get('actual_occurrences')==count,f'{key}: native operation counts disagree')
        check(result.get('native_operations_verified') is True and result.get('deletion_delta_verified') is True,f'{key}: native/deletion delta evidence missing')
        check(result.get('original_reference_native_style_verified') is True,f'{key}: original same-status native style evidence missing')
        for metric,limit in LIMITS.items():
            value=result.get('style_metrics',{}).get(metric)
            check(type(value) in (int,float) and math.isfinite(value) and 0<=value<=limit,f'{key}: topology {metric} exceeds unchanged limit or is missing')
        width=result.get('original_reference_native_width_delta_px')
        check(type(width) in (int,float) and math.isfinite(width) and 0<=width<=1.25,f'{key}: original reference native width mismatch')
    visual=review.get('independent_visual_review',{})
    if not isinstance(visual,dict):visual={}
    for key in ('independent','source_plan_review_completed','actual_size_review_completed','paired_4x_review_completed','no_visible_style_mismatch'):
        check(visual.get(key) is True,f'Topology independent visual review requires {key}')
    check(visual.get('artifact_sha256')==artifact_sha256 and visual.get('plan_sha256')==review.get('plan_sha256'),'Independent topology review must bind final PDF and exact source-backed plan')
    check(isinstance(visual.get('evidence'),str) and bool(visual['evidence'].strip()),'Independent topology review needs source/region-specific evidence')
    captures=report.get('paired_4x_screenshots',[])
    check(isinstance(captures,list) and {c.get('mask_id') for c in captures if isinstance(c,dict)}==set(expected),'Require actual paired 4x captures for every topology mask')
    if isinstance(captures,list):
        for capture in captures:
            if isinstance(capture,dict):
                for key in ('before_4x','after_4x'):check(file_record(capture.get(key)),f'Missing or changed topology {key} screenshot')
    check(file_record(report.get('actual_size_screenshot')),'Missing or changed actual-size topology screenshot')
    for key in ('expected_source','expected_final'):check(file_record(report.get(key)),f'Missing or changed source-backed {key} PDF evidence')
    return errors
