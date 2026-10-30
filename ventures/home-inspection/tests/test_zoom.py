"""Pixel-level and provenance acceptance gates for native source zoom."""
from __future__ import annotations
import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from inspection_engine.core import DataError,validate_project,coverage,blockers,sha256
from inspection_engine.capture import intake_files,video_frames,verify_custody
from inspection_engine.zoom import create_zoom_views,grid_regions,verify_zoom_record,zoom_from_predictions
from inspection_engine.vision import analyze_zoom_views,apply_predictions

VIDEO_TOOLS=bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))

class NativeZoomAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.doc={'project_id':'ZOOM-SYNTHETIC-ONLY','property':{'label':'Synthetic pixel test',
             'inspection_date':'2026-10-30','synthetic':True,'qualified_reviewer':None},
             'media':[],'observations':[],'findings':[],'equipment':[],'limitations':[]}
        self.src=self.root/'photo.png'
        # Full resolution: a tiny 2x2 marker disappears on 1400px thumbnail.
        im=Image.new('RGB',(3600,2400),(235,236,232))
        dr=ImageDraw.Draw(im)
        dr.line((2275,1394,2360,1404),fill=(24,26,30),width=3)
        dr.rectangle((2331,1399,2332,1400),fill=(250,0,0))
        im.save(self.src)
        self.original=intake_files(self.doc,self.root,[self.src],'roof','eave')[0]

    def _one(self, bbox=(0.6,0.5,0.7,0.7)):
        return create_zoom_views(self.doc,self.root,self.original['id'],[bbox],
                   'roof-specialist','Look for visible roof flashing and seams')[0]

    def _provider(self,image_bytes,prompt):
        self.assertIn('ORIGINAL SOURCE PIXEL',prompt)
        self.assertIn('CROPPED VIEW',prompt)
        return {'candidates':[
            {'type':'potential_concern','system':'roof',
             'description':'A narrow dark mark is visible; its cause is unknown.',
             'status':'partially_observed','location':'roof eave',
             'bbox':[0.1,0.3,0.75,0.7]}]}

    def test_zoom_crops_actual_source_pixels_not_upsampling(self):
        z=self._one();validate_project(self.doc,self.root)
        self.assertEqual(z['source_type'],'original_photo')
        self.assertEqual(z['crop_native_size'],[360,480])
        self.assertEqual(z['pixel_policy'],'LOSSLESS_NATIVE_CROP_NO_ENHANCEMENT')
        self.assertGreater(z['linear_zoom_equivalent'],6)
        verify_zoom_record(z,self.doc,self.root,deep=True)
        with Image.open(self.src) as base,Image.open(self.root/z['path']) as crop:
            self.assertEqual(crop.tobytes(),base.crop(tuple(z['pixel_bbox'])).tobytes())
        self.assertEqual(verify_custody(self.doc,self.root),[])

    def test_arbitrarily_deep_nested_coordinates_but_never_invent_pixels(self):
        a=self._one((0.5,0.5,0.75,0.75))
        # Request a much smaller subset in SOURCE coordinates; original is used again.
        b=self._one((0.647,0.583,0.65,0.59))
        self.assertGreater(b['linear_zoom_equivalent'],a['linear_zoom_equivalent']*10)
        self.assertGreaterEqual(min(b['crop_native_size']),2)
        self.assertEqual(a['source_sha256'],b['source_sha256'])
        self.assertNotEqual(a['sha256'],b['sha256'])

    def test_grid_complete_overlapping_and_multi_request(self):
        tiles=grid_regions((0.1,0.1,0.9,0.9),2,3,.25)
        self.assertEqual(len(tiles),6)
        self.assertEqual(tiles[0][0],.1)
        self.assertAlmostEqual(tiles[-1][2],.9)
        self.assertAlmostEqual(tiles[-1][3],.9)
        zooms=create_zoom_views(self.doc,self.root,self.original['id'],tiles,'exterior-specialist','Grid scan')
        self.assertEqual(len({z['id'] for z in zooms}),6)
        self.assertEqual(verify_custody(self.doc,self.root),[])

    def test_missing_invalid_zoom_regions_fail_closed_without_creating_files(self):
        invalids=[[0,0,0,0],[.8,.1,.2,.2],[-.1,0,1,1],[0,0,float('nan'),1],
                  [0,0,float('inf'),1],[0,.5,1,1.01],[0,0,0.0001,0.0001]]
        for bad in invalids:
            with self.subTest(bbox=bad):
                with self.assertRaises(DataError):create_zoom_views(self.doc,self.root,self.original['id'],[bad])
        self.assertEqual(self.doc.get('zoom_views'),None)
        self.assertEqual(list((self.root/'zoom_views').glob('*.png')),[])

    def test_roll_back_batch_on_invalid_tiny_crop(self):
        with self.assertRaises(DataError):
            create_zoom_views(self.doc,self.root,self.original['id'],
                [(0,0,.5,.5),(0,0,.00001,.00001)],'roof-agent','Test rollback')
        self.assertFalse(self.doc.get('zoom_views'))
        self.assertEqual(list((self.root/'zoom_views').glob('*.png')),[])

    def test_crop_or_original_tamper_blocks_analysis(self):
        z=self._one()
        p=self.root/z['path']
        with Image.open(p) as im: hacked=im.copy()
        hacked.putpixel((0,0),(0,0,0));hacked.save(p)
        self.assertTrue(verify_custody(self.doc,self.root))
        with self.assertRaises(DataError):analyze_zoom_views(self.doc,self.root,[z['id']],self._provider)

    def test_zoom_analysis_review_gating_and_full_image_bbox(self):
        z=self._one()
        predictions=analyze_zoom_views(self.doc,self.root,[z['id']],self._provider,'scripted-test-not-real-ai')
        p=predictions['results'][0]['proposals'][0]
        self.assertEqual(p['zoom_view_ids'],[z['id']])
        self.assertAlmostEqual(p['bbox'][0],.61)
        self.assertAlmostEqual(p['bbox'][1],.56)
        result=apply_predictions(self.doc,self.root,predictions)
        finding=result['findings'][0]
        self.assertEqual(finding['zoom_view_ids'],[z['id']])
        self.assertEqual(finding['evidence_ids'],[self.original['id']])
        self.assertEqual(finding['review'],'review_pending')
        self.assertEqual(finding['severity'],'further_evaluation')
        self.assertEqual(next(x for x in coverage(result) if x['system']=='roof')['status'],'not verified')
        self.assertTrue(blockers(result))
        self.assertEqual(self.doc['findings'],[])

    def test_zoom_prediction_swaps_are_rejected(self):
        z=self._one()
        prediction=analyze_zoom_views(self.doc,self.root,[z['id']],self._provider)
        for field,bad in [('zoom_sha256','f'*64),('zoom_view_id','Z9999'),
                          ('zoom_source_bbox',[0,.2,.3,.4])]:
            p=copy.deepcopy(prediction);p['results'][0][field]=bad
            with self.subTest(field=field),self.assertRaises(DataError):
                apply_predictions(self.doc,self.root,p)
        p=copy.deepcopy(prediction)
        p['results'][0]['proposals'][0]['bbox']=[0,0,1,1]
        with self.assertRaises(DataError):apply_predictions(self.doc,self.root,p)
        p=copy.deepcopy(prediction)
        p['results'][0]['proposals'][0]['zoom_view_ids']=['Z0002']
        with self.assertRaises(DataError):apply_predictions(self.doc,self.root,p)

    def test_crop_forgery_with_matching_hash_is_detected_by_deep_source_check(self):
        z=self._one()
        path=self.root/z['path']
        with Image.open(path) as im: fake=im.copy()
        fake.putpixel((10,10),(12,43,76));fake.save(path)
        z['sha256']=sha256(path)
        # Manifest & file hashes now agree, but actual source pixels do not.
        verify_zoom_record(z,self.doc,self.root,deep=False)
        with self.assertRaises(DataError):verify_zoom_record(z,self.doc,self.root,deep=True)
        with self.assertRaises(DataError):analyze_zoom_views(self.doc,self.root,[z['id']],self._provider)

    def test_generated_pdf_evidence_shows_context_and_closeup(self):
        from inspection_engine.report import build_pdf
        from pypdf import PdfReader
        z=self._one()
        p=analyze_zoom_views(self.doc,self.root,[z['id']],self._provider)
        changed=apply_predictions(self.doc,self.root,p)
        output=self.root/'report.pdf';build_pdf(changed,self.root,output)
        self.assertTrue(output.exists())
        reader=PdfReader(output)
        self.assertEqual(len(reader.pages),6)
        appendix=reader.pages[-1].extract_text()
        self.assertIn('NATIVE DETAIL',appendix)
        self.assertIn(z['id'],appendix)
        self.assertIn('NOT REVIEWED OR APPROVED',appendix)
        self.assertIn('CONTEXT',appendix)

    def test_invalid_grid_limits_and_no_fake_superresolution(self):
        for args in [(9,1,0),(1,9,0),(8,8,0), (2,2,-.1),(2,2,.5)]:
            with self.subTest(args=args),self.assertRaises(DataError):
                grid_regions((0,0,1,1),*args)
        z=self._one()
        self.assertNotIn('super_resolved',z)
        self.assertNotIn('enhanced',z['pixel_policy'].lower())

    def test_agent_can_request_deeper_zoom_from_its_bounding_box(self):
        from inspection_engine.vision import analyze_media
        def proposer(image,prompt):
            return {'candidates':[{'type':'potential_concern','system':'roof',
                'description':'A small roofline detail might need close examination.',
                'status':'partially_observed','location':'eave',
                'bbox':[.60,.50,.70,.70]}]}
        p=analyze_media(self.doc,self.root,[self.original['id']],proposer)
        selected=zoom_from_predictions(self.doc,self.root,p,self.original['id'],'roof-specialist')
        self.assertEqual(len(selected),1)
        self.assertGreater(selected[0]['linear_zoom_equivalent'],4)
        self.assertTrue(selected[0]['normalized_bbox'][0]<.60)
        zoom_response=analyze_zoom_views(self.doc,self.root,[selected[0]['id']],self._provider)
        deeper=zoom_from_predictions(self.doc,self.root,zoom_response,self.original['id'],'roof-specialist')
        self.assertEqual(len(deeper),1)
        self.assertGreater(deeper[0]['linear_zoom_equivalent'],selected[0]['linear_zoom_equivalent'])
        self.assertEqual(len(self.doc['findings']),0)

    def test_agent_cannot_request_zoom_from_tampered_proposal(self):
        from inspection_engine.vision import analyze_media
        def proposer(image,prompt):
            return {'candidates':[{'type':'potential_concern','system':'roof',
                'description':'Uncertain small dark region.',
                'status':'partially_observed','bbox':[.6,.5,.7,.7]}]}
        p=analyze_media(self.doc,self.root,[self.original['id']],proposer)
        p['results'][0]['sha256']='a'*64
        with self.assertRaises(DataError):zoom_from_predictions(self.doc,self.root,p,self.original['id'])
        self.assertFalse(self.doc.get('zoom_views'))

    @unittest.skipUnless(VIDEO_TOOLS,'FFmpeg tools needed for native video frame test')
    def test_video_zoom_recovers_original_frame_resolution(self):
        vid=self.root/'synthetic.mp4'
        subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi',
             '-i','testsrc=size=1440x900:rate=2','-t','2',
             '-pix_fmt','yuv420p','-y',str(vid)],capture_output=True,check=True,timeout=50)
        item=intake_files(self.doc,self.root,[vid],'roof','walkthrough')[0]
        frames=video_frames(self.doc,self.root,item['id'],2)
        with Image.open(self.root/frames[0]['path']) as downscaled:
            self.assertLessEqual(downscaled.width,1280)
        zoom=create_zoom_views(self.doc,self.root,frames[0]['id'],[(0.2,0.2,0.8,0.8)],
                     'roof-specialist','Inspect native-resolution original footage')[0]
        self.assertEqual(zoom['source_type'],'original_video_native_frame')
        self.assertEqual(zoom['native_source_size'],[1440,900])
        self.assertEqual(zoom['crop_native_size'],[864,540])
        verify_zoom_record(zoom,self.doc,self.root,deep=True)
        self.assertEqual(verify_custody(self.doc,self.root),[])

if __name__=='__main__': unittest.main()
