"""Data-only, one-neutral-fill preservation contract. No caller code or raster bypass.

The authority record is independently authored; it binds the immutable source plan,
registration plan, original assignment and pre-operation review. Reports never
replace direct replay against the current artifact.
"""
from pathlib import Path
from datetime import datetime
import hashlib, json, math
import fitz
import numpy as np

KIND = 'neutral_paint_knockout'
SCALES = (1, 2, 4, 8)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def bound(record):
    require(isinstance(record, dict) and set(record) == {'path', 'sha256'}, 'invalid file record')
    p = Path(record['path'])
    require(p.is_file() and sha(p) == record['sha256'], 'file identity mismatch: ' + str(p))
    return p

def load(record):
    value = json.loads(bound(record).read_text())
    require(isinstance(value, dict), 'JSON record must be object')
    return value

def numbers(values, count):
    require(isinstance(values, list) and len(values) == count and
            all(type(v) in (int, float) and math.isfinite(v) for v in values), 'invalid finite coordinates')
    return values

def clean(drawing):
    return {k: v for k, v in drawing.items() if k != 'seqno'}

def command(plan):
    """Generate the only allowed command from numeric polygon data, never raw code."""
    polygon = plan['polygon_source_y_down']
    require(isinstance(polygon, list) and 3 <= len(polygon) <= 16, 'polygon vertex count')
    mask = numbers(plan['mask_source'], 4)
    require(mask[0] < mask[2] and mask[1] < mask[3], 'empty mask')
    h = plan['source_height']
    require(type(h) in (int, float) and math.isfinite(h) and h > 0, 'source height')
    for point in polygon:
        x, y = numbers(point, 2)
        require(mask[0] <= x <= mask[2] and mask[1] <= y <= mask[3], 'polygon outside immutable mask')
    from shapely.geometry import Polygon
    poly = Polygon(polygon)
    require(poly.is_valid and poly.area > 0, 'invalid polygon')
    require(plan['neutral_cmyk'] == [0, 0, 0, 0], 'only CMYK white knockout supported')
    lines = ['q', '0 0 0 0 k']
    for i, (x, y) in enumerate(polygon):
        lines.append(f'{x:.12f} {h-y:.12f} ' + ('m' if i == 0 else 'l'))
    return ('\n'.join(lines) + '\nh\nf\nQ\n').encode('ascii')

def inserted(raw, plan):
    anchor = plan['anchor_native_bytes'].encode('ascii')
    count, occurrence = plan['anchor_occurrences'], plan['insert_after_occurrence']
    require(type(count) is int and type(occurrence) is int and 1 <= occurrence <= count and anchor, 'anchor specification')
    require(raw.count(anchor) == count, 'anchor occurrence mismatch')
    pos = 0
    for _ in range(occurrence):
        pos = raw.index(anchor, pos) + len(anchor)
    return raw[:pos] + b'\n' + command(plan) + raw[pos:]

def object_custody(before, after, xref, plan, label):
    require(len(before) == len(after) == 1, label + ' page count')
    require(before.xref_length() == after.xref_length(), label + ' object count')
    require(after.xref_stream(xref) == inserted(before.xref_stream(xref), plan), label + ' exact one fill insertion')
    for i in range(1, before.xref_length()):
        def dictionary(doc):
            return {k: doc.xref_get_key(i, k) for k in doc.xref_get_keys(i)
                    if k not in ('Length', 'Filter', 'DecodeParms')}
        require(dictionary(before) == dictionary(after), label + ' object dictionary ' + str(i))
        require(before.xref_is_stream(i) == after.xref_is_stream(i), label + ' stream type')
        if i != xref and before.xref_is_stream(i):
            require(before.xref_stream(i) == after.xref_stream(i), label + ' unrelated stream ' + str(i))
    a, b = before[0], after[0]
    require(a.rect == b.rect and a.rotation == b.rotation, label + ' page geometry')
    require(a.get_text('dict') == b.get_text('dict'), label + ' text')
    require(a.get_image_info(hashes=True) == b.get_image_info(hashes=True), label + ' images')
    require(not list(a.annots() or []) and not list(b.annots() or []), label + ' annotations unsupported')
    da, db = a.get_drawings(), b.get_drawings()
    require(len(db) == len(da) + 1, label + ' native count')
    candidates = [i for i, d in enumerate(db) if d['type'] == 'f' and d['fill'] == (1, 1, 1) and d['fill_opacity'] == 1
                  and [clean(x) for x in da] == [clean(x) for j, x in enumerate(db) if j != i]]
    require(len(candidates) == 1, label + ' original native/style/layer custody')
    return candidates[0]

