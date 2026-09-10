"""Bounded native-PDF addition/removal gate; existing-path comparator is untouched.

A source-reviewed plan, not candidate geometry, is the expected authority. This
checks exact native changes, all final path/style operations, deletion deltas,
actual final renders, and fixed same-status stroke limits. Source truth and plan
provenance additionally require independent review before release.
"""
from __future__ import annotations
import sys
from shared_junction_contract import inspect_pairs, SCHEMA as PAIR_SCHEMA, module_sha256 as pair_module_sha256
import argparse
import hashlib
import json
import math
import numbers
import re
from pathlib import Path

import fitz
import numpy as np
from shapely.geometry import LineString, box
from shapely.ops import unary_union
import validate_stroke_style as stroke
from topology_masks import source_mask_parts

STYLE_LIMITS = {'median_width_delta_px':1.25, 'maximum_color_delta_rgb':18.0,
                'edge_softness_delta_px':0.85, 'texture_delta':2.5,
                'unexpected_status_pixel_count':0}
# Fixed PDF decimal-serialization allowance, far below the 2px repair limit.
FINAL_GEOMETRY_EPSILON_PT = .01


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    data=json.loads(Path(path).read_text())
    if not isinstance(data,dict):raise ValueError('JSON root must be an object')
    return data


def require(value,message):
    if not value:raise ValueError(message)


def evidence_file(record,tag):
    require(isinstance(record,dict),f'{tag} must be an evidence record')
    path=Path(record.get('path',''))
    require(path.is_file() and sha(path)==record.get('sha256'),f'{tag} file/hash mismatch')
    return path


