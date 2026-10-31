import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from inspection_engine.michigan_authority import (load_authorities,validate_authorities,
    applicable_references,build_michigan_brief,KnowledgeError)
from inspection_engine.case_verification import (validate_case_context,evaluate_finding,coverage_gaps)
from inspection_engine.agents import execute_specialists

class MichiganRegistryTests(unittest.TestCase):
    def setUp(self):self.data=load_authorities()
    def test_registry_valid_and_primary(self):self.assertEqual(len(validate_authorities(self.data)['sources']),10)
    def test_residential_2015_active_2026(self):
        p=applicable_references(building_type='residential_one_two_family',inspection_date='2026-10-31')
        ids={x['id'] for x in p['candidate_references']}
        self.assertIn('MI_RES_2015',ids)
        self.assertNotIn('MI_BUILDING_2021',ids)
        self.assertIn('MI_RES_2021_STAYED',p['excluded_reference_ids'])
        self.assertIn('MI_RES_ENERGY_2021_STAYED',p['excluded_reference_ids'])
        self.assertFalse(p['applicability_verified'])
    def test_commercial_2021_active(self):
        p=applicable_references(building_type='commercial_general',inspection_date='2026-10-31')
        ids={x['id'] for x in p['candidate_references']}
        self.assertIn('MI_BUILDING_2021',ids)
        self.assertIn('MI_COMM_ENERGY_2021',ids)
        self.assertNotIn('MI_RES_2015',ids)
    def test_before_2025_commercial_edition_not_applied(self):
        ids={x['id'] for x in applicable_references(building_type='commercial_general',inspection_date='2024-05-01')['candidate_references']}
        self.assertNotIn('MI_BUILDING_2021',ids)
    def test_stayed_cannot_become_effective_without_revision(self):
        d=copy.deepcopy(self.data)
        s=next(s for s in d['sources'] if s['id']=='MI_RES_2021_STAYED')
        s['effective_from']='2025-08-29'
        with self.assertRaises(KnowledgeError):validate_authorities(d)
    def test_fabricated_publisher_url_rejected(self):
        d=copy.deepcopy(self.data);d['sources'][0]['authority_url']='https://fake-michigan.gov/lara/codes'
        with self.assertRaises(KnowledgeError):validate_authorities(d)
    def test_duplicate_ids_rejected(self):
        d=copy.deepcopy(self.data);d['sources'][1]['id']=d['sources'][0]['id']
        with self.assertRaises(KnowledgeError):validate_authorities(d)
    def test_catalog_mutation_isolated(self):
        a=load_authorities();a['sources'][0]['edition']='2099'
        self.assertNotEqual(load_authorities()['sources'][0]['edition'],'2099')
    def test_unknown_occupancy_blocks_code_selection(self):
        with self.assertRaises(KnowledgeError):applicable_references(building_type='unknown',inspection_date='2026-10-31')
    def test_michigan_prompt_never_claims_legality(self):
        b=build_michigan_brief(['foundation','electrical'],'2026-10-31','residential_one_two_family')
        self.assertIn('MI_RES_2015',b)
        self.assertIn('MI_ELECTRICAL_2023',b)
        self.assertIn('UNVERIFIED',b)
    def test_unknown_property_no_editions_assumed(self):
        b=build_michigan_brief(['roof'],'','unverified')
        self.assertIn('occupancy is not verified',b)
        self.assertNotIn('MI_RES_2015',b)

class MichiganCaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        Image.new('RGB',(128,128),'white').save(self.root/'source.png')
        self.case={'case_id':'SYNTH-MI-1','state':'MI','county':'Oakland','municipality':'Auburn Hills',
                   'building_type':'residential_one_two_family','inspection_date':'2026-10-31',
                   'work_type':'visual_inspection','media':[{'id':'P1','path':'source.png',
                   'sha256':hashlib.sha256((self.root/'source.png').read_bytes()).hexdigest()}]}
        self.finding={'claim_type':'potential_defect','system':'foundation','feature_code':'visible_foundation_condition',
             'observed_symptom':'Visible irregular line on drawn foundation surface, not diagnosed.',
             'evidence_ids':['P1'],
             'cause_assessment':{'status':'hypotheses_only','hypotheses':[
                  {'possible_mechanism':'Possible shrinkage','alternative_explanation':'Settlement',
                   'verification_needed':'Qualified inspector must assess pattern and movement'}]}}
    def test_base_case(self):self.assertEqual(validate_case_context(self.case)['building_type'],'residential_one_two_family')
    def test_visible_concern_pending_not_verified(self):
        r=evaluate_finding(self.case,self.finding,self.root)
        self.assertEqual(r['status'],'EVIDENCE_LINKED_REVIEW_PENDING')
        self.assertFalse(r['cause_established']);self.assertFalse(r['customer_release_allowed'])
        self.assertEqual(len(r['evidence_receipts']),1)
    def test_wrong_hash_blocks(self):
        f=copy.deepcopy(self.case);f['media'][0]['sha256']='a'*64
        self.assertEqual(evaluate_finding(f,self.finding,self.root)['status'],'BLOCKED')
    def test_fake_source_id_blocks(self):
        f=copy.deepcopy(self.finding);f['evidence_ids']=['FAKE']
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_path_traversal_blocks(self):
        c=copy.deepcopy(self.case);c['media'][0]['path']='../unauthorized.png'
        self.assertEqual(evaluate_finding(c,self.finding,self.root)['status'],'BLOCKED')
    def test_symlink_to_outside_blocks(self):
        external=self.root.parent/'disallowed_evidence.tmp'
        external.write_bytes(b'synthetic')
        try:
            (self.root/'escape.png').symlink_to(external)
            c=copy.deepcopy(self.case);c['media'][0]['path']='escape.png';c['media'][0]['sha256']=hashlib.sha256(external.read_bytes()).hexdigest()
            self.assertEqual(evaluate_finding(c,self.finding,self.root)['status'],'BLOCKED')
        finally:external.unlink(missing_ok=True)
    def test_unknown_system_code_blocks(self):
        f=copy.deepcopy(self.finding);f['feature_code']='invented_code'
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_definitive_cause_blocks(self):
        f=copy.deepcopy(self.finding);f['cause_assessment']['status']='confirmed'
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_cause_requires_alternative_and_verification(self):
        f=copy.deepcopy(self.finding);f['cause_assessment']['hypotheses'][0].pop('alternative_explanation')
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_unobserved_not_no_defect(self):
        f=copy.deepcopy(self.finding);f['claim_type']='condition_clear'
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_categorical_code_compliance_rejected(self):
        f=copy.deepcopy(self.finding);f['observed_symptom']='This area is guaranteed safe and fully compliant.'
        self.assertEqual(evaluate_finding(self.case,f,self.root)['status'],'BLOCKED')
    def test_code_claim_with_no_ahj_or_section_blocks(self):
        f=copy.deepcopy(self.finding);f['claim_type']='code_violation';f['code_discipline']='building'
        r=evaluate_finding(self.case,f,self.root)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertIn('Building AHJ receipt required',r['blockers'])
    def test_code_pending_edition_blocks_even_with_ahj(self):
        f=copy.deepcopy(self.finding);f['claim_type']='code_violation';f['code_discipline']='building'
        f['provision_receipts']=[{'authority_id':'MI_RES_2021_STAYED','section':'R301.1','edition':'2021',
                                 'source_url':'https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open',
                                 'original_provision_text_confirmed_by':'SYNTH-REVIEW',
                                 'original_provision_review_authenticated':True}]
        r=evaluate_finding(self.case,f,self.root)
        self.assertIn('Code provision authority is not a candidate for this case',r['blockers'])
    def test_reviewer_claim_alone_not_approval(self):
        f=copy.deepcopy(self.finding);f['reviewer_decision']='approved';f['review_authenticated']=True
        self.assertFalse(evaluate_finding(self.case,f,self.root)['customer_release_allowed'])
    def test_unknown_municipality_blocks(self):
        c=copy.deepcopy(self.case);c['municipality']=''
        self.assertEqual(evaluate_finding(c,self.finding,self.root)['status'],'BLOCKED')
    def test_cover_all_46_codes_without_claiming_negative(self):
        r=coverage_gaps(self.case,[])
        self.assertEqual(r['required_feature_count'],46)
        self.assertEqual(r['documented_feature_count'],0)
        self.assertTrue(r['no_defect_absence_inferred'])
    def test_observation_counts_only_known_feature_and_evidence(self):
        r=coverage_gaps(self.case,[{'system':'foundation','feature_code':'visible_foundation_condition','evidence_ids':['P1']},
                                   {'system':'foundation','feature_code':'fake','evidence_ids':['P1']}])
        self.assertEqual(r['documented_feature_count'],1)
    def test_michigan_prompt_sent_to_role(self):
        doc={'project_id':'SYNTH-KNOW','property':{'label':'Synthetic house','inspection_date':'2026-10-31',
             'state':'MI','building_type':'residential_one_two_family','synthetic':True},
             'media':[{'id':'P0001','path':'source.png','kind':'photo','sha256':self.case['media'][0]['sha256'],'area':'foundation'}],
             'observations':[],'findings':[],'equipment':[],'limitations':[]}
        prompts=[]
        def provider(im,prompt):
            prompts.append(prompt)
            return {'candidates':[],'requests':[]}
        _,dossier=execute_specialists(doc,self.root,provider,media_ids=['P0001'])
        self.assertIn('MICHIGAN_SOURCE_POLICY',prompts[0]);self.assertIn('MI_RES_2015',prompts[0]);self.assertFalse(dossier['customer_release_allowed'])
        self.assertIn('NATIONAL_INSPECTION_POLICY_V4',prompts[0])
        self.assertIn('POLICY_DIGEST_SHA256',prompts[0])
        self.assertIn('embedded_knowledge_policy_sha256',dossier['plan'])
    def test_other_state_not_falsely_given_michigan_law(self):
        doc={'project_id':'SYNTH-KNOW','property':{'label':'Synthetic house','inspection_date':'2026-10-31',
             'state':'OH','building_type':'residential_one_two_family','synthetic':True},
             'media':[{'id':'P0001','path':'source.png','kind':'photo','sha256':self.case['media'][0]['sha256'],'area':'foundation'}],
             'observations':[],'findings':[],'equipment':[],'limitations':[]}
        prompts=[]
        def provider(im,prompt):
            prompts.append(prompt);return {'candidates':[],'requests':[]}
        execute_specialists(doc,self.root,provider,media_ids=['P0001'])
        self.assertNotIn('MICHIGAN_SOURCE_POLICY',prompts[0])

if __name__=='__main__':unittest.main()
