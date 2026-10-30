"""Reproducible synthetic media and deterministic fixture replay.
NO model invocation, real defect detection, or real property data.
"""
from __future__ import annotations
import json
import shutil
import re
import subprocess
from pathlib import Path
from inspection_engine.core import load_project
from inspection_engine.capture import intake_files, video_frames
from inspection_engine.vision import analyze_media, apply_predictions
from inspection_engine.report import build_pdf

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'examples'/'m1'
D.mkdir(exist_ok=True,parents=True)

def save(path,obj):
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf8')

def main():
    # A controlled synthetic fixture only: do not erase unknown files.
    for folder,pattern in [('assets',r'^[PV]0001_[0-9a-f]{16}\.(png|mp4)$'),
                           ('frames',r'^V0001_t[0-9]{9}_[0-9a-f]{8}\.jpg$')]:
        dst=D/folder
        if dst.exists():
            for file in dst.iterdir():
                if not file.is_file() or not re.fullmatch(pattern,file.name):
                    raise RuntimeError('Refusing to delete an unknown demo file: '+str(file))
                file.unlink()
    # Use the pre-existing synthetic scenario and original exterior as baseline.
    for n in ['demo_exterior.png','demo_evidence.png']:
        shutil.copyfile(ROOT/'examples'/n,D/n)
    source=json.loads((ROOT/'examples'/'editorial_demo_project.json').read_text())
    source['property']['label']='Illustrative demonstration residence — NOT A REAL INSPECTION'
    source['project_id']='DEMO-M1-SYNTHETIC'
    # Reconcile earlier schematic-only notes against the newly included exterior.
    for obs in source['observations']:
        if obs['id']=='O04':
            obs.update(status='partially_observed', evidence_ids=['P00'],
                description='Illustration shows roof surfaces, but actual roof material, installation and condition remain unverified.')
    for limitation in source['limitations']:
        if limitation['id']=='L01':
            limitation['description']='No close-up roof inspection images or roof access evidence supplied; the exterior illustration cannot establish roof condition.'
    save(D/'00_baseline_project.json',source)
    doc=load_project(D/'00_baseline_project.json')
    # Ingest via actual image parser/hasher; no actual property footage is present.
    added=intake_files(doc,D,[D/'demo_exterior.png'],'exterior','front elevation')[0]
    added['caption']='Synthetic visual model replay — illustrative home image only'
    test_pattern=D/'synthetic_video_test_pattern.mp4'
    if not test_pattern.exists():
        subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi',
                        '-i','testsrc=size=480x320:rate=4','-t','3','-pix_fmt','yuv420p',
                        '-y',str(test_pattern)],check=True,timeout=30)
    video=intake_files(doc,D,[test_pattern],'test_pattern','synthetic frame sample')[0]
    save(D/'01_intake.json',doc)
    extracted=video_frames(doc,D,video['id'],4)
    save(D/'02_with_video_frames.json',doc)
    def fake_provider(image, prompt):
        # Human-authored scenario fixture. NEVER presented as a real vision result.
        return {'candidates':[
            {'type':'feature','system':'exterior','feature_code':'cladding_type',
             'description':'The illustration depicts areas of horizontal lap-style siding and masonry veneer. The actual wall assembly remains unverified.',
             'status':'partially_observed','location':'depicted front elevation',
             'bbox':[0.03,0.20,0.98,0.90]},
            {'type':'feature','system':'roof','feature_code':'roof_covering',
             'description':'Dark, overlapping shingle-style roof surfaces are depicted. Material, age and condition cannot be established from this illustration.',
             'status':'partially_observed','location':'depicted roof surfaces',
             'bbox':[0.15,0.07,0.90,0.47]},
            {'type':'potential_concern','system':'exterior',
             'description':'Illustrated tree branches appear close to exterior roof edges. Only an on-site inspection can establish actual clearance and condition.',
             'status':'partially_observed','location':'depicted side elevations',
             'bbox':[0.0,0.05,0.99,0.82]}
        ]}
    predictions=analyze_media(doc,D,[added['id']],fake_provider,
                    provider_id='SYNTHETIC_HUMAN_AUTHORED_REPLAY_NOT_AI')
    save(D/'03_synthetic_replay_predictions.json',predictions)
    revised=apply_predictions(doc,D,predictions)
    save(D/'04_provisional_project.json',revised)
    pdf=ROOT/'output'/'m1_photo_video_evidence_editorial_demo.pdf'
    build_pdf(revised,D,pdf)
    summary={'demo':'SYNTHETIC / UNVERIFIED / NO MODEL WAS RUN',
             'original_media_count':len(doc['media'])-len(extracted),
             'sampled_video_frames':len(extracted),
             'proposed_observations':2,'proposed_concerns':1,
             'report_pdf':str(pdf.relative_to(ROOT))}
    save(ROOT/'output'/'m1_verified_execution_manifest.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
