"""Controller tests for encrypted real-card critic. Mocks are not visual evidence."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import engine,real_card_review as r

class RealCardReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.job=self.root/'job.json';self.out=self.root/'result';self.calln=0
        self.identity={'model':r.neural.MODEL,'digest':r.MODEL_DIGEST,'runtime':'ollama','version':'0.33.3'}
        self.images={}
        for i,name in enumerate(['wrong','leader','clutter','branch','balance','source','candidate','clean','full','close','family','nav','cov1','cov2']):
            p=self.root/(name+'.png');Image.new('RGB',(160,160),(220+i,225,230)).save(p);self.images[name]=p
        def spec(name):return {'path':self.images[name].name,'sha256':r.sha(self.images[name])}
        qtypes=[('wrong_side_label','wrong'),('leader_attachment_target','leader'),('label_clutter','clutter'),('branch_ownership','branch'),('map_balance','balance'),('geometry_fidelity','source'),('clean_card','clean')]
        q=[]
        for i,(typ,name) in enumerate(qtypes):
            imgs=[spec(name)] if typ!='geometry_fidelity' else [spec('source'),spec('candidate')]
            q.append({'id':f'{i+1:016x}','check':typ,'expected_defect':typ!='clean_card','focus':typ,'images':imgs})
        ctypes=[('full_visual',['full']),('closeup_visual',['close']),('source_fidelity',['source','candidate']),('family_resemblance',['family','full']),('navigation_context',['full','nav']),('coverage_scope',['cov1','cov2'])]
        checks=[{'id':f'{j:016x}','check':typ,'images':[spec(n) for n in names]} for j,(typ,names) in enumerate(ctypes,20)]
        self.data={'schema_version':1,'kind':'territory_card_review','qualification_cases':q,'review_checks':checks,
                   'scope_sha256':'a'*64,'duplicate_evidence_refs':[{'file':'cov1.png','sha256':r.sha(self.images['cov1'])}]}
    def infer(self,images,prompt,schema,**kw):
        self.calln+=1
        if 'defect' in schema['properties']:
            result={'observation':'fixture','defect':self.calln<=6,'uncertain':False}
        elif 'complete_active_scope_verified' in schema['properties']:
            result={'observation':'coverage','score':9.5,'uncertain':False,'complete_active_scope_verified':True,
                    'canonical_identity_verified':True,'measures_and_sides_verified':True,'source_to_artifact_inventory_verified':True,'unresolved_items':[]}
        else:
            result={'observation':'review','score':9.5,'blocking_defect':False,'uncertain':False,'defects':[]}
        return {'identity':self.identity,'image_sha256':[r.sha(p) for p in images],'kind':'actual_local_model_inference','result':result,
                'raw_response':{'model':self.identity['model'],'done':True,'done_reason':'stop','message':{'content':json.dumps(result)}}}
    def runjob(self,call=None):
        self.job.write_text(json.dumps(self.data))
        with patch.object(engine,'private_guard'),patch.object(engine,'verify_skills',return_value={'verified_files':138}):
            return r.run(self.job,self.out,infer=call or self.infer,identity=self.identity)
    def test_full_mock_path_passes_controller_but_does_not_authorize_release(self):
        got=self.runjob();self.assertTrue(got['qualified']);self.assertTrue(got['release_candidate']);self.assertEqual(got['minimum_score'],9.5)
        dup=json.loads((self.out/'duplicate-independent-review.json').read_text());self.assertTrue(dup['complete_active_scope_verified'])
    def test_missing_qualification_class_fails_closed(self):
        self.data['qualification_cases']=self.data['qualification_cases'][:-1]
        with self.assertRaises(r.ReviewError):self.runjob()
    def test_missing_review_class_fails_closed(self):
        self.data['review_checks']=self.data['review_checks'][:-1]
        with self.assertRaises(r.ReviewError):self.runjob()
    def test_failed_fixture_prevents_card_scoring(self):
        def bad(images,prompt,schema,**kw):
            out=self.infer(images,prompt,schema,**kw)
            if self.calln==1:out['result']['defect']=False;out['raw_response']['message']['content']=json.dumps(out['result'])
            return out
        got=self.runjob(bad);self.assertFalse(got['qualified']);self.assertFalse(got['release_candidate']);self.assertEqual(got['checks'],[])
    def test_blocking_visual_prevents_release_candidate(self):
        def bad(images,prompt,schema,**kw):
            out=self.infer(images,prompt,schema,**kw)
            if self.calln==8:out['result']['blocking_defect']=True;out['raw_response']['message']['content']=json.dumps(out['result'])
            return out
        self.assertFalse(self.runjob(bad)['release_candidate'])
    def test_unresolved_coverage_prevents_release_candidate(self):
        def bad(images,prompt,schema,**kw):
            out=self.infer(images,prompt,schema,**kw)
            if 'complete_active_scope_verified' in schema['properties']:
                out['result']['score']=8;out['result']['complete_active_scope_verified']=False;out['result']['unresolved_items']=['scope gap'];out['raw_response']['message']['content']=json.dumps(out['result'])
            return out
        self.assertFalse(self.runjob(bad)['release_candidate'])

if __name__=='__main__':unittest.main()
