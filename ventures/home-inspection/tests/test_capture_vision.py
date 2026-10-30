import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from PIL import Image
from inspection_engine.core import DataError, validate_project, coverage, blockers
from inspection_engine.capture import intake_files, video_frames, verify_custody
from inspection_engine.vision import validate_proposal, analyze_media, apply_predictions, ollama_local

ROOT=Path(__file__).resolve().parents[1]
FFMPEG=shutil.which('ffmpeg') and shutil.which('ffprobe')

class CaptureAndVisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.doc={"project_id":"SYNTHETIC-TEST","property":{
             "label":"Test home","inspection_date":"2026-10-30","synthetic":True,"qualified_reviewer":None},
             "media":[],"observations":[],"findings":[],"equipment":[],"limitations":[]}
        self.source=self.root/'upload.jpg'
        Image.new('RGB',(300,200),(128,150,160)).save(self.source)

    def _intake(self):
        return intake_files(self.doc,self.root,[self.source],'exterior','entry')[0]

    def _provider(self, b, prompt):
        self.assertTrue(b.startswith(b'\xff\xd8'))
        self.assertIn('System feature codes',prompt)
        return {'candidates':[{'type':'feature','system':'exterior',
                  'feature_code':'cladding_type','description':'Gray exterior wall cladding is visible.',
                  'status':'observed','location':'front elevation','bbox':[0.1,0.1,0.9,0.9]},
                 {'type':'potential_concern','system':'exterior',
                  'description':'A discolored area may warrant a closer visual look.',
                  'status':'partially_observed','location':'front elevation'}]}

    def test_intake_writes_original_hash_and_room(self):
        m=self._intake()
        self.assertEqual(m['room'],'entry')
        self.assertEqual(len(m['sha256']),64)
        self.assertTrue((self.root/m['path']).is_file())
        self.assertEqual(verify_custody(self.doc,self.root),[])

    def test_reject_fake_image_even_with_jpeg_extension(self):
        self.source.write_bytes(b'not a real jpeg')
        with self.assertRaises(DataError):self._intake()
        self.assertFalse(self.doc['media'])

    def test_rollback_when_second_item_corrupt(self):
        other=self.root/'bad.jpg';other.write_bytes(b'bad')
        with self.assertRaises(DataError):
            intake_files(self.doc,self.root,[self.source,other],'exterior')
        self.assertEqual(self.doc['media'],[])
        self.assertEqual(list((self.root/'assets').glob('*.jpg')),[])

    def test_integrity_error_on_mutation(self):
        m=self._intake()
        Image.new('RGB',(300,200),(70,70,70)).save(self.root/m['path'])
        with self.assertRaises(DataError):validate_project(self.doc,self.root)
        self.assertTrue(verify_custody(self.doc,self.root))

    def test_no_entire_system_verified_from_capture(self):
        self._intake()
        self.assertEqual(next(x for x in coverage(self.doc) if x['system']=='exterior')['status'],'not verified')
        self.assertTrue(blockers(self.doc))

    def test_adapter_returns_pending_only(self):
        m=self._intake()
        p=analyze_media(self.doc,self.root,[m['id']],self._provider,'deterministic-test-fixture')
        self.assertEqual(p['status'],'UNVERIFIED_MACHINE_DRAFT')
        self.assertEqual(p['results'][0]['proposals'][0]['status'],'partially_observed')
        upgraded=apply_predictions(self.doc,self.root,p)
        self.assertEqual(len(upgraded['observations']),1)
        self.assertEqual(len(upgraded['findings']),1)
        self.assertEqual(upgraded['findings'][0]['severity'],'further_evaluation')
        self.assertIn('Possible visible concern',upgraded['findings'][0]['condition'])
        self.assertEqual(upgraded['observations'][0]['review'],'review_pending')
        self.assertEqual(len(self.doc['observations']),0)  # original unchanged
        self.assertIn('HOLD',__import__('inspection_engine.core',fromlist=['record_status']).record_status(dict(upgraded,property=dict(upgraded['property'],synthetic=False))))

    def test_prevent_proposal_swap_between_two_images(self):
        m=self._intake()
        p=analyze_media(self.doc,self.root,[m['id']],self._provider)
        swapped=copy.deepcopy(p);swapped['results'][0]['sha256']='0'*64
        with self.assertRaises(DataError):apply_predictions(self.doc,self.root,swapped)

    def test_reject_invalid_bbox_or_system_feature(self):
        m=self._intake()
        c={'type':'feature','system':'hvac','feature_code':'cladding_type','description':'claimed',
           'status':'observed','bbox':[0,0,1,1]}
        with self.assertRaises(DataError):validate_proposal({'candidates':[c]},m)
        c.update({'system':'exterior','bbox':[0.9,0.2,0.1,0.6]})
        with self.assertRaises(DataError):validate_proposal({'candidates':[c]},m)

    def test_reject_false_safety_assurance(self):
        m=self._intake()
        with self.assertRaises(DataError):
            validate_proposal({'candidates':[{'type':'feature','system':'exterior',
               'feature_code':'cladding_type','description':'No defects observed on whole exterior',
               'status':'observed'}]},m)

    def test_reject_concealed_system_claim_from_exterior_photo(self):
        m=self._intake()
        with self.assertRaises(DataError):
            validate_proposal({'candidates':[{'type':'feature','system':'framing',
               'feature_code':'exterior_wall_structure','description':'Framing is wood',
               'status':'observed'}]},m)

    def test_unknown_concern_does_not_make_finding(self):
        m=self._intake()
        result=validate_proposal({'candidates':[{'type':'potential_concern','system':'roof',
                      'status':'unknown','description':'No visible proof'}]},m)
        self.assertEqual(result,[])

    def test_batch_requires_photos_or_sampled_frames(self):
        self._intake()
        with self.assertRaises(DataError):analyze_media(self.doc,self.root,['missing'],self._provider)

    def test_reject_overlong_model_proposal_in_report(self):
        m=self._intake()
        c={'type':'feature','system':'exterior','feature_code':'cladding_type',
           'description':'UnbrokenString'*30,'status':'partially_observed'}
        with self.assertRaises(DataError):validate_proposal({'candidates':[c]},m)

    def test_appendix_contains_all_unreviewed_proposals(self):
        from inspection_engine.report import build_pdf
        from pypdf import PdfReader
        m=self._intake()
        preds=analyze_media(self.doc,self.root,[m['id']],self._provider,'test')
        full=apply_predictions(self.doc,self.root,preds)
        output=self.root/'visual_review.pdf'
        build_pdf(full,self.root,output)
        reader=PdfReader(output)
        self.assertEqual(len(reader.pages),6)
        appendix=' '.join(x.extract_text() for x in reader.pages[5:])
        self.assertIn('VIS-0001',appendix)
        self.assertIn('VIS-0002',appendix)
        self.assertIn('NOT REVIEWED OR APPROVED',appendix)
        self.assertIn(m['id'],appendix)

    def test_invalid_model_identifier_rejected_without_network(self):
        with self.assertRaises(DataError):ollama_local(b'x','prompt','https://bad.site')

    @unittest.skipUnless(FFMPEG,'FFmpeg required')
    def test_real_video_extraction_preserves_timestamp_and_parent(self):
        video=self.root/'walkthrough.mp4'
        subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi','-i','testsrc=size=160x120:rate=2',
                        '-t','2','-pix_fmt','yuv420p','-y',str(video)],
                       check=True,capture_output=True,timeout=25)
        item=intake_files(self.doc,self.root,[video],'roof','attic')[0]
        frames=video_frames(self.doc,self.root,item['id'],3)
        self.assertEqual(len(frames),3)
        self.assertTrue(all(f['original_sha256']==item['sha256'] for f in frames))
        self.assertTrue(all(f['derived_from_id']==item['id'] for f in frames))
        self.assertLess(frames[0]['timestamp_seconds'],frames[1]['timestamp_seconds'])
        self.assertEqual(verify_custody(self.doc,self.root),[])
        self.assertEqual(next(x for x in coverage(self.doc) if x['system']=='roof')['status'],'not verified')
        # Tamper the original video without touching the derived images.
        with (self.root/item['path']).open('ab') as f:f.write(b'changed')
        self.assertTrue(verify_custody(self.doc,self.root))
        with self.assertRaises(DataError):validate_project(self.doc,self.root)

    @unittest.skipUnless(FFMPEG,'FFmpeg required')
    def test_bad_video_is_not_accepted(self):
        src=self.root/'bad.mp4';src.write_bytes(b'invalid video')
        with self.assertRaises(DataError):
            intake_files(self.doc,self.root,[src],'hvac')

if __name__=='__main__':unittest.main()
