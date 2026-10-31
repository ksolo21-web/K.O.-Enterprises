from __future__ import annotations
from datetime import date
from pathlib import Path
from .descriptors import REQUIRED_FEATURES, missing_features
import hashlib
import json
import re

SYSTEMS = (
    ('site', 'Site and drainage'),
    ('foundation', 'Foundation and support'),
    ('subfloor', 'Floor platform and subfloor'),
    ('framing', 'Structural framing'),
    ('exterior', 'Exterior envelope'),
    ('roof', 'Roof covering and drainage'),
    ('attic', 'Attic, insulation and ventilation'),
    ('interior', 'Interiors and stairs'),
    ('electrical', 'Electrical system'),
    ('plumbing', 'Plumbing'),
    ('water_heating', 'Water heating'),
    ('hvac', 'Heating and cooling'),
    ('crawlspace', 'Crawlspace or basement'),
)
SYSTEM_NAME = dict(SYSTEMS)
REQUIRED = {'project_id', 'property', 'media', 'observations', 'findings', 'equipment', 'limitations'}
PHOTO_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.m4v', '.webm'}
VALID_STATUS = {'observed', 'partially_observed', 'not_observed', 'unknown'}
VALID_SEVERITY = {'safety', 'further_evaluation', 'maintenance'}
VALID_REVIEW = {'review_pending', 'human_verified'}
MAX_FRAME_TIMESTAMP = 45 * 60

class DataError(ValueError):
    pass

def _check(is_ok: bool, message: str):
    if not is_ok:
        raise DataError(message)

def safe_path(root: Path, value: str) -> Path:
    _check(isinstance(value, str) and value.strip(), 'Media path missing')
    path = (root / value).resolve()
    _check(path.is_relative_to(root.resolve()), f'Unsafe media path: {value}')
    _check(path.is_file(), f'Missing media file: {value}')
    return path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1_048_576), b''):
            h.update(block)
    return h.hexdigest()

