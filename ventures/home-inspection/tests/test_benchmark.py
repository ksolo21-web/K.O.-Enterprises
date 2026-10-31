import tempfile
import unittest
from pathlib import Path
from PIL import Image
from inspection_engine.benchmark import evaluate
from inspection_engine.core import DataError
from inspection_engine.capture import intake_files
import json

class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        pic=self.root/'test.png';Image.new('RGB',(400,300),'white').save(pic)
        fixture=Path(__file__).parent.parent/'examples'/'demo_project.json'
        self.doc=json.loads(fixture.read_text())
        self.doc['project_id']='BM-1';self.doc['media']=[]
        self.doc['observations']=[];self.doc['findings']=[];self.doc['equipment']=[];self.doc['limitations']=[]
        added=intake_files(self.doc,self.root,[pic],'exterior','Front')
        self.media=self.doc['media'][0]
        self.truth={'project_id':'BM-1','label_source':'independent_human_inspector',
          'annotator_id':'fixture-inspector','reviewed_media_ids':[self.media['id']],
          'labels':[{'media_id':self.media['id'],'system':'exterior','issue_code':'siding.crack',
                     'severity':'major','bbox':[.2,.2,.4,.4]}]}
        self.pred={'project_id':'BM-1','source':'model_draft','proposals':[
          {'media_id':self.media['id'],'system':'exterior','issue_code':'siding.crack',
           'source_sha256':self.media['sha256'],'bbox':[.2,.2,.4,.4]}]}
    def evaluate(self):return evaluate(self.doc,self.root,self.truth,self.pred,minimum_cases=1)
    def test_exact_matching(self):
        r=self.evaluate();self.assertEqual((r['tp'],r['fp'],r['fn']), (1,0,0));self.assertFalse(r['customer_release_allowed'])
    def test_overlapping_boxes_maximize_valid_detections(self):
        # The best individual IoU consumes the only match for the second
        # defect. Maximum-cardinality matching finds both valid detections.
        self.truth['labels'][0]['bbox']=[.388,.132,.616,.407]
        other=dict(self.truth['labels'][0])
        other['bbox']=[.495,.168,.692,.298]
        self.truth['labels'].append(other)
        self.pred['proposals'][0]['bbox']=[.344,.142,.671,.384]
        other_proposal=dict(self.pred['proposals'][0])
        other_proposal['bbox']=[.252,.262,.649,.417]
        self.pred['proposals'].append(other_proposal)
        result=self.evaluate()
        self.assertEqual((result['tp'],result['fp'],result['fn']),(2,0,0))

    def test_mislocated(self):
        self.pred['proposals'][0]['bbox']=[.5,.5,.7,.7]
        r=self.evaluate();self.assertEqual((r['tp'],r['fp'],r['fn'],r['critical_misses']),(0,1,1,1))
    def test_wrong_code(self):
        self.pred['proposals'][0]['issue_code']='siding.discoloration'
        self.assertEqual(self.evaluate()['tp'],0)
    def test_missing_prediction(self):
        self.pred['proposals']=[];self.assertEqual(self.evaluate()['critical_misses'],1)
    def test_duplicate_predictions_blocked(self):
        self.pred['proposals']*=2
        with self.assertRaises(DataError):self.evaluate()
    def test_bad_label_source_blocked(self):
        self.truth['label_source']='model_generated'
        with self.assertRaises(DataError):self.evaluate()
    def test_tampered_predictions_blocked(self):
        self.pred['proposals'][0]['source_sha256']='0'*64
        with self.assertRaises(DataError):self.evaluate()
    def test_zero_corpus_not_passed(self):
        r=evaluate(self.doc,self.root,self.truth,self.pred,minimum_cases=10)
        self.assertFalse(r['sufficient_sample_size']);self.assertFalse(r['customer_release_allowed'])
    def test_invalid_bbox_blocked(self):
        self.pred['proposals'][0]['bbox']=[.5,.5,.5,.8]
        with self.assertRaises(DataError):self.evaluate()
    def test_invalid_project_blocked(self):
        self.truth['project_id']='wrong'
        with self.assertRaises(DataError):self.evaluate()

if __name__=='__main__':unittest.main()
