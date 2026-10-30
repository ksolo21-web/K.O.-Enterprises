import copy
import json
from pathlib import Path
import tempfile
import unittest
from inspection_engine.core import (DataError,blockers,coverage,detect_mode,load_project,
                                   record_status, safe_path, validate_project,media_inventory)
from inspection_engine.equipment import research_equipment
from inspection_engine.learning import compare_to_human
from inspection_engine.report import build_pdf

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples'/'demo_project.json'

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.sample=load_project(EXAMPLE)
    def test_photo_only(self):
        self.assertEqual(detect_mode(self.sample),'photos')
    def test_video_media_manifest_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'intake.mp4').write_bytes(b'fixture only; not a playable video')
            sample=copy.deepcopy(self.sample)
            sample['media']=[{'id':'V1','kind':'video','path':'intake.mp4','area':'attic'}]
            sample['observations']=[];sample['findings']=[]
            validate_project(sample,root)
            self.assertEqual(detect_mode(sample),'videos')
            self.assertEqual(len(media_inventory(sample,root)),1)
            self.assertEqual(next(c for c in coverage(sample) if c['system']=='attic')['status'],'not verified')
    def test_video_only(self):
        p=copy.deepcopy(self.sample)
        p['media'][0]['kind']='video';p['media'][0]['path']='placeholder.mp4'
        self.assertEqual(detect_mode(p),'videos')
    def test_mixed(self):
        p=copy.deepcopy(self.sample);p['media'].append({'id':'V01','kind':'video','area':'roof','path':'example.mp4'})
        self.assertEqual(detect_mode(p),'mixed')
    def test_no_photos_not_verified(self):
        c=coverage(self.sample);self.assertEqual(c[0]['status'],'not verified');self.assertEqual(next(x for x in c if x['system']=='foundation')['status'],'partial');self.assertEqual(next(x for x in c if x['system']=='roof')['status'],'not verified')
    def test_full_property_descriptors_remain_missing_until_documented(self):
        x=next(x for x in coverage(self.sample) if x['system']=='foundation')
        self.assertNotIn('foundation_type',x['missing_features'])
        self.assertIn('foundation_material',x['missing_features'])
        self.assertIn('support_configuration',x['missing_features'])
    def test_invalid_property_feature_code_rejected(self):
        p=copy.deepcopy(self.sample)
        p['observations'][0]['feature_code']='fictional_invisible_support'
        with self.assertRaises(DataError):validate_project(p,EXAMPLE.parent)
    def test_single_photo_never_verifies_entire_system(self):
        x=next(x for x in coverage(self.sample) if x['system']=='foundation')
        self.assertEqual(x['status'],'partial')
    def test_no_automatic_release(self):
        self.assertIn('DEMONSTRATION',record_status(self.sample))
        self.assertTrue(blockers(self.sample))
    def test_orphan_evidence_ref_rejected(self):
        p=copy.deepcopy(self.sample);p['findings'][0]['evidence_ids']=['FAKE']
        with self.assertRaises(DataError):validate_project(p,EXAMPLE.parent)
    def test_path_traversal_rejected(self):
        with self.assertRaises(DataError):safe_path(EXAMPLE.parent,'../../../etc/passwd')
    def test_hypothetical_observation_no_evidence_rejected(self):
        p=copy.deepcopy(self.sample);p['observations'][0]['evidence_ids']=[]
        with self.assertRaises(DataError):validate_project(p,EXAMPLE.parent)
    def test_file_hash(self):
        inventory=media_inventory(self.sample, EXAMPLE.parent)
        self.assertEqual(len(inventory[0]['sha256']),64)
    def test_manufacturer_decoding_single_candidate(self):
        x=research_equipment('Bradford White','WC9876553','2026-10-30')
        self.assertEqual(x['manufacturer_date'],'2000-03')
        self.assertEqual(x['verification'],'manufacturer_code_only')
    def test_manufacturer_20_year_cycle_uncertainty(self):
        x=research_equipment('Bradford White','CA1234567','2026-10-30')
        self.assertEqual(x['candidates'],['1986-01','2006-01'])
        self.assertIsNone(x['manufacturer_date'])
        self.assertEqual(x['verification'],'ambiguous_cycle')
    def test_rheem_published_format(self):
        x=research_equipment('Rheem','1209D01234','2026-10-30')
        self.assertEqual(x['manufacturer_date'],'2009-12')
        self.assertIn('rheem.com',x['source'])
    def test_rheem_future_date_rejected(self):
        x=research_equipment('Rheem','1126D01234','2026-10-30')
        self.assertIsNone(x['manufacturer_date'])
    def test_carrier_manufacturer_source_link(self):
        x=research_equipment('Carrier','ABC12345','2026-10-30')
        self.assertIn('carrier.com',x['source'])
        self.assertIsNone(x['manufacturer_date'])
    def test_manufacturer_invalid(self):
        x=research_equipment('Bradford White','! BAD','2026-10-30')
        self.assertIsNone(x['manufacturer_date'])
    def test_unverified_manufacturer(self):
        x=research_equipment('Carrier','123456789','2026-10-30')
        self.assertEqual(x['verification'],'not_verified')
    def test_learning_missed_items(self):
        human=json.loads((ROOT/'examples'/'human_reference.json').read_text())
        d=compare_to_human(self.sample,human)
        self.assertEqual(len(d['missed']),2)
        self.assertFalse(d['training_approved'])
    def test_learning_extra_not_assumed_false(self):
        human={'observations':[]}
        self.assertGreater(len(compare_to_human(self.sample,human)['extra']),0)
    def test_pdf_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'report.pdf'
            build_pdf(self.sample, EXAMPLE.parent,dest)
            self.assertTrue(dest.is_file())
            self.assertGreater(dest.stat().st_size,10000)

if __name__=='__main__':unittest.main()