def validate_project(document: dict, root: Path, strict_files: bool = True) -> dict:
    """Validate evidence references and traceability, not inspection accuracy."""
    _check(isinstance(document, dict), 'Expected JSON object')
    _check(REQUIRED <= document.keys(), f'Missing top-level keys {sorted(REQUIRED-document.keys())}')
    _check(bool(str(document['project_id']).strip()), 'project_id required')
    p = document['property']
    _check(isinstance(p, dict) and p.get('label') and p.get('inspection_date'), 'Property label/date required')
    try:
        date.fromisoformat(p['inspection_date'])
    except (ValueError, TypeError):
        raise DataError('inspection_date must be ISO 8601 date')
    for collection in ('media', 'observations', 'findings', 'equipment', 'limitations'):
        _check(isinstance(document[collection], list), f'{collection} must be array')
    media_ids = set()
    for item in document['media']:
        _check(isinstance(item, dict) and item.get('id'), 'Media id required')
        _check(item['id'] not in media_ids, f'Duplicate media id {item["id"]}')
        media_ids.add(item['id'])
        _check(item.get('kind') in ('photo','video'), 'Media kind must be photo or video')
        _check(item.get('area'), f'Media area missing: {item["id"]}')
        if strict_files:
            path = safe_path(root, item.get('path',''))
            extensions = PHOTO_EXTS if item['kind']=='photo' else VIDEO_EXTS
            _check(path.suffix.lower() in extensions, f'Unexpected media format {path.name}')
    # Derived still frames must resolve to a real video and an exact source hash.
    by_id={m['id']:m for m in document['media']}
    for item in document['media']:
        if 'sha256' in item:
            _check(isinstance(item['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',item['sha256']) is not None,
                   'Invalid media SHA-256')
            if strict_files:
                _check(sha256(safe_path(root,item['path']))==item['sha256'], 'Evidence SHA-256 mismatch')
        if item.get('derived_from_id'):
            parent=by_id.get(item['derived_from_id'])
            _check(parent is not None and parent['kind']=='video' and item['kind']=='photo',
                   'Frame must reference an original video')
            _check(isinstance(item.get('timestamp_seconds'),(int,float))
                   and 0<=item['timestamp_seconds']<=MAX_FRAME_TIMESTAMP, 'Invalid frame timestamp')
            _check(isinstance(item.get('original_sha256'),str)
                   and re.fullmatch(r'[0-9a-f]{64}',item['original_sha256']) is not None,
                   'Missing original video hash')
            if strict_files:
                _check(sha256(safe_path(root,parent['path']))==item['original_sha256'],
                       'Derived frame no longer matches source video')
            if item.get('capture_origin')=='selected_video_still':
                _check(item.get('pixel_policy')=='NATIVE_LOSSLESS_FRAME_NO_ENHANCEMENT',
                       'Selected photo must be lossless native video pixels')
                _check(isinstance(item.get('selected_by'),str) and bool(item['selected_by']),
                       'Selected video photo must record requesting specialist')
                size=item.get('native_frame_size')
                _check(isinstance(size,list) and len(size)==2 and
                       all(type(x)==int and 16<=x<=8192 for x in size),
                       'Native source frame dimensions required')
                capture=item.get('capture',{})
                _check((capture.get('width'),capture.get('height'),capture.get('image_format'))
                       ==(size[0],size[1],'PNG'), 'Selected video photo was resized')
                _check(type(item.get('requested_seek_seconds')) in (int,float) and
                       0<=item['requested_seek_seconds']<=MAX_FRAME_TIMESTAMP,
                       'Requested source timestamp missing')
                if strict_files:
                    from PIL import Image
                    with Image.open(safe_path(root,item['path'])) as frame:
                        _check(frame.format=='PNG' and frame.size==tuple(size),
                               'Selected video photo dimensions/format changed')
    # Native-resolution zoom views are subordinate derived evidence, never replacement originals.
    zoom_ids=set()
    zoom_media={m['id']:m for m in document['media']}
    _check(isinstance(document.get('zoom_views',[]),list),'zoom_views must be array')
    for z in document.get('zoom_views',[]):
        _check(isinstance(z,dict) and isinstance(z.get('id'),str) and z['id'].startswith('Z'),
               'Invalid zoom view ID')
        _check(z['id'] not in zoom_ids,'Duplicate zoom ID')
        zoom_ids.add(z['id'])
        _check(z.get('media_id') in zoom_media and zoom_media[z['media_id']]['kind']=='photo',
               'Zoom view must reference a photo or video-derived frame')
        if strict_files:
            from .zoom import verify_zoom_record
            verify_zoom_record(z,document,root)
    _check(isinstance(document.get('coverage_reviews', {}), dict), 'coverage_reviews must be an object')
    for section in ('observations', 'findings', 'equipment', 'limitations'):
        seen = set()
        for item in document[section]:
            _check(isinstance(item,dict) and item.get('id'), f'{section} id required')
            _check(item['id'] not in seen, f'Duplicate {section} id')
            seen.add(item['id'])
            _check(item.get('system') in SYSTEM_NAME, f'Unknown system {item.get("system")}')
            _check(isinstance(item.get('evidence_ids',[]),list), 'evidence_ids must be array')
            for media_id in item.get('evidence_ids',[]):
                _check(media_id in media_ids, f'Untraceable media reference {media_id}')
            _check(isinstance(item.get('zoom_view_ids',[]),list),'zoom_view_ids must be an array')
            for zoom_id in item.get('zoom_view_ids',[]):
                _check(zoom_id in zoom_ids, f'Untraceable zoom reference {zoom_id}')
                original=next(z['media_id'] for z in document['zoom_views'] if z['id']==zoom_id)
                _check(original in item.get('evidence_ids',[]),
                       'Zoom-linked finding must also cite the actual original media')
            if section == 'observations':
                _check(item.get('status') in VALID_STATUS, 'Invalid observation status')
                _check(isinstance(item.get('feature'), str) and bool(item['feature'].strip()), 'feature required')
                _check(item.get('review') in VALID_REVIEW, 'Observation must have review state')
                _check(not item.get('feature_code') or item['feature_code'] in REQUIRED_FEATURES[item['system']], 'Feature code not in system checklist')
                _check(item['status'] not in {'observed','partially_observed'} or bool(item['evidence_ids']) or item.get('recorded_by') == 'inspector', 'Observed feature needs evidence or inspector attribution')
            if section == 'findings':
                _check(item.get('severity') in VALID_SEVERITY, 'Invalid finding severity')
                _check(item.get('review') in VALID_REVIEW, 'Finding must have review state')
                _check(bool(item.get('condition')) and bool(item.get('recommendation')), 'Finding needs condition and specialist referral')
                _check(bool(item.get('evidence_ids')) or item.get('recorded_by') == 'inspector', 'Finding needs evidence or inspector attribution')
    return document

def media_inventory(document: dict, root: Path) -> list[dict]:
    return [dict(item, sha256=sha256(safe_path(root, item['path']))) for item in document['media']]

def detect_mode(document: dict) -> str:
    kinds = {item['kind'] for item in document['media']}
    return 'mixed' if kinds == {'photo','video'} else ('photos' if kinds=={'photo'} else ('videos' if kinds=={'video'} else 'no media'))

def coverage(document: dict) -> list[dict]:
    """A media area is NOT automatically a verified inspection."""
    out=[]
    for system,label in SYSTEMS:
        observations=[o for o in document['observations'] if o['system']==system]
        visible=[o for o in observations if o['status']=='observed']
        partial=[o for o in observations if o['status']=='partially_observed']
        unknown=[o for o in observations if o['status'] in ('not_observed','unknown')]
        # A single clear view cannot establish full-system coverage.
        # Full coverage requires a signed, system-scoped human attestation.
        attestation = document.get('coverage_reviews', {}).get(system, {})
        missing = missing_features(document,system)
        complete = (bool(visible) and not partial and not unknown and not missing
                    and attestation.get('status') == 'complete'
                    and bool(attestation.get('qualified_reviewer'))
                    and bool(attestation.get('reviewed_at')))
        if complete: status='observed'
        elif visible or partial: status='partial'
        else: status='not verified'
        out.append({'system':system,'title':label,'status':status,'count':len(observations), 'missing_features':missing,'open':status!='observed'})
    return out

def blockers(document: dict) -> list[str]:
    b=[]
    if document.get('adjudication_queue') is not None or document.get('agent_workflow') or 'coverage_work_orders' in document or any(
        item.get('model_proposal') for section in ('observations','findings') for item in document[section]):
        from .adjudication import build_queue,validate_record
        current=build_queue(document)
        review=document.get('adjudication',{})
        if current['entries']:
            try:held=validate_record(document,review)
            except (DataError,KeyError,TypeError,ValueError):
                b.append('Q03 adjudication of the current observation ledger required')
            else:
                if held:
                    b.append('Q03 duplicate, conflict or evidence holds require resolution')
    from .coverage_workflow import report_holds
    b.extend(report_holds(document))
    for item in coverage(document):
        if item['open']:
            b.append(f"{item['title']}: visual coverage or system description not verified")
    for section in ('observations','findings'):
        for item in document[section]:
            if item['review']!='human_verified':
                b.append(f'{section[:-1].capitalize()} {item["id"]}: independent human review required')
    if not document['property'].get('qualified_reviewer'):
        b.append('Qualified release reviewer not assigned')
    if not document['media']:
        b.append('No photo or video evidence uploaded')
    return b

def record_status(document: dict) -> str:
    return 'INTERNAL DEMONSTRATION - NOT FOR CLIENT RELEASE' if document['property'].get('synthetic',False) else ('HOLD - REVIEW INCOMPLETE' if blockers(document) else 'READY FOR HUMAN SIGN-OFF')

def load_project(filename: Path, strict_files=True) -> dict:
    root=filename.resolve().parent
    return validate_project(json.loads(filename.read_text(encoding='utf-8')), root, strict_files)
