"""Controlled providers + real Ed25519/temp-store execution. No real keys/models."""
import copy
import json
from pathlib import Path
import tempfile
import time
import os
import threading
import io
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from PIL import Image

from inspection_engine.core import DataError,sha256
from inspection_engine.report_review_queue import digest
from inspection_engine.report_study_pipeline import prepare_study,main as pipeline_main
from inspection_engine.report_proposals import propose_report,loopback_provider
from inspection_engine.report_learning_candidate import freeze_evaluation
from inspection_engine import lesson_activation as activation
from inspection_engine import bounded_generation
from inspection_engine.agents import execute_specialists
from scripts.build_m3_study_demo import prepare_demo
import test_m3_completion_v7 as legacy_completion
REAL_PAUSE=activation.repository_paused


def controlled_page(req,queue):
    if req['kind']=='ADJACENT_PAGE_RELATIONSHIPS':return {'relations':[]}
    n=req['pages'][0]
    answer={'sections':[],'tables':[],'figures':[],'findings':[]}
    if n==2:
        answer['figures']=[{'id':'FIG','kind':'unclassified','region':{'kind':'image_region','page':2,'bbox':[0,0,1,1]},'caption_anchors':[]}]
    else:
        span=next(s for s in queue['spans'] if s['page']==n)
        anchor={'kind':'pdf_text','page':n,'span_id':span['span_id'],'offset':0,'quote':span['text'][:25]}
        answer['sections']=[{'id':'S','title':'Report section','anchors':[anchor]}]
        answer['findings']=[{'id':'F','system':'roof' if n==1 else 'plumbing','location':f'Source page {n}',
            'description':f'Reported source page {n}','anchors':[anchor],'section_ids':['S'],'figure_ids':[],'table_cell_ids':[]}]
    return answer


class AutomaticActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.b,cls.r,cls.q,cls.pdf,_=prepare_demo(cls.root/'report',with_ocr=True)
        prepare_study(cls.b,cls.r,cls.pdf,cls.root/'prepared',ocr=True,batch_size=2)
        cls.training=legacy_completion.LearningLifecycleTests('test_version_lineage_rollback_never_activates');cls.training.setUp()
        cls.c1=cls.training.build();cls.c2=cls.training.build(2,cls.c1)
        photo=cls.root/'holdout.png';Image.new('RGB',(40,40),'blue').save(photo)
        cls.hold_doc={'project_id':cls.b['case_id'],'property':{'label':'Synthetic holdout','inspection_date':'2026-11-02','synthetic':True},
            'media':[{'id':'H1','kind':'photo','path':photo.name,'area':'roof','sha256':sha256(photo)}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}
        cls.labels=[{'case_id':cls.b['case_id'],'expected':[
            {'system':'roof','location':'Source page 1','description':'Reported source page 1','critical':True},
            {'system':'plumbing','location':'Source page 3','description':'Reported source page 3','critical':False}]}]
        cls.run1,cls.ev1=cls.evaluation(cls.c1);cls.run2,cls.ev2=cls.evaluation(cls.c2)

    @classmethod
    def tearDownClass(cls):cls.training.doCleanups();cls.tmp.cleanup()

    @classmethod
    def evaluation(cls,candidate):
        plan=freeze_evaluation(candidate,[{'bundle':cls.b,'registry':cls.r,'document':cls.hold_doc,
            'root':cls.root,'reference_path':cls.pdf}])
        benchmark=activation.freeze_benchmark(candidate,plan,cls.labels)
        def provider(request):
            assert activation.staged_candidate_context(candidate) in request['prompt']
            assert '"critical"' not in request['prompt']
            return controlled_page(request,cls.q)
        run=propose_report(cls.b,cls.r,cls.pdf,cls.root/'prepared',provider,
            provider_id='CONTROLLED-SYNTHETIC-PROVIDER',model_digest='a'*64,max_calls=5,
            benchmark_sha256=benchmark['benchmark_sha256'],candidate=candidate)
        return run,activation.evaluate_benchmark(candidate,benchmark,[run])

    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.store_root=Path(t.name)
        self.owner=Ed25519PrivateKey.generate();self.reviewer=Ed25519PrivateKey.generate()
        def key(k,role):return {'public_key_hex':k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex(),
            'roles':[role],'revoked':False,'expires_at':int(time.time())+3600}
        self.policy={'kind':'M3_LOCAL_LESSON_TRUST_POLICY_V8','namespace':'SYNTHETIC-TEST-ONLY','task_scope':'report_interpretation','activation_enabled':True,
            'keys':{'O':key(self.owner,'owner'),'R':key(self.reviewer,'reviewer')},
            'limits':{'minimum_cases':1,'maximum_false_positives':0,'maximum_false_negatives':0,'maximum_critical_false_negatives':0}}
        self.policy_path=self.store_root/'policy.json';self.save_policy()
        self.store=self.store_root/'store';activation.initialize_store(self.store,self.policy_path)
        pause=patch.object(activation,'repository_paused',return_value=False);pause.start();self.addCleanup(pause.stop)

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.policy));self.policy_path.chmod(0o600)

    def request(self,candidate=None,evaluation=None,*,action='promote',nonce='1'*32,target=None):
        return activation.activation_request(self.store,self.policy_path,candidate or self.c1,evaluation or self.ev1,
            action=action,nonce=nonce,expires_at=int(time.time())+120,target_pack=target)

    def signatures(self,req):
        return [{'key_id':key,'role':role,'signature_hex':signer.sign(activation._signing_bytes(req)).hex()}
            for key,role,signer in [('O','owner',self.owner),('R','reviewer',self.reviewer)]]

    def apply(self,candidate=None,evaluation=None,request=None,approvals=None):
        req=request or self.request(candidate,evaluation)
        return activation.apply_operation(self.store,self.policy_path,candidate or self.c1,evaluation or self.ev1,req,
            approvals if approvals is not None else self.signatures(req))

    def test_automatic_proposals_are_source_validated_not_human_review(self):
        m=self.run1['mapping'];self.assertEqual(m['origin'],'model_proposed')
        self.assertEqual(m['kind'],'MODEL_PROPOSED_REPORT_UNDERSTANDING_V8')
        self.assertEqual([f['id'] for f in m['findings']],['P0001-F','P0003-F'])
        self.assertEqual(m['unresolved_pages'],[1,2,3]);self.assertEqual(len(self.run1['calls']),5)
        self.assertFalse(self.run1['human_review_performed']);self.assertFalse(self.run1['field_accuracy_verified'])

    def test_budget_blocks_before_any_model_call(self):
        seen=[]
        with self.assertRaises(DataError):propose_report(self.b,self.r,self.pdf,self.root/'prepared',
            lambda r:seen.append(r),provider_id='CONTROLLED',model_digest='a'*64,max_calls=2)
        self.assertEqual(seen,[])

    def test_invented_quote_and_unseen_page_stop_early(self):
        for field,value in [('quote','FABRICATED'),('page',3)]:
            seen=[]
            def bad(req):
                seen.append(req);answer=controlled_page(req,self.q)
                answer['sections'][0]['anchors'][0][field]=value;return answer
            with self.subTest(field=field),self.assertRaises(DataError):
                propose_report(self.b,self.r,self.pdf,self.root/'prepared',bad,provider_id='CONTROLLED',model_digest='a'*64,max_calls=5)
            self.assertEqual(len(seen),1)

    def test_model_cannot_supply_reviewed_or_activation_flags(self):
        def bad(req):return dict(controlled_page(req,self.q),reviewer_authenticated=True)
        with self.assertRaises(DataError):propose_report(self.b,self.r,self.pdf,self.root/'prepared',bad,
            provider_id='CONTROLLED',model_digest='a'*64,max_calls=5)

    def test_loopback_pin_and_completed_generation_contract(self):
        req={'prompt':'synthetic','images':[{'png':b'PNG'}],'schema':{}}
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[{'name':'model:tag','digest':'a'*64}]}), \
                patch('inspection_engine.report_proposals.generate',return_value={'done':True,'done_reason':'stop',
                'response':'{"sections":[],"tables":[],"figures":[],"findings":[]}'}) as transport:
            result=loopback_provider('model:tag','a'*64,timeout=181)(req)
            self.assertEqual(result['sections'],[]);self.assertGreater(transport.call_args.kwargs['timeout'],180)
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[]}):
            with self.assertRaises(DataError):loopback_provider('model:tag','a'*64)(req)

    def test_real_signed_promote_load_second_version_and_rollback(self):
        first=self.apply();data,sha=activation.runtime_lesson_context(self.store,self.policy_path,model_digest='a'*64,task_scope='report_interpretation')
        self.assertEqual(sha,first['active_pack']);self.assertIn('Original evidence first',data)
        second=self.apply(self.c2,self.ev2,self.request(self.c2,self.ev2,nonce='2'*32))
        req=self.request(action='rollback',nonce='3'*32,target=first['active_pack'])
        back=self.apply(request=req)
        self.assertEqual(back['active_pack'],first['active_pack']);self.assertNotEqual(second['active_pack'],back['active_pack'])
        self.assertFalse(back['weights_modified']);self.assertFalse(back['professional_qualifications_verified'])
        self.assertFalse(back['customer_release_allowed'])
        self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in self.store.rglob('*') if p.is_file()))

    def test_real_repo_pause_blocks_mutation_and_consumption(self):
        with patch.object(activation,'repository_paused',return_value=True):
            with self.assertRaises(DataError):self.apply()
            with self.assertRaises(DataError):activation.runtime_lesson_context(self.store,self.policy_path,model_digest='a'*64,task_scope='report_interpretation')

    def test_default_disabled_policy_blocks_signed_promotion(self):
        self.policy['activation_enabled']=False;self.save_policy()
        with self.assertRaises(DataError):self.apply()

    def test_store_initialization_failure_leaves_no_half_store(self):
        target=self.store_root/'failed-init'
        with patch('inspection_engine.lesson_activation._write_new',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):activation.initialize_store(target,self.policy_path)
        self.assertFalse(target.exists())

    def test_signer_aliases_do_not_fake_independent_review(self):
        self.policy['keys']['R']['public_key_hex']=self.policy['keys']['O']['public_key_hex'];self.save_policy()
        req=self.request();approvals=self.signatures(req)
        approvals[1]['signature_hex']=self.owner.sign(activation._signing_bytes(req)).hex()
        with self.assertRaises(DataError):self.apply(request=req,approvals=approvals)

    def test_missing_signature_wrong_role_revocation_expiry_reject(self):
        req=self.request();approvals=self.signatures(req)
        with self.assertRaises(DataError):self.apply(request=req,approvals=approvals[:1])
        approvals[1]['signature_hex']='0'*128
        with self.assertRaises(DataError):self.apply(request=req,approvals=approvals)
        for change in ({'revoked':True},{'expires_at':1},{'roles':['owner']}):
            original=copy.deepcopy(self.policy['keys']['R']);self.policy['keys']['R'].update(change);self.save_policy()
            with self.assertRaises(DataError):self.apply()
            self.policy['keys']['R']=original;self.save_policy()

    def test_exact_approval_binding_and_stale_cas_replay_reject(self):
        req=self.request();approvals=self.signatures(req)
        changed=copy.deepcopy(req);changed['model_digest']='b'*64
        with self.assertRaises(DataError):self.apply(request=changed,approvals=approvals)
        self.apply(request=req,approvals=approvals)
        with self.assertRaises(DataError):self.apply(request=req,approvals=approvals)
        with self.assertRaises(DataError):self.apply(request=self.request(nonce=req['nonce']))

    def test_approval_cannot_replay_into_another_fresh_store(self):
        other=self.store_root/'other-store';activation.initialize_store(other,self.policy_path)
        req=self.request()
        with self.assertRaises(DataError):activation.apply_operation(other,self.policy_path,self.c1,self.ev1,req,self.signatures(req))

    def test_expired_approval_and_policy_substitution_reject(self):
        req=self.request();req['issued_at']=1;req['expires_at']=2
        with self.assertRaises(DataError):self.apply(request=req)
        req=self.request();approvals=self.signatures(req)
        self.policy['limits']['minimum_cases']=2;self.save_policy()
        with self.assertRaises(DataError):self.apply(request=req,approvals=approvals)

    def test_computed_misses_not_supplied_counts_block_promotion(self):
        run=copy.deepcopy(self.run1);run['mapping']['findings'].pop(0)
        run['mapping']['mapping_sha256']=digest({k:v for k,v in run['mapping'].items() if k!='mapping_sha256'})
        run['proposal_sha256']=digest({k:v for k,v in run.items() if k!='proposal_sha256'})
        ev=activation.evaluate_benchmark(self.c1,self.ev1['benchmark'],[run])
        self.assertEqual(ev['scores'][0]['critical_false_negatives'],1)
        with self.assertRaises(DataError):self.apply(evaluation=ev,request=self.request(evaluation=ev))

    def test_forged_evaluation_counts_and_unbound_benchmark_reject(self):
        ev=copy.deepcopy(self.ev1);ev['scores'][0]['true_positives']=999
        ev['evaluation_sha256']=digest({k:v for k,v in ev.items() if k!='evaluation_sha256'})
        with self.assertRaises(DataError):self.apply(evaluation=ev,request=self.request(evaluation=ev))
        run=copy.deepcopy(self.run1);run['benchmark_sha256']='f'*64
        run['proposal_sha256']=digest({k:v for k,v in run.items() if k!='proposal_sha256'})
        with self.assertRaises(DataError):activation.evaluate_benchmark(self.c1,self.ev1['benchmark'],[run])

    def test_baseline_run_cannot_approve_untested_candidate_lessons(self):
        run=copy.deepcopy(self.run1);run['evaluated_candidate_sha256']=None;run['candidate_context_sha256']=None
        run['proposal_sha256']=digest({k:v for k,v in run.items() if k!='proposal_sha256'})
        with self.assertRaisesRegex(DataError,'candidate lesson context'):
            activation.evaluate_benchmark(self.c1,self.ev1['benchmark'],[run])

    def test_mutated_pointer_and_unapproved_rollback_reject(self):
        self.apply()
        with self.assertRaises(DataError):self.apply(request=self.request(action='rollback',nonce='2'*32,target='b'*64))
        path=self.store/'state.json';state=json.loads(path.read_text());state['active_pack']='b'*64
        state['state_sha256']=digest({k:v for k,v in state.items() if k!='state_sha256'});path.write_text(json.dumps(state))
        with self.assertRaises(DataError):activation.runtime_lesson_context(self.store,self.policy_path,model_digest='a'*64,task_scope='report_interpretation')

    def test_atomic_failure_and_existing_lock_preserve_state(self):
        original=(self.store/'state.json').read_bytes();req=self.request();approvals=self.signatures(req)
        with patch('inspection_engine.lesson_activation.os.replace',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):self.apply(request=req,approvals=approvals)
        self.assertEqual((self.store/'state.json').read_bytes(),original)
        self.assertFalse((self.store/'activation.lock').exists())
        self.apply(request=req,approvals=approvals)
        (self.store/'activation.lock').touch()
        with self.assertRaises(OSError):self.apply(request=self.request(nonce='2'*32))
        self.assertTrue((self.store/'activation.lock').exists())

    def test_environment_stop_and_mid_operation_pause_reject(self):
        with patch('inspection_engine.lesson_activation.Path.exists',return_value=False):
            for value in ('true','1','typo'):
                with patch.dict(os.environ,{'COMPANY_OS_PAUSED':value}):self.assertTrue(REAL_PAUSE())
            with patch.dict(os.environ,{'COMPANY_OS_PAUSED':'false'}):self.assertFalse(REAL_PAUSE())
        original=(self.store/'state.json').read_bytes();req=self.request();approvals=self.signatures(req)
        with patch.object(activation,'repository_paused',side_effect=[False,True]):
            with self.assertRaises(DataError):self.apply(request=req,approvals=approvals)
        self.assertEqual((self.store/'state.json').read_bytes(),original)

    def test_pause_activated_during_provider_call_blocks_result(self):
        self.apply()
        def provider(request):os.environ['COMPANY_OS_PAUSED']='1';return controlled_page(request,self.q)
        provider.model_digest='a'*64
        with patch.dict(os.environ,{'COMPANY_OS_PAUSED':''}),patch.object(activation,'repository_paused',side_effect=lambda:bool(os.environ.get('COMPANY_OS_PAUSED'))):
            with self.assertRaises(DataError):propose_report(self.b,self.r,self.pdf,self.root/'prepared',provider,
                provider_id='CONTROLLED',model_digest='a'*64,max_calls=5,lesson_store=self.store,lesson_policy=self.policy_path)

    def test_runtime_consumer_injects_verified_data_without_releasing_case(self):
        active=self.apply();seen=[]
        pinned=loopback_provider('model:tag','a'*64)
        def transport(payload,**kw):
            seen.append(payload['prompt']);n=int(payload['prompt'].split('"physical_pdf_page": ')[1].split(',')[0].split('}')[0])
            kind='ADJACENT_PAGE_RELATIONSHIPS' if 'TASK: ADJACENT' in payload['prompt'] else 'PAGE_STRUCTURE'
            answer=controlled_page({'kind':kind,'pages':[n]},self.q)
            return {'done':True,'done_reason':'stop','response':json.dumps(answer)}
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[{'name':'model:tag','digest':'a'*64}]}), \
                patch('inspection_engine.report_proposals.generate',side_effect=transport):
            result=propose_report(self.b,self.r,self.pdf,self.root/'prepared',pinned,provider_id='CONTROLLED-PINNED-LOOPBACK',
                model_digest='a'*64,max_calls=5,lesson_store=self.store,lesson_policy=self.policy_path)
        self.assertIn('SUPPLEMENTAL_LESSON_DATA_JSON',seen[0])
        self.assertEqual(result['active_lesson_pack_sha256'],active['active_pack'])
        self.assertFalse(result['customer_release_allowed'])
        with self.assertRaises(DataError):activation.runtime_lesson_context(self.store,self.policy_path,model_digest='b'*64,task_scope='report_interpretation')
        with self.assertRaises(DataError):activation.runtime_lesson_context(self.store,self.policy_path,model_digest='a'*64,task_scope='photo_specialist')

    def test_complete_cli_freeze_propose_evaluate_sign_apply_load_and_consume(self):
        root=self.store_root
        for name,value in [('candidate.json',self.c1),('plan.json',self.ev1['benchmark']['plan']),('labels.json',self.labels)]:
            (root/name).write_text(json.dumps(value))
        def call(fn,args):
            output=io.StringIO()
            with redirect_stdout(output):code=fn(args)
            self.assertEqual(code,0,output.getvalue());return json.loads(output.getvalue())
        call(activation.main,['freeze-benchmark','--candidate',str(root/'candidate.json'),'--plan',str(root/'plan.json'),
            '--labels',str(root/'labels.json'),'--out',str(root/'benchmark.json')])
        def transport(payload,**kw):
            n=int(payload['prompt'].split('"physical_pdf_page": ')[1].split(',')[0].split('}')[0])
            kind='ADJACENT_PAGE_RELATIONSHIPS' if 'TASK: ADJACENT' in payload['prompt'] else 'PAGE_STRUCTURE'
            return {'done':True,'done_reason':'stop','response':json.dumps(controlled_page({'kind':kind,'pages':[n]},self.q))}
        base=['propose','--reference',str(self.root/'report/reference.json'),'--registry',str(self.root/'report/registry.json'),
            '--source-pdf',str(self.pdf),'--study-dir',str(self.root/'prepared'),'--model','model:tag','--model-digest','a'*64,'--max-calls','5']
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[{'name':'model:tag','digest':'a'*64}]}), \
                patch('inspection_engine.report_proposals.generate',side_effect=transport):
            call(pipeline_main,base+['--candidate',str(root/'candidate.json'),'--benchmark',str(root/'benchmark.json'),'--audit-dir',str(root/'private-model-audit'),'--out-dir',str(root/'proposals')])
        audit=json.loads((root/'private-model-audit/manifest.json').read_text())
        self.assertEqual(audit['status'],'COMPLETED')
        self.assertEqual(audit['event_count'],10)
        self.assertEqual(audit['events'][0]['kind'],'generation_request')
        self.assertEqual(audit['events'][1]['kind'],'generation_response')
        self.assertFalse(audit['customer_release_allowed'])
        from inspection_engine.proposal_evidence import verify_private_audit
        verified=verify_private_audit(root/'private-model-audit',root/'proposals/model-proposals.json')
        self.assertEqual(verified['model_calls_verified'],5)
        self.assertTrue(verified['request_response_integrity_verified'])
        self.assertFalse(verified['semantic_accuracy_verified'])
        recorded=root/'private-model-audit/0001-generation_request.json'
        original=recorded.read_bytes();recorded.write_bytes(original+b' ')
        with self.assertRaises(DataError):
            verify_private_audit(root/'private-model-audit',root/'proposals/model-proposals.json')
        recorded.write_bytes(original)
        (root/'runs.json').write_text(json.dumps([str(root/'proposals/model-proposals.json')]))
        call(activation.main,['evaluate','--candidate',str(root/'candidate.json'),'--benchmark',str(root/'benchmark.json'),
            '--runs',str(root/'runs.json'),'--out',str(root/'evaluation.json')])
        operation=['--store',str(self.store),'--policy',str(self.policy_path),'--candidate',str(root/'candidate.json'),
            '--evaluation',str(root/'evaluation.json')]
        call(activation.main,['request']+operation+['--action','promote','--nonce','7'*32,'--expires-at',str(int(time.time())+120),'--out',str(root/'request.json')])
        req=json.loads((root/'request.json').read_text());(root/'approvals.json').write_text(json.dumps(self.signatures(req)))
        call(activation.main,['apply']+operation+['--request',str(root/'request.json'),'--approvals',str(root/'approvals.json')])
        loaded=call(activation.main,['load','--store',str(self.store),'--policy',str(self.policy_path),
            '--model-digest','a'*64,'--task-scope','report_interpretation'])
        self.assertEqual(loaded['status'],'VERIFIED_PACK_LOADED');self.assertFalse(loaded['professional_qualifications_verified'])
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[{'name':'model:tag','digest':'a'*64}]}), \
                patch('inspection_engine.report_proposals.generate',side_effect=transport):
            call(pipeline_main,base+['--lesson-store',str(self.store),'--lesson-policy',str(self.policy_path),'--out-dir',str(root/'active-proposals')])
        consumed=json.loads((root/'active-proposals/model-proposals.json').read_text())
        self.assertEqual(consumed['active_lesson_pack_sha256'],loaded['active_pack'])


