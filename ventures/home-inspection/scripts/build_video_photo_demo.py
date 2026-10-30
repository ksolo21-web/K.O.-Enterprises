"""Reproducible synthetic house video -> selectable native still photo -> PDF proof.

Video is created by panning a generated illustration/photo. This is NOT a
real inspection and does not call or benchmark a vision model.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
from inspection_engine.core import load_project
from inspection_engine.capture import intake_files
from inspection_engine.video_photos import capture_video_photos,verify_selected_photo_pixels
from inspection_engine.zoom import create_zoom_views,verify_zoom_record
from inspection_engine.report import build_pdf

ROOT=Path(__file__).resolve().parents[1]
DEMO=ROOT/'examples'/'v05_photo_from_video'
OUT=ROOT/'output'

def main():
    DEMO.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    # Original v0.4 project was a designed sample, not verified field evidence.
    legacy=ROOT/'examples'/'m1'
    for sub in ('assets','frames'):
        (DEMO/sub).mkdir(exist_ok=True)
        for original in (legacy/sub).iterdir():
            dest=DEMO/sub/original.name
            if original.is_file() and not dest.exists():shutil.copy2(original,dest)
    for name in ('demo_exterior.png','demo_evidence.png'):
        if not (DEMO/name).exists():shutil.copy2(legacy/name,DEMO/name)
    initial=DEMO/'00_existing_project.json'
    if not initial.exists():shutil.copy2(legacy/'04_provisional_project.json',initial)
    doc=load_project(initial)
    video=DEMO/'synthetic_moving_house_view.mp4'
    if not video.exists():
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-loop','1',
            '-framerate','4','-i',str(DEMO/'demo_exterior.png'),
            '-vf',"zoompan=z='min(zoom+0.0015,1.045)':d=24:s=1440x900:fps=4",
            '-t','6','-an','-c:v','mpeg4','-q:v','5','-pix_fmt','yuv420p',
            '-y',str(video)],check=True,capture_output=True,timeout=100)
    registered=intake_files(doc,DEMO,[video],'exterior','front elevation')[0]
    photos=capture_video_photos(doc,DEMO,registered['id'],times=['00:00.500','2.5','4.5'],
        requested_by='inspection-specialist',note='Select house-view footage frames for closer human review')
    for p in photos:verify_selected_photo_pixels(doc,DEMO,p['id'])
    zoom=create_zoom_views(doc,DEMO,photos[1]['id'],[[.3,.08,.7,.48]],
        requested_by='roof-specialist',purpose='Check native pixels of video-captured still')[0]
    verify_zoom_record(zoom,doc,DEMO,deep=True)
    final=DEMO/'01_video_photos_and_zoom_project.json'
    final.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
    pdf=OUT/'Option2_Video_To_Photos_v0.5_Demo.pdf'
    build_pdf(doc,DEMO,pdf)
    # One-page illustration of video-to-photo workflow with 3 real decoded frames.
    board=Image.new('RGB',(1680,1010),'#f2f5f6')
    draw=ImageDraw.Draw(board)
    def font(sz,b=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if b else '')+'.ttf',sz)
    draw.rectangle((0,0,1680,130),fill='#152A3C')
    draw.text((62,32),'VIDEO FOOTAGE  /  STILL PHOTOGRAPHS',fill='white',font=font(39,True))
    draw.text((62,91),'Synthetic demonstration - native decoded frames, exact timestamps, editable report evidence',fill='#dde6ec',font=font(18))
    for i,item in enumerate(photos):
        x=56+548*i
        draw.rectangle((x,195,x+514,820),fill='white')
        with Image.open(DEMO/item['path']) as im:
            photo=ImageOps.contain(im.convert('RGB'),(488,405))
        board.paste(photo,(x+(514-photo.width)//2,254+(405-photo.height)//2))
        draw.text((x+17,215),f"{item['id']}  |  {item['timestamp_seconds']:.3f}s",fill='#152A3C',font=font(25,True))
        draw.text((x+17,695),f"Source video: {item['derived_from_id']}",fill='#425367',font=font(20))
        draw.text((x+17,730),f"{item['native_frame_size'][0]} x {item['native_frame_size'][1]} native pixels",fill='#425367',font=font(18))
        draw.text((x+17,770),'UNREVIEWED EVIDENCE',fill='#A2794B',font=font(16,True))
    draw.text((56,869),'Each photograph is saved separately, available for zoom and analysis, and traceable to the original video.',fill='#152A3C',font=font(19,True))
    draw.text((56,908),'The photographed home and video movement are illustrative; no real home, model or defect was inspected.',fill='#526477',font=font(18))
    image=OUT/'Video_Still_Photos_Overview_v0.5.png'
    board.save(image)
    manifest={'demonstration':'SYNTHETIC HOUSE VIDEO; NO LIVE VISION MODEL',
      'source_video':registered['id'],'source_video_sha256':registered['sha256'],
      'saved_video_photos':photos,
      'native_zoom_from_video_photo':{'id':zoom['id'],'source_photo':zoom['media_id'],
                    'zoom_native_size':zoom['crop_native_size']},
      'deep_video_photo_audits':'3 / 3 PASS','deep_zoom_source_audit':'PASS',
      'report':str(pdf.relative_to(ROOT)),'photo_overview':str(image.relative_to(ROOT))}
    (OUT/'video_photo_demo_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'photos':[p['id'] for p in photos],
        'photo_timestamp_seconds':[p['timestamp_seconds'] for p in photos],
        'pdf':str(pdf),'overview':str(image),'source_size':photos[0]['native_frame_size']},indent=2))

if __name__=='__main__':main()
