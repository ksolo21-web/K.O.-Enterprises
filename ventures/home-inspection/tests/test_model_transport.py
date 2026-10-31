"""Optional loopback model transport contract; uses controlled responses only."""
import base64
import json
import unittest
from unittest.mock import patch
from inspection_engine.core import DataError
from inspection_engine.vision import ollama_local, MAX_MODEL_REPLY
from inspection_engine.critic import CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT

class LocalModelTransportTests(unittest.TestCase):
    def test_request_format_carries_image_and_critic_schema(self):
        seen=[]
        def fake_local(method,endpoint,payload,**kwargs):
            seen.append((method,endpoint,payload,kwargs))
            return {'done':True,'response':json.dumps({'decision':'insufficient_evidence',
                'reason':'Low resolution','missing_evidence':'Request new angle'})}
        with patch('inspection_engine.vision.local_json',side_effect=fake_local):
            answer=ollama_local(b'JPEG-TEST','Do not invent defect','vision-test',timeout=3,
                   schema=CRITIC_SCHEMA,system_prompt=CRITIC_SYSTEM_PROMPT)
        self.assertEqual(answer['decision'],'insufficient_evidence')
        method,endpoint,payload,opts=seen[0]
        self.assertEqual((method,endpoint),('POST','/api/generate'))
        self.assertEqual(opts['timeout'],3)
        self.assertEqual(opts['max_bytes'],MAX_MODEL_REPLY)
        self.assertEqual(base64.b64decode(payload['images'][0]),b'JPEG-TEST')
        self.assertEqual(payload['model'],'vision-test')
        self.assertEqual(payload['format'],CRITIC_SCHEMA)
        self.assertEqual(payload['system'],CRITIC_SYSTEM_PROMPT)
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['options']['temperature'],0)

    def test_invalid_model_identifier_rejected_before_connect(self):
        with patch('inspection_engine.vision.local_json') as fake:
            with self.assertRaisesRegex(DataError,'Invalid local model'):
                ollama_local(b'abc','test','https://remote-server.example')
            fake.assert_not_called()

    def test_missing_server_is_visible_failure(self):
        with patch('inspection_engine.vision.local_json',side_effect=DataError('Local Ollama unavailable')):
            with self.assertRaisesRegex(DataError,'unavailable'):
                ollama_local(b'abc','test','vision-test')

    def test_invalid_model_json_fails_closed(self):
        with patch('inspection_engine.vision.local_json',return_value={'done':True,'response':'not-json'}):
            with self.assertRaisesRegex(DataError,'invalid JSON'):
                ollama_local(b'abc','test','vision-test')

    def test_partial_missing_and_error_completion_envelopes_rejected(self):
        payload=json.dumps({'candidates':[]})
        for extra in ({},{'done':False},{'done':1},{'done':'true'},
                      {'done':True,'error':'generation failed'}, {'done':True,'error':None}):
            with self.subTest(extra=extra), patch('inspection_engine.vision.local_json',
                    return_value={'response':payload,**extra}):
                with self.assertRaisesRegex(DataError,'complete generation'):
                    ollama_local(b'abc','test','vision-test')

    def test_audit_sees_untrusted_reply_before_json_validation(self):
        raw={'done':True,'response':'invalid-json'}
        seen=[]
        with patch('inspection_engine.vision.local_json',return_value=raw):
            with self.assertRaisesRegex(DataError,'invalid JSON'):
                ollama_local(b'abc','test','vision-test',response_audit=seen.append)
        self.assertEqual(seen,[raw])

    def test_audit_callback_cannot_turn_partial_reply_into_completion(self):
        raw={'done':False,'response':'{"candidates":[]}'}
        def mutate(copied): copied['done']=True
        with patch('inspection_engine.vision.local_json',return_value=raw):
            with self.assertRaisesRegex(DataError,'complete generation'):
                ollama_local(b'abc','test','vision-test',response_audit=mutate)
        self.assertFalse(raw['done'])

    def test_invalid_audit_callback_rejected_before_connect(self):
        with patch('inspection_engine.vision.local_json') as transport:
            with self.assertRaisesRegex(DataError,'audit must be callable'):
                ollama_local(b'abc','test','vision-test',response_audit='not-a-callback')
        transport.assert_not_called()

    def test_model_reply_size_limit_propagates(self):
        with patch('inspection_engine.vision.local_json',side_effect=DataError('Local model response exceeds limit')):
            with self.assertRaisesRegex(DataError,'exceeds limit'):
                ollama_local(b'abc','test','vision-test')

if __name__=='__main__':unittest.main()
