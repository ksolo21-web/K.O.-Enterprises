"""Deterministic synthetic reviewer-collation tests. No qualifications authenticated."""
import copy
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from inspection_engine.core import DataError
from inspection_engine.report_review_queue import digest
from inspection_engine.report_visual_reconciliation import reconcile_visual_reviews


class VisualReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.manifest={'schema_version':1,'kind':'UNVERIFIED_PDF_PAGE_EVIDENCE',
            'case_id':'SYNTHETIC','pdf_source_sha256':'a'*64,
            'reference_bundle_sha256':'b'*64,'visual_findings_verified':False,
            'pages':[{'page':1,'sha256':'c'*64},{'page':2,'sha256':'d'*64}]}
        self.manifest['manifest_sha256']=digest(self.manifest)
        self.first=self.review('REVIEWER-A','A1',[.1,.1,.6,.6])
        self.second=self.review('REVIEWER-B','B1',[.11,.11,.59,.59])

    def review(self,reviewer,name,box,*,system='roof',kind='potential_concern',code=None,page=1):
        m={'id':name,'page':page,'bbox':box,'system':system,'kind':kind,'feature_code':code,
          'location':'Sample','description':'Pending mark','reviewer_id':reviewer,
          'source_pdf_sha256':'a'*64,'source_page_png_sha256':('c' if page==1 else 'd')*64,
          'reference_bundle_sha256':'b'*64,'status':'HUMAN_DECLARED_UNVERIFIED',
          'reviewer_authenticated':False,'finding_approved':False,'training_approved':False}
        r={'kind':'PENDING_HUMAN_PDF_VISUAL_MARKS','case_id':'SYNTHETIC','manifest_sha256':self.manifest['manifest_sha256'],
           'marks':[m],'independent_review_required':True,'not_text_quote_annotations':True,
           'customer_release_allowed':False,'training_approved':False}
        r['record_sha256']=digest(r)
        return r

    def test_overlap_only_suggests_not_confirms_and_preserves_both(self):
        x=reconcile_visual_reviews(self.manifest,self.first,self.second)
        self.assertEqual(len(x['possible_spatial_matches']),1)
        self.assertFalse(x['semantic_agreement_verified']);self.assertFalse(x['ground_truth_established'])
        self.assertFalse(x['reviewers_authenticated']);self.assertFalse(x['training_approved'])
        self.assertFalse(x['customer_release_allowed'])
        self.assertEqual(x['original_mark_counts'],[1,1]);self.assertTrue(x['no_marks_dropped'])
        self.assertFalse(x['possible_spatial_matches'][0]['finding_identity_verified'])

    def test_conflicting_classification_is_never_resolved_by_overlap(self):
        self.second=self.review('REVIEWER-B','B1',[.12,.12,.58,.58],system='exterior')
        x=reconcile_visual_reviews(self.manifest,self.first,self.second)
        self.assertEqual(x['possible_spatial_matches'],[])
        self.assertEqual(len(x['spatial_or_category_disputes']),1)
        self.assertEqual(x['unmatched_first_ids'],['A1'])
        self.assertEqual(x['unmatched_second_ids'],['B1'])

    def test_distinct_locations_not_silently_merged(self):
        self.second=self.review('REVIEWER-B','B1',[.75,.75,.9,.9])
        x=reconcile_visual_reviews(self.manifest,self.first,self.second)
        self.assertEqual(x['possible_spatial_matches'],[])
        self.assertEqual(x['unmatched_first_ids'],['A1'])
        self.assertEqual(x['unmatched_second_ids'],['B1'])

    def test_same_declared_reviewer_not_independent(self):
        self.second=self.review('REVIEWER-A','B1',[.11,.11,.59,.59])
        with self.assertRaises(DataError):reconcile_visual_reviews(self.manifest,self.first,self.second)

    def test_tampered_or_backdated_review_rejected(self):
        for key,value in [('training_approved',True),('manifest_sha256','fake')]:
            r=copy.deepcopy(self.first);r[key]=value
            with self.subTest(key=key),self.assertRaises(DataError):reconcile_visual_reviews(self.manifest,r,self.second)
        m=copy.deepcopy(self.first);m['marks'][0]['source_page_png_sha256']='0'*64;m['record_sha256']=digest({k:v for k,v in m.items() if k!='record_sha256'})
        with self.assertRaises(DataError):reconcile_visual_reviews(self.manifest,m,self.second)

    def test_wrong_system_feature_code_refused_even_with_valid_digest(self):
        x=self.review('REVIEWER-B','B1',[.1,.1,.6,.6],kind='feature',code='cladding_type')
        with self.assertRaises(DataError):reconcile_visual_reviews(self.manifest,self.first,x)

    def test_mark_records_require_source_hash_and_never_copy_instructions(self):
        r=copy.deepcopy(self.first);r['marks'][0]['reviewer_id']='REVIEWER-B';r['record_sha256']=digest({k:v for k,v in r.items() if k!='record_sha256'})
        with self.assertRaises(DataError):reconcile_visual_reviews(self.manifest,r,self.second)

if __name__=='__main__':unittest.main()
