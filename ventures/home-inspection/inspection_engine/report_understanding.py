"""Source-backed HUMAN DECLARATIONS of report structure; never semantic truth.

Original PDF text, untrusted OCR and selected image pixels remain distinct.
Every declaration is reproducible against the current source/registry/receipts.
"""
from __future__ import annotations
from copy import deepcopy
import json
import re

from .core import DataError, SYSTEM_NAME
from .report_document_coverage import audit_document
from .report_layout_navigation import validate_layout_index, _rect
from .report_review_queue import digest

ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}\Z')
MAX_RECORD_BYTES=4_000_000


def _text(value,label,limit=1000):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 and c not in '\n\t' for c in value)):
        raise DataError('Invalid '+label)
    return value


def _array(value,label,limit=128):
    if not isinstance(value,list) or len(value)>limit:raise DataError('Invalid '+label)
    return value


def _fields(value,fields,label):
    if not isinstance(value,dict) or set(value)!=set(fields.split()):raise DataError('Invalid '+label+' fields')


def checked_sources(bundle,registry,queue,pdf_path,batches):
    if not isinstance(batches,list) or not 1<=len(batches)<=25:raise DataError('Invalid source batches')
    for g in batches:
        if not isinstance(g,dict) or set(g) not in ({'manifest','layout','render_dir'},
                {'manifest','layout','render_dir','ocr_record'}):raise DataError('Invalid source batch fields')
    audit=audit_document(bundle,registry,queue,pdf_path,
        [{'manifest':g['manifest'],'render_dir':g['render_dir']} for g in batches],
        ocr_records=[g['ocr_record'] for g in batches if 'ocr_record' in g])
    pages={};words={}
    for group in batches:
        validate_layout_index(group['layout'],group['manifest'],bundle,registry,pdf_path,
            group['render_dir'],queue,ocr_record=group.get('ocr_record'))
        for page in group['manifest']['pages']:pages[page['page']]=page
        if 'ocr_record' in group:
            for page in group['ocr_record']['pages']:
                words[page['page']]={w['word_index']:w for w in page['untrusted_ocr_words']}
    return audit,pages,words


