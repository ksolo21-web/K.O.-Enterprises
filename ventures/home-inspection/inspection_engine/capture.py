"""Local-only evidence intake and timestamped FFmpeg video stills.

These utilities establish chain of custody; they do not interpret images.
"""
from __future__ import annotations
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from .core import DataError, PHOTO_EXTS, VIDEO_EXTS, media_inventory, safe_path, sha256, validate_project

MAX_PHOTO_BYTES = 35 * 1024 * 1024
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_DURATION_SECONDS = 45 * 60
AREA_RE = re.compile(r'^[a-z][a-z0-9_-]{1,39}$')


def run_command(cmd: list[str], timeout: int=45, with_stderr: bool=False) -> bytes | tuple[bytes,bytes]:
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise DataError('Required FFmpeg tool unavailable or timed out') from exc
    if result.returncode:
        raise DataError('Media decoder failed: ' + result.stderr.decode('utf-8', 'replace')[-350:])
    return (result.stdout, result.stderr) if with_stderr else result.stdout


def probe_video(path: Path) -> dict:
    raw=run_command(['ffprobe','-v','error','-show_entries',
                     'format=duration:stream=codec_type,width,height,avg_frame_rate','-of','json',str(path)],timeout=25)
    try:
        obj=json.loads(raw)
        duration=float(obj.get('format',{}).get('duration', 0))
        video=next(s for s in obj['streams'] if s.get('codec_type')=='video')
    except (ValueError, KeyError, TypeError, StopIteration) as exc:
        raise DataError('No decodable video stream or duration') from exc
    if not math.isfinite(duration) or duration<=0 or duration>MAX_DURATION_SECONDS:
        raise DataError('Video duration missing or exceeds 45-minute ingestion limit')
    w=int(video.get('width',0)); h=int(video.get('height',0))
    if not (16<=w<=8192 and 16<=h<=8192):
        raise DataError('Video dimensions invalid or too large')
    try:
        num,den=(int(v) for v in str(video.get('avg_frame_rate','0/0')).split('/'))
        fps=num/den if den else 0
    except (ValueError,ZeroDivisionError):fps=0
    if not 0.1<=fps<=240:fps=2.0  # conservative fallback
    return {'duration_seconds':round(duration,3),'width':w,'height':h,'fps':round(fps,4)}


def validate_image(path:Path)->dict:
    if path.stat().st_size > MAX_PHOTO_BYTES:
        raise DataError('Photo exceeds 35MB ingest limit')
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            width,height=im.size
            fmt=im.format
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise DataError('Image content not recognized') from exc
    if width<64 or height<64 or width*height>80_000_000:
        raise DataError('Image dimensions outside supported range')
    if fmt not in {'JPEG','PNG','WEBP'}:
        raise DataError('Image encoding not supported')
    return {'width':width,'height':height,'image_format':fmt}


def _next_id(document:dict, kind:str)->str:
    prefix='P' if kind=='photo' else 'V'
    existing={m['id'] for m in document['media']}
    n=1
    while f'{prefix}{n:04d}' in existing:
        n+=1
    return f'{prefix}{n:04d}'


def intake_files(document:dict,root:Path,files:list[Path],area:str, room:str='') -> list[dict]:
    """Copy original media into the private project root; no internet and no deletion.

    Mutates document only after all inputs are decoded and staged. Caller saves JSON.
    """
    root=root.resolve()
    if not AREA_RE.fullmatch(area):
        raise DataError('Area must be a lowercase underscore-delimited label')
    if not files or len(files)>40:
        raise DataError('Intake requires 1-40 media files')
    if len(room)>80:raise DataError('Room label too long')
    assets=root/'assets'; assets.mkdir(mode=0o700,exist_ok=True)
    staged=[]; entries=[]
    try:
        for src in files:
            src=Path(src).resolve(strict=True)
            if not src.is_file():raise DataError('Input must be a file')
            ext=src.suffix.lower()
            kind='photo' if ext in PHOTO_EXTS else 'video' if ext in VIDEO_EXTS else None
            if kind is None:raise DataError('Unsupported media extension')
            limit=MAX_PHOTO_BYTES if kind=='photo' else MAX_VIDEO_BYTES
            if src.stat().st_size>limit:raise DataError('Media exceeds configured size limit')
            details=validate_image(src) if kind=='photo' else probe_video(src)
            media_id=_next_id({'media': document['media']+entries}, kind)
            name=f'{media_id}_{sha256(src)[:16]}{ext}'
            dest=assets/name
            if dest.exists():raise DataError('Duplicate destination collision')
            with tempfile.NamedTemporaryFile(dir=assets, prefix='.pending_',delete=False) as handle:
                temp=Path(handle.name)
            staged.append((temp,dest))
            shutil.copyfile(src,temp)
            if sha256(temp)!=sha256(src):raise DataError('Media hash changed in transit')
            item={'id':media_id,'kind':kind,'path':dest.relative_to(root).as_posix(),
                  'area':area,'room':room,'caption':'Original submitted evidence — not yet reviewed',
                  'sha256':sha256(src),'capture':details,'source_name':src.name[:110],
                  'evidence_state':'unreviewed_original'}
            entries.append(item)
        # Move atomically only after validating every input, with no partial manifest.
        for tmp,dst in staged:os.replace(tmp,dst)
        candidate=dict(document,media=document['media']+entries)
        validate_project(candidate,root)
        document['media'].extend(entries)
        return entries
    except Exception:
        for tmp,dst in staged:
            tmp.unlink(missing_ok=True)
            dst.unlink(missing_ok=True)
        raise


