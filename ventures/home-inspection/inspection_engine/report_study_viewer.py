"""M3 v5: offline, private, read-only report-study HTML navigation.

Never creates a web server, executable script, inferred defect, lesson, or release.
All PDF/PNG/OCR receipts are verified against their local sources before copying.
Original report text remains private and is HTML-escaped, never active markup.
"""
from __future__ import annotations
from copy import deepcopy
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
import hashlib

from .core import DataError
from .report_review_queue import digest,validate_review_queue,_read_json
from .report_layout_navigation import validate_layout_index
from .report_reading_order import build_reading_order,validate_reading_order
from .report_page_evidence import _source

MAX_BATCHES=25
MAX_HTML_BYTES=9_000_000
MAX_ASSET_BYTES=8_000_000


def _safe(value):
    return html.escape(str(value),quote=True)


def _checked_png(path,expected):
    path=Path(path)
    if path.is_symlink():raise DataError('Page asset symlink rejected')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    with os.fdopen(os.open(path,flags),'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise DataError('Page asset not a regular file')
        raw=stream.read(MAX_ASSET_BYTES+1)
    if len(raw)>MAX_ASSET_BYTES or hashlib.sha256(raw).hexdigest()!=expected:
        raise DataError('Page asset changed or exceeds size limit')
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise DataError('Unrecognized page PNG')
    return raw


def _box_overlay(box,kind):
    if not isinstance(box,list) or len(box)!=4 or any(type(x) not in (float,int) or not 0<=x<=1 for x in box) or not box[0]<box[2] or not box[1]<box[3]:
        raise DataError('Invalid visual overlay region')
    label={'image':'Embedded raster object; photograph/diagram type not established',
           'text':'PDF text navigation rectangle; reading order not established'}[kind]
    style=f'left:{box[0]*100:.3f}%;top:{box[1]*100:.3f}%;width:{(box[2]-box[0])*100:.3f}%;height:{(box[3]-box[1])*100:.3f}%'
    return f'<span class="overlay {kind}" title="{_safe(label)}" style="{style}"></span>'


def _page_section(page,layout,reading,spans,asset_name):
    number=page['page'];body=[]
    body.append(f'<section id="page-{number}" class="page">')
    body.append(f'<h2>Page {number} <small>Unverified review</small></h2>')
    body.append(f'<p class="meta">PNG SHA-256: <code>{_safe(page["sha256"])}</code></p>')
    body.append('<div class="page-image" aria-label="Original rendered PDF page with navigation overlays">')
    body.append(f'<img loading="lazy" src="assets/{asset_name}" alt="Rendered source PDF page {number}, not a verified defect finding">')
    for box in layout.get('raster_object_boxes_unverified',[]):body.append(_box_overlay(box,'image'))
    for box in layout.get('pdf_text_line_boxes_untrusted',[]):body.append(_box_overlay(box,'text'))
    body.append('</div>')
    body.append('<p class="meta">Outlines are locator hints only. Amber = embedded raster image; blue = PDF text region. No photographic interpretation.</p>')
    body.append('<details><summary>Candidate OCR reading order — inspect against page</summary>')
    body.append(f'<p>Method: {_safe(reading["mode"])}. Columns, tables, and reading order require manual verification.</p>')
    if reading['candidate_lines']:
        body.append('<ol class="reading">')
        for line in reading['candidate_lines']:
            body.append(f'<li><span class="meta">{_safe(line["column_candidate"])} · {_safe(line["source_row_id"])}</span> {_safe(line["untrusted_reading_text"])}</li>')
        body.append('</ol>')
    else:body.append('<p>No verified OCR reading order exists for this page.</p>')
    body.append('<p class="meta">Warnings: '+_safe(', '.join(reading['ambiguous_layout_reasons']))+'</p></details>')
    body.append('<details><summary>Original extracted PDF text — exact source chunks</summary>')
    if spans:
        for span in spans:
            body.append(f'<div class="excerpt"><small>{_safe(span["span_id"])}; source text, not an authenticated finding</small><pre>{_safe(span["text"])}</pre></div>')
    else:body.append('<p>No extractable PDF text; OCR and visual review required.</p>')
    body.append('</details></section>')
    return '\n'.join(body)


def render_html(case_id,pages,missing,sections):
    counts=f'{len(pages)} of {len(pages)+len(missing)} pages have verified rendered image assets'
    status='PARTIAL_SOURCE_COVERAGE' if missing else 'COMPLETE_RENDER_COVERAGE_NOT_REVIEWED'
    navigation=' '.join(f'<a href="#page-{p}">{p}</a>' for p in pages)
    gaps=', '.join(map(str,missing)) if missing else 'none'
    css='''
:root{font-family:system-ui,-apple-system,sans-serif;color:#e8edf6;background:#111620}
body{margin:0 auto;padding:24px;max-width:1040px;line-height:1.55}
h1{font-size:1.8rem}h2{margin-bottom:0}small,.meta{color:#bbc7d8;font-size:.83rem;overflow-wrap:anywhere}
header,.page{padding:18px;border:1px solid #46566d;border-radius:14px;margin:18px 0;background:#192230}
a{color:#a6d3ff;margin-right:8px}a:focus,summary:focus{outline:3px solid #f4c675}
.notice{border-left:5px solid #efbd65;padding:12px 16px;background:#2b2a2c}
.page-image{display:inline-block;position:relative;margin:12px 0;max-width:100%;vertical-align:top;overflow:hidden}
.page-image img{display:block;max-width:100%;height:auto;box-shadow:0 2px 20px #080a0e}
.overlay{position:absolute;pointer-events:none;box-sizing:border-box;border:2px dashed #68aff0;background:rgba(86,175,250,.06)}
.overlay.image{border-color:#ecac54;background:rgba(236,172,84,.1)}
details{margin:14px 0;padding:12px;background:#232d3c;border-radius:8px}
summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;font-size:.94rem}
.excerpt{border-left:2px solid #52667f;padding:6px 10px;margin:6px 0;background:#192230}
code{font-size:.8em;word-break:break-all}ol.reading{padding-left:26px}li{margin:5px 0}
@media print{body{background:white;color:black}header,.page{background:white!important;color:black!important}details,.notice{display:block;background:#f1f4f8!important;color:#171f2b!important}small,.meta{color:#445166!important}a{color:#175e9a!important}}
'''
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' file: data:; style-src \'unsafe-inline\'; form-action \'none\'; connect-src \'none\'; base-uri \'none\'">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Private M3 report study</title>'
        f'<style>{css}</style></head><body><header><h1>Private report-study viewer</h1>'
        f'<p>Case: {_safe(case_id)}</p><div class="notice"><strong>UNVERIFIED — NOT A CUSTOMER REPORT.</strong> '
        'OCR, PDF text navigation, column ordering and image outlines are review aids only. '
        'No defect, component identity or safety conclusion is established. No online synchronization.</div>'
        f'<p>Render coverage: {_safe(counts)}. Status: {_safe(status)}. Missing rendered pages: {_safe(gaps)}.</p>'
        f'<nav aria-label="Report page navigation">{navigation}</nav></header>'
        + '\n'.join(sections)
        + '<footer><p>Read-only offline artifact. Local source/evidence verification required before professional use. '
        'No report release, automatic learning or authenticated inspector signoff.</p></footer></body></html>')


