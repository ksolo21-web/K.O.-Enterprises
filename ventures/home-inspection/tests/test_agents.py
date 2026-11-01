"""Deterministic M2 agent work-order and evidence-contract tests; no live model."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from inspection_engine.agents import ROLES, SYSTEM_OWNER, ROLE_BY_ID, plan_specialists, execute_specialists, _review_dossier, specialist_schema
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

    def test_actual_a06_missing_feature_field_remains_rejected(self):
        # Exact rejected A06 answer: do not infer a feature code from description.
        answer={'candidates':[
            {'type':'feature','system':'exterior','description':'cladding_type','status':'unknown'},
            {'type':'feature','system':'exterior','description':'trim_decks_and_attached_features','status':'unknown'}],
            'requests':[{'kind':'zoom','bbox':[0,0,1,1]}]}
        with self.assertRaisesRegex(DataError,'Feature code must belong'):
            execute_specialists(self.doc,self.root,lambda i,p:answer,media_ids=['P0001'])
        self.assertEqual(self.doc['observations'],[])

    def test_exact_a08_repeated_candidates_block_before_any_tool_execution(self):
        path=Path(__file__).resolve().parents[1]/'docs/evidence/A08_REJECTED_WRITER_EVIDENCE.json'
        evidence=json.loads(path.read_text())
        raw=evidence['files']['request/response.json']['transport_response_untrusted']['response']
        answer=json.loads(raw)
        self.assertEqual(len(answer['candidates']),12)
        with self.assertRaisesRegex(DataError,'Duplicate indistinguishable'):
            execute_specialists(self.doc,self.root,lambda i,p:copy.deepcopy(answer),media_ids=['P0001'])
        self.assertFalse((self.root/'zoom_views').exists())
        self.assertEqual(self.doc['observations'],[])

    def test_separate_locations_and_crop_regions_are_not_silently_merged(self):
        first=self._feature(bbox=[.1,.1,.3,.3]);second=dict(first,location='Rear wall',bbox=[.6,.6,.9,.9])
        updated,dossier=execute_specialists(self.doc,self.root,lambda i,p:{
            'candidates':[first,second],'requests':[]},media_ids=['P0001'])
        self.assertEqual(len(updated['observations']),2)
        self.assertEqual([p['feature_code'] for p in dossier['proposals']],['cladding_type']*2)

    def test_schema_opt_in_reaches_actual_ollama_request(self):
        from unittest.mock import patch
        from inspection_engine.vision import ollama_local
        seen=[]
        def transport(method,path,request,**kw):
            seen.append(request)
            return {'done':True,'response':json.dumps({'candidates':[],'requests':[]})}
        with patch('inspection_engine.vision.local_json',transport):
            execute_specialists(self.doc,self.root,
                lambda image,prompt,*,schema:ollama_local(image,prompt,'test-model',schema=schema),
                media_ids=['P0001'],provider_accepts_schema=True)
        request=seen[0]
        schema=request['format']
        branches=schema['properties']['candidates']['items']['anyOf']
        features=[b for b in branches if b['properties']['type']['enum']==['feature']]
        self.assertEqual(len(features),1)
        self.assertIn('feature_code',features[0]['required'])
        self.assertEqual(features[0]['properties']['system']['enum'],['exterior'])
        self.assertIn('cladding_type',features[0]['properties']['feature_code']['enum'])
        self.assertNotIn('roof_covering',features[0]['properties']['feature_code']['enum'])
        concerns=[b for b in branches if b['properties']['type']['enum']==['potential_concern']]
        self.assertNotIn('feature_code',concerns[0]['properties'])
        self.assertFalse(concerns[0]['additionalProperties'])
        from inspection_engine.input_compaction import digest
        self.assertNotIn('OUTPUT_JSON_SCHEMA:',request['prompt'])
        self.assertIn('OUTPUT_GUIDE:',request['prompt'])
        grounded=request['prompt'].split('PROVIDER_SCHEMA_SHA256: ')[1].splitlines()[0]
        self.assertEqual(digest(schema),grounded)
        self.assertIn('observed|partially_observed|unknown',request['prompt'])
        self.assertIn('[0,0,1,1] is unchanged',request['prompt'])

    def test_work_order_cannot_claim_other_system_within_same_role(self):
        with self.assertRaisesRegex(DataError,'outside delegated systems'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[
                dict(self._feature(),system='roof',feature_code='roof_covering')],
                'requests':[]},media_ids=['P0001'])

    def test_invalid_schema_opt_in_stops_before_provider(self):
        calls=[]
        with self.assertRaisesRegex(DataError,'must be a boolean'):
            execute_specialists(self.doc,self.root,lambda *a:calls.append(a),
                media_ids=['P0001'],provider_accepts_schema=1)
        self.assertEqual(calls,[])

    def test_multi_system_schema_keeps_codes_coupled_and_actions_disjoint(self):
        from inspection_engine.descriptors import REQUIRED_FEATURES
        schema=specialist_schema(['plumbing','water_heating'],video_duration=4.0)
        for branch in schema['properties']['candidates']['items']['anyOf']:
            system=branch['properties']['system']['enum'][0]
            if branch['properties']['type']['enum']==['feature']:
                self.assertEqual(branch['properties']['feature_code']['enum'],list(REQUIRED_FEATURES[system]))
        actions=schema['properties']['requests']['items']['anyOf']
        self.assertEqual(actions[0]['required'],['kind','bbox'])
        self.assertNotIn('timestamp_seconds',actions[0]['properties'])
        self.assertEqual(actions[1]['required'],['kind','timestamp_seconds'])
        self.assertNotIn('bbox',actions[1]['properties'])
        self.assertEqual(actions[1]['properties']['timestamp_seconds']['exclusiveMaximum'],4.0)
        photo_actions=specialist_schema(['exterior'])['properties']['requests']['items']['anyOf']
        self.assertEqual(len(photo_actions),1)
        self.assertEqual(photo_actions[0]['properties']['kind']['enum'],['zoom'])
        for invalid in (0,-1,float('inf'),float('nan'),True):
            with self.assertRaises(DataError):specialist_schema(['exterior'],video_duration=invalid)

    def test_standalone_photo_context_never_invents_video_or_forces_tool(self):
        seen=[]
        def provider(image,prompt):
            seen.append(json.loads(prompt.split('EVIDENCE_CONTEXT_JSON: ')[1].splitlines()[0]))
            return {'candidates':[],'requests':[]}
        _,dossier=execute_specialists(self.doc,self.root,provider,media_ids=['P0001'])
        self.assertEqual(seen[0]['source_kind'],'standalone_photo')
        self.assertFalse(seen[0]['video_still_available'])
        self.assertNotIn('video_duration_seconds',seen[0])
        self.assertEqual(dossier['tool_requests'],[])

    def test_invalid_event_recorder_rejected_before_model(self):
        seen=[]
        with self.assertRaisesRegex(DataError,'recorder must be callable'):
            execute_specialists(self.doc,self.root,lambda *a:seen.append(a),
                                media_ids=['P0001'],audit_event='invalid')
        self.assertEqual(seen,[])

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
                context=json.loads(prompt.split('EVIDENCE_CONTEXT_JSON: ')[1].splitlines()[0])
                self.assertTrue(context['video_still_available'])
                self.assertEqual(context['source_video_id'],'V0001')
                self.assertEqual(context['video_duration_seconds'],4.0)
                self.assertEqual(context['current_source_timestamp_seconds'],0.0 if len(calls)==1 else 1.0)
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
