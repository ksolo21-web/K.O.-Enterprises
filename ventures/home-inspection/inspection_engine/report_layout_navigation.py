"""M3 v4: bounded, source-verified PDF layout navigation; never defect interpretation.

This is a *navigation* layer, not a document understanding model. It combines
trusted-source render receipts, PDFium object geometry and optional untrusted OCR
word positions. Every candidate still requires manual page review.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from .core import DataError
from .report_review_queue import digest, _read_json, _write_new, validate_review_queue
from .report_page_evidence import validate_page_evidence, _source, _pdf_to_display_bbox

MAX_IMAGES_PER_PAGE=96
MAX_ROWS=600
MAX_OCR_WORDS_PER_PAGE=6000
MAX_OUTPUT_BYTES=4_000_000
MAX_WORKER_RESPONSE_BYTES=350_000
MAX_TEXT_RECTANGLES=3500


def _rect(box):
    return (type(box) is list and len(box)==4 and all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=1 for x in box)
            and box[0]<box[2] and box[1]<box[3])


def _image_objects_from_pdf(raw:bytes,pages:list[int]):
    """Bounded isolated PDFium worker; original PDF bytes only, never file path."""
    command=[sys.executable,'-m','inspection_engine.report_layout_navigation','_worker',json.dumps(pages)]
    try:
        process=subprocess.run(command,input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25,check=False)
    except subprocess.TimeoutExpired as exc:
        raise DataError('PDF object inventory exceeded time budget') from exc
    if process.returncode or len(process.stdout)>MAX_WORKER_RESPONSE_BYTES:
        raise DataError('PDF object inventory rejected source or exceeded output budget')
    try:
        rows=json.loads(process.stdout)
    except (ValueError,UnicodeError) as exc:
        raise DataError('PDF object inventory produced invalid data') from exc
    if not isinstance(rows,list) or [r.get('page') for r in rows if isinstance(r,dict)]!=pages:
        raise DataError('PDF object inventory omitted or duplicated pages')
    return rows


def _run_worker(raw:bytes,pages:list[int]):
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,)*2)
        resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    import pypdfium2 as pdfium
    document=pdfium.PdfDocument(raw)
    if not pages or pages[-1]>len(document):raise DataError('Requested PDF page does not exist')
    rows=[]
    for num in pages:
        page=document[num-1];width,height=page.get_size();rotation=page.get_rotation()
        if not (0<width<=20000 and 0<height<=20000):raise DataError('Invalid PDF geometry')
        boxes=[];unlocated=0;count=0
        for obj in page.get_objects():
            if not isinstance(obj,pdfium.PdfImage):continue
            count+=1
            if count>MAX_IMAGES_PER_PAGE:raise DataError('Embedded image count requires explicit batching')
            # Nested Form XObject bounds are form-local. Without composing all
            # parent transforms they are not page coordinates; never draw them.
            if obj.level>0:
                unlocated+=1
                continue
            coords=_pdf_to_display_bbox(obj.get_bounds(),rotation,width,height)
            if coords is None:unlocated+=1
            else:boxes.append(coords)
        rows.append({'page':num,'raster_object_count':count,'raster_object_boxes_normalized':boxes,
                     'unlocated_raster_objects':unlocated})
    return rows


def _ocr_rows(words):
    """Group OCR word boxes into visual rows, never trusted table semantics."""
    if not isinstance(words,list) or len(words)>MAX_OCR_WORDS_PER_PAGE:
        raise DataError('OCR word list exceeds layout bound')
    items=[]
    for word in words:
        if not isinstance(word,dict) or not _rect(word.get('bbox_normalized')):
            raise DataError('Untrusted OCR geometry must be verified before layout')
        bb=word['bbox_normalized'];items.append((round((bb[1]+bb[3])/2,7),bb[0],word['word_index'],bb))
    items.sort()
    groups=[]
    for y,x,ident,box in items:
        tolerance=max(.007,(box[3]-box[1])*.65)
        if groups and abs(groups[-1]['center_y']-y)<=tolerance:
            group=groups[-1];group['members'].append((x,ident,box));group['center_y']=round((group['center_y']*(len(group['members'])-1)+y)/len(group['members']),7)
        else:
            if len(groups)>=MAX_ROWS:raise DataError('OCR layout row count exceeds bound')
            groups.append({'center_y':y,'members':[(x,ident,box)]})
    output=[]
    for i,g in enumerate(groups,1):
        ordered=sorted(g['members'],key=lambda item:(item[0],item[1]))
        output.append({'row_id':f'ROW-{i:04d}','ocr_word_indices':[v[1] for v in ordered],
                       'position_y':g['center_y'],
                       'x_anchors':[round(v[0],5) for v in ordered],
                       'reading_order_is_unverified':True})
    if sorted(idx for row in output for idx in row['ocr_word_indices'])!=sorted(w['word_index'] for w in words):
        raise DataError('Layout index lost OCR words')
    return output


def _table_like(rows):
    """Only a positional cue: repeated columns in 3+ rows, no generated cells."""
    possible=[]
    if len(rows)<3:return possible
    for i in range(len(rows)-2):
        chunk=rows[i:i+3]
        if min(len(r['x_anchors']) for r in chunk)<3:continue
        anchors=[r['x_anchors'][:3] for r in chunk]
        if all(max(col)-min(col)<=.035 for col in zip(*anchors)):
            possible.append({'row_ids':[r['row_id'] for r in chunk],
                             'cue':'POSSIBLE_REPEATED_HORIZONTAL_ALIGNMENT',
                             'table_structure_confirmed':False})
    return possible[:MAX_ROWS]


def build_layout_index(manifest,bundle,registry,pdf_path,render_dir,text_queue,*,ocr_record=None):
    """Validate every upstream custody receipt and preserve all navigational gaps."""
    validate_page_evidence(manifest,bundle,registry,pdf_path,render_dir)
    validate_review_queue(text_queue,bundle,registry)
    if ocr_record is not None:
        from .report_ocr_review import validate_ocr_record
        validate_ocr_record(ocr_record,manifest)
    raw=_source(Path(pdf_path))
    if manifest.get('pdf_source_sha256')!=__import__('hashlib').sha256(raw).hexdigest():
        raise DataError('PDF source bytes differ from rendered evidence')
    pages=[x['page'] for x in manifest['pages']]
    if not 1<=len(pages)<=8 or pages!=sorted(set(pages)):
        raise DataError('Layout navigation requires a bounded, ordered render batch')
    objects=_image_objects_from_pdf(raw,pages)
    object_by_page={row['page']:row for row in objects}
    ocr_by_page={x['page']:x for x in ocr_record['pages']} if ocr_record is not None else {}
    spans={n:[] for n in pages}
    for span in text_queue['spans']:
        if span['page'] in spans:
            spans[span['page']].append({'span_id':span['span_id'],'text_sha256':span['text_sha256']})
    layout=[]
    for source in manifest['pages']:
        number=source['page'];inventory=object_by_page[number]
        if inventory['raster_object_count']!=source['raster_image_objects_reported']:
            raise DataError('PDF raster inventory differs from original renderer')
        if inventory['raster_object_count']!=len(inventory['raster_object_boxes_normalized'])+inventory['unlocated_raster_objects']:
            raise DataError('Raster objects omitted from navigation record')
        lines=source['untrusted_text_line_rectangles']
        if (not isinstance(lines,list) or len(lines)>MAX_TEXT_RECTANGLES or any(not _rect(box) for box in lines)):
            raise DataError('Invalid page text rectangle navigation metadata')
        words=ocr_by_page.get(number,{}).get('untrusted_ocr_words',[])
        rows=_ocr_rows(words)
        page={'page':number,'page_image_sha256':source['sha256'],
              'pdf_source_sha256':manifest['pdf_source_sha256'],
              'reference_page_text_sha256':text_queue['page_coverage'][number-1]['source_text_sha256'],
              'text_span_ids':[s['span_id'] for s in spans[number]],
              'reported_pdf_text_rectangles':len(lines),'pdf_text_line_boxes_untrusted':deepcopy(lines),
              'unlocated_text_rectangles':source['line_rectangles_unmapped_due_to_geometry'],
              'embedded_raster_object_count':inventory['raster_object_count'],
              'raster_object_boxes_unverified':inventory['raster_object_boxes_normalized'],
              'unlocated_raster_objects':inventory['unlocated_raster_objects'],
              'ocr_performed':number in ocr_by_page,
              'ocr_word_count':len(words),'ocr_navigation_rows':rows,
              'possible_table_alignments_not_verified':_table_like(rows),
              'photos_vs_diagrams_not_classified':True,
              'reading_order_not_verified':True,'tables_not_structurally_verified':True,
              'page_requires_human_review':True}
        layout.append(page)
    result={'schema_version':1,'kind':'M3_UNVERIFIED_LAYOUT_NAVIGATION_V4',
            'case_id':bundle['case_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
            'page_manifest_sha256':manifest['manifest_sha256'],
            'text_queue_sha256':text_queue['queue_sha256'],
            'ocr_record_sha256':ocr_record['record_sha256'] if ocr_record is not None else None,
            'pages':layout,'all_render_batch_pages_indexed':True,
            'all_pdf_objects_classified_as_photos_or_diagrams':False,
            'table_cells_interpreted':False,'reading_order_verified':False,
            'qualified_review_required':True,'training_approved':False,
            'customer_release_allowed':False,'status':'LAYOUT_NAVIGATION_PENDING_HUMAN'}
    if len(json.dumps(result,ensure_ascii=True,allow_nan=False).encode())>MAX_OUTPUT_BYTES:
        raise DataError('Layout index exceeds 4MB; use smaller page batch')
    result['index_sha256']=digest(result)
    return result


def validate_layout_index(index,manifest,bundle,registry,pdf_path,render_dir,text_queue,*,ocr_record=None):
    """Recreate every page and geometry reference, not just the unsigned digest."""
    if not isinstance(index,dict) or index!=build_layout_index(manifest,bundle,registry,pdf_path,render_dir,text_queue,ocr_record=ocr_record):
        raise DataError('Layout index is stale, altered, incomplete, or outside scope')
    return index


def main(argv=None):
    p=argparse.ArgumentParser(description='Private M3 unverified PDF navigation; no defect recognition')
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True)
    p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--render-dir',type=Path,required=True)
    p.add_argument('--text-queue',type=Path,required=True)
    p.add_argument('--ocr',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=build_layout_index(_read_json(a.manifest),_read_json(a.reference),_read_json(a.registry),a.pdf,a.render_dir,_read_json(a.text_queue),ocr_record=_read_json(a.ocr) if a.ocr else None)
        _write_new(a.out,result)
        print(json.dumps({'status':result['status'],'pages':len(result['pages']),
                          'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'customer_release_allowed':False,
                          'training_approved':False}))
        return 2


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='_worker':
        try:
            pages=json.loads(sys.argv[2]);raw=sys.stdin.buffer.read(20_000_001)
            if not raw or len(raw)>20_000_000 or not isinstance(pages,list) or not 1<=len(pages)<=8 or pages!=sorted(set(pages)) or any(type(n) is not int or not 1<=n<=200 for n in pages):
                raise DataError('Invalid worker source or page selection')
            output=_run_worker(raw,pages)
            encoded=json.dumps(output,ensure_ascii=True,allow_nan=False).encode()
            if len(encoded)>MAX_WORKER_RESPONSE_BYTES:raise DataError('Worker result too large')
            sys.stdout.buffer.write(encoded)
        except Exception:
            sys.exit(2)
    else:raise SystemExit(main())
