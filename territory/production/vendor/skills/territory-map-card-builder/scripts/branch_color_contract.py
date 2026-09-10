"""Fail-closed reporting contract; source correctness still requires visual review."""
import re

def validate_branch_color_review(review, artifact_sha256):
    errors=[]
    def need(value,message):
        if not value:errors.append('branch_color_review: '+message)
    if not isinstance(review,dict):return ['branch_color_review: required whole-branch/status-paint evidence missing']
    need(review.get('artifact_sha256')==artifact_sha256,'artifact hash mismatch')
    need(bool(re.fullmatch(r'Territory - [0-9]{3}(?:[AT])?[a-z]*\.pdf',str(review.get('delivery_filename','')))),'delivery filename must follow Territory - 000Letters.pdf')
    for key in ['branch_inventory_complete','status_junction_inventory_complete']:
        need(review.get(key)is True,key+' must be true')
    need(bool(review.get('actual_size_screenshot')),'actual-size screenshot missing')
    need(isinstance(review.get('closeup_screenshots'),list)and bool(review['closeup_screenshots']),'close-up screenshots missing')
    for key in ['unresolved_branch_labels','mixed_status_defects']:
        need(review.get(key)==[],key+' must be an explicit empty list')
    branches=review.get('branches');need(isinstance(branches,list)and bool(branches),'branch inventory missing')
    seen=set()
    for row in branches if isinstance(branches,list)else[]:
        if not isinstance(row,dict):need(False,'invalid branch record');continue
        need(bool(row.get('id'))and row.get('id')not in seen,'branch ID missing/duplicate');seen.add(row.get('id'))
        for key in ['source_binding','name_or_descriptor','decision_evidence','visual_evidence']:need(bool(row.get(key)),'branch '+str(row.get('id'))+' lacks '+key)
        need(isinstance(row.get('label_ids'),list),'label_ids must be an explicit list')
        if not row.get('label_ids'):need(bool(row.get('omission_evidence')),'unlabeled branch needs specific omission evidence')
    junctions=review.get('status_junctions');need(isinstance(junctions,list),'status junction inventory missing')
    if junctions==[]:need(bool(review.get('no_status_junctions_evidence')),'empty junction inventory needs source evidence')
    for row in junctions if isinstance(junctions,list)else[]:
        if not isinstance(row,dict):need(False,'invalid status junction record');continue
        for key in ['id','source_binding','statuses','visual_evidence']:need(bool(row.get(key)),'junction lacks '+key)
        need(row.get('verdict')in ['clean_handoff','separated'],'junction has unresolved paint')
    return errors
