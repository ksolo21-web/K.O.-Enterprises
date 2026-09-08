"""Regression tests for orchestration, not a visual approval of territory cards."""
import contextlib
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import fitz
import engine as e

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'})
        self.environment.start()
    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()
    def write(self, name, text='x'):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text); return p
    def recipe(self):
        template = self.root / 'blank.pdf'
        with fitz.open() as doc:
            page = doc.new_page(width=450, height=320)
            page.draw_rect(fitz.Rect(0,0,100,320), color=(.1,.1,.1), fill=(.1,.1,.1))
            page.insert_text((5,310),'SYNTHETIC TEMPLATE',fontsize=5)
            doc.save(template)
        source = self.root / 'source.pdf'
        with fitz.open() as doc:
            page=doc.new_page(width=300,height=280)
            page.draw_line(fitz.Point(20,140),fitz.Point(280,140),color=(.1,.8,.1),width=5)
            page.insert_text((95,130),'SYNTHETIC ROAD',fontsize=10)
            doc.save(source)
        recipe={'mode':'preserve_supplied_map','approved_blank_template':True,
                'source_class':'individually_approved_map','filename':'Territory - 999.pdf',
                'template':{'file':'blank.pdf','sha256':e.sha(template)},
                'map':{'file':'source.pdf','page':0,'sha256':e.sha(source)},
                'map_box':[110,20,440,300], 'approved_font_resources':['helv'],
                'approved_texts':[{'box':[5,10,97,60],'text':'TERRITORY\n999','size':11,'fontname':'helv'}]}
        path=self.root/'recipe.json'; e.json_write(path,recipe)
        return path,recipe
    def test_confined_path(self):
        self.write('a.txt'); self.assertEqual(e.within(self.root,'a.txt'),self.root/'a.txt')
    def test_traversal_rejected(self):
        for value in ('../escape','/tmp/a','a\\b','C:/a','a/../../b',''):
            with self.subTest(value=value), self.assertRaises(e.GateError):e.within(self.root,value, must_exist=False)
    def test_symlink_escape_rejected(self):
        (self.root/'link').symlink_to('/tmp')
        with self.assertRaises(e.GateError):e.within(self.root,'link/a',must_exist=False)
    def test_hash_change_rejected(self):
        p=self.write('a.txt'); record={'file':'a.txt','sha256':e.sha(p)}
        e.pinned(self.root,record);p.write_text('changed')
        with self.assertRaises(e.GateError):e.pinned(self.root,record)
    def test_missing_hash_rejected(self):
        with self.assertRaises(e.GateError):e.pinned(self.root,{'file':'a.txt'})
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(e.GateError):e.json_read(self.write('a.json','{"pass":true,"pass":false}'))
    def test_nonfinite_json_rejected(self):
        with self.assertRaises(e.GateError):e.json_read(self.write('a.json','{"score":NaN}'))
    def test_exact_ten_required(self):
        base={'overall_score':10,'categories':dict.fromkeys(e.CATEGORIES,10)}
        e.score_guard(base)
        for score in (0,8,9,9.99,9.999999,10.1,True):
            item=copy.deepcopy(base);item['overall_score']=score
            with self.subTest(score=score),self.assertRaises(e.GateError):e.score_guard(item)
    def test_one_category_failure_cannot_be_averaged(self):
        for category in e.CATEGORIES:
            item={'overall_score':10,'categories':dict.fromkeys(e.CATEGORIES,10)}
            item['categories'][category]={'score':9.99}
            with self.subTest(category=category),self.assertRaises(e.GateError):e.score_guard(item)
    def test_missing_category_rejected(self):
        with self.assertRaises(e.GateError):e.score_guard({'overall_score':10,'categories':{}})
    def test_public_ci_private_ingestion_blocked(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),self.assertRaises(e.GateError):e.private_guard()
    def test_rect_validation(self):
        for value in ([0,0,0,1],[2,2,1,1],[0,0,float('inf'),1],[False,0,1,1],[0,1]):
            with self.subTest(value=value),self.assertRaises(e.GateError):e.rect(value)
    def test_build_preserves_sources_and_never_approves(self):
        path,recipe=self.recipe();target=self.root/recipe['filename']
        before={r['file']:r['sha256'] for r in (recipe['map'],recipe['template'])}
        receipt=e.build(path,target)
        self.assertFalse(receipt['release_ready'])
        for name,digest in before.items():self.assertEqual(e.sha(self.root/name),digest)
        self.assertEqual(e.inspect_pdf(target)['pages'],1)
        with fitz.open(target) as doc:self.assertIn('SYNTHETIC ROAD',doc[0].get_text())
    def test_existing_candidate_never_overwritten(self):
        path,recipe=self.recipe();target=self.root/recipe['filename'];target.write_bytes(b'KEEP')
        with self.assertRaises(e.GateError):e.build(path,target)
        self.assertEqual(target.read_bytes(),b'KEEP')
    def test_unapproved_or_legacy_source_blocked(self):
        for field,value in (('approved_blank_template',False),('source_class','legacy_update_candidate'),('mode','vector_rebuild')):
            path,recipe=self.recipe();recipe[field]=value;e.json_write(path,recipe)
            with self.subTest(field=field),self.assertRaises(e.GateError):e.build(path,self.root/recipe['filename'])
    def test_clipped_map_box_blocked(self):
        path,recipe=self.recipe();recipe['map_box']=[100,0,451,300];e.json_write(path,recipe)
        with self.assertRaises(e.GateError):e.build(path,self.root/recipe['filename'])
    def test_template_text_cannot_touch_map(self):
        path,recipe=self.recipe();recipe['approved_texts'][0]['box']=[120,30,200,80];e.json_write(path,recipe)
        with self.assertRaises(e.GateError):e.build(path,self.root/recipe['filename'])
    def test_text_overflow_rejected_without_shrinking(self):
        path,recipe=self.recipe();recipe['approved_texts'][0]['text']='TOO LONG '*100;e.json_write(path,recipe)
        with self.assertRaises(e.GateError):e.build(path,self.root/recipe['filename'])
    def test_noncanonical_filename_blocked(self):
        path,recipe=self.recipe()
        with self.assertRaises(e.GateError):e.build(path,self.root/'Territory-999.pdf')
    def test_front_size_boundary_rejected(self):
        p=self.root/'large.pdf';p.write_bytes(b'x'*300000)
        with self.assertRaises(e.GateError):e.inspect_pdf(p)
    def test_two_page_front_blocked(self):
        p=self.root/'double.pdf'
        with fitz.open() as doc:doc.new_page();doc.new_page();doc.save(p)
        with self.assertRaises(e.GateError):e.inspect_pdf(p)
    def test_capture_reuses_no_directory(self):
        with patch.object(e,'verify_skills',return_value={}),self.assertRaises(e.GateError):e.capture(self.root/'a.pdf',self.root)
    def test_model_calls_require_cloud_off(self):
        with patch.dict(os.environ,{'OLLAMA_NO_CLOUD':'0'}),self.assertRaises(e.GateError):e.local_review([], '', self.root/'review.json')
    def test_cloud_model_names_rejected(self):
        with patch.dict(os.environ,{'OLLAMA_NO_CLOUD':'1'}),self.assertRaises(e.GateError):e.local_review([self.write('a.png')], '', self.root/'review.json',model='cloud:cloud')
    def test_timeout_is_a_failure(self):
        result=e.run_checked([e.sys.executable,'-c','import time;time.sleep(1)'],timeout=.01)
        self.assertEqual(result['returncode'],124)
    def test_archived_sources_are_complete(self):
        lock=e.json_read(e.ROOT/'source-lock.json')
        self.assertEqual(lock['file_count'],138)
        self.assertEqual(set(lock['required_skills']),set(e.SKILL_NAMES))
        self.assertRegex(lock['manifest_sha256'],r'^[0-9a-f]{64}$')
    def test_original_dependency_identity_when_installed(self):
        # CI must explicitly report missing vendor rather than claim an installed skill.
        if not e.source_root().exists():
            with self.assertRaises(e.GateError):e.verify_skills()
        else:self.assertEqual(e.verify_skills()['verified_files'],138)

if __name__=='__main__':unittest.main(verbosity=2)
