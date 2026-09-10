"""Additive raster-source contract prototype. Does not replace native topology gate.
Independent review and trusted recomputation are mandatory. Reports alone never pass.
"""
from pathlib import Path
import hashlib,json,math
LIMITS={'median_width_delta_px':1.25,'maximum_color_delta_rgb':18.,'edge_softness_delta_px':.85,'texture_delta':2.5,'unexpected_status_pixel_count':0,'centerline_p95_deviation_px':2.,'boundary_presence_mismatch_px':0}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate(report,review=None,recomputed=None):
 errors=[]
 def check(ok,msg):
  if not ok:errors.append(msg)
 def binding(value,label):
  try:check(digest(value['path'])==value['sha256'],label+' hash mismatch')
  except (OSError,KeyError,TypeError):errors.append(label+' binding missing/unreadable')
 check(report.get('schema_version')=='raster-topology-evidence-1','wrong schema')
 for k in ['artifact','original_assignment','coverage_source','prior_plan','source_plan_origin','expected_source_map','original_geometry_final_layout','expected_final']:binding(report.get(k),k)
 check(bool(report.get('source_inputs')),'source input bindings missing')
 for v in report.get('source_inputs',[]):binding(v,'source input')
 check(report.get('original_image_decoded_identity') is True,'source decoded pixels differ')
 check(report.get('original_visible_native_path_count')==0,'raster branch requires raster-only original street source')
 check(report.get('replayed_map_matches_actual_embedded_image') is True,'actual embedded map differs from replay')
 layer=report.get('style_layer',{})
 for k in ['actual','baseline']:binding(layer.get(k),'style layer '+k)
 check(layer.get('embedded_image_decoded_identity') is True,'style layer must match actual embedded map')
 check(layer.get('scale')==2,'style layer must use fixed 2x scale')
 check(len(layer.get('actual_pdf_image_rect',[]))==4,'actual map placement absent')
 rows=report.get('render_checks',[])
 check([r.get('scale')for r in rows]==[1,2,4],'all render scales required')
 for r in rows:
  check(r.get('expected_final_changed_pixels')==0,'expected final mismatch')
  check(r.get('changed_outside_declared_masks')==0,'changed pixels outside masks')
  check(r.get('mask_renderer_guard_2x_px')==1,'renderer guard changed')
 check(bool(report.get('results')),'operation list empty')
 ids=[]
 for r in report.get('results',[]):
  ids.append(r.get('id'))
  check(r.get('thresholds')==LIMITS,'thresholds altered')
  for k,v in LIMITS.items():
   m=r.get('style_metrics',{}).get(k)
   check(type(m) in (int,float) and math.isfinite(m) and 0<=m<=v,'style limit '+k)
  check(len(r.get('mask_final',[]))==4,'operation mask absent')
  check(bool(r.get('feature_ids')),'operation source geometry absent')
  for k in ['before','after']:binding(r.get('paired_4x',{}).get(k),'paired '+k)
 check(len(ids)==len(set(ids)),'duplicate operation identity')
 # Caller must supply output freshly recomputed by the trusted replay implementation.
 check(recomputed is not None and recomputed==report,'fresh recomputation required; edited report insufficient')
 if review is None:errors.append('independent review absent')
 else:
  check(review.get('reviewer_independent') is True,'independent reviewer required')
  check(review.get('decision')=='PASS','independent review not PASS')
  check(review.get('artifact_sha256')==report.get('artifact',{}).get('sha256'),'review artifact stale')
  report_digest=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  check(review.get('canonical_report_sha256')==report_digest,'review evidence stale')
  check(review.get('operation_ids')==ids,'review must cover exact operations')
  for k in ['prior_source_plan_provenance_verified','source_geometry_and_assignment_verified','same_status_references_representative','paired_4x_reviewed','expected_final_derivation_verified']:
   check(review.get(k) is True,'review missing '+k)
 return errors
if __name__=='__main__':
 import sys
 r=json.loads(Path(sys.argv[1]).read_text());print(json.dumps({'status':'FAIL','errors':validate(r)},indent=2))


def validate_raster_topology(block,pdf,masks,source_sha256):
 """Replay only independently approved, exact-hash local script; fail closed."""
 import subprocess,sys
 errors=[]
 def bound(k):
  v=block[k];p=Path(v['path'])
  if digest(p)!=v['sha256']:raise ValueError(k+' hash mismatch')
  return p
 try:
  rp=bound('report');review_path=bound('independent_review');script=bound('replay_script')
  before=json.loads(rp.read_text());review=json.loads(review_path.read_text())
  if before['artifact']['sha256']!=digest(pdf):raise ValueError('actual PDF hash mismatch')
  if before['coverage_source']['sha256']!=source_sha256:raise ValueError('actual source hash mismatch')
  if review.get('report_sha256')!=block['report']['sha256']:raise ValueError('review report hash mismatch')
  if review.get('replay_script_sha256')!=block['replay_script']['sha256']:raise ValueError('unapproved replay script')
  if review.get('source_plan_origin')!=before.get('source_plan_origin'):raise ValueError('plan origin not approved')
  if review.get('prior_plan')!=before.get('prior_plan'):raise ValueError('prior plan not approved')
  # Never execute a merely provided script until independent approval is verified.
  if review.get('reviewer_independent') is not True or review.get('decision')!='PASS':raise ValueError('independent approval absent')
  preflight=validate(before,review,before)
  if preflight:raise ValueError('preflight: '+'; '.join(preflight))
  prior=before.get('prior_plan',{})
  if 'path' in prior and digest(prior['path'])!=prior.get('sha256'):raise ValueError('prior plan hash mismatch')
  args=block.get('replay_args')
  if not isinstance(args,list) or not all(isinstance(x,str)for x in args):raise ValueError('explicit replay arguments required')
  if review.get('replay_args')!=args:raise ValueError('unapproved replay arguments')
  declared={}
  for m in masks:
   if m.get('edit_kind')=='raster_topology_addition':
    if m['id'] in declared:raise ValueError('duplicate mask ID')
    declared[m['id']]=[m['x'],m['y'],m['x']+m['width'],m['y']+m['height']]
  actual={r['id']:r['mask_final']for r in before['results']}
  if declared!=actual:raise ValueError('PROJECT masks differ from replay operation masks')
  subprocess.run([sys.executable,str(script),*args],check=True,capture_output=True,text=True,timeout=180)
  after=json.loads(rp.read_text())
  errors.extend(validate(before,review,after))
  if digest(pdf)!=before['artifact']['sha256']:errors.append('replay altered actual PDF')
 except (OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError) as exc:errors.append(str(exc))
 return errors
