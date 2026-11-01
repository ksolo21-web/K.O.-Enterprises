"""Offline/controlled checks only; no inference, tokenizer or latency claims."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import shutil,tempfile,unittest,zipfile
from unittest.mock import patch
from PIL import Image
from inspection_engine.agents import execute_specialists,specialist_schema
from inspection_engine.core import DataError,sha256,blockers
from inspection_engine.input_compaction import compact_writer_prompt,compact_json,digest,schema_guide,TASK_METADATA
from scripts.profile_writer_input import profile_request

ROOT=Path(__file__).resolve().parents[1]
SYSTEMS=['site','foundation','subfloor','framing','exterior','roof','attic','interior','electrical','plumbing','water_heating','hvac','crawlspace']


def payload(prompt,label):return json.loads(prompt.split(label+': ',1)[1].splitlines()[0])


class CompactInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        Image.new('RGB',(160,120),'gray').save(self.root/'photo.png')
        self.doc={'project_id':'SYNTHETIC-INPUT-COMPARISON','property':{'label':'Controlled','inspection_date':'2026-10-31',
            'synthetic':True,'building_type':'residential'},
            'media':[{'id':'P1','kind':'photo','path':'photo.png','area':'exterior','sha256':sha256(self.root/'photo.png')}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}
    def capture(self,compact,doc=None,reply=None,root=None):
        seen=[];events=[]
        def provider(image,prompt,**kw):
            seen.append({'image':image,'prompt':prompt,'schema':kw.get('schema')})
            return reply(image,prompt,**kw) if reply else {'candidates':[],'requests':[]}
        d,ds=execute_specialists(doc or self.doc,root or self.root,provider,media_ids=['P1'],
            provider_id='controlled',provider_accepts_schema=compact,audit_event=events.append)
        return seen,d,ds,events
    def compare_knowledge(self,old,new):
        for line in old.splitlines():
            key,sep,value=line.partition(': ')
            if key=='OUTPUT_JSON_SCHEMA':continue
            if key=='ASSIGNED_COVERAGE_TASKS_JSON':
                before=json.loads(value);after=payload(new,key)
                self.assertEqual(after,[{k:v for k,v in t.items() if k not in TASK_METADATA} for t in before])
            elif sep and (key.endswith('_JSON') or key=='MANDATORY_SCOPE' or key.startswith('EXPERT_DOMAIN ')):
                self.assertEqual(json.loads(value),payload(new,key),key)
            else:self.assertIn(line,new.splitlines())
    def test_all_thirteen_systems_keep_knowledge_image_schema_and_canonical_records(self):
        for system in SYSTEMS:
            with self.subTest(system=system):
                doc=deepcopy(self.doc);doc['media'][0]['area']=system
                legacy,d1,_,_=self.capture(False,doc);compact,d2,ds,events=self.capture(True,doc)
                before,after=legacy[0],compact[0]
                self.assertEqual(before['image'],after['image'])
                self.assertEqual(payload(before['prompt'],'OUTPUT_JSON_SCHEMA'),after['schema'])
                self.compare_knowledge(before['prompt'],after['prompt'])
                self.assertEqual(d1,d2);self.assertTrue(blockers(d2));self.assertFalse(ds['customer_release_allowed'])
                self.assertLess(len(after['prompt']),len(before['prompt']))
                receipt=ds['input_profiles'][0]
                self.assertEqual(receipt['provider_schema_sha256'],digest(after['schema']))
                self.assertEqual(receipt['task_projection']['canonical_task_cards'],payload(before['prompt'],'ASSIGNED_COVERAGE_TASKS_JSON'))
                self.assertTrue(any(e['kind']=='specialist_input_profile' for e in events))
    def test_legacy_two_argument_provider_retains_full_schema_and_no_projection(self):
        seen,_,ds,_=self.capture(False)
        self.assertIsNone(seen[0]['schema']);self.assertIn('OUTPUT_JSON_SCHEMA:',seen[0]['prompt'])
        self.assertNotIn('input_profiles',ds)
        self.assertIn('evidence_snapshot',payload(seen[0]['prompt'],'ASSIGNED_COVERAGE_TASKS_JSON')[0])
    def test_multisystem_schema_code_coupling_stays_at_transport(self):
        from inspection_engine import agents
        with patch.dict(agents.AREA_SYSTEMS,{'dual':('plumbing','water_heating')}):
            self.doc['media'][0]['area']='dual'
            old,_,_,_=self.capture(False);new,_,_,_=self.capture(True)
        self.assertEqual(payload(old[0]['prompt'],'OUTPUT_JSON_SCHEMA'),new[0]['schema'])
        branches=new[0]['schema']['properties']['candidates']['items']['anyOf']
        self.assertEqual({b['properties']['system']['enum'][0] for b in branches},{'plumbing','water_heating'})
        self.compare_knowledge(old[0]['prompt'],new[0]['prompt'])
    def test_MI_packet_and_policy_values_remain_identical(self):
        self.doc['property'].update(state='MI',county='Wayne',municipality='Westland',municipality_type='city')
        old,_,_,_=self.capture(False);new,_,_,_=self.capture(True)
        self.compare_knowledge(old[0]['prompt'],new[0]['prompt'])
        self.assertIn('GOVERNED_MICHIGAN_SOURCE_PACKET_JSON:',new[0]['prompt'])
    def test_required_fields_and_limits_are_in_readable_guidance(self):
        seen,_,_,_=self.capture(True);p=seen[0]['prompt']
        for value in ['candidates (max 12)','requests (max 1)','type,system,description (1-320 chars)',
            'observed|partially_observed|unknown','feature also requires feature_code','potential_concern forbids feature_code',
            'location is 1-100 chars','four numbers 0..1','current-view coordinates','Omit absent optional fields',
            'No extra keys','[0,0,1,1] is unchanged']:
            self.assertIn(value,p)
        self.assertNotIn('kind=video_still plus timestamp_seconds',p)
        g,_=schema_guide(specialist_schema(['exterior'],video_duration=4.25))
        self.assertIn('0 <= t < 4.25',g)
    def test_task_unknown_technical_fields_and_meaningful_whitespace_are_preserved(self):
        old,_,_,_=self.capture(False);p=old[0]['prompt'];cards=payload(p,'ASSIGNED_COVERAGE_TASKS_JSON')
        cards[0]['future_critical_warning']='Keep  two spaces\nand a new line'
        cards[0]['instructions']['future']='Unicode: \u6c34 and literal : separator'
        p=p.replace(next(l for l in p.splitlines() if l.startswith('ASSIGNED_COVERAGE_TASKS_JSON: ')),
            'ASSIGNED_COVERAGE_TASKS_JSON: '+json.dumps(cards))
        new,receipt=compact_writer_prompt(p,payload(p,'OUTPUT_JSON_SCHEMA'))
        after=payload(new,'ASSIGNED_COVERAGE_TASKS_JSON')[0]
        self.assertEqual(after['future_critical_warning'],cards[0]['future_critical_warning'])
        self.assertEqual(after['instructions'],cards[0]['instructions'])
        self.assertEqual(receipt['task_projection']['canonical_task_cards'],cards)
        for key in ['id','task_sha256','scope','state','physical_check_required','project_id','inspection_date']:
            self.assertEqual(after[key],cards[0][key])
    def test_input_memory_values_and_omission_counts_stay_intact(self):
        old,_,_,_=self.capture(False);p=old[0]['prompt'];mem=payload(p,'OBSERVATION_MEMORY_JSON')
        mem.update(records=[{'description':'a  b\n c : d','evidence_ids':['P1']}],omitted_from_prompt=7,relevant_total=8)
        p=p.replace(next(l for l in p.splitlines() if l.startswith('OBSERVATION_MEMORY_JSON: ')),
            'OBSERVATION_MEMORY_JSON: '+json.dumps(mem))
        new,_=compact_writer_prompt(p,payload(p,'OUTPUT_JSON_SCHEMA'))
        self.assertEqual(payload(new,'OBSERVATION_MEMORY_JSON'),mem)
    def test_compact_path_keeps_exact_duplicate_and_invalid_code_rejection(self):
        bad={'type':'feature','system':'exterior','feature_code':'invalid','description':'A mark','status':'observed'}
        with self.assertRaises(DataError):self.capture(True,reply=lambda *a,**k:{'candidates':[bad],'requests':[]})
        good=dict(bad,feature_code='cladding_type')
        with self.assertRaises(DataError):self.capture(True,reply=lambda *a,**k:{'candidates':[good,good],'requests':[]})
    def test_complete_prompt_budget_still_blocks_before_provider(self):
        with patch('inspection_engine.agents.build_knowledge_brief',return_value='K'*21000),self.assertRaises(DataError):self.capture(True)
    def test_schema_change_or_mismatch_fails_closed(self):
        old,_,_,_=self.capture(False);p=old[0]['prompt'];s=payload(p,'OUTPUT_JSON_SCHEMA')
        wrong=deepcopy(s);wrong['properties']['candidates']['maxItems']=11
        with self.assertRaises(DataError):compact_writer_prompt(p,wrong)
        s['properties']['candidates']['items']['anyOf'][0]['properties']['description']['pattern']='future constraint'
        p=p.replace(next(l for l in p.splitlines() if l.startswith('OUTPUT_JSON_SCHEMA: ')),'OUTPUT_JSON_SCHEMA: '+json.dumps(s))
        with self.assertRaises(DataError):compact_writer_prompt(p,s)
    def test_missing_or_duplicate_structured_labels_are_rejected(self):
        old,_,_,_=self.capture(False);p=old[0]['prompt'];s=payload(p,'OUTPUT_JSON_SCHEMA')
        with self.assertRaises(DataError):compact_writer_prompt(p.replace('OUTPUT_JSON_SCHEMA:','OTHER_SCHEMA:'),s)
        line=next(l for l in p.splitlines() if l.startswith('OBSERVATION_MEMORY_JSON: '))
        with self.assertRaises(DataError):compact_writer_prompt(p+line+'\n',s)
    def test_later_native_zoom_iterations_keep_context_and_images(self):
        captured=[]
        for compact in (False,True):
            root=self.root/str(compact);root.mkdir();shutil.copyfile(self.root/'photo.png',root/'photo.png')
            def reply(image,prompt,**kw):
                context=payload(prompt,'EVIDENCE_CONTEXT_JSON')
                return {'candidates':[],'requests':[{'kind':'zoom','bbox':[.1,.1,.7,.7]}] if context['iteration']==1 else []}
            captured.append(self.capture(compact,root=root,reply=reply)[0])
        self.assertEqual([s['image'] for s in captured[0]],[s['image'] for s in captured[1]])
        self.assertEqual(len(captured[1]),2)
        for a,b in zip(*captured):
            self.assertEqual(payload(a['prompt'],'EVIDENCE_CONTEXT_JSON'),payload(b['prompt'],'EVIDENCE_CONTEXT_JSON'))
            self.assertEqual(payload(a['prompt'],'OUTPUT_JSON_SCHEMA'),b['schema'])
    def test_profile_cannot_claim_token_latency_or_quality_evidence(self):
        _,_,ds,_=self.capture(True);r=ds['input_profiles'][0]
        for name in ('token_counts_measured','latency_benchmarked','observation_quality_benchmarked','customer_release_allowed'):
            self.assertIs(r[name],False)


class SavedA09ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        with zipfile.ZipFile(ROOT/'docs/evidence/A09/Home-Inspection-A09-Live-Evidence.zip') as z:z.extractall(self.root/'original')
        self.request=self.root/'original/trial/invocations/0001-writer.request.json'
    def test_actual_saved_request_profile_has_identical_image_schema_and_all_knowledge(self):
        original=self.request.read_bytes();r=profile_request(self.request,self.root/'new')
        self.assertEqual(r['original_characters'],11700);self.assertLess(r['characters'],11700)
        self.assertEqual(r['model_invocations'],0);self.assertTrue(r['image_bytes_unchanged']);self.assertTrue(r['response_schema_unchanged'])
        self.assertEqual(self.request.read_bytes(),original)
        before=json.loads(original);after=json.loads((self.root/'new/optimized_request.json').read_text())
        self.assertEqual(before['generation_schema'],after['generation_schema'])
        self.assertEqual(after['execution_kind'],'OFFLINE_NOT_EXECUTED');self.assertEqual(after['model_invocations'],0)
        self.assertNotIn('started_utc',after);self.assertNotIn('call_id',after)
        self.assertEqual(after['source_request_metadata']['call_id'],before['call_id'])
        self.assertEqual(after['source_request_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual((self.request.parent/before['image_path']).read_bytes(),(self.root/'new'/after['image_path']).read_bytes())
        CompactInputTests.compare_knowledge(self,before['prompt'],after['prompt'])
    def test_tampered_input_and_existing_output_refused(self):
        self.request.write_text(self.request.read_text().replace('A CLEARER','ALTERED'))
        record=json.loads(self.request.read_text());record['prompt']+=' altered';self.request.write_text(json.dumps(record))
        with self.assertRaises(DataError):profile_request(self.request,self.root/'new')
        self.assertFalse((self.root/'new').exists())
        with self.assertRaises(DataError):profile_request(self.request,self.root/'original')
