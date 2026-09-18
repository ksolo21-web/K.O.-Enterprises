#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
REQ={
 'Territory-Map-Card-Builder-SKILL.md':['R51 Measured label baseline + PDF-only release','same-card label-gap baseline','final user deliverable is the canonical PDF'],
 'Territory-Card-Critic-SKILL.md':['R51 Independent label-metric + PDF-delivery review','validate_pdf_label_metrics.py','primary user deliverable is an image'],
 'Kaleb-Quality-Loop-SKILL.md':['Territory R51 PDF-delivery / measured-label override'],
 'Territory-Automatic-Execution-Contract.md':['R51 automatic PDF + metric stage','PDF DELIVERY/METRIC PREFLIGHT'],
 'New-Designed-Card-Family-Contract.md':['R51 Measured placement consistency and navigation repeats'],
 'New-Designed-Visual-Regression-Standard.md':['R51 road-gap consistency / PDF-output regression'],
 'Territory-Label-Completeness-Preflight-Contract.md':['R51 measured-gap / repeat-count / PDF-delivery extension'],
 'Territory-PDF-Label-Metric-Contract.md':['PDF is the only release artifact','Measured road-gap baseline','Navigation repeats on long/complex roads']
}
HASH_KEYS={
 'internal_reviewer_parity_validator_sha256':'validate_internal_reviewer_parity.py',
 'label_contract_validator_sha256':'validate_label_placement_contract.py',
 'label_completeness_validator_sha256':'validate_label_completeness_preflight.py',
 'label_metric_validator_sha256':'validate_pdf_label_metrics.py',
 'label_metric_contract_sha256':'Territory-PDF-Label-Metric-Contract.md',
 'source_truth_preflight_validator_sha256':'validate_source_truth_preflight.py',
 'renderer_sha256':'render_locked_template.py',
 'strict_style_validator_sha256':'validate_style_token_layer.py',
 'style_token_sha256':'R48-Canonical-Style-Tokens.json'
}
REQ['Territory-Segment-Role-Whole-Label-Contract.md']=['Lock each label','Inspect the entire label','actual font metrics','validate_label_navigation_contract.py']
for rel in ['Territory-Map-Card-Builder-SKILL.md','Territory-Card-Critic-SKILL.md','Kaleb-Quality-Loop-SKILL.md','Territory-Automatic-Execution-Contract.md','New-Designed-Card-Family-Contract.md','New-Designed-Visual-Regression-Standard.md','Territory-Label-Completeness-Preflight-Contract.md','Territory-PDF-Label-Metric-Contract.md']:
 REQ[rel].append('R52')
HASH_KEYS['label_navigation_validator_sha256']='validate_label_navigation_contract.py'
HASH_KEYS['label_navigation_contract_sha256']='Territory-Segment-Role-Whole-Label-Contract.md'
HASH_KEYS['activation_validator_sha256']='validate_territory_activation.py'
def resolve(root, rel):
 for folder in ['', 'scripts', 'references', 'assets']:
  path=root/folder/rel
  if path.is_file(): return path
 return root/rel

def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(root):
 root=Path(root); e=[]
 for rel,marks in REQ.items():
  p=resolve(root,rel)
  if not p.exists(): e.append(f'missing {rel}'); continue
  t=p.read_text(encoding='utf-8',errors='replace')
  for m in marks:
   if m not in t: e.append(f'{rel} missing marker: {m}')
 for rel in ['validate_internal_reviewer_parity.py','validate_label_placement_contract.py','validate_label_completeness_preflight.py','validate_pdf_label_metrics.py','validate_source_truth_preflight.py','validate_territory_activation.py']:
  if not resolve(root,rel).exists(): e.append(f'missing {rel}')
 ap=root/'ACTIVE-SKILLS.json'
 if not ap.exists(): return {'passed':False,'errors':e+['missing ACTIVE-SKILLS.json']}
 a=json.loads(ap.read_text(encoding='utf-8'))
 if a.get('revision')!='segment-role-whole-label-2026-09-13-r52': e.append('ACTIVE-SKILLS revision must be R52')
 if a.get('acceptance_test')!='/Skills/Territory Cards/R52-FINAL-ACCEPTANCE.json': e.append('acceptance_test must point R52')
 if a.get('package')!='/Skills/Territory Cards/Kaleb-Territory-Skills-Segment-Role-Whole-Label-2026-09-13-r52.zip': e.append('package must point R52')
 if a.get('final_territory_release_format')!='pdf_only': e.append('final_territory_release_format must be pdf_only')
 if a.get('image_preview_release_authority') is not False: e.append('image_preview_release_authority must be false')
 if a.get('same_card_label_gap_baseline_required') is not True: e.append('same_card_label_gap_baseline_required must be true')
 if a.get('navigation_repeat_label_count_enforced') is not True: e.append('navigation_repeat_label_count_enforced must be true')
 if a.get('mandatory_internal_reviewer') is not True: e.append('mandatory_internal_reviewer must be true')
 if a.get('automatic_territory_execution') is not True: e.append('automatic_territory_execution must be true')
 for flag in ['exact_segment_role_binding_required','whole_label_suffix_review_required','native_font_spacing_visual_review_required']:
  if a.get(flag) is not True: e.append(flag+' must be true')
 if a.get('score_operator')!='>' or a.get('default_minimum')!=9.0 or a.get('target')!=10 or a.get('all_mandatory_checks_required') is not True:
  e.append('original strict score/all-gates policy must be preserved')
 for k,rel in HASH_KEYS.items():
  if resolve(root,rel).exists() and a.get(k)!=h(resolve(root,rel)): e.append(f'{k} hash mismatch')
 return {'passed':not e,'errors':e}
if __name__=='__main__':
 r=main(sys.argv[1] if len(sys.argv)>1 else '.'); print(json.dumps(r,indent=2)); sys.exit(0 if r['passed'] else 1)