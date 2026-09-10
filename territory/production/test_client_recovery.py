"""Real crypto with a controlled in-memory GitHub boundary; not visual approval."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import client as c
import sealed
import transport as t

class Interrupted(BaseException): pass

class MemoryGitHub:
    def __init__(self, root):
        self.root=root; self.objects={}; self.commits=[]; self.reads=[]
        self.server=sealed.new_key(); self.fail=None; self.auto_result=True; self.inputs=0
    def read(self,path):
        self.reads.append(path)
        if path not in self.objects: raise t.MissingObject('not yet available')
        return copy.deepcopy(self.objects[path])
    def commit(self,files,message):
        is_request=any('/requests/' in n or '/visual-requests/' in n for n in files)
        is_input=any('/inputs/' in n for n in files)
        if is_input and self.fail=='before_input':
            self.fail=None; raise Interrupted()
        self.objects.update(copy.deepcopy(files)); self.commits.append(copy.deepcopy(files))
        if is_request:
            request=next(iter(files.values())); session=request['session']
            visual='client_public' in request
            ready={'version':1,'session':session}
            ready.update({'server_public':sealed.public(self.server),'expires':c.time.time()+600} if visual else
                         {'public_key':sealed.public(self.server),'expires_at':c.time.time()+600})
            self.objects['territory/transport/sessions/'+session+('/ready.json' if visual else '/public.json')]=ready
            if self.fail=='after_request': self.fail=None; raise Interrupted()
        if is_input:
            self.inputs+=1
            if self.auto_result: self.produce_result()
            if self.fail=='after_input': self.fail=None; raise Interrupted()
        return '0'*40
    def produce_result(self,unused=None):
        name=next(n for n in self.objects if '/inputs/' in n and n.endswith('/manifest.json'))
        session=name.split('/')[-2]
        envelope=t.receive_envelope(session,'inputs')
        raw=sealed.unseal(envelope,self.server,session,'job')
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            job=Path(directory)/'job'; sealed.unpack(raw,job)
            assert (job/'job.json').read_text()=='{"private":"do-not-publish"}'
            result=Path(directory)/'result'; result.mkdir()
            (result/'CHECKPOINT.json').write_text('{"release_ready":false,"synthetic":true}')
            (result/'evidence.txt').write_text('An authenticated test return, not a territory card.')
            request=next(v for n,v in self.objects.items() if '/requests/' in n or '/visual-requests/' in n)
            receiver=request.get('client_public',request.get('reply_public_key'))
            t.send_envelope(sealed.seal(sealed.pack(result),receiver,session,'result'),'outputs')

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.job=self.root/'job'; self.job.mkdir()
        (self.job/'job.json').write_text('{"private":"do-not-publish"}')
        self.output=self.root/'output'; self.cp=c.checkpoint_for(self.output)
        self.backend=MemoryGitHub(self.root)
        self.addCleanup(patch.stopall)
        patch.object(t,'read',self.backend.read).start(); patch.object(t,'commit',self.backend.commit).start()
    def start(self,kind='candidates'):
        self.state=c.prepare(self.job,self.output,self.cp,kind); return self.state
    def resume(self):
        self.state=c.load(self.cp,self.output); return c.advance(self.state,self.cp)
    def finish(self):
        self.start(); c.advance(self.state,self.cp); self.assertEqual(self.resume(),'received')
    def test_candidate_round_trip(self):
        self.finish(); self.assertEqual(self.backend.inputs,1); self.assertFalse(json.loads((self.output/'CHECKPOINT.json').read_text())['release_ready'])
    def test_visual_round_trip(self):
        self.start('visual'); c.advance(self.state,self.cp); self.assertEqual(self.resume(),'received'); self.assertEqual(self.backend.inputs,1)
    def test_checkpoint_private_from_creation(self):
        self.start(); self.assertEqual(self.cp.stat().st_mode & 0o777,0o600)
    def test_checkpoint_inside_job_refused(self):
        with self.assertRaises(c.RecoveryError): c.prepare(self.job,self.job/'out',self.job/'key.json','candidates')
    def test_plaintext_and_private_key_never_published(self):
        self.finish(); text=json.dumps(self.backend.commits)
        self.assertNotIn('do-not-publish',text); self.assertNotIn(self.state['private_key'],text)
    def test_interruption_after_request_no_duplicate(self):
        self.start(); self.backend.fail='after_request'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        self.resume(); self.resume()
        self.assertEqual(sum(any('/requests/' in n for n in commit) for commit in self.backend.commits),1)
    def test_interruption_after_input_no_duplicate(self):
        self.start(); self.backend.fail='after_input'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        self.assertEqual(self.resume(),'received'); self.assertEqual(self.backend.inputs,1)
    def test_uncertain_input_reuses_exact_ciphertext(self):
        self.start(); self.backend.fail='before_input'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        saved=c.read_json(self.cp)['envelope']; self.resume()
        self.assertEqual(saved,t.receive_envelope(self.state['session'],'inputs'))
    def test_uploaded_input_without_result_is_not_repeated(self):
        self.start(); self.backend.auto_result=False; self.backend.fail='after_input'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        self.assertEqual(self.resume(),'awaiting_result'); self.assertEqual(self.backend.inputs,1)
    def test_completed_result_recovers_when_job_missing(self):
        self.start(); c.advance(self.state,self.cp)
        (self.job/'job.json').unlink(); self.job.rmdir()
        self.assertEqual(self.resume(),'received')
    def test_changed_input_before_upload_rejected(self):
        self.start(); (self.job/'job.json').write_text('different')
        with self.assertRaises(c.RecoveryError): c.advance(self.state,self.cp)
        self.assertFalse(self.backend.commits)
    def test_mismatched_public_key_rejected(self):
        self.start(); self.state['client_public']=sealed.public(sealed.new_key()); c.atomic_json(self.cp,self.state)
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_other_output_path_rejected(self):
        self.start()
        with self.assertRaises(c.RecoveryError): c.load(self.cp,self.root/'other')
    def test_other_job_path_rejected(self):
        self.start()
        with self.assertRaises(c.RecoveryError): c.load(self.cp,self.output,self.root/'other')
    def test_other_job_kind_rejected(self):
        self.start()
        with self.assertRaises(c.RecoveryError): c.load(self.cp,self.output,kind='visual')
    def test_checkpoint_inventory_tampering_rejected(self):
        self.start(); self.state['inputs']['job.json']='0'*64; c.atomic_json(self.cp,self.state)
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_symlink_checkpoint_rejected(self):
        self.start(); saved=self.root/'saved'; self.cp.rename(saved); self.cp.symlink_to(saved)
        with self.assertRaises(c.RecoveryError): self.resume()
    @unittest.skipUnless(os.name=='posix','POSIX-specific permission check')
    def test_insecure_checkpoint_not_opened(self):
        self.start(); self.cp.chmod(0o644)
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_existing_output_not_overwritten(self):
        self.start(); self.output.mkdir(); (self.output/'keep.txt').write_text('keep')
        with self.assertRaises(c.RecoveryError): self.resume()
        self.assertEqual((self.output/'keep.txt').read_text(),'keep')
    def test_delivered_output_verified_on_each_resume(self):
        self.finish(); (self.output/'evidence.txt').write_text('changed')
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_completed_resume_needs_no_remote_reads(self):
        self.finish(); self.backend.reads=[]; self.assertEqual(self.resume(),'received'); self.assertEqual(self.backend.reads,[])
    def test_interruption_after_atomic_output_install_recovers(self):
        self.start(); c.advance(self.state,self.cp); real=c.atomic_json
        def fail(path,state):
            if state.get('phase')=='received': raise Interrupted()
            return real(path,state)
        with patch.object(c,'atomic_json',fail):
            with self.assertRaises(Interrupted): self.resume()
        self.assertEqual(c.read_json(self.cp)['phase'],'delivery_prepared')
        self.assertEqual(self.resume(),'received'); self.assertEqual(self.backend.inputs,1)
    def test_changed_remote_request_rejected(self):
        self.start(); self.backend.fail='after_request'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        path=next(n for n in self.backend.objects if '/requests/' in n)
        self.backend.objects[path]['reply_public_key']=sealed.public(sealed.new_key())
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_expired_worker_preserves_session(self):
        self.start(); self.backend.fail='after_request'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        path=next(n for n in self.backend.objects if n.endswith('/public.json')); self.backend.objects[path]['expires_at']=0
        with self.assertRaises(c.RecoveryError): self.resume()
        self.assertEqual(c.read_json(self.cp)['session'],self.state['session']); self.assertEqual(self.backend.inputs,0)
    def test_changed_worker_key_refused_after_preparation(self):
        self.start(); self.backend.fail='before_input'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        path=next(n for n in self.backend.objects if n.endswith('/public.json')); self.backend.objects[path]['public_key']=sealed.public(sealed.new_key())
        with self.assertRaises(c.RecoveryError): self.resume()
    def test_terminal_failure_retains_key(self):
        self.start(); self.backend.objects['territory/transport/sessions/'+self.state['session']+'/status.json']={'session':self.state['session'],'status':'failed'}
        with self.assertRaises(c.RecoveryError): self.resume()
        self.assertEqual(c.read_json(self.cp)['private_key'],self.state['private_key'])
    def test_auth_error_not_mistaken_for_missing_object(self):
        self.start()
        with patch.object(t,'read',side_effect=t.TransportError('authorization unavailable')):
            with self.assertRaises(t.TransportError): self.resume()
        self.assertFalse(self.backend.commits)
    def test_two_process_locks_cannot_own_one_checkpoint(self):
        with c.exclusive(self.cp):
            with self.assertRaises(c.RecoveryError):
                with c.exclusive(self.cp): pass
    def test_legacy_key_recovers_existing_authenticated_result_only(self):
        self.start(); c.advance(self.state,self.cp)
        c.atomic_json(self.cp,{k:self.state[k] for k in ('session','private_key')})
        self.assertEqual(self.resume(),'received'); self.assertTrue(c.read_json(self.cp)['legacy_result_only']); self.assertEqual(self.backend.inputs,1)
    def test_legacy_key_never_resubmits_unbound_input(self):
        self.start(); self.backend.fail='after_request'
        with self.assertRaises(Interrupted): c.advance(self.state,self.cp)
        c.atomic_json(self.cp,{k:self.state[k] for k in ('session','private_key')})
        with self.assertRaises(c.RecoveryError): self.resume()
        self.assertEqual(self.backend.inputs,0)

class WireTests(unittest.TestCase):
    def setUp(self):
        self.key=sealed.new_key(); self.session=sealed.new_session(); self.env=sealed.seal(b'bounded test payload',sealed.public(self.key),self.session,'job')
    def test_current_wire_format_roundtrip(self):
        self.assertEqual(t.validate_envelope(self.env,'inputs'),self.env)
        self.assertEqual(sealed.unseal(self.env,self.key,self.session,'job'),b'bounded test payload')
    def test_prior_wrong_header_is_rejected_before_upload(self):
        wrong={k:v for k,v in self.env.items() if k not in ('sender','receiver')}; wrong.update(suite='X25519-HKDF-SHA256-AES256GCM',ephemeral_public=self.env['sender'])
        with patch.object(t,'commit') as commit:
            with self.assertRaises(t.ProtocolError): t.send_envelope(wrong,'inputs')
            commit.assert_not_called()
    def test_wrong_direction_is_rejected(self):
        with self.assertRaises(t.ProtocolError): t.validate_envelope(self.env,'outputs')
    def test_bool_version_is_rejected(self):
        self.env['version']=True
        with self.assertRaises(t.ProtocolError): t.validate_envelope(self.env,'inputs')
    def test_invalid_nonce_is_rejected(self):
        self.env['nonce']=sealed.b64(b'short')
        with self.assertRaises(t.ProtocolError): t.validate_envelope(self.env,'inputs')
    def test_invalid_base64_is_rejected(self):
        self.env['ciphertext']='bad*base64'
        with self.assertRaises(t.ProtocolError): t.validate_envelope(self.env,'inputs')
    def test_wrong_header_stops_before_part_reads(self):
        with patch.object(t,'read',return_value={'envelope':{'suite':'wrong'},'parts':[],'ciphertext_sha256':'x'}) as read:
            with self.assertRaises(t.ProtocolError): t.receive_envelope(self.session,'inputs')
            self.assertEqual(read.call_count,1)
    def test_manifest_with_missing_part_is_not_pending(self):
        data=self.env['ciphertext']; header={k:v for k,v in self.env.items() if k!='ciphertext'}
        manifest={'envelope':header,'parts':[{'name':'part-0000.json','sha256':c.digest(data.encode())}],'ciphertext_sha256':c.digest(data.encode())}
        with patch.object(t,'read',side_effect=[manifest,t.MissingObject('missing')]):
            with self.assertRaises(t.ProtocolError): t.receive_envelope(self.session,'inputs')
    def test_http404_has_distinct_type(self):
        with patch.object(t.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='gh: Not Found (HTTP 404)',stdout='')):
            with self.assertRaises(t.MissingObject): t.api('repos/'+t.REPO+'/contents/test')
    def test_http403_not_missing(self):
        with patch.object(t.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='Forbidden (HTTP 403)',stdout='')):
            with self.assertRaises(t.TransportError) as error: t.api('repos/'+t.REPO+'/contents/test')
            self.assertNotIsInstance(error.exception,t.MissingObject)
    def test_dot_parent_suffix_rejected(self):
        with self.assertRaises(t.TransportError): t.safe_path('territory/transport/inputs/'+self.session+'/..')


class WorkerRecoveryTests(unittest.TestCase):
    """Actual worker control flow; model inference is explicitly mocked."""
    def setUp(self):
        import importlib.util
        import sys
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.session=sealed.new_session(); self.key=sealed.new_key()
        self.event=self.root/'event.json'; self.event.write_text(json.dumps({'repository':{'private':False,'full_name':t.REPO},'sender':{'login':'ksolo21-web'}}))
        self.identity={'test_only':True}; self.records=[]
        self.stub=SimpleNamespace(neural=SimpleNamespace(model_identity=lambda:self.identity),run=self.review)
        spec=importlib.util.spec_from_file_location('_worker_under_test',Path(__file__).with_name('visual_worker.py'))
        self.worker=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'visual_review':self.stub}): spec.loader.exec_module(self.worker)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ,{'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':t.REPO,'GITHUB_REF':'refs/heads/'+t.BRANCH,'GITHUB_EVENT_PATH':str(self.event),'RUNNER_TEMP':str(self.root),'GITHUB_RUN_ID':'mock-controller-test'}).start()
        patch.object(self.worker.engine,'verify_skills',return_value={'verified_files':138}).start()
        patch.object(t,'read',return_value={'version':1,'session':self.session,'client_public':sealed.public(self.key)}).start()
        patch.object(t,'commit',side_effect=lambda files,message:self.records.append(copy.deepcopy(files))).start()
        self.job=self.root/'source'; self.job.mkdir(); (self.job/'job.json').write_text('{}')
        self.model_calls=0
    def review(self,job,output,identity):
        self.model_calls+=1; output.mkdir(); (output/'calibration.json').write_text('{"mock":true,"release_ready":false}')
    def incoming(self,*args):
        record=next(v for f in self.records for n,v in f.items() if n.endswith('/ready.json'))
        return sealed.seal(sealed.pack(self.job),record['server_public'],self.session,'job')
    def failure(self,error):
        import io
        from contextlib import redirect_stdout
        stream=io.StringIO()
        with redirect_stdout(stream):
            with self.assertRaises(type(error)): self.worker.run(self.session)
        self.assertNotIn('PRIVATE-SENTINEL',stream.getvalue())
        return next(v for f in reversed(self.records) for n,v in f.items() if n.endswith('/status.json'))
    def test_malformed_input_is_not_polled_until_timeout(self):
        error=t.ProtocolError('PRIVATE-SENTINEL')
        with patch.object(t,'receive_envelope',side_effect=error) as receive,patch.object(self.worker.time,'sleep') as sleep:
            report=self.failure(error); self.assertEqual(receive.call_count,1); sleep.assert_not_called()
        self.assertEqual(report['stage'],'receive_input'); self.assertEqual(report['code'],'protocol_error'); self.assertEqual(self.model_calls,0)
    def test_missing_manifest_waits_then_real_crypto_return_succeeds(self):
        attempts=iter([False,True]); sent=[]
        def receive(*args):
            if not next(attempts): raise t.MissingObject('not ready')
            return self.incoming()
        with patch.object(t,'receive_envelope',side_effect=receive),patch.object(t,'send_envelope',side_effect=lambda envelope,direction:sent.append(envelope)),patch.object(self.worker.time,'sleep') as sleep:
            result=self.worker.run(self.session); self.assertEqual(sleep.call_count,1)
        self.assertFalse(result['release_ready']); self.assertEqual(self.model_calls,1)
        raw=sealed.unseal(sent[0],self.key,self.session,'result'); target=self.root/'received'; sealed.unpack(raw,target)
        self.assertEqual(json.loads((target/'calibration.json').read_text()),{'mock':True,'release_ready':False})
    def test_model_failure_reports_stage_without_private_exception(self):
        error=RuntimeError('PRIVATE-SENTINEL')
        with patch.object(self.stub.neural,'model_identity',side_effect=error): report=self.failure(error)
        self.assertEqual(report['stage'],'verify_local_model'); self.assertEqual(self.model_calls,0)
    def test_authenticated_payload_failure_is_distinct(self):
        def corrupted(*args):
            value=self.incoming(); raw=bytearray(sealed.unb64(value['ciphertext'])); raw[0]^=1; value['ciphertext']=sealed.b64(bytes(raw)); return value
        with patch.object(t,'receive_envelope',side_effect=corrupted): report=self.failure(sealed.EnvelopeError('expected'))
        self.assertEqual(report['code'],'authentication_error'); self.assertEqual(report['stage'],'authenticate_input')
    def test_private_temporary_files_removed_after_review_failure(self):
        error=RuntimeError('PRIVATE-SENTINEL')
        with patch.object(t,'receive_envelope',side_effect=self.incoming),patch.object(self.stub,'run',side_effect=error): report=self.failure(error)
        self.assertEqual(report['stage'],'visual_review'); self.assertEqual(list(self.root.glob('territory-visual-*')),[])
    def test_private_repository_never_starts_or_writes(self):
        self.event.write_text(json.dumps({'repository':{'private':True},'sender':{'login':'ksolo21-web'}}))
        with self.assertRaises(RuntimeError): self.worker.run(self.session)
        self.assertEqual(self.records,[]); self.assertEqual(self.model_calls,0)
    def test_wrong_owner_never_starts_or_writes(self):
        self.event.write_text(json.dumps({'repository':{'private':False,'full_name':t.REPO},'sender':{'login':'untrusted'}}))
        with self.assertRaises(RuntimeError): self.worker.run(self.session)
        self.assertEqual(self.records,[])
    def test_expired_window_has_safe_terminal_status(self):
        with patch.object(self.worker.time,'time',side_effect=[0,1201]): report=self.failure(TimeoutError('expected'))
        self.assertEqual(report['code'],'input_window_expired'); self.assertEqual(self.model_calls,0)
    def test_candidate_worker_advertises_actual_input_window(self):
        import worker
        request={'version':1,'session':self.session,'reply_public_key':sealed.public(self.key),'created_at':c.time.time()}
        start=c.time.time()
        with patch.object(t,'read',return_value=request),patch.object(t,'api',return_value=[{'author':{'login':'ksolo21-web'}}]),patch.object(t,'receive_envelope',side_effect=t.ProtocolError('bad')),patch.object(worker.time,'sleep') as sleep:
            with self.assertRaises(t.ProtocolError): worker.run(self.session)
            sleep.assert_not_called()
        ready=next(v for f in self.records for n,v in f.items() if n.endswith('/public.json'))
        self.assertGreaterEqual(ready['expires_at']-start,899); self.assertLess(ready['expires_at']-start,901)

if __name__=='__main__': unittest.main()
