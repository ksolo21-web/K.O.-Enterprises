"""Deterministic M2 agent work-order and evidence-contract tests; no live model."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from inspection_engine.agents import ROLES, SYSTEM_OWNER, ROLE_BY_ID, plan_specialists, execute_specialists, _review_dossier
from inspection_engine.core import DataError, SYSTEM_NAME, sha256, blockers, validate_project

SOURCE=Path(__file__).resolve().parents[1]/'examples'/'v05_photo_from_video'

class SpecialistTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='m2_specialists_')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        source=SOURCE/'demo_exterior.png'
        shutil.copyfile(source,self.root/'photo.png')
        self.doc={'project_id':'DEMO-ROLE-TEST',
                  'property':{'label':'Synthetic test house','inspection_date':'2026-10-30',
                              'synthetic':True,'qualified_reviewer':None},
                  'media':[{'id':'P0001','kind':'photo','path':'photo.png','area':'exterior',
                            'sha256':sha256(self.root/'photo.png')}],
                  'observations':[],'findings':[],'equipment':[],'limitations':[]}
    def _feature(self,system='exterior',bbox=None):
        return {'type':'feature','system':system,'feature_code':'cladding_type',
                'description':'Visible illustrative exterior wall finish, material unconfirmed',
                'location':'Front elevation','status':'partially_observed','bbox':bbox}
    def test_roles_cover_all_13_systems_once(self):
        self.assertEqual(set(SYSTEM_OWNER),set(SYSTEM_NAME))
        self.assertEqual(len(SYSTEM_OWNER),sum(len(x.systems) for x in ROLES))
        self.assertEqual(len(ROLES),8)
        self.assertEqual(SYSTEM_OWNER['hvac'],'T08')
        self.assertEqual(SYSTEM_OWNER['water_heating'],'T07')
    def test_plan_routes_by_inspector_label_only(self):
        out=plan_specialists(self.doc,['P0001'])
        self.assertEqual(out['jobs'][0]['assigned_to'],'T03')
        self.assertEqual(out['jobs'][0]['systems'],['exterior'])
        self.assertFalse(out['jobs'][0]['release_authority'])
    def test_job_budget_cannot_be_expanded(self):
        with self.assertRaises(DataError):plan_specialists(self.doc,max_jobs=9999)
    def test_unrecognized_area_requires_triage(self):
        self.doc['media'][0]['area']='unknown_cabinet'
        plan=plan_specialists(self.doc)
        self.assertFalse(plan['jobs'])
        self.assertEqual(plan['unassigned_media'][0]['media_id'],'P0001')
    def test_raw_video_not_treated_as_checked(self):
        self.doc['media'][0]['kind']='video';self.doc['media'][0]['path']='photo.mp4'
        plan=plan_specialists(self.doc)
        self.assertFalse(plan['jobs']);self.assertEqual(len(plan['unreviewed_videos']),1)
    def test_unknown_and_duplicate_evidence_rejected(self):
        with self.assertRaises(DataError):plan_specialists(self.doc,['MISSING'])
        with self.assertRaises(DataError):plan_specialists(self.doc,['P0001','P0001'])
    def test_execution_creates_pending_project_and_evidence_dossier(self):
        def provider(image,prompt):
            self.assertIn('ROLE T03',prompt)
            self.assertIn('Delegated systems: ["exterior"]',prompt)
            return {'candidates':[self._feature(bbox=[.1,.1,.3,.3])],'requests':[]}
        updated, dossier=execute_specialists(self.doc,self.root,provider,media_ids=['P0001'])
        self.assertEqual(len(updated['observations']),1)
        self.assertEqual(updated['observations'][0]['review'],'review_pending')
        self.assertEqual(updated['observations'][0]['evidence_ids'],['P0001'])
        self.assertTrue(dossier['review']['Q01']['passed'])
        self.assertTrue(dossier['review']['Q02']['passed'])
        self.assertFalse(dossier['customer_release_allowed'])
        self.assertTrue(blockers(updated))
        self.assertEqual(self.doc['observations'],[])
    def test_specialist_prompt_enumerates_only_delegated_feature_codes(self):
        prompts=[]
        def model(image,prompt):
            prompts.append(prompt)
            return {'candidates':[],'requests':[]}
        execute_specialists(self.doc,self.root,model,media_ids=['P0001'])
        self.assertEqual(len(prompts),1)
        self.assertIn('"exterior": ["cladding_type", "flashing_openings", "trim_decks_and_attached_features"]',prompts[0])
        self.assertIn('For type=feature, choose feature_code exactly',prompts[0])
        self.assertIn('for type=potential_concern, omit feature_code',prompts[0])
        self.assertNotIn('"foundation_type"',prompts[0])

    def test_invalid_model_feature_code_is_never_silently_corrected(self):
        def model(image,prompt):
            return {'candidates':[dict(self._feature(),feature_code='made_up_cladding_label')],
                    'requests':[]}
        with self.assertRaisesRegex(DataError,'Feature code must belong'):
            execute_specialists(self.doc,self.root,model,media_ids=['P0001'])

    def test_specialist_cannot_make_other_roles_claims(self):
        with self.assertRaisesRegex(DataError,'outside delegated systems'):
            execute_specialists(self.doc,self.root,lambda image,prompt:{
                'candidates':[{'type':'potential_concern','system':'electrical',
                    'description':'Possible exposed conductors','location':'unknown',
                    'status':'observed'}], 'requests':[]},media_ids=['P0001'])
    def test_specialist_cannot_assert_no_defects(self):
        with self.assertRaises(DataError):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[
                dict(self._feature(),description='No issues found, fully safe')],
                'requests':[]},media_ids=['P0001'])
    def test_unknown_provider_action_rejected(self):
        with self.assertRaisesRegex(DataError,'Unsupported specialist'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[],
                'requests':[{'kind':'delete_file','path':'photo.png'}]},media_ids=['P0001'])
    def test_missing_evidence_hash_fails_before_model_access(self):
        self.doc['media'][0].pop('sha256')
        calls=[]
        with self.assertRaisesRegex(DataError,'recorded SHA-256'):
            execute_specialists(self.doc,self.root,lambda i,p:calls.append(p) or {},media_ids=['P0001'])
        self.assertEqual(calls,[])
    def test_plan_only_video_stops_before_model_call(self):
        shutil.copyfile(SOURCE/'synthetic_moving_house_view.mp4',self.root/'clip.mp4')
        self.doc['media'][0]['kind']='video'
        self.doc['media'][0]['path']='clip.mp4'
        self.doc['media'][0]['sha256']=sha256(self.root/'clip.mp4')
        with self.assertRaisesRegex(DataError,'No specialist work orders'):
            execute_specialists(self.doc,self.root,lambda i,p:{},media_ids=['P0001'])
    def test_agent_cannot_ask_for_video_still_from_standalone_photo(self):
        with self.assertRaisesRegex(DataError,'standalone'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[],
                'requests':[{'kind':'video_still','timestamp_seconds':1.0}]},media_ids=['P0001'])
    def test_zoom_actual_pixels_and_evidence_mapping(self):
        calls=[]
        def provider(img,prompt):
            calls.append(len(img))
            if len(calls)==1:
                return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.15,.2,.48,.55]}]}
            return {'candidates':[self._feature(bbox=[.2,.2,.8,.8])],'requests':[]}
        updated,dossier=execute_specialists(self.doc,self.root,provider,media_ids=['P0001'])
        self.assertEqual(len(calls),2)
        self.assertEqual(len(updated['zoom_views']),1)
        self.assertEqual(updated['observations'][0]['zoom_view_ids'],['Z0001'])
        self.assertEqual(updated['observations'][0]['evidence_ids'],['P0001'])
        self.assertEqual(dossier['tool_requests'][0]['status'],'EXECUTED')
        self.assertTrue(all(x['passed'] for x in dossier['review'].values()))
        self.assertFalse(dossier['customer_release_allowed'])
    def test_zoom_cannot_repeat_full_view(self):
        with self.assertRaisesRegex(DataError,'unchanged or enlarged'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[],
                'requests':[{'kind':'zoom','bbox':[0,0,1,1]}]},media_ids=['P0001'])
    def test_zoom_requires_native_pixels(self):
        with self.assertRaisesRegex(DataError,'fewer than 2'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[],
                'requests':[{'kind':'zoom','bbox':[.1,.1,.10000001,.10000001]}]},media_ids=['P0001'])
    def test_agent_iteration_budget(self):
        calls=[]
        def provider(i,p):
            calls.append(p)
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.2,.2,.8,.8]}]}
        updated,dossier=execute_specialists(self.doc,self.root,provider,media_ids=['P0001'])
        self.assertEqual(len(calls),3)
        self.assertEqual(len(updated['zoom_views']),2)
        self.assertEqual(dossier['tool_requests'][-1]['status'],'DENIED_BUDGET')
    def test_review_fails_if_source_hash_changed_in_dossier(self):
        updated,dossier=execute_specialists(self.doc,self.root,lambda i,p:{
              'candidates':[self._feature()],'requests':[]},media_ids=['P0001'])
        dossier['proposals'][0]['evidence_sha256']='0'*64
        self.assertFalse(_review_dossier(dossier,updated,self.root)['Q01']['passed'])
    def test_provider_attempts_self_approval_is_ignored(self):
        with self.assertRaises(DataError):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[self._feature()],
                'requests':[],'approved':True},media_ids=['P0001'])
    def test_empty_proposal_is_not_marked_complete(self):
        updated,dossier=execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[], 'requests':[]},media_ids=['P0001'])
        self.assertEqual(len(updated['observations']),0)
        self.assertFalse(dossier['customer_release_allowed'])
        self.assertGreater(len(blockers(updated)),0)

class VideoStillSpecialistTest(unittest.TestCase):
    def test_model_requests_native_video_still_then_reviews_it(self):
        with tempfile.TemporaryDirectory(prefix='m2_video_') as rootstr:
            root=Path(rootstr)
            source=SOURCE/'synthetic_moving_house_view.mp4'
            shutil.copyfile(source,root/'tour.mp4')
            from inspection_engine.capture import probe_video, video_frames
            doc={'project_id':'M2-VIDEO-SYNTHETIC',
                 'property':{'label':'Fake test house','inspection_date':'2026-10-30','synthetic':True},
                 'media':[{'id':'V0001','kind':'video','path':'tour.mp4','area':'exterior',
                          'sha256':sha256(root/'tour.mp4'),'capture':probe_video(root/'tour.mp4')}],
                 'observations':[],'findings':[],'equipment':[],'limitations':[]}
            samples=video_frames(doc,root,'V0001',max_frames=2)
            calls=[]
            def provider(img,prompt):
                calls.append(prompt)
                if len(calls)==1:return {'candidates':[],
                    'requests':[{'kind':'video_still','timestamp_seconds':1.0}]}
                return {'candidates':[{'type':'feature','system':'exterior',
                    'feature_code':'cladding_type','description':'Illustrative facade shown in frame',
                    'location':'Front elevation','status':'partially_observed',
                    'bbox':[.1,.1,.8,.8]}], 'requests':[]}
            updated,dossier=execute_specialists(doc,root,provider,media_ids=[samples[0]['id']])
            self.assertEqual(len(calls),2)
            self.assertEqual(len([m for m in updated['media'] if m.get('capture_origin')=='selected_video_still']),1)
            derived=next(m for m in updated['media'] if m.get('capture_origin')=='selected_video_still')
            self.assertIn(derived['id'],updated['observations'][0]['evidence_ids'])
            self.assertTrue(dossier['review']['Q01']['passed'])
            self.assertTrue(dossier['review']['Q02']['passed'])
            self.assertFalse(dossier['customer_release_allowed'])

if __name__=='__main__':unittest.main()
