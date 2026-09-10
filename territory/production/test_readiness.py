import copy
import json
from pathlib import Path
import tempfile
import unittest
import readiness

class ReadinessTests(unittest.TestCase):
    def sample(self):
        cases=[]
        for i in range(8):
            expected={'label_collision':bool(i%2),'broken_road':bool(i%3)}
            cases.append({'id':str(i),'passed':True,'expected':expected,
                          'receipt':{'kind':'actual_local_model_inference',
                          'identity':{'digest':readiness.MODEL_DIGEST,'version':'0.33.3'},
                          'raw_response':{'done':True,'done_reason':'stop'},
                          'image_sha256':['0'*64],'request_sha256':'1'*64,'result':dict(expected)}})
        return {'required':8,'completed':8,'passed':8,'cases':cases}
    def check(self,data):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'synthetic-unit-test.json';p.write_text(json.dumps(data))
            return readiness.calibration_check(p)
    def reject(self,data):
        with self.assertRaises(ValueError):self.check(data)
    def test_complete_synthetic_receipt_is_not_card_approval(self):
        r=self.check(self.sample());self.assertTrue(r['passed']);self.assertIn('not real-card',r['scope'])
    def test_missing_case(self):
        r=self.sample();r['cases'].pop();self.reject(r)
    def test_duplicate_case(self):
        r=self.sample();r['cases'][1]['id']='0';self.reject(r)
    def test_failed_case(self):
        r=self.sample();r['cases'][1]['passed']=False;self.reject(r)
    def test_wrong_model(self):
        r=self.sample();r['cases'][1]['receipt']['identity']['digest']='0'*64;self.reject(r)
    def test_truncated(self):
        r=self.sample();r['cases'][1]['receipt']['raw_response']['done_reason']='length';self.reject(r)
    def test_missing_images(self):
        r=self.sample();r['cases'][1]['receipt']['image_sha256']=[];self.reject(r)
    def test_wrong_ground_truth(self):
        r=self.sample();r['cases'][1]['receipt']['result']['broken_road']=False;self.reject(r)
    def test_count_alone_not_approval(self):
        r=self.sample();r['cases'][0]['receipt']['kind']='rule_checker';self.reject(r)
    def test_no_unattended_approval_without_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            r=readiness.report(Path(t));self.assertFalse(r['unattended_card_release_ready']);self.assertEqual(r['approval'],'NOT APPROVED')
    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'test.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):readiness.read_json(p)
    def test_nan_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'test.json';p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):readiness.read_json(p)

if __name__=='__main__':unittest.main()
