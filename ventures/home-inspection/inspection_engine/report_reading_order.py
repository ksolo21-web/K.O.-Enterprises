"""M3 v5: lossless, *unverified* OCR reading-order suggestions.

No semantic interpretation, defect labels, table cells, PDF text-offset substitution,
or permission to learn/release. Every OCR word must appear exactly once.
"""
from __future__ import annotations
from copy import deepcopy
import math

from .core import DataError
from .report_review_queue import digest

MAX_PAGES=8
MAX_WORDS=6000
MAX_ROW_GROUPS=600


def _box(bb):
    return (isinstance(bb,list) and len(bb)==4 and all(type(x) in (int,float)
        and math.isfinite(x) and 0<=x<=1 for x in bb) and bb[0]<bb[2] and bb[1]<bb[3])


def _page_ocr(layout,ocr_record):
    if not isinstance(layout,dict) or layout.get('kind')!='M3_UNVERIFIED_LAYOUT_NAVIGATION_V4' or layout.get('index_sha256')!=digest({k:v for k,v in layout.items() if k!='index_sha256'}):
        raise DataError('Layout index altered or unsupported')
    if any(layout.get(k) is not v for k,v in [('training_approved',False),('customer_release_allowed',False),('reading_order_verified',False)]):
        raise DataError('Layout cannot authorize learning or verified reading order')
    pages=layout.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES or len({p.get('page') for p in pages if isinstance(p,dict)})!=len(pages):
        raise DataError('Invalid layout page coverage')
    if ocr_record is None:
        if layout.get('ocr_record_sha256') is not None or any(p.get('ocr_performed') for p in pages):
            raise DataError('OCR record required for OCR layout')
        return {},pages
    if not isinstance(ocr_record,dict) or ocr_record.get('record_sha256')!=layout.get('ocr_record_sha256'):
        raise DataError('OCR record identity mismatch')
    if ocr_record.get('record_sha256')!=digest({k:v for k,v in ocr_record.items() if k!='record_sha256'}):
        raise DataError('OCR record digest mismatch')
    if (ocr_record.get('training_approved') is not False or ocr_record.get('customer_release_allowed') is not False or
        ocr_record.get('converted_to_reference_quotes') is not False):
        raise DataError('OCR content is not approved reference text')
    rows=ocr_record.get('pages')
    if not isinstance(rows,list) or len(rows)>MAX_PAGES or len({p.get('page') for p in rows if isinstance(p,dict)})!=len(rows):
        raise DataError('Invalid OCR page identity')
    return {p['page']:p for p in rows},pages


def _row_words(page,words):
    if not isinstance(words,list) or len(words)>MAX_WORDS:
        raise DataError('Unbounded OCR words')
    wordmap={}
    for idx,w in enumerate(words,1):
        if (not isinstance(w,dict) or w.get('word_index')!=idx or not _box(w.get('bbox_normalized'))
            or not isinstance(w.get('text_untrusted'),str) or not w['text_untrusted'].strip() or len(w['text_untrusted'])>240):
            raise DataError('Missing or changed OCR words')
        wordmap[idx]=w
    rows=page.get('ocr_navigation_rows',[])
    if not isinstance(rows,list) or len(rows)>MAX_ROW_GROUPS:
        raise DataError('Unbounded navigation rows')
    seen=[];clean=[]
    for row in rows:
        ids=row.get('ocr_word_indices') if isinstance(row,dict) else None
        if not isinstance(ids,list) or not ids or any(type(i) is not int or i not in wordmap for i in ids):
            raise DataError('Invalid navigation row references')
        if ids!=sorted(ids,key=lambda i:(wordmap[i]['bbox_normalized'][0],i)):
            raise DataError('Navigation row order disagrees with OCR geometry')
        seen.extend(ids)
        center=sum((wordmap[i]['bbox_normalized'][1]+wordmap[i]['bbox_normalized'][3])/2 for i in ids)/len(ids)
        clean.append({'row_id':row['row_id'],'word_indices':ids,'center_y':round(center,6)})
    if sorted(seen)!=list(range(1,len(words)+1)):
        raise DataError('OCR navigation lost, repeated or added words')
    if page.get('ocr_word_count')!=len(words) or page.get('ocr_performed') is not True:
        raise DataError('Layout OCR counts disagree')
    return clean,wordmap


def _candidate_gutter(rows,wordmap):
    # Repeated large whitespace between word groups is only an indicator of columns.
    # A document table can have exactly the same signal: never infer semantics.
    gaps=[]
    for row in rows:
        ids=row['word_indices']
        for a,b in zip(ids,ids[1:]):
            first=wordmap[a]['bbox_normalized'];second=wordmap[b]['bbox_normalized']
            gap=second[0]-first[2]
            if gap>=.11 and .15<first[2]<.85 and .15<second[0]<.85:
                gaps.append((round((first[2]+second[0])/2,4),row['row_id']))
    candidates=[]
    for coord,ident in gaps:
        support={r for x,r in gaps if abs(x-coord)<=.055}
        if len(support)>=3:
            candidates.append((len(support),coord))
    if not candidates:return None,'COLUMN_BOUNDARY_NOT_ESTABLISHED'
    candidates.sort(key=lambda x:(-x[0],abs(x[1]-.5),x[1]))
    leader=candidates[0]
    # Two different strong gutters suggests a table or more complex layout.
    if any(n>=leader[0]-1 and abs(x-leader[1])>.12 for n,x in candidates[1:]):
        return None,'MULTIPLE_POSSIBLE_GUTTERS_REVIEW_REQUIRED'
    return leader[1],'POSSIBLE_TWO_COLUMN_STRUCTURE'


