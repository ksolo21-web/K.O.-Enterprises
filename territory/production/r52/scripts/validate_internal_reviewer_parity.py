#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
from territory_identity import derive
from validate_label_completeness_preflight import main as validate_label_completeness
from validate_pdf_label_metrics import main as validate_pdf_label_metrics
from validate_label_navigation_contract import main as validate_label_navigation
HEX64=re.compile(r'^[0-9a-fA-F]{64}$')
REQ_TRUE=[
 'candidate_frozen_before_review','fresh_capture_generated','actual_size_inspected','full_page_2x_inspected',
 'overlapping_4x_full_coverage_inspected','targeted_closeups_inspected','same_critic_contract_applied',
 'same_hard_vetoes_applied','same_score_floor_applied','same_report_schema_applied','whole_card_rechecked_after_repairs',
 'independent_label_reinventory_completed','label_contact_visual_review_completed','label_cluster_visual_review_completed','independent_label_metric_remeasurement_completed','final_pdf_delivery_verified'
]
REQ_FALSE=['critic_independent','reviewer_edited_during_review','builder_claimed_score_used_as_evidence','builder_label_ledger_used_as_proof','prior_label_score_used_as_proof','builder_label_metrics_used_as_proof']
REQ_CATS=['preservation','geography','labels','template','export']
REQ_PARTS=['direct_curved_label_placement','callout_leader_system','branch_completeness','clutter_whitespace_balance','map_balance_and_context','family_resemblance']
REQ_OBJECTS=[
 'label_clutter_review','new_design_visual_review','label_glyph_review','housing_instruction_review','coverage_review',
 'current_inventory_review','major_crossroad_review','card_content_review','navigation_presentation_review','branch_color_review',
 'duplicate_coverage_review','card_family_review','label_placement_decision_review','territory_identity_review',
 'source_truth_preflight','critic_source_truth_review','label_completeness_review','label_contact_cluster_review','critic_label_audit','delivery_format_review','label_metric_review','critic_label_metric_review'
]

