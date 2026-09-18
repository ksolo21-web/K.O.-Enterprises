#!/usr/bin/env python3
import argparse, hashlib, json, os, sys

def fail(msg):
    print('FAIL:', msg)
    raise SystemExit(1)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('review_json')
    ap.add_argument('--pdf')
    a=ap.parse_args()
    d=json.load(open(a.review_json,'r',encoding='utf-8'))
    p=d.get('source_truth_preflight')
    if not isinstance(p,dict): fail('missing source_truth_preflight')
    for k in ('assignment_sources','topology_sources','roads','precritic_family_review'):
        if k not in p: fail('missing '+k)
    if not p['assignment_sources']: fail('assignment_sources empty')
    if not p['topology_sources']: fail('topology_sources empty')
    if not p['roads']: fail('roads empty')
    checks={
      'invented_connections':0,
      'unresolved_omissions':0,
      'topology_conflicts':0,
      'boundary_box_used_as_geography':False,
      'endpoint_trace_complete':True,
      'all_worked_boundary_context_roads_inventoried':True,
      'unresolved_name_status':0,
    }
    for k,v in checks.items():
        if p.get(k)!=v: fail(f'{k} expected {v!r}, got {p.get(k)!r}')
    for i,r in enumerate(p['roads']):
        if not isinstance(r,dict): fail(f'roads[{i}] not object')
        for k in ('name','name_status','label_required','role','render_disposition','endpoints','connections','termination_type','source_evidence','result'):
            if k not in r: fail(f'roads[{i}] missing {k}')
        if r.get('name_status') not in ('named_public','named_private','unnamed','nonroad_feature'): fail(f'roads[{i}] invalid name_status')
        if r.get('name_status')=='named_public' and r.get('label_required') is not True: fail(f'roads[{i}] named_public must have label_required true')
        if r.get('name_status') in ('unnamed','nonroad_feature') and r.get('label_required') is not False: fail(f'roads[{i}] unnamed/nonroad must have label_required false')
        if r.get('name_status') in ('named_public','named_private') and not str(r.get('name','')).strip(): fail(f'roads[{i}] named road requires name')
        if r.get('result')!='pass': fail(f'roads[{i}] result not pass')
        if not r.get('source_evidence'): fail(f'roads[{i}] source_evidence empty')
    f=p['precritic_family_review']
    for k in ('actual_size_inspected','two_x_inspected','four_x_map_inspected','map_drawing_match_passed'):
        if f.get(k) is not True: fail(f'precritic_family_review.{k} must be true')
    if f.get('obvious_family_mismatch_count')!=0: fail('obvious_family_mismatch_count must be 0')
    if f.get('residential_neighborhood_redraw') is True and f.get('territory_273_side_by_side') is not True:
        fail('Territory 273 side-by-side required for residential/neighborhood redraw')
    if a.pdf:
        h=hashlib.sha256(open(a.pdf,'rb').read()).hexdigest()
        if p.get('artifact_sha256')!=h: fail('artifact_sha256 does not match PDF')
    c=d.get('critic_source_truth_review')
    if c is not None:
        required_true=('raw_sources_reopened','independent_topology_reconstruction_completed')
        for k in required_true:
            if c.get(k) is not True: fail(f'critic_source_truth_review.{k} must be true')
        if c.get('builder_topology_ledger_used_as_proof') is not False: fail('critic may not use builder topology ledger as proof')
        if c.get('prior_score_used_as_proof') is not False: fail('critic may not use prior score as proof')
        for k in ('invented_connections_found','unresolved_omissions_found','source_conflicts_unresolved'):
            if c.get(k)!=0: fail(f'critic_source_truth_review.{k} must be 0')
        if not c.get('roads_reviewed'): fail('critic_source_truth_review.roads_reviewed empty')
    print('PASS: R50 source-truth/name preflight evidence structure')

if __name__=='__main__': main()