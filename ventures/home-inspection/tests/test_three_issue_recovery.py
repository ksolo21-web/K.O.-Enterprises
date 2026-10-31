"""Algorithm/controlled-provider tests only. No real cases or field-accuracy evidence."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from inspection_engine.serious_defect_benchmark import score_serious_defects,BenchmarkBlock,SYSTEMS,METRIC_REVIEW_PENDING
from inspection_engine.field_validation_v7 import evaluation_summary
from inspection_engine.agents import plan_specialists,execute_specialists,SYSTEM_OWNER
from inspection_engine.coverage_workflow import (inspection_scope,build_work_orders,attach_plan,task_dispositions,report_holds)
from inspection_engine.adjudication import entries,memory_context,adjudicate,validate_record
from inspection_engine.critic import review_specialist_dossier
from inspection_engine.core import DataError,sha256,blockers,record_status


def algorithm_case(i=0,system='electrical'):
    # Deliberately fabricated metadata to exercise scorer paths; not collected holdout data.
    return {'case_id':'ALGORITHM-ONLY-'+str(i),'synthetic':False,'consented_for_evaluation':True,
        'evidence_sha256':'a'*64,'partition':'locked_holdout','training_overlap':False,
        'qualified_labeler_id':'TEST-ONLY-A','independent_adjudicator_id':'TEST-ONLY-B',
        'scope':'residential' if i%2 else 'commercial','jurisdiction':'MI',
        'labels':[{'label_id':'L1','severity':'critical','system':system,'status':'adjudicated'}]}


def algorithm_prediction(c,pid='P1',**updates):
    return dict({'case_id':c['case_id'],'prediction_id':pid,'system':c['labels'][0]['system'],
        'matched_label_id':'L1','human_match_verified':True},**updates)


def protocol():
    return {'version':7,'consent_required':True,'qualified_inspector_signature_required':True,
        'independent_label_review_required':True,'holdout_locked_before_inference':True,
        'training_case_exclusion':True,'min_real_cases':100,'min_critical':30,
        'protocol_sha256':'a'*64,'protocol_owner_signature_sha256':'b'*64}


class BenchmarkRecovery(unittest.TestCase):
    def test_same_label_unverified_prediction_counts_separately(self):
        c=algorithm_case();ds=[algorithm_prediction(c),algorithm_prediction(c,'P2',human_match_verified=False)]
        r=score_serious_defects([c],ds)
        self.assertEqual(r['human_verified_precision'],.5)
        self.assertEqual(r['true_positive_predictions'],1);self.assertEqual(r['evaluated_predictions'],2)
        self.assertEqual(r['unmatched_or_unverified_predictions'][0]['prediction_id'],'P2')
        self.assertEqual(r['critical_misses'],[])

    def test_same_label_wrong_system_verified_prediction_is_false_positive(self):
        c=algorithm_case();r=score_serious_defects([c],[algorithm_prediction(c),algorithm_prediction(c,'P2',system='roof')])
        self.assertEqual(r['human_verified_precision'],.5);self.assertEqual(r['critical_misses'],[])

    def test_eleven_extra_predictions_cannot_hide_behind_one_label(self):
        c=algorithm_case();ds=[algorithm_prediction(c)]+[algorithm_prediction(c,str(i),human_match_verified=False) for i in range(11)]
        r=score_serious_defects([c],ds)
        self.assertEqual(len(r['unmatched_or_unverified_predictions']),11)
        self.assertAlmostEqual(r['human_verified_precision'],1/12)

    def test_match_requires_exact_boolean(self):
        c=algorithm_case()
        for v in (0,1,None,'true'):
            with self.subTest(v=v),self.assertRaises(BenchmarkBlock):
                score_serious_defects([c],[algorithm_prediction(c,human_match_verified=v)])

    def test_duplicate_genuine_match_still_rejected(self):
        c=algorithm_case()
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[algorithm_prediction(c),algorithm_prediction(c,'P2')])

    def cohort(self):
        systems=sorted(SYSTEMS);cs=[algorithm_case(i,systems[i%len(systems)]) for i in range(100)]
        return cs,[algorithm_prediction(c) for c in cs]

    def test_metric_pass_reaches_external_audit_without_release(self):
        cs,ds=self.cohort();r=evaluation_summary(cs,ds,protocol())
        self.assertEqual(r['scoring']['status'],METRIC_REVIEW_PENDING)
        self.assertEqual(r['status'],'ADJUDICATION_EVIDENCE_AUDIT_REQUIRED')
        self.assertFalse(r['field_detection_accuracy_verified']);self.assertFalse(r['customer_release_allowed'])
        self.assertFalse(r['identity_and_qualification_independently_authenticated'])
        self.assertFalse(r['scoring']['production_release_allowed'])

    def test_same_label_extras_can_block_previously_passing_cohort(self):
        cs,ds=self.cohort();ds += [algorithm_prediction(cs[0],'FP'+str(i),human_match_verified=False) for i in range(6)]
        r=evaluation_summary(cs,ds,protocol());self.assertEqual(r['status'],'BLOCKED')
        self.assertLess(r['scoring']['human_verified_precision'],.95)


class CoverageRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        Image.new('RGB',(240,180),'gray').save(self.root/'photo.png')
        self.doc={'project_id':'SYNTHETIC-COVERAGE-ONLY','property':{'label':'Controlled test',
            'inspection_date':'2026-10-31','synthetic':True,'building_type':'residential'},
            'media':[{'id':'P1','kind':'photo','path':'photo.png','area':'garage','sha256':sha256(self.root/'photo.png')}],
            'observations':[],'findings':[],'equipment':[],'limitations':[]}

    def stage(self,claim=False):
        def writer(image,prompt):
            self.assertLessEqual(len(prompt.encode()),20000)
            self.assertIn('ASSIGNED_COVERAGE_TASKS_JSON:',prompt)
            candidates=[{'type':'potential_concern','system':'interior','description':'Possible mark on illustrative door panel',
                'location':'Garage panel','status':'partially_observed','bbox':[.1,.1,.5,.5]}] if claim else []
            return {'candidates':candidates,'requests':[]}
        return execute_specialists(self.doc,self.root,writer,media_ids=['P1'],provider_id='controlled-writer')

    def technical(self,d,ds,calls=None):
        def reviewer(image,prompt):
            if calls is not None:calls.append(prompt)
            with Image.open(io.BytesIO(image)) as im:self.assertEqual(im.size,(1800,960))
            return {'decision':'visually_plausible','reason':'Controlled view usefulness only','missing_evidence':'Qualified inspector physical checks still required'}
        return review_specialist_dossier(d,self.root,ds,reviewer,reviewer_id='Q02',provider_id='controlled-Q02')

    def reasoner(self,prompt,schema):
        packet=json.loads(prompt.split('LEDGER_PACKET_JSON: ')[1])
        return {'decisions':[{'entry_id':e['entry_id'],'decision':'distinct','related_ids':[],
            'reason':'Controlled reconciliation only','evidence_gap':''} for e in packet['queue']['entries']]}

    def test_whole_case_thirteen_hazards_and_two_residential_specialties_assigned(self):
        plan=build_work_orders(self.doc);self.assertEqual(len(plan['tasks']),15)
        self.assertEqual({t['system'] for t in plan['tasks'] if t['kind']=='hazard_sweep'},set(SYSTEMS))
        self.assertTrue(all(t['assigned_to']==SYSTEM_OWNER[t['system']] for t in plan['tasks']))
        self.assertTrue(all(t['physical_check_required'] for t in plan['tasks']))
        self.assertFalse(plan['tasks_are_findings']);self.assertFalse(plan['customer_release_allowed'])

    def test_specialty_aliases_route_to_T05_with_stable_task_ids(self):
        for area,task in [('garage','GARAGE_DOOR'),('fireplace','FIREPLACE_HEARTH')]:
            self.doc['media'][0]['area']=area;p=plan_specialists(self.doc)
            self.assertEqual(p['jobs'][0]['assigned_to'],'T05')
            self.assertIn('SPECIALTY:'+task,p['jobs'][0]['coverage_task_ids'])

    def test_generic_interior_does_not_prove_specialty_evidence(self):
        self.doc['media'][0]['area']='interior'
        self.assertTrue(all(not t['evidence_ids'] for t in build_work_orders(self.doc)['tasks'] if t['kind']=='specialty'))

    def test_commercial_scope_does_not_reuse_residential_specialties(self):
        self.doc['property']['building_type']='commercial_pca';p=build_work_orders(self.doc)
        self.assertEqual([t['id'] for t in p['tasks'] if t['kind']=='specialty'],['SPECIALTY:COMMERCIAL_FIRE_LIFE_SAFETY'])

    def test_unknown_and_conflicting_scope_held(self):
        self.doc['property'].pop('building_type');self.assertIsNone(inspection_scope(self.doc))
        with self.assertRaises(DataError):build_work_orders(self.doc)
        self.doc['coverage_work_orders']={};self.assertTrue(report_holds(self.doc))
        self.doc['property'].update(building_type='commercial',inspection_scope='residential')
        with self.assertRaises(DataError):build_work_orders(self.doc)

    def test_bound_plan_changes_when_date_source_catalog_or_policy_changes(self):
        a=build_work_orders(self.doc)
        d=copy.deepcopy(self.doc);d['media'][0]['sha256']='b'*64
        self.assertNotEqual(a['plan_sha256'],build_work_orders(d)['plan_sha256'])
        d=copy.deepcopy(self.doc);d['property']['inspection_date']='2026-10-30'
        self.assertNotEqual(a['plan_sha256'],build_work_orders(d)['plan_sha256'])
        with patch('inspection_engine.inspection_policy.policy_digest',return_value='b'*64):
            self.assertNotEqual(a['plan_sha256'],build_work_orders(self.doc)['plan_sha256'])
        from inspection_engine.hazard_sweep import load_hazard_sweep
        catalog=load_hazard_sweep();catalog['topics'][0]['signal']+=' Test-only change'
        with patch('inspection_engine.coverage_workflow.load_hazard_sweep',return_value=catalog):
            self.assertNotEqual(a['plan_sha256'],build_work_orders(self.doc)['plan_sha256'])

    def test_zero_claim_execution_preserves_open_work_without_fabricated_findings(self):
        d,ds=self.stage();self.assertEqual(d['observations']+d['findings'],[])
        self.assertEqual(len(entries(d)),15);self.assertEqual(ds['proposals'],[])
        self.assertTrue(any('Coverage SPECIALTY:GARAGE_DOOR' in h for h in blockers(d)))

    def test_Q02_actually_reviews_each_available_task_photo_even_without_claims(self):
        d,ds=self.stage();calls=[];q=self.technical(d,ds,calls)
        self.assertEqual(len(calls),2);self.assertEqual(q['actual_image_assessments'],2)
        self.assertEqual(len(q['coverage_items']),2);self.assertEqual(len(q['coverage_missing_evidence_task_ids']),13)
        self.assertTrue(all('COVERAGE_TASK_DATA:' in c for c in calls))
        disp=task_dispositions(d,q)
        self.assertEqual(disp['coverage:SPECIALTY:FIREPLACE_HEARTH'][0]['review_kind'],'DETERMINISTIC_MISSING_EVIDENCE_NOT_MODEL_REVIEW')
        self.assertFalse(q['customer_release_allowed'])

    def test_Q02_missing_all_views_is_explicitly_zero_model_calls(self):
        d=attach_plan(dict(self.doc,media=[]));ds={'project_id':d['project_id'],'provider':'controlled-writer','proposals':[],'tool_requests':[]}
        calls=[];q=self.technical(d,ds,calls)
        self.assertEqual(calls,[]);self.assertEqual(q['actual_image_assessments'],0)
        self.assertEqual(len(q['coverage_missing_evidence_task_ids']),15)

    def test_Q02_budget_fails_before_any_model_call(self):
        d,ds=self.stage();calls=[]
        with self.assertRaises(DataError):
            review_specialist_dossier(d,self.root,ds,lambda i,p:calls.append(p),reviewer_id='Q02',provider_id='other',max_proposals=1)
        self.assertEqual(calls,[])

    def test_Q02_cannot_reuse_missing_stale_or_unexpected_task_photo_record(self):
        d,ds=self.stage();q=self.technical(d,ds)
        for mode in ('missing','hash','task','unknown_photo','duplicate','not_hex'):
            bad=copy.deepcopy(q)
            if mode=='missing':bad['coverage_items'].pop()
            elif mode=='hash':bad['coverage_items'][0]['source_sha256']='b'*64
            elif mode=='task':bad['coverage_items'][0]['task_sha256']='b'*64
            elif mode=='unknown_photo':bad['coverage_items'].append(dict(bad['coverage_items'][0],source_media_id='UNKNOWN'))
            elif mode=='duplicate':bad['coverage_items'].append(copy.deepcopy(bad['coverage_items'][0]))
            else:
                d=copy.deepcopy(d);d['media'][0]['sha256']='z'*64
            with self.subTest(mode=mode),self.assertRaises(DataError):task_dispositions(d,bad)

    def test_shared_ledger_links_claims_and_tasks_without_crowding_writer_memory(self):
        d,ds=self.stage(True);records=entries(d);claim=next(e for e in records if e['type']=='potential_concern')
        task=next(e for e in records if e.get('task_id')=='SPECIALTY:GARAGE_DOOR')
        self.assertIn(task['task_id'],claim['coverage_task_ids']);self.assertIn(claim['entry_id'],task['related_claim_ids'])
        self.assertEqual(memory_context(d,[],['interior'])['records'][0]['entry_id'],claim['entry_id'])

    def test_Q03_distinct_preserves_physical_and_missing_evidence_holds(self):
        d,ds=self.stage(True);q=self.technical(d,ds);a=adjudicate(d,self.root,q,self.reasoner,provider_id='controlled-Q03')
        self.assertEqual(len(a['decisions']),16);self.assertEqual(len(validate_record(d,a)),15)
        self.assertEqual(a['status'],'ADJUDICATION_HOLD');self.assertFalse(a['customer_release_allowed'])
        self.assertTrue(all(x['resolution']=='HOLD' and x['coverage_hold_preserved'] for x in a['decisions'] if x['entry_id'].startswith('coverage:')))
        d['adjudication']=a;self.assertTrue(blockers(d))
        self.assertIn('NOT FOR CLIENT RELEASE',record_status(d))
        bad=copy.deepcopy(a);bad['decisions'][-1]['resolution']='INTERNAL_DRAFT_ONLY'
        with self.assertRaises(DataError):validate_record(d,bad)

    def test_plan_deletion_or_cached_completion_does_not_remove_report_holds(self):
        d,_=self.stage();d.pop('coverage_work_orders');d.pop('adjudication_queue')
        self.assertTrue(any('missing or stale' in h for h in blockers(d)))
        d=attach_plan(d);d['coverage_work_orders']['tasks'][0]['state']='COMPLETE'
        self.assertTrue(any('missing or stale' in h for h in blockers(d)))
        self.assertTrue(any('Coverage HAZARD:' in h for h in blockers(d)))

    def test_saved_Q03_fails_after_source_or_scope_change(self):
        d,ds=self.stage();q=self.technical(d,ds);a=adjudicate(d,self.root,q,self.reasoner,provider_id='controlled-Q03')
        for change in ('source','scope'):
            bad=copy.deepcopy(d)
            if change=='source':bad['media'][0]['sha256']='b'*64
            else:bad['property']['building_type']='commercial'
            with self.subTest(change=change),self.assertRaises(DataError):validate_record(bad,a)

    def test_input_not_mutated(self):
        before=copy.deepcopy(self.doc);self.stage(True);self.assertEqual(before,self.doc)
