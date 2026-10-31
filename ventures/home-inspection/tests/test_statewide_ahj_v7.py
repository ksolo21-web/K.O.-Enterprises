import unittest
from inspection_engine.statewide_ahj_v7 import parse_verified_transcription,find_record,AHJImportBlocked

HEADER='county,municipality,municipality_type,building,building_effective_date,electrical,electrical_effective_date,mechanical,mechanical_effective_date,plumbing,plumbing_effective_date,temporary_assistance_notes\n'
EXAMPLE=HEADER+'Wayne,Exampletown,city,LOCAL,2008-01-01,STATE,2010-02-01,COUNTY,2015-03-01,COUNTY,,\n'
class StatewideAHJTests(unittest.TestCase):
 def make(self,s=EXAMPLE,**kw):
  return parse_verified_transcription(s,state_source_sha256='a'*64,source_revision='2026-09-28',operator_id='researcher_1',**kw)
 def test_multitrade_source_not_equated_to_parcel_verification(self):
  x=self.make();self.assertEqual(x['records'][0]['jurisdiction_levels']['electrical'],'STATE');self.assertFalse(x['complete_michigan_coverage_verified']);self.assertIsNone(x['records'][0]['effective_dates']['plumbing'])
 def test_lookups_do_not_certify_authorities(self):
  x=self.make();r=find_record(x,{'county':'Wayne','municipality':'Exampletown','municipality_type':'city'})
  self.assertFalse(r['authority_names_authenticated']);self.assertNotEqual(r['effective_dates']['building'],r['effective_dates']['electrical'])
 def test_unknown_city_never_assigned_guess(self):
  with self.assertRaises(AHJImportBlocked):find_record(self.make(),{'county':'Wayne','municipality':'Westland','municipality_type':'city'})
 def test_disagreement_of_trade_levels_represented(self):
  x=self.make();t=x['records'][0]['jurisdiction_levels'];self.assertEqual(len(set(t.values())),3)
 def test_duplicate_municipalities_block(self):
  with self.assertRaises(AHJImportBlocked):self.make(EXAMPLE+EXAMPLE.splitlines()[-1]+'\n')
 def test_missing_trade_blocks(self):
  with self.assertRaises(AHJImportBlocked):self.make(HEADER+'Wayne,Test,city,LOCAL,,LOCAL,,,LOCAL,,\n')
 def test_unrecognized_enforcement_level_blocks(self):
  with self.assertRaises(AHJImportBlocked):self.make(EXAMPLE.replace('STATE,2010-02-01','GUESSED,2010-02-01'))
 def test_future_date_blocks(self):
  with self.assertRaises(AHJImportBlocked):self.make(EXAMPLE.replace('2015-03-01','2999-01-01'))
 def test_no_records_blocks(self):
  with self.assertRaises(AHJImportBlocked):self.make(HEADER)
 def test_missing_provenance_blocks(self):
  with self.assertRaises(AHJImportBlocked):parse_verified_transcription(EXAMPLE,state_source_sha256='bad',source_revision='2026-09-28',operator_id='reviewer_1')
 def test_not_an_official_directory_or_real_coverage(self):
  x=self.make();self.assertEqual(x['status'],'STATE_SOURCE_TRANSCRIPTION_PENDING_AHJ_RECONFIRMATION')

if __name__=='__main__':unittest.main()

class HistoricalAHJNuances(unittest.TestCase):
 def test_temporary_assistance_cannot_be_silenced(self):
  row=EXAMPLE.replace('COUNTY,,\n','COUNTY,,temporary state assistance annotated\n')
  x=parse_verified_transcription(row,state_source_sha256='f'*64,source_revision='2026-09-28',operator_id='researcher_1')
  self.assertTrue(x['records'][0]['assistance_requires_individual_review'])
 def test_extra_columns_rejected(self):
  with self.assertRaises(AHJImportBlocked):parse_verified_transcription(EXAMPLE.replace('COUNTY,,\n','COUNTY,,EXTRA,UNEXPECTED\n'),state_source_sha256='f'*64,source_revision='2026-09-28',operator_id='researcher_1')
