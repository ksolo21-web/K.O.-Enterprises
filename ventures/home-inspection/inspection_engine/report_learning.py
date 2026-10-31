"""Local report-study foundation. Imported text and corrections are untrusted data.

No model calls, OCR, automatic defect labels, prompt updates or weight training.
Checksums bind versions; they do not authenticate authors, consent or credentials.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from .core import DataError,SYSTEM_NAME,validate_project
from .capture import verify_custody

MAX_SOURCE_BYTES=20_000_000
MAX_PAGES=200
MAX_TEXT=500_000
PARTITIONS={'reference','training_candidate','locked_holdout'}
CATEGORIES={'missed_observation','false_alarm','description_correction','evidence_gap',
            'ambiguous_match','reference_error','no_change'}
HEX=re.compile(r'[0-9a-f]{64}\Z')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _text(value,name,limit,*,empty=False):
    if (not isinstance(value,str) or len(value)>limit or (not empty and not value.strip())
        or any(ord(c)<32 and c not in '\n\r\t' for c in value)):
        raise DataError('Invalid '+name)
    return value


def _pdf_pages(raw):
    """Bound parser memory/CPU/wall time in a disposable local child process."""
    try:
        result=subprocess.run([sys.executable,'-m','inspection_engine.report_learning','_pdf-worker'],input=raw,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=False)
    except subprocess.TimeoutExpired as exc:raise DataError('PDF text extraction exceeded 20-second limit') from exc
    if result.returncode or len(result.stdout)>MAX_TEXT*7+10_000:
        raise DataError('PDF parser rejected document or exceeded resource limits')
    try:pages=json.loads(result.stdout)
    except (ValueError,UnicodeError) as exc:raise DataError('PDF parser returned invalid text') from exc
    return pages


def _bounded_source(path):
    import os
    import stat
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise DataError('Reference must be a regular file')
        raw=stream.read(MAX_SOURCE_BYTES+1)
    if not 1<=len(raw)<=MAX_SOURCE_BYTES:raise DataError('Reference exceeds 20MB limit or is empty')
    return raw


def text_fingerprint(pages,source_sha):
    import unicodedata
    words=' '.join(unicodedata.normalize('NFKC',' '.join(pages)).casefold().split())
    return digest(words if words else {'unreadable_source':source_sha})


def import_reference(path:Path,*,case_id:str,partition:str,authorized_use:bool,consented:bool):
    _text(case_id,'case ID',100)
    if partition not in PARTITIONS:raise DataError('Explicit report-study partition required')
    if authorized_use is not True or consented is not True:
        raise DataError('Explicit authorized-use and comparison-consent declarations required')
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise DataError('Reference must be a regular local file')
    if not 1<=path.stat().st_size<=MAX_SOURCE_BYTES:raise DataError('Reference exceeds 20MB limit or is empty')
    raw=_bounded_source(path)
    if len(raw)>MAX_SOURCE_BYTES:raise DataError('Reference changed beyond source size limit')
    suffix=path.suffix.lower()
    if suffix=='.pdf':
        page_data=_pdf_pages(raw)
        pages=[p['text'] for p in page_data]
        # Detect replacement while child process read the original file.
        if _bounded_source(path)!=raw:raise DataError('Reference changed during extraction')
    elif suffix=='.txt':
        try:
            pages=[raw.decode('utf-8')]
            page_data=[{'text':pages[0],'has_raster_images':False}]
        except UnicodeError as exc:raise DataError('Text reference must be UTF-8') from exc
    else:raise DataError('Supported reference formats are PDF and UTF-8 TXT')
    if (not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES
        or any(not isinstance(p,str) for p in pages) or sum(map(len,pages))>MAX_TEXT):
        raise DataError('Reference exceeds page/text limits or contains invalid pages')
    for page in pages:_text(page,'page text',MAX_TEXT,empty=True)
    bundle={'schema_version':1,'kind':'UNVERIFIED_REFERENCE_TEXT','case_id':case_id,'partition':partition,
        'source':{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'format':suffix[1:]},
        'pages':[{'number':i+1,'text':p,'text_available':bool(p.strip()),
            'has_raster_images':page_data[i]['has_raster_images'],
            'review_limitations':['IMAGES_LAYOUT_HANDWRITING_NOT_ANALYZED']+(['NO_EXTRACTABLE_TEXT_OCR_REQUIRED'] if not p.strip() else [])}
            for i,p in enumerate(pages)],
        'text_sha256':text_fingerprint(pages,hashlib.sha256(raw).hexdigest()),
        'unreadable_text_pages':[i+1 for i,p in enumerate(pages) if not p.strip()],
        'scope':'TEXT_ONLY_IMAGES_LAYOUT_AND_HANDWRITING_NOT_REVIEWED',
        'authorization_declared':True,'comparison_consent_declared':True,
        'authorization_authenticated':False,'source_author_authenticated':False,
        'human_review_required':True,'training_approved':False,'customer_release_allowed':False}
    bundle['bundle_sha256']=digest(bundle)
    return bundle


def validate_bundle(bundle):
    if not isinstance(bundle,dict):raise DataError('Reference bundle must be an object')
    clean=deepcopy(bundle);recorded=clean.pop('bundle_sha256',None)
    if recorded!=digest(clean):raise DataError('Reference bundle digest mismatch')
    if (bundle.get('schema_version')!=1 or bundle.get('kind')!='UNVERIFIED_REFERENCE_TEXT'
        or bundle.get('partition') not in PARTITIONS):raise DataError('Invalid reference bundle identity')
    _text(bundle.get('case_id'),'case ID',100)
    source=bundle.get('source',{})
    if (not isinstance(source,dict) or not isinstance(source.get('sha256'),str) or not HEX.fullmatch(source['sha256'])
        or type(source.get('bytes')) is not int or not 1<=source['bytes']<=MAX_SOURCE_BYTES
        or source.get('format') not in {'pdf','txt'}):raise DataError('Invalid reference source receipt')
    pages=bundle.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES:raise DataError('Invalid reference pages')
    for i,page in enumerate(pages,1):
        if not isinstance(page,dict) or page.get('number')!=i:raise DataError('Invalid reference page order')
        _text(page.get('text'),'page text',MAX_TEXT,empty=True)
        if page.get('text_available') is not bool(page['text'].strip()):raise DataError('Invalid text availability')
        if type(page.get('has_raster_images')) is not bool:raise DataError('Invalid page image metadata')
        expected=['IMAGES_LAYOUT_HANDWRITING_NOT_ANALYZED']+(['NO_EXTRACTABLE_TEXT_OCR_REQUIRED'] if not page['text'].strip() else [])
        if page.get('review_limitations')!=expected:raise DataError('Invalid page completeness warnings')
    if bundle.get('text_sha256')!=text_fingerprint([p['text'] for p in pages],source['sha256']):raise DataError('Reference text checksum mismatch')
    if sum(len(p['text']) for p in pages)>MAX_TEXT:raise DataError('Reference text exceeds limit')
    if bundle.get('unreadable_text_pages')!=[p['number'] for p in pages if not p['text'].strip()]:raise DataError('Missing-text register mismatch')
    if bundle.get('scope')!='TEXT_ONLY_IMAGES_LAYOUT_AND_HANDWRITING_NOT_REVIEWED':raise DataError('Unsupported extraction scope')
    for key,val in [('authorization_declared',True),('comparison_consent_declared',True),
        ('authorization_authenticated',False),('source_author_authenticated',False),('human_review_required',True),
        ('training_approved',False),('customer_release_allowed',False)]:
        if bundle.get(key) is not val:raise DataError('Reference cannot authenticate, train or release')
    return bundle


def _agent_entries(document):
    validate_project(document,Path('.'),strict_files=False)
    result=[]
    for section in ('observations','findings'):
        for item in document[section]:
            _text(item['id'],'agent entry ID',100)
            description=item.get('description',item.get('feature','')) if section=='observations' else item['condition']
            _text(description,'agent description',2000)
            _text(item.get('location','Not specified'),'agent location',150)
            result.append({'entry_id':'agent:'+section+':'+item['id'],'kind':'feature' if section=='observations' else 'potential_concern',
                'system':item['system'],'feature_code':item.get('feature_code'),
                'location':item.get('location','Not specified'),
                'description':description,
                'evidence_ids':list(item.get('evidence_ids',[])),'review':item['review']})
    if len(result)>128:raise DataError('Report comparison requires explicit batching above 128 claims')
    return result


def prepare_comparison(document,bundle,annotations,*,registry):
    """Explicit page-quote annotations; exact-key candidates are never accepted matches."""
    validate_bundle(bundle)
    from .study_registry import require_registered
    require_registered(bundle,registry)
    if document['project_id']!=bundle['case_id']:raise DataError('Reference and inspection case IDs differ')
    agents=_agent_entries(document)
    if not isinstance(annotations,list) or not 1<=len(annotations)<=128:raise DataError('Require 1-128 explicit reference annotations')
    refs=[];seen=set()
    for item in annotations:
        if not isinstance(item,dict) or set(item)!={'id','system','kind','feature_code','location','description','page','quote','offset'}:
            raise DataError('Reference annotation fields are invalid')
        for key,limit in [('id',60),('location',150),('description',1000),('quote',2000)]:_text(item[key],key,limit)
        if item['id'] in seen:raise DataError('Duplicate annotation ID; no reference claim may be overwritten')
        seen.add(item['id'])
        if item['system'] not in SYSTEM_NAME or item['kind'] not in {'feature','potential_concern'}:
            raise DataError('Unknown reference system or kind')
        if item['feature_code'] is not None:_text(item['feature_code'],'feature code',100)
        page=item['page']
        offset=item['offset']
        if (type(page) is not int or not 1<=page<=len(bundle['pages']) or type(offset) is not int or offset<0
            or bundle['pages'][page-1]['text'][offset:offset+len(item['quote'])]!=item['quote']):
            raise DataError('Reference annotation must quote its exact imported page')
        refs.append(dict(deepcopy(item),entry_id='reference:'+item['id']))
    def identity(x):return (x['system'],x['kind'],x['feature_code'],' '.join(x['location'].casefold().split()))
    candidates={r['entry_id']:[a['entry_id'] for a in agents if identity(a)==identity(r)] for r in refs}
    result={'schema_version':1,'case_id':document['project_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
        'project_snapshot_sha256':digest(document),'annotations':deepcopy(annotations),
        'reference_entries':refs,'agent_entries':agents,'candidate_matches':candidates,
        'review_entry_ids':[r['entry_id'] for r in refs]+[a['entry_id'] for a in agents],
        'status':'AWAITING_HUMAN_COMPARISON','exact_key_is_semantic_match':False,
        'human_reference_is_ground_truth':False,'training_approved':False,'customer_release_allowed':False}
    if len(json.dumps(result,ensure_ascii=True).encode())>4_000_000:
        raise DataError('Comparison exceeds 4MB bounded output; explicit batching required')
    result['comparison_sha256']=digest(result)
    return result


def record_corrections(document,root:Path,bundle,comparison,decisions,*,reviewer_id,registry):
    """Save human-declared corrections as pending candidates; never activate learning."""
    _text(reviewer_id,'reviewer ID',80)
    if not isinstance(comparison,dict):raise DataError('Comparison record required')
    expected=prepare_comparison(document,bundle,comparison.get('annotations'),registry=registry)
    if comparison!=expected:raise DataError('Comparison is stale or altered; rerun comparison')
    validate_project(document,root)
    if verify_custody(document,root):raise DataError('Evidence custody failed before correction capture')
    if not isinstance(decisions,list):raise DataError('Correction decisions required')
    ids=set(comparison['review_entry_ids']);seen=set();clean=[];lessons=[]
    media={m['id']:m for m in document['media']}
    for item in decisions:
        if not isinstance(item,dict) or set(item)!={'entry_id','category','related_entry_ids','evidence_ids','explanation','lesson_text'}:
            raise DataError('Invalid correction fields')
        ident=item['entry_id'];category=item['category']
        if not isinstance(ident,str) or ident not in ids or ident in seen or category not in CATEGORIES:
            raise DataError('Unknown/duplicate correction entry or category')
        seen.add(ident)
        if category=='missed_observation' and not ident.startswith('reference:'):raise DataError('Missed reference observation required')
        if category=='false_alarm' and not ident.startswith('agent:'):raise DataError('False alarm requires an agent claim')
        _text(item['explanation'],'correction explanation',1000);_text(item['lesson_text'],'lesson text',1000,empty=True)
        related=item['related_entry_ids'];evidence=item['evidence_ids']
        if (not isinstance(related,list) or len(related)>16 or any(not isinstance(x,str) or x not in ids or x==ident for x in related)
            or len(related)!=len(set(related))):raise DataError('Invalid correction related entries')
        if (not isinstance(evidence,list) or len(evidence)>16 or any(not isinstance(x,str) or x not in media for x in evidence)
            or len(evidence)!=len(set(evidence))):raise DataError('Invalid correction evidence IDs')
        snapshot={}
        for eid in evidence:
            value=media[eid].get('sha256')
            if not isinstance(value,str) or not HEX.fullmatch(value):raise DataError('Correction evidence requires recorded SHA256')
            snapshot[eid]=value
        actionable=category in {'missed_observation','false_alarm','description_correction','reference_error'}
        if actionable and (not evidence or not item['lesson_text'].strip()):
            raise DataError('Proposed correction lesson needs case evidence and explicit lesson text')
        clean.append(dict(deepcopy(item),evidence_snapshot=snapshot))
        if actionable and bundle['partition']!='locked_holdout':
            lessons.append({'entry_id':ident,'text':item['lesson_text'],'evidence_snapshot':snapshot,
                'status':'HUMAN_DECLARED_CANDIDATE_EXTERNAL_REVIEW_PENDING','training_approved':False})
    if seen!=ids:raise DataError('Every reference and agent entry requires an explicit correction decision')
    result={'schema_version':1,'case_id':document['project_id'],'partition':bundle['partition'],
        'reference_bundle_sha256':bundle['bundle_sha256'],'comparison_sha256':comparison['comparison_sha256'],
        'reviewer_id':reviewer_id,'reviewer_credentials_authenticated':False,'decisions':clean,'lesson_candidates':lessons,
        'source_and_evidence_custody_checked':True,'holdout_learning_excluded':bundle['partition']=='locked_holdout',
        'status':'CORRECTIONS_CAPTURED_NOT_ACTIVATED','prompt_modified':False,'weights_modified':False,
        'training_approved':False,'customer_release_allowed':False}
    result['correction_sha256']=digest(result)
    return result


def _worker():
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(10,10))
    from pypdf import PdfReader
    from io import BytesIO
    raw=sys.stdin.buffer.read(MAX_SOURCE_BYTES+1)
    if not 1<=len(raw)<=MAX_SOURCE_BYTES:raise DataError('PDF worker source size limit exceeded')
    reader=PdfReader(BytesIO(raw),strict=True)
    if reader.is_encrypted or not 1<=len(reader.pages)<=MAX_PAGES:raise DataError('Unsupported encrypted/page-limited PDF')
    pages=[];total=0
    for page in reader.pages:
        text=page.extract_text() or '';total+=len(text)
        if total>MAX_TEXT:raise DataError('PDF text limit exceeded')
        pages.append({'text':text,'has_raster_images':bool(page.images.keys())})
    print(json.dumps(pages))


if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='_pdf-worker':_worker()
    else:
        from .report_learning_cli import main
        main()
