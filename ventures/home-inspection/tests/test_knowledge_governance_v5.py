import copy, hashlib, json, unittest
from inspection_engine.knowledge_registry import (load_registry, validate_registry, ReferenceBlock,
    prepare_case_research, verify_provision_receipt, source_change_queue, case_agent_packet)
from inspection_engine.serious_defect_benchmark import (score_serious_defects, BenchmarkBlock, SYSTEMS)

H='a'*64
K='b'*64

def case():
    return {'state':'MI','county':'Oakland','municipality':'Auburn Hills','inspection_date':'2026-10-31',
            'building_type':'residential','ahj_receipt_sha256':H,'verified_media_sha256':[K]}

def real_case(name='R1',labels=None):
    if labels is None: labels=[{'label_id':'F1','severity':'critical','system':'electrical','status':'adjudicated'}]
    return {'case_id':name,'synthetic':False,'consented_for_evaluation':True,'evidence_sha256':H,
            'partition':'locked_holdout','training_overlap':False,'qualified_labeler_id':'InspectorA',
            'independent_adjudicator_id':'InspectorB','scope':'residential','jurisdiction':'MI','labels':labels}

def detected(name='R1',label='F1'):
    return {'case_id':name,'prediction_id':'P1','system':'electrical','matched_label_id':label,'human_match_verified':True}

class RegistryTests(unittest.TestCase):
    def setUp(self):self.r=load_registry()
    def test_registry_operational(self):self.assertGreaterEqual(len(self.r['sources']),16)
    def test_registry_unlicensed_full_copyright_text_excluded(self):
        self.assertTrue(all(not x.get('full_text_embedded') for x in self.r['sources']))
    def test_copy_mutation_isolated(self):
        p=load_registry();p['sources'][0]['status']='malicious';self.assertNotEqual(p['sources'][0]['status'],load_registry()['sources'][0]['status'])
    def test_duplicate_reference_rejected(self):
        r=copy.deepcopy(self.r);r['sources'].append(copy.deepcopy(r['sources'][0]))
        with self.assertRaises(ReferenceBlock):validate_registry(r)
    def test_wrong_publisher_domain_rejected(self):
        r=copy.deepcopy(self.r);r['sources'][0]['url']='https://example.com/fake'
        with self.assertRaises(ReferenceBlock):validate_registry(r)
    def test_http_link_rejected(self):
        r=copy.deepcopy(self.r);r['sources'][0]['url']=r['sources'][0]['url'].replace('https:', 'http:')
        with self.assertRaises(ReferenceBlock):validate_registry(r)
    def test_metadata_not_full_text(self):
        r=copy.deepcopy(self.r);next(x for x in r['sources'] if x['id']=='ASTM_E2018_24')['full_text_embedded']=True
        with self.assertRaises(ReferenceBlock):validate_registry(r)
    def test_fake_license_rejected(self):
        r=copy.deepcopy(self.r);next(x for x in r['sources'] if x['id']=='ASTM_E2018_24')['rights']='licensed_local'
        with self.assertRaises(ReferenceBlock):validate_registry(r)
    def test_research_tasks_not_ahj_approval(self):
        x=prepare_case_research(case());self.assertEqual(len(x['ahj_disciplines']),4)
        self.assertTrue(all(v=='NOT_VERIFIED' for v in x['ahj_disciplines'].values()))
    def test_state_required(self):
        c=case();c['state']='OH'
        with self.assertRaises(ReferenceBlock):prepare_case_research(c)
    def test_county_municipality_required(self):
        c=case();c['municipality']=''
        with self.assertRaises(ReferenceBlock):prepare_case_research(c)
    def test_commercial_index(self):
        c=case();c['building_type']='commercial';x=prepare_case_research(c)
        self.assertTrue(any(s['id']=='ASTM_E2018_24' for s in x['source_index']))
        self.assertFalse(any(s['id']=='MI_RES_CODE_2015' for s in x['source_index']))
    def test_agent_packet_scoped(self):
        s=case_agent_packet(case(),['hvac']);self.assertIn('GOVERNED_MICHIGAN_SOURCE_PACKET_JSON',s)
        self.assertIn('CARRIER_LOOKUP',s);self.assertNotIn('BW_AGE',s)
        self.assertIn('UNVERIFIED',s)
    def test_case_receipt_retains_human_review(self):
        receipt={'source_id':'MI_RES_CODE_2015','edition':'2015','section':'R303.1',
                 'official_authority':'Michigan LARA','jurisdiction_evidence_sha256':H,
                 'inspector_evidence_sha256':K,'human_reviewer_id':'qualified-inspector-1'}
        out=verify_provision_receipt(receipt,case());self.assertFalse(out['legal_conclusion_approved'])
    def test_missing_ahj_hash_blocks(self):
        c=case();c['ahj_receipt_sha256']='f'*64
        receipt={'source_id':'MI_RES_CODE_2015','edition':'2015','section':'R303.1',
                 'official_authority':'Michigan LARA','jurisdiction_evidence_sha256':H,
                 'inspector_evidence_sha256':K,'human_reviewer_id':'qualified-inspector-1'}
        with self.assertRaises(ReferenceBlock):verify_provision_receipt(receipt,c)
    def test_prohibited_conclusion_blocks(self):
        receipt={'source_id':'MI_RES_CODE_2015','edition':'2015','section':'R303.1',
                 'official_authority':'Michigan LARA','jurisdiction_evidence_sha256':H,
                 'inspector_evidence_sha256':K,'human_reviewer_id':'qualified-inspector-1',
                 'code_violation_confirmed':True}
        with self.assertRaises(ReferenceBlock):verify_provision_receipt(receipt,case())
    def test_rights_page_cannot_prove_code(self):
        receipt={'source_id':'ICC_COPYRIGHT','edition':'2021','section':'R303.1',
                 'official_authority':'Michigan LARA','jurisdiction_evidence_sha256':H,
                 'inspector_evidence_sha256':K,'human_reviewer_id':'qualified-inspector-1'}
        with self.assertRaises(ReferenceBlock):verify_provision_receipt(receipt,case())
    def test_snapshot_change_queue(self):
        out=source_change_queue({'ICC_COPYRIGHT':H},{'ICC_COPYRIGHT':K})
        self.assertEqual(out[0]['status'],'CHANGED_REVERIFY_BEFORE_USE')
    def test_injected_snapshot_digest_rejected(self):
        with self.assertRaises(ReferenceBlock):source_change_queue({}, {'ICC_COPYRIGHT':'nope'})

