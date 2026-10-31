"""Contract tests for live smoke runner; only mock transport, NOT actual VLM."""
import base64
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from PIL import Image
from inspection_engine.model_smoke import synthetic_probe_image, smoke_probe, _parse_visual_response
from inspection_engine.core import DataError

class ModelSmokeContractTests(unittest.TestCase):
    def test_synthetic_probe_is_valid_image(self):
        for color, shape in [('red','square'), ('blue','circle')]:
            with Image.open(BytesIO(synthetic_probe_image(color=color,shape=shape))) as im:
                self.assertEqual(im.size, (512,384))
                self.assertEqual(im.format, 'PNG')

    def test_both_models_receive_actual_images_and_correct_role(self):
        calls=[]
        def mock_transport(method,endpoint,payload,**kwargs):
            calls.append(payload)
            self.assertEqual((method,endpoint),('POST','/api/generate'))
            self.assertEqual(payload['keep_alive'],0)
            self.assertEqual(payload['format'],'json')
            self.assertEqual(payload['options']['temperature'],0)
            raw=base64.b64decode(payload['images'][0])
            with Image.open(BytesIO(raw)) as im:
                self.assertEqual(im.size,(512,384))
            return {'response':json.dumps({'color':'red','shape':'square'} if len(calls)==1 else
                                            {'color':'blue','shape':'circle'}), 'done':True}
        result=smoke_probe('writer:3b','reviewer:2b',transport=mock_transport)
        self.assertEqual(result['status'],'MOCK_CONTRACT_PASSED')
        self.assertFalse(result['actual_image_inference_executed'])
        self.assertEqual([x['model'] for x in calls],['writer:3b','reviewer:2b'])
        self.assertFalse(result['customer_release_allowed'])
        self.assertFalse(result['real_property_accuracy_verified'])

    def test_model_wrong_visual_reading_fails(self):
        def wrong(*args, **kwargs):
            return {'response':'{"color":"red","shape":"square"}', 'done':True}
        result=smoke_probe('w','r',transport=wrong)
        self.assertFalse(result['models'][1]['passed'])
        self.assertEqual(result['status'],'MOCK_CONTRACT_FAILED')

    def test_noncompleted_model_response_rejected(self):
        with self.assertRaisesRegex(DataError,'did not complete'):
            smoke_probe('w','r',transport=lambda *a,**kw:{'response':'{}'})

    def test_unambiguous_attributes_required(self):
        for reply in ('red and blue square','a square','{"color":"red","shape":"thing?"}','invalid'):
            with self.subTest(reply=reply), self.assertRaises(DataError):_parse_visual_response(reply)

    def test_unavailable_local_runtime_is_blocked_before_inference(self):
        with patch('inspection_engine.model_smoke.preflight_models',side_effect=DataError('Local Ollama unavailable')):
            with self.assertRaisesRegex(DataError,'unavailable'):
                smoke_probe('qwen2.5vl:3b','granite3.2-vision:2b')

if __name__=='__main__':unittest.main()
