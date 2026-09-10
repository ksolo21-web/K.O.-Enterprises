"""Isolated proposal: immutable original -> native addition -> existing repair.

The whole-ROI historical comparator is retained. Only its contaminated width
statistic may be replaced by source-bound connected normal sections, with a
maximum (not median) <= the unchanged 1.25px limit. All other metrics remain.
"""
import json,sys,math,copy
from pathlib import Path
import fitz,numpy as np
from matched_width import measure
sys.path.insert(0,str(Path(__file__).resolve().parent))
import validate_topology_patch as t
import validate_stroke_style as stroke

def verify(plan_path,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);p=t.load(plan_path)
    t.require(p.get('schema_version')=='mixed-native-existing-chain-1','Invalid chain schema')
    def bound(k):return t.evidence_file(p[k],k)
    addplan=bound('addition_plan');ap=t.load(addplan)
    paths={k:bound(k)for k in ['original_textfree','addition_source','original_layout_final','addition_final','repaired_source','final_pdf','repair_origin','independent_repair_review','estimator_diagnosis','independent_estimator_review']}
    # This runs the unchanged native gate against true original authority.
    native=t.verify(addplan,paths['original_textfree'],paths['addition_source'],paths['original_layout_final'],paths['addition_final'],out/'addition-evidence')
    (out/'addition-report.json').write_text(json.dumps(native,indent=2))
    estimator_review=t.load(paths['independent_estimator_review'])
    t.require(estimator_review.get('module_sha256')==t.sha(Path(__file__).with_name('matched_width.py')) and estimator_review.get('accepted_for_estimator_use') is True and bool(estimator_review.get('independent_reviewer')),'Matched estimator lacks exact independently reviewed implementation')
    origin=t.load(paths['repair_origin']);review=t.load(paths['independent_repair_review'])
    t.require(review.get('proposal_sha256')==t.sha(paths['repair_origin']) and review.get('approved_for_bounded_candidate_repair') is True and review.get('independent_plan_review') is True,'Repair origin lacks independent exact-plan approval')
    t.require(origin.get('mask_source')==review.get('mask_source')==p.get('repair_mask_source'),'Repair mask differs from independently reviewed origin')
    t.require(not ap.get('source_views'),'Mixed proposal currently requires one scalar native view')
    before=fitz.open(paths['addition_source']);after=fitz.open(paths['repaired_source']);expected=fitz.open(paths['addition_source']);page=ap['source_page_index'];xref,raw=t.source_stream(before,page);changed=raw
    operations=origin.get('operations');t.require(isinstance(operations,list) and operations,'Missing predeclared repair operations')
    for op in operations:
        old,new=op['before_ascii'],op['after_ascii'];t.require(t.native_tokens(old)==t.native_tokens(new),'Repair changed graphics context')
        t.require(changed.count(old.encode())==1 and new.encode() not in raw,'Repair exact operation occurrence mismatch')
        changed=changed.replace(old.encode(),new.encode())
    expected.update_stream(xref,changed)
    t.require(len(after)==len(expected),'Repair page count changed')
    for index in range(len(after)):
        t.compare_all_drawings(expected[index],after[index],epsilon=1e-6)
        t.require(expected[index].get_pixmap(matrix=fitz.Matrix(2,2),alpha=True).samples==after[index].get_pixmap(matrix=fitz.Matrix(2,2),alpha=True).samples,'Repaired source contains undeclared image or visibility changes')
    ax,ar=t.source_stream(after,page);t.require(ar==changed,'Actual repaired source stream differs from exact planned replay')
    bd=before[page].get_drawings();ed=expected[page].get_drawings();t.require(len(bd)==len(ed),'Existing repair changed drawing count')
    changed_ids=[];stems=[]
    for index,(old,new) in enumerate(zip(bd,ed)):
        t.require(t.drawing_record(old)['style']==t.drawing_record(new)['style'],'Existing repair changed native source style')
        if old['items']==new['items']:continue
        changed_ids.append(index)
        t.require(old['items'][:-1]==new['items'][:-1] and old['items'][-1][0]==new['items'][-1][0]=='l','Only predeclared terminal line endpoint repair is supported')
        a,e=map(np.array,map(tuple,old['items'][-1][1:]));aa,ee=map(np.array,map(tuple,new['items'][-1][1:]))
        t.require(np.array_equal(a,aa),'Terminal start changed')
        v=e-a;ratio=float(np.dot(ee-a,v)/np.dot(v,v));perp=float(np.linalg.norm((ee-a)-ratio*v))
        t.require(0<ratio<1 and perp<=t.FINAL_GEOMETRY_EPSILON_PT,'Repair must be a collinear terminal retreat within serialization allowance')
        stems.append((index,a,ee,old))
    t.require(set(changed_ids)=={op['drawing']for op in operations},'Actual changed native drawings differ from independent plan')
    original_final=fitz.open(paths['addition_final']);actual=fitz.open(paths['final_pdf']);expected_final=fitz.open(paths['addition_final']);form=t.find_form(expected_final,0,raw);expected_final.update_stream(form,changed)
    t.require(len(actual)==len(expected_final)==1,'Final must stay one page')
    t.compare_all_drawings(expected_final[0],actual[0]);t.require(original_final[0].get_text('rawdict')==actual[0].get_text('rawdict'),'Repair changed glyph content or placement')
    scale,tx,ty=[ap['source_to_final'][k]for k in ['scale','translate_x','translate_y']];transform=np.array([tx,ty]);mask=p['repair_mask_source'];checks=[]
    for z in [1,2,4]:
        def render(doc):
            pix=doc[0].get_pixmap(matrix=fitz.Matrix(z,z),alpha=False);return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        base,final,planned=map(render,[original_final,actual,expected_final]);t.require(np.array_equal(final,planned),'Actual final differs from exact composed expected render')
        region=np.zeros(base.shape[:2],bool);x0,y0,x1,y1=[(mask[0]*scale+tx)*z,(mask[1]*scale+ty)*z,(mask[2]*scale+tx)*z,(mask[3]*scale+ty)*z];region[math.floor(y0):math.ceil(y1),math.floor(x0):math.ceil(x1)]=True
        outside=int((np.any(base!=final,axis=2)&~region).sum());t.require(outside==0,'Repair pixels changed outside exact independent mask');checks.append({'scale':z,'outside_pixels':outside})
        if z==2:base2,final2=base,final
        if z==4:base4,final4=base,final
    # Original comparator is executed fresh on actual final2x; keep its report.
    t.require(set(p['stroke_config_2x'])<= {'palette','masks'} and set(p['stroke_config_4x'])<= {'palette','masks'},'Matched repair cannot override original comparator parameters or limits')
    cfg=copy.deepcopy(p['stroke_config_2x']);m=cfg['masks'];t.require(len(m)==1 and m[0].get('contains_stroke_repair') is True,'Exactly one existing repair mask required')
    def box(coords,z=2):
        x0,y0,x1,y1=[(coords[0]*scale+tx)*z,(coords[1]*scale+ty)*z,(coords[2]*scale+tx)*z,(coords[3]*scale+ty)*z];return dict(x=math.floor(x0),y=math.floor(y0),width=math.ceil(x1)-math.floor(x0),height=math.ceil(y1)-math.floor(y0))
    t.require(all(m[0].get(k)==v for k,v in box(mask).items()),'Stroke mask does not match source-bound final2x footprint')
    historic=stroke.serializable_diagnostics(stroke.analyze(base2,final2,cfg));(out/'original-comparator-report.json').write_text(json.dumps(historic,indent=2))
    names,colors=stroke.parse_palette(cfg);bclass,bdist=stroke.palette_assignment(base2,colors);aclass,adist=stroke.palette_assignment(final2,colors);measurements=[]
    for index,a,e,drawing in stems:
        rgb=np.asarray(drawing['color'])*255;status_index=int(np.argmin(np.linalg.norm(colors-rgb,axis=1)))
        # This bounded contract requires explicit work-status coverage for every changed paint.
        t.require(np.linalg.norm(colors[status_index]-rgb)<=stroke.DEFAULT_CORE_COLOR_TOLERANCE,'Changed native paint absent from explicit work-status palette')
        t.require(names[status_index] in m[0]['statuses'],'Every changed native work status must receive all historical comparator checks')
        before_mask=(bclass==status_index)&(bdist<=stroke.DEFAULT_FRINGE_COLOR_TOLERANCE);after_mask=(aclass==status_index)&(adist<=stroke.DEFAULT_FRINGE_COLOR_TOLERANCE);core=(bclass==status_index)&(bdist<=stroke.DEFAULT_CORE_COLOR_TOLERANCE)
        r=measure(before_mask,after_mask,core,(a*scale+transform)*2,(e*scale+transform)*2,drawing['width']*scale*2);t.require(r['passed'],'Matched source-stem width exceeds unchanged1.25px limit');r.update(source_drawing=index,status=names[status_index],render_scale=2);measurements.append(r)
    t.require(measurements,'No native source-bound work-status stem measured')
    cfg4=copy.deepcopy(p['stroke_config_4x']);t.require(len(cfg4['masks'])==1 and cfg4['masks'][0].get('contains_stroke_repair') is True and cfg4['masks'][0]['statuses']==m[0]['statuses'] and cfg4['palette']==cfg['palette'],'4x status/palette must match2x')
    t.require(all(cfg4['masks'][0].get(k)==v for k,v in box(mask,4).items()),'4x mask does not match fixed source footprint')
    historic4=stroke.serializable_diagnostics(stroke.analyze(base4,final4,cfg4));(out/'original-comparator-report-4x.json').write_text(json.dumps(historic4,indent=2))
    bc4,bd4=stroke.palette_assignment(base4,colors);ac4,ad4=stroke.palette_assignment(final4,colors)
    for index,a,e,drawing in stems:
        rgb=np.asarray(drawing['color'])*255;si=int(np.argmin(np.linalg.norm(colors-rgb,axis=1)))
        t.require(np.linalg.norm(colors[si]-rgb)<=stroke.DEFAULT_CORE_COLOR_TOLERANCE,'Changed4x native paint absent from explicit palette')
        r=measure((bc4==si)&(bd4<=120),(ac4==si)&(ad4<=120),(bc4==si)&(bd4<=55),(a*scale+transform)*4,(e*scale+transform)*4,drawing['width']*scale*4);t.require(r['passed'],'4x matched native stem width exceeds unchanged1.25px');r.update(source_drawing=index,status=names[si],render_scale=4);measurements.append(r)
    for row in historic4['results']:
        t.require(all(f.startswith('stroke_width:')for f in row.get('failures',[])),'4x original comparator has non-width failure')
    t.require(historic4.get('pixels_changed_outside_declared_masks')==0,'4x outside-mask comparator failed')
    # No other historical failure may be waived. Limits remain original defaults.
    for result in historic['results']:
        failures=result.get('failures',[])
        t.require(all(f.startswith('stroke_width:') for f in failures),'Existing comparator has a non-width failure: '+str(failures))
    t.require(historic.get('pixels_changed_outside_declared_masks')==0,'Original comparator outside-mask gate failed')
    # The addition remains visible exactly as independently verified in stage1.
    addition_region=np.zeros(base2.shape[:2],bool)
    for op in ap['operations']:
        for part in t.source_mask_parts(op):
            bounds=box(part);addition_region |= stroke.box_mask(base2.shape[:2],tuple(bounds[k] for k in ('x','y','width','height')))
    t.require(not np.any(np.any(base2!=final2,axis=2)&addition_region),'Repair alters an addition-stage region; overlapping stages need a separately supported contract')
    expected.save(out/'expected-repaired-source.pdf');expected_final.save(out/'expected-composed-final.pdf')
    def record(path):return {'path':str(path),'sha256':t.sha(path)}
    current_capture=out/'actual-final-1x.png';actual[0].get_pixmap(alpha=False).save(current_capture)
    paired=[]
    for label,doc in [('before',original_final),('after',actual)]:
        path=out/('repair-'+label+'-4x.png');rect=fitz.Rect(mask[0]*scale+tx,mask[1]*scale+ty,mask[2]*scale+tx,mask[3]*scale+ty);doc[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False).save(path);paired.append(record(path))
    corrected=copy.deepcopy(historic);corrected['schema_version']='source-bound-existing-stem-style-report-1';corrected['status']='PASS';corrected['artifact_sha256']=t.sha(paths['final_pdf']);corrected['chain_plan_sha256']=t.sha(plan_path);corrected['original_comparator']=record(out/'original-comparator-report.json');corrected['method']='Exact native terminal replay and source-bound connected normal sections; all other original comparator metrics retained';corrected['repaired_stroke_style_mismatches']=0
    for row in corrected['results']:
        row['original_width_median_delta_px']=row['metrics']['median_width_delta_px'];row['metrics']['median_width_delta_px']=max(m['maximum_width_delta_px']for m in measurements);row['width_statistic']='maximum_paired_source_station_delta';row['original_whole_roi_status_metrics']=row.pop('status_metrics',{});row['matched_stem_measurements']=measurements;row['passed']=True;row['failures']=[]
    (out/'corrected-style-report.json').write_text(json.dumps(corrected,indent=2))
    report={'schema_version':'mixed-native-existing-report-1','status':'PASS','artifact_sha256':t.sha(paths['final_pdf']),'chain_plan_sha256':t.sha(plan_path),'original_assignment_sha256':native['original_assignment_sha256'],'addition_artifact_sha256':t.sha(paths['addition_final']),'source_chain_exact':True,'existing_native_style_identity':True,'source_bound_terminal_operations':changed_ids,'full_composed_expected_native_and_render_identical':True,'repair_render_checks':checks,'historical_comparator_retained':str(out/'original-comparator-report.json'),'matched_stem_measurements':measurements,'all_other_original_comparator_checks_passed':True,'independent_final_visual_review_required':True,'release_ready':False,'inputs':{k:record(v)for k,v in paths.items()},'addition_plan':record(addplan),'native_stage_report':record(out/'addition-report.json'),'corrected_style_report':record(out/'corrected-style-report.json'),'expected_source':record(out/'expected-repaired-source.pdf'),'expected_final':record(out/'expected-composed-final.pdf'),'actual_size_screenshot':record(current_capture),'paired_repair_4x':paired,'addition_region_unchanged_by_repair':True,'repair_mask_source':mask,'validator_sha256':t.sha(__file__),'matched_width_sha256':t.sha(Path(__file__).with_name('matched_width.py')),'historical_comparator_reports':[record(out/'original-comparator-report.json'),record(out/'original-comparator-report-4x.json')]}
    (out/'report.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    try:print(json.dumps(verify(sys.argv[1],sys.argv[2]),indent=2))
    except Exception as exc:
        Path(sys.argv[2]).mkdir(parents=True,exist_ok=True);Path(sys.argv[2],'report.json').write_text(json.dumps({'status':'FAIL','error':str(exc)},indent=2));raise
