"""Lossless, source-referenced native-resolution visual zoom for inspection specialists.

An arbitrary-depth request is legal while source pixels remain. Zoom NEVER implies
new information; digital enlargement/interpolation is deliberately not used.
For derived video frames, the original footage is decoded on demand, avoiding the
1280px convenience still. Model findings remain reviewer-pending.
"""
from __future__ import annotations
import math
import os
import re
import tempfile
from pathlib import Path
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError
from .core import DataError, safe_path, sha256, validate_project
from .capture import decode_video_frame, verify_custody

MAX_BATCH = 32  # per-command resource guard; commands can be repeated
MAX_TILES_PER_AXIS = 8
AGENT_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$')


def validate_bbox(bbox) -> tuple[float,float,float,float]:
    """Accept normalized bounds; origin top-left, coordinates after EXIF rotation."""
    if (not isinstance(bbox,(tuple,list)) or len(bbox)!=4
        or any(type(x) not in (float,int) or not math.isfinite(x) or not 0<=x<=1 for x in bbox)
        or bbox[0]>=bbox[2] or bbox[1]>=bbox[3]):
        raise DataError('Zoom region requires finite normalized [left,top,right,bottom]')
    return tuple(float(x) for x in bbox)


def grid_regions(region, columns:int=2, rows:int=2, overlap:float=0.15) -> list[tuple[float,float,float,float]]:
    """Overlapping multi-scale tiling; repeat on any tile to zoom further."""
    x0,y0,x1,y1=validate_bbox(region)
    if type(columns)!=int or type(rows)!=int or not 1<=columns<=MAX_TILES_PER_AXIS or not 1<=rows<=MAX_TILES_PER_AXIS:
        raise DataError('Grid must have 1-8 rows and columns')
    if columns*rows>MAX_BATCH:raise DataError('Maximum 32 tiles per request; create another batch for more')
    if type(overlap) not in (float,int) or not math.isfinite(overlap) or not 0<=overlap<0.5:
        raise DataError('Overlap must be between 0 and 0.5')
    def axis(low, high, count):
        width=(high-low)/(count-(count-1)*overlap)
        return [(low+i*width*(1-overlap), min(high,low+i*width*(1-overlap)+width)) for i in range(count)]
    return [(xlo,ylo,xhi,yhi) for ylo,yhi in axis(y0,y1,rows)
                                  for xlo,xhi in axis(x0,x1,columns)]


def _native_image(document,root:Path,media:dict):
    """Return an oriented image plus source lineage and temp path (if decoded video)."""
    temp=None
    if media.get('derived_from_id'):
        by_id={m['id']:m for m in document['media']}
        parent=by_id.get(media['derived_from_id'])
        if not parent or parent['kind']!='video':raise DataError('Zoom video parent not found')
        source=safe_path(root,parent['path'])
        if sha256(source)!=media.get('original_sha256') or sha256(source)!=parent.get('sha256'):
            raise DataError('Original video does not match stored frame provenance')
        recorded=media.get('timestamp_seconds')
        if type(recorded) not in (float,int) or not math.isfinite(recorded):
            raise DataError('Missing video frame capture time')
        with tempfile.NamedTemporaryFile(prefix='native_video_',suffix='.png',delete=False,dir=root) as f:
            temp=Path(f.name)
        try:
            # Accurate seek, native video pixels, and timestamp diagnostic.
            selection=media.get('requested_seek_seconds',recorded)
            actual=decode_video_frame(source,temp,selection,timeout=90)
            fps=max(float(parent.get('capture',{}).get('fps') or 1),0.1)
            if abs(actual-recorded)>max(0.15,1.1/fps):
                raise DataError('Decoded native frame is not the selected video sample')
            with Image.open(temp) as im:
                frame=ImageOps.exif_transpose(im).convert('RGB')
            return frame, 'original_video_native_frame',source,round(actual,6),temp
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    source=safe_path(root,media['path'])
    if media.get('sha256')!=sha256(source):raise DataError('Original image hash mismatch')
    try:
        with Image.open(source) as im:
            result=ImageOps.exif_transpose(im).convert('RGB')
        return result,'original_photo',source,None,None
    except (OSError,UnidentifiedImageError,ValueError) as exc:
        raise DataError('Original image cannot be decoded for native zoom') from exc


