#!/usr/bin/env python3
import argparse, hashlib, json, re, sys
from pathlib import Path

HEX64 = re.compile(r'^[0-9a-fA-F]{64}$')
NAMED_PUBLIC='named_public'
UNLABELED_ALLOWED={'intentionally_unlabeled_private','intentionally_unlabeled_unnamed','nonroad_feature'}
LABELED={'direct','curved','same_road_relocated_direct','same_road_relocated_curved','callout','detail_direct','detail_curved','detail_callout'}
CALLOUT={'callout','detail_callout'}
DIRECT={'direct','curved','same_road_relocated_direct','same_road_relocated_curved','detail_direct','detail_curved'}
NAME_STATUS={'named_public','named_private','unnamed','nonroad_feature'}


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main(review_path,pdf_path=None):
    data=json.loads(Path(review_path).read_text(encoding='utf-8'))
    errs=[]
    comp=data.get('label_completeness_review')
    vis=data.get('label_contact_cluster_review')
    if not isinstance(comp,dict): return {'passed':False,'errors':['missing label_completeness_review']}
    if not isinstance(vis,dict): return {'passed':False,'errors':['missing label_contact_cluster_review']}
    art=str(comp.get('artifact_sha256',''))
    if not HEX64.fullmatch(art): errs.append('label_completeness_review.artifact_sha256 must be 64 hex')
    if str(vis.get('artifact_sha256',''))!=art: errs.append('label review artifact hashes must match')
    if data.get('artifact_sha256') and data.get('artifact_sha256')!=art: errs.append('top-level artifact_sha256 must match label review')
    if pdf_path:
        actual=sha256(pdf_path)
        if actual.lower()!=art.lower(): errs.append('artifact_sha256 does not match exact PDF')
    for k in ['measurable_pdf_candidate','all_visible_road_features_inventoried','all_named_public_roads_labeled','private_unnamed_exceptions_source_verified']:
        if comp.get(k) is not True: errs.append(f'label_completeness_review.{k} must be true')
    if comp.get('generated_raster_only') is not False: errs.append('label_completeness_review.generated_raster_only must be false')
    zero_comp=['unaccounted_visible_road_count','unlabeled_required_road_count','unsupported_unlabeled_count','wrong_or_duplicate_road_label_count']
    for k in zero_comp:
        if comp.get(k)!=0: errs.append(f'label_completeness_review.{k} must equal 0')
    records=comp.get('records')
    if not isinstance(records,list): records=[]; errs.append('label_completeness_review.records must be an array')
    if comp.get('visible_road_feature_count')!=len(records): errs.append('visible_road_feature_count must equal records length')
    named_public=0
    seen_ids=set()
    label_owners={}
    for i,r in enumerate(records):
        p=f'label_completeness_review.records[{i}]'
        if not isinstance(r,dict): errs.append(f'{p} must be object'); continue
        rid=str(r.get('road_id','')).strip()
        if not rid: errs.append(f'{p}.road_id required')
        elif rid in seen_ids: errs.append(f'{p}.road_id duplicate')
        seen_ids.add(rid)
        ns=r.get('name_status')
        if ns not in NAME_STATUS: errs.append(f'{p}.name_status invalid')
        name=str(r.get('name','')).strip()
        if ns in ('named_public','named_private') and not name: errs.append(f'{p}.name required for named road')
        if not str(r.get('source_evidence','')).strip(): errs.append(f'{p}.source_evidence required')
        disp=r.get('label_disposition')
        req=r.get('label_required')
        ids=r.get('label_ids')
        if not isinstance(ids,list): ids=[]; errs.append(f'{p}.label_ids must be array')
        for lid in ids:
            lid=str(lid).strip()
            if not lid: errs.append(f'{p}.label_ids contains blank id'); continue
            prev=label_owners.get(lid)
            if prev is not None and prev!=rid: errs.append(f'label_id {lid} assigned to multiple roads: {prev}, {rid}')
            label_owners[lid]=rid
        if ns==NAMED_PUBLIC:
            named_public+=1
            if req is not True: errs.append(f'{p}.label_required must be true for named_public')
            if disp not in LABELED: errs.append(f'{p}.label_disposition must be labeled treatment for named_public')
            if not ids: errs.append(f'{p}.label_ids must contain at least one label for named_public')
            rc=r.get('required_label_count')
            if not isinstance(rc,int) or rc < 1: errs.append(f'{p}.required_label_count must be integer >=1 for named_public')
            elif len(ids) < rc: errs.append(f'{p}.label_ids count must meet required_label_count')
            if r.get('navigation_repeat_required') is True:
                if not isinstance(rc,int) or rc < 2: errs.append(f'{p}.navigation repeat requires required_label_count >=2')
                roles=r.get('navigation_roles')
                if not isinstance(roles,list) or len([x for x in roles if str(x).strip()]) < rc: errs.append(f'{p}.navigation_roles must cover repeated labels')
        elif ns=='named_private':
            if disp in UNLABELED_ALLOWED:
                if disp!='intentionally_unlabeled_private': errs.append(f'{p} named_private unlabeled disposition must be intentionally_unlabeled_private')
                if ids: errs.append(f'{p} intentionally unlabeled private road must not list label_ids')
            elif disp not in LABELED: errs.append(f'{p}.label_disposition invalid')
        elif ns=='unnamed':
            if disp!='intentionally_unlabeled_unnamed': errs.append(f'{p} unnamed road must use intentionally_unlabeled_unnamed')
            if ids: errs.append(f'{p} unnamed road must not list label_ids')
        elif ns=='nonroad_feature':
            if disp!='nonroad_feature': errs.append(f'{p} nonroad feature must use nonroad_feature disposition')
        if r.get('result') not in ('pass','PASS',True): errs.append(f'{p}.result must pass')
        if disp in DIRECT and r.get('is_short_street') is True:
            u=r.get('usable_run_px'); ink=r.get('label_ink_px'); br=r.get('end_breathing_room_px')
            if not all(isinstance(x,(int,float)) for x in (u,ink,br)): errs.append(f'{p} short direct measurements required')
            elif u < ink+30 or br < 15: errs.append(f'{p} short direct fit rule failed; use callout/detail')
        if disp in CALLOUT:
            for k in ['same_road_direct_options_exhausted','nearest_practical_whitespace_used','leader_attached','target_street_verified']:
                if r.get(k) is not True: errs.append(f'{p}.{k} must be true')
            gap=r.get('leader_tail_gap_px')
            if not isinstance(gap,(int,float)) or not (0<=gap<=2): errs.append(f'{p}.leader_tail_gap_px must be 0..2')
            if r.get('culdesac_has_stem') is True and r.get('target_stem_verified') is not True: errs.append(f'{p}.target_stem_verified required when culdesac_has_stem')
            if r.get('leader_word_crossings',0)!=0: errs.append(f'{p}.leader_word_crossings must be 0')
            if r.get('leader_unrelated_road_crossings',0)!=0: errs.append(f'{p}.leader_unrelated_road_crossings must be 0')
    if comp.get('named_public_visible_count')!=named_public: errs.append('named_public_visible_count must equal named_public records')

    for k in ['actual_size_inspected','two_x_inspected','four_x_full_map_inspected','all_labels_contact_checked','all_callouts_closeup_inspected','all_cluster_triggers_inspected']:
        if vis.get(k) is not True: errs.append(f'label_contact_cluster_review.{k} must be true')
    residential=comp.get('residential_neighborhood_map') is True
    if residential and vis.get('territory_273_label_system_side_by_side') is not True:
        errs.append('territory_273_label_system_side_by_side must be true for residential/neighborhood maps')
    zero_vis=['label_road_touch_count','label_road_overlap_count','wrong_road_contact_count','label_label_overlap_count','avoidable_label_cluster_count','clipped_label_count','broken_word_count','detached_leader_count','wrong_callout_target_count','callout_crossing_count','premature_callout_count']
    for k in zero_vis:
        if vis.get(k)!=0: errs.append(f'label_contact_cluster_review.{k} must equal 0')
    if vis.get('cluster_trigger_gap_px')!=12: errs.append('label_contact_cluster_review.cluster_trigger_gap_px must equal 12')
    if vis.get('all_label_pairs_screened_for_cluster_trigger') is not True: errs.append('label_contact_cluster_review.all_label_pairs_screened_for_cluster_trigger must be true')
    clusters=vis.get('cluster_records')
    if not isinstance(clusters,list): errs.append('label_contact_cluster_review.cluster_records must be an array'); clusters=[]
    if vis.get('cluster_trigger_count')!=len(clusters): errs.append('label_contact_cluster_review.cluster_trigger_count must equal cluster_records length')
    placement=data.get('label_placement_decision_review') or {}
    if isinstance(placement,dict) and isinstance(placement.get('label_count'),int) and vis.get('label_placement_count_screened')!=placement.get('label_count'):
        errs.append('label_contact_cluster_review.label_placement_count_screened must equal label_placement_decision_review.label_count')
    for i,c in enumerate(clusters):
        p=f'label_contact_cluster_review.cluster_records[{i}]'
        if not isinstance(c,dict): errs.append(f'{p} must be object'); continue
        if c.get('reviewed') is not True: errs.append(f'{p}.reviewed must be true')
        if c.get('ownership_unambiguous') is not True: errs.append(f'{p}.ownership_unambiguous must be true')
        if c.get('same_road_alternatives_assessed') is not True: errs.append(f'{p}.same_road_alternatives_assessed must be true')
        if c.get('clearer_alternative_exists') is not False: errs.append(f'{p}.clearer_alternative_exists must be false in passing artifact')
        if not isinstance(c.get('nearest_label_gap_px'),(int,float)): errs.append(f'{p}.nearest_label_gap_px required')
        ev=c.get('evidence')
        if not isinstance(ev,list) or len(ev)<2: errs.append(f'{p}.evidence must include actual-size and closeup')
    ev=vis.get('evidence')
    if not isinstance(ev,list) or len(ev)<3: errs.append('label_contact_cluster_review.evidence must list actual-size, 2x, and 4x evidence')
    if not isinstance(data.get('delivery_format_review'),dict): errs.append('delivery_format_review required by R51')
    if not isinstance(data.get('label_metric_review'),dict): errs.append('label_metric_review required by R51')
    return {'passed':not errs,'errors':errs,'visible_road_feature_count':len(records),'named_public_visible_count':named_public,'cluster_record_count':len(clusters)}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('review_json')
    ap.add_argument('--pdf')
    a=ap.parse_args()
    res=main(a.review_json,a.pdf)
    print(json.dumps(res,indent=2))
    sys.exit(0 if res['passed'] else 1)