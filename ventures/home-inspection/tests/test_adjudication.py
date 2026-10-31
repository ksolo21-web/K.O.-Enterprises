"""Controlled memory/Q03 integration. No live AI or inspection accuracy claim."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from inspection_engine.agents import execute_specialists
from inspection_engine.adjudication import entries,memory_context,build_queue,adjudicate,validate_record,ollama_reasoner
from inspection_engine.critic import review_specialist_dossier
from inspection_engine.core import DataError,sha256,blockers

SOURCE=Path(__file__).resolve().parents[1]/'examples/v05_photo_from_video'


def feature(description='Visible illustrative wall finish, material unknown',location='Front wall',bbox=None):
    return {'type':'feature','system':'exterior','feature_code':'cladding_type','description':description,
            'location':location,'status':'partially_observed','bbox':bbox}


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        shutil.copyfile(SOURCE/'demo_exterior.png',self.root/'photo.png')
        self.doc={'project_id':'SYNTHETIC-LEDGER','property':{'label':'Synthetic','inspection_date':'2026-10-31','synthetic':True},
            'media':[{'id':'P1','kind':'photo','path':'photo.png','area':'exterior','sha256':sha256(self.root/'photo.png')}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}

    def staged(self,two=False):
        candidates=[feature()]
        if two:candidates.append(feature(location='Rear wall',bbox=[.5,.5,.9,.9]))
        return execute_specialists(self.doc,self.root,lambda i,p:{'candidates':candidates,'requests':[]},
                                   media_ids=['P1'],provider_id='writer')

    def technical(self,document,dossier,decision='visually_plausible'):
        return review_specialist_dossier(document,self.root,dossier,lambda i,p:{'decision':decision,
            'reason':'Visible candidate remains unverified' if decision=='visually_plausible' else 'Named feature not visually established',
            'missing_evidence':'' if decision=='visually_plausible' else 'Inspector close-up of the wall material'},
            reviewer_id='Q02',provider_id='visual-reviewer')

    def reply(self,prompt,schema):
        packet=json.loads(prompt.split('LEDGER_PACKET_JSON: ')[1])
        return {'decisions':[{'entry_id':e['entry_id'],'decision':'distinct','related_ids':[],
                              'reason':'No reconciliation issue identified in controlled test','evidence_gap':''}
                             for e in packet['queue']['entries']]}

    def test_prior_records_are_present_in_next_model_call_without_mutation(self):
        document,_=self.staged();snapshot=copy.deepcopy(document);seen=[]
        def model(image,prompt):
            seen.append(json.loads(prompt.split('OBSERVATION_MEMORY_JSON: ')[1].splitlines()[0]))
            return {'candidates':[],'requests':[]}
        execute_specialists(document,self.root,model,media_ids=['P1'])
        self.assertEqual(seen[0]['records'][0]['description'],feature()['description'])
        self.assertEqual(document,snapshot)

    def test_existing_exact_observation_is_not_added_again(self):
        document,_=self.staged()
        with self.assertRaisesRegex(DataError,'already recorded'):
            execute_specialists(document,self.root,lambda i,p:{'candidates':[feature()],'requests':[]},media_ids=['P1'])
        self.assertEqual(len(document['observations']),1)

    def test_current_batch_is_shared_across_photo_work_orders(self):
        from PIL import Image
        Image.new('RGB',(320,240),'white').save(self.root/'photo2.png')
        self.doc['media'].append(dict(self.doc['media'][0],id='P2',path='photo2.png',sha256=sha256(self.root/'photo2.png')))
        seen=[]
        def model(image,prompt):
            seen.append(json.loads(prompt.split('OBSERVATION_MEMORY_JSON: ')[1].splitlines()[0]))
            return {'candidates':[feature()],'requests':[]}
        document,_=execute_specialists(self.doc,self.root,model,media_ids=['P1','P2'])
        self.assertEqual(seen[0]['relevant_total'],0);self.assertEqual(seen[1]['relevant_total'],1)
        self.assertEqual(len(document['observations']),2)
        self.assertTrue(build_queue(document)['potential_overlap_groups'])

    def test_reimported_identical_source_bytes_do_not_create_a_second_claim(self):
        self.doc['media'].append(dict(self.doc['media'][0],id='P2'))
        with self.assertRaisesRegex(DataError,'already recorded'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[feature()],'requests':[]},media_ids=['P1','P2'])

    def test_memory_byte_cap_omits_whole_records_and_keeps_full_snapshot(self):
        document,_=self.staged();document['observations'][0]['description']='x'*70000
        full=entries(document);memory=memory_context(document,[],['exterior'])
        self.assertEqual(len(json.dumps(memory,sort_keys=True).encode())<=6000,True)
        self.assertEqual(memory['records'],[]);self.assertEqual(memory['omitted_from_prompt'],1)
        self.assertEqual(len(full[0]['description']),70000)

    def test_context_window_omission_is_explicit_and_full_ledger_is_kept(self):
        document,_=self.staged()
        document['observations']=[dict(document['observations'][0],id=f'R{i}',description=f'Visible detail {i}') for i in range(8)]
        memory=memory_context(document,[],['exterior'])
        self.assertEqual(memory['relevant_total'],8);self.assertGreaterEqual(memory['omitted_from_prompt'],4)
        self.assertEqual(len(entries(document)),8)
        document['observations']*=17
        with self.assertRaisesRegex(DataError,'128'):entries(document)

    def test_new_zoom_view_can_corroborate_a_prior_claim_pending_adjudication(self):
        calls=[]
        def model(image,prompt):
            calls.append(1)
            return {'candidates':[feature()], 'requests':[{'kind':'zoom','bbox':[.1,.1,.8,.8]}] if len(calls)==1 else []}
        document,dossier=execute_specialists(self.doc,self.root,model,media_ids=['P1'])
        self.assertEqual(len(document['observations']),2)
        self.assertEqual(dossier['proposals'][1]['zoom_view_ids'],['Z0001'])
        self.assertTrue(document['adjudication_queue']['potential_overlap_groups'])

    def test_Q03_reads_Q02_reasons_and_cannot_override_hold_or_change_claims(self):
        document,dossier=self.staged();technical=self.technical(document,dossier,'insufficient_evidence');seen=[]
        before=copy.deepcopy(document)
        def model(prompt,schema):seen.append(prompt);return self.reply(prompt,schema)
        result=adjudicate(document,self.root,technical,model,provider_id='reasoner')
        self.assertIn('Inspector close-up of the wall material',seen[0])
        self.assertIn('Named feature not visually established',seen[0])
        self.assertEqual(result['status'],'ADJUDICATION_HOLD');self.assertTrue(result['held_entry_ids'])
        self.assertEqual(document,before);self.assertFalse(result['customer_release_allowed'])
        self.assertEqual(validate_record(document,result),result['held_entry_ids'])

    def test_distinct_components_can_reconcile_only_as_internal_draft(self):
        document,dossier=self.staged(two=True)
        result=adjudicate(document,self.root,self.technical(document,dossier),self.reply,provider_id='reasoner')
        self.assertEqual(len(result['decisions']),2);self.assertEqual(result['status'],'RECONCILED_INTERNAL_DRAFT')
        document['adjudication']=result
        self.assertFalse(any('Q03' in b for b in blockers(document)))
        self.assertTrue(any('human review' in b for b in blockers(document)))

    def test_empty_or_tampered_saved_decisions_cannot_clear_Q03_hold(self):
        document,dossier=self.staged();technical=self.technical(document,dossier)
        result=adjudicate(document,self.root,technical,self.reply,provider_id='reasoner')
        for change in ({'decisions':[]},{'source_snapshot_sha256':'0'*64},{'customer_release_allowed':True}):
            broken=copy.deepcopy(result);broken.update(change);document['adjudication']=broken
            self.assertTrue(any('Q03' in b for b in blockers(document)))
        held=adjudicate(document,self.root,self.technical(document,dossier,'not_supported'),self.reply,provider_id='reasoner')
        held['held_entry_ids']=[];held['status']='RECONCILED_INTERNAL_DRAFT';held['decisions'][0]['Q02_hold_preserved']=False
        held['decisions'][0]['resolution']='INTERNAL_DRAFT_ONLY';document['adjudication']=held
        self.assertTrue(any('Q03' in b for b in blockers(document)))

    def test_deleting_cached_queue_cannot_bypass_adjudication_for_model_records(self):
        document,_=self.staged();document.pop('adjudication_queue')
        self.assertTrue(any('Q03' in b for b in blockers(document)))

    def test_evidence_hash_or_provenance_change_invalidates_saved_adjudication(self):
        document,dossier=self.staged();result=adjudicate(document,self.root,self.technical(document,dossier),self.reply,provider_id='reasoner')
        document['adjudication']=result;old=build_queue(document)['entry_snapshot_sha256']
        document['media'][0]['sha256']='a'*64
        self.assertNotEqual(build_queue(document)['entry_snapshot_sha256'],old)
        self.assertTrue(any('Q03' in b for b in blockers(document)))

    def test_Q03_must_cover_all_claims_and_reference_only_known_other_claims(self):
        document,dossier=self.staged(two=True);technical=self.technical(document,dossier)
        def omitted(prompt,schema):return {'decisions':[]}
        with self.assertRaisesRegex(DataError,'omitted'):adjudicate(document,self.root,technical,omitted,provider_id='reasoner')
        def bad_id(prompt,schema):
            value=self.reply(prompt,schema);value['decisions'][0].update(decision='possible_duplicate',related_ids=['invented'],evidence_gap='Verify component identity');return value
        with self.assertRaisesRegex(DataError,'related'):adjudicate(document,self.root,technical,bad_id,provider_id='reasoner')

    def test_possible_duplicates_remain_held_without_merging(self):
        document,dossier=self.staged(two=True)
        def model(prompt,schema):
            value=self.reply(prompt,schema);first,second=value['decisions']
            first.update(decision='possible_duplicate',related_ids=[second['entry_id']],evidence_gap='Inspector to identify whether these are the same wall')
            return value
        result=adjudicate(document,self.root,self.technical(document,dossier),model,provider_id='reasoner')
        self.assertEqual(result['status'],'ADJUDICATION_HOLD');self.assertFalse(result['physical_components_merged'])
        self.assertEqual(len(document['observations']),2)

    def test_writer_or_Q02_cannot_be_declared_Q03(self):
        document,dossier=self.staged();technical=self.technical(document,dossier)
        for identity in ('writer','visual-reviewer'):
            with self.assertRaisesRegex(DataError,'differ'):adjudicate(document,self.root,technical,self.reply,provider_id=identity)

    def test_pending_claim_without_bound_Q02_review_fails_before_reasoner(self):
        document,dossier=self.staged();technical=self.technical(document,dossier);technical['items'][0]['source_sha256']='a'*64
        calls=[]
        with self.assertRaisesRegex(DataError,'source-matched'):
            adjudicate(document,self.root,technical,lambda *a:calls.append(1),provider_id='reasoner')
        self.assertEqual(calls,[])

    def test_Q02_crop_hash_and_region_are_required_before_adjudication(self):
        calls=[]
        def writer(image,prompt):
            calls.append(1)
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.1,.1,.8,.8]}]} if len(calls)==1 else {'candidates':[feature()],'requests':[]}
        document,dossier=execute_specialists(self.doc,self.root,writer,media_ids=['P1'],provider_id='writer')
        technical=self.technical(document,dossier)
        for key,wrong in [('zoom_sha256','0'*64),('zoom_source_bbox',[0,0,1,1])]:
            bad=copy.deepcopy(technical);bad['items'][0][key]=wrong;seen=[]
            with self.assertRaisesRegex(DataError,'source-matched'):
                adjudicate(document,self.root,bad,lambda *a:seen.append(1),provider_id='reasoner')
            self.assertEqual(seen,[])

    def test_absent_source_hash_cannot_match_a_missing_Q02_hash(self):
        document,dossier=self.staged();technical=self.technical(document,dossier)
        document['media'][0].pop('sha256');technical['items'][0]['source_sha256']=None;seen=[]
        with self.assertRaisesRegex(DataError,'recorded source SHA256'):
            adjudicate(document,self.root,technical,lambda *a:seen.append(1),provider_id='reasoner')
        self.assertEqual(seen,[])

    def test_human_verified_records_are_retained_and_never_rewritten(self):
        document,dossier=self.staged();document['observations'][0]['review']='human_verified';before=copy.deepcopy(document)
        technical=self.technical(*self.staged());technical['items']=[]
        result=adjudicate(document,self.root,technical,self.reply,provider_id='reasoner')
        self.assertEqual(document,before);self.assertFalse(result['records_modified'])

    def test_text_reasoner_is_loopback_only_and_rejects_partial_completion(self):
        with patch('inspection_engine.local_runtime.local_json',return_value={'done':True,'done_reason':'stop','response':'{"decisions":[]}'}) as transport:
            self.assertEqual(ollama_reasoner('test',{},'reasoner:1'),{'decisions':[]})
            payload=transport.call_args.args[2];self.assertNotIn('images',payload)
        with patch('inspection_engine.local_runtime.local_json',return_value={'done':False,'response':'{"decisions":[]}'}):
            with self.assertRaisesRegex(DataError,'incomplete'):ollama_reasoner('test',{},'reasoner:1')

    def test_adjudication_CLI_writes_separate_review_and_held_project_without_human_approval(self):
        import io,sys
        from contextlib import redirect_stdout
        from inspection_engine.__main__ import main
        document,dossier=self.staged();technical=self.technical(document,dossier,'insufficient_evidence')
        project=self.root/'project.json';review=self.root/'technical.json'
        project.write_text(json.dumps(document));review.write_text(json.dumps(technical))
        out=self.root/'adjudication.json';out_project=self.root/'held.json'
        argv=['inspection_engine','agents-adjudicate',str(project),'--technical-review',str(review),
              '--reasoning-model','reasoner:1','--out',str(out),'--out-project',str(out_project)]
        with patch.object(sys,'argv',argv),patch('inspection_engine.__main__.ollama_reasoner',
             side_effect=lambda prompt,schema,model:self.reply(prompt,schema)),redirect_stdout(io.StringIO()):main()
        saved=json.loads(out_project.read_text());result=json.loads(out.read_text())
        self.assertEqual(result['status'],'ADJUDICATION_HOLD')
        self.assertTrue(any('Q03' in b for b in blockers(saved)))
        self.assertEqual(saved['observations'][0]['review'],'review_pending')
        self.assertEqual(json.loads(project.read_text()),document)


    def test_decoded_same_frame_is_rejected_and_new_file_is_rolled_back(self):
        from inspection_engine.capture import probe_video,video_frames
        shutil.copyfile(SOURCE/'synthetic_moving_house_view.mp4',self.root/'clip.mp4')
        self.doc['media']=[{'id':'V1','kind':'video','path':'clip.mp4','area':'exterior',
                            'sha256':sha256(self.root/'clip.mp4'),'capture':probe_video(self.root/'clip.mp4')}]
        frames=video_frames(self.doc,self.root,'V1',max_frames=2)
        current=frames[-1];self.assertEqual(current['timestamp_seconds'],3.5)
        before={p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(DataError,'decoded to the current'):
            execute_specialists(self.doc,self.root,lambda i,p:{'candidates':[],
                'requests':[{'kind':'video_still','timestamp_seconds':3.49}]},media_ids=[current['id']])
        after={p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(after,before)

    def test_subpixel_crop_changes_cannot_duplicate_the_same_native_region(self):
        from inspection_engine.zoom import create_zoom_views
        create_zoom_views(self.doc,self.root,'P1',[[.1001,.1001,.8001,.8001]])
        before={p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()};calls=[]
        def model(image,prompt):
            calls.append(1)
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.1002,.1002,.8002,.8002]}]}
        with self.assertRaisesRegex(DataError,'already saved native pixels'):
            execute_specialists(self.doc,self.root,model,media_ids=['P1'])
        self.assertEqual(calls,[1]);self.assertEqual(len(self.doc['zoom_views']),1)
        self.assertEqual({p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()},before)

    def test_distinct_uniform_native_regions_remain_available_despite_equal_crop_hash(self):
        from PIL import Image
        from inspection_engine.zoom import create_zoom_views
        Image.new('RGB',(200,200),'white').save(self.root/'photo.png');self.doc['media'][0]['sha256']=sha256(self.root/'photo.png')
        create_zoom_views(self.doc,self.root,'P1',[[.1,.1,.4,.4]])
        calls=[]
        def model(image,prompt):
            calls.append(1)
            return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.5,.5,.8,.8]}] if len(calls)==1 else []}
        document,_=execute_specialists(self.doc,self.root,model,media_ids=['P1'])
        first,second=document['zoom_views']
        self.assertEqual(first['sha256'],second['sha256']);self.assertNotEqual(first['pixel_bbox'],second['pixel_bbox'])
        self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