def capture_report_mapping(bundle,registry,queue,pdf_path,batches,declarations,*,origin='human_declared'):
    if origin not in ('human_declared','model_proposed'):raise DataError('Invalid mapping origin')
    audit,pages,words=checked_sources(bundle,registry,queue,pdf_path,batches)
    _fields(declarations,'reviewer_id coverage sections tables figures findings relations','declaration')
    _text(declarations['reviewer_id'],'reviewer ID',80)
    spans={s['span_id']:s for s in queue['spans']}
    all_pages={p['number'] for p in bundle['pages']}
    anchor_count=0;seen=set()

    def ident(value):
        if not isinstance(value,str) or not ID.fullmatch(value) or value in seen:
            raise DataError('Invalid or duplicate mapping identity')
        seen.add(value);return value

    def anchors(items,*,page=None):
        nonlocal anchor_count
        _array(items,'evidence anchors',32)
        if not items:raise DataError('Source anchors required')
        result=[]
        for a in items:
            anchor_count+=1
            if anchor_count>2048:raise DataError('Too many mapping evidence anchors')
            if not isinstance(a,dict):raise DataError('Invalid source anchor')
            n=a.get('page')
            if type(n) is not int or n not in all_pages or (page is not None and n!=page):
                raise DataError('Anchor page outside declared source')
            kind=a.get('kind')
            if kind=='pdf_text':
                _fields(a,'kind page span_id offset quote','PDF text anchor')
                span=spans.get(a['span_id']);offset=a['offset'];quote=a['quote']
                _text(quote,'exact source quote',2000)
                if (span is None or span['page']!=n or type(offset) is not int or offset<0
                        or span['text'][offset:offset+len(quote)]!=quote):
                    raise DataError('PDF quote does not match exact original span/offset')
                result.append(dict(deepcopy(a),source_text_sha256=span['text_sha256'],
                    source_page_offset=span['start']+offset,interpretation_verified=False))
            elif kind=='ocr_words':
                _fields(a,'kind page word_indices','OCR anchor')
                ids=a['word_indices'];_array(ids,'OCR word IDs',128)
                if (not ids or any(type(i) is not int or i not in words.get(n,{}) for i in ids)
                        or ids!=sorted(set(ids))):raise DataError('Invalid original OCR word references')
                result.append(dict(deepcopy(a),source_words_untrusted=[deepcopy(words[n][i]) for i in ids],
                    source_page_png_sha256=pages[n]['sha256'],text_is_verified_pdf_quote=False))
            elif kind=='image_region':
                _fields(a,'kind page bbox','image anchor')
                if n not in pages or not _rect(a['bbox']):raise DataError('Missing image or invalid selected region')
                result.append(dict(deepcopy(a),source_page_png_sha256=pages[n]['sha256'],
                    image_semantics_verified=False))
            else:raise DataError('Unknown source anchor kind')
        return result

    coverage=[];covered=set()
    for item in _array(declarations['coverage'],'page dispositions',200):
        _fields(item,'page status note','page disposition')
        n=item['page']
        if type(n) is not int or n not in all_pages or n in covered:raise DataError('Invalid/duplicate coverage page')
        covered.add(n);_text(item['note'],'page disposition note')
        if item['status'] not in ('declared_reviewed','unresolved'):raise DataError('Unknown page disposition')
        if item['status']=='declared_reviewed' and n not in pages:raise DataError('Cannot declare unseen page reviewed')
        coverage.append(deepcopy(item))
    if covered!=all_pages:raise DataError('Every source page needs an explicit disposition')
    sections=[]
    for item in _array(declarations['sections'],'sections'):
        _fields(item,'id title anchors','section');ident(item['id']);_text(item['title'],'section title',200)
        sections.append(dict(deepcopy(item),anchors=anchors(item['anchors'])))
    section_ids={s['id'] for s in sections}
    tables=[];cell_ids=set();total_cells=0
    for item in _array(declarations['tables'],'tables',16):
        _fields(item,'id page column_count rows','table');ident(item['id'])
        used_source_words=set()
        n=item['page'];columns=item['column_count']
        if type(n) is not int or n not in pages or type(columns) is not int or not 1<=columns<=16:
            raise DataError('Invalid table page/column count')
        rows=[]
        for row in _array(item['rows'],'table rows',128):
            _fields(row,'id cells','table row');ident(row['id']);occupied=set();cells=[]
            for cell in _array(row['cells'],'table cells',16):
                _fields(cell,'id column column_span role anchors','table cell');ident(cell['id']);cell_ids.add(cell['id'])
                total_cells+=1
                if total_cells>2048:raise DataError('Table cell limit exceeded')
                start=cell['column'];width=cell['column_span']
                if type(start) is not int or type(width) is not int or not 1<=start<=columns or not 1<=width<=columns-start+1:
                    raise DataError('Invalid cell position/span')
                slots=set(range(start,start+width))
                if occupied & slots:raise DataError('Overlapping declared table cells')
                occupied|=slots
                if cell['role'] not in ('header','data','blank','unresolved'):raise DataError('Invalid declared cell role')
                aa=anchors(cell['anchors'],page=n)
                for a in aa:
                    if a['kind']=='ocr_words':
                        tokens={(n,i) for i in a['word_indices']}
                        if used_source_words & tokens:raise DataError('OCR word assigned to multiple table cells')
                        used_source_words|=tokens
                if cell['role']=='blank' and any(a['kind']!='image_region' for a in aa):
                    raise DataError('Blank cells require explicitly selected source image regions')
                cells.append(dict(deepcopy(cell),anchors=aa,role_verified=False))
            if not cells:raise DataError('Table row needs explicit cells')
            rows.append({'id':row['id'],'cells':cells,'unassigned_columns':sorted(set(range(1,columns+1))-occupied)})
        if not rows:raise DataError('Table requires explicit source-backed rows')
        tables.append(dict(deepcopy(item),rows=rows,structure_verified=False))
    figures=[]
    for item in _array(declarations['figures'],'figures'):
        _fields(item,'id kind region caption_anchors','figure');ident(item['id'])
        if item['kind'] not in ('photo','diagram','unclassified'):raise DataError('Invalid declared figure kind')
        region=anchors([item['region']])[0]
        if region['kind']!='image_region':raise DataError('Figure requires a source image region')
        captions=anchors(item['caption_anchors']) if item['caption_anchors'] else []
        figures.append(dict(deepcopy(item),region=region,caption_anchors=captions,classification_verified=False))
    figure_ids={f['id'] for f in figures};findings=[]
    for item in _array(declarations['findings'],'report findings'):
        _fields(item,'id system location description anchors section_ids figure_ids table_cell_ids','report finding')
        ident(item['id']);_text(item['location'],'location',200);_text(item['description'],'description',2000)
        if item['system'] not in SYSTEM_NAME:raise DataError('Invalid finding system')
        for key,allowed in [('section_ids',section_ids),('figure_ids',figure_ids),('table_cell_ids',cell_ids)]:
            ids=_array(item[key],key,32)
            if any(not isinstance(i,str) or i not in allowed for i in ids) or len(set(ids))!=len(ids):
                raise DataError('Unknown/duplicate mapping target')
        findings.append(dict(deepcopy(item),anchors=anchors(item['anchors']),finding_verified=False))
    finding_ids={f['id'] for f in findings};finding_pages={f['id']:{a['page'] for a in f['anchors']} for f in findings};relations=[]
    for item in _array(declarations['relations'],'cross-page relationships'):
        _fields(item,'id kind from_finding to_finding reason anchors','relationship');ident(item['id'])
        if (item['kind'] not in ('continuation','supports','contradicts','same_component_candidate')
                or item['from_finding'] not in finding_ids or item['to_finding'] not in finding_ids
                or item['from_finding']==item['to_finding']):raise DataError('Invalid finding relationship')
        _text(item['reason'],'relationship explanation')
        aa=anchors(item['anchors'])
        involved={a['page'] for a in aa}
        if len(involved)<2:raise DataError('Cross-page relation needs source anchors on both pages')
        if not any(a!=b and {a,b}<=involved for a in finding_pages[item['from_finding']] for b in finding_pages[item['to_finding']]):
            raise DataError('Cross-page anchors must include distinct source pages of both endpoint findings')
        if any(n not in pages for n in range(min(involved),max(involved)+1)):
            raise DataError('Cross-page relation cannot skip unrendered intervening pages')
        relations.append(dict(deepcopy(item),anchors=aa,relation_verified=False,records_merged=False))
    result={'schema_version':1,'kind':('HUMAN_DECLARED_REPORT_UNDERSTANDING_V7' if origin=='human_declared' else 'MODEL_PROPOSED_REPORT_UNDERSTANDING_V8'),
        'origin':origin,'case_id':bundle['case_id'],
        'reference_bundle_sha256':bundle['bundle_sha256'],'source_pdf_sha256':bundle['source']['sha256'],
        'document_audit_sha256':audit['audit_sha256'],'declarations':deepcopy(declarations),
        'coverage':sorted(coverage,key=lambda x:x['page']),'sections':sections,'tables':tables,
        'figures':figures,'findings':findings,'relations':relations,
        'unresolved_pages':[p['page'] for p in coverage if p['status']=='unresolved'],
        'missing_rendered_pages':audit['missing_rendered_pages'],
        'missing_ocr_for_textless_pages':audit['missing_ocr_for_textless_pages'],
        'reviewer_authenticated':False,'semantic_understanding_verified':False,
        'training_approved':False,'customer_release_allowed':False,'status':'PROFESSIONAL_STRUCTURE_REVIEW_PENDING'}
    if len(json.dumps(result,ensure_ascii=True).encode())>MAX_RECORD_BYTES:raise DataError('Report mapping exceeds 4MB')
    result['mapping_sha256']=digest(result)
    return result


