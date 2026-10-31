"""Actual local HTTP protocol tests, not AI model or field accuracy tests."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
import json
import unittest

from inspection_engine.core import DataError
from inspection_engine import local_runtime

class Handler(BaseHTTPRequestHandler):
    calls=[]
    reply_kind='normal'
    def log_message(self,*args):pass
    def process(self):
        Handler.calls.append((self.command,self.path))
        if Handler.reply_kind == 'redirect':
            self.send_response(302)
            self.send_header('Location','https://bad.example/upload')
            self.end_headers()
            return
        if self.path == '/api/tags':
            review_digest='b'*64 if Handler.reply_kind!='same-digest' else 'a'*64
            obj={'models':[{'name':'writer:1','digest':'a'*64},
                           {'name':'reviewer:2','digest':review_digest}]}
        elif self.path == '/api/show':
            n=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))['model']
            obj={'capabilities':['completion','vision'] if n!='reviewer:2' or Handler.reply_kind!='text-only' else ['completion']}
        else:
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            obj={'response':json.dumps({'candidates':[]})}
        body=json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    do_GET=process
    do_POST=process

class LocalRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.port_patch=patch.object(local_runtime,'PORT',cls.server.server_port)
        cls.port_patch.start()
    @classmethod
    def tearDownClass(cls):
        cls.port_patch.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        Handler.calls=[];Handler.reply_kind='normal'
    def test_read_only_check_advertises_both_local_vision_models(self):
        res=local_runtime.preflight_models('writer:1','reviewer:2')
        self.assertEqual(res['preflight'],'LOCAL_MODELS_ADVERTISED_VISION')
        self.assertEqual([m['role'] for m in res['models']],['writer','reviewer'])
        self.assertEqual(res['models'][0]['model_digest_sha256'],'a'*64)
        self.assertEqual(res['models'][1]['model_digest_sha256'],'b'*64)
        self.assertFalse(res['real_inference_completed'])
        self.assertFalse(res['separate_runtime_identity_verified'])
        self.assertFalse(res['customer_release_allowed'])
        self.assertEqual(Handler.calls,[('GET','/api/tags'),('POST','/api/show'),('POST','/api/show')])
    def test_redirect_cannot_send_photos_to_another_host(self):
        Handler.reply_kind='redirect'
        with self.assertRaisesRegex(DataError,'redirect refused'):
            local_runtime.local_json('POST','/api/generate',{'images':['very-private-photo']})
        self.assertEqual(Handler.calls,[('POST','/api/generate')])
    def test_missing_model_fails_closed(self):
        with self.assertRaisesRegex(DataError,'not installed locally'):
            local_runtime.preflight_models('missing:1','reviewer:2')
        self.assertEqual(Handler.calls,[('GET','/api/tags')])
    def test_text_only_model_not_accepted_as_vision(self):
        Handler.reply_kind='text-only'
        with self.assertRaisesRegex(DataError,'does not advertise vision'):
            local_runtime.preflight_models('writer:1','reviewer:2')
    def test_same_digest_different_names_denied(self):
        Handler.reply_kind='same-digest'
        with self.assertRaisesRegex(DataError,'identical model digests'):
            local_runtime.preflight_models('writer:1','reviewer:2')

    def test_same_model_denied(self):
        with self.assertRaisesRegex(DataError,'distinct model'):
            local_runtime.preflight_models('writer:1','writer:1')
        self.assertFalse(Handler.calls)
    def test_reject_other_endpoints_and_get_payload(self):
        with self.assertRaisesRegex(DataError,'Unapproved'):
            local_runtime.local_json('GET','http://example.com/')
        with self.assertRaisesRegex(DataError,'GET may not include'):
            local_runtime.local_json('GET','/api/tags',{'secret':'no'})
        self.assertFalse(Handler.calls)
    def test_reject_nonjson_reply_inputs(self):
        with self.assertRaisesRegex(DataError,'POST requires'):
            local_runtime.local_json('POST','/api/show',None)
        with self.assertRaisesRegex(DataError,'timeout'):
            local_runtime.local_json('GET','/api/tags',timeout=0)
        self.assertFalse(Handler.calls)
    def test_invalid_name_blocks_request(self):
        for model in ('http://somewhere','../../tmp','', 'bad model'):
            with self.subTest(model=model), self.assertRaisesRegex(DataError,'Invalid local model'):
                local_runtime.preflight_models(model,'reviewer:2')
        self.assertFalse(Handler.calls)
    def test_actual_loopback_generation_response(self):
        reply=local_runtime.local_json('POST','/api/generate',{'prompt':'synthetic test'})
        self.assertEqual(json.loads(reply['response']),{'candidates':[]})
        self.assertEqual(Handler.calls,[('POST','/api/generate')])

if __name__=='__main__':unittest.main()

class LocalPreflightCliTests(unittest.TestCase):
    def test_blocked_cli_returns_json_and_nonzero(self):
        import io
        import sys
        from contextlib import redirect_stdout
        from inspection_engine.__main__ import main
        out=io.StringIO()
        with patch.object(sys,'argv',['inspection_engine','model-preflight',
             '--writer-model','w:1','--review-model','r:2']), \
             patch('inspection_engine.__main__.preflight_models',side_effect=DataError('Local Ollama unavailable')), \
             redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            main()
        self.assertEqual(raised.exception.code,2)
        payload=json.loads(out.getvalue())
        self.assertEqual(payload['preflight'],'BLOCKED')
        self.assertFalse(payload['customer_release_allowed'])
    def test_ready_cli_reports_no_inference_done(self):
        import io
        import sys
        from contextlib import redirect_stdout
        from inspection_engine.__main__ import main
        out=io.StringIO()
        with patch.object(sys,'argv',['inspection_engine','model-preflight',
             '--writer-model','w:1','--review-model','r:2']), \
             patch('inspection_engine.__main__.preflight_models',return_value={'preflight':'LOCAL_MODELS_ADVERTISED_VISION', 'real_inference_completed':False}), \
             redirect_stdout(out):
            main()
        self.assertFalse(json.loads(out.getvalue())['real_inference_completed'])
