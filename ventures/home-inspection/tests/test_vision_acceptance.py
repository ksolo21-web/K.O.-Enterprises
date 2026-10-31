"""Unit tests for the acceptance controller; cannot prove live model inference."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inspection_engine.core import DataError
from scripts.run_vision_acceptance import run_acceptance, main


def fake_ready(a,b):
    return {'models':[{'model':a,'vision_capability_advertised':True,'model_digest_sha256':'a'*64},
                      {'model':b,'vision_capability_advertised':True,'model_digest_sha256':'b'*64}],
            'real_inference_completed':False}


def fake_smoke(a,b):
    return {'status':'MOCK_CONTRACT_PASSED','actual_image_inference_executed':False,
            'probes_per_model':2,'models':[{'passed':True} for _ in range(4)]}


def fake_trial(root,a,b,with_video=True):
    root.mkdir()
    (root/'trial_status.json').write_text(json.dumps({'synthetic':True}))
    return {'status':'SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED',
            'autonomous_zoom_request_count':1,'autonomous_video_still_count':1,
            'technical_review_items':2,'reviewer_model_calls_completed':False,
            'real_model_invocations_completed':False}

class VisionAcceptanceTests(unittest.TestCase):
    def test_scripted_pipeline_is_necessarily_blocked_and_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'proof'
            result=run_acceptance(directory,'writer','reviewer',preflight=fake_ready,smoke=fake_smoke,trial=fake_trial)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse(result['production_dependencies_used'])
            self.assertFalse(result['live_model_inference_verified'])
            self.assertFalse(result['customer_release_allowed'])
            self.assertIn('image_probe.json',result['artifact_sha256'])
            self.assertIn('trial/trial_status.json',result['artifact_sha256'])
            self.assertTrue((directory/'acceptance_status.json').exists())

    def test_fixed_response_cannot_pass_two_images_per_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            def weak(*args):
                r=fake_smoke(*args)
                r['models'][1]['passed']=False
                return r
            result=run_acceptance(Path(tmp)/'proof','a','b',preflight=fake_ready,smoke=weak,trial=fake_trial)
            self.assertEqual(result['stage'],'synthetic_image_probe')
            self.assertIn('challenge failed',result['blocker'])
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse((Path(tmp)/'proof/trial').exists())

    def test_existing_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'proof';root.mkdir();(root/'old.txt').write_text('retained')
            with self.assertRaisesRegex(DataError,'overwrite'):
                run_acceptance(root,'a','b',preflight=fake_ready,smoke=fake_smoke,trial=fake_trial)
            self.assertEqual((root/'old.txt').read_text(),'retained')

    def test_missing_ollama_creates_factual_blocked_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            def blocked(*args): raise DataError('Local runtime unavailable')
            root=Path(tmp)/'proof'
            result=run_acceptance(root,'a','b',preflight=blocked,smoke=fake_smoke,trial=fake_trial)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(result['stage'],'preflight')
            self.assertIn('unavailable',result['blocker'])
            self.assertTrue((root/'acceptance_status.json').exists())

    def test_equal_model_names_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DataError,'different model'):
                run_acceptance(Path(tmp)/'trial','same','same',preflight=fake_ready,smoke=fake_smoke,trial=fake_trial)

    def test_nonchanging_video_cannot_pass_full_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_acceptance(Path(tmp)/'proof','a','b',
                                  preflight=fake_ready,smoke=fake_smoke,trial=fake_trial)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse(result['synthetic_video_temporal_change_verified'])
            self.assertIn('visibly changing',result['blocker'])
            self.assertFalse(result['customer_release_allowed'])

    def test_no_video_never_passes_full_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_acceptance(Path(tmp)/'proof','a','b',preflight=fake_ready,smoke=fake_smoke,trial=fake_trial,with_video=False)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse(result['customer_release_allowed'])

if __name__=='__main__': unittest.main()
