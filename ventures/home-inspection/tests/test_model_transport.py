"""Optional localhost Ollama transport contract. Mock endpoint, not vision inference."""
import base64
import json
import unittest
from unittest.mock import patch
from inspection_engine.core import DataError
from inspection_engine.vision import ollama_local, MAX_MODEL_REPLY
from inspection_engine.critic import CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT

class FakeResponse:
    def __init__(self,value):self.value=value
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.value[:n]

class LocalModelTransportTests(unittest.TestCase):
    def test_actual_request_format_carries_image_and_critic_schema(self):
        seen=[]
        def fake_urlopen(request,timeout):
            seen.append((request,timeout))
            return FakeResponse(json.dumps({'response':json.dumps({
                'decision':'insufficient_evidence','reason':'Low resolution',
                'missing_evidence':'Request new angle'})}).encode())
        with patch('inspection_engine.vision.urllib.request.urlopen',side_effect=fake_urlopen):
            answer=ollama_local(b'JPEG-TEST','Do not invent defect','vision-test',timeout=3,schema=CRITIC_SCHEMA,system_prompt=CRITIC_SYSTEM_PROMPT)
        self.assertEqual(answer['decision'],'insufficient_evidence')
        req,t=seen[0]
        self.assertEqual(req.full_url,'http://127.0.0.1:11434/api/generate')
        self.assertEqual(t,3)
        payload=json.loads(req.data)
        self.assertEqual(base64.b64decode(payload['images'][0]),b'JPEG-TEST')
        self.assertEqual(payload['model'],'vision-test')
        self.assertEqual(payload['format'],CRITIC_SCHEMA)
        self.assertEqual(payload['system'],CRITIC_SYSTEM_PROMPT)
        self.assertNotIn('candidates array',payload['system'])
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['options']['temperature'],0)

    def test_invalid_model_identifier_rejected_before_connect(self):
        with patch('inspection_engine.vision.urllib.request.urlopen') as fake:
            with self.assertRaisesRegex(DataError,'Invalid local model'):
                ollama_local(b'abc','test','https://remote-server.example')
            fake.assert_not_called()

    def test_missing_server_is_visible_failure(self):
        from urllib.error import URLError
        with patch('inspection_engine.vision.urllib.request.urlopen',side_effect=URLError('offline')):
            with self.assertRaisesRegex(DataError,'unavailable'):
                ollama_local(b'abc','test','vision-test')

    def test_invalid_model_json_fails_closed(self):
        with patch('inspection_engine.vision.urllib.request.urlopen',return_value=FakeResponse(b'{"response":"not-json"}')):
            with self.assertRaisesRegex(DataError,'invalid JSON'):
                ollama_local(b'abc','test','vision-test')

    def test_model_reply_size_limit(self):
        with patch('inspection_engine.vision.urllib.request.urlopen',return_value=FakeResponse(b'A'*(MAX_MODEL_REPLY+1))):
            with self.assertRaisesRegex(DataError,'exceeds limit'):
                ollama_local(b'abc','test','vision-test')

if __name__=='__main__':unittest.main()
