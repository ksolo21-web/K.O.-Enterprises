"""Milestone 3: whole-document PDF coverage and quarantined cross-modal review tasks.

A rendered page is NOT an inspected page. OCR words, human-declared visual marks,
text annotations and agent drafts remain distinct and unverified; no automatic
match, diagnosis, inspector sign-off, model learning or customer publication.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path

from .core import DataError, validate_project
from .report_review_queue import build_review_queue, validate_review_queue, digest, _read_json, _write_new
from .report_page_evidence import validate_page_evidence, MAX_BATCH_PAGES
from .report_ocr_review import validate_ocr_record
from .report_visual_reconciliation import reconcile_visual_reviews

MAX_DOCUMENT_BATCHES=25
MAX_DOCUMENT_OUTPUT=4_000_000
MAX_LINKS=256


def plan_document(bundle, registry):
    from .report_learning import validate_bundle
    from .study_registry import require_registered, validate_registry
    validate_registry(registry);validate_bundle(bundle);require_registered(bundle,registry)
    if bundle['source']['format']!='pdf':raise DataError('PDF source required for visual coverage plan')
    numbers=[p['number'] for p in bundle['pages']]
    batches=[numbers[i:i+MAX_BATCH_PAGES] for i in range(0,len(numbers),MAX_BATCH_PAGES)]
    if len(batches)>MAX_DOCUMENT_BATCHES:raise DataError('PDF batch plan exceeds governed limit')
    result={'schema_version':1,'kind':'PENDING_M3_DOCUMENT_PAGE_PLAN',
        'case_id':bundle['case_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
        'registry_sha256':digest(registry),'total_pages':len(numbers),
        'batches':[{'batch_index':i+1,'pages':group} for i,group in enumerate(batches)],
        'all_pages_scheduled':True,'pages_actually_rendered':0,
        'visual_review_completed':False,'qualified_inspector_approved':False,
        'training_approved':False,'customer_release_allowed':False}
    result['plan_sha256']=digest(result)
    return result


def audit_document(bundle,registry,text_queue,pdf_path:Path,batches:list,*,ocr_records:list|None=None,
                   independent_reviews:list|None=None):
    plan=plan_document(bundle,registry)
    validate_review_queue(text_queue,bundle,registry)
    if not isinstance(batches,list) or len(batches)>MAX_DOCUMENT_BATCHES:
        raise DataError('PDF rendering batches must be a bounded list')
    manifests={};render_locations={};page_row={};checked=[]
    for group in batches:
        if not isinstance(group,dict) or set(group)!={'manifest','render_dir'}:
            raise DataError('Render batch must contain manifest and private directory')
        manifest=group['manifest'];root=Path(group['render_dir'])
        validate_page_evidence(manifest,bundle,registry,pdf_path,root)
        if (manifest.get('all_requested_pages_rendered') is not True
            or manifest.get('all_report_pages_reviewed') is not False):
            raise DataError('Page render manifest falsely claims review completion')
        key=manifest['manifest_sha256']
        if key in manifests:raise DataError('Duplicate render batch')
        manifests[key]=manifest;render_locations[key]=root
        for row in manifest['pages']:
            n=row['page']
            if n in page_row:raise DataError('Duplicate rendered page across batches')
            page_row[n]={'render_batch_sha256':key,'page_png_sha256':row['sha256']}
        checked.append({'manifest_sha256':key,'pages':[r['page'] for r in manifest['pages']]})
    required={p['number'] for p in bundle['pages']};present=set(page_row)
    if not present.issubset(required):raise DataError('Extra rendered page outside imported report')
    missing=sorted(required-present)
    ocr_seen=set();ocr_page_hashes={};empty_ocr_pages=[]
    if ocr_records is None:ocr_records=[]
    if not isinstance(ocr_records,list) or len(ocr_records)>MAX_DOCUMENT_BATCHES:
        raise DataError('OCR record list exceeds document batch limit')
    for rec in ocr_records:
        if not isinstance(rec,dict) or rec.get('manifest_sha256') not in manifests:
            raise DataError('OCR record references a missing render batch')
        manifest=manifests[rec['manifest_sha256']]
        validate_ocr_record(rec,manifest)
        if rec['record_sha256'] in ocr_seen:raise DataError('Repeated OCR record')
        ocr_seen.add(rec['record_sha256'])
        for row in rec['pages']:
            n=row['page']
            if n in ocr_page_hashes:raise DataError('Duplicate OCR for one page')
            ocr_page_hashes[n]=rec['record_sha256']
            if row['empty_ocr_needs_manual_review']:empty_ocr_pages.append(n)
    reviews=[];reviewed_manifests=set();reviewer_mark_records=[]
    if independent_reviews is None:independent_reviews=[]
    if not isinstance(independent_reviews,list) or len(independent_reviews)>MAX_DOCUMENT_BATCHES:
        raise DataError('Independent reviewer pairs exceed bounded batch count')
    for pair in independent_reviews:
        if not isinstance(pair,dict) or set(pair)!={'manifest_sha256','first','second'}:
            raise DataError('Visual reviewer pair format invalid')
        key=pair['manifest_sha256']
        if key not in manifests or key in reviewed_manifests:raise DataError('Reviewer pair missing/duplicated batch')
        reviewed_manifests.add(key)
        rec=reconcile_visual_reviews(manifests[key],pair['first'],pair['second'])
        reviews.append({'manifest_sha256':key,'reconciliation_sha256':rec['reconciliation_sha256'],
            'possible_spatial_matches':len(rec['possible_spatial_matches']),
            'spatial_or_category_disputes':len(rec['spatial_or_category_disputes']),
            'unmatched_first_ids':rec['unmatched_first_ids'],
            'unmatched_second_ids':rec['unmatched_second_ids'],
            'human_adjudication_required':True})
        reviewer_mark_records.append(pair)
    unreadable=[p['number'] for p in bundle['pages'] if not p['text_available']]
    # OCR output is untrusted. It is never a substitute for inspecting the
    # original page pixels or for expert interpretation of tables/figures.
    result={'schema_version':1,'kind':'PENDING_FULL_DOCUMENT_VISUAL_COVERAGE',
        'case_id':bundle['case_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
        'registry_sha256':digest(registry),'text_queue_sha256':text_queue['queue_sha256'],
        'plan_sha256':plan['plan_sha256'],'document_page_count':len(required),
        'rendered_pages':sorted(present),'missing_rendered_pages':missing,
        'page_receipts':{str(k):v for k,v in sorted(page_row.items())},
        'validated_render_batches':checked,'ocr_page_receipts':{str(k):v for k,v in sorted(ocr_page_hashes.items())},
        'missing_ocr_for_textless_pages':sorted(set(unreadable)-set(ocr_page_hashes)),
        'ocr_attempts_with_no_recognized_words':sorted(empty_ocr_pages),
        'pages_still_requiring_professional_visual_review':sorted(required),
        'independent_visual_review_pairs':reviews,
        'pages_rendered_all':not bool(missing),'text_queue_complete':True,
        'all_page_pixels_reviewed_by_qualified_person':False,
        'independent_reviewers_authenticated':False,
        'visual_disagreements_resolved':False,
        'no_report_defects_verified_from_ocr':True,
        'human_adjudication_required':True,
        'training_approved':False,'customer_release_allowed':False,
        'status':'REQUIRES_QUALIFIED_HUMAN_VISUAL_AND_TEXT_REVIEW'}
    if len(json.dumps(result,ensure_ascii=True).encode())>MAX_DOCUMENT_OUTPUT:
        raise DataError('Whole-document audit exceeds output limit')
    result['audit_sha256']=digest(result)
    return result


def cross_modal_queue(document,bundle,registry,text_queue,pdf_path,batches,
                      *,annotations:list,independent_reviews:list,ocr_records:list|None=None):
    """Hold every text annotation, visual mark and agent draft as a separate task.

    Nothing from a scanned page is converted into an invented PDF-text quote.
    Reviewers may later create explicit candidate links, which still cannot train.
    """
    audit=audit_document(bundle,registry,text_queue,pdf_path,batches,
                         independent_reviews=independent_reviews,ocr_records=ocr_records)
    if not isinstance(document,dict) or document.get('project_id')!=bundle['case_id']:
        raise DataError('Inspection case does not match private reference')
    from .report_learning import prepare_comparison, _agent_entries
    if not isinstance(annotations,list) or len(annotations)>128:
        raise DataError('Text annotations must be a bounded explicit list')
    # Existing comparison is authoritative for text-quote identity and source.
    comparison=prepare_comparison(document,bundle,annotations,registry=registry) if annotations else None
    if comparison is None:validate_project(document,Path('.'),strict_files=False)
    agents=comparison['agent_entries'] if comparison else _agent_entries(document)
    texts=comparison['reference_entries'] if comparison else []
    manifests={x['manifest']['manifest_sha256']:x['manifest'] for x in batches}
    visual=[];seen=set()
    for pair in independent_reviews:
        manifest=manifests[pair['manifest_sha256']]
        for name in ('first','second'):
            for mark in pair[name]['marks']:
                ident=f"visual:{pair['manifest_sha256']}:{mark['reviewer_id']}:{mark['id']}"
                if ident in seen:raise DataError('Duplicate cross-modal visual identity')
                seen.add(ident)
                visual.append({'review_id':ident,'page':mark['page'],'bbox':deepcopy(mark['bbox']),
                    'source_page_png_sha256':mark['source_page_png_sha256'],
                    'source_pdf_sha256':mark['source_pdf_sha256'],
                    'system_unverified':mark['system'],'description_untrusted':mark['description'],
                    'reviewer_authenticated':False,'finding_confirmed':False})
    result={'schema_version':1,'kind':'UNVERIFIED_CROSS_MODAL_REPORT_REVIEW_QUEUE',
        'case_id':bundle['case_id'],'document_audit_sha256':audit['audit_sha256'],
        'reference_bundle_sha256':bundle['bundle_sha256'],'project_sha256':digest(document),
        'text_comparison_sha256':comparison['comparison_sha256'] if comparison else None,
        'text_reference_entries':deepcopy(texts),'visual_reference_entries':visual,
        'agent_entries':deepcopy(agents),
        'text_reference_review_ids':[x['entry_id'] for x in texts],
        'visual_reference_review_ids':[x['review_id'] for x in visual],
        'agent_review_ids':[x['entry_id'] for x in agents],
        'unresolved_page_numbers':list(range(1,audit['document_page_count']+1)),
        'all_claims_kept_separate':True,
        'possible_spatial_match_is_not_finding_identity':True,
        'ocr_text_is_not_a_quote_or_ground_truth':True,
        'no_automatic_merges':True,'professional_reviewer_approval_authenticated':False,
        'training_approved':False,'customer_release_allowed':False,
        'status':'CROSS_MODAL_ADJUDICATION_PENDING'}
    if len(json.dumps(result,ensure_ascii=True).encode())>MAX_DOCUMENT_OUTPUT:
        raise DataError('Cross-modal queue exceeds output bound')
    result['queue_sha256']=digest(result)
    return result


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description='Private PDF page-coverage audit; no model or training')
    p.add_argument('command',choices=['plan','audit'])
    for field in ('reference','registry','out'):
        p.add_argument('--'+field,required=True,type=Path)
    p.add_argument('--text-queue',type=Path)
    p.add_argument('--source-pdf',type=Path)
    p.add_argument('--batches',type=Path,help='JSON array of {manifest:path,render_dir:path} objects')
    p.add_argument('--ocr-records',type=Path,help='JSON array of OCR record paths')
    a=p.parse_args(argv)
    try:
        bundle=_read_json(a.reference);registry=_read_json(a.registry)
        if a.command=='plan':result=plan_document(bundle,registry)
        else:
            if not a.text_queue or not a.source_pdf or not a.batches:
                raise DataError('Audit needs text queue, original PDF and batch index')
            indexed=_read_json(a.batches)
            if not isinstance(indexed,list) or len(indexed)>MAX_DOCUMENT_BATCHES:
                raise DataError('Invalid batch path index')
            groups=[]
            for item in indexed:
                if not isinstance(item,dict) or set(item)!={'manifest','render_dir'}:
                    raise DataError('Invalid batch index row')
                groups.append({'manifest':_read_json(Path(item['manifest'])),'render_dir':Path(item['render_dir'])})
            selected=_read_json(a.ocr_records) if a.ocr_records else []
            if not isinstance(selected,list) or len(selected)>MAX_DOCUMENT_BATCHES:
                raise DataError('Invalid OCR index')
            result=audit_document(bundle,registry,_read_json(a.text_queue),a.source_pdf,groups,
                ocr_records=[_read_json(Path(path)) for path in selected])
        _write_new(a.out,result)
        print(json.dumps({'status':result.get('status','PLAN_ONLY'),'missing_pages':len(result.get('missing_rendered_pages',[])),
            'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,TypeError,ValueError,KeyError,UnicodeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'training_approved':False,'customer_release_allowed':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())


def record_cross_modal_decisions(queue:dict,decisions:list,*,reviewer_id:str)->dict:
    """Record only unverified human cross-modal correspondence, never lessons.

    Every text/visual reference gets exactly one explicit decision. Every agent
    claim remains in the unmatched review queue unless a reviewer proposes a
    possible relationship; even then the relationship is NOT verified truth.
    """
    import re
    if (not isinstance(queue,dict) or queue.get('kind')!='UNVERIFIED_CROSS_MODAL_REPORT_REVIEW_QUEUE'
        or queue.get('queue_sha256')!=digest({k:v for k,v in queue.items() if k!='queue_sha256'})
        or queue.get('professional_reviewer_approval_authenticated') is not False
        or queue.get('training_approved') is not False or queue.get('customer_release_allowed') is not False
        or queue.get('no_automatic_merges') is not True):
        raise DataError('Cross-modal queue missing/stale or falsely approved')
    if not isinstance(reviewer_id,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{2,80}',reviewer_id):
        raise DataError('Human reviewer declaration ID required')
    sources=queue['text_reference_review_ids']+queue['visual_reference_review_ids']
    agents=set(queue['agent_review_ids'])
    if (len(sources)!=len(set(sources)) or len(agents)!=len(queue['agent_review_ids'])
        or not isinstance(decisions,list) or len(decisions)!=len(sources)):
        raise DataError('Must decide every source once, without dropping any')
    allowed={'possible_correspondence','possible_conflict','potential_missed_issue',
             'reference_error','needs_more_evidence','unrelated_to_agent','unresolved'}
    seen=set();clean=[];linked=set()
    for choice in decisions:
        if not isinstance(choice,dict) or set(choice)!={'reference_review_id','relation',
                   'candidate_agent_ids','explanation'}:
            raise DataError('Cross-modal decision field set invalid')
        ident=choice['reference_review_id'];rel=choice['relation'];targets=choice['candidate_agent_ids']
        if ident not in sources or ident in seen or rel not in allowed:
            raise DataError('Unknown, duplicate, or unauthorized source decision')
        seen.add(ident)
        if (not isinstance(targets,list) or len(targets)>16 or len(targets)!=len(set(targets))
            or any(not isinstance(x,str) or x not in agents for x in targets)):
            raise DataError('Unrecognized candidate agent source')
        if ((rel in {'possible_correspondence','possible_conflict'} and not targets)
            or (rel in {'potential_missed_issue','reference_error','needs_more_evidence',
                         'unrelated_to_agent','unresolved'} and targets)):
            raise DataError('Decision relation incompatible with candidate targets')
        exp=choice['explanation']
        if not isinstance(exp,str) or not exp.strip() or len(exp)>1500 or any(ord(c)<32 and c not in '\n\r\t' for c in exp):
            raise DataError('Decision requires bounded explanation')
        clean.append(deepcopy(choice));linked.update(targets)
    if seen!=set(sources):raise DataError('Incomplete human cross-modal decisions')
    result={'schema_version':1,'kind':'QUARANTINED_CROSS_MODAL_CORRESPONDENCE',
        'case_id':queue['case_id'],'review_queue_sha256':queue['queue_sha256'],
        'reviewer_declaration':reviewer_id,'reviewer_authenticated':False,
        'source_decision_count':len(clean),'all_references_preserved':True,
        'decisions':clean,'unmatched_agent_ids':sorted(agents-linked),
        'possible_match_is_not_verified_identity':True,
        'verified_defect_labels':[],'promotable_lessons':[],
        'professional_signoff_required':True,'training_approved':False,
        'customer_release_allowed':False,'status':'PENDING_QUALIFIED_REVIEW_AND_CASE_EVIDENCE'}
    if len(json.dumps(result,ensure_ascii=True).encode())>MAX_DOCUMENT_OUTPUT:
        raise DataError('Cross-modal decisions exceed size budget')
    result['decisions_sha256']=digest(result)
    return result
