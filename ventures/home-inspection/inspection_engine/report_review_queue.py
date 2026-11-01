"""Milestone 3: exhaustive, source-bound text triage for privately imported reports.

A text cue is a REVIEW TASK, never a defect, diagnosis, compliance finding,
verified inspector label, or training datum. All page text must be represented
by exact, nonoverlapping spans. No OCR, model/network call or report publication.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .core import DataError, SYSTEM_NAME
from .descriptors import REQUIRED_FEATURES

MAX_JSON_BYTES = 5_000_000
MAX_QUEUE_BYTES = 4_000_000
MAX_SPANS = 2500
MAX_SPAN_CHARS = 1000
MAX_MARKS = 128
CUES = ('recommend', 'further evaluation', 'repair', 'replace', 'defect', 'damage',
        'crack', 'moisture', 'leak', 'stain', 'corrosion', 'overheat', 'hazard',
        'unsafe', 'missing', 'not accessible', 'not inspected', 'suspect',
        'specialist', 'disconnected', 'loose', 'deteriorat', 'safety')
CUE_RE = re.compile(r'(?<![a-z])(?:' + '|'.join(re.escape(s) for s in CUES) + r')', re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _pages_of(bundle, registry):
    # Keep the authoritative v1.6 validators and partition/holdout registry.
    from .report_learning import validate_bundle
    from .study_registry import require_registered, validate_registry
    validate_registry(registry)
    validate_bundle(bundle)
    require_registered(bundle, registry)
    return bundle['pages']


def _spans(text: str):
    """Cover every original character exactly once, including whitespace."""
    if not isinstance(text, str):
        raise DataError('Untrusted report page has non-text content')
    # Joining/splitting by lines preserves every character, including CRLF.
    pos = 0
    out = []
    start = 0
    for line in text.splitlines(keepends=True):
        if not isinstance(line, str):
            raise DataError('Unexpected report line')
        line_pos = 0
        while line_pos < len(line):
            available = MAX_SPAN_CHARS - (pos - start)
            if available == 0:
                out.append((start, pos)); start = pos
                available = MAX_SPAN_CHARS
            n = min(available, len(line) - line_pos)
            pos += n
            line_pos += n
            if pos - start == MAX_SPAN_CHARS:
                out.append((start, pos)); start = pos
        # Split at blank lines and full stops at line ends to keep reviewer chunks usable.
        if not line.strip() and pos > start:
            out.append((start, pos)); start = pos
    if pos != len(text):
        raise DataError('Report line tokenizer lost characters')
    if pos > start:
        out.append((start, pos))
    if any(a == b or b - a > MAX_SPAN_CHARS for a, b in out):
        raise DataError('Report span is empty or exceeds length bound')
    if ''.join(text[a:b] for a, b in out) != text:
        raise DataError('Report text spans do not reconstruct source')
    return out


def build_review_queue(bundle: dict, registry: dict) -> dict:
    """Create a privacy-local task queue without synthesizing any technical facts."""
    pages = _pages_of(bundle, registry)
    spans = []
    coverage = []
    for page in pages:
        number = page['number']
        content = page['text']
        rows = _spans(content)
        if len(rows) + len(spans) > MAX_SPANS:
            raise DataError('Report exceeds full-review span limit; split into governed batches')
        for first, last in rows:
            quoted = content[first:last]
            if not quoted: raise DataError('Empty report excerpt')
            # Cues are search hints only; negations and quoted errors are NOT parsed.
            cue_terms = sorted({m.group().casefold() for m in CUE_RE.finditer(quoted)})
            spans.append({'span_id':f'P{number:04d}-C{first:06d}', 'page':number,
                          'start':first,'end':last,'text':quoted,
                          'text_sha256':hashlib.sha256(quoted.encode('utf-8')).hexdigest(),
                          'review_cues_untrusted':cue_terms, 'review_required':True})
        coverage.append({'page':number,'source_text_sha256':hashlib.sha256(content.encode()).hexdigest(),
                         'characters':len(content),'represented_characters':sum(b-a for a,b in rows),
                         'spans':len(rows),'text_available':page['text_available'],
                         'has_raster_images':page['has_raster_images'],
                         'visual_review_required':True,
                         'missing_text_requires_OCR_review':not page['text_available']})
    result = {'schema_version':1,'kind':'UNVERIFIED_REPORT_TEXT_REVIEW_QUEUE',
              'case_id':bundle['case_id'],'partition':bundle['partition'],
              'reference_bundle_sha256':bundle['bundle_sha256'],
              'registry_sha256':digest(registry),
              'page_coverage':coverage,'spans':spans,
              'all_extracted_text_represented':True,
              'report_figures_tables_layout_handwriting_reviewed':False,
              'any_defect_identified':False,'root_cause_verified':False,
              'qualified_inspector_approved':False,'human_review_required':True,
              'training_approved':False,'customer_release_allowed':False,
              'status':'TEXT_REVIEW_PENDING_HUMAN'}
    if len(json.dumps(result, ensure_ascii=True).encode()) > MAX_QUEUE_BYTES:
        raise DataError('Review queue exceeds bounded 4MB output')
    result['queue_sha256'] = digest(result)
    return result


def validate_review_queue(queue: dict, bundle: dict, registry: dict) -> dict:
    if not isinstance(queue, dict) or queue != build_review_queue(bundle, registry):
        raise DataError('Report queue is stale, incomplete, or altered')
    return queue


def draft_annotations(queue: dict, bundle: dict, registry: dict, marks: list) -> list:
    """Create existing Milestone 3 annotation format only from human choices.

    Neither this function nor a cue can decide what is a defect. The resulting
    annotations still require prepare_comparison and qualified review.
    """
    validate_review_queue(queue, bundle, registry)
    if not isinstance(marks,list) or not 1<=len(marks)<=MAX_MARKS:
        raise DataError('Requires 1-128 explicitly marked excerpts')
    sources = {x['span_id']:x for x in queue['spans']}
    seen = set()
    result = []
    for mark in marks:
        required = {'id','span_id','start','end','system','kind','feature_code',
                    'location','description'}
        if not isinstance(mark, dict) or set(mark)!=required:
            raise DataError('Human annotation field set invalid')
        ident = mark['id']
        if (not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,59}',ident)
            or ident in seen):
            raise DataError('Duplicate or invalid reviewer annotation ID')
        seen.add(ident)
        span = sources.get(mark['span_id']) if isinstance(mark['span_id'],str) else None
        if span is None:
            raise DataError('Reviewer selected missing source excerpt')
        first,last=mark['start'],mark['end']
        if (type(first) is not int or type(last) is not int or
            not 0<=first<last<=len(span['text']) or last-first>2000):
            raise DataError('Reviewer quote must be an exact bounded excerpt')
        quote=span['text'][first:last]
        if not quote.strip():raise DataError('Reviewer cannot annotate whitespace as a finding')
        system=mark['system'];kind=mark['kind'];feature=mark['feature_code']
        if (not isinstance(system,str) or system not in SYSTEM_NAME or
            kind not in ('feature','potential_concern')):
            raise DataError('Unknown annotation system or finding kind')
        if kind=='feature':
            if feature not in REQUIRED_FEATURES[system]:raise DataError('Feature code not delegated to selected system')
        elif feature is not None:
            raise DataError('Potential concern must not invent a feature code')
        for name,limit in (('location',150),('description',1000)):
            value=mark[name]
            if (not isinstance(value,str) or not value.strip() or len(value)>limit
                or any(ord(c)<32 and c not in '\r\n\t' for c in value)):
                raise DataError('Invalid manual annotation '+name)
        absolute=span['start']+first
        if bundle['pages'][span['page']-1]['text'][absolute:absolute+len(quote)]!=quote:
            raise DataError('Reference annotation does not match original page text')
        result.append({'id':ident,'system':system,'kind':kind,'feature_code':feature,
                       'location':mark['location'],'description':mark['description'],
                       'page':span['page'],'offset':absolute,'quote':quote})
    return result


def _read_json(path: Path) -> object:
    if path.is_symlink(): raise DataError('Private study JSON must not be a symlink')
    flags=os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0)
    with os.fdopen(os.open(path,flags),'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise DataError('Private study JSON must be a regular file')
        raw=stream.read(MAX_JSON_BYTES+1)
    if not 1<=len(raw)<=MAX_JSON_BYTES: raise DataError('Study JSON exceeds 5MB bound')
    return json.loads(raw.decode('utf-8'))


def _write_new(path: Path, data: object) -> None:
    raw=(json.dumps(data,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    if len(raw)>MAX_QUEUE_BYTES:raise DataError('Study output exceeds 4MB bound')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description='Private report text review; no OCR/training/model execution')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('triage','annotate'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--reference',required=True,type=Path)
        cmd.add_argument('--registry',required=True,type=Path)
        cmd.add_argument('--out',required=True,type=Path)
        if name=='annotate':
            cmd.add_argument('--queue',required=True,type=Path)
            cmd.add_argument('--marks',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        bundle=_read_json(args.reference); registry=_read_json(args.registry)
        if args.command=='triage': result=build_review_queue(bundle,registry)
        else:
            result=draft_annotations(_read_json(args.queue),bundle,registry,_read_json(args.marks))
        # Require existing private directory; never create customer-data folders in repo.
        _write_new(args.out,result)
        print(json.dumps({'status':'REVIEW_PENDING','output_created':True,
                          'record_count':len(result['spans']) if isinstance(result,dict) else len(result),
                          'training_approved':False,'customer_release_allowed':False}))
        return 0
    except (DataError,ValueError,TypeError,OSError,UnicodeError,KeyError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),
                          'training_approved':False,'customer_release_allowed':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