def _page_order(page,record):
    if record is None:
        if page.get('ocr_performed') or page.get('ocr_word_count'):
            raise DataError('OCR evidence missing for indexed page')
        return {'page':page['page'],'mode':'NO_OCR_READING_ORDER_AVAILABLE','candidate_gutter_x':None,
                'candidate_lines':[],'every_ocr_word_represented_once':True,
                'ambiguous_layout_reasons':['PAGE_REQUIRES_VISUAL_REVIEW'],
                'text_span_ids_unordered':deepcopy(page.get('text_span_ids',[]))}
    if record.get('page')!=page.get('page') or record.get('ocr_word_count')!=len(record.get('untrusted_ocr_words',[])):
        raise DataError('Page and OCR data disagree')
    rows,wordmap=_row_words(page,record['untrusted_ocr_words'])
    gutter,reason=_candidate_gutter(rows,wordmap)
    classified=[];issues=[]
    for row in rows:
        ids=row['word_indices']
        left=[];right=[];cross=[]
        if gutter is not None:
            for i in ids:
                box=wordmap[i]['bbox_normalized']
                if box[2]<=gutter:left.append(i)
                elif box[0]>=gutter:right.append(i)
                else:cross.append(i)
        if gutter is None or cross:
            if cross:issues.append('WORD_CROSSES_CANDIDATE_COLUMN_GUTTER')
            classified.append(('full_page',row['center_y'],ids,row['row_id']))
        else:
            if left:classified.append(('left',row['center_y'],left,row['row_id']))
            if right:classified.append(('right',row['center_y'],right,row['row_id']))
    if gutter is None:
        order=sorted(classified,key=lambda r:(r[1],r[3]))
        mode='ROW_MAJOR_UNVERIFIED'
    else:
        # Full-width rows are structural separators; preserve their y position.
        # Only sort column-major within contiguous bands separated by full-width rows.
        order=[];band=[]
        def flush():
            if band:
                order.extend(sorted(band,key=lambda r:({'left':0,'right':1}[r[0]],r[1],r[3])))
                band.clear()
        for item in sorted(classified,key=lambda r:(r[1],r[3],r[0])):
            if item[0]=='full_page':flush();order.append(item)
            else:band.append(item)
        flush();mode='POSSIBLE_TWO_COLUMN_UNVERIFIED'
    seen=[i for _,_,ids,_ in order for i in ids]
    if sorted(seen)!=list(range(1,len(wordmap)+1)):
        raise DataError('Reading-order proposal lost or repeated source words')
    lines=[]
    for n,(column,y,ids,source_row) in enumerate(order,1):
        lines.append({'sequence':n,'source_row_id':source_row,'column_candidate':column,
                      'word_indices':ids,'untrusted_reading_text':' '.join(wordmap[i]['text_untrusted'] for i in ids),
                      'text_is_verified_pdf_quote':False,'line_order_confirmed':False})
    reasons=[reason,'TABLE_LIKE_OR_MULTI_COLUMN_CONTENT_MAY_MIMIC_GUTTERS','PAGE_REQUIRES_VISUAL_REVIEW']+sorted(set(issues))
    return {'page':page['page'],'mode':mode,'candidate_gutter_x':gutter,
            'candidate_lines':lines,'every_ocr_word_represented_once':True,
            'ambiguous_layout_reasons':reasons,
            'text_span_ids_unordered':deepcopy(page.get('text_span_ids',[]))}


def build_reading_order(layout,ocr_record=None):
    records,pages=_page_ocr(layout,ocr_record)
    result={'schema_version':1,'kind':'M3_UNVERIFIED_READING_ORDER_V5',
            'case_id':layout['case_id'],'layout_index_sha256':layout['index_sha256'],
            'ocr_record_sha256':layout.get('ocr_record_sha256'),
            'pages':[_page_order(page,records.get(page['page'])) for page in pages],
            'text_span_identity_preserved':True,'ocr_words_never_converted_to_pdf_quotes':True,
            'reading_order_verified':False,'tables_interpreted':False,
            'training_approved':False,'customer_release_allowed':False,
            'status':'READING_ORDER_REQUIRES_HUMAN_REVIEW'}
    result['reading_order_sha256']=digest(result)
    return result


def validate_reading_order(record,layout,ocr_record=None):
    expected=build_reading_order(layout,ocr_record)
    if not isinstance(record,dict) or record!=expected:
        raise DataError('Reading order stale, altered, or incomplete')
    return record