def build_study_viewer(bundle,registry,text_queue,pdf_path,*,batches:list,out_dir:Path):
    """Validate every named PDF receipt; then create a new offline read-only workspace.

    batches: [{manifest,layout,ocr_record(optional),render_dir}]. 1-25 batches, max 8 pages each.
    Caller never supplies source text to the HTML as instructions; all are escaped.
    """
    from .report_learning import validate_bundle
    from .study_registry import require_registered
    validate_bundle(bundle);require_registered(bundle,registry)
    validate_review_queue(text_queue,bundle,registry)
    if bundle['source']['format']!='pdf':raise DataError('PDF viewer requires a PDF source')
    if not isinstance(batches,list) or not 1<=len(batches)<=MAX_BATCHES:
        raise DataError('Viewer requires a bounded set of render batches')
    # Revalidate the original PDF before and after building a private copy.
    if hashlib.sha256(_source(Path(pdf_path))).hexdigest()!=bundle['source']['sha256']:
        raise DataError('Source PDF changed before viewer construction')
    original_pages={x['number'] for x in bundle['pages']}
    all_pages={};assets={};all_readings={};all_layouts={}
    for group in batches:
        if not isinstance(group,dict) or set(group) not in ({'manifest','layout','render_dir'}, {'manifest','layout','render_dir','ocr_record'}):
            raise DataError('Invalid viewer render batch')
        manifest,layout=group['manifest'],group['layout'];ocr=group.get('ocr_record')
        root=Path(group['render_dir'])
        validate_layout_index(layout,manifest,bundle,registry,pdf_path,root,text_queue,ocr_record=ocr)
        reading=build_reading_order(layout,ocr)
        validate_reading_order(reading,layout,ocr)
        indexed={x['page']:x for x in layout['pages']};ordered={x['page']:x for x in reading['pages']}
        for page in manifest['pages']:
            n=page['page']
            if type(n) is not int or n not in original_pages or n in all_pages or n not in indexed or n not in ordered:
                raise DataError('PDF viewer page duplicated or outside original report')
            all_pages[n]=deepcopy(page);all_layouts[n]=deepcopy(indexed[n]);all_readings[n]=deepcopy(ordered[n])
            assets[n]=_checked_png(root/page['image_path'],page['sha256'])
    missing=sorted(original_pages-set(all_pages))
    texts={n:[] for n in all_pages}
    for span in text_queue['spans']:
        if span['page'] in texts:texts[span['page']].append(span)
    source_pages=sorted(all_pages)
    sections=[_page_section(all_pages[n],all_layouts[n],all_readings[n],texts[n],f'page-{n:04d}.png') for n in source_pages]
    page_html=render_html(bundle['case_id'],source_pages,missing,sections).encode('utf-8')
    if len(page_html)>MAX_HTML_BYTES:raise DataError('Viewer exceeds bounded output; split document')
    record={'schema_version':1,'kind':'M3_PRIVATE_OFFLINE_VIEWER_V5',
            'case_id':bundle['case_id'],'reference_bundle_sha256':bundle['bundle_sha256'],
            'source_pdf_sha256':bundle['source']['sha256'],
            'rendered_pages':source_pages,'unrendered_pages':missing,
            'all_pdf_pages_rendered':not bool(missing),'all_pages_professionally_reviewed':False,
            'html_sha256':hashlib.sha256(page_html).hexdigest(),
            'asset_sha256':{f'page-{n:04d}.png':all_pages[n]['sha256'] for n in source_pages},
            'file_url_only':True,'no_javascript_or_network':True,
            'reading_order_verified':False,'professional_approval_authenticated':False,
            'training_approved':False,'customer_release_allowed':False,
            'status':'PRIVATE_OFFLINE_REVIEW_PENDING'}
    record['receipt_sha256']=digest(record)
    encoded=(json.dumps(record,indent=2,ensure_ascii=True)+'\n').encode()
    out_dir=Path(out_dir)
    if (out_dir.exists() or out_dir.is_symlink() or not out_dir.parent.is_dir()
        or out_dir.parent.is_symlink()):raise DataError('Viewer output must be new in a private existing directory')
    os.mkdir(out_dir,0o700)
    try:
        assets_dir=out_dir/'assets';os.mkdir(assets_dir,0o700)
        def private_write(target,payload):
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream:
                stream.write(payload);stream.flush();os.fsync(stream.fileno())
        for n in source_pages:private_write(assets_dir/f'page-{n:04d}.png',assets[n])
        private_write(out_dir/'index.html',page_html)
        private_write(out_dir/'receipt.json',encoded)
        if hashlib.sha256(_source(Path(pdf_path))).hexdigest()!=bundle['source']['sha256']:
            raise DataError('Source PDF changed during viewer construction')
    except BaseException:
        shutil.rmtree(out_dir)
        raise
    return record


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description='Private, offline, read-only report-study viewer')
    for key in ('reference','registry','text-queue','source-pdf','batches','out-dir'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(argv)
    try:
        groups=_read_json(a.batches)
        if not isinstance(groups,list):raise DataError('Batch declaration must be an array')
        batches=[]
        for group in groups:
            if not isinstance(group,dict) or set(group) not in ({'manifest','layout','render_dir'},{'manifest','layout','render_dir','ocr_record'}):
                raise DataError('Batch declaration contains invalid fields')
            batches.append({'manifest':_read_json(Path(group['manifest'])),
                            'layout':_read_json(Path(group['layout'])),
                            'render_dir':Path(group['render_dir']),
                            **({'ocr_record':_read_json(Path(group['ocr_record']))} if 'ocr_record' in group else {})})
        record=build_study_viewer(_read_json(a.reference),_read_json(a.registry),_read_json(a.text_queue),a.source_pdf,
                                   batches=batches,out_dir=a.out_dir)
        print(json.dumps({'status':record['status'],'pages':len(record['rendered_pages']),
            'missing_pages':len(record['unrendered_pages']),'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'training_approved':False,'customer_release_allowed':False}))
        return 2

if __name__=='__main__':raise SystemExit(main())