def create_zoom_views(document:dict,root:Path,media_id:str,regions:list,
                      requested_by:str='inspection-specialist',purpose:str='closer visual examination') -> list[dict]:
    """Create 1-32 authentic source-pixel crops and append traceable zoom records.

    Does NOT resize or infer detail. Commit to in-memory project only after every
    crop is validated; failed requests remove every newly-created crop.
    """
    root=root.resolve()
    if not AGENT_RE.fullmatch(requested_by):raise DataError('Agent ID is invalid')
    if not isinstance(purpose,str) or not (1<=len(purpose.strip())<=160):
        raise DataError('Zoom purpose must be 1-160 characters')
    if not isinstance(regions,list) or not 1<=len(regions)<=MAX_BATCH:
        raise DataError('Zoom requires 1-32 regions')
    regions=[validate_bbox(r) for r in regions]
    matching=[m for m in document['media'] if m['id']==media_id and m['kind']=='photo']
    if len(matching)!=1:raise DataError('Zoom requires an original photo or indexed video sample')
    if verify_custody(document,root):raise DataError('Evidence custody failed before zoom')
    media=matching[0]
    image=None;tmp_source=None;staged=[];out=[]
    zoom_dir=root/'zoom_views';zoom_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    try:
        image,mode,native_source,decoded_time,tmp_source=_native_image(document,root,media)
        width,height=image.size
        if not (64<=width<=30000 and 64<=height<=30000 and width*height<=80_000_000):
            raise DataError('Native zoom source dimensions are unsupported')
        existing={z['id'] for z in document.get('zoom_views',[])}
        cursor=1
        for region in regions:
            l,t,r,b=region
            # Map to native pixel boundaries. No invented pixels or upsampling.
            px=[max(0,math.floor(l*width)),max(0,math.floor(t*height)),
                min(width,math.ceil(r*width)),min(height,math.ceil(b*height))]
            if px[2]-px[0]<2 or px[3]-px[1]<2:
                raise DataError('Requested zoom region contains fewer than 2 native source pixels per axis')
            while f'Z{cursor:04d}' in existing:cursor+=1
            zid=f'Z{cursor:04d}';existing.add(zid);cursor+=1
            dest=zoom_dir/f'{zid}_{media_id}.png'
            if dest.exists():raise DataError('Zoom destination already exists')
            with tempfile.NamedTemporaryFile(dir=zoom_dir,prefix='.zoom_',suffix='.png',delete=False) as f:
                tmp=Path(f.name)
            staged.append((tmp,dest))
            crop=image.crop(tuple(px))
            crop.save(tmp,format='PNG',compress_level=3)
            cwidth,cheight=crop.size
            out.append({'id':zid,'media_id':media_id,'path':dest.relative_to(root).as_posix(),
                'sha256':sha256(tmp),'source_sha256':media['sha256'],
                'native_source_sha256':sha256(native_source),
                'source_type':mode,'source_timestamp_seconds':media.get('timestamp_seconds'),
                'decoded_timestamp_seconds':decoded_time,
                'normalized_bbox':list(region),'pixel_bbox':px,
                'native_source_size':[width,height],'crop_native_size':[cwidth,cheight],
                'linear_zoom_equivalent':round(((width*height)/(cwidth*cheight))**0.5,2),
                'requested_by':requested_by,'purpose':purpose.strip(),
                'pixel_policy':'LOSSLESS_NATIVE_CROP_NO_ENHANCEMENT',
                'review':'review_pending'})
        for tmp,dest in staged:os.replace(tmp,dest)
        candidate=dict(document,zoom_views=document.get('zoom_views',[])+out)
        validate_project(candidate,root)
        document['zoom_views']=candidate['zoom_views']
        return out
    except Exception:
        for tmp,dest in staged:
            tmp.unlink(missing_ok=True);dest.unlink(missing_ok=True)
        raise
    finally:
        if image is not None:image.close()
        if tmp_source is not None:tmp_source.unlink(missing_ok=True)