def native_tokens(block):
    require(isinstance(block,str),'Native operations must be ASCII strings')
    require(block.isascii(),'Native operations must be ASCII')
    values=block.split()
    allowed={'m','l','c','v','y','h','re','S','s','n','cm','q','Q'}
    for token in values:
        if token not in allowed:
            require(bool(re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)',token)),f'Native patch contains prohibited non-path/style operator: {token}')
    # Preserve graphics-state transforms exactly; no color/width/cap operators allowed.
    context=[]
    for i,token in enumerate(values):
        if token=='cm':
            require(i>=6,'Malformed native cm operator')
            context.append(tuple(values[i-6:i+1]))
        elif token in ('q','Q'):context.append((token,))
    return context


def primitive_points(item):
    op=item[0]
    if op=='l':return [tuple(item[1]),tuple(item[2])]
    if op=='c':
        p=np.asarray([tuple(v) for v in item[1:5]],dtype=float)
        return [tuple((1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]) for t in np.linspace(0,1,33)]
    if op=='re':
        r=item[1];return [(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1),(r.x0,r.y0)]
    if op=='qu':
        q=item[1];return [tuple(q.ul),tuple(q.ur),tuple(q.lr),tuple(q.ll),tuple(q.ul)]
    raise ValueError(f'Unsupported native drawing primitive: {op}')


def linework(page):
    lines=[]
    for drawing in page.get_drawings():
        if drawing.get('color') is None:continue
        for item in drawing['items']:
            pts=primitive_points(item)
            if len(set(pts))>1:lines.append(LineString(pts))
    return unary_union(lines)


def drawing_record(drawing,scale=1.0,dx=0.0,dy=0.0):
    items=[]
    for item in drawing['items']:
        pts=primitive_points(item)
        items.append((item[0],[(x*scale+dx,y*scale+dy) for x,y in pts]))
    style={key:drawing.get(key) for key in ('type','color','fill','lineCap','lineJoin','dashes','closePath','even_odd','stroke_opacity','fill_opacity')}
    style['width']=None if drawing.get('width') is None else drawing['width']*scale
    return {'items':items,'style':style}


def near_value(a,b,epsilon):
    if isinstance(a,(tuple,list)) and isinstance(b,(tuple,list)):
        return len(a)==len(b) and all(near_value(x,y,epsilon) for x,y in zip(a,b))
    if isinstance(a,numbers.Real) and isinstance(b,numbers.Real):return abs(a-b)<=epsilon
    return a==b


def drawing_equal(a,b,epsilon=FINAL_GEOMETRY_EPSILON_PT):
    if len(a['items'])!=len(b['items']):return False
    for key in a['style']:
        tol=epsilon if key=='width' else 1e-6
        if not near_value(a['style'][key],b['style'].get(key),tol):return False
    return all(x[0]==y[0] and near_value(x[1],y[1],epsilon) for x,y in zip(a['items'],b['items']))


def compare_all_drawings(expected,actual,epsilon=FINAL_GEOMETRY_EPSILON_PT):
    left=[drawing_record(d) for d in expected.get_drawings()]
    right=[drawing_record(d) for d in actual.get_drawings()]
    require(len(left)==len(right),'Unexpected addition/deletion of final native drawing operations')
    require(all(drawing_equal(a,b,epsilon) for a,b in zip(left,right)),'Actual native path geometry/style/order differs from independently planned expected PDF')
    return len(left)


def source_stream(doc,page_index):
    streams=doc[page_index].get_contents()
    require(len(streams)==1,'Bounded native gate requires one content stream on source page; normalize before locking/hash if necessary')
    return streams[0],doc.xref_stream(streams[0])


def find_form(doc,page_index,stream):
    matches=sorted({xref for xref,_,_,_ in doc.get_page_xobjects(page_index) if doc.xref_stream(xref)==stream})
    require(len(matches)==1,'Final PDF must contain exactly one unchanged full source-map Form stream')
    return matches[0]


def source_view_wrappers(doc, page_index, stream):
    """Return every imported source invocation's literal clip and transform."""
    records=[]
    for xref, _, parent, _ in doc.get_page_xobjects(page_index):
        if doc.xref_stream(xref) != stream:
            continue
        require(parent > 0, 'Source view must have an explicit imported wrapper')
        record={}
        for key in ('BBox','Matrix'):
            kind,value=doc.xref_get_key(parent,key)
            require(kind=='array', 'Source view wrapper requires '+key)
            record[key]=[float(x) for x in value.strip('[]').split()]
        records.append(record)
    return records


def view_region(parts, view, shape, guard=1):
    clip=view['clip_source'];clipped=[]
    for part in parts:
        rect=[max(part[0],clip[0]),max(part[1],clip[1]),min(part[2],clip[2]),min(part[3],clip[3])]
        if rect[0]<rect[2] and rect[1]<rect[3]:clipped.append(rect)
    return mapped_parts(clipped,view['scale'],view['translate_x'],view['translate_y'],shape,guard)


def pixels(page):
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
    return np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3].astype(np.int16)


def mapped_box(rect,scale,dx,dy,shape,guard=0):
    require(isinstance(rect,list) and len(rect)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in rect),'Mask/reference bounds must be four finite numbers')
    require(rect[0]<rect[2] and rect[1]<rect[3],'Mask/reference bounds must be ordered')
    x0=math.floor(2*(rect[0]*scale+dx))-guard;y0=math.floor(2*(rect[1]*scale+dy))-guard
    x1=math.ceil(2*(rect[2]*scale+dx))+guard;y1=math.ceil(2*(rect[3]*scale+dy))+guard
    return stroke.box_mask(shape,(x0,y0,x1-x0,y1-y0))


def mapped_parts(parts,scale,dx,dy,shape,guard=1):
    region=np.zeros(shape,dtype=bool)
    for part in parts:
        region|=mapped_box(part,scale,dx,dy,shape,guard)
    return region


