#!/usr/bin/env python3
import argparse, hashlib, json, os, re, sys
from pathlib import Path
HEX64=re.compile(r'^[0-9a-fA-F]{64}$')

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def main(review_path,pdf_path=None):
    d=json.loads(Path(review_path).read_text(encoding='utf-8')); e=[]
    fmt=d.get('delivery_format_review'); m=d.get('label_metric_review')
    if not isinstance(fmt,dict): return {'passed':False,'errors':['missing delivery_format_review']}
    if not isinstance(m,dict): return {'passed':False,'errors':['missing label_metric_review']}
    art=str(m.get('artifact_sha256',''))
    if not HEX64.fullmatch(art): e.append('label_metric_review.artifact_sha256 must be 64 hex')
    if str(fmt.get('artifact_sha256',''))!=art: e.append('delivery/metric artifact hashes must match')
    if d.get('artifact_sha256') and d.get('artifact_sha256')!=art: e.append('top-level artifact hash mismatch')
    name=str(fmt.get('artifact_filename',''))
    if not name.lower().endswith('.pdf'): e.append('artifact_filename must end .pdf')
    if fmt.get('artifact_mime_type')!='application/pdf': e.append('artifact_mime_type must be application/pdf')
    for k in ['final_user_deliverable_pdf','image_preview_only','vector_or_native_map_geometry','pdf_openable','single_page']:
        if fmt.get(k) is not True: e.append(f'delivery_format_review.{k} must be true')
    if fmt.get('encrypted') is not False: e.append('delivery_format_review.encrypted must be false')
    b=fmt.get('bytes')
    if not isinstance(b,int) or b<=0 or b>=300000: e.append('delivery_format_review.bytes must be 1..299999')
    if pdf_path:
        if Path(pdf_path).suffix.lower()!='.pdf': e.append('provided release artifact is not PDF')
        elif sha256(pdf_path).lower()!=art.lower(): e.append('artifact_sha256 does not match exact PDF')
        if isinstance(b,int) and os.path.exists(pdf_path) and os.path.getsize(pdf_path)!=b: e.append('delivery bytes mismatch')
    if m.get('measurement_reference')!='exact_final_pdf_1x_72dpi': e.append('measurement_reference must be exact_final_pdf_1x_72dpi')
    refs=m.get('reference_label_ids'); gaps=m.get('reference_gap_values_px')
    if not isinstance(refs,list) or len(refs)<3: e.append('at least 3 reference_label_ids required')
    if not isinstance(gaps,list) or len(gaps)<3 or not all(isinstance(x,(int,float)) for x in gaps): e.append('at least 3 numeric reference_gap_values_px required')
    med=m.get('reference_gap_median_px'); tol=m.get('consistency_tolerance_px')
    if not isinstance(med,(int,float)) or not (2<=med<=15): e.append('reference_gap_median_px must be 2..15')
    if not isinstance(tol,(int,float)) or tol<=0 or tol>3: e.append('consistency_tolerance_px must be >0 and <=3')
    if m.get('reference_gap_consistency_passed') is not True: e.append('reference_gap_consistency_passed must be true')
    if m.get('outlier_label_count')!=0: e.append('outlier_label_count must be 0')
    metrics=m.get('label_metrics')
    if not isinstance(metrics,list) or not metrics: metrics=[]; e.append('label_metrics array required')
    seen=set()
    for i,x in enumerate(metrics):
        p=f'label_metrics[{i}]'
        if not isinstance(x,dict): e.append(f'{p} must be object'); continue
        lid=str(x.get('label_id','')).strip(); street=str(x.get('street','')).strip()
        if not lid: e.append(f'{p}.label_id required')
        elif lid in seen: e.append(f'{p}.label_id duplicate')
        seen.add(lid)
        if not street: e.append(f'{p}.street required')
        gap=x.get('assigned_road_gap_px')
        if not isinstance(gap,(int,float)) or gap<2 or gap>15: e.append(f'{p}.assigned_road_gap_px must be 2..15')
        if x.get('touches_any_road') is not False: e.append(f'{p}.touches_any_road must be false')
        if x.get('overlaps_any_road') is not False: e.append(f'{p}.overlaps_any_road must be false')
        if x.get('alignment_passed') is not True: e.append(f'{p}.alignment_passed must be true')
        if x.get('match_reference_gap') is True and isinstance(gap,(int,float)) and isinstance(med,(int,float)) and isinstance(tol,(int,float)) and abs(gap-med)>tol:
            e.append(f'{p} exceeds same-card reference gap tolerance')
        if x.get('cluster_clearance_passed') is not True: e.append(f'{p}.cluster_clearance_passed must be true')
    groups=m.get('repeat_label_groups')
    if not isinstance(groups,list): groups=[]; e.append('repeat_label_groups array required')
    for i,g in enumerate(groups):
        p=f'repeat_label_groups[{i}]'
        if not isinstance(g,dict): e.append(f'{p} must be object'); continue
        req=g.get('required_count'); actual=g.get('actual_count'); ids=g.get('label_ids'); roles=g.get('navigation_roles')
        if not isinstance(req,int) or req<2: e.append(f'{p}.required_count must be >=2')
        if actual!=req: e.append(f'{p}.actual_count must equal required_count')
        if not isinstance(ids,list) or len(ids)!=req or len(set(ids))!=req: e.append(f'{p}.label_ids must be distinct and match count')
        if not isinstance(roles,list) or len(roles)!=req or len(set(map(str,roles)))!=req: e.append(f'{p}.navigation_roles must be distinct and match count')
        if g.get('materially_separated_runs') is not True: e.append(f'{p}.materially_separated_runs must be true')
        if g.get('navigation_improved') is not True: e.append(f'{p}.navigation_improved must be true')
        if g.get('new_cluster_created') is not False: e.append(f'{p}.new_cluster_created must be false')
    return {'passed':not e,'errors':e,'label_metric_count':len(metrics),'repeat_group_count':len(groups)}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('review_json'); ap.add_argument('--pdf'); a=ap.parse_args()
    r=main(a.review_json,a.pdf); print(json.dumps(r,indent=2)); sys.exit(0 if r['passed'] else 1)