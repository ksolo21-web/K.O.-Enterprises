"""Prepare a frozen three-case synthetic source-reading baseline before inference.

No model calls, professional acceptance, lesson activation or external jobs.
"""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import re
import json

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
import pypdfium2
from inspection_engine.core import DataError
from inspection_engine.report_learning import import_reference
from inspection_engine.study_registry import empty_registry,register_bundle
from inspection_engine.report_review_queue import digest,_read_json,_write_new
from inspection_engine.report_study_pipeline import prepare_study,load_prepared

MODEL='qwen2.5vl:3b'
MODEL_SHA='fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1'
ROWS=[['System','Observation','Status'],['Roof','Vent condition','See note'],
      ['Panel','Cover not removed','Not inspected'],['HVAC','Filter','']]
WIDTH,HEIGHT=480,320
COLS=[20,120,330,460]
TOP=218
ROW_HEIGHT=42


def _hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _norm(text):return ' '.join(re.findall(r'[a-z0-9]+',text.casefold()))


def _new(path):
    p=Path(path)
    if p.exists() or p.is_symlink() or not p.parent.is_dir() or any(a.is_symlink() for a in p.absolute().parents):
        raise DataError('Probe output must be new under an existing local directory')
    p.mkdir(mode=0o700)
    return p


def _text_pdf(path,negative):
    c=Canvas(str(path),pagesize=(WIDTH,HEIGHT),invariant=1)
    c.setFont('Helvetica',10);c.drawString(20,300,'SYNTHETIC SOURCE READING - NOT A REAL PROPERTY')
    c.setFont('Helvetica-Bold',12);c.drawString(20,276,'Roof / south vent')
    c.setFont('Helvetica',14);c.drawString(20,251,'No leak observed at vent.' if negative else 'Leak observed at vent.')
    for x in COLS:c.line(x,TOP,x,TOP-len(ROWS)*ROW_HEIGHT)
    for row in range(len(ROWS)+1):c.line(COLS[0],TOP-row*ROW_HEIGHT,COLS[-1],TOP-row*ROW_HEIGHT)
    for i,row in enumerate(ROWS):
        c.setFont('Helvetica-Bold' if i==0 else 'Helvetica',12)
        for j,text in enumerate(row):c.drawString(COLS[j]+7,TOP-i*ROW_HEIGHT-26,text)
    c.showPage();c.save();Path(path).chmod(0o600)


