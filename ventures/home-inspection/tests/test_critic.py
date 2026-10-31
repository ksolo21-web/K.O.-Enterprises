"""M2 second-pass review tests: actual source pixels; controlled mock outputs."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from PIL import Image
from inspection_engine.agents import execute_specialists
from inspection_engine.critic import CRITIC_SCHEMA, review_specialist_dossier
from inspection_engine.core import DataError, sha256

SOURCE=Path(__file__).resolve().parents[1]/'examples'/'v05_photo_from_video'/'demo_exterior.png'

class CriticStageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='m2_critic_')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copyfile(SOURCE,self.root/'original.png')
        self.project={'project_id':'SYNTHETIC-SECOND-PASS',
            'property':{'label':'Synthetic test','inspection_date':'2026-10-30','synthetic':True},
            'media':[{'id':'P0001','path':'original.png','kind':'photo','area':'exterior',
                      'sha256':sha256(self.root/'original.png')}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}
        def proposal(i,p):
            return {'candidates':[{'type':'potential_concern','system':'exterior',
                 'description':'Possible stain near lower wall','status':'partially_observed',
                 'location':'Front wall','bbox':[.2,.1,.7,.8]}],'requests':[]}
        self.staged,self.dossier=execute_specialists(self.project,self.root,proposal,
                 media_ids=['P0001'],provider_id='writer-v1')

    def _review(self,reply=None,**opts):
        if reply is None:
            reply={'decision':'insufficient_evidence','reason':'Photo needs corroboration',
                   'missing_evidence':'Inspector to capture oblique view'}
        return review_specialist_dossier(self.staged,self.root,self.dossier,
                 lambda image,prompt:reply,reviewer_id='Q02',provider_id='critic-v2',**opts)

    def test_second_pass_runs_as_separate_call_with_image_and_prompt(self):
        calls=[]
        def provider(image,prompt):
            with Image.open(io.BytesIO(image)) as im:
                self.assertEqual(im.size,(1800,960))
            self.assertIn('CLAIM DATA:',prompt)
            self.assertIn('UNTRUSTED HYPOTHESIS',prompt)
            calls.append(1)
            return {'decision':'visually_plausible','reason':'Image may depict a dark mark',
                    'missing_evidence':''}
        out=review_specialist_dossier(self.staged,self.root,self.dossier,provider,
                           reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual(calls,[1]);self.assertEqual(out['decision_summary']['visually_plausible'],1)
        self.assertFalse(out['qualified_human_signed'])
        self.assertFalse(out['independent_runtime_verified'])
        self.assertFalse(out['customer_release_allowed'])
        self.assertEqual(self.staged['observations'],[])

    def test_distinct_provider_required(self):
        with self.assertRaisesRegex(DataError,'differ'):
            review_specialist_dossier(self.staged,self.root,self.dossier,lambda i,p:{},
                              reviewer_id='Q02',provider_id='writer-v1')

    def _feature_dossier(self):
        return execute_specialists(self.project,self.root,lambda i,p:{'candidates':[
            {'type':'feature','system':'exterior','feature_code':'cladding_type',
             'description':'Visible illustrative facade, material unknown','status':'partially_observed'}],
            'requests':[]},media_ids=['P0001'],provider_id='writer-v1')

    def test_feature_code_reaches_Q02_claim_and_review_record(self):
        staged,dossier=self._feature_dossier();seen=[]
        def reviewer(image,prompt):
            seen.append(json.loads(prompt.split('CLAIM DATA: ')[1]))
            self.assertIn('description addresses its assigned system and feature_code',prompt)
            return {'decision':'insufficient_evidence','reason':'Material not established',
                    'missing_evidence':'Inspector close-up and material verification'}
        review=review_specialist_dossier(staged,self.root,dossier,reviewer,reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual(seen[0]['feature_code'],'cladding_type')
        self.assertEqual(review['items'][0]['proposal_feature_code'],'cladding_type')
        self.assertFalse(review['customer_release_allowed'])

    def test_changed_allowed_feature_code_cannot_change_Q02_claim(self):
        staged,dossier=self._feature_dossier();dossier['proposals'][0]['feature_code']='flashing_openings';calls=[]
        with self.assertRaisesRegex(DataError,'not present'):
            review_specialist_dossier(staged,self.root,dossier,lambda i,p:calls.append(1),
                                      reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual(calls,[])

    def test_missing_feature_code_in_legacy_feature_dossier_fails_before_review(self):
        staged,dossier=self._feature_dossier();dossier['proposals'][0].pop('feature_code');calls=[]
        with self.assertRaisesRegex(DataError,'gate'):
            review_specialist_dossier(staged,self.root,dossier,lambda i,p:calls.append(1),
                                      reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual(calls,[])

    def test_distinct_locations_reach_Q02_and_remain_bound_to_staged_evidence(self):
        candidate={'type':'feature','system':'exterior','feature_code':'cladding_type',
                   'description':'Visible illustrative facade, material unknown','status':'partially_observed',
                   'location':'Front wall','bbox':[.1,.1,.3,.3]}
        second=dict(candidate,location='Rear wall',bbox=[.6,.6,.9,.9])
        staged,dossier=execute_specialists(self.project,self.root,lambda i,p:{
            'candidates':[candidate,second],'requests':[]},media_ids=['P0001'],provider_id='writer-v1')
        seen=[]
        def review(image,prompt):
            seen.append(json.loads(prompt.split('CLAIM DATA: ')[1]))
            return {'decision':'insufficient_evidence','reason':'Material unverified',
                    'missing_evidence':'Qualified inspection and new angle'}
        result=review_specialist_dossier(staged,self.root,dossier,review,reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual([c['location'] for c in seen],['Front wall','Rear wall'])
        self.assertEqual([c['candidate_source_bbox'] for c in seen],[candidate['bbox'],second['bbox']])
        self.assertEqual(len(result['items']),2)
        for key,wrong in [('location','Different location'),('bbox',[0,0,1,1])]:
            bad=copy.deepcopy(dossier);bad['proposals'][0][key]=wrong;calls=[]
            with self.assertRaisesRegex(DataError,'not present'):
                review_specialist_dossier(staged,self.root,bad,lambda i,p:calls.append(1),
                                          reviewer_id='Q02',provider_id='critic-v2')
            self.assertEqual(calls,[])

    def test_specialist_cannot_review_itself(self):
        with self.assertRaisesRegex(DataError,'Specialist'):
            review_specialist_dossier(self.staged,self.root,self.dossier,lambda i,p:{},
                              reviewer_id='T03',provider_id='critic-v2')

    def test_identity_mismatch_rejected(self):
        bad=copy.deepcopy(self.dossier);bad['project_id']='OTHER'
        with self.assertRaisesRegex(DataError,'match'):
            review_specialist_dossier(self.staged,self.root,bad,lambda i,p:{},
                              reviewer_id='Q02',provider_id='critic-v2')

    def test_source_tampering_rejected_before_model(self):
        (self.root/'original.png').write_bytes(b'TAMPER')
        calls=[]
        with self.assertRaises(DataError):
            review_specialist_dossier(self.staged,self.root,self.dossier,
                       lambda i,p:calls.append(1) or {},reviewer_id='Q02',provider_id='critic-v2')
        self.assertEqual(calls,[])

    def test_pending_followup_requires_specific_evidence(self):
        with self.assertRaisesRegex(DataError,'evidence gap'):
            self._review({'decision':'insufficient_evidence','reason':'Unclear','missing_evidence':''})

    def test_bad_decision_rejected(self):
        with self.assertRaisesRegex(DataError,'Invalid reviewer decision'):
            self._review({'decision':'compliant','reason':'Looks fine','missing_evidence':''})

    def test_critics_cannot_assert_certified_safe(self):
        with self.assertRaisesRegex(DataError,'conclusive'):
            self._review({'decision':'visually_plausible','reason':'Fully safe','missing_evidence':''})

    def test_critics_cannot_issue_actions(self):
        with self.assertRaisesRegex(DataError,'only'):
            self._review({'decision':'visually_plausible','reason':'Maybe','missing_evidence':'','run_shell':'rm -rf'})

    def test_evidence_missing_photo_rejected(self):
        bad=copy.deepcopy(self.dossier)
        bad['proposals'][0]['evidence_id']='MISSING'
        with self.assertRaises(DataError):
            review_specialist_dossier(self.staged,self.root,bad,lambda i,p:{},
                               reviewer_id='Q02',provider_id='critic-v2')

    def test_forged_proposal_fails_original_project_crosslink(self):
        bad=copy.deepcopy(self.dossier);bad['proposals'][0]['description']='New unsupported claim'
        with self.assertRaisesRegex(DataError,'not present'):
            review_specialist_dossier(self.staged,self.root,bad,lambda i,p:{},
                               reviewer_id='Q02',provider_id='critic-v2')

    def test_no_proposals_is_not_a_pass(self):
        bad=copy.deepcopy(self.dossier);bad['proposals']=[]
        with self.assertRaisesRegex(DataError,'1-48'):
            review_specialist_dossier(self.staged,self.root,bad,lambda i,p:{},
                               reviewer_id='Q02',provider_id='critic-v2')

    def test_cannot_bypass_original_scope_review(self):
        bad=copy.deepcopy(self.dossier)
        bad['proposals'][0]['assigned_to']='T08'
        with self.assertRaisesRegex(DataError,'gate'):
            review_specialist_dossier(self.staged,self.root,bad,lambda i,p:{},
                               reviewer_id='Q02',provider_id='critic-v2')

    def test_critic_preserves_unapproved_findings(self):
        output=self._review()
        self.assertEqual(self.staged['findings'][0]['review'],'review_pending')
        self.assertEqual(output['items'][0]['decision'],'insufficient_evidence')
        self.assertEqual(output['items'][0]['source_sha256'],self.staged['media'][0]['sha256'])

if __name__=='__main__':unittest.main()
