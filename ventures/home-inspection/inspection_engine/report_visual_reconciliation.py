"""M3: compare independent, UNAUTHENTICATED human-declared visual report marks.

Spatial overlap is a review suggestion, NOT semantic truth or defect verification.
Never merges observations, accepts reports, authorizes learning, or creates labels.
"""
from __future__ import annotations
from copy import deepcopy
import json
from .core import DataError
from .report_review_queue import digest

MAX_VISUAL_MARKS = 128


def _validate(record, manifest):
    if not isinstance(record,dict) or record.get('kind')!='PENDING_HUMAN_PDF_VISUAL_MARKS':
        raise DataError('Visual review record required')
    check=deepcopy(record)
    observed=check.pop('record_sha256',None)
    if observed!=digest(check):raise DataError('Visual reviewer record changed')
    if (record.get('case_id')!=manifest['case_id']
        or record.get('manifest_sha256')!=manifest['manifest_sha256']
        or record.get('independent_review_required') is not True
        or record.get('not_text_quote_annotations') is not True
        or record.get('customer_release_allowed') is not False
        or record.get('training_approved') is not False):
        raise DataError('Visual reviewer record has wrong source or approval state')
    marks=record.get('marks')
    if not isinstance(marks,list) or not 1<=len(marks)<=MAX_VISUAL_MARKS:
        raise DataError('Visual review record missing original marks')
    ids=set();reviewer_ids=set();verified=[]
    pages={r['page']:r for r in manifest['pages']}
    for m in marks:
        if not isinstance(m,dict):raise DataError('Invalid visual mark')
        expected={'id','page','bbox','system','kind','feature_code','location','description',
            'reviewer_id','source_pdf_sha256','source_page_png_sha256','reference_bundle_sha256',
            'status','reviewer_authenticated','finding_approved','training_approved'}
        if set(m)!=expected:raise DataError('Visual mark field set tampered')
        if m['id'] in ids or not isinstance(m['id'],str):raise DataError('Duplicate visual mark')
        ids.add(m['id']);reviewer_ids.add(m['reviewer_id'])
        row=pages.get(m['page']) if type(m['page']) is int else None
        if (row is None or m['source_pdf_sha256']!=manifest['pdf_source_sha256']
            or m['source_page_png_sha256']!=row['sha256']
            or m['reference_bundle_sha256']!=manifest['reference_bundle_sha256']
            or m['status']!='HUMAN_DECLARED_UNVERIFIED'
            or m['reviewer_authenticated'] is not False
            or m['finding_approved'] is not False or m['training_approved'] is not False):
            raise DataError('Visual mark source or approval altered')
        bb=m['bbox']
        if (not isinstance(bb,list) or len(bb)!=4
            or any(type(v) not in (float,int) or not 0<=v<=1 for v in bb)
            or not bb[0]<bb[2] or not bb[1]<bb[3]):
            raise DataError('Visual mark coordinates invalid')
        # An existing record with a valid hash can be forged. Identity and mark
        # declarations must be rechecked against trusted system/code categories.
        from .descriptors import REQUIRED_FEATURES
        if (m['system'] not in REQUIRED_FEATURES or m['kind'] not in ('feature','potential_concern')
            or (m['kind']=='feature' and m['feature_code'] not in REQUIRED_FEATURES[m['system']])
            or (m['kind']=='potential_concern' and m['feature_code'] is not None)):
            raise DataError('Visual mark classification invalid')
        verified.append(m)
    if len(reviewer_ids)!=1:raise DataError('A review set cannot combine different reviewers')
    return next(iter(reviewer_ids)), verified


def _iou(a,b):
    left=max(a[0],b[0]);top=max(a[1],b[1]);right=min(a[2],b[2]);bottom=min(a[3],b[3])
    area=max(0,right-left)*max(0,bottom-top)
    if area==0:return 0.0
    aa=(a[2]-a[0])*(a[3]-a[1]);ab=(b[2]-b[0])*(b[3]-b[1])
    return area/(aa+ab-area)


