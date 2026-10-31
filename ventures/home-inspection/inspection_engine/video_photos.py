"""Persist native-resolution video frames as first-class inspection photos.

An exported still is a reproducible single moment from an original video, not
proof that the whole scene/video was inspected. Only source pixels are saved;
there is no enhancement, interpolation, AI upscale, or synthetic frame creation.
"""
from __future__ import annotations

import math
import os
import re
import tempfile
from pathlib import Path
from PIL import Image
from .capture import decode_video_frame, probe_video, validate_image, verify_custody, _next_id
from .core import DataError, safe_path, sha256, validate_project

MAX_STILLS_PER_BATCH = 20
TIMECODE = re.compile(r'^(?:(\d{1,2}):)?([0-5]?\d):([0-5]\d(?:\.\d{1,6})?)$')


def parse_timecode(value: str | float | int) -> float:
    """Accept seconds (e.g. 12.5) or mm:ss.sss / hh:mm:ss.sss."""
    if type(value) in (float, int):
        seconds=float(value)
    elif isinstance(value, str) and value.strip():
        value=value.strip()
        match=TIMECODE.fullmatch(value)
        if match:
            hours, minutes, seconds_text=match.groups()
            seconds=(int(hours or 0)*3600 + int(minutes)*60 + float(seconds_text))
        else:
            try:seconds=float(value)
            except ValueError as exc:raise DataError('Invalid timecode') from exc
    else:raise DataError('Invalid timecode')
    if not math.isfinite(seconds) or seconds<0:
        raise DataError('Timecode must be a finite nonnegative value')
    return round(seconds,6)


def _timestamp_points(duration:float, fps:float, times:list[str|int|float] | None,
                      every_seconds:float | None, limit:int) -> list[float]:
    if not 1<=limit<=MAX_STILLS_PER_BATCH:
        raise DataError('Choose 1-20 maximum photos')
    if (times is None)==(every_seconds is None):
        raise DataError('Choose exact times OR an interval (not both)')
    if times is not None:
        if not isinstance(times,list) or not 1<=len(times)<=limit:
            raise DataError('Supply between 1 and max-photos selected times')
        points=[parse_timecode(t) for t in times]
    else:
        if type(every_seconds) not in (int,float) or not math.isfinite(every_seconds) or every_seconds<=0:
            raise DataError('Interval must be positive and finite')
        if every_seconds < duration/limit:
            raise DataError('Requested interval exceeds max-photos; use a larger interval')
        count=math.ceil(duration/every_seconds)
        if count>limit:
            raise DataError('Requested interval exceeds max-photos; use a larger interval or smaller selection')
        points=[round(i*every_seconds,6) for i in range(count)]
    if len(set(points))!=len(points):
        raise DataError('Duplicate selected video timestamps')
    # Reject seeks beyond duration; ffmpeg would otherwise pick no frame or wrong frame.
    for second in points:
        if second >= duration:
            raise DataError(f'Capture time {second:g}s is outside video duration {duration:g}s')
    return points