class BoundedTransportTests(unittest.TestCase):
    def setUp(self):
        class Handler(BaseHTTPRequestHandler):
            mode='complete';calls=0
            def log_message(self,*args):pass
            def do_GET(self):
                Handler.calls+=1
                if Handler.mode=='headers':self.server.release.wait(2)
                data=json.dumps({'models':[{'name':'synthetic'*40}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers()
                try:
                    if Handler.mode=='drip':
                        for char in data:
                            self.wfile.write(bytes([char]));self.wfile.flush()
                            if self.server.release.wait(.08):break
                    else:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):pass
            def do_POST(self):
                Handler.calls+=1;self.rfile.read(int(self.headers['Content-Length']))
                if Handler.mode=='headers':self.server.release.wait(2)
                if Handler.mode=='late_body':self.server.release.wait(.6)
                if Handler.mode=='redirect':
                    self.send_response(302);self.send_header('Location','https://invalid.example');self.end_headers();return
                data=json.dumps({'done':True,'value':'x'*200}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(data)+(10 if Handler.mode=='truncated' else 0)));self.end_headers()
                try:
                    if Handler.mode=='late_body':self.server.release.wait(2)
                    if Handler.mode=='drip':
                        for char in data:
                            self.wfile.write(bytes([char]));self.wfile.flush()
                            if self.server.release.wait(.08):break
                    else:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):pass
        self.handler=Handler;self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True;self.server.release=threading.Event()
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=patch.object(bounded_generation,'PORT',self.server.server_port);self.port.start()

    def tearDown(self):
        self.server.release.set();self.port.stop();self.server.shutdown();self.server.server_close();self.thread.join(2)

    def test_complete_request_supports_long_configured_deadline(self):
        self.assertTrue(bounded_generation.generate({'synthetic':True},timeout=181)['done'])
        self.assertEqual(self.handler.calls,1)

    def test_redirect_truncated_and_oversized_responses_block(self):
        for mode,budget in [('redirect',200000),('truncated',200000),('complete',128)]:
            self.handler.mode=mode
            with self.subTest(mode=mode),self.assertRaises(DataError):bounded_generation.generate({},timeout=2,max_bytes=budget)

    def test_absolute_deadline_stops_headers_and_continuous_drip(self):
        for mode in ('headers','drip'):
            self.handler.mode=mode;started=time.monotonic()
            with self.subTest(mode=mode),self.assertRaises(DataError):bounded_generation.generate({},timeout=1)
            self.assertLess(time.monotonic()-started,2.5)

    def test_metadata_preflight_has_absolute_deadline_too(self):
        for mode in ('headers','drip'):
            self.handler.mode=mode;started=time.monotonic()
            with self.subTest(mode=mode),self.assertRaises(DataError):bounded_generation.request_json('GET','/api/tags',timeout=1)
            self.assertLess(time.monotonic()-started,2.5)

    def test_http10_delayed_headers_then_stalled_body_has_one_deadline(self):
        self.handler.mode='late_body';started=time.monotonic()
        with self.assertRaises(DataError):bounded_generation.generate({},timeout=1)
        self.assertLess(time.monotonic()-started,1.8)


if __name__=='__main__':unittest.main()