class SeriousDefectTests(unittest.TestCase):
    def test_no_human_case_refuses(self):
        with self.assertRaises(BenchmarkBlock):score_serious_defects([],[])
    def test_synthetic_case_refuses(self):
        c=real_case();c['synthetic']=True
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[])
    def test_unconsented_case_refuses(self):
        c=real_case();c['consented_for_evaluation']=False
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[])
    def test_same_labeler_reviewer_refuses(self):
        c=real_case();c['independent_adjudicator_id']='InspectorA'
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[])
    def test_training_overlap_refuses(self):
        c=real_case();c['training_overlap']=True
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[])
    def test_unreviewed_label_refuses(self):
        c=real_case();c['labels'][0]['status']='suggested'
        with self.assertRaises(BenchmarkBlock):score_serious_defects([c],[])
    def test_critical_miss_blocks(self):
        out=score_serious_defects([real_case()],[])
        self.assertEqual(len(out['critical_misses']),1);self.assertEqual(out['status'],'BLOCKED')
    def test_single_success_not_approval(self):
        out=score_serious_defects([real_case()],[detected()]);self.assertEqual(out['critical_recall'],1.0)
        self.assertEqual(out['status'],'BLOCKED');self.assertFalse(out['minimum_cohort_met'])
    def test_wrong_system_not_credit(self):
        d=detected();d['system']='roof';out=score_serious_defects([real_case()],[d]);self.assertEqual(len(out['critical_misses']),1)
    def test_false_positive_precision(self):
        extra=detected();extra['prediction_id']='P2';extra['matched_label_id']=None;extra['human_match_verified']=False
        out=score_serious_defects([real_case()],[detected(),extra]);self.assertEqual(out['human_verified_precision'],0.5)
    def test_duplicate_matched_label_refuses(self):
        d=detected();e=detected();e['prediction_id']='P2'
        with self.assertRaises(BenchmarkBlock):score_serious_defects([real_case()],[d,e])
    def test_missing_label_refuses(self):
        with self.assertRaises(BenchmarkBlock):score_serious_defects([real_case()],[detected(label='F999')])
    def test_critical_recall_zero_with_miss(self):
        out=score_serious_defects([real_case()],[]);self.assertEqual(out['critical_recall'],0.0)
    def test_all_systems_coverage_gate(self):
        label=[{'label_id':s,'severity':'minor','system':s,'status':'adjudicated'} for s in sorted(SYSTEMS)]
        c=real_case(labels=label);out=score_serious_defects([c],[])
        self.assertEqual(out['unrepresented_systems'],[]);self.assertFalse(out['minimum_cohort_met'])

