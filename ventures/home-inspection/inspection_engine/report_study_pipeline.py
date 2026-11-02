"""Complete local preparation and declared report mapping; no network or learning.

Uses an already imported, registered PDF and never changes the shared registry.
Failed builds remove their new output only. Existing files are never overwritten.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import html
import json
import os
from pathlib import Path
import shutil

from .core import DataError
from .report_review_queue import build_review_queue, digest, _read_json, _write_new
from .report_page_evidence import render_batch, _source
from .report_ocr_review import ocr_review_batch
from .report_layout_navigation import build_layout_index
from .report_document_coverage import plan_document, audit_document
from .report_study_viewer import build_study_viewer
from .report_understanding import capture_report_mapping, validate_report_mapping, milestone_readiness


def _new_directory(path):
    path=Path(path)
    if (path.exists() or path.is_symlink() or not path.parent.is_dir()
            or any(p.is_symlink() for p in path.absolute().parents)):
        raise DataError('Output must be new under an existing private directory without symlink ancestors')
    os.mkdir(path,0o700)
    return path


def _snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def prepare_study(bundle,registry,pdf_path,out_dir,*,ocr=False,batch_size=8):
    if type(ocr) is not bool or type(batch_size) is not int or not 1<=batch_size<=8:
        raise DataError('Explicit boolean OCR and 1-8 page batches required')
    plan=plan_document(bundle,registry)
    queue=build_review_queue(bundle,registry)
    if hashlib.sha256(_source(Path(pdf_path))).hexdigest()!=bundle['source']['sha256']:
        raise DataError('Original PDF changed before study preparation')
    pages=[p['number'] for p in bundle['pages']]
    if (len(pages)+batch_size-1)//batch_size>25:raise DataError('Preparation exceeds 25 render batches')
    root=_new_directory(out_dir)
    try:
        for name,value in [('reference.json',bundle),('registry.json',registry),('text-queue.json',queue),('plan.json',plan)]:
            _write_new(root/name,value)
        groups=[];declarations=[];total_png=0
        for first in range(0,len(pages),batch_size):
            index=len(groups)+1;folder=root/f'render-{index:03d}'
            manifest=render_batch(bundle,registry,pdf_path,folder,pages[first:first+batch_size])
            total_png+=sum((folder/p['image_path']).stat().st_size for p in manifest['pages'])
            if total_png>96_000_000:raise DataError('Study page assets exceed 96MB')
            record=ocr_review_batch(manifest,bundle,registry,pdf_path,folder,pages=pages[first:first+batch_size]) if ocr else None
            layout=build_layout_index(manifest,bundle,registry,pdf_path,folder,queue,ocr_record=record)
            _write_new(root/f'layout-{index:03d}.json',layout)
            group={'manifest':manifest,'layout':layout,'render_dir':folder}
            paths={'manifest':f'render-{index:03d}/manifest.json','layout':f'layout-{index:03d}.json','render_dir':f'render-{index:03d}'}
            if record is not None:
                _write_new(root/f'ocr-{index:03d}.json',record);group['ocr_record']=record
                paths['ocr_record']=f'ocr-{index:03d}.json'
            groups.append(group);declarations.append(paths)
        audit=audit_document(bundle,registry,queue,pdf_path,
            [{'manifest':g['manifest'],'render_dir':g['render_dir']} for g in groups],
            ocr_records=[g['ocr_record'] for g in groups if 'ocr_record' in g])
        _write_new(root/'audit.json',audit);_write_new(root/'batches.json',declarations)
        template={'reviewer_id':'UNASSIGNED','coverage':[{'page':p,'status':'unresolved','note':'Awaiting source-page review'} for p in pages],
            'sections':[],'tables':[],'figures':[],'findings':[],'relations':[]}
        _write_new(root/'mapping-template.json',template)
        viewer=build_study_viewer(bundle,registry,queue,pdf_path,batches=groups,out_dir=root/'viewer')
        if hashlib.sha256(_source(Path(pdf_path))).hexdigest()!=bundle['source']['sha256']:
            raise DataError('Original PDF changed during preparation')
        receipt={'schema_version':1,'kind':'M3_PRIVATE_STUDY_PREPARATION_V7','case_id':bundle['case_id'],
            'reference_bundle_sha256':bundle['bundle_sha256'],'registry_sha256':digest(registry),
            'source_pdf_sha256':bundle['source']['sha256'],'ocr_requested':ocr,'rendered_pages':pages,
            'viewer_receipt_sha256':viewer['receipt_sha256'],'files':_snapshot(root),
            'missing_ocr_for_textless_pages':audit['missing_ocr_for_textless_pages'],
            'training_approved':False,'customer_release_allowed':False,'full_milestone_3_complete':False,
            'status':'ALL_PAGES_PREPARED_PROFESSIONAL_REVIEW_PENDING'}
        receipt['preparation_sha256']=digest(receipt);_write_new(root/'preparation.json',receipt)
        return receipt
    except BaseException:
        shutil.rmtree(root)
        raise


def load_prepared(root,bundle,registry):
    """Check every private file hash and bind source/registry before using paths."""
    root=Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.absolute().parents):raise DataError('Study directory symlink rejected')
    receipt=_read_json(root/'preparation.json');clean=deepcopy(receipt);sha=clean.pop('preparation_sha256',None)
    if (sha!=digest(clean) or receipt.get('kind')!='M3_PRIVATE_STUDY_PREPARATION_V7'
            or receipt.get('reference_bundle_sha256')!=bundle['bundle_sha256']
            or receipt.get('registry_sha256')!=digest(registry)
            or any(receipt.get(k) is not False for k in ('training_approved','customer_release_allowed','full_milestone_3_complete'))):
        raise DataError('Study receipt stale or altered')
    files=receipt.get('files')
    if not isinstance(files,dict) or not 1<=len(files)<=1000:raise DataError('Invalid prepared file inventory')
    for name,expected in files.items():
        path=Path(name)
        if path.is_absolute() or not path.parts or any(x in ('.','..') for x in path.parts):raise DataError('Unsafe prepared path')
        target=root/path
        if target.is_symlink() or any(p.is_symlink() for p in target.absolute().parents):raise DataError('Prepared asset symlink rejected')
        if not target.is_file() or target.stat().st_size>9_000_000:raise DataError('Prepared file missing or oversized')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise DataError('Prepared file changed')
    groups=[]
    rows=_read_json(root/'batches.json')
    if not isinstance(rows,list) or not 1<=len(rows)<=25:raise DataError('Invalid prepared batches')
    for row in rows:
        if not isinstance(row,dict) or set(row) not in ({'manifest','layout','render_dir'},
                {'manifest','layout','render_dir','ocr_record'}):raise DataError('Invalid prepared batch fields')
        g={}
        for key,value in row.items():
            if not isinstance(value,str) or Path(value).is_absolute() or '..' in Path(value).parts:
                raise DataError('Unsafe batch path')
            if key!='render_dir' and value not in files:raise DataError('Batch file absent from receipt')
            if (root/value).is_symlink() or any(p.is_symlink() for p in (root/value).absolute().parents):
                raise DataError('Prepared batch directory symlink rejected')
            g[key]=root/value if key=='render_dir' else _read_json(root/value)
        groups.append(g)
    return receipt,_read_json(root/'text-queue.json'),groups


def mapping_html(mapping,readiness):
    safe=lambda x:html.escape(str(x),quote=True)
    def anchor_text(anchor):
        if anchor['kind']=='pdf_text':return anchor['quote']
        if anchor['kind']=='ocr_words':return ' '.join(w['text_untrusted'] for w in anchor['source_words_untrusted'])+' [untrusted OCR]'
        return 'Selected original image region '+str(anchor['bbox'])
    def evidence(anchors):
        return '<ul>'+''.join('<li><a href="source-viewer/index.html#page-'+str(a['page'])+'">Source page '+str(a['page'])+'</a>: '+safe(anchor_text(a))+'</li>' for a in anchors)+'</ul>'
    content=[]
    for section in mapping['sections']:
        content.append('<article><h2>'+safe(section['title'])+'</h2>'+evidence(section['anchors'])+'</article>')
    for table in mapping['tables']:
        rows=[]
        for row in table['rows']:
            cells=[];position=1
            for c in sorted(row['cells'],key=lambda c:c['column']):
                while position<c['column']:
                    cells.append('<td><small>Unassigned column '+str(position)+'</small></td>');position+=1
                cells.append('<td colspan="'+str(c['column_span'])+'"><small>Declared '+safe(c['role'])+' · column '+str(c['column'])+'</small>'+evidence(c['anchors'])+'</td>')
                position+=c['column_span']
            while position<=table['column_count']:
                cells.append('<td><small>Unassigned column '+str(position)+'</small></td>');position+=1
            rows.append('<tr>'+''.join(cells)+'</tr>')
        # This presentation follows declared cells; ragged gaps stay explicit.
        content.append('<article><h2>Declared table '+safe(table['id'])+'</h2><p>Unverified rows/cell roles; empty positions are not inferred.</p><div class="scroll"><table>'+''.join(rows)+'</table></div><p>Unassigned columns by row: '+safe({r['id']:r['unassigned_columns'] for r in table['rows']})+'</p></article>')
    for figure in mapping['figures']:
        content.append('<article><h2>Declared '+safe(figure['kind'])+' '+safe(figure['id'])+'</h2>'+evidence([figure['region']]+figure['caption_anchors'])+'</article>')
    for finding in mapping['findings']:
        content.append('<article><h2>'+safe(finding['id'])+' · '+safe(finding['system'])+'</h2><p>'+safe(finding['description'])+'</p><p>'+safe(finding['location'])+'</p>'+evidence(finding['anchors'])+'</article>')
    for relation in mapping['relations']:
        content.append('<article><h2>Declared '+safe(relation['kind'])+'</h2><p>'+safe(relation['from_finding'])+' → '+safe(relation['to_finding'])+': '+safe(relation['reason'])+'</p><p>Records remain separate; relationship unverified.</p>'+evidence(relation['anchors'])+'</article>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">'
        '<title>Private report structure review</title><style>body{font:16px/1.5 system-ui;background:#111620;color:#e8edf6;max-width:1000px;margin:auto;padding:20px;overflow-wrap:anywhere}article,details{background:#192230;border:1px solid #52667f;border-radius:10px;padding:16px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:bold}summary:focus,a:focus{outline:3px solid #efbd65}.notice{border-left:5px solid #efbd65;padding:12px}small{color:#bbc7d8}a{color:#a6d3ff}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}td{min-width:140px;border:1px solid #52667f;padding:10px}td ul{padding-left:18px}</style></head><body>'
        '<h1>Report structure and evidence review</h1><p class="notice">HUMAN-DECLARED — UNVERIFIED. No professional authentication, learning activation or customer release.</p>'
        '<p>Case: '+safe(mapping['case_id'])+'</p><article><h2>Original Milestone 3 acceptance</h2><ul>'
        +''.join('<li>'+safe(b)+'</li>' for b in readiness['blockers'])+'</ul></article>'+''.join(content)
        +''.join('<details><summary>'+safe(key.title())+' ('+str(len(mapping[key]))+')</summary><pre>'
            +safe(json.dumps(mapping[key],indent=2,ensure_ascii=False))+'</pre></details>'
            for key in ('coverage','sections','tables','figures','findings','relations'))+'</body></html>')


def record_mapping(bundle,registry,pdf_path,study_dir,declarations,out_dir):
    receipt,queue,groups=load_prepared(study_dir,bundle,registry)
    mapping=capture_report_mapping(bundle,registry,queue,pdf_path,groups,declarations)
    validate_report_mapping(mapping,bundle,registry,queue,pdf_path,groups)
    readiness=milestone_readiness(mapping)
    markup=mapping_html(mapping,readiness).encode()
    if len(markup)>9_000_000:raise DataError('Mapping HTML exceeds bound')
    root=_new_directory(out_dir)
    try:
        # Rebuild presentation from source; unsigned hashes alone cannot make
        # externally edited HTML safe. Never copy active imported markup.
        canonical=build_study_viewer(bundle,registry,queue,pdf_path,batches=groups,out_dir=root/'source-viewer')
        expected_viewer={str(Path(name).relative_to('viewer')):sha
            for name,sha in receipt['files'].items() if name.startswith('viewer/')}
        if (canonical['receipt_sha256']!=receipt.get('viewer_receipt_sha256')
                or _snapshot(root/'source-viewer')!=expected_viewer):
            raise DataError('Prepared viewer differs from source-reconstructed presentation; prepare a new study')
        _write_new(root/'mapping.json',mapping);_write_new(root/'readiness.json',readiness)
        fd=os.open(root/'index.html',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(markup);stream.flush();os.fsync(stream.fileno())
        if hashlib.sha256(_source(Path(pdf_path))).hexdigest()!=bundle['source']['sha256']:
            raise DataError('Original PDF changed during mapping export')
        final={'preparation_sha256':receipt['preparation_sha256'],'mapping_sha256':mapping['mapping_sha256'],
            'files':_snapshot(root),'training_approved':False,'customer_release_allowed':False}
        _write_new(root/'receipt.json',final)
        return mapping,readiness
    except BaseException:
        shutil.rmtree(root)
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('prepare','map'):
        q=sub.add_parser(name)
        for key in ('reference','registry','source-pdf','out-dir'):q.add_argument('--'+key,type=Path,required=True)
        if name=='prepare':q.add_argument('--ocr',action='store_true');q.add_argument('--batch-size',type=int,default=8)
        else:q.add_argument('--study-dir',type=Path,required=True);q.add_argument('--declarations',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        b=_read_json(a.reference);r=_read_json(a.registry)
        if a.command=='prepare':
            result=prepare_study(b,r,a.source_pdf,a.out_dir,ocr=a.ocr,batch_size=a.batch_size)
            answer={'status':result['status'],'rendered_pages':len(result['rendered_pages'])}
        else:
            m,g=record_mapping(b,r,a.source_pdf,a.study_dir,_read_json(a.declarations),a.out_dir)
            answer={'status':m['status'],'acceptance_blockers':g['blockers']}
        print(json.dumps(dict(answer,training_approved=False,customer_release_allowed=False,full_milestone_3_complete=False)))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        # Do not echo exception text: unknown identifiers may contain source text.
        print(json.dumps({'status':'BLOCKED','error_type':type(exc).__name__,
            'training_approved':False,'customer_release_allowed':False,'full_milestone_3_complete':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