def preserve_probe_optional_content(source, destination):
    """Bind imported OCG default visibility; reject ambiguous/unknown bindings.

    Probe contains only this source. Reopen destination after calling: MuPDF may
    cache visibility when show_pdf_page first imports the Form.
    """
    states = {}
    for info in source.get_ocgs().values():
        name = info['name']
        require(name not in states or states[name] == info['on'],
                'Ambiguous source OCG visibility: ' + name)
        states[name] = info['on']
    groups, on, off = [], [], []
    for xref in range(1, destination.xref_length()):
        if destination.xref_get_key(xref, 'Type') != ('name', '/OCG'):
            continue
        name = destination.xref_get_key(xref, 'Name')[1]
        require(name in states, 'Imported probe OCG lacks source visibility: ' + name)
        groups.append(xref)
        (on if states[name] else off).append(xref)
    if groups:
        refs = lambda seq: ' '.join(f'{xref} 0 R' for xref in seq)
        destination.xref_set_key(destination.pdf_catalog(), 'OCProperties',
            f'<< /OCGs [{refs(groups)}] /D << /ON [{refs(on)}] /OFF [{refs(off)}] /Order [{refs(groups)}] >> >>')
    return {'source_visibility_by_name': states, 'on': on, 'off': off}


def verify(plan_path,base_source,patched_source,baseline_final,final_pdf,evidence_dir=None):
    plan=load(plan_path)
    require(plan.get('schema_version')=='native-topology-patch-1','Unsupported topology plan version')
    require(plan.get('source_class') in ('legacy_update_candidate','locked_new_drawing'),'Only classified legacy or explicitly authorized locked-source changes qualify')
    authority=plan.get('correction_authority',{})
    require(authority.get('authorized') is True and bool(authority.get('evidence')),'Missing existing correction authority evidence')
    if plan['source_class']=='locked_new_drawing':require(authority.get('explicit_locked_edit_authorized') is True,'Locked-source topology needs explicit scoped edit authority')
    origin=plan.get('plan_origin',{})
    evidence_file(origin,'predeclared plan origin')
    require(origin.get('predates_candidate') is True and bool(origin.get('evidence')),'Require retained evidence that source-backed plan predates candidate; never derive expected paths from candidate')
    review=plan.get('independent_plan_review',{})
    for key in ('independent','source_geometry_verified','not_candidate_derived'):
        require(review.get(key) is True,f'Independent plan review requires {key}')
    require(bool(review.get('evidence')),'Independent plan/source review evidence is required')
    sources=plan.get('source_evidence')
    require(isinstance(sources,list) and bool(sources),'Retained source evidence is required')
    for record in sources:
        evidence_file(record,'topology source evidence')
        require(bool(record.get('url')) and bool(record.get('feature_ids')) and bool(record.get('evidence')),'Source evidence must identify URL/features and supported topology')
    require(sha(base_source)==plan.get('base_source_sha256'),'Immutable base source hash mismatch')
    require(sha(baseline_final)==plan.get('baseline_final_sha256'),'Predeclared original-geometry final-layout baseline hash mismatch')
    assignment=plan.get('original_assignment',{})
    assignment_path=evidence_file(assignment,'original assignment')
    source_page=plan.get('source_page_index');final_page=plan.get('final_page_index',0)
    require(type(source_page) is int and source_page>=0 and type(final_page) is int and final_page>=0,'Page indices must be nonnegative integers')
    original=fitz.open(assignment_path);base=fitz.open(base_source);patched=fitz.open(patched_source)
    expected=fitz.open(stream=Path(base_source).read_bytes(),filetype='pdf')
    baseline=fitz.open(baseline_final);actual=fitz.open(final_pdf)
    expected_final=fitz.open(stream=Path(baseline_final).read_bytes(),filetype='pdf')
    require(len(base)==len(patched),'Patched source page count changed')
    require(source_page<len(base) and final_page<len(baseline) and final_page<len(actual),'Page index out of bounds')
    assignment_page=assignment.get('page_index',source_page)
    compare_all_drawings(original[assignment_page],base[source_page],epsilon=1e-6)
    def image_identity(page):
        return [{k:v for k,v in item.items() if k in ('bbox','transform','width','height','colorspace','bpc','digest')} for item in page.get_image_info(hashes=True)]
    require(image_identity(original[assignment_page])==image_identity(base[source_page]),'Original-to-textfree-base visible image content/placement changed')
    xref,raw=source_stream(base,source_page)
    final_form=find_form(baseline,final_page,raw)
    operations=plan.get('operations')
    require(isinstance(operations,list) and bool(operations),'Plan requires native addition/removal operations')
    transformed=plan.get('source_to_final',{})
    scale=transformed.get('scale');dx=transformed.get('translate_x');dy=transformed.get('translate_y')
    require(all(type(v) in (int,float) and math.isfinite(v) for v in (scale,dx,dy)) and scale>0,'Require a positive uniform source-to-final transform')
    baseline_records=[drawing_record(d) for d in baseline[final_page].get_drawings()]
    # Ask the PDF renderer to transform the immutable source. This also handles
    # renderer-specific lineJoin extraction and curve floating-point values.
    probe=fitz.open();probe_page=probe.new_page(width=baseline[final_page].rect.width,height=baseline[final_page].rect.height)
    source_rect=base[source_page].rect
    views=plan.get('source_views')
    if views is None:
        views=[{'id':'main','scale':scale,'translate_x':dx,'translate_y':dy,'clip_source':list(source_rect)}]
    else:
        require(isinstance(views,list) and bool(views),'Explicit source_views must be nonempty')
        evidence_file(plan.get('source_views_provenance',{}),'predeclared source view layout')
        require(bool(plan['source_views_provenance'].get('evidence')),'Source view provenance requires layout authority evidence')
    view_ids=set()
    for view in views:
        require(isinstance(view.get('id'),str) and view['id'] and view['id'] not in view_ids,'View IDs must be unique and nonempty');view_ids.add(view['id'])
        vs,vx,vy=[view.get(k) for k in ('scale','translate_x','translate_y')]
        require(all(type(v) in (int,float) and math.isfinite(v) for v in (vs,vx,vy)) and vs>0,'Every view requires a positive uniform transform')
        bounds=view.get('clip_source')
        require(isinstance(bounds,list) and len(bounds)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in bounds),'Every view requires an explicit finite source clip')
        clip=fitz.Rect(bounds)
        require(not clip.is_empty and source_rect.contains(clip),'View clip must be nonempty and inside source page')
        target=fitz.Rect(clip.x0*vs+vx,clip.y0*vs+vy,clip.x1*vs+vx,clip.y1*vs+vy)
        probe_page.show_pdf_page(target,base,source_page,clip=clip)
    preserve_probe_optional_content(base, probe)
    probe_bytes = probe.tobytes()
    probe.close()
    probe = fitz.open(stream=probe_bytes, filetype='pdf')
    probe_page = probe[0]
    expected_views=source_view_wrappers(probe,0,raw)
    actual_views=source_view_wrappers(baseline,final_page,raw)
    require('source_views' in plan or len(actual_views)==1,'Multiple native source views require explicit source_views transforms/clips')
    require('source_views' not in plan or (len(expected_views)==len(actual_views) and all(all(near_value(a[k],b[k],FINAL_GEOMETRY_EPSILON_PT) for k in a) for a,b in zip(expected_views,actual_views))),
            'Declared source view count/transform/clip differs from baseline')
    unmatched=list(baseline_records)
    for drawing in probe_page.get_drawings():
        wanted=drawing_record(drawing)
        matches=[i for i,d in enumerate(unmatched) if drawing_equal(wanted,d)]
        require(bool(matches),'Declared uniform transform does not match actual baseline PDF source geometry/style')
        unmatched.pop(matches[0])
    probe.close()
    before_pixels=pixels(baseline[final_page]);shape=before_pixels.shape[:2]
    masks=[];parts_by_operation=[];all_masks=np.zeros(shape,dtype=bool)
    for op in operations:
        parts=source_mask_parts(op)
        region=np.zeros(shape,dtype=bool)
        for view in views:region|=view_region(parts,view,shape,guard=1)
        # Optional exact original-bound pair policy runs after collecting unchanged member masks.
        all_masks|=region;masks.append(region);parts_by_operation.append(parts)
    pair_records=inspect_pairs(plan,operations,masks,views,shape,sys.modules[__name__])
    result_stream=raw;ids=set();op_results=[]
    for op,parts,region in zip(operations,parts_by_operation,masks):
        oid=op.get('id');kind=op.get('kind');before=op.get('before');after=op.get('after');count=op.get('expected_occurrences')
        require(isinstance(oid,str) and oid and oid not in ids,'Operation IDs must be unique and nonempty');ids.add(oid)
        require(kind in ('addition','removal'),'Only explicit native additions/removals are supported')
        require(type(count) is int and count>0,'Native occurrence count must be a positive integer')
        require(isinstance(before,str) and before and before!=after,'Native before/after operations must differ')
        require(native_tokens(before)==native_tokens(after),'Native graphics-state transforms may not change')
        b,a=before.encode('ascii'),after.encode('ascii')
        require(raw.count(b)==count and result_stream.count(b)==count,f'{oid}: exact original before-operation count mismatch/overlapping replacements')
        require(raw.count(a)==0 if a else True,f'{oid}: after operations already exist in original; ambiguous expected count')
        next_stream=result_stream.replace(b,a)
        require(next_stream.count(a)==count if a else True,f'{oid}: exact after-operation count mismatch')
        # Derive each delta by applying only this declared operation to immutable base.
        isolated=fitz.open(stream=Path(base_source).read_bytes(),filetype='pdf');isolated.update_stream(xref,raw.replace(b,a))
        before_geom=linework(base[source_page]);after_geom=linework(isolated[source_page])
        area=unary_union([box(*part) for part in parts])
        added_delta=after_geom.difference(before_geom.buffer(.001))
        removed_delta=before_geom.difference(after_geom.buffer(.001))
        added_outside=added_delta.difference(area).length
        removed_outside=removed_delta.difference(area).length
        require(added_outside==0 and removed_outside==0,
                f'{oid}: isolated native geometry changed outside declared topology correction mask union')
        added=added_delta.intersection(area).length
        removed=removed_delta.intersection(area).length
        require((added if kind=='addition' else removed)>.01,f'{oid}: declared {kind} has no verified native geometric delta')
        require((removed if kind=='addition' else added)<=.01,f'{oid}: unplanned opposite topology delta; split additions and removals explicitly')
        isolated_final=fitz.open(stream=Path(baseline_final).read_bytes(),filetype='pdf')
        isolated_final.update_stream(final_form,raw.replace(b,a))
        isolated_changed=np.any(before_pixels!=pixels(isolated_final[final_page]),axis=2)
        isolated_outside=int(np.sum(isolated_changed&~region))
        isolated_final.close()
        require(isolated_outside==0,
                f'{oid}: isolated rendered pixels changed outside declared topology correction mask union')
        result_stream=next_stream
        op_results.append({'mask_id':oid,'kind':kind,'expected_occurrences':count,'actual_occurrences':count,'added_length_source_pt':added,'removed_length_source_pt':removed,'deletion_delta_verified':True,'native_operations_verified':True,
                           'mask_source':op['mask_source'],'mask_source_parts':parts,'mask_renderer_guard_2x_px':1,
                           'isolated_delta_contained':True,'isolated_pixels_changed_outside_mask':isolated_outside,
                           'added_length_outside_mask_source_pt':added_outside,'removed_length_outside_mask_source_pt':removed_outside})
        isolated.close()
    expected.update_stream(xref,result_stream)
    _,patched_raw=source_stream(patched,source_page)
    require(patched_raw==result_stream,'Patched source contains undeclared native operation changes')
    for index in range(len(base)):
        compare_all_drawings(expected[index],patched[index],epsilon=1e-6)
        if index!=source_page:
            require(b''.join(expected.xref_stream(x) for x in expected[index].get_contents())==b''.join(patched.xref_stream(x) for x in patched[index].get_contents()),'Unrelated source page content changed')
    require(len(baseline)==len(actual)==1 and final_page==0,'Territory final and baseline must each be one front page')
    find_form(actual,final_page,result_stream)
    if 'source_views' in plan:
        final_views=source_view_wrappers(actual,final_page,result_stream)
        require(len(expected_views)==len(final_views) and all(all(near_value(a[k],b[k],FINAL_GEOMETRY_EPSILON_PT) for k in a) for a,b in zip(expected_views,final_views)),
                'Declared source view count/transform/clip differs from final PDF')
    expected_final.update_stream(final_form,result_stream)
    geometry_count=0
    for index in range(len(actual)):
        require(expected_final[index].rect==actual[index].rect,'Final page dimensions changed')
        geometry_count+=compare_all_drawings(expected_final[index],actual[index])
    # Pair-only stronger contribution/composition proof; disjoint legacy behavior is untouched.
    by_operation={o['id']:o for o in operations}
    for pair in pair_records:
        aa,bb=[by_operation[i]for i in pair['operation_ids']]
        def replace_one(stream,op):return stream.replace(op['before'].encode('ascii'),op['after'].encode('ascii'))
        require(replace_one(replace_one(raw,aa),bb)==replace_one(replace_one(raw,bb),aa),'Shared pair replacements do not commute against original stream')
        pair['ordered_composition_bytes_equal']=True;pair['member_contributions']=[]
        for oid in pair['operation_ids']:
            op=by_operation[oid];single=fitz.open(stream=Path(baseline_final).read_bytes(),filetype='pdf');single.update_stream(final_form,replace_one(raw,op))
            isolated_count=int(np.sum(np.any(before_pixels!=pixels(single[final_page]),axis=2)));single.close()
            without=raw
            for other in operations:
                if other['id']!=oid:without=replace_one(without,other)
            minus=fitz.open(stream=Path(baseline_final).read_bytes(),filetype='pdf');minus.update_stream(final_form,without)
            marginal_count=int(np.sum(np.any(pixels(minus[final_page])!=pixels(actual[final_page]),axis=2)));minus.close()
            require(isolated_count>0 and marginal_count>0,'Shared pair member is invisible or canceled in actual final')
            pair['member_contributions'].append({'operation_id':oid,'isolated_changed_pixels':isolated_count,'marginal_changed_pixels':marginal_count})
    after_pixels=pixels(actual[final_page]);expected_pixels=pixels(expected_final[final_page])
    require(before_pixels.shape==after_pixels.shape,'Final render sizes differ')
    require(np.array_equal(after_pixels,expected_pixels),'Actual final render differs from source-backed expected native patch (including overlay/visibility)')
    changed=np.any(before_pixels!=after_pixels,axis=2)
    outside=int(np.sum(changed&~all_masks));require(outside==0,'Rendered pixels changed outside declared topology correction masks')
    names,colors=stroke.parse_palette({'palette':plan.get('palette')})
    bclass,bdistance=stroke.palette_assignment(before_pixels,colors);aclass,adistance=stroke.palette_assignment(after_pixels,colors)
    eclass,edistance=stroke.palette_assignment(expected_pixels,colors)
    bcore=bdistance<=stroke.DEFAULT_CORE_COLOR_TOLERANCE;acore=adistance<=stroke.DEFAULT_CORE_COLOR_TOLERANCE
    bfringe=bdistance<=stroke.DEFAULT_FRINGE_COLOR_TOLERANCE;afringe=adistance<=stroke.DEFAULT_FRINGE_COLOR_TOLERANCE
    ecore=edistance<=stroke.DEFAULT_CORE_COLOR_TOLERANCE;efringe=edistance<=stroke.DEFAULT_FRINGE_COLOR_TOLERANCE
    for op,result,region,parts in zip(operations,op_results,masks,parts_by_operation):
        for view in views:
            region=view_region(parts,view,shape,guard=1)
            if not region.any():continue
            scale,dx,dy=[view[k] for k in ('scale','translate_x','translate_y')]
            status=op.get('status');require(status in names,'Every operation needs a same-status original reference')
            index=names.index(status)
            reference=view_region([op.get('reference_box_source')],view,shape,guard=0)
            require(not np.any(reference&all_masks),'Style reference must remain outside every topology mask')
            require(not np.any(changed&reference),'Style reference was altered')
            bc=bcore&(bclass==index);bf=bfringe&(bclass==index);ac=acore&(aclass==index);af=afringe&(aclass==index)
            ec=ecore&(eclass==index);ef=efringe&(eclass==index)
            ref_pixels=before_pixels[reference&bc]
            require(len(ref_pixels)>=stroke.MINIMUM_STATUS_PIXELS,'Insufficient untouched same-status reference pixels')
            # At a removed T-branch, medial-axis width is topology, not brush width.
            # Compare actual junction paint to the independently planned expected
            # paint generated from untouched source style, and separately prove that
            # the affected native styles match adjacent original same-status paths.
            source_ref=fitz.Rect(op['reference_box_source'])
            def same_status(d):
                return d.get('color') is not None and float(np.linalg.norm(np.asarray(d['color'])*255-colors[index]))<=stroke.DEFAULT_CORE_COLOR_TOLERANCE
            def stroke_intersects(d,region):
                radius=max(float(d.get('width') or 0)/2,1e-6)
                return (d['rect']+(-radius,-radius,radius,radius)).intersects(region)
            references=[drawing_record(d)['style'] for d in base[source_page].get_drawings() if same_status(d) and stroke_intersects(d,source_ref)]
            affected=[drawing_record(d)['style'] for doc in (base,expected) for d in doc[source_page].get_drawings() if same_status(d) and any(stroke_intersects(d,fitz.Rect(part)) for part in parts)]
            require(references and affected,'Missing affected/adjacent original same-status native paths')
            require(all(any(all(near_value(style[k],ref.get(k),1e-6) for k in style) for ref in references) for style in affected),'Affected native width/color/caps/joins/opacity differ from original same-status reference styles')
            original_reference_native_width_delta_px=max(min(abs(style['width']-ref['width'])*scale*2 for ref in references) for style in affected)
            require(original_reference_native_width_delta_px<=STYLE_LIMITS['median_width_delta_px'],'Original same-status native width comparison exceeds unchanged limit')
            removed_only=op['kind']=='removal' and int(np.sum(region&ac))<stroke.MINIMUM_STATUS_PIXELS
            if removed_only:
                # Exact final==expected and explicit removal delta prove absence.
                # Compare the deleted original paint against itself and retain its
                # separately verified native/reference style identity.
                sample_image=before_pixels;expected_image=before_pixels
                sample_core=bc;expected_core=bc;sample_fringe=bf;expected_fringe=bf
            else:
                sample_image=after_pixels;expected_image=expected_pixels
                sample_core=ac;expected_core=ec;sample_fringe=af;expected_fringe=ef
            sample_pixels=sample_image[region&sample_core];planned_pixels=expected_image[region&expected_core]
            require(len(sample_pixels)>=stroke.MINIMUM_STATUS_PIXELS and len(planned_pixels)>=stroke.MINIMUM_STATUS_PIXELS,'Insufficient actual/expected same-status samples')
            metrics={
              'median_width_delta_px':stroke.finite_delta(stroke.median_stroke_width(sample_fringe,region),stroke.median_stroke_width(expected_fringe,region)),
              'maximum_color_delta_rgb':float(np.linalg.norm(np.median(sample_pixels,axis=0)-np.median(planned_pixels,axis=0))),
              'edge_softness_delta_px':stroke.finite_delta(stroke.edge_softness(sample_core,sample_fringe,region),stroke.edge_softness(expected_core,expected_fringe,region)),
              'texture_delta':stroke.finite_delta(stroke.texture_measure(sample_image,sample_core,region),stroke.texture_measure(expected_image,expected_core,region)),
              'unexpected_status_pixel_count':int(np.sum(region&((acore!=ecore)|(acore&ecore&(aclass!=eclass)))))
            }
            for key,limit in STYLE_LIMITS.items():require(math.isfinite(metrics[key]) and metrics[key]<=limit,f'{op["id"]}: same-status {key}={metrics[key]} exceeds unchanged limit {limit}')
            result.update(passed=True,status=status,style_metrics=metrics,style_limits=STYLE_LIMITS,style_reference_method='independently_planned_paint_with_original_native_style_and_adjacent_same_status_reference',original_reference_native_style_verified=True,original_reference_native_width_delta_px=original_reference_native_width_delta_px,style_sample='verified_absence_after_deletion' if removed_only else 'actual_final_vs_independently_expected_junction_paint')
            result.setdefault('per_view_style_checks',[]).append({'view_id':view['id'],'style_metrics':dict(metrics),'passed':True})
    report={'schema_version':'native-topology-report-1','status':'PASS','artifact_sha256':sha(final_pdf),'plan_sha256':sha(plan_path),'base_source_sha256':sha(base_source),'patched_source_sha256':sha(patched_source),'baseline_final_sha256':sha(baseline_final),'original_assignment_sha256':sha(assignment_path),'original_to_base_drawing_identity_verified':True,'validator_sha256':sha(__file__),'source_class':plan['source_class'],'operation_ids':sorted(ids),'native_operations_verified':True,'no_other_native_path_or_style_changes':True,'actual_final_transformed_geometry_verified':True,'expected_final_render_identical':True,'deletion_deltas_verified':True,'pixels_changed_outside_declared_masks':outside,'final_geometry_operations_compared':geometry_count,'source_to_final':transformed,'source_views':views,'source_view_wrappers_verified':('source_views' in plan),'geometry_serialization_epsilon_pt':FINAL_GEOMETRY_EPSILON_PT,'results':op_results,'independent_visual_review_required':True}
    if pair_records:report['shared_junction_review']={'schema_version':PAIR_SCHEMA,'pair_validator_sha256':pair_module_sha256(),'pairs':pair_records}
    if evidence_dir is not None:
        evidence_dir=Path(evidence_dir);evidence_dir.mkdir(parents=True,exist_ok=True)
        def recorded(path):return {'path':str(path.resolve()),'sha256':sha(path)}
        for name,doc in [('expected-source.pdf',expected),('expected-final.pdf',expected_final)]:
            path=evidence_dir/name;doc.save(path,garbage=4,deflate=True)
            report[name.removesuffix('.pdf').replace('-','_')]=recorded(path)
        normal=evidence_dir/'actual-final-1x.png'
        actual[final_page].get_pixmap(alpha=False).save(normal)
        report['actual_size_screenshot']=recorded(normal)
        captures=[]
        for i,op in enumerate(operations):
            source_bounds=op['mask_source']
            clip=fitz.Rect(source_bounds[0]*scale+dx,source_bounds[1]*scale+dy,source_bounds[2]*scale+dx,source_bounds[3]*scale+dy)+(-6,-6,6,6)
            clip=clip&actual[final_page].rect
            capture={'mask_id':op['id']}
            for label,doc in [('before',baseline),('after',actual)]:
                path=evidence_dir/f'{i+1}-{label}-4x.png'
                doc[final_page].get_pixmap(matrix=fitz.Matrix(4,4),clip=clip,alpha=False).save(path)
                capture[label+'_4x']=recorded(path)
            captures.append(capture)
        report['paired_4x_screenshots']=captures
    for doc in (original,base,patched,expected,baseline,actual,expected_final):doc.close()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('plan','base-source','patched-source','baseline-final','final-pdf','report'):
        parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    try:
        result=verify(args.plan,args.base_source,args.patched_source,args.baseline_final,args.final_pdf,args.report.parent/"evidence")
    except (ValueError,KeyError,TypeError,IndexError,OSError) as exc:
        result={'schema_version':'native-topology-report-1','status':'FAIL','error':str(exc),'results':[]}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    raise SystemExit(0 if result['status']=='PASS' else 1)
