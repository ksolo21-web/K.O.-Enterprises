"""Controller tests for gated full-card visual review. Mocks are not visual evidence."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import engine,visual_review as v

class CardReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.job=self.root/'job.json';self.out=self.root/'result';self.calls=[]
        self.identity={'model':v.neural.MODEL,'digest':v.MODEL_DIGEST,'runtime':'ollama','version':'0.33.3'}
        self.images=[]
        for i,cat in enumerate(v.REVIEW_WEIGHTS):
            p=self.root/f'{cat}.png';Image.new('RGB',(160,160),(240-i,245,250)).save(p);self.images.append((cat,p))
        q={'kind':'private_real_image_calibration','actual_model_inference':True,'selected_checks_passed':True,
           'scope':sorted(v.REQUIRED_QUALIFICATION),'model_identity':self.identity,'program_sha256':engine.sha(Path(v.__file__))}
        self.q=self.root/'qualification.json';self.q.write_text(json.dumps(q))
        self.data={'schema_version':1,'kind':'visual_card_review','qualification':{'file':self.q.name,'sha256':engine.sha(self.q)},
                   'cases':[{'category':cat,'focus':'Strict territory-card review','images':[{'file':p.name,'sha256':engine.sha(p)}]} for cat,p in self.images]}
    def infer(self,images,prompt,schema,**kw):
        self.calls.append((images,prompt,schema,kw))
        result={'observation':'Mock only.','score':10.0,'blocking':False,'uncertain':False,'findings':[]}
        return {'identity':self.identity,'image_sha256':[engine.sha(p) for p in images],'kind':'actual_local_model_inference','result':result,
                'raw_response':{'model':self.identity['model'],'done':True,'done_reason':'stop','message':{'content':json.dumps(result)}}}
    def runjob(self,call=None):
        self.job.write_text(json.dumps(self.data))
        with patch.object(engine,'private_guard'),patch.object(engine,'verify_skills',return_value={'verified_files':138}):
            return v.run(self.job,self.out,infer=call or self.infer,identity=self.identity)
    def test_mock_review_runs_all_categories_but_never_authorizes(self):
        r=self.runjob();self.assertEqual(len(self.calls),5);self.assertEqual(r['independent_visual_score'],10);self.assertFalse(r['visual_pass']);self.assertFalse(r['release_ready'])
    def test_qualification_is_required(self):
        self.data['qualification']={'file':'missing.json','sha256':'0'*64}
        with self.assertRaises(engine.GateError):self.runjob()
    def test_qualification_must_cover_required_defects(self):
        q=json.loads(self.q.read_text());q['scope']=['leader_attachment'];self.q.write_text(json.dumps(q));self.data['qualification']['sha256']=engine.sha(self.q)
        with self.assertRaises(v.VisualError):self.runjob()
    def test_qualification_must_bind_same_program_and_model(self):
        q=json.loads(self.q.read_text());q['program_sha256']='0'*64;self.q.write_text(json.dumps(q));self.data['qualification']['sha256']=engine.sha(self.q)
        with self.assertRaises(v.VisualError):self.runjob()
    def test_exact_five_categories_required(self):
        self.data['cases']=self.data['cases'][:-1]
        with self.assertRaises(v.VisualError):self.runjob()
    def test_duplicate_category_rejected(self):
        self.data['cases'][-1]['category']=self.data['cases'][0]['category']
        with self.assertRaises(v.VisualError):self.runjob()
    def test_blocking_category_caps_score(self):
        def call(images,prompt,schema,**kw):
            r=self.infer(images,prompt,schema,**kw)
            if len(self.calls)==1:
                r['result']['blocking']=True;r['raw_response']['message']['content']=json.dumps(r['result'])
            return r
        r=self.runjob(call);self.assertEqual(r['independent_visual_score'],8.0);self.assertTrue(r['blocking_categories'])
    def test_uncertainty_caps_score(self):
        def call(images,prompt,schema,**kw):
            r=self.infer(images,prompt,schema,**kw)
            if len(self.calls)==2:
                r['result']['uncertain']=True;r['raw_response']['message']['content']=json.dumps(r['result'])
            return r
        self.assertEqual(self.runjob(call)['independent_visual_score'],8.0)
    def test_score_below_eight_is_recorded(self):
        def call(images,prompt,schema,**kw):
            r=self.infer(images,prompt,schema,**kw)
            if len(self.calls)==3:
                r['result']['score']=7.5;r['raw_response']['message']['content']=json.dumps(r['result'])
            return r
        r=self.runjob(call);self.assertEqual(len(r['categories_below_8']),1)
    def test_builder_score_never_reaches_model_prompt(self):
        self.data['builder_score']='SECRET BUILDER 10';self.runjob();self.assertTrue(all('SECRET' not in p for _,p,_,_ in self.calls))

if __name__=='__main__':unittest.main()
