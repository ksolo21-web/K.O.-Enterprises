"""Controlled evidence and regression checks; never live model inference."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from inspection_engine.core import DataError
from scripts.run_local_live_trial import run_trial, _distinct_video_sample_frames
from scripts.trial_evidence import tool_review_evidence


def feature(code='cladding_type'):
    return {'type':'feature','system':'exterior','feature_code':code,
            'status':'partially_observed','description':'Visible synthetic facade',
            'location':'front','bbox':[.1,.1,.8,.8]}


class FailedTrialEvidenceTests(unittest.TestCase):
    def test_invalid_feature_retains_exact_untrusted_answer_and_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'trial'
            wrong={'candidates':[feature('invented_feature')],'requests':[]}
            result=run_trial(root,'writer','reviewer',writer=lambda *a:wrong,
                             reviewer=lambda *a:{},with_video=False)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertIn('Feature code must belong',result['error'])
            request=json.loads((root/'invocations/0001-writer.request.json').read_text())
            reply=json.loads((root/'invocations/0001-writer.response.json').read_text())
            self.assertEqual(reply['structured_response_untrusted'],wrong)
            self.assertEqual(reply['status'],'RETURNED_UNVALIDATED_DATA')
            self.assertEqual(hashlib.sha256((root/'invocations'/request['image_path']).read_bytes()).hexdigest(),request['image_sha256'])
            self.assertEqual(hashlib.sha256(request['prompt'].encode()).hexdigest(),request['prompt_sha256'])
            schema=request['generation_schema']
            self.assertEqual(hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest(),request['generation_schema_sha256'])
            self.assertIn('feature_code',schema['properties']['candidates']['items']['anyOf'][0]['required'])
            self.assertEqual(reply['execution_kind'],'controlled_test')
            self.assertEqual(result['invocation_audit']['completed_live_calls'],{'writer':0,'reviewer':0})
            self.assertFalse((root/'technical_review.json').exists())
            self.assertFalse(result['customer_release_allowed'])

    def test_rejected_reviewer_output_is_preserved_without_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'trial'
            result=run_trial(root,'writer','reviewer',
                writer=lambda *a:{'candidates':[feature()],'requests':[]},
                reviewer=lambda *a:{'approved':True},with_video=False)
            self.assertEqual(result['status'],'BLOCKED')
            reply=json.loads((root/'invocations/0002-reviewer.response.json').read_text())
            self.assertEqual(reply['structured_response_untrusted'],{'approved':True})
            self.assertFalse(result['real_model_invocations_completed'])
            self.assertFalse(result['customer_release_allowed'])

    def test_provider_error_leaves_a_request_and_error_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'trial'
            def fail(*args):raise DataError('Controlled transport failure')
            result=run_trial(root,'writer','reviewer',writer=fail,reviewer=lambda *a:{},with_video=False)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertTrue((root/'invocations/0001-writer.request.json').exists())
            reply=json.loads((root/'invocations/0001-writer.response.json').read_text())
            self.assertEqual(reply['status'],'PROVIDER_ERROR')
            self.assertNotIn('structured_response_untrusted',reply)


class ToolReviewLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name,color in [('initial.png','red'),('selected.png','blue')]:
            Image.new('RGB',(80,80),color).save(self.root/name)
        self.doc={'media':[
            {'id':'F0','path':'initial.png','sha256':'a'*64,'derived_from_id':'V1','timestamp_seconds':0.0},
            {'id':'P1','path':'selected.png','sha256':'b'*64,'derived_from_id':'V1','timestamp_seconds':2.5,
             'capture_origin':'selected_video_still'}],
            'zoom_views':[{'id':'Z1','media_id':'F0'}]}
        self.dossier={'events':[
            {'invocation_id':'request-zoom','media_id':'F0','request_count':1,'candidate_count':0},
            {'invocation_id':'read-zoom','media_id':'F0','zoom_id':'Z1','request_count':0,'candidate_count':1},
            {'invocation_id':'request-still','media_id':'F0','request_count':1,'candidate_count':0},
            {'invocation_id':'read-still','media_id':'P1','request_count':0,'candidate_count':1}],
            'tool_requests':[
                {'kind':'zoom','status':'EXECUTED','zoom_id':'Z1','invocation_id':'request-zoom','requested_from_media_id':'F0'},
                {'kind':'video_still','status':'EXECUTED','photo_id':'P1','invocation_id':'request-still','requested_from_media_id':'F0'}],
            'proposals':[
                {'evidence_id':'F0','zoom_view_ids':['Z1'],'invocation_id':'read-zoom','description':'Zoom detail','work_order':'WO1'},
                {'evidence_id':'P1','zoom_view_ids':[],'invocation_id':'read-still','description':'Later detail','work_order':'WO2'}]}
        self.review={'items':[
            {'source_media_id':'F0','source_sha256':'a'*64,'zoom_id':'Z1','proposal_description':'Zoom detail','work_order':'WO1'},
            {'source_media_id':'P1','source_sha256':'b'*64,'zoom_id':None,'proposal_description':'Later detail','work_order':'WO2'}]}

    def evidence(self):
        return tool_review_evidence(self.doc,self.dossier,self.review,self.root,_distinct_video_sample_frames)

    def test_linked_post_tool_proposals_and_reviews_are_counted(self):
        r=self.evidence()
        self.assertEqual(r['reviewed_zoom_ids'],['Z1'])
        self.assertEqual(r['visibly_changed_reviewed_video_still_ids'],['P1'])

    def test_aggregate_execution_with_only_original_claim_review_is_insufficient(self):
        self.dossier['proposals']=[{'evidence_id':'F0','zoom_view_ids':[],
            'invocation_id':'request-zoom','description':'Original claim','work_order':'WO1'}]
        self.dossier['events'][0]['candidate_count']=1
        self.review['items']=[{'source_media_id':'F0','source_sha256':'a'*64,
            'zoom_id':None,'proposal_description':'Original claim','work_order':'WO1'}]
        r=self.evidence()
        self.assertEqual(r['reviewed_zoom_ids'],[])
        self.assertEqual(r['reviewed_video_still_ids'],[])

    def test_wrong_review_hash_cannot_verify_still(self):
        self.review['items'][1]['source_sha256']='c'*64
        self.assertEqual(self.evidence()['reviewed_video_still_ids'],[])

    def test_missing_post_tool_invocation_cannot_verify_zoom(self):
        self.dossier['proposals'][0].pop('invocation_id')
        self.assertEqual(self.evidence()['reviewed_zoom_ids'],[])

    def test_reselected_start_frame_is_not_temporal_progress(self):
        self.doc['media'][1]['timestamp_seconds']=0.0
        r=self.evidence()
        self.assertEqual(r['reviewed_video_still_ids'],['P1'])
        self.assertEqual(r['temporally_distinct_reviewed_video_still_ids'],[])

    def test_different_timestamp_with_unchanged_pixels_is_not_changed_content(self):
        Image.new('RGB',(80,80),'red').save(self.root/'selected.png')
        r=self.evidence()
        self.assertEqual(r['temporally_distinct_reviewed_video_still_ids'],['P1'])
        self.assertEqual(r['visibly_changed_reviewed_video_still_ids'],[])

    def test_tool_must_link_to_the_model_request_event(self):
        self.dossier['tool_requests'][0]['invocation_id']='invented-call'
        self.assertEqual(self.evidence()['reviewed_zoom_ids'],[])

    def test_unrelated_work_order_review_cannot_verify_tool(self):
        self.review['items'][0]['work_order']='UNRELATED'
        self.assertEqual(self.evidence()['reviewed_zoom_ids'],[])

    def test_different_source_video_is_not_temporal_progress(self):
        self.doc['media'][1]['derived_from_id']='V2'
        self.assertEqual(self.evidence()['temporally_distinct_reviewed_video_still_ids'],[])