def points(d):
    out = []
    for item in d['items']:
        for v in item[1:]:
            if isinstance(v, fitz.Point): out.append([v.x, v.y])
            elif isinstance(v, fitz.Rect): out.extend([[v.x0, v.y0], [v.x1, v.y1]])
            elif isinstance(v, fitz.Quad): out.extend([[q.x, q.y] for q in (v.ul, v.ur, v.ll, v.lr)])
    return np.array(out)

def actual_transform(colored, final, transform):
    scale = transform['scale']; tx, ty = numbers(transform['translation'], 2)
    require(type(scale) in (int, float) and math.isfinite(scale) and scale > 0, 'invalid uniform transform')
    last = -1
    for d in colored[0].get_drawings():
        expected = points(d) * scale + [tx, ty]
        require(expected.size > 0, 'empty colored primitive')
        matches = []
        for j, f in enumerate(final[0].get_drawings()):
            p = points(f)
            if j <= last or p.shape != expected.shape or np.max(abs(p-expected)) > .001: continue
            if [i[0] for i in d['items']] != [i[0] for i in f['items']]: continue
            if any(d.get(k) != f.get(k) for k in ('type','color','fill','lineCap','dashes','closePath','stroke_opacity','fill_opacity')): continue
            if abs(f['width'] - d['width']*scale) > .001: continue
            matches.append(j)
        require(matches, 'source-to-final actual transformed paint missing or reordered')
        last = matches[0]

def raster_outside(before, after, mask, transform, label):
    s, (tx, ty) = transform['scale'], transform['translation']
    result = []
    for z in SCALES:
        a = before[0].get_pixmap(matrix=fitz.Matrix(z,z), colorspace=fitz.csRGB, alpha=False)
        b = after[0].get_pixmap(matrix=fitz.Matrix(z,z), colorspace=fitz.csRGB, alpha=False)
        require((a.width,a.height,a.n) == (b.width,b.height,b.n), label + ' raster geometry')
        x = np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,a.n)
        y = np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,b.n)
        delta = np.any(x != y,axis=2); outside = delta.copy()
        box = [math.floor((mask[0]*s+tx)*z),math.floor((mask[1]*s+ty)*z),
               math.ceil((mask[2]*s+tx)*z),math.ceil((mask[3]*s+ty)*z)]
        require(0 <= box[0] < box[2] <= a.width and 0 <= box[1] < box[3] <= a.height, 'mask outside rendered page')
        outside[box[1]:box[3],box[0]:box[2]] = False
        result.append({'scope':label,'scale':z,'changed_pixels':int(delta.sum()),'outside_mask_pixels':int(outside.sum())})
        require(not outside.any(), label + ' outside original mask at ' + str(z))
    return result

def resource_value(value, seen=None):
    """Resolve paint resources independent of xref renumbering; reject cycles."""
    from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject
    seen = set() if seen is None else seen
    if isinstance(value, IndirectObject):
        key = (id(value.pdf),value.idnum,value.generation)
        require(key not in seen, 'cyclic paint resource unsupported')
        return resource_value(value.get_object(),seen|{key})
    if isinstance(value, DictionaryObject):
        out = {str(k):resource_value(v,seen) for k,v in value.items()
               if str(k) not in ('/Length','/Filter','/DecodeParms')}
        if hasattr(value,'get_data'): out['decoded_stream_sha256'] = hashlib.sha256(value.get_data()).hexdigest()
        return out
    if isinstance(value, ArrayObject): return [resource_value(v,seen) for v in value]
    return value