if __name__=='__main__':unittest.main()

from inspection_engine.knowledge_registry import verify_manufacturer_manual_receipt, verify_recall_match
from inspection_engine.sop_scope import audit_sop_scope

class ManualAndSOPTests(unittest.TestCase):
    def test_sop_gap_register_exposes_fireplaces(self):
        s=audit_sop_scope();self.assertEqual(s['status'],'SOP_COVERAGE_INCOMPLETE')
        self.assertTrue(any('fireplaces' in x['topic'] for x in s['unresolved_topics']))
    def test_sop_gap_register_exposes_garage(self):
        s=audit_sop_scope();self.assertTrue(any('garage' in x['topic'] for x in s['unresolved_topics']))
    def test_sop_invalid_system_rejected(self):
        from inspection_engine.sop_scope import CATALOG
        data=json.loads(CATALOG.read_text());data['topics'][0]['systems']=['invented_system']
        with self.assertRaises(ReferenceBlock):audit_sop_scope(data)
    def test_manual_requires_exact_pictured_model(self):
        m={'manufacturer':'Carrier','exact_model':'ABC','manual_revision':'rev-2',
           'retrieved_on':'2026-10-31','reviewer_id':'reviewer1','manual_sha256':H,
           'pictured_rating_plate_model':'XYZ','model_match_human_verified':True}
        with self.assertRaises(ReferenceBlock):verify_manufacturer_manual_receipt(m)
    def test_manual_approved_identity_not_cause(self):
        m={'manufacturer':'Carrier','exact_model':'ABC','manual_revision':'rev-2',
           'retrieved_on':'2026-10-31','reviewer_id':'reviewer1','manual_sha256':H,
           'pictured_rating_plate_model':'ABC','model_match_human_verified':True}
        r=verify_manufacturer_manual_receipt(m)
        self.assertFalse(r['defect_root_cause_confirmed']);self.assertFalse(r['customer_release_allowed'])
    def test_manual_rights_required_for_full_text(self):
        m={'manufacturer':'Carrier','exact_model':'ABC','manual_revision':'rev-2',
           'retrieved_on':'2026-10-31','reviewer_id':'reviewer1','manual_sha256':H,
           'pictured_rating_plate_model':'ABC','model_match_human_verified':True,
           'licensed_for_automated_full_text':True}
        with self.assertRaises(ReferenceBlock):verify_manufacturer_manual_receipt(m)
    def test_recall_not_confirmed_without_lot(self):
        m={'recall_number':'25-999','source_url':'https://www.cpsc.gov/Recalls',
           'product_model':'ABC','pictured_model':'ABC','checked_on':'2026-10-31',
           'reviewed_by':'inspector1','model_match_verified':True}
        r=verify_recall_match(m);self.assertFalse(r['recall_eligibility_confirmed'])
    def test_fake_recall_domain_denied(self):
        m={'recall_number':'25-999','source_url':'https://malicious.net/Recalls',
           'product_model':'ABC','pictured_model':'ABC','checked_on':'2026-10-31',
           'reviewed_by':'inspector1','model_match_verified':True}
        with self.assertRaises(ReferenceBlock):verify_recall_match(m)

