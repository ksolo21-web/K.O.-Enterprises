"""Uninstalled saved branch. Fixed independent approval required; fail closed."""
from pathlib import Path
import hashlib, json, importlib.util, tempfile
ROOT=Path('/workspace/scratch/9e6ec3f4f96f/territory-batch-12/gate-learning/61AB-unchanged-paint-proposal')
WORKING=ROOT/'activated-working/native_unchanged_width_contract.py'
WORKING_SHA='08a1268e75c7d2db26905e86df1caf03dda6226ea1ff7ebc37fa1cde4aac463e'
DELIVERY=Path('/root/.codex/skills/remote-skills/skill-6a9c3cf205788191980b577497433361/scripts/delivery_wrapper.py')
DELIVERY_SHA='f662e4ee34fc6eb5832794544729979089ff764fedf5a3f56acbe88f4e74722a'
APPROVAL=ROOT/'independent-saved-branch-approval.json'
APPROVAL_SHA='d7727dfece9406e07a7ef61252b870b1a51d5e4825433f30dbc825ed506d5b92'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def load(path,digest,name):
 require(sha(path)==digest,'Verifier code changed: '+name)
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def bound(ref):
 require(isinstance(ref,dict)and set(ref)=={'path','sha256'},'Exact immutable reference required')
 p=Path(ref['path']);require(sha(p)==ref['sha256'],'Immutable reference mismatch');return p

def validate_saved(wrapper,pdf,preservation=None,critic_manifest=None):
 try:
  require(APPROVAL_SHA!='NOT_ACTIVATED','Saved branch not independently activated')
  require(sha(APPROVAL)==APPROVAL_SHA,'Fixed saved approval hash mismatch')
  a=json.load(open(APPROVAL));require(a.get('status')=='APPROVED_SAVED_BRANCH'and a.get('independent')is True,'Saved approval invalid')
  require(isinstance(wrapper,dict)and set(wrapper)=={'contract_path','contract_sha256'},'Only bound saved contract allowed')
  cp=bound({'path':wrapper['contract_path'],'sha256':wrapper['contract_sha256']})
  require(sha(cp)==a['saved_contract_sha256'],'Saved contract not approved')
  c=json.load(open(cp));require(c['schema_version']=='61AB-strict-saved-delivery-v1','Unknown saved schema')
  require(c['saved_sha256']==sha(pdf)==a['saved_sha256'],'Actual saved identity mismatch')
  op=bound(c['working_operation']);wc=bound(c['working_contract']);wr=bound(c['working_review']);wg=bound(c['working_complete_gates'])
  for key in ('working_operation','working_contract','working_review','working_complete_gates'):
   require(c[key]['sha256']==a[key+'_sha256'],'Working authority not independently approved: '+key)
  working=load(WORKING,WORKING_SHA,'working_61ab')
  # The frozen working module is already activated; never override its authority.
  require(working.APPROVAL_SHA==a['working_activation_sha256']and sha(working.APPROVAL)==working.APPROVAL_SHA,'Working activation mismatch')
  errors,checks=working.validate_native_unchanged_width({'contract_path':str(wc),'contract_sha256':sha(wc)},op,preservation=preservation)
  require(not errors,'Working replay failed: '+repr(errors))
  review=json.load(open(wr));gates=json.load(open(wg))
  require(review['artifact_sha256']==sha(op)and review['release_ready']is True,'Immutable working review incomplete')
  require(gates['artifact_sha256']==sha(op)and gates['all_required_gates_passed']is True,'Immutable working gates incomplete')
  delivery=load(DELIVERY,DELIVERY_SHA,'strict_delivery_61ab').verify_delivery(op,pdf)
  require(delivery['operation_sha256']==sha(op)and delivery['delivery_sha256']==sha(pdf)and delivery['kind']in ('identical_bytes','strict_c2pa_incremental'),'Delivery identity mismatch')
  vp=bound(c['saved_visual_receipt']);require(sha(vp)==a['saved_visual_receipt_sha256'],'Saved visual receipt unapproved')
  receipt=json.load(open(vp));old=json.load(open(json.load(open(wc))['independent_visual_receipt_path']))
  require(not {str(Path(x['path']).resolve())for x in old['captures']}&{str(Path(x['path']).resolve())for x in receipt['captures']},'Saved captures must be freshly separate')
  primitive=load(working.PRIMITIVE,working.PRIMITIVE_SHA,'saved_operation_replay')
  with tempfile.TemporaryDirectory()as td:
   r=primitive.evaluate(op,sha(op),td);require(r['status']=='PROPOSED_BOUNDED_BRANCH_PASS','Immutable operation replay failed')
   visual=working.verify_prescribed_visual(receipt,pdf,Path(td)/'independently-replayed-expected.pdf',{'approved_visual_reviewer':a['saved_visual_reviewer']})
  if critic_manifest is not None:require(critic_manifest['artifact_sha256']==sha(pdf),'Saved manifest mismatch')
  return [],checks,{'delivery':delivery,'saved_visual':visual,'working_operation_sha256':sha(op),'working_contract_sha256':sha(wc),'working_review_sha256':sha(wr),'release_approval':False}
 except Exception as e:return ['saved_native_unchanged_width: '+str(e)],[],{}