def prepare(root):
    root=_new(root)
    _text_pdf(root/'A.pdf',False);_text_pdf(root/'B.pdf',True)
    document=pypdfium2.PdfDocument((root/'B.pdf').read_bytes())
    try:
        bitmap=document[0].render(scale=105/72);scan=bitmap.to_pil().copy()
        scan.save(root/'B-scan-source.png')
    finally:document.close()
    c=Canvas(str(root/'C.pdf'),pagesize=(WIDTH,HEIGHT),invariant=1)
    c.drawImage(ImageReader(scan),0,0,width=WIDTH,height=HEIGHT);c.showPage();c.save();(root/'C.pdf').chmod(0o600)
    bundles={};registry=empty_registry()
    for ident in ('A','B','C'):
        b=import_reference(root/f'{ident}.pdf',case_id='SYNTH-M3-READ-'+ident,partition='locked_holdout',authorized_use=True,consented=True)
        registry=register_bundle(b,registry);bundles[ident]=b
    _write_new(root/'registry.json',registry)
    cases=[]
    for ident,b in bundles.items():
        _write_new(root/f'{ident}-reference.json',b)
        study=root/f'{ident}-study';receipt=prepare_study(b,registry,root/f'{ident}.pdf',study,ocr=True,batch_size=1)
        _,_,groups=load_prepared(study,b,registry)
        ocr=groups[0]['ocr_record'];words=ocr['pages'][0]['untrusted_ocr_words'];cells=[]
        for i,row in enumerate(ROWS):
            for j,expected in enumerate(row):
                box=[COLS[j]/WIDTH,(HEIGHT-(TOP-i*ROW_HEIGHT))/HEIGHT,
                    COLS[j+1]/WIDTH,(HEIGHT-(TOP-(i+1)*ROW_HEIGHT))/HEIGHT]
                selected=[w for w in words if box[0]<(w['bbox_normalized'][0]+w['bbox_normalized'][2])/2<box[2]
                    and box[1]<(w['bbox_normalized'][1]+w['bbox_normalized'][3])/2<box[3]]
                # All fixture cells contain at most one printed line. X order
                # avoids glyph-height differences changing top-pixel order.
                actual=' '.join(w['text_untrusted'] for w in sorted(selected,key=lambda w:w['bbox_normalized'][0]))
                if _norm(actual)!=_norm(expected):raise DataError('Fixture OCR differs from printed cell; do not freeze')
                cells.append({'row':i+1,'column':j+1,'column_span':1,
                    'role':'header' if i==0 else ('blank' if not expected else 'data'),
                    'printed_text':expected,'bbox':box,'ocr_word_indices':sorted(w['word_index'] for w in selected),'ocr_text':actual})
        cases.append({'id':ident,'case_id':b['case_id'],'modality':'image_only_scan' if ident=='C' else 'pdf_text',
            'reference':f'{ident}-reference.json','source_pdf':f'{ident}.pdf','study_dir':f'{ident}-study',
            'source_pdf_sha256':b['source']['sha256'],'source_png_sha256':groups[0]['manifest']['pages'][0]['sha256'],
            'preparation_sha256':receipt['preparation_sha256'],'ocr_record_sha256':ocr['record_sha256'],
            'polarity_source_sentence':'Leak observed at vent.' if ident=='A' else 'No leak observed at vent.',
            'polarity_expectation':'reported_affirmative' if ident=='A' else 'reported_negation',
            'inspection_limitation':'Panel cover not removed / Not inspected',
            'table_count':1,'row_count':4,'column_count':3,'cells':cells})
    oracle={'kind':'FROZEN_SYNTHETIC_SOURCE_READING_ORACLE_V9','model':MODEL,'model_manifest_sha256':MODEL_SHA,
        'maximum_generation_calls':3,'maximum_generation_calls_per_case':1,'blank_cell_minimum_iou':.5,
        'fixture_script_sha256':_hash(__file__),'scan_parent_pdf_sha256':_hash(root/'B.pdf'),
        'scan_source_png_sha256':_hash(root/'B-scan-source.png'),'cases':cases,
        'manual_polarity_and_scope_review_required':True,'professional_accuracy_verified':False,
        'lesson_activation_allowed':False}
    oracle['oracle_sha256']=digest(oracle);_write_new(root/'oracle.json',oracle)
    return oracle


def verify_sources(root):
    root=Path(root);oracle=_read_json(root/'oracle.json');clean=deepcopy(oracle);sha=clean.pop('oracle_sha256',None)
    if sha!=digest(clean) or oracle.get('kind')!='FROZEN_SYNTHETIC_SOURCE_READING_ORACLE_V9':raise DataError('Frozen oracle changed')
    if _hash(__file__)!=oracle['fixture_script_sha256']:raise DataError('Frozen fixture recipe changed')
    if _hash(root/'B-scan-source.png')!=oracle['scan_source_png_sha256']:raise DataError('Frozen scan parent changed')
    registry=_read_json(root/'registry.json')
    for case in oracle['cases']:
        b=_read_json(root/case['reference']);receipt,_,groups=load_prepared(root/case['study_dir'],b,registry)
        if (_hash(root/case['source_pdf'])!=case['source_pdf_sha256'] or receipt['preparation_sha256']!=case['preparation_sha256']
                or groups[0]['manifest']['pages'][0]['sha256']!=case['source_png_sha256']
                or groups[0]['ocr_record']['record_sha256']!=case['ocr_record_sha256']):raise DataError('Frozen fixture source changed')
    return oracle,registry


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-dir',type=Path,required=True)
    a=p.parse_args();oracle=prepare(a.out_dir);verify_sources(a.out_dir)
    print(json.dumps({'status':'ORACLE_FROZEN_BEFORE_INFERENCE','cases':len(oracle['cases']),
        'oracle_sha256':oracle['oracle_sha256'],'model_inference_performed':False}))


if __name__=='__main__':main()