def video_frames(document:dict,root:Path,video_id:str,max_frames:int=6)->list[dict]:
    """Extract evenly spaced representative stills, recording parent hash/time.

    Stills are *samples*, not an assertion that the remainder was reviewed.
    """
    if not (1<=max_frames<=12):raise DataError('Frame count must be 1-12')
    candidates=[m for m in document['media'] if m['id']==video_id]
    if len(candidates)!=1 or candidates[0]['kind']!='video':raise DataError('Unknown video media ID')
    original=candidates[0]; src=safe_path(root,original['path'])
    video_hash=sha256(src)
    if original.get('sha256') and original['sha256']!=video_hash:
        raise DataError('Video original hash mismatch')
    details=probe_video(src)
    duration=details['duration_seconds']
    last=max(0,duration - 2.0/details['fps'])
    points=([0.0] if max_frames==1 or last<0.05 else
            list(dict.fromkeys(round(last*i/(max_frames-1),3) for i in range(max_frames))))
    frame_dir=root.resolve()/'frames';frame_dir.mkdir(mode=0o700,exist_ok=True)
    frames=[]; staged=[]
    try:
        for index,second in enumerate(points):
            name=f'{video_id}_t{int(round(second*1000)):09d}_{video_hash[:8]}.jpg'
            dst=frame_dir/name
            if dst.exists():raise DataError('Frame already exists; choose a new capture batch')
            with tempfile.NamedTemporaryFile(dir=frame_dir,prefix='.frame_',suffix='.jpg',delete=False) as handle:
                tmp=Path(handle.name)
            staged.append((tmp,dst))
            _, diagnostic=run_command(['ffmpeg','-hide_banner','-loglevel','info','-nostdin',
                         '-copyts','-ss',f'{second:.3f}','-i',str(src),'-frames:v','1',
                         '-vf','showinfo,scale=w=1280:h=1280:force_original_aspect_ratio=decrease',
                         '-update','1','-q:v','3','-y',str(tmp)],timeout=45,with_stderr=True)
            validate_image(tmp)
            match=re.search(rb'pts_time:([0-9]+(?:\.[0-9]+)?)',diagnostic)
            if not match:raise DataError('Cannot determine decoded frame timestamp')
            actual_second=float(match.group(1))
            frame_id=f'{video_id}-F{index+1:02d}'
            if any(m['id']==frame_id for m in document['media']):raise DataError('Frame ID already exists')
            frames.append({'id':frame_id,'kind':'photo','path':dst.relative_to(root).as_posix(),
                           'area':original['area'],'room':original.get('room',''),
                           'caption':f'Video sample at {actual_second:.3f}s; sampled frames are not complete video coverage',
                           'derived_from_id':video_id,'timestamp_seconds':actual_second,'requested_seek_seconds':second,'original_sha256':video_hash,
                           'evidence_state':'unreviewed_derived_frame','sha256':sha256(tmp)})
        for tmp,dst in staged:os.replace(tmp,dst)
        candidate=dict(document,media=document['media']+frames)
        validate_project(candidate,root)
        document['media'].extend(frames)
        return frames
    except Exception:
        for tmp,dst in staged:
            tmp.unlink(missing_ok=True);dst.unlink(missing_ok=True)
        raise


def verify_custody(document:dict,root:Path)->list[str]:
    errors=[]; by_id={m['id']:m for m in document.get('media',[])}
    for m in document.get('media',[]):
        try:
            actual=sha256(safe_path(root,m['path']))
            if m.get('sha256') and actual!=m['sha256']:
                errors.append(m['id']+': content hash mismatch')
            if m.get('derived_from_id'):
                parent=by_id.get(m['derived_from_id'])
                if not parent or parent['kind']!='video':errors.append(m['id']+': missing source video')
                elif sha256(safe_path(root,parent['path']))!=m.get('original_sha256'):
                    errors.append(m['id']+': parent video identity mismatch')
        except (OSError,ValueError) as exc:
            errors.append(m['id']+': '+str(exc))
    # Zoom evidence is subordinate to original photos/frames and must remain intact.
    for z in document.get('zoom_views',[]):
        try:
            from .zoom import verify_zoom_record
            verify_zoom_record(z,document,root)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            errors.append(str(z.get('id','unknown zoom'))+': '+str(exc))
    return errors
