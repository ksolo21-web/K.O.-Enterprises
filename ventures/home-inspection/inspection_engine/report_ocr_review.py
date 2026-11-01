"""Milestone 3: local, bounded, UNVERIFIED OCR over source-checked PDF page PNGs.

OCR never creates a trusted quote in the imported PDF text, defect, code claim,
training label or report finding. The original PDF and page raster remain authoritative
for what pixels were captured; interpretation requires professional review.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import io
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .core import DataError
from .report_review_queue import digest, _read_json, _write_new
from .report_page_evidence import validate_page_evidence

MAX_OCR_PAGES=8
MAX_OCR_WORDS=6000
MAX_OCR_RAW_BYTES=3_000_000
MAX_WORD_LENGTH=240
MAX_OUTPUT_BYTES=4_000_000


def _engine_version():
    engine=shutil.which('tesseract')
    if not engine: raise DataError('Tesseract is not installed; OCR cannot be claimed')
    try:
        process=subprocess.run([engine,'--version'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                               timeout=5,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise DataError('Local OCR engine version check failed') from exc
    if process.returncode or not process.stdout:
        raise DataError('Local OCR engine version unavailable')
    version=process.stdout.decode('utf-8',errors='replace').splitlines()[0][:120]
    if not re.fullmatch(r'tesseract\s+\d[^\x00-\x1f]{0,115}',version):
        raise DataError('Unexpected local OCR engine identity')
    return engine,version


def _tsv(encoded:bytes,engine:str)->bytes:
    """Send only page PNG bytes through stdin; fixed args, no network or temp images.

    The output is a size-limited anonymous local file instead of a potentially
    unbounded stdout buffer. A child wall/CPU/file-size budget applies.
    """
    if not isinstance(encoded,bytes) or not encoded.startswith(b'\x89PNG\r\n\x1a\n') or len(encoded)>8_000_000:
        raise DataError('OCR requires an existing bounded PNG raster')
    def limits():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(25,25))
        resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
        resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_OCR_RAW_BYTES,MAX_OCR_RAW_BYTES))
    with tempfile.TemporaryFile() as output:
        try:
            result=subprocess.run([engine,'stdin','stdout','-l','eng','--psm','3','tsv'],
                    input=encoded,stdout=output,stderr=subprocess.DEVNULL,timeout=30,check=False,
                    preexec_fn=limits if __import__('os').name=='posix' else None)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise DataError('Bounded OCR engine failed or timed out') from exc
        if result.returncode:
            raise DataError('OCR engine returned an error; no output accepted')
        output.seek(0)
        data=output.read(MAX_OCR_RAW_BYTES+1)
        if len(data)>MAX_OCR_RAW_BYTES:
            raise DataError('OCR output exceeds resource budget')
        return data


def _words(tsv:bytes,width:int,height:int)->list:
    try:source=tsv.decode('utf-8',errors='strict')
    except UnicodeError as exc:raise DataError('OCR output is not UTF-8') from exc
    if len(source)>MAX_OCR_RAW_BYTES:raise DataError('OCR text exceeds resource limit')
    rows=csv.DictReader(io.StringIO(source),delimiter='\t')
    names={'level','left','top','width','height','conf','text'}
    if not rows.fieldnames or not names.issubset(rows.fieldnames):
        raise DataError('Malformed OCR TSV header')
    result=[]
    for number,row in enumerate(rows,1):
        if number>70_000:raise DataError('OCR engine returned too many layout rows')
        if row.get('level')!='5':continue
        value=row.get('text')
        if not isinstance(value,str) or not value.strip():continue
        if len(value)>MAX_WORD_LENGTH or any(ord(c)<32 for c in value):
            raise DataError('Unbounded OCR word')
        try:
            x,y,w,h=(int(row[k]) for k in ('left','top','width','height'))
            confidence=float(row['conf'])
        except (ValueError,TypeError,KeyError) as exc:
            raise DataError('Invalid OCR word geometry or confidence') from exc
        if (w<=0 or h<=0 or not 0<=x<x+w<=width or not 0<=y<y+h<=height
            or not math.isfinite(confidence) or not -1<=confidence<=100):
            raise DataError('OCR engine returned invalid pixel geometry')
        result.append({'text_untrusted':value,'bbox_normalized':[round(x/width,7),round(y/height,7),
            round((x+w)/width,7),round((y+h)/height,7)],'confidence_untrusted':round(confidence,2),
            'word_index':len(result)+1})
        if len(result)>MAX_OCR_WORDS:raise DataError('OCR word count exceeded')
    return result


def ocr_review_batch(manifest,bundle,registry,pdf_path:Path,render_dir:Path,*,pages:list[int]):
    validate_page_evidence(manifest,bundle,registry,pdf_path,render_dir)
    entries={row['page']:row for row in manifest['pages']}
    if (not isinstance(pages,list) or not 1<=len(pages)<=MAX_OCR_PAGES
        or any(type(p) is not int or p not in entries for p in pages)
        or pages!=sorted(set(pages))):
        raise DataError('OCR page selection must be a sorted subset of verified render pages')
    engine,version=_engine_version()
    completed=[]
    for number in pages:
        row=entries[number]
        png=(Path(render_dir)/row['image_path']).read_bytes()
        if sha256(png).hexdigest()!=row['sha256']:raise DataError('OCR image changed')
        content=_tsv(png,engine)
        words=_words(content,row['pixel_width'],row['pixel_height'])
        completed.append({'page':number,'source_page_png_sha256':row['sha256'],
            'untrusted_ocr_words':words,'ocr_word_count':len(words),
            'empty_ocr_needs_manual_review':not bool(words),
            'extracted_text_page_offsets_valid':False,'visual_page_review_complete':False})
    result={'schema_version':1,'kind':'UNTRUSTED_LOCAL_OCR_PAGE_REVIEW',
        'case_id':bundle['case_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
        'manifest_sha256':manifest['manifest_sha256'],'pdf_source_sha256':manifest['pdf_source_sha256'],
        'ocr_engine':version,'engine_mode':'OFFLINE_TESSERACT_ENGLISH_PSM3_TSV',
        'pages':completed,'ocr_words_are_unverified':True,'converted_to_reference_quotes':False,
        'no_code_or_defect_inferences':True,'qualified_inspector_review_required':True,
        'training_approved':False,'customer_release_allowed':False,'status':'OCR_REVIEW_PENDING'}
    if len(json.dumps(result,ensure_ascii=True).encode())>MAX_OUTPUT_BYTES:
        raise DataError('OCR review result exceeds 4MB')
    result['record_sha256']=digest(result)
    return result


def validate_ocr_record(record,manifest):
    if not isinstance(record,dict):raise DataError('Missing OCR review record')
    clean=deepcopy(record);signed=clean.pop('record_sha256',None)
    if signed!=digest(clean):raise DataError('OCR record was altered')
    if (record.get('schema_version')!=1 or set(record)!={'schema_version','kind','case_id','reference_bundle_sha256',
        'manifest_sha256','pdf_source_sha256','ocr_engine','engine_mode','pages',
        'ocr_words_are_unverified','converted_to_reference_quotes','no_code_or_defect_inferences',
        'qualified_inspector_review_required','training_approved','customer_release_allowed',
        'status','record_sha256'}
        or record.get('engine_mode')!='OFFLINE_TESSERACT_ENGLISH_PSM3_TSV'
        or not isinstance(record.get('ocr_engine'),str)
        or not re.fullmatch(r'tesseract\s+\d[^\x00-\x1f]{0,115}',record['ocr_engine'])
        or record.get('kind')!='UNTRUSTED_LOCAL_OCR_PAGE_REVIEW'
        or record.get('case_id')!=manifest.get('case_id')
        or record.get('manifest_sha256')!=manifest.get('manifest_sha256')
        or record.get('pdf_source_sha256')!=manifest.get('pdf_source_sha256')
        or record.get('reference_bundle_sha256')!=manifest.get('reference_bundle_sha256')
        or record.get('ocr_words_are_unverified') is not True
        or record.get('converted_to_reference_quotes') is not False
        or record.get('no_code_or_defect_inferences') is not True
        or record.get('qualified_inspector_review_required') is not True
        or record.get('customer_release_allowed') is not False
        or record.get('training_approved') is not False
        or record.get('status')!='OCR_REVIEW_PENDING'):
        raise DataError('OCR identity or review gate invalid')
    pages={row['page']:row for row in manifest['pages']}
    listed=record.get('pages')
    if not isinstance(listed,list) or not 1<=len(listed)<=MAX_OCR_PAGES:raise DataError('OCR page list invalid')
    nums=[x.get('page') for x in listed if isinstance(x,dict)]
    if nums!=sorted(set(nums)) or any(type(n) is not int or n not in pages for n in nums):
        raise DataError('OCR page selection invalid')
    for row in listed:
        source=pages[row['page']]
        if (set(row)!={'page','source_page_png_sha256','untrusted_ocr_words','ocr_word_count',
            'empty_ocr_needs_manual_review','extracted_text_page_offsets_valid','visual_page_review_complete'}
            or row.get('source_page_png_sha256')!=source['sha256']
            or row.get('extracted_text_page_offsets_valid') is not False
            or row.get('visual_page_review_complete') is not False
            or row.get('empty_ocr_needs_manual_review') is not (not bool(row.get('untrusted_ocr_words')))):
            raise DataError('OCR page receipt or status invalid')
        words=row.get('untrusted_ocr_words')
        if not isinstance(words,list) or len(words)>MAX_OCR_WORDS or row.get('ocr_word_count')!=len(words):
            raise DataError('OCR word metadata invalid')
        for i,w in enumerate(words,1):
            if not isinstance(w,dict) or set(w)!={'text_untrusted','bbox_normalized','confidence_untrusted','word_index'}:
                raise DataError('OCR word record altered')
            box=w['bbox_normalized'];txt=w['text_untrusted'];conf=w['confidence_untrusted']
            if (not isinstance(txt,str) or not txt.strip() or len(txt)>MAX_WORD_LENGTH
                or any(ord(ch)<32 for ch in txt)
                or not isinstance(box,list) or len(box)!=4
                or any(type(n) not in (int,float) or not math.isfinite(n) or not 0<=n<=1 for n in box)
                or not box[0]<box[2] or not box[1]<box[3]
                or type(conf) not in (int,float) or not -1<=conf<=100
                or w['word_index']!=i):raise DataError('Invalid OCR word value')
    return record


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description='Bounded local UNTRUSTED OCR; no customer release or training')
    for name in ('reference','registry','source-pdf','manifest','out'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--pages',required=True,help='Sorted comma-separated page numbers, max 8')
    a=p.parse_args(argv)
    try:
        pages=[int(x) for x in a.pages.split(',')]
        result=ocr_review_batch(_read_json(a.manifest),_read_json(a.reference),_read_json(a.registry),
            a.source_pdf,a.manifest.parent,pages=pages)
        _write_new(a.out,result)
        print(json.dumps({'status':result['status'],'pages':len(result['pages']),
            'ocr_is_unverified':True,'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),
            'training_approved':False,'customer_release_allowed':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