def raw_custody(plan):
    """Only text-show removal and explicit paint suppression may produce the bases."""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    a = PdfReader(bound(plan['authorities']['original'])).pages[plan['original_page_index']]
    b = PdfReader(bound(plan['authorities']['textfree'])).pages[0]
    c = PdfReader(bound(plan['authorities']['colored'])).pages[0]
    oa,ob,oc = [page.get_contents().operations for page in (a,b,c)]
    require(all(not (op == b'Tr' and args and float(args[0]) >= 4) for args,op in oa), 'text clipping source unsupported')
    require([op for op in oa if op[1] not in (b'Tj',b'TJ',b"'",b'"')] == ob,
            'original raw operations to textfree may only remove text-show operators')
    # Fonts cannot paint after removal of text-show operators. Every painting resource remains identical.
    for category in ('/ExtGState','/ColorSpace','/Pattern','/Shading','/Properties','/XObject'):
        av = a['/Resources'].get(category,{})
        bv = b['/Resources'].get(category,{})
        require(resource_value(av) == resource_value(bv), 'original/textfree paint resource '+category)
        cv = c['/Resources'].get(category,{})
        if category != '/XObject':
            require(resource_value(bv) == resource_value(cv),'textfree/colored paint resource '+category)
        else:
            bv,cv = bv.get_object() if hasattr(bv,'get_object') else bv, cv.get_object() if hasattr(cv,'get_object') else cv
            for key in bv: require(key in cv and resource_value(bv.raw_get(key)) == resource_value(cv.raw_get(key)), 'changed original colored XObject resource')
    require(len(ob) == len(oc), 'colored raw operation count')
    paints = {b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'}
    suppressed = 0
    for old,new in zip(ob,oc):
        if old == new: continue
        if old[1] in paints and new == ([],b'n'):
            suppressed += 1; continue
        require(old[1] == new[1] == b'Do' and len(old[0]) == len(new[0]) == 1,
                'colored base changes something other than neutral paint suppression')
        before = b['/Resources']['/XObject'][old[0][0]]
        after = c['/Resources']['/XObject'][new[0][0]]
        x,y = ContentStream(before,b.pdf).operations,ContentStream(after,c.pdf).operations
        require(len(x) == len(y) and all(l == r or (l[1] in paints and r == ([],b'n')) for l,r in zip(x,y)), 'suppressed form changed unrelated native operators')
        for key in ('/Matrix','/BBox','/Group','/Resources'):
            av,bv = resource_value(before.get(key)),resource_value(after.get(key))
            if key == '/Resources':
                av = {k:v for k,v in av.items() if v != {}}
                bv = {k:v for k,v in bv.items() if v != {}}
            require(av == bv, 'suppressed form resource or transform')
    return suppressed

def unaffected_paint(before, after, xref, plan, label):
    """Disable only the approved anchor stroke in proof copies; all remaining paint is exact."""
    from pypdf.generic import ContentStream, DecodedStreamObject
    anchor = plan['anchor_native_bytes'].encode('ascii')
    stream = DecodedStreamObject(); stream.set_data(anchor)
    operations = ContentStream(stream,None).operations
    allowed = {b'q',b'Q',b'cm',b'm',b'l',b'c',b'v',b'y',b'h',b're',b'S',b's'}
    require(all(op in allowed for args,op in operations) and
            sum(op in (b'S',b's') for args,op in operations) == 1,
            'anchor must contain exactly one existing stroke, no resources or other paint')
    require(anchor.endswith(b'S\nQ') or anchor.endswith(b's\nQ'), 'anchor must end with its isolated stroke')
    suppressed = anchor[:-3]+b'n\nQ'
    copies = []
    try:
        for doc in (before,after):
            isolated = fitz.open(stream=doc.tobytes(),filetype='pdf')
            raw = isolated.xref_stream(xref)
            require(raw.count(anchor) == plan['anchor_occurrences'], 'unaffected isolation anchor count')
            isolated.update_stream(xref,raw.replace(anchor,suppressed)); copies.append(isolated)
        out = []
        for z in SCALES:
            a,b = [d[0].get_pixmap(matrix=fitz.Matrix(z,z),colorspace=fitz.csRGB,alpha=False) for d in copies]
            require((a.width,a.height,a.n) == (b.width,b.height,b.n), 'unaffected raster dimensions')
            count = int(np.count_nonzero(np.frombuffer(a.samples,np.uint8) != np.frombuffer(b.samples,np.uint8)))
            out.append({'scope':label,'scale':z,'unrelated_paint_changed_channels':count})
            require(count == 0, label+' unrelated paint altered inside or outside mask at '+str(z))
        return out
    finally:
        for doc in copies: doc.close()

def source_binding(p):
    source_plan = load(p['source_authored_plan'])
    # Existing source-authored plan uses explicit fixed fields, not arbitrary JSON pointers/code.
    for key in ('mask_source','polygon_source_y_down','final_transform'):
        require(source_plan[key] == p[key], 'source-authored ' + key + ' changed')
    require(source_plan['operation']['anchor_before'] == p['anchor_native_bytes'], 'source-authored anchor changed')
    require(source_plan['operation']['anchor_occurrences'] == p['anchor_occurrences'] and source_plan['operation']['insert_after_occurrence'] == p['insert_after_occurrence'], 'source-authored insertion position')
    require(source_plan['operation']['inserted_native_bytes'].encode('ascii') == command(p), 'source-authored neutral command differs')
    for key, old in [('original','source'),('textfree','textfree_base'),('colored','native_colored_base'),('baseline_final','baseline_final')]:
        require(source_plan[old+'_sha256'] == p['authorities'][key]['sha256'], 'source-authored authority changed')

def replay(plan_record, final_path, source_after_record):
    """Always performs all native and 1/2/4/8 raster checks. No optional scales."""
    p = load(plan_record)
    require(set(p) == {'schema_version','source_authored_plan','mask_id','authorities','original_page_index','colored_original_indices','stream_xrefs','colored_stream_sha256','source_height','neutral_cmyk','mask_source','polygon_source_y_down','final_transform','anchor_native_bytes','anchor_occurrences','insert_after_occurrence'}, 'unknown or missing plan field')
    require(p['schema_version'] == 'native-neutral-knockout-plan-1', 'plan version')
    source_binding(p)
    authorities = p['authorities']
    raw_custody(p)
    docs = {k:fitz.open(bound(authorities[k])) for k in ('original','textfree','colored','baseline_final')}
    original, textfree, colored, baseline = [docs[k] for k in ('original','textfree','colored','baseline_final')]
    source = fitz.open(bound(source_after_record)); final = fitz.open(final_path)
    try:
        page = p['original_page_index']; indices = p['colored_original_indices']
        require(type(page) is int and 0 <= page < len(original), 'original page')
        require(isinstance(indices,list) and indices and all(type(i) is int for i in indices) and indices == sorted(set(indices)), 'colored source indices')
        require(len(textfree) == len(colored) == len(baseline) == 1, 'authority pages')
        require(original[page].rect == textfree[0].rect and original[page].rotation == textfree[0].rotation, 'original-to-textfree page geometry')
        require(original[page].get_image_info(hashes=True) == textfree[0].get_image_info(hashes=True), 'original-to-textfree images')
        raw = original[page].get_drawings()
        require([clean(d) for d in raw] == [clean(d) for d in textfree[0].get_drawings()], 'original-to-textfree drawing custody')
        require(not textfree[0].get_text().strip(), 'textfree has text')
        require([clean(raw[i]) for i in indices] == [clean(d) for d in colored[0].get_drawings()], 'original-to-colored custody')
        xrefs = p['stream_xrefs']
        require(all(type(xrefs[k]) is int and xrefs[k] > 0 for k in ('textfree','colored','baseline_final')), 'stream xrefs')
        require(textfree[0].get_contents() == [xrefs['textfree']] and colored[0].get_contents() == [xrefs['colored']], 'declared base stream must be actual single page content')
        raw_colored = colored.xref_stream(xrefs['colored'])
        require(raw_colored == baseline.xref_stream(xrefs['baseline_final']), 'colored stream to baseline form custody')
        require(hashlib.sha256(raw_colored).hexdigest() == p['colored_stream_sha256'], 'colored stream hash')
        require(original[page].rect.height == textfree[0].rect.height == p['source_height'], 'native y conversion source height')
        command(p)
        actual_transform(colored, baseline, p['final_transform'])
        source_fill = object_custody(textfree, source, xrefs['textfree'], p, 'source')
        final_fill = object_custody(baseline, final, xrefs['baseline_final'], p, 'final')
        comparisons = raster_outside(textfree,source,p['mask_source'],{'scale':1,'translation':[0,0]},'source')
        comparisons += raster_outside(baseline,final,p['mask_source'],p['final_transform'],'final')
        unaffected = unaffected_paint(textfree,source,xrefs['textfree'],p,'source')
        unaffected += unaffected_paint(baseline,final,xrefs['baseline_final'],p,'final')
        return {'status':'PASS','schema_version':'native-neutral-knockout-proof-1','plan_sha256':plan_record['sha256'],
                'artifact_sha256':sha(final_path),'source_after_sha256':source_after_record['sha256'],
                'source_fill_index':source_fill,'final_fill_index':final_fill,'comparisons':comparisons,'unaffected_paint':unaffected,
                'scope':'Exact one neutral fill; all original native paint and style unchanged. Full release gates still required.'}
    finally:
        for d in list(docs.values())+[source,final]: d.close()

def validate_visual_pixels(visual, plan, artifact_path):
    """Decode actual PNG pixels and compare with fresh prescribed PDF renders."""
    from PIL import Image
    full = fitz.open(artifact_path)
    before = fitz.open(bound(plan['authorities']['baseline_final']))
    try:
        scale = plan['final_transform']['scale']; tx,ty = plan['final_transform']['translation']
        x0,y0,x1,y1 = plan['mask_source']
        # Fixed eight-final-point margin; callers cannot select a different/blank crop.
        crop = fitz.Rect(x0*scale+tx-8,y0*scale+ty-8,x1*scale+tx+8,y1*scale+ty+8) & full[0].rect
        for name,document,z,clip in [('actual_size',full,1,None),('before_4x',before,4,crop),('after_4x',full,4,crop)]:
            path = bound(visual[name])
            with Image.open(path) as image:
                require(image.format == 'PNG' and image.mode == 'RGB', name+' must be an actual RGB PNG')
                image.load()
                rendered = document[0].get_pixmap(matrix=fitz.Matrix(z,z),clip=clip,colorspace=fitz.csRGB,alpha=False)
                require(image.size == (rendered.width,rendered.height), name+' screenshot dimensions differ from prescribed render')
                require(image.tobytes() == rendered.samples, name+' screenshot pixels differ from actual prescribed PDF render')
    finally:
        full.close(); before.close()

def validate_neutral_knockout(review, artifact_path, masks, original_assignment_sha256):
    """Registration gate: current files + independent source authority + fresh direct replay."""
    if not isinstance(masks,list): return ['neutral_paint_knockout: masks must be a list']
    relevant = [m for m in masks if isinstance(m,dict) and m.get('edit_kind') == KIND]
    if review is None and not relevant: return []
    try:
        require(isinstance(review,dict) and len(relevant) == 1, 'exactly one knockout mask and contract required')
        p = load(review['plan']); approval = load(review['authority']); receipt = load(review['operation_receipt'])
        source_plan = load(p['source_authored_plan'])
        require(approval['status'] == 'APPROVED_FOR_IMPLEMENTATION_ONLY' and approval['independent'] is True, 'independent plan approval required')
        require(approval['plan_sha256'] == review['plan']['sha256'] and approval['source_plan_sha256'] == p['source_authored_plan']['sha256'], 'approval must bind both immutable plans')
        require(approval['original_assignment_sha256'] == original_assignment_sha256 == p['authorities']['original']['sha256'], 'original assignment authority mismatch')
        require(approval['source_plan_preceded_operation'] is True and isinstance(approval['evidence'],str) and approval['evidence'].strip(), 'pre-operation source plan review required')
        start = datetime.fromisoformat(receipt['started_at']); approved = datetime.fromisoformat(approval['approved_at'])
        require(start.tzinfo is not None and approved.tzinfo is not None and approved <= start, 'independent approval must precede operation')
        require(receipt['authority_sha256'] == review['authority']['sha256'] and receipt['plan_sha256'] == review['plan']['sha256'], 'operation receipt authority binding')
        require(receipt['artifact_sha256'] == sha(artifact_path) and receipt['source_after_sha256'] == review['source_after']['sha256'], 'operation artifact identity')
        source_binding(p)
        m = relevant[0]; s = p['final_transform']['scale']; tx,ty = p['final_transform']['translation']; x0,y0,x1,y1 = p['mask_source']
        require(m['contains_stroke_repair'] is True and m['id'] == p['mask_id'], 'truthful paint repair mask identity')
        require(all(math.isclose(m[k],v,abs_tol=1e-9,rel_tol=0) for k,v in zip(('x','y','width','height'),(x0*s+tx,y0*s+ty,(x1-x0)*s,(y1-y0)*s))), 'project mask changed')
        proof = replay(review['plan'],artifact_path,review['source_after'])
        recorded = load(review['report'])
        require(recorded == proof, 'stored proof must equal current direct replay')
        visual = review['independent_visual_review']
        require(visual['artifact_sha256'] == sha(artifact_path) and visual['plan_sha256'] == review['plan']['sha256'], 'visual identity')
        for key in ('independent','source_plan_review_completed','actual_size_review_completed','paired_4x_review_completed','no_visible_style_mismatch'):
            require(visual.get(key) is True, 'knockout visual requires ' + key)
        require(isinstance(visual['evidence'],str) and visual['evidence'].strip(), 'visual explanation')
        validate_visual_pixels(visual,p,artifact_path)
        return []
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError,AttributeError) as e:
        return ['neutral_paint_knockout: ' + str(e)]

