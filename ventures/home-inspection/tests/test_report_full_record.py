"""Prevent fixed-layout report previews from silently dropping inspection records."""
from pathlib import Path
import copy
import tempfile
import unittest
from pypdf import PdfReader
from inspection_engine.core import load_project
from inspection_engine.report import build_pdf

ROOT = Path(__file__).resolve().parents[1]


class ReportCompletenessTests(unittest.TestCase):
    def test_long_report_preserves_all_unique_records_and_tail_prose(self):
        doc = copy.deepcopy(load_project(ROOT/'examples'/'demo_project.json'))
        doc['findings'] = []
        doc['observations'] = []
        doc['limitations'] = []
        doc['equipment'] = []
        for n in range(27):
            doc['findings'].append({
                'id':f'F-LONG-{n:02}', 'system':'exterior', 'location':f'Zone {n}',
                'severity':'further_evaluation',
                'condition':f'CONDITION-UNIQUE-{n:02} ' + 'Visible area inconclusive. '*16,
                'recommendation':f'RECOMMENDATION-UNIQUE-{n:02} ' + 'Qualified inspector follow-up advised. '*7,
                'evidence_ids':[], 'review':'review_pending'})
        for n in range(23):
            doc['observations'].append({
                'id':f'O-LONG-{n:02}', 'system':'framing',
                'feature':'Framing type', 'status':'unknown',
                'description':f'FEATURE-UNIQUE-{n:02} ' + 'Concealed detail unverified. '*15,
                'review':'review_pending','evidence_ids':[]})
        for n in range(9):
            doc['equipment'].append({'id':f'E-LONG-{n:02}', 'system':'hvac',
                'brand':'Placeholder','model':f'MODEL-UNIQUE-{n:02}',
                'serial':f'SERIAL-UNIQUE-{n:02}', 'evidence_ids':[]})
        for n in range(10):
            doc['limitations'].append({'id':f'L-LONG-{n:02}', 'system':'roof',
                'description':f'LIMITATION-UNIQUE-{n:02} ' + 'Access not established. '*13,
                'evidence_ids':[]})
        # Last item is > one page and has an unbroken token. Never lose the tail.
        doc['limitations'][-1]['description'] += ' ' + 'Z'*1100 + ' FINAL-UNIQUE-TAIL-SEGMENT'
        with tempfile.TemporaryDirectory() as tmp:
            pdf=Path(tmp)/'long.pdf'
            build_pdf(doc,ROOT/'examples',pdf)
            reader=PdfReader(pdf)
            self.assertGreater(len(reader.pages),15)
            text='\n'.join(page.extract_text() or '' for page in reader.pages)
            for group,ct in [('CONDITION-UNIQUE',27),('RECOMMENDATION-UNIQUE',27),
                             ('FEATURE-UNIQUE',23),('MODEL-UNIQUE',9),
                             ('SERIAL-UNIQUE',9),('LIMITATION-UNIQUE',10)]:
                for n in range(ct):
                    self.assertIn(f'{group}-{n:02}',text)
            self.assertIn('FINAL-UNIQUE-TAIL-SEGMENT',text)
            self.assertIn('Full inspection record',text)

    def test_empty_synthetic_report_still_has_five_editorial_pages(self):
        doc=load_project(ROOT/'examples'/'demo_project.json')
        for key in ('observations','findings','equipment','limitations'):
            doc[key]=[]
        with tempfile.TemporaryDirectory() as tmp:
            pdf=Path(tmp)/'short.pdf'
            build_pdf(doc,ROOT/'examples',pdf)
            self.assertEqual(len(PdfReader(pdf).pages),5)

if __name__=='__main__':unittest.main()
