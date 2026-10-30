"""Reproducible synthetic specialist-workflow demonstration (never actual inspection)."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
from inspection_engine.core import sha256, blockers
from inspection_engine.video_photos import verify_selected_photo_pixels
from inspection_engine.capture import probe_video, video_frames
from inspection_engine.agents import execute_specialists, plan_specialists
from inspection_engine.report import build_pdf

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'examples'/'v05_photo_from_video'
OUT=ROOT/'output'/'m2_specialist_demo'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for existing in list(OUT.iterdir()):
        if existing.is_file(): existing.unlink()
        elif existing.is_dir():shutil.rmtree(existing)
    shutil.copyfile(SRC/'demo_exterior.png',OUT/'house_synthetic.png')
    shutil.copyfile(SRC/'synthetic_moving_house_view.mp4',OUT/'video_synthetic.mp4')
    doc={'project_id':'SYNTHETIC-M2-SPECIALIST-REPLAY',
         'property':{'label':'Illustrative home - synthetic agent demonstration',
                     'inspection_date':'2026-10-30','synthetic':True,
                     'inspector':'Test fixture; no actual inspection','qualified_reviewer':None},
         'media':[{'id':'P0001','kind':'photo','path':'house_synthetic.png','area':'exterior',
                    'sha256':sha256(OUT/'house_synthetic.png'),
                    'caption':'Generated test illustration - NOT site evidence'},
                  {'id':'V0001','kind':'video','path':'video_synthetic.mp4','area':'exterior',
                    'sha256':sha256(OUT/'video_synthetic.mp4'),
                    'capture':probe_video(OUT/'video_synthetic.mp4'),
                    'caption':'Synthetic video file - NOT site evidence'}],
         'observations':[],'findings':[],'equipment':[],'limitations':[]}
    initial_frames=video_frames(doc,OUT,'V0001',max_frames=2)
    selected=["P0001",initial_frames[0]['id']]
    (OUT/'01_work_orders.json').write_text(json.dumps(plan_specialists(doc,selected),indent=2)+'\n')
    call_index={}
    def fake_provider(img:bytes,prompt:str):
        import re
        mid=re.search(r'evidence ID ([\w-]+)',prompt).group(1)
        call_index[mid]=call_index.get(mid,0)+1
        if mid=='P0001' and call_index[mid]==1:
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.1,.1,.6,.7]}]}
        if mid==initial_frames[0]['id']:
            return {'candidates':[],'requests':[{'kind':'video_still','timestamp_seconds':1.0}]}
        return {'candidates':[{'type':'feature','system':'exterior',
             'feature_code':'cladding_type',
             'description':'Synthetic illustration contains visible exterior cladding; actual composition unverified',
             'location':'Illustrative front elevation','status':'partially_observed',
             'bbox':[.15,.2,.75,.85]}],'requests':[]}
    staged,dossier=execute_specialists(doc,OUT,fake_provider,media_ids=selected,
                                       provider_id='DISCLOSED_MANUAL_FIXTURE_NOT_REAL_AI')
    (OUT/'02_specialist_dossier.json').write_text(json.dumps(dossier,indent=2)+'\n')
    (OUT/'03_project_unapproved.json').write_text(json.dumps(staged,indent=2)+'\n')
    build_pdf(staged,OUT,OUT/'M2_Option2_Synthetic_Draft.pdf')
    derived=next(m for m in staged['media'] if m.get('capture_origin')=='selected_video_still')
    pixel_audit=verify_selected_photo_pixels(staged,OUT,derived['id'])
    summary={'video_photo_pixel_audit':pixel_audit,
             'work_orders':len(dossier['plan']['jobs']),
             'evidence_tool_actions':dossier['tool_requests'],
             'new_media_count':len(staged['media'])-len(doc['media']),
             'new_zoom_count':len(staged.get('zoom_views',[])),
             'proposed_observations':len(staged['observations']),
             'control_review':dossier['review'],
             'human_approved':dossier['human_approved'],
             'customer_release_allowed':dossier['customer_release_allowed'],
             'release_blockers':len(blockers(staged)),
             'model_executed':False,
             'kind':'Synthetic fixtures and manually scripted replay only'}
    (OUT/'04_acceptance.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