def reconcile_visual_reviews(manifest,first,second):
    """One reproducible, independent-case pending queue; no automatic decisions."""
    if not isinstance(manifest,dict) or manifest.get('kind')!='UNVERIFIED_PDF_PAGE_EVIDENCE':
        raise DataError('Original PDF page evidence manifest required')
    clean=deepcopy(manifest);received=clean.pop('manifest_sha256',None)
    if received!=digest(clean) or manifest.get('visual_findings_verified') is not False:
        raise DataError('Original page evidence manifest invalid')
    a_id,a=_validate(first,manifest);b_id,b=_validate(second,manifest)
    if a_id==b_id:raise DataError('Reviewer declarations must have distinct identities')
    if len(a)*len(b)>16_384:raise DataError('Visual pair comparison exceeds bound')
    comparison=[];spatial_disputes=[];a_linked=set();b_linked=set()
    for am in a:
        for bm in b:
            if am['page']!=bm['page']:continue
            overlap=_iou(am['bbox'],bm['bbox'])
            if overlap<0.25:continue
            same=(am['system'],am['kind'],am['feature_code'])==(bm['system'],bm['kind'],bm['feature_code'])
            row={'first_id':am['id'],'second_id':bm['id'],'page':am['page'],
                'overlap_iou':round(overlap,5),'same_declared_category':same,
                'finding_identity_verified':False,'specialist_adjudication_required':True}
            if same and overlap>=0.5:
                comparison.append(row);a_linked.add(am['id']);b_linked.add(bm['id'])
            else:spatial_disputes.append(row)
    unmatched_a=[x['id'] for x in a if x['id'] not in a_linked]
    unmatched_b=[x['id'] for x in b if x['id'] not in b_linked]
    result={'schema_version':1,'kind':'PENDING_VISUAL_REVIEW_RECONCILIATION',
        'case_id':manifest['case_id'],'manifest_sha256':manifest['manifest_sha256'],
        'input_review_record_sha256':[first['record_sha256'],second['record_sha256']],
        'reviewer_declarations':[a_id,b_id],
        'possible_spatial_matches':comparison,'spatial_or_category_disputes':spatial_disputes,
        'unmatched_first_ids':unmatched_a,'unmatched_second_ids':unmatched_b,
        'original_mark_counts':[len(a),len(b)],'no_marks_dropped':True,
        'reviewers_authenticated':False,'semantic_agreement_verified':False,
        'ground_truth_established':False,'human_adjudication_required':True,
        'training_approved':False,'customer_release_allowed':False,
        'status':'INDEPENDENT_REVIEW_PENDING_VERIFICATION'}
    raw=json.dumps(result,ensure_ascii=True).encode()
    if len(raw)>1_000_000:raise DataError('Visual reconciliation output exceeds size budget')
    result['reconciliation_sha256']=digest(result)
    return result


def main(argv=None):
    """Private CLI requires re-render verification of underlying original PDF."""
    import argparse
    from pathlib import Path
    from .report_review_queue import _read_json, _write_new
    from .report_page_evidence import validate_page_evidence
    parser=argparse.ArgumentParser(description='Review independent UNVERIFIED PDF visual marks; never train')
    for name in ('reference','registry','source-pdf','manifest','first','second','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        bundle=_read_json(args.reference);registry=_read_json(args.registry)
        manifest=_read_json(args.manifest)
        validate_page_evidence(manifest,bundle,registry,args.source_pdf,args.manifest.parent)
        result=reconcile_visual_reviews(manifest,_read_json(args.first),_read_json(args.second))
        _write_new(args.out,result)
        print(json.dumps({'status':'INDEPENDENT_REVIEW_PENDING_VERIFICATION',
            'possible_spatial_matches':len(result['possible_spatial_matches']),
            'conflicting_or_unmatched_review_required':bool(result['spatial_or_category_disputes']
                or result['unmatched_first_ids'] or result['unmatched_second_ids']),
            'ground_truth_established':False,'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'training_approved':False,
                          'customer_release_allowed':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
