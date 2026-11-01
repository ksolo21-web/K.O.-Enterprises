"""Private, reproducible PDF page-image evidence for M3 expert report study.

This renderer does NOT use OCR, classify defects, validate code or grant inspection
approval. It binds complete rendered pages to an authorized/registered reference
bundle. Page pixels remain untrusted until qualified human review. No auto-learning.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

from .core import DataError, SYSTEM_NAME
from .descriptors import REQUIRED_FEATURES
from .report_review_queue import digest, _read_json, _write_new

MAX_BATCH_PAGES = 8
MAX_PAGE_PIXELS = 3_000_000
MAX_PNG_BYTES = 8_000_000
MAX_OUTPUT_BYTES = 4_000_000
MAX_TEXT_LINES_PER_PAGE = 3500
MAX_WORD_CHARS = 300
MAX_PAGE_RANGE = 200
MAX_MANUAL_MARKS = 128
IMAGE_DPI = 105
SHA = re.compile(r'[0-9a-f]{64}\Z')


def _source(path: Path) -> bytes:
    """Read an existing PDF without following symlinks or waiting on FIFOs."""
    from .report_learning import MAX_SOURCE_BYTES
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise DataError('PDF source must be a regular file')
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if not 1 <= len(raw) <= MAX_SOURCE_BYTES or not raw.startswith(b'%PDF-'):
        raise DataError('PDF source is empty, oversized or invalid')
    return raw


def _preflight(bundle, registry, pdf_path, page_numbers):
    from .report_learning import validate_bundle
    from .study_registry import require_registered, validate_registry
    validate_registry(registry)
    validate_bundle(bundle)
    require_registered(bundle, registry)
    if bundle['source']['format'] != 'pdf':
        raise DataError('Page-image study requires the original PDF source')
    if (not isinstance(page_numbers, list) or not 1 <= len(page_numbers) <= MAX_BATCH_PAGES
        or len(set(page_numbers)) != len(page_numbers)
        or any(type(n) is not int or n < 1 or n > min(MAX_PAGE_RANGE, len(bundle['pages'])) for n in page_numbers)
        or page_numbers != sorted(page_numbers)):
        raise DataError('Render 1-8 unique, sorted, in-range pages per batch')
    raw = _source(Path(pdf_path))
    if sha256(raw).hexdigest() != bundle['source']['sha256'] or len(raw) != bundle['source']['bytes']:
        raise DataError('Original PDF does not match registered imported source bytes')
    return raw


def _pdf_to_display_bbox(box,rotation,width,height):
    """Normalize PDF bottom-left geometry to the displayed top-left raster."""
    left,bottom,right,top=box
    if rotation==0:
        points=[(left,height-top),(right,height-bottom)];display_w,display_h=width,height
    elif rotation==90:
        points=[(bottom,left),(top,right)];display_w,display_h=height,width
    elif rotation==180:
        points=[(width-right,bottom),(width-left,top)];display_w,display_h=width,height
    elif rotation==270:
        points=[(height-top,width-right),(height-bottom,width-left)];display_w,display_h=height,width
    else:raise DataError('Unsupported PDF page rotation')
    x0,y0=points[0];x1,y1=points[1]
    if not all(-.001<=v<=1.001 for v in (x0/display_w,y0/display_h,x1/display_w,y1/display_h)):
        return None
    if x0>=x1 or y0>=y1:return None
    return [round(max(0,min(x0/display_w,1)),7),round(max(0,min(y0/display_h,1)),7),
            round(max(0,min(x1/display_w,1)),7),round(max(0,min(y1/display_h,1)),7)]


def _worker(raw, page_numbers, dest: Path):
    """Child process only. Resource bounds before opening untrusted PDF bytes."""
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise DataError('pypdfium2 required for private PDF page rendering') from exc
    document=pdfium.PdfDocument(raw)
    if len(document)<max(page_numbers):
        raise DataError('Incomplete PDF cannot be rendered')
    rows=[]
    for num in page_numbers:
        page=document[num-1]
        width,height=page.get_size()  # unrotated PDF point dimensions
        rotation=page.get_rotation()
        shown_width,shown_height=(height,width) if rotation in (90,270) else (width,height)
        if not (0<shown_width<=20000 and 0<shown_height<=20000):
            raise DataError('Invalid or excessive PDF page geometry')
        expected_w=round(shown_width*IMAGE_DPI/72)
        expected_h=round(shown_height*IMAGE_DPI/72)
        if expected_w<=0 or expected_h<=0 or expected_w*expected_h>MAX_PAGE_PIXELS:
            raise DataError('Page raster would exceed pixel budget')
        bitmap=page.render(scale=IMAGE_DPI/72)
        pixels=bitmap.to_pil().convert('RGB')
        if pixels.width*pixels.height>MAX_PAGE_PIXELS:
            raise DataError('Actual PDF rendering exceeded pixel budget')
        import io
        buf=io.BytesIO();pixels.save(buf,format='PNG');encoded=buf.getvalue()
        if len(encoded)>MAX_PNG_BYTES:raise DataError('Page PNG exceeds byte limit')
        name=f'page-{num:04d}.png'
        fd=os.open(dest/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(encoded)
        # PDFium line rectangles are navigation hints, not pypdf-imported
        # extracted-text offsets, and not independent evidence of a defect.
        line_boxes=[];unmapped_lines=0
        textpage=page.get_textpage()
        nr=textpage.count_rects()
        if nr>MAX_TEXT_LINES_PER_PAGE:
            raise DataError('PDF page text rectangle count exceeds bound')
        for idx in range(nr):
            normalized=_pdf_to_display_bbox(textpage.get_rect(idx),rotation,width,height)
            if normalized is None:unmapped_lines+=1
            else:line_boxes.append(normalized)
        image_count=sum(isinstance(obj,pdfium.PdfImage) for obj in page.get_objects())
        rows.append({'page':num,'image_path':name,'sha256':sha256(encoded).hexdigest(),
            'bytes':len(encoded),'pixel_width':pixels.width,'pixel_height':pixels.height,
            'page_width_points':round(shown_width,3),'page_height_points':round(shown_height,3),
            'page_rotation_degrees':rotation,
            'raster_image_objects_reported':image_count,
            'untrusted_text_line_rectangles':line_boxes,
            'line_rectangles_unmapped_due_to_geometry':unmapped_lines,
            'renderer_text_may_differ_from_imported_offsets':True,
            'visual_analysis_completed':False,'qualified_review_required':True})
    return rows


def _bounded_worker(raw,page_numbers,staging:Path):
    request={'page_numbers':page_numbers,'source_bytes':len(raw)}
    worker_cmd=[sys.executable,'-m','inspection_engine.report_page_evidence','_render_worker',
                str(staging),json.dumps(request,separators=(',',':'))]
    try:
        response=subprocess.run(worker_cmd,input=raw,stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,timeout=40,check=False)
    except subprocess.TimeoutExpired as exc:
        raise DataError('Page renderer timed out; no review data was committed') from exc
    if response.returncode or len(response.stdout)>MAX_OUTPUT_BYTES:
        raise DataError('Bounded PDF renderer rejected source or exceeded output budget')
    try:rows=json.loads(response.stdout)
    except ValueError as exc:raise DataError('Invalid PDF renderer response') from exc
    return rows


def render_batch(bundle, registry, pdf_path:Path, out_dir:Path, page_numbers:list[int]) -> dict:
    """Render only explicitly requested pages into a NEW private directory.

    All files/manifest are written in staging; move only on successful completion.
    Existing output and any source mismatch always fail before creating it.
    """
    raw = _preflight(bundle,registry,pdf_path,page_numbers)
    out_dir=Path(out_dir)
    if out_dir.exists() or out_dir.is_symlink() or not out_dir.parent.is_dir():
        raise DataError('Output must be a new directory in existing private workspace')
    # Source checked again to catch a swap while planning. Child receives same raw bytes.
    if _source(pdf_path) != raw:
        raise DataError('Source PDF changed before rendering')
    with tempfile.TemporaryDirectory(prefix='.m3-page-',dir=out_dir.parent) as temporary:
        staging=Path(temporary)
        os.chmod(staging,0o700)
        rows=_bounded_worker(raw,page_numbers,staging)
        if (not isinstance(rows,list) or len(rows)!=len(page_numbers)
            or [x.get('page') for x in rows if isinstance(x,dict)]!=page_numbers):
            raise DataError('PDF renderer did not cover all selected pages')
        for row in rows:
            path=staging/row['image_path']
            if (not path.is_file() or path.is_symlink() or path.stat().st_size!=row['bytes']
                or sha256(path.read_bytes()).hexdigest()!=row['sha256']):
                raise DataError('Rendered page pixels failed custody validation')
        manifest={'schema_version':1,'kind':'UNVERIFIED_PDF_PAGE_EVIDENCE',
            'case_id':bundle['case_id'],'partition':bundle['partition'],
            'reference_bundle_sha256':bundle['bundle_sha256'],
            'pdf_source_sha256':bundle['source']['sha256'],
            'registry_sha256':digest(registry),'pages':rows,
            'all_requested_pages_rendered':True,'all_report_pages_reviewed':False,
            'ocr_performed':False,'visual_findings_verified':False,
            'human_review_required':True,'training_approved':False,
            'customer_release_allowed':False}
        manifest['manifest_sha256']=digest(manifest)
        encoded=json.dumps(manifest,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'
        if len(encoded)>MAX_OUTPUT_BYTES:
            raise DataError('Page evidence manifest exceeds 4MB output budget')
        fd=os.open(staging/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(encoded)
            stream.flush();os.fsync(stream.fileno())
        # TemporaryDirectory contains only files created by the child, but
        # require an exact name set and reject any unexpected entries.
        if {p.name for p in staging.iterdir()} != {'manifest.json'}|{r['image_path'] for r in rows}:
            raise DataError('Unexpected file in rendered page staging directory')
        # mkdir is exclusive: rename() could silently replace an existing
        # empty directory created in a TOCTOU race. Never overwrite it.
        os.mkdir(out_dir,0o700)
        try:
            for name in sorted(p.name for p in staging.iterdir() if p.name!='manifest.json'):
                os.rename(staging/name,out_dir/name)
            os.rename(staging/'manifest.json',out_dir/'manifest.json')
        except BaseException:
            import shutil
            shutil.rmtree(out_dir)
            raise
        return manifest


def validate_page_evidence(manifest,bundle,registry,pdf_path,root):
    """Validate source, registry and ALL rendered PNG hashes before any annotation."""
    if not isinstance(manifest,dict) or not isinstance(manifest.get('pages'),list):
        raise DataError('Invalid visual evidence manifest')
    if any(not isinstance(x,dict) or 'page' not in x for x in manifest['pages']):
        raise DataError('Invalid visual page manifest rows')
    raw=_preflight(bundle,registry,pdf_path,[x['page'] for x in manifest['pages']])
    clean=deepcopy(manifest)
    recorded=clean.pop('manifest_sha256',None)
    if recorded!=digest(clean):raise DataError('Page evidence manifest altered')
    if (manifest.get('schema_version')!=1 or manifest.get('kind')!='UNVERIFIED_PDF_PAGE_EVIDENCE'
        or manifest.get('reference_bundle_sha256')!=bundle['bundle_sha256']
        or manifest.get('pdf_source_sha256')!=sha256(raw).hexdigest()
        or manifest.get('registry_sha256')!=digest(registry)
        or manifest.get('case_id')!=bundle['case_id'] or manifest.get('partition')!=bundle['partition']
        or manifest.get('ocr_performed') is not False
        or manifest.get('visual_findings_verified') is not False
        or manifest.get('training_approved') is not False
        or manifest.get('customer_release_allowed') is not False
        or manifest.get('human_review_required') is not True):
        raise DataError('Invalid evidence scope or unauthorized promotion flag')
    root=Path(root).resolve()
    for row in manifest['pages']:
        expected=f"page-{row['page']:04d}.png"
        if row.get('image_path')!=expected or row.get('visual_analysis_completed') is not False:
            raise DataError('Page identity or review state altered')
        path=root/expected
        if path.is_symlink() or not path.is_file():raise DataError('Missing original rendered page image')
        raw_img=path.read_bytes()
        if (len(raw_img)!=row['bytes'] or sha256(raw_img).hexdigest()!=row['sha256']
            or not isinstance(row['sha256'],str) or not SHA.fullmatch(row['sha256'])):
            raise DataError('Rendered page pixels do not match review manifest')
    # Verify the PNGs are actually rendered from these PDF bytes, not forged
    # page images with freshly recomputed hashes and manifest digest.
    with tempfile.TemporaryDirectory(prefix='.m3-rerender-') as tmp:
        rebuilt = _bounded_worker(raw,[r['page'] for r in manifest['pages']],Path(tmp))
    if rebuilt != manifest['pages']:
        raise DataError('Page pixels/word geometry differ from the trusted PDF renderer')
    return manifest


def record_visual_marks(manifest,bundle,registry,pdf_path,root,marks):
    """Capture only human-DECLARED page rectangle interpretations; no diagnosis.

    Visual marks are deliberately NOT compatible with text-quote annotations:
    no fictional OCR quote or pypdf text offset may be emitted.
    """
    validate_page_evidence(manifest,bundle,registry,pdf_path,root)
    if not isinstance(marks,list) or not 1<=len(marks)<=MAX_MANUAL_MARKS:
        raise DataError('Require 1-128 explicit human page-image selections')
    pages={p['page']:p for p in manifest['pages']};ids=set();items=[]
    for mark in marks:
        required={'id','page','bbox','system','kind','feature_code','location','description','reviewer_id'}
        if not isinstance(mark,dict) or set(mark)!=required:raise DataError('Visual annotation schema invalid')
        ident=mark['id'];rid=mark['reviewer_id']
        if (not isinstance(ident,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,59}',ident)
            or ident in ids or not isinstance(rid,str) or not re.fullmatch('[A-Za-z0-9_.-]{2,80}',rid)):
            raise DataError('Invalid or repeated visual mark ID / reviewer declaration')
        ids.add(ident)
        if type(mark['page']) is not int or mark['page'] not in pages:
            raise DataError('Visual region references an unrendered page')
        bb=mark['bbox']
        if (not isinstance(bb,list) or len(bb)!=4 or any(type(x) not in (float,int) or not 0<=x<=1 for x in bb)
            or not bb[0]<bb[2] or not bb[1]<bb[3]):
            raise DataError('Visual bbox must be a valid normalized page rectangle')
        system,kind,code=mark['system'],mark['kind'],mark['feature_code']
        if system not in SYSTEM_NAME or kind not in ('feature','potential_concern'):
            raise DataError('Unknown building system or mark kind')
        if (kind=='feature' and code not in REQUIRED_FEATURES[system]) or (kind=='potential_concern' and code is not None):
            raise DataError('Feature code not supported for selected system and kind')
        for key,limit in (('location',150),('description',1000)):
            val=mark[key]
            if not isinstance(val,str) or not val.strip() or len(val)>limit or any(ord(c)<32 and c not in '\n\r\t' for c in val):
                raise DataError('Invalid visual review text')
        items.append({**deepcopy(mark),
            'source_pdf_sha256':manifest['pdf_source_sha256'],
            'source_page_png_sha256':pages[mark['page']]['sha256'],
            'reference_bundle_sha256':manifest['reference_bundle_sha256'],
            'status':'HUMAN_DECLARED_UNVERIFIED',
            'reviewer_authenticated':False,'finding_approved':False,'training_approved':False})
    record={'schema_version':1,'kind':'PENDING_HUMAN_PDF_VISUAL_MARKS',
        'case_id':bundle['case_id'],'manifest_sha256':manifest['manifest_sha256'],
        'marks':items,'independent_review_required':True,'training_approved':False,
        'customer_release_allowed':False,'not_text_quote_annotations':True}
    record['record_sha256']=digest(record)
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description='Private PDF visual page review; no OCR/model/training')
    sub=p.add_subparsers(dest='command',required=True)
    render=sub.add_parser('render')
    render.add_argument('--reference',required=True,type=Path)
    render.add_argument('--registry',required=True,type=Path)
    render.add_argument('--source-pdf',required=True,type=Path)
    render.add_argument('--pages',required=True,help='Comma-separated sorted page numbers, up to 8')
    render.add_argument('--out-dir',required=True,type=Path)
    mark=sub.add_parser('mark')
    for field in ('reference','registry','source-pdf','manifest','marks','out'):
        mark.add_argument('--'+field.replace('_','-'),required=True,type=Path)
    try:
        a=p.parse_args(argv)
        bundle=_read_json(a.reference);registry=_read_json(a.registry)
        if a.command=='render':
            numbers=[int(x) for x in a.pages.split(',')]
            result=render_batch(bundle,registry,a.source_pdf,a.out_dir,numbers)
            count=len(result['pages'])
        else:
            result=record_visual_marks(_read_json(a.manifest),bundle,registry,
                a.source_pdf,a.manifest.parent,_read_json(a.marks))
            _write_new(a.out,result);count=len(result['marks'])
        print(json.dumps({'status':'HUMAN_VISUAL_REVIEW_PENDING','count':count,
            'ocr_performed':False,'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,ValueError,TypeError,OSError,KeyError,UnicodeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'training_approved':False,
                          'customer_release_allowed':False}))
        return 2


def _worker_entry(argv):
    if len(argv)!=2:raise DataError('Invalid isolated PDF render worker request')
    target=Path(argv[0]);request=json.loads(argv[1]);pages=request['page_numbers']
    # Caller supplies the exact bounded/hash-bound source bytes via stdin.
    from .report_learning import MAX_SOURCE_BYTES
    raw=sys.stdin.buffer.read(MAX_SOURCE_BYTES+1)
    if len(raw)!=request['source_bytes'] or len(raw)>MAX_SOURCE_BYTES:raise DataError('PDF worker source length mismatch')
    rows=_worker(raw,pages,target)
    response=json.dumps(rows,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
    if len(response)>MAX_OUTPUT_BYTES:raise DataError('Page metadata response exceeds limit')
    sys.stdout.buffer.write(response)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='_render_worker':
        try:_worker_entry(sys.argv[2:])
        except Exception:raise SystemExit(2) from None
    else:raise SystemExit(main())
