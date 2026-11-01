"""Offline A10 evidence replay; no model inference or benchmark accuracy claim."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from inspection_engine.visual_stage import VisualStageError,project_visual_stage,preserve_deferred_packet,MAX_VISUAL_PROMPT_BYTES

ARTIFACT=Path('/mnt/data/HomeInspection_A10_Real_Run_Evidence.zip')


class VisualStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARTIFACT.is_file():raise unittest.SkipTest('Exact A10 evidence archive not available')
        with zipfile.ZipFile(ARTIFACT) as z:
            cls.request=json.loads(z.read('trial/invocations/0001-writer.request.json'))

    def test_real_a10_replay_under_budget(self):
        d=self.request
        p,r=project_visual_stage(d['prompt'],d['generation_schema'])
        print('A10 visual bytes',r['visual_context_bytes'],'baseline',r['full_context_bytes'])
        self.assertLessEqual(r['visual_context_bytes'],MAX_VISUAL_PROMPT_BYTES)
        self.assertLess(r['visual_context_bytes'],r['full_context_bytes']*.5)
        self.assertIn('P0001',p)
        self.assertIn('cladding_type',p)
        self.assertIn('UNRECORDED_FEATURE_TASKS_JSON',p)
        self.assertIn('NO_CUSTOMER_RELEASE',p)
        self.assertFalse(r['customer_release_allowed'])
        self.assertFalse(r['latency_improvement_verified'])
        self.assertFalse(r['deferred_context_retained_by_caller'])
        self.assertNotIn('EPA_MOISTURE',p)
        self.assertNotIn('BUILDING_SCIENCE_DIFFERENTIAL',p)
        self.assertEqual(r['provider_schema_sha256'],d['generation_schema_sha256'])
        self.assertEqual(r['full_original_prompt_sha256'],d['prompt_sha256'])

    def test_memory_and_evidence_json_unchanged(self):
        p,_=project_visual_stage(self.request['prompt'],self.request['generation_schema'])
        def get(s,field):return json.loads(next(x.partition(': ')[2] for x in s.splitlines() if x.startswith(field+': ')))
        for name in ('EVIDENCE_CONTEXT_JSON','OBSERVATION_MEMORY_JSON','UNRECORDED_FEATURE_TASKS_JSON'):
            self.assertEqual(get(self.request['prompt'],name),get(p,name))

    def test_original_input_object_unchanged(self):
        a=copy.deepcopy(self.request)
        project_visual_stage(a['prompt'],a['generation_schema'])
        self.assertEqual(a,self.request)

    def test_reject_changed_schema(self):
        s=copy.deepcopy(self.request['generation_schema'])
        s['properties']['candidates']['maxItems']=500
        with self.assertRaisesRegex(VisualStageError,'digest'):project_visual_stage(self.request['prompt'],s)

    def test_refuse_missing_memory(self):
        lines=[x for x in self.request['prompt'].splitlines() if not x.startswith('OBSERVATION_MEMORY_JSON: ')]
        with self.assertRaises(VisualStageError):project_visual_stage('\n'.join(lines),self.request['generation_schema'])

    def test_duplicate_memory_refused(self):
        row=next(x for x in self.request['prompt'].splitlines() if x.startswith('OBSERVATION_MEMORY_JSON: '))
        with self.assertRaises(VisualStageError):project_visual_stage(self.request['prompt']+'\n'+row,self.request['generation_schema'])

    def test_oversized_memory_refused_without_loss(self):
        raw=self.request['prompt'];row=next(x for x in raw.splitlines() if x.startswith('OBSERVATION_MEMORY_JSON: '))
        data=json.loads(row.partition(': ')[2]);data['notes']='x'*3900
        edited=raw.replace(row,'OBSERVATION_MEMORY_JSON: '+json.dumps(data))
        with self.assertRaisesRegex(VisualStageError,'budget'):project_visual_stage(edited,self.request['generation_schema'])

    def test_incomplete_coverage_hold_refused(self):
        raw=self.request['prompt'];row=next(x for x in raw.splitlines() if x.startswith('ASSIGNED_COVERAGE_TASKS_JSON: '))
        tasks=json.loads(row.partition(': ')[2]);tasks[0].pop('physical_check_required')
        edited=raw.replace(row,'ASSIGNED_COVERAGE_TASKS_JSON: '+json.dumps(tasks))
        with self.assertRaisesRegex(VisualStageError,'coverage'):project_visual_stage(edited,self.request['generation_schema'])

    def test_complete_deferred_context_retained_under_matching_hash(self):
        prompt,profile=project_visual_stage(self.request['prompt'],self.request['generation_schema'])
        source=preserve_deferred_packet(self.request['prompt'],profile,invocation_id='WO-0001:I01',evidence_id='P0001')
        self.assertEqual(source['full_prompt'],self.request['prompt'])
        self.assertEqual(source['full_prompt_sha256'],self.request['prompt_sha256'])
        self.assertFalse(source['qualified_review_completed'])
        self.assertFalse(source['customer_release_allowed'])
        self.assertGreater(len(source['full_prompt']),len(prompt))

    def test_changed_original_cannot_be_bound_to_old_visual_receipt(self):
        _,profile=project_visual_stage(self.request['prompt'],self.request['generation_schema'])
        with self.assertRaisesRegex(VisualStageError,'hash mismatch'):
            preserve_deferred_packet(self.request['prompt']+' alteration',profile,invocation_id='WO-0001:I01',evidence_id='P0001')

    def test_limited_model_output_and_uncertainty_still_expected(self):
        p,_=project_visual_stage(self.request['prompt'],self.request['generation_schema'])
        for word in ['At most 3 distinct visible candidates','requests:[]','review_pending',
                     'Never diagnose root cause','NO_CUSTOMER_RELEASE']:
            self.assertIn(word,p)


if __name__=='__main__':unittest.main()