from inspection_engine.licensed_reference import prepare_licensed_reference,LicenseBlock
from pathlib import Path
import tempfile

class PrivateLicensedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.ref=self.root/'restricted_document.pdf';self.ref.write_bytes(b'Original synthetic legal test content')
        self.perm={'publisher':'ICC','title':'Synthetic test document','edition':'v0',
                   'licensee':'TestOnly','permission_receipt_sha256':H,'expires_on':'2099-01-01',
                   'machine_indexing_authorized':True,'private_local_only':True,
                   'public_repository_distribution':False}
    def test_explicit_local_permission_gives_metadata_only(self):
        x=prepare_licensed_reference(self.ref,private_root=self.root,permission=self.perm)
        self.assertTrue(x['machine_use_permission_recorded']);self.assertFalse(x['content_extracted'])
        self.assertFalse(x['machine_indexing_approved_for_production'])
        self.assertNotIn('Original synthetic',str(x))
    def test_purchased_without_machine_rights_blocked(self):
        p=dict(self.perm,machine_indexing_authorized=False)
        with self.assertRaises(LicenseBlock):prepare_licensed_reference(self.ref,private_root=self.root,permission=p)
    def test_expired_license_blocked(self):
        p=dict(self.perm,expires_on='2000-01-01')
        with self.assertRaises(LicenseBlock):prepare_licensed_reference(self.ref,private_root=self.root,permission=p)
    def test_outside_private_root_blocked(self):
        other=Path('/etc/hosts')
        with self.assertRaises(LicenseBlock):prepare_licensed_reference(other,private_root=self.root,permission=self.perm)
    def test_no_public_distribution(self):
        p=dict(self.perm,public_repository_distribution=True)
        with self.assertRaises(LicenseBlock):prepare_licensed_reference(self.ref,private_root=self.root,permission=p)

from inspection_engine.knowledge_registry import safe_agent_reference_brief
class EmbeddedPacketTests(unittest.TestCase):
    def test_michigan_property_without_county_does_not_infer_code(self):
        x=safe_agent_reference_brief({'state':'MI','building_type':'residential_one_two_family'},['roof'])
        self.assertIn('MISSING_CASE_FACTS',x)
        self.assertIn('do not assert code compliance',x)
    def test_agent_valid_michigan_case_context(self):
        x=safe_agent_reference_brief({'state':'MI','county':'Oakland','municipality':'Auburn Hills',
           'building_type':'residential_one_two_family','inspection_date':'2026-10-31'},['roof'])
        self.assertIn('GOVERNED_MICHIGAN_SOURCE_PACKET_JSON',x)
    def test_agent_out_of_state_not_mislead(self):
        x=safe_agent_reference_brief({'state':'OH','building_type':'residential'},['roof'])
        self.assertIn('NOT_APPLICABLE',x)

class RiskHardeningTests(unittest.TestCase):
    def test_wrong_edition_cannot_support_claim(self):
        receipt={'source_id':'MI_RES_CODE_2015','edition':'2021','section':'R303.1',
                 'official_authority':'Michigan LARA','jurisdiction_evidence_sha256':H,
                 'inspector_evidence_sha256':K,'human_reviewer_id':'qualified-inspector-1'}
        with self.assertRaises(ReferenceBlock):verify_provision_receipt(receipt,case())
    def test_private_root_cannot_be_public(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);file=root/'private.pdf';file.write_bytes(b'fixture')
            root.chmod(0o755)
            perm={'publisher':'NFPA','title':'Test','edition':'0','licensee':'a',
                'permission_receipt_sha256':H,'expires_on':'2099-01-01',
                'machine_indexing_authorized':True,'private_local_only':True}
            with self.assertRaises(LicenseBlock):prepare_licensed_reference(file,private_root=root,permission=perm)