def verify_zoom_record(record:dict,document:dict,root:Path,deep:bool=False) -> None:
    media={m['id']:m for m in document['media']}.get(record.get('media_id'))
    if not media or media['kind']!='photo':raise DataError('Zoom original media missing')
    if media.get('sha256')!=record.get('source_sha256'):
        raise DataError('Zoom provenance original image hash mismatch')
    path=safe_path(root,record['path'])
    if path.suffix.lower()!='.png' or sha256(path)!=record.get('sha256'):
        raise DataError('Zoom crop SHA-256 mismatch')
    region=validate_bbox(record.get('normalized_bbox'))
    size=record.get('native_source_size');px=record.get('pixel_bbox')
    if (not isinstance(size,list) or len(size)!=2 or any(type(x)!=int or x<64 for x in size)
        or not isinstance(px,list) or len(px)!=4 or any(type(x)!=int for x in px)):
        raise DataError('Zoom geometry metadata invalid')
    width,height=size
    expected=[math.floor(region[0]*width),math.floor(region[1]*height),
              math.ceil(region[2]*width),math.ceil(region[3]*height)]
    if px!=expected or not 0<=px[0]<px[2]<=width or not 0<=px[1]<px[3]<=height:
        raise DataError('Zoom pixel location disagrees with source region')
    with Image.open(path) as img:
        if img.size!=(px[2]-px[0],px[3]-px[1]) or img.format!='PNG':
            raise DataError('Zoom image dimensions do not match recorded pixels')
    if record.get('pixel_policy')!='LOSSLESS_NATIVE_CROP_NO_ENHANCEMENT':
        raise DataError('Zoom image must declare unenhanced native crop')
    if media.get('derived_from_id'):
        parent={m['id']:m for m in document['media']}.get(media['derived_from_id'])
        if not parent or sha256(safe_path(root,parent['path']))!=record.get('native_source_sha256'):
            raise DataError('Native zoom video source identity does not match')
        if record.get('source_type')!='original_video_native_frame':
            raise DataError('Source frame must be decoded at original video resolution')
    elif record.get('source_type')!='original_photo' or record.get('native_source_sha256')!=media['sha256']:
        raise DataError('Native zoom source identity incorrect')

    if deep:
        native=None; temp=None
        try:
            native,mode,source,decoded,temp=_native_image(document,root,media)
            if native.size!=tuple(size) or sha256(source)!=record['native_source_sha256']:
                raise DataError('Deep zoom source identity/dimensions changed')
            with Image.open(path) as im:
                actual=im.convert('RGB')
                expected=native.crop(tuple(px))
                if ImageChops.difference(actual,expected).getbbox() is not None:
                    raise DataError('Zoom pixels do not actually match selected original region')
            if mode=='original_video_native_frame' and abs(decoded-record['decoded_timestamp_seconds'])>0.001:
                raise DataError('Zoom video re-decode timestamp differs from source')
        finally:
            if native is not None:native.close()
            if temp is not None:temp.unlink(missing_ok=True)


def zoom_from_predictions(document:dict,root:Path,prediction:dict,media_id:str,
                          requested_by:str='inspection-specialist',margin:float=0.12,
                          all_bbox_items:bool=False)->list[dict]:
    """Stage the agent's next close-ups from evidence-bound candidate rectangles.

    This is *suggestion-directed navigation*, not autonomous claim verification.
    The agent can repeat zoom -> analyze -> request zoom using newly returned
    full-source coordinates. Defaults to suspected concerns with visible bboxes;
    optional all_bbox_items also includes ordinary visible features.
    """
    if type(margin) not in (int,float) or not math.isfinite(margin) or not 0<=margin<=0.5:
        raise DataError('Zoom margin must be 0-0.5 of the candidate extent')
    # Reuse strict prediction/replay validation, including zoom/view provenance.
    from .vision import apply_predictions
    apply_predictions(document,root,prediction)
    regions=[]
    for result in prediction.get('results',[]):
        if result.get('media_id')!=media_id:continue
        parent_zoom=None
        if result.get('zoom_view_id'):
            parent_zoom=next(z for z in document['zoom_views'] if z['id']==result['zoom_view_id'])
        bounds=parent_zoom['normalized_bbox'] if parent_zoom else [0,0,1,1]
        for cand in result.get('proposals',[]):
            if cand.get('type')!='potential_concern' and not all_bbox_items:continue
            if cand.get('bbox') is None:continue
            l,t,r,b=validate_bbox(cand['bbox'])
            dx,dy=r-l,b-t
            region=(max(bounds[0],l-margin*dx),max(bounds[1],t-margin*dy),
                    min(bounds[2],r+margin*dx),min(bounds[3],b+margin*dy))
            if region[2]-region[0]<1e-9 or region[3]-region[1]<1e-9:
                continue
            # Repeatedly asking for an identical view is NOT an improvement.
            if (parent_zoom and all(abs(a-b)<1e-6 for a,b in zip(region,bounds))):
                continue
            if not any(all(abs(a-b)<1e-7 for a,b in zip(region,prior)) for prior in regions):
                regions.append(region)
            if len(regions)==MAX_BATCH:break
        if len(regions)==MAX_BATCH:break
    if not regions:
        raise DataError('No narrower evidence-linked candidate regions; request new source imagery rather than fabricate detail')
    return create_zoom_views(document,root,media_id,regions,requested_by,
                     'Closer visual check requested from unverified model candidate bounding box')
