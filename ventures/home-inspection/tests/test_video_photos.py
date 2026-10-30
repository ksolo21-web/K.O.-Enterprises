"""Real source-video to native-resolution photo + zoom + report acceptance tests."""
from __future__ import annotations
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
from inspection_engine.core import DataError, validate_project, coverage
from inspection_engine.capture import intake_files, video_frames, verify_custody
from inspection_engine.video_photos import parse_timecode, capture_video_photos, verify_selected_photo_pixels
from inspection_engine.zoom import create_zoom_views, verify_zoom_record
from inspection_engine.report import build_pdf
from inspection_engine.vision import analyze_media

FFMPEG=shutil.which('ffmpeg') and shutil.which('ffprobe')
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(FFMPEG,'FFmpeg/ffprobe required')
class NativeVideoPhotoTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.doc={'project_id':'VIDEO-PHOTOS-TEST','property':{
             'label':'Synthetic test property','inspection_date':'2026-10-30',
             'synthetic':True,'qualified_reviewer':None},
             'media':[],'observations':[],'findings':[],'equipment':[],'limitations':[]}
        src=self.root/'original_walkthrough.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'testsrc2=size=1440x900:rate=4','-t','2.5','-pix_fmt','yuv420p','-y',str(src)],
            check=True,capture_output=True,timeout=30)
        self.vid=intake_files(self.doc,self.root,[src],'exterior','porch')[0]

    def test_selected_photos_have_native_pixels_and_evidence_chain(self):
        items=capture_video_photos(self.doc,self.root,self.vid['id'],times=['00:00.250','1.25'],requested_by='roof-specialist')
        self.assertEqual(len(items),2)
        self.assertTrue(all(x['kind']=='photo' and x['id'].startswith('P') for x in items))
        self.assertTrue(all(x['capture_origin']=='selected_video_still' for x in items))
        self.assertEqual([x['native_frame_size'] for x in items],[[1440,900]]*2)
        self.assertTrue(all(x['sha256']==__import__('inspection_engine.core',fromlist=['sha256']).sha256(self.root/x['path']) for x in items))
        self.assertTrue(all(x['original_sha256']==self.vid['sha256'] for x in items))
        self.assertEqual(verify_custody(self.doc,self.root),[])
        self.assertEqual(validate_project(self.doc,self.root),self.doc)
        for item in items:
            with Image.open(self.root/item['path']) as im:
                self.assertEqual(im.size,(1440,900))
                self.assertEqual(im.format,'PNG')
            self.assertTrue(verify_selected_photo_pixels(self.doc,self.root,item['id'])['pixel_equal_to_source'])
        self.assertEqual(next(x for x in coverage(self.doc) if x['system']=='exterior')['status'],'not verified')

    def test_interval_selection_plus_original_video_remains(self):
        photos=capture_video_photos(self.doc,self.root,self.vid['id'],every_seconds=1,max_photos=4)
        self.assertEqual(len(photos),3)
        self.assertIn(self.vid,self.doc['media'])
        self.assertEqual([p['requested_seek_seconds'] for p in photos],[0.,1.,2.])

    def test_real_zoom_and_model_accept_extracted_photo(self):
        photo=capture_video_photos(self.doc,self.root,self.vid['id'],times=['0.75'])[0]
        zoom=create_zoom_views(self.doc,self.root,photo['id'],[[0.2,0.2,0.5,0.5]],
                               'roof-specialist','Inspect selected photograph more closely')[0]
        verify_zoom_record(zoom,self.doc,self.root,deep=True)
        self.assertEqual(zoom['native_source_size'],[1440,900])
        def mock(_pixels,_prompt):return {'candidates':[]}
        self.assertEqual(len(analyze_media(self.doc,self.root,[photo['id']],mock)['results']),1)

    def test_pdf_includes_photo_gallery_and_video_timestamp(self):
        captures=capture_video_photos(self.doc,self.root,self.vid['id'],times=['0','0.50','1.0'])
        pdf=self.root/'report.pdf'
        build_pdf(self.doc,self.root,pdf)
        reader=PdfReader(pdf)
        self.assertEqual(len(reader.pages),7) # baseline 5 + two gallery pages
        gallery=' '.join(p.extract_text() for p in reader.pages[5:])
        self.assertIn('Photographs from video',gallery)
        self.assertIn('VIDEO-DERIVED PHOTOGRAPH',gallery)
        self.assertIn('UNREVIEWED SOURCE EVIDENCE',gallery)
        for c in captures:self.assertIn(c['id'],gallery)
        self.assertIn(self.vid['id'],gallery)

    def test_reject_duplicate_timestamp_and_bad_seek_without_mutation(self):
        with self.assertRaises(DataError):capture_video_photos(self.doc,self.root,self.vid['id'],times=[1.0,1.0])
        with self.assertRaises(DataError):capture_video_photos(self.doc,self.root,self.vid['id'],times=[0,100])
        with self.assertRaises(DataError):capture_video_photos(self.doc,self.root,self.vid['id'],every_seconds=0.1,max_photos=3)
        self.assertEqual(len(self.doc['media']),1)
        self.assertEqual(list((self.root/'video_photos').glob('*.png')),[])
        capture_video_photos(self.doc,self.root,self.vid['id'],times=[1])
        with self.assertRaises(DataError):capture_video_photos(self.doc,self.root,self.vid['id'],times=[1])
        self.assertEqual(len(self.doc['media']),2)

    def test_tampering_and_photo_relabeling_rejected(self):
        p=capture_video_photos(self.doc,self.root,self.vid['id'],times=[0.5])[0]
        with Image.open(self.root/p['path']) as im:
            im2=im.copy()
        im2.putpixel((0,0),(255,255,255));im2.save(self.root/p['path'])
        with self.assertRaises(DataError):validate_project(self.doc,self.root)
        p['sha256']=__import__('inspection_engine.core',fromlist=['sha256']).sha256(self.root/p['path'])
        validate_project(self.doc,self.root) # Basic hashes alone cannot reject deliberate rehash
        with self.assertRaises(DataError):verify_selected_photo_pixels(self.doc,self.root,p['id'])
        p['capture']['image_format']='JPEG'
        with self.assertRaises(DataError):validate_project(self.doc,self.root)

    def test_cli_export_and_deep_audit(self):
        initial=self.root/'project.json'
        initial.write_text(json.dumps(self.doc))
        exported=self.root/'with_stills.json'
        command=[sys.executable,'-m','inspection_engine','video-photos',str(initial),
                 '--video-id',self.vid['id'],'--at','0.5','1.5',
                 '--out-project',str(exported)]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=40,check=True)
        self.assertEqual(len(json.loads(result.stdout)['saved_photos']),2)
        loaded=json.loads(exported.read_text())
        ids=[m['id'] for m in loaded['media'] if m.get('capture_origin')=='selected_video_still']
        verified=subprocess.run([sys.executable,'-m','inspection_engine','video-photo-audit',
                                 str(exported),'--photo-ids',*ids],cwd=ROOT,
                                 capture_output=True,text=True,timeout=50,check=True)
        self.assertTrue(all(x['pixel_equal_to_source'] for x in json.loads(verified.stdout)['audits']))

    def test_existing_thumbnails_unchanged_and_new_ids_do_not_collide(self):
        frames=video_frames(self.doc,self.root,self.vid['id'],2)
        photos=capture_video_photos(self.doc,self.root,self.vid['id'],times=[0.5])
        self.assertTrue(all(p['id']!=f['id'] for p in photos for f in frames))
        self.assertEqual(len(self.doc['media']),4)
        self.assertTrue(all(f['evidence_state']=='unreviewed_derived_frame' for f in frames))
        self.assertEqual(verify_custody(self.doc,self.root),[])

class TimecodeTests(unittest.TestCase):
    def test_times(self):
        self.assertEqual(parse_timecode('01:24.500'),84.5)
        self.assertEqual(parse_timecode('00:01:24.500'),84.5)
        self.assertEqual(parse_timecode('12.50'),12.5)
    def test_invalid(self):
        for value in ['-1','1:99','abc',float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(DataError):parse_timecode(value)

if __name__=='__main__':unittest.main()