def main(path):
 data=json.loads(Path(path).read_text(encoding='utf-8'))
 p=data.get('reviewer_parity_review'); errs=[]
 if not isinstance(p,dict): return {'passed':False,'errors':['missing reviewer_parity_review']}
 if p.get('contract_revision')!='R52': errs.append('contract_revision must be R52')
 if p.get('reviewer_type')!='authorized_internal': errs.append('reviewer_type must be authorized_internal')
 for k in REQ_TRUE:
  if p.get(k) is not True: errs.append(f'{k} must be true')
 for k in REQ_FALSE:
  if p.get(k) is not False: errs.append(f'{k} must be false')
 sha=str(p.get('artifact_sha256',''))
 if not HEX64.fullmatch(sha): errs.append('artifact_sha256 must be 64 hex')
 if data.get('artifact_sha256') and data.get('artifact_sha256')!=sha: errs.append('artifact hash mismatch between report and parity record')
 if not str(p.get('active_skill_revision','')).strip(): errs.append('active_skill_revision required')
 ss=p.get('screenshots_inspected')
 if not isinstance(ss,list) or len(ss)<3: errs.append('screenshots_inspected must list actual evidence')
 else:
  low=[str(x).lower() for x in ss]
  if not any('1x' in x or 'actual' in x for x in low): errs.append('missing actual/1x screenshot evidence')
  if not any('2x' in x for x in low): errs.append('missing 2x screenshot evidence')
  if not any('4x' in x or 'region' in x for x in low): errs.append('missing 4x regional screenshot evidence')
 cats=data.get('categories'); scores=[]
 if not isinstance(cats,dict): errs.append('categories object required')
 else:
  for c in REQ_CATS:
   x=cats.get(c)
   if not isinstance(x,dict) or not isinstance(x.get('score'),(int,float)): errs.append(f'category {c} score required')
   else:
    scores.append(float(x['score']))
    if x['score']<=9.0: errs.append(f'category {c} must be strictly >9.0')
 for k in REQ_OBJECTS:
  if not isinstance(data.get(k),dict): errs.append(f'{k} object required for reviewer parity')

 # Exact identity still required.
 ir=data.get('territory_identity_review')
 if isinstance(ir,dict):
  if str(ir.get('artifact_sha256','')) != sha: errs.append('territory_identity_review artifact_sha256 must match exact review artifact')
  ci=ir.get('card_identity')
  if not isinstance(ci,dict): errs.append('territory_identity_review.card_identity required')
  else:
   try:
    exp=derive(ci.get('base_number'),ci.get('card_class',''),ci.get('suffix',''))
    for kk in ('base_number','card_class','suffix','display_id','canonical_filename'):
     if ci.get(kk)!=exp.get(kk): errs.append(f'territory_identity_review.card_identity.{kk} mismatch')
   except Exception as e: errs.append(f'territory_identity_review invalid identity: {e}')
   if ci.get('identity_status')!='verified': errs.append('territory_identity_review production identity_status must be verified')
  if not str(ir.get('source_master_label','')).strip(): errs.append('territory_identity_review.source_master_label required')
  for kk in ['derived_display_id_match','derived_filename_match','visible_identity_match','extracted_text_identity_match','pdf_metadata_identity_match','source_alias_not_rendered_as_card_identity','actual_filename_match','identity_validator_passed','pdf_identity_validator_passed']:
   if ir.get(kk) is not True: errs.append(f'territory_identity_review.{kk} must be true')
  if ir.get('hidden_stale_identity_count')!=0: errs.append('territory_identity_review.hidden_stale_identity_count must be 0')
  ev=ir.get('evidence')
  if not isinstance(ev,list) or len(ev)<3: errs.append('territory_identity_review.evidence must list exact PDF and both validator reports')

 # R49 geography anti-anchoring is now parity-enforced.
 cs=data.get('critic_source_truth_review')
 if isinstance(cs,dict):
  for kk in ['raw_sources_reopened','independent_topology_reconstruction_completed']:
   if cs.get(kk) is not True: errs.append(f'critic_source_truth_review.{kk} must be true')
  if cs.get('builder_topology_ledger_used_as_proof') is not False: errs.append('critic_source_truth_review.builder_topology_ledger_used_as_proof must be false')
  if cs.get('prior_score_used_as_proof') is not False: errs.append('critic_source_truth_review.prior_score_used_as_proof must be false')
  for kk in ['invented_connections_found','unresolved_omissions_found','source_conflicts_unresolved']:
   if cs.get(kk)!=0: errs.append(f'critic_source_truth_review.{kk} must be 0')

 # R50 full rendered-road label completeness/contact/clutter gate.
 lc=validate_label_completeness(path)
 if not lc.get('passed'):
  errs.extend([f'R50 label completeness: {e}' for e in lc.get('errors',[])])
 ca=data.get('critic_label_audit')
 if isinstance(ca,dict):
  for kk in ['raw_name_topology_sources_reopened','independent_visible_road_reinventory_completed','independent_label_reinventory_completed','all_callouts_closeup_inspected','all_cluster_triggers_inspected']:
   if ca.get(kk) is not True: errs.append(f'critic_label_audit.{kk} must be true')
  if ca.get('builder_label_ledger_used_as_proof') is not False: errs.append('critic_label_audit.builder_label_ledger_used_as_proof must be false')
  if ca.get('prior_label_score_used_as_proof') is not False: errs.append('critic_label_audit.prior_label_score_used_as_proof must be false')
  if ca.get('generated_raster_treated_as_final') is not False: errs.append('critic_label_audit.generated_raster_treated_as_final must be false')
  zero=['unaccounted_visible_road_count','unlabeled_required_road_count','unsupported_unlabeled_count','wrong_or_duplicate_road_label_count','label_road_touch_count','label_road_overlap_count','label_label_overlap_count','avoidable_label_cluster_count','detached_leader_count','wrong_callout_target_count','premature_callout_count']
  for kk in zero:
   if ca.get(kk)!=0: errs.append(f'critic_label_audit.{kk} must be 0')
  comp=data.get('label_completeness_review') or {}
  if ca.get('visible_road_feature_count')!=comp.get('visible_road_feature_count'): errs.append('critic_label_audit.visible_road_feature_count must independently reconcile to rendered road inventory')
  if ca.get('named_public_visible_count')!=comp.get('named_public_visible_count'): errs.append('critic_label_audit.named_public_visible_count must reconcile')
  if ca.get('required_label_count')!=comp.get('named_public_visible_count'): errs.append('critic_label_audit.required_label_count must equal named_public_visible_count')
  if ca.get('residential_neighborhood_map') is True and ca.get('territory_273_label_system_side_by_side') is not True:
   errs.append('critic_label_audit.territory_273_label_system_side_by_side required for residential/neighborhood map')
  ev=ca.get('evidence')
  if not isinstance(ev,list) or len(ev)<3: errs.append('critic_label_audit.evidence must include actual-size and closeup evidence')

 # R52 adds exact segment/role and complete label/font review; all prior gates remain.
 nr=validate_label_navigation(path)
 if not nr.get('passed'):
  errs.extend([f'R52 navigation: {e}' for e in nr.get('errors',[])])
 if (data.get('label_navigation_review') or {}).get('scope')!='whole_card':
  errs.append('bounded component evidence cannot certify full-card release')

 # R51 exact-PDF delivery and label metrics gate.
 mr=validate_pdf_label_metrics(path,None)
 if not mr.get('passed'):
  errs.extend([f'R51 metric: {e}' for e in mr.get('errors',[])])
 clm=data.get('critic_label_metric_review')
 if isinstance(clm,dict):
  for kk in ['independent_remeasurement_completed','reference_sample_remeasured','disputed_labels_remeasured','repeat_label_groups_rechecked','final_pdf_delivery_verified']:
   if clm.get(kk) is not True: errs.append(f'critic_label_metric_review.{kk} must be true')
  if clm.get('builder_metrics_used_as_proof') is not False: errs.append('critic_label_metric_review.builder_metrics_used_as_proof must be false')
  if clm.get('outlier_label_count')!=0: errs.append('critic_label_metric_review.outlier_label_count must be 0')

 nd=data.get('new_design_visual_review')
 if isinstance(nd,dict):
  parts=nd.get('part_scores')
  if not isinstance(parts,dict): errs.append('new_design_visual_review.part_scores required')
  else:
   for k in REQ_PARTS:
    v=parts.get(k)
    if not isinstance(v,(int,float)): errs.append(f'visual part score {k} required')
    else:
     scores.append(float(v))
     if v<=9.0: errs.append(f'visual part {k} must be strictly >9.0')
   ed=nd.get('enlarged_detail_review')
   if isinstance(ed,dict) and ed.get('used') is True:
    v=parts.get('enlarged_detail_quality')
    if not isinstance(v,(int,float)) or v<=9.0: errs.append('enlarged_detail_quality must be strictly >9.0 when detail used')
 if data.get('blockers') not in ([],None): errs.append('blockers must be empty for pass')
 if data.get('unverified') not in ([],None): errs.append('unverified must be empty for pass')
 overall=data.get('overall_score')
 if not isinstance(overall,(int,float)) or overall<=9.0: errs.append('overall_score must be strictly >9.0')
 elif scores and abs(float(overall)-min(scores))>1e-9: errs.append('overall_score must equal lowest applicable category/part score in fixture/report')
 stage=data.get('review_stage')
 if stage not in ('candidate','final_saved'): errs.append('review_stage must be candidate or final_saved')
 if stage=='final_saved' and not isinstance(data.get('delivery_identity_review'),dict): errs.append('delivery_identity_review required for final_saved review')
 if data.get('release_ready') is not True: errs.append('release_ready must be true for a passing parity report')
 return {'passed':not errs,'errors':errs}

if __name__=='__main__':
 if len(sys.argv)!=2: print('usage: validate_internal_reviewer_parity.py REVIEW.json',file=sys.stderr); sys.exit(2)
 r=main(sys.argv[1]); print(json.dumps(r,indent=2)); sys.exit(0 if r['passed'] else 1)