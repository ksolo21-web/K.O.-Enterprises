"""Actual loopback deadline/protocol tests and controlled diagnostic evidence."""
import copy
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from inspection_engine.core import DataError
from scripts import isolate_specialist_request as isolated


class Handler(BaseHTTPRequestHandler):
    mode='normal'
    calls=[]
    def log_message(self,*args):pass
    def do_POST(self):
        Handler.calls.append((self.command,self.path))
        self.rfile.read(int(self.headers['Content-Length']))
        if Handler.mode=='headers_stall':self.server.release.wait(3)
        if Handler.mode=='redirect':
            self.send_response(302);self.send_header('Location','https://bad.example');self.end_headers();return
        data=json.dumps({'done':True,'done_reason':'stop','response':'{"candidates":[],"requests":[]}'}).encode()
        if Handler.mode=='oversize':data=b'x'*(isolated.MAX_MODEL_REPLY+1)
        if Handler.mode=='json_error':data=json.dumps({'error':'Unsupported test grammar','thinking':'do not retain','context':[1,2]}).encode()
        if Handler.mode=='malformed':data=b'not JSON at all'
        self.send_response(400 if Handler.mode=='json_error' else 200)
        if Handler.mode=='chunked':self.send_header('Transfer-Encoding','chunked')
        elif Handler.mode!='close_delimited':
            self.send_header('Content-Length',str(len(data)+(100 if Handler.mode=='truncated' else 0)))
        self.end_headers()
        try:
            if Handler.mode=='body_drip':
                for char in data:
                    self.wfile.write(bytes([char]));self.wfile.flush()
                    if self.server.release.wait(.1):break
            elif Handler.mode=='chunked':
                self.wfile.write(f'{len(data):X}\r\n'.encode()+data+b'\r\n0\r\n\r\n')
            else:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass


class DiagnosticHTTPTests(unittest.TestCase):
    def setUp(self):
        Handler.mode='normal';Handler.calls=[]
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True;self.server.release=threading.Event()
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        self.port=patch.object(isolated,'PORT',self.server.server_port);self.port.start()
    def tearDown(self):
        self.server.release.set();self.port.stop()
        self.server.shutdown();self.server.server_close();self.worker.join(2)
    def test_one_request_no_redirect_following_or_retry(self):
        Handler.mode='redirect'
        with self.assertRaisesRegex(DataError,'302'):
            isolated.diagnostic_generate({'synthetic':'only'},deadline_seconds=2)
        self.assertEqual(Handler.calls,[('POST','/api/generate')])
    def test_completed_loopback_object_and_raw_hash(self):
        reply,digest=isolated.diagnostic_generate({'synthetic':'only'},deadline_seconds=2)
        self.assertIs(reply['done'],True);self.assertEqual(len(digest),64)
        self.assertEqual(Handler.calls,[('POST','/api/generate')])
    def test_absolute_deadline_stops_missing_headers_and_continuous_body_drip(self):
        for mode in ('headers_stall','body_drip'):
            with self.subTest(mode=mode):
                Handler.mode=mode
                started=time.monotonic()
                with self.assertRaises(TimeoutError):
                    isolated.diagnostic_generate({'synthetic':'only'},deadline_seconds=1)
                self.assertLess(time.monotonic()-started,2.5)
        self.assertEqual(len(Handler.calls),2)
    def test_oversized_reply_rejected(self):
        Handler.mode='oversize'
        with self.assertRaisesRegex(DataError,'exceeds limit'):
            isolated.diagnostic_generate({'synthetic':'only'},deadline_seconds=2)
    def test_invalid_budget_stops_before_network(self):
        for budget in (0,601,True,1.5):
            with self.assertRaises(DataError):isolated.diagnostic_generate({},deadline_seconds=budget)
        self.assertEqual(Handler.calls,[])

    def test_http_json_error_is_audited_before_status_rejection(self):
        Handler.mode='json_error';seen=[]
        with self.assertRaisesRegex(DataError,'400'):
            isolated.diagnostic_generate({},deadline_seconds=2,response_audit=seen.append)
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0]['transport_response_untrusted'],{'error':'Unsupported test grammar'})
        self.assertEqual(seen[0]['http_status'],400)
        self.assertTrue(seen[0]['body_complete']);self.assertEqual(len(seen[0]['body_sha256']),64)
        self.assertNotIn('do not retain',json.dumps(seen))

    def test_malformed_json_preserves_status_size_digest_and_parse_failure(self):
        Handler.mode='malformed';seen=[]
        with self.assertRaisesRegex(DataError,'invalid JSON'):
            isolated.diagnostic_generate({},deadline_seconds=2,response_audit=seen.append)
        self.assertEqual(len(seen),1);self.assertEqual(seen[0]['http_status'],200)
        self.assertTrue(seen[0]['body_complete']);self.assertIn('parse_error_type',seen[0])
        self.assertEqual(seen[0]['received_bytes'],len(b'not JSON at all'))

    def test_valid_json_in_truncated_declared_body_cannot_pass(self):
        Handler.mode='truncated';seen=[]
        with self.assertRaisesRegex(DataError,'body truncated'):
            isolated.diagnostic_generate({},deadline_seconds=2,response_audit=seen.append)
        self.assertFalse(seen[0]['body_complete'])
        self.assertEqual(seen[0]['declared_bytes_remaining'],100)
        self.assertGreater(seen[0]['received_bytes'],0)

    def test_complete_chunked_and_close_delimited_bodies_remain_supported(self):
        for mode in ('chunked','close_delimited'):
            with self.subTest(mode=mode):
                Handler.mode=mode;seen=[]
                reply,_=isolated.diagnostic_generate({},deadline_seconds=2,response_audit=seen.append)
                self.assertIs(reply['done'],True);self.assertTrue(seen[0]['body_complete'])


class DiagnosticEvidenceTests(unittest.TestCase):
    def test_replay_is_exact_pinned_synthetic_request(self):
        payload,request=isolated.replay_payload()
        self.assertEqual(payload['model'],isolated.MODEL)
        self.assertFalse(payload['stream']);self.assertEqual(payload['options'],{'temperature':0})
        self.assertEqual(payload['format'],request['generation_schema'])
        self.assertEqual(payload['prompt'],request['prompt'])
        self.assertEqual(payload['system'],isolated.SYSTEM_PROMPT)
    def test_changed_source_cannot_supply_customer_or_other_input(self):
        with patch.object(isolated,'SOURCE_SHA256','0'*64):
            with self.assertRaisesRegex(DataError,'document changed'):isolated.replay_payload()
    def test_wrong_digest_blocks_generation(self):
        with patch.object(isolated,'local_json',return_value={'models':[{'name':isolated.MODEL,'digest':'0'*64}]}):
            with self.assertRaisesRegex(DataError,'digest'):isolated.verify_writer()
    def test_completed_answer_is_provisional_and_never_executes_tools_or_Q02(self):
        envelope={'done':True,'done_reason':'stop','response':json.dumps({'candidates':[
            {'type':'feature','system':'exterior','feature_code':'cladding_type',
             'description':'Synthetic illustrative facade, material unconfirmed','status':'partially_observed'}],
            'requests':[{'kind':'zoom','bbox':[.1,.1,.5,.5]}]}),'thinking':'never retain','context':[1,2]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(isolated,'verify_writer',return_value={'model':'controlled'}), \
             patch.object(isolated,'diagnostic_generate',return_value=(envelope,'a'*64)) as call:
            root=Path(tmp)/'run';result=isolated.run(root,deadline_seconds=600)
            self.assertTrue(result['specialist_contract_validated'])
            self.assertEqual(result['tools_executed'],0);self.assertEqual(result['Q02_calls'],0)
            self.assertFalse(result['customer_release_allowed']);self.assertFalse(result['field_accuracy_verified'])
            self.assertNotIn('thinking',(root/'response.json').read_text().split('omitted_fields')[0])
            self.assertEqual(call.call_count,1)
    def test_invalid_or_partial_answer_is_preserved_and_blocked(self):
        variants=[{'done':False,'done_reason':'stop','response':'{}'},
                  {'done':True,'done_reason':'length','response':'{}'},
                  {'done':True,'done_reason':'stop','error':'failed','response':'{}'},
                  {'done':True,'done_reason':'stop','response':json.dumps({'candidates':[
                    {'type':'feature','system':'exterior','description':'cladding_type','status':'unknown'}],
                    'requests':[]})}]
        for reply in variants:
            with self.subTest(reply=reply),tempfile.TemporaryDirectory() as tmp, \
                 patch.object(isolated,'verify_writer',return_value={}), \
                 patch.object(isolated,'diagnostic_generate',return_value=(copy.deepcopy(reply),'a'*64)):
                root=Path(tmp)/'run';result=isolated.run(root)
                self.assertEqual(result['status'],'BLOCKED')
                self.assertFalse(result['specialist_contract_validated'])
                captured=json.loads((root/'response.json').read_text())['transport_response_untrusted']
                self.assertEqual(captured,reply)
    def test_timeout_persists_request_cause_and_blocked_status(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(isolated,'verify_writer',return_value={}), \
             patch.object(isolated,'diagnostic_generate',side_effect=TimeoutError('Absolute deadline expired')) as call:
            root=Path(tmp)/'run';result=isolated.run(root)
            self.assertEqual(result['error_type'],'TimeoutError')
            self.assertFalse(result['completed_model_response']);self.assertEqual(call.call_count,1)
            self.assertTrue((root/'request.json').exists());self.assertTrue((root/'status.json').exists())
    def test_unchanged_zoom_does_not_pass_diagnostic_contract(self):
        envelope={'done':True,'done_reason':'stop','response':json.dumps({'candidates':[],
                      'requests':[{'kind':'zoom','bbox':[0,0,1,1]}]})}
        with tempfile.TemporaryDirectory() as tmp,patch.object(isolated,'verify_writer',return_value={}), \
             patch.object(isolated,'diagnostic_generate',return_value=(envelope,'a'*64)):
            result=isolated.run(Path(tmp)/'run')
            self.assertEqual(result['status'],'BLOCKED');self.assertIn('Unchanged zoom',result['error'])


if __name__=='__main__':unittest.main()
