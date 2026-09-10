"""Evidence contract for an explicit native-addition then existing-repair chain."""
import hashlib,json,math
from pathlib import Path

def valid(record):
    try:return hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()==record['sha256']
    except (KeyError,TypeError,OSError,ValueError):return False

def validate_mixed_chain(review,artifact_hash,assignment_hash,native_report_record,native_plan_record,preservation=None):
    errors=[]
    def check(value,message):
        if not value:errors.append('Mixed chain: '+message)
    if not isinstance(review,dict):return ['Mixed chain evidence is required'],None
    def load(key):
        record=review.get(key);check(valid(record),key+' file/hash mismatch')
        try:return json.loads(Path(record['path']).read_text()) if valid(record) else {}
        except (ValueError,TypeError):return {}
    plan=load('plan');report=load('report')
    check(plan.get('schema_version')=='mixed-native-existing-chain-1','unsupported plan schema')
    for name,key in [('validate_mixed_chain.py','validator_sha256'),('matched_width.py','matched_width_sha256')]:
        module=Path(__file__).with_name(name);check(module.is_file() and hashlib.sha256(module.read_bytes()).hexdigest()==report.get(key),'validator implementation hash mismatch')
    check(report.get('schema_version')=='mixed-native-existing-report-1' and report.get('status')=='PASS','actual mixed verifier must pass')
    check(report.get('chain_plan_sha256')==(review.get('plan')or{}).get('sha256'),'report/plan mismatch')
    check(report.get('artifact_sha256')==artifact_hash,'final artifact mismatch')
    check(report.get('original_assignment_sha256')==assignment_hash,'immutable original source mismatch')
    check(report.get('native_stage_report')==native_report_record,'outer topology must reference exact intermediate native stage report')
    check(report.get('addition_plan')==native_plan_record==plan.get('addition_plan'),'outer topology must preserve original native stage plan')
    keys=['original_textfree','addition_source','original_layout_final','addition_final','repaired_source','final_pdf','repair_origin','independent_repair_review','estimator_diagnosis','independent_estimator_review']
    for key in keys:
        record=plan.get(key);check(valid(record) and report.get('inputs',{}).get(key)==record,key+' chain input missing/stale')
    check((plan.get('final_pdf')or{}).get('sha256')==artifact_hash,'chain final does not bind actual card')
    check((plan.get('addition_final')or{}).get('sha256')==report.get('addition_artifact_sha256'),'intermediate native artifact mismatch')
    for key in ['source_chain_exact','existing_native_style_identity','full_composed_expected_native_and_render_identical','addition_region_unchanged_by_repair','all_other_original_comparator_checks_passed']:
        check(report.get(key)is True,key+' must be verified')
    checks=report.get('repair_render_checks',[]);check({r.get('scale')for r in checks}=={1,2,4} and all(r.get('outside_pixels')==0 for r in checks),'actual1x2x4x repair containment missing')
    measurements=report.get('matched_stem_measurements',[])
    check(bool(measurements) and {m.get('render_scale')for m in measurements}=={2,4},'both2x4x source-bound stem measurements required')
    for m in measurements:
        v=m.get('maximum_width_delta_px');check(type(v)in(int,float) and math.isfinite(v) and 0<=v<=1.25 and m.get('passed')is True,'matched source-stem width exceeds unchanged limit')
        check(m.get('source_station_selection_only')is True and len(m.get('stations',[]))>=3,'source-only stations missing')
    for key in ['expected_source','expected_final','corrected_style_report','actual_size_screenshot']:
        check(valid(report.get(key)),key+' exact evidence missing/stale')
    check(len(report.get('paired_repair_4x',[]))==2 and all(valid(v)for v in report.get('paired_repair_4x',[])),'paired actual repair4x evidence required')
    history=report.get('historical_comparator_reports',[]);check(len(history)==2 and all(valid(v)for v in history),'both original2x4x comparator reports must remain hash-bound')
    visual=review.get('independent_visual_review',{})
    for key in ['independent','original_source_reviewed','addition_stage_reviewed','repair_stage_reviewed','actual_size_review_completed','paired_4x_review_completed','no_visible_style_mismatch']:
        check(visual.get(key)is True,'independent visual '+key+' required')
    check(visual.get('artifact_sha256')==artifact_hash and visual.get('chain_plan_sha256')==(review.get('plan')or{}).get('sha256'),'independent visual binding mismatch')
    check(bool(visual.get('evidence')),'independent source/region evidence required')
    if isinstance(preservation,dict):
        check({'path':preservation.get('stroke_style_report'),'sha256':preservation.get('stroke_style_report_sha256')}==report.get('corrected_style_report'),'project must bind corrected existing-style report, retaining historical failure separately')
    return errors,report.get('addition_artifact_sha256')