def validate_report_mapping(record,bundle,registry,queue,pdf_path,batches):
    if not isinstance(record,dict) or record!=capture_report_mapping(bundle,registry,queue,pdf_path,batches,record.get('declarations'),origin=record.get('origin','human_declared')):
        raise DataError('Report mapping stale, altered or incomplete')
    return record


def milestone_readiness(mapping):
    """Non-authorizing status, never accepts freely supplied professional flags."""
    clean=deepcopy(mapping);received=clean.pop('mapping_sha256',None)
    if (received!=digest(clean) or mapping.get('kind') not in ('HUMAN_DECLARED_REPORT_UNDERSTANDING_V7','MODEL_PROPOSED_REPORT_UNDERSTANDING_V8')
            or any(mapping.get(k) is not False for k in ('reviewer_authenticated','semantic_understanding_verified',
                'training_approved','customer_release_allowed'))):raise DataError('Invalid mapping readiness input')
    blockers=['INSPECTOR_REVIEWED_SEMANTIC_EXTRACTION_NOT_ESTABLISHED',
        'AUTHENTICATED_REVIEW_AND_CASE_PROVENANCE_NOT_ESTABLISHED',
        'HELD_OUT_SEMANTIC_AND_LEARNING_EVALUATION_NOT_COMPLETED',
        'LEARNING_FRAMEWORK_REQUIRES_TRUSTED_ENROLLMENT_AND_REAL_EVALUATION']
    if mapping.get('origin')=='model_proposed':blockers.append('MODEL_PROPOSALS_REQUIRE_HUMAN_SOURCE_REVIEW')
    if mapping['unresolved_pages']:blockers.append('UNRESOLVED_PAGE_DISPOSITIONS')
    if mapping['missing_rendered_pages']:blockers.append('MISSING_RENDERED_PAGES')
    if mapping['missing_ocr_for_textless_pages']:blockers.append('MISSING_SCAN_OCR')
    return {'kind':'M3_ORIGINAL_SCOPE_READINESS','mapping_sha256':received,'blockers':blockers,
        'full_milestone_3_complete':False,'training_approved':False,'customer_release_allowed':False}
