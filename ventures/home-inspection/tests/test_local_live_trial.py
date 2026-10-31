"""Synthetic end-to-end trial; provider replies are scripted, NOT real AI."""
import tempfile
from pathlib import Path
import unittest
from inspection_engine.core import DataError
from scripts.run_local_live_trial import run_trial

class LocalLiveTrialTests(unittest.TestCase):
    def test_scripted_specialist_and_distinct_reviewer_produce_unreleased_record(self):
        with tempfile.TemporaryDirectory() as path:
            out=Path(path)/'demo'
            called={'writer':0,'reviewer':0}
            def writer(image,prompt):
                called['writer']+=1
                return {'candidates':[{'type':'feature','system':'exterior',
                        'feature_code':'cladding_type','status':'partially_observed',
                        'description':'A facade appears in the computer generated illustration',
                        'location':'front view','bbox':[0.1,0.1,0.8,0.8]}], 'requests':[]}
            def reviewer(image,prompt):
                called['reviewer']+=1
                return {'decision':'insufficient_evidence','reason':'Only a synthetic drawing',
                        'missing_evidence':'Real site photography'}
            result=run_trial(out,'writer:model','reviewer:model',writer=writer,reviewer=reviewer,with_video=False)
            self.assertEqual(result['status'],'SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED')
            self.assertEqual(result['technical_review_items'],1)
            self.assertTrue(called['writer']>0 and called['reviewer']>0)
            self.assertFalse(result['real_model_invocations_requested'])
            self.assertFalse(result['field_accuracy_verified'])
            self.assertFalse(result['customer_release_allowed'])
            self.assertTrue((out/'trial_status.json').exists())

    def test_empty_candidate_fails_trial_approval(self):
        with tempfile.TemporaryDirectory() as path:
            out=Path(path)/'no_claim'
            res=run_trial(out,'w','r',writer=lambda *a:{'candidates':[],'requests':[]},
                          reviewer=lambda *a:{},with_video=False)
            self.assertEqual(res['status'],'INCOMPLETE_NO_REVIEWABLE_CLAIM')
            self.assertFalse(res['customer_release_allowed'])

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaisesRegex(DataError,'existing'):
                run_trial(Path(path),'w','r',writer=lambda *a:{},reviewer=lambda *a:{},with_video=False)

if __name__=='__main__':unittest.main()

class NativeZoomAndVideoTrialTests(unittest.TestCase):
    def test_model_tools_on_real_synthetic_video_fixture(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)/'video_trial'
            states={'writer':0,'reviewer':0}
            def writer(img,prompt):
                states['writer']+=1
                # First exterior overview -> zoom -> proposal. Sampled video ->
                # native video still -> proposal with retained original timestamp.
                if 'evidence ID P0001' in prompt and 'region [0, 0, 1, 1]' in prompt:
                    return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.15,.15,.55,.60]}]}
                if 'evidence ID V0001-F01' in prompt and 'normalized original-image region [0, 0, 1, 1]' in prompt:
                    return {'candidates':[],'requests':[{'kind':'video_still','timestamp_seconds':1.0}]}
                return {'candidates':[{'type':'feature','system':'exterior',
                       'feature_code':'cladding_type','status':'partially_observed',
                       'description':'Visible stylized exterior siding in a synthetic illustration',
                       'location':'front','bbox':[.1,.1,.4,.4]}], 'requests':[]}
            def reviewer(img,prompt):
                states['reviewer']+=1
                return {'decision':'insufficient_evidence','reason':'Only synthetic drawings provided',
                        'missing_evidence':'Real exterior photograph'}
            result=run_trial(root,'writer:3b','reviewer:2b',writer=writer,reviewer=reviewer,with_video=True)
            self.assertEqual(result['status'],'SYNTHETIC_TRIAL_COMPLETE_UNVERIFIED',result)
            self.assertEqual(result['autonomous_zoom_request_count'],1)
            self.assertEqual(result['autonomous_video_still_count'],1)
            self.assertGreaterEqual(result['technical_review_items'],2)
            self.assertFalse(result['customer_release_allowed'])
            self.assertFalse(result['real_model_invocations_completed'])
            self.assertGreater(states['reviewer'],0)
