"""Activation orchestration tests: mocked models are never real inference."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from inspection_engine.core import DataError
from scripts.activate_vision import activate, machine_status


def machine():
    return {'python_supported':True,'project_dependencies_found':True,
            'ollama_binary_found':True,'ffmpeg_found':True,'ram_caution':False,
            'disk_caution':False}


def ready(a,b):
    return {'models':[{'model':a,'vision_capability_advertised':True},
                      {'model':b,'vision_capability_advertised':True}],
            'real_inference_completed':False}


class ActivationTests(unittest.TestCase):
    def test_absent_ollama_blocks_without_start_or_download(self):
        calls=[]
        with tempfile.TemporaryDirectory() as t:
            m=machine();m['ollama_binary_found']=False
            result=activate(Path(t)/'run',status_fn=lambda:m,
                            ready_fn=lambda:calls.append('ready'),
                            pull_fn=lambda *a,**k:calls.append('pull'))
            self.assertEqual(result['status'],'BLOCKED')
            self.assertIn('not installed',result['blocker'])
            self.assertEqual(calls,[])
            self.assertTrue((Path(t)/'run/activation_status.json').exists())

    def test_running_server_and_installed_models_no_side_effects(self):
        calls=[]
        with tempfile.TemporaryDirectory() as t, patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            result=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:True,
                preflight_fn=ready,pull_fn=lambda *a,**k:calls.append('pull'),
                start_fn=lambda *a:calls.append('start'))
            self.assertEqual(result['status'],'LOCAL_MODELS_READY_FIELD_VALIDATION_OPEN')
            self.assertFalse(result['model_inference_verified'])
            self.assertFalse(result['customer_release_allowed'])
            self.assertEqual(calls,[])

    def test_pull_only_when_explicitly_selected_and_distinct_models(self):
        calls=[]
        def pull(cmd,**kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as t, patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            r=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:True,
                preflight_fn=ready,pull_fn=pull,download_models=True)
        self.assertEqual(r['model_downloads_performed'],['qwen2.5vl:3b','granite3.2-vision:2b'])
        self.assertEqual(calls,[['/safe/ollama','pull','qwen2.5vl:3b'],
                                ['/safe/ollama','pull','granite3.2-vision:2b']])

    def test_failed_pull_blocks_and_does_not_continue_to_preflight(self):
        with tempfile.TemporaryDirectory() as t, patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            r=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:True,
                preflight_fn=lambda *args:self.fail('preflight should not run'),
                pull_fn=lambda *a,**kw:SimpleNamespace(returncode=1),
                download_models=True)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(r['model_downloads_performed'],[])
        self.assertIn('download failed',r['blocker'])

    def test_missing_server_does_not_auto_start(self):
        with tempfile.TemporaryDirectory() as t,patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            r=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:False,
                       preflight_fn=ready)
        self.assertIn('not running',r['blocker'])
        self.assertFalse(r['server_process_started'])

    def test_start_server_explicit_and_readiness_verified(self):
        states=iter([False,True,True])
        events=[]
        process=SimpleNamespace(pid=123456,poll=lambda:None)
        with tempfile.TemporaryDirectory() as t,patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            r=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:next(states),
               start_fn=lambda *a:(events.append('start') or process),
               preflight_fn=ready,start_server=True,sleep_fn=lambda s:events.append('sleep'))
        self.assertEqual(r['status'],'LOCAL_MODELS_READY_FIELD_VALIDATION_OPEN')
        self.assertEqual(events,['start'])
        self.assertTrue(r['server_process_started'])

    def test_scripted_fake_live_gate_cannot_claim_inference(self):
        fake_trial=lambda *a:{'status':'LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN',
                 'live_model_inference_verified':True,
                 'live_specialist_tool_use_verified':True,
                 'reviewer_visual_assessment_verified':True,
                 'production_dependencies_used':True}
        with tempfile.TemporaryDirectory() as t,patch('scripts.activate_vision.shutil.which',return_value='/safe/ollama'):
            r=activate(Path(t)/'run',status_fn=machine,ready_fn=lambda:True,
                preflight_fn=ready,runner=fake_trial,run_live_gate=True)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertFalse(r['model_inference_verified'])
        self.assertFalse(r['customer_release_allowed'])

    def test_full_video_trial_requires_ffmpeg(self):
        with tempfile.TemporaryDirectory() as t:
            m=machine();m['ffmpeg_found']=False
            r=activate(Path(t)/'run',status_fn=lambda:m,run_live_gate=True)
        self.assertIn('FFmpeg',r['blocker'])

    def test_reject_other_host_before_any_creation(self):
        with tempfile.TemporaryDirectory() as t, patch.dict(os.environ,{'OLLAMA_HOST':'0.0.0.0:11434'}):
            root=Path(t)/'proof'
            with self.assertRaisesRegex(DataError,'127.0.0.1'):
                activate(root,status_fn=machine)
            self.assertFalse(root.exists())

    def test_existing_proof_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'proof';p.mkdir();(p/'keep').write_text('old')
            with self.assertRaisesRegex(DataError,'overwrite'):
                activate(p,status_fn=machine)
            self.assertEqual((p/'keep').read_text(),'old')

    def test_duplicate_model_names_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(DataError,'differ'):
                activate(Path(t)/'proof','qwen:1','qwen:1',status_fn=machine)

    def test_actual_doctor_is_readonly(self):
        m=machine_status()
        self.assertIn('ollama_binary_found',m)
        self.assertFalse(m['customer_release_allowed'])
        self.assertFalse(m['live_inference_verified'])

if __name__=='__main__':unittest.main()
