#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
from validate_label_completeness_preflight import main as validate_completeness
HEX64=re.compile(r'^[0-9a-fA-F]{64}$')
ALLOWED={
 'direct','curved','same_road_relocated_direct','same_road_relocated_curved',
 'callout','detail_direct','detail_curved','detail_callout','approved_source_connector'
}
CALLOUT={'callout','detail_callout'}
DIRECT={'direct','curved','same_road_relocated_direct','same_road_relocated_curved','detail_direct','detail_curved'}

def fail(msg, errs): errs.append(msg)
def main(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    r=data.get('label_placement_decision_review') or data.get('new_design_visual_review',{}).get('label_placement_decision_review')
    errs=[]
    if not isinstance(r,dict):
        return {'passed':False,'errors':['missing label_placement_decision_review']}
    if not HEX64.fullmatch(str(r.get('artifact_sha256',''))): fail('artifact_sha256 must be 64 hex',errs)
    for k in ['all_navigational_labels_inventoried','label_decision_tree_completed','same_road_before_callout_verified']:
        if r.get(k) is not True: fail(f'{k} must be true',errs)
    zero_fields=[
      'label_overhang_violations','floating_unled_labels','distant_avoidable_callouts',
      'callouts_without_exhausted_direct_options','callouts_not_in_nearest_practical_whitespace',
      'label_road_touch_violations','label_road_overlap_violations','avoidable_label_clusters',
      'missing_required_labels','unsupported_unlabeled_roads'
    ]
    for k in zero_fields:
        if r.get(k)!=0: fail(f'{k} must equal 0',errs)
    if r.get('all_visible_named_public_roads_accounted_for') is not True:
        fail('all_visible_named_public_roads_accounted_for must be true',errs)
    if r.get('label_cluster_review_completed') is not True:
        fail('label_cluster_review_completed must be true',errs)
    dec=r.get('decisions')
    if not isinstance(dec,list): dec=[]; fail('decisions must be an array',errs)
    if r.get('label_count')!=len(dec): fail('label_count must equal decisions length',errs)
    calc_callouts=0
    for i,d in enumerate(dec):
        p=f'decisions[{i}]'
        if not isinstance(d,dict): fail(f'{p} must be object',errs); continue
        street=str(d.get('street') or d.get('feature') or '').strip()
        if not street: fail(f'{p}.street/feature required',errs)
        t=d.get('treatment')
        if t not in ALLOWED: fail(f'{p}.treatment invalid',errs)
        if d.get('road_binding_verified') is not True: fail(f'{p}.road_binding_verified must be true',errs)
        if d.get('result') not in ('pass','PASS',True): fail(f'{p}.result must pass',errs)
        if d.get('touches_any_road') is not False: fail(f'{p}.touches_any_road must be false',errs)
        if d.get('overlaps_any_road') is not False: fail(f'{p}.overlaps_any_road must be false',errs)
        if d.get('nearest_label_cluster_reviewed') is not True: fail(f'{p}.nearest_label_cluster_reviewed must be true',errs)
        if t in DIRECT:
            gap=d.get('assigned_road_gap_px')
            if not isinstance(gap,(int,float)) or gap<2 or gap>15: fail(f'{p}.assigned_road_gap_px must be 2..15',errs)
            if d.get('follows_road_geometry') is not True: fail(f'{p}.follows_road_geometry must be true',errs)
            if d.get('overhang_avoided') is not True: fail(f'{p}.overhang_avoided must be true',errs)
            if d.get('junction_bulb_crowding_avoided') is not True: fail(f'{p}.junction_bulb_crowding_avoided must be true',errs)
            if d.get('is_short_street') is True:
                u=d.get('usable_run_px'); ink=d.get('label_ink_px'); br=d.get('end_breathing_room_px')
                if not all(isinstance(x,(int,float)) for x in [u,ink,br]): fail(f'{p} short direct measurements required',errs)
                elif u < ink+30 or br < 15: fail(f'{p} short direct fit rule failed; use callout/detail',errs)
            else:
                br=d.get('end_breathing_room_px')
                if isinstance(br,(int,float)) and br<6 and not d.get('end_breathing_exception'):
                    fail(f'{p} ordinary direct end breathing <6 without exception',errs)
        if t in CALLOUT:
            calc_callouts+=1
            required=['same_road_direct_options_exhausted','nearest_practical_whitespace_used','leader_attached','target_street_verified','callout_closeup_inspected']
            for k in required:
                if d.get(k) is not True: fail(f'{p}.{k} must be true',errs)
            gap=d.get('leader_tail_gap_px')
            if not isinstance(gap,(int,float)) or not (0 <= gap <= 2): fail(f'{p}.leader_tail_gap_px must be 0..2',errs)
            ll=d.get('leader_length_px')
            if not isinstance(ll,(int,float)): fail(f'{p}.leader_length_px required',errs)
            elif ll>110 and not d.get('user_approved_long_routing'): fail(f'{p} leader >110 without explicit approval',errs)
            elif ll>80 and not d.get('no_closer_clean_placement_justification'): fail(f'{p} leader >80 needs no-closer-placement justification',errs)
            if d.get('leader_word_crossings',0)!=0: fail(f'{p}.leader_word_crossings must 0',errs)
            if d.get('leader_unrelated_road_crossings',0)!=0: fail(f'{p}.leader_unrelated_road_crossings must 0',errs)
            if d.get('culdesac_has_stem') is True and d.get('target_stem_verified') is not True: fail(f'{p}.target_stem_verified required',errs)
    if r.get('callout_count')!=calc_callouts: fail('callout_count must equal callout decisions',errs)
    if r.get('leaders_reviewed_count')!=calc_callouts: fail('leaders_reviewed_count must equal callout_count',errs)

    # R50: the per-label ledger cannot pass while the full rendered-road inventory/contact/clutter gate is absent.
    c=validate_completeness(path)
    if not c.get('passed'):
        errs.extend([f'R50 completeness: {e}' for e in c.get('errors',[])])
    comp=data.get('label_completeness_review') or {}
    required_names={str(x.get('name','')).strip().lower() for x in comp.get('records',[]) if isinstance(x,dict) and x.get('name_status')=='named_public'}
    decision_names={str((x.get('street') or x.get('feature') or '')).strip().lower() for x in dec if isinstance(x,dict)}
    missing=sorted(n for n in required_names if n and n not in decision_names)
    if missing: errs.append('named_public roads missing from label decision ledger: '+', '.join(missing))
    return {'passed':not errs,'errors':errs,'label_count':len(dec),'callout_count':calc_callouts}

if __name__=='__main__':
    if len(sys.argv)!=2:
        print('usage: validate_label_placement_contract.py REVIEW.json',file=sys.stderr); sys.exit(2)
    res=main(sys.argv[1]); print(json.dumps(res,indent=2)); sys.exit(0 if res['passed'] else 1)