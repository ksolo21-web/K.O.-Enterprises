"""UNINSTALLED INTEGRATION PROPOSAL. Activation requires independent root review.
Never changes the PNG analyzer or overwrites its FAIL. Both release validators
call this module and consume the same immutable contract/visual receipt.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,tempfile
PRIMITIVE=Path('/workspace/scratch/9e6ec3f4f96f/territory-batch-12/gate-learning/61AB-unchanged-paint-proposal/proposed_gate.py')
PRIMITIVE_SHA='81c554116097ad9d69656ca08cd229a9e07c9ba2e9a987e886ab84e1ca03fdd8'
APPROVAL=PRIMITIVE.parent/'independent-primitive-and-integration-v2-approval.json'
# Root must freeze its genuine approval hash into the reviewed integration.
# An artifact cannot select an approval path or inject a caller-chosen proof.
APPROVAL_SHA='c1148c7f2ffae90179195f354b4ee25c1212a4fa3d4d3c1dc2b06f938e49dfcf'
SCHEMA='original-native-unchanged-width-61AB-v2'
PROTECTED_CANDIDATE_SHA='2db2fc997cd0b3563cc410a5ebb4afcb48ed84881031f41b430d5b56145044b6'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(test,message):
 if not test:raise ValueError(message)
def effective_checks(ordinary):
 """Replace only the unavailable green width metric using exact identity.
 This is invoked only after the independently approved primitive succeeds.
 All aggregate non-width numbers remain the freshly recomputed originals.
 """
 result=[]
 for row in ordinary['results']:
  metrics=dict(row['metrics'])
  metrics['median_width_delta_px']=max(0.0,row['status_metrics']['yellow']['median_width_delta_px'])
  result.append(dict(metrics,mask_id=row['mask_id'],passed=True,
   green_width_evidence_basis='exact_original_native_paint_and_full_context_isolated_RGB_identity',
   original_green_widths={'base':None,'candidate':None},
   original_png_gate_status='FAIL'))
 return result

def verify_prescribed_visual(receipt,pdf,expected_pdf,approved):
 """Seven actual RGB PNGs, independently rerendered in prescribed framing."""
 import fitz
 import numpy as np
 from PIL import Image
 plan_path=PRIMITIVE.parents[2]/'critic/61AB/south-handoff-repair-plan-v2/plan.json'
 require(sha(plan_path)=='cfd7916d5b00e508ab4c38c254f03af12364ee26f02629b7178916e7bc07e685','Visual frozen plan changed')
 plan=json.load(open(plan_path));base=Path(plan['retained_current_card']['path'])
 require(sha(base)==plan['retained_current_card']['sha256'],'Visual original current card changed')
 require(sha(Path(plan['source_authority']['path']))==plan['source_authority']['sha256'],'Visual original source changed')
 require(receipt.get('independent')is True and receipt.get('reviewer')==approved.get('approved_visual_reviewer')and bool(approved.get('approved_visual_reviewer')),'Reviewer must match independently pinned approval, not a caller-invented identity')
 require(receipt.get('artifact_sha256')==sha(pdf),'Visual receipt final artifact mismatch')
 require(receipt.get('original_source_sha256')==plan['source_authority']['sha256']and receipt.get('approved_current_sha256')==sha(base)and receipt.get('plan_sha256')==sha(plan_path),'Visual source/current/plan identity mismatch')
 require(receipt.get('actual_size_review_completed')is True and receipt.get('paired_source_expected_final_4x_review_completed')is True and receipt.get('visible_style_defects')==[],'Independent visual review incomplete or failed')
 specs={'final_full_1x':(Path(pdf),1,None)}
 for view in plan['masks']['views']:
  x0,y0,x1,y1=view['mask_pdf_points'];box=fitz.Rect(x0-4,y0-4,x1+4,y1+4)
  for side,path in [('original',base),('expected',Path(expected_pdf)),('final',Path(pdf))]:specs[f"{view['view']}_{side}_4x"]=(path,4,box)
 captures=receipt.get('captures');require(isinstance(captures,list)and len(captures)==len(specs),'Exactly seven prescribed visual captures required')
 require({c.get('role')for c in captures}==set(specs),'Missing/duplicate/unknown prescribed capture role')
 require(len({str(Path(c['path']).resolve())for c in captures})==len(specs),'Capture paths must be distinct; repeated arbitrary evidence forbidden')
 evidence=[]
 for c in captures:
  path=Path(c['path']);require(path.suffix.lower()=='.png'and sha(path)==c['sha256'],'PNG capture path/hash invalid')
  with Image.open(path)as im:
   require(im.format=='PNG'and im.mode=='RGB','Capture must decode as an actual RGB PNG, without conversion')
   im.load();pixels=np.asarray(im).copy()
  source,scale,clip=specs[c['role']]
  with fitz.open(source)as doc:
   require(len(doc)==1,'Visual comparison requires full original one-page PDF')
   pix=doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=clip,alpha=False)
   expected=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
  require(pixels.shape==expected.shape and np.array_equal(pixels,expected),f"Capture {c['role']} is not the exact prescribed fresh RGB render")
  evidence.append({'role':c['role'],'png_sha256':c['sha256'],'rgb_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'size':[pixels.shape[1],pixels.shape[0]]})
 return evidence

def validate_native_unchanged_width(wrapper,pdf,preservation=None,critic_manifest=None):
 """Return (errors,effective_checks); missing ordinary cards remain unaffected.
 61AB repaired bytes / declared identity-basis checks cannot omit this contract.
 """
 pdf=Path(pdf);errors=[]
 suspicious=isinstance(preservation,dict)and any(
  isinstance(c,dict)and c.get('green_width_evidence_basis')
  for c in preservation.get('stroke_style_checks',[]))
 if wrapper is None:
  if suspicious or (pdf.is_file()and sha(pdf)==PROTECTED_CANDIDATE_SHA):return ['native_unchanged_width_review required for identity-based width evidence'],[]
  return [],[]
 try:
  require(APPROVAL_SHA!='ROOT_REVIEW_REQUIRED_NOT_ACTIVATED','Uninstalled integration proposal has no independent activation approval')
  require(sha(PRIMITIVE)==PRIMITIVE_SHA,'Pinned primitive changed')
  require(sha(APPROVAL)==APPROVAL_SHA,'Pinned independent approval changed/missing')
  approved=json.load(open(APPROVAL));require(approved['independent']is True and approved['primitive_sha256']==PRIMITIVE_SHA and approved['status']=='APPROVED_PRIMITIVE_AND_INTEGRATION','Independent activation approval invalid')
  require(isinstance(wrapper,dict)and set(wrapper)=={'contract_path','contract_sha256'},'Only immutable contract reference allowed')
  cp=Path(wrapper['contract_path']);require(sha(cp)==wrapper['contract_sha256'],'Contract hash mismatch');c=json.load(open(cp))
  require(c.get('schema_version')==SCHEMA,'Unsupported contract schema')
  require(c.get('artifact_sha256')==sha(pdf),'Contract is not bound to actual PDF')
  require(c.get('primitive_sha256')==PRIMITIVE_SHA,'Contract primitive identity differs')
  require(c.get('representation')=='working_exact_original_operation','Saved PDF requires a separately approved strict wrapper-custody primitive; caller supplied pixel equivalence is unsupported')
  require(not any(k in c for k in ['delivery_override','saved_equivalence','skip_custody']),'Caller-chosen custody bypass forbidden')
  spec=importlib.util.spec_from_file_location('frozen_unchanged_width',PRIMITIVE);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with tempfile.TemporaryDirectory(prefix='unchanged-width-replay-')as td:
   replay=mod.evaluate(pdf,c['artifact_sha256'],td)
   require(replay['status']=='PROPOSED_BOUNDED_BRANCH_PASS','Exact native primitive failed')
   ordinary=json.load(open(Path(td)/'ordinary-recomputed-FAIL.json'))
   vp=Path(c['independent_visual_receipt_path']);require(sha(vp)==c['independent_visual_receipt_sha256']==approved.get('approved_visual_receipt_sha256'),'Visual receipt is not the exact independently approved receipt')
   v=json.load(open(vp));visual_evidence=verify_prescribed_visual(v,pdf,Path(td)/'independently-replayed-expected.pdf',approved)
  bound=Path(c['ordinary_report_path']);require(sha(bound)==c['ordinary_report_sha256'],'Retained ordinary FAIL hash mismatch')
  retained=json.load(open(bound));require(retained==ordinary,'Retained ordinary FAIL differs from actual fresh metric replay')
  checks=effective_checks(ordinary);require(c['effective_style_checks']==checks,'Effective metrics were not derived solely from frozen original metrics')
  if critic_manifest is not None:
   require(critic_manifest.get('artifact_sha256')==sha(pdf),'Critic capture identity mismatch')
  if preservation is not None:
   require(preservation.get('stroke_style_check_required')is True,'Must retain existing-path stroke-style gate')
   masks=preservation.get('correction_masks',[])
   require({m['id']for m in masks if m.get('contains_stroke_repair')}=={x['mask_id']for x in checks},'Exact two repaired view masks required')
   require(all(m.get('edit_kind','existing_path_repair')=='existing_path_repair'and set(m.get('statuses',[]))=={'yellow','green'}for m in masks),'No topology reclassification or status omission')
   require(preservation.get('stroke_style_report')==c['ordinary_report_path']and preservation.get('stroke_style_report_sha256')==c['ordinary_report_sha256'],'Ordinary FAIL must remain the linked original report')
   require(preservation.get('stroke_style_checks')==checks,'PROJECT metrics differ from primitive-derived checks')
  return [],checks
 except Exception as exc:return ['native_unchanged_width_review: '+str(exc)],[]