def capture_video_photos(document:dict,root:Path,video_id:str,
                         times:list[str|int|float] | None=None,
                         every_seconds:float | None=None,
                         max_photos:int=12,
                         requested_by:str='inspector',
                         note:str='Selected evidence from original video') -> list[dict]:
    """Save full-frame lossless PNG photographs, with video and timestamp provenance.

    Each extracted still is a first-class photo record, available for normal
    photo analysis, native zoom and an editorial PDF gallery. The manifest is
    updated only if *all* outputs validate. No source video is modified.
    """
    root=root.resolve()
    if not isinstance(requested_by,str) or not re.fullmatch(r'[A-Za-z0-9][\w.\-]{0,63}',requested_by):
        raise DataError('Invalid requester identity label')
    if not isinstance(note,str) or not 1<=len(note.strip())<=140:
        raise DataError('Capture note must contain 1-140 characters')
    candidates=[m for m in document['media'] if m.get('id')==video_id]
    if len(candidates)!=1 or candidates[0]['kind']!='video':
        raise DataError('Unknown source video')
    if verify_custody(document,root):
        raise DataError('Evidence custody mismatch: cannot capture from changed source')
    video=candidates[0]
    original=safe_path(root,video['path'])
    video_hash=sha256(original)
    if video.get('sha256')!=video_hash:
        raise DataError('Original video SHA-256 does not match evidence register')
    info=probe_video(original)
    points=_timestamp_points(info['duration_seconds'], info['fps'],times,every_seconds,max_photos)
    # A specific point is only one derived still; avoid unintended duplicate capture batches.
    existing=[m for m in document['media'] if m.get('derived_from_id')==video_id
              and m.get('capture_origin')=='selected_video_still']
    if any(abs(p-float(m['requested_seek_seconds']))<0.0005 for p in points for m in existing):
        raise DataError('This source video timestamp has already been saved as a selected photo')
    output_dir=root/'video_photos'
    output_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    staged:list[tuple[Path,Path]]=[]
    records=[]
    try:
        for requested in points:
            photo_id=_next_id({'media':document['media']+records},'photo')
            name=f'{photo_id}_from_{video_id}_t{round(requested*1000):010d}_{video_hash[:12]}.png'
            dest=output_dir/name
            if dest.exists():raise DataError('Video photo destination collision')
            with tempfile.NamedTemporaryFile(dir=output_dir,suffix='.png',prefix='.pending_photo_',delete=False) as stream:
                temp=Path(stream.name)
            staged.append((temp,dest))
            # Accurate seek after input, source dimensions unchanged; PNG preserves
            # decoded source pixels losslessly. -copyts keeps showinfo source timing.
            actual=decode_video_frame(original,temp,requested,timeout=90)
            if any(abs(actual-other['timestamp_seconds'])<0.0005 for other in records+existing):
                raise DataError('Multiple selected times decode to the same source video frame')
            tolerance=max(0.15,1.1/max(info['fps'],0.1))
            if actual<0 or abs(actual-requested)>tolerance:
                raise DataError('Decoded video frame differs too far from requested time')
            image_details=validate_image(temp)
            if image_details['image_format']!='PNG' or (image_details['width'],image_details['height'])!=(info['width'],info['height']):
                raise DataError('Selected video still was resized or is not native lossless PNG')
            # The output must contain the decoded frame, not a thumbnail.
            with Image.open(temp) as image:
                if image.n_frames!=1:
                    raise DataError('Video photo must be a single still image')
            records.append({'id':photo_id,'kind':'photo',
                  'path':dest.relative_to(root).as_posix(),
                  'area':video['area'],'room':video.get('room',''),
                  'caption':f'Video still at {actual:.3f}s, selected for detailed examination; not a complete video inspection',
                  'sha256':sha256(temp),'capture':image_details,
                  'source_name':name,
                  'capture_origin':'selected_video_still',
                  'derived_from_id':video_id,'timestamp_seconds':actual,
                  'requested_seek_seconds':requested,
                  'original_sha256':video_hash,
                  'native_frame_size':[info['width'],info['height']],
                  'pixel_policy':'NATIVE_LOSSLESS_FRAME_NO_ENHANCEMENT',
                  'selected_by':requested_by,'selection_note':note.strip(),
                  'evidence_state':'unreviewed_selected_video_photo'})
        for tmp,dst in staged:os.replace(tmp,dst)
        candidate=dict(document,media=document['media']+records)
        validate_project(candidate,root)
        document['media'].extend(records)
        return records
    except Exception:
        for tmp,dest in staged:
            tmp.unlink(missing_ok=True)
            dest.unlink(missing_ok=True)
        raise


def verify_selected_photo_pixels(document:dict,root:Path,photo_id:str) -> dict:
    """Deep audit: re-decode requested source moment and compare ALL image pixels.

    This is intentionally more expensive than ordinary SHA-256 validation. It
    proves pixel correspondence in this deterministic FFmpeg environment, not
    that the video itself is authentic or that the house is defect-free.
    """
    from PIL import ImageChops
    by_id={m['id']:m for m in document.get('media',[])}
    photo=by_id.get(photo_id)
    if not photo or photo.get('capture_origin')!='selected_video_still':
        raise DataError('Unknown selected video photograph')
    parent=by_id.get(photo['derived_from_id'])
    if not parent or parent['kind']!='video':
        raise DataError('Selected photograph missing source video')
    if verify_custody(document,root):
        raise DataError('Media hashes do not match for selected photo audit')
    if photo.get('original_sha256')!=parent.get('sha256'):
        raise DataError('Photo source hash mismatch')
    src=safe_path(root,parent['path'])
    with tempfile.NamedTemporaryFile(suffix='.png',prefix='.video_photo_audit_',dir=root,delete=False) as f:
        tmp=Path(f.name)
    try:
        selected=decode_video_frame(src,tmp,photo['requested_seek_seconds'],timeout=90)
        if abs(selected-photo['timestamp_seconds'])>0.001:
            raise DataError('Selected photo timestamp does not reproduce')
        with Image.open(tmp) as expected, Image.open(safe_path(root,photo['path'])) as observed:
            if expected.size!=observed.size or ImageChops.difference(expected.convert('RGB'),observed.convert('RGB')).getbbox():
                raise DataError('Selected photo pixels do not match source video frame')
        return {'photo_id':photo_id,'source_video_id':parent['id'],
                'source_sha256':parent['sha256'],'timestamp_seconds':photo['timestamp_seconds'],
                'pixel_equal_to_source':True,'status':'PASS'}
    finally:tmp.unlink(missing_ok=True)
