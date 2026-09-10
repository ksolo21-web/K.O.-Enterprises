import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import engine,privacy,sealed
class PrivacyTests(unittest.TestCase):
    def test_plain_data_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as t,self.assertRaises(ValueError):
            with privacy.authenticated_session(Path(t),b'not authenticated'):pass
    def test_proof_cannot_be_constructed(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.AuthenticatedPayload(b'fake')
    def test_authenticated_payload_type(self):
        k=sealed.new_key();s=sealed.new_session();e=sealed.seal(b'test',sealed.public(k),s,'job')
        self.assertIsInstance(sealed.unseal(e,k,s,'job'),sealed.AuthenticatedPayload)
    def test_plain_ci_still_blocked(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),self.assertRaises(engine.GateError):engine.private_guard()
    def test_scoped_local_authorization(self):
        k=sealed.new_key();s=sealed.new_session();e=sealed.seal(b'test',sealed.public(k),s,'job');payload=sealed.unseal(e,k,s,'job')
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            self.assertFalse(privacy.active())
            with privacy.authenticated_session(Path(t),payload):self.assertTrue(privacy.active())
            self.assertFalse(privacy.active())
    def test_exception_cleans_authorization(self):
        k=sealed.new_key();s=sealed.new_session();payload=sealed.unseal(sealed.seal(b'test',sealed.public(k),s,'job'),k,s,'job')
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            try:
                with privacy.authenticated_session(Path(t),payload):raise RuntimeError('test')
            except RuntimeError:pass
            self.assertFalse(privacy.active())
    def test_valid_confined_ci_session(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'source';src.mkdir();(src/'test.json').write_text('{}')
            k=sealed.new_key();s=sealed.new_session();payload=sealed.unseal(sealed.seal(sealed.pack(src),sealed.public(k),s,'job'),k,s,'job')
            target=root/'job';sealed.unpack(payload,target)
            event=root/'event.json';event.write_text(json.dumps({'repository':{'full_name':'ksolo21-web/K.O.-Enterprises','private':False},'sender':{'login':'ksolo21-web'}}))
            env={'GITHUB_ACTIONS':'true','RUNNER_TEMP':str(root),'GITHUB_EVENT_PATH':str(event),'GITHUB_REF':'refs/heads/territory-card-production'}
            with patch.dict(os.environ,env):
                with privacy.authenticated_session(target,payload):engine.private_guard()
                with self.assertRaises(engine.GateError):engine.private_guard()
    def test_private_repo_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);job=root/'job';job.mkdir();k=sealed.new_key();s=sealed.new_session();payload=sealed.unseal(sealed.seal(b'data',sealed.public(k),s,'job'),k,s,'job')
            event=root/'event.json';event.write_text(json.dumps({'repository':{'full_name':'ksolo21-web/K.O.-Enterprises','private':True},'sender':{'login':'ksolo21-web'}}))
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'true','RUNNER_TEMP':str(root),'GITHUB_EVENT_PATH':str(event),'GITHUB_REF':'refs/heads/territory-card-production'}),self.assertRaises(ValueError):
                with privacy.authenticated_session(job,payload):pass
if __name__=='__main__':unittest.main()