# Keep the pre-existing unsigned registration path byte-for-byte above.
_validate_operation_neutral_knockout = validate_neutral_knockout

def validate_delivery_wrapper(review, artifact_path, masks, original_assignment_sha256):
    """Strict operation replay first; a narrowly verified delivery envelope second."""
    try:
        require(set(review) == {'delivery_wrapper'}, 'wrapper review must contain only delivery_wrapper')
        w = review['delivery_wrapper']
        require(isinstance(w, dict) and set(w) == {'schema_version','operation_pdf','operation_review','current_pdf','independent_visual_review'}, 'wrapper fields')
        require(w['schema_version'] == 'neutral-knockout-delivery-wrapper-1', 'wrapper version')
        operation = bound(w['operation_pdf'])
        operation_review = load(w['operation_review'])
        require(set(operation_review) == {'plan','authority','operation_receipt','source_after','report','independent_visual_review'}, 'complete strict operation review required; nested wrapper prohibited')
        receipt = load(operation_review['operation_receipt'])
        require(receipt['artifact_sha256'] == w['operation_pdf']['sha256'], 'operation PDF must match existing operation receipt')
        # No stripping of current bytes, receipt rewriting or relaxed replay.
        errors = _validate_operation_neutral_knockout(operation_review, operation, masks, original_assignment_sha256)
        require(not errors, 'strict operation replay failed: ' + '; '.join(errors))
        current = bound(w['current_pdf'])
        require(current.resolve() == Path(artifact_path).resolve() and sha(artifact_path) == w['current_pdf']['sha256'], 'wrapper must bind actual current artifact path and bytes')
        from delivery_wrapper import verify_delivery
        custody = verify_delivery(operation, artifact_path)
        require(custody['operation_sha256'] == receipt['artifact_sha256'] and custody['delivery_sha256'] == sha(artifact_path), 'delivery custody artifact binding')
        visual = load(w['independent_visual_review'])
        require(visual['artifact_sha256'] == sha(artifact_path) and visual['plan_sha256'] == operation_review['plan']['sha256'], 'current delivery visual identity')
        require(visual['operation_review_sha256'] == w['operation_review']['sha256'] and visual['operation_pdf_sha256'] == receipt['artifact_sha256'], 'current visual must bind exact reviewed operation')
        for key in ('independent','source_plan_review_completed','actual_size_review_completed','paired_4x_review_completed','no_visible_style_mismatch'):
            require(visual.get(key) is True, 'current delivery visual requires ' + key)
        require(isinstance(visual['evidence'],str) and visual['evidence'].strip(), 'current delivery visual explanation')
        validate_visual_pixels(visual, load(operation_review['plan']), artifact_path)
        return []
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError,AttributeError) as e:
        return ['neutral_paint_knockout: delivery_wrapper: ' + str(e)]

def validate_neutral_knockout(review, artifact_path, masks, original_assignment_sha256):
    if isinstance(review,dict) and 'delivery_wrapper' in review:
        return validate_delivery_wrapper(review, artifact_path, masks, original_assignment_sha256)
    return _validate_operation_neutral_knockout(review, artifact_path, masks, original_assignment_sha256)
