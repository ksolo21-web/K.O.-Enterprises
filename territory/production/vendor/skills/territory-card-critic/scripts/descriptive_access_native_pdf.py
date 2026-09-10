"""Isolate native PDF text/glyph paint with original fonts, advances and transforms.

The source is never edited. The adapter changes only paint operators in a fresh
in-memory PdfReader, keeping inherited forms/resources, clipping and text state.
Selected whole text events retain their original Tj/TJ operators. Glyph isolation
splits encoded glyph codes while preserving TJ adjustments and all advances.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
import copy,io,json,hashlib
import fitz,numpy as np
from pypdf import PdfReader,PdfWriter,_cmap
from pypdf.generic import ContentStream,NumberObject,ByteStringObject,ArrayObject,NameObject,DictionaryObject,DecodedStreamObject

TEXT_SHOW={b'Tj',b'TJ',b"'",b'"'}
PATH_PAINT={b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'}
RASTER_PAINT={b'sh',b'INLINE IMAGE'}

def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def render_pdf(pdf,scale=2):
    d=fitz.open(stream=pdf,filetype='pdf') if isinstance(pdf,bytes) else fitz.open(pdf)
    p=d[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()

def render_alpha(pdf,scale=2):
    d=fitz.open(stream=pdf,filetype='pdf') if isinstance(pdf,bytes) else fitz.open(pdf)
    p=d[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=True)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,4)[:,:,3].copy()

def _raw(value):
    if isinstance(value,bytes):return bytes(value)
    return value.original_bytes

def glyph_codes(raw,font):
    """Return original encoded glyph bytes and decoded Unicode; fail unsupported CMaps."""
    enc,cmap=_cmap.get_encoding(font)
    if font.get('/Subtype')=='/Type0':
        if font.get('/Encoding') not in ('/Identity-H','/Identity-V'):
            raise ValueError('Unsupported variable-width Type0 CMap; preserve native code segmentation explicitly')
        width=2
    else:width=1
    if len(raw)%width:raise ValueError('Incomplete native encoded glyph')
    result=[]
    for k in range(0,len(raw),width):
        code=raw[k:k+width]
        if isinstance(enc,dict):mapped=enc.get(code[0],chr(code[0]))
        else:mapped=code.decode(enc,errors='strict')
        result.append((code,cmap.get(mapped,mapped)))
    return result

def _tokens(args,op,font):
    values=args[0] if op==b'TJ' else [args[-1]]
    out=[]
    for value in values:
        if isinstance(value,(str,bytes,ByteStringObject)):
            out.extend(('glyph',code,char)for code,char in glyph_codes(_raw(value),font))
        else:out.append(('adjustment',value,None))
    return out

def _prefix(args,op):
    if op==b"'":return [([],b'T*')]
    if op==b'"':return [([args[0]],b'Tw'),([args[1]],b'Tc'),([],b'T*')]
    return []

@dataclass
class NativePDF:
    path:Path
    page_index:int=0

    def paint_mapping(self):
        """Map native paint operators to actual drawing records by isolated identity.

        MuPDF merges a consecutive fill then stroke of one identical path into one
        fs record. Keep both original operators bound to that exact record.
        """
        if hasattr(self,'_paint_mapping'):return self._paint_mapping
        inventory=self.inventory();actual=fitz.open(self.path)[self.page_index].get_drawings();result=[];index=0;covered=set()
        for paint in inventory['paint_events']:
            pdf=self.isolate(event_ids=[],keep_vector_event_ids=[paint['event_id']]);isolated=fitz.open(stream=pdf,filetype='pdf')[0].get_drawings()
            if not isolated:continue
            if len(isolated)!=1:raise ValueError('One native paint event produced multiple vector drawing records')
            source=isolated[0];target=actual[index]
            if str(source['items'])!=str(target['items']):raise ValueError(('Native paint geometry mismatch',index,paint['event_id']))
            parts=set(source['type']);required=set(target['type'])
            if not parts<=required:raise ValueError(('Native paint type mismatch',index))
            for component in parts:
                keys=['fill','fill_opacity','even_odd']if component=='f'else ['color','width','stroke_opacity','lineCap','lineJoin','dashes']
                for key in keys:
                    if str(source.get(key))!=str(target.get(key)):raise ValueError(('Native paint style mismatch',index,key))
            result.append({'event_id':paint['event_id'],'final_drawing_index':index,'final_seqno':target['seqno'],'native_components':sorted(parts),'native_isolated_path_matches_actual_drawing':True})
            covered|=parts
            if covered==required:index+=1;covered=set()
        if index!=len(actual)or covered:raise ValueError(('Incomplete native paint mapping',index,len(actual)))
        self._paint_mapping=result;return result

    def inventory(self):
        reader=PdfReader(self.path);events=[];paints=[];calls=Counter();ignored_restore_events=[]
        def walk(owner,resources,path,state):
            source=owner.get('/Contents') if '/Contents'in owner else owner
            content=ContentStream(source,reader);state=copy.copy(state);stack=[];current_path=[]
            for index,(args,op)in enumerate(content.operations):
                if op in [b'm',b'l',b'c',b'v',b'y',b'h',b're']:current_path.append((args,op))
                elif op==b'n':current_path=[]
                if op==b'q':stack.append(copy.copy(state))
                elif op==b'Q':
                    if stack:state=stack.pop()
                    else:ignored_restore_events.append(path+f'/op{index}')
                elif op==b'Tf':
                    state['font_resource']=str(args[0]);state['font']=resources['/Font'][args[0]].get_object();state['font_size']=float(args[1])
                elif op==b'Tr':state['render_mode']=int(args[0])
                elif op==b'Do':
                    ref=resources['/XObject'][args[0]];obj=ref.get_object()
                    if obj.get('/Subtype')=='/Form':
                        xref=obj.indirect_reference.idnum;calls[xref]+=1
                        walk(obj,obj.get('/Resources',resources),path+f'/Do{index}:{str(args[0])}@{xref}',state)
                elif op in TEXT_SHOW:
                    font=state.get('font')
                    if font is None:raise ValueError('Text show has no bound native font')
                    tokens=_tokens(args,op,font);glyphs=[x for x in tokens if x[0]=='glyph'];eid=path+f'/op{index}'
                    events.append({'event_id':eid,'owner_xref':getattr(getattr(owner,'indirect_reference',None),'idnum',None),'operation_index':index,'operator':op.decode(),'font_resource':state['font_resource'],'font_base_name':str(font.get('/BaseFont')),'font_subtype':str(font.get('/Subtype')),'font_size_native':state.get('font_size'),'text_render_mode':state.get('render_mode',0),'text':''.join(x[2]for x in glyphs),'glyphs':[{'index':i,'encoded_hex':x[1].hex(),'unicode':x[2]}for i,x in enumerate(glyphs)]})
                elif op in PATH_PAINT:
                    if current_path:paints.append({'event_id':path+f'/op{index}','operation_index':index,'operator':op.decode(),'native_path_operation_count':len(current_path)})
                    current_path=[]
        page=reader.pages[self.page_index];walk(page,page['/Resources'],f'p{self.page_index}',{})
        doc=fitz.open(self.path);page=doc[self.page_index];traces=page.get_texttrace();chars=[]
        for ti,tr in enumerate(traces):
            for char in tr['chars']:chars.append({'unicode':chr(char[0]),'glyph_id':char[1],'origin':list(char[2]),'bbox':list(char[3]),'trace_index':ti,'seqno':tr['seqno'],'font':tr['font'],'font_size_final_pt':tr['size']})
        native_text=''.join(e['text']for e in events);trace_text=''.join(c['unicode']for c in chars)
        if native_text!=trace_text:raise ValueError('Native code-to-Unicode traversal does not exactly match actual PDF trace; explicit mapping required')
        ci=0
        for event in events:
            selected=chars[ci:ci+len(event['text'])];ci+=len(event['text']);event['texttrace_indices']=sorted(set(c['trace_index']for c in selected))
            if selected:event['page_bbox_pt']=[min(c['bbox'][0]for c in selected),min(c['bbox'][1]for c in selected),max(c['bbox'][2]for c in selected),max(c['bbox'][3]for c in selected)]
            offset=0
            for glyph in event['glyphs']:
                glyph['actual_trace_characters']=selected[offset:offset+len(glyph['unicode'])];offset+=len(glyph['unicode'])
        drawings=page.get_drawings();paint_map_verified=len(drawings)==len(paints)
        if paint_map_verified:
            for i,(paint,drawing)in enumerate(zip(paints,drawings)):
                expected='s'if paint['operator']in ['S','s']else 'f'if paint['operator']in ['f','F','f*']else 'fs'
                if drawing['type']!=expected:paint_map_verified=False;break
                paint.update(final_drawing_index=i,final_seqno=drawing['seqno'],final_page_rect_pt=list(drawing['rect']),final_width_pt=drawing['width'],final_stroke_rgb=drawing['color'],final_fill_rgb=drawing['fill'])
        if not paint_map_verified:
            for paint in paints:
                for key in list(paint):
                    if key.startswith('final_'):paint.pop(key)
        return {'artifact':str(self.path),'artifact_sha256':sha256(self.path),'page_index':self.page_index,'events':events,'paint_events':paints,'native_paint_to_final_drawing_order_verified':paint_map_verified,'native_paint_count':len(paints),'actual_final_drawing_count':len(drawings),'form_invocation_counts':dict(calls),'original_unmatched_Q_retained_as_renderer_noop':ignored_restore_events}

    def isolate(self,event_ids=None,glyph_refs=None,suppress_vector_paint=True,suppress_all_text=False,keep_vector_event_ids=None):
        """event_ids=None keeps all text; glyph_refs selects (event_id,glyph_index).

        Per-invocation form clones keep selection stable even when a source form is
        reused inside a clipped preservation patch. Fonts remain original resources.
        """
        selected=None if event_ids is None else set(event_ids)
        selected_glyphs=None if glyph_refs is None else set(tuple(x)for x in glyph_refs)
        selected_vectors=set(keep_vector_event_ids or [])
        reader=PdfReader(self.path);visited=set();seen_events=set();seen_glyphs=set()
        def walk(owner,resources,path,state):
            # Clone resource dictionaries per invocation, retaining every original
            # font reference. Each Do gets its own decoded Form stream below.
            resources=DictionaryObject(dict(resources));resources[NameObject('/XObject')]=DictionaryObject(dict(resources.get('/XObject',{})))
            owner[NameObject('/Resources')]=resources
            source=owner.get('/Contents') if '/Contents'in owner else owner
            content=ContentStream(source,reader);state=copy.copy(state);stack=[];out=[]
            for index,(args,op)in enumerate(content.operations):
                if op==b'q':stack.append(copy.copy(state))
                elif op==b'Q':
                    if stack:state=stack.pop()
                elif op==b'Tf':state['font']=resources['/Font'][args[0]].get_object()
                elif op==b'Tr':state['render_mode']=int(args[0])
                if op==b'Do':
                    obj=resources['/XObject'][args[0]].get_object()
                    if obj.get('/Subtype')=='/Form':
                        xref=obj.indirect_reference.idnum
                        clone=DecodedStreamObject()
                        for key,value in obj.items():
                            if key not in ['/Length','/Filter','/DecodeParms']:clone[key]=value
                        clone.set_data(obj.get_data());alias=NameObject('/NativeIsolation'+str(index));resources['/XObject'][alias]=clone
                        walk(clone,obj.get('/Resources',resources),path+f'/Do{index}:{str(args[0])}@{xref}',state)
                        args=[alias]
                    elif suppress_vector_paint:continue
                if suppress_vector_paint and op in PATH_PAINT and path+f'/op{index}'not in selected_vectors:
                    out.append(([],b'n'));continue
                if suppress_vector_paint and op in RASTER_PAINT:continue
                if op in TEXT_SHOW:
                    eid=path+f'/op{index}';seen_events.add(eid);mode=state.get('render_mode',0)
                    keep=not suppress_all_text and (selected is None or eid in selected)
                    if selected_glyphs is None:
                        if not keep:out.append(([NumberObject(3)],b'Tr'))
                        out.append((args,op))
                        if not keep:out.append(([NumberObject(mode)],b'Tr'))
                    else:
                        out.extend(_prefix(args,op));gi=0
                        for kind,value,unicode in _tokens(args,op,state['font']):
                            if kind=='adjustment':out.append(([ArrayObject([value])],b'TJ'));continue
                            ref=(eid,gi);seen_glyphs.add(ref);paint=keep and ref in selected_glyphs
                            out.append(([NumberObject(mode if paint else 3)],b'Tr'));out.append(([ByteStringObject(value)],b'Tj'));gi+=1
                        out.append(([NumberObject(mode)],b'Tr'))
                    continue
                out.append((args,op))
            content.operations=out
            if '/Contents'in owner:owner[NameObject('/Contents')]=content
            else:owner.set_data(content.get_data())
        page=reader.pages[self.page_index];walk(page,page['/Resources'],f'p{self.page_index}',{})
        if selected is not None and selected-seen_events:raise ValueError(f'Missing text event selectors:{selected-seen_events}')
        if selected_glyphs is not None and selected_glyphs-seen_glyphs:raise ValueError(f'Missing glyph selectors:{selected_glyphs-seen_glyphs}')
        writer=PdfWriter();writer.add_page(page)
        optional_content=reader.trailer['/Root'].get('/OCProperties')
        if optional_content is not None:
            writer._root_object[NameObject('/OCProperties')]=optional_content.clone(writer)
        buffer=io.BytesIO();writer.write(buffer);return buffer.getvalue()

    def label_evidence(self,event_ids,out_dir,scale=2,threshold=220):
        out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
        inv=self.inventory();events={e['event_id']:e for e in inv['events']};selected=[events[e]for e in event_ids]
        label_pdf=self.isolate(event_ids=event_ids);(out_dir/'label.pdf').write_bytes(label_pdf)
        label_rgb=render_pdf(label_pdf,scale);label_mask=render_alpha(label_pdf,scale)>(255-threshold)
        full=render_pdf(self.path,scale);glyphs=[]
        context=render_pdf(self.isolate(event_ids=event_ids,suppress_vector_paint=False),scale)
        if not hasattr(self,'_background_cache'):self._background_cache={}
        if scale not in self._background_cache:self._background_cache[scale]=render_pdf(self.isolate(suppress_all_text=True,suppress_vector_paint=False),scale)
        background=self._background_cache[scale]
        for event in selected:
            for g in event['glyphs']:
                if g['unicode'].isspace():continue
                ref=(event['event_id'],g['index']);pdf=self.isolate(event_ids=event_ids,glyph_refs=[ref]);mask=render_alpha(pdf,scale)>(255-threshold)
                if not mask.any():raise ValueError(f'Empty painted glyph:{ref}')
                glyphs.append((g['unicode'],mask));(out_dir/f'glyph-{len(glyphs)-1:03}.pdf').write_bytes(pdf)
        union=np.any([m for c,m in glyphs],axis=0)
        overlap=sum(int((a&b).sum())for i,(ac,a)in enumerate(glyphs)for bc,b in glyphs[i+1:])
        adjacent=[]
        from scipy.spatial import cKDTree
        for (ac,a),(bc,b)in zip(glyphs,glyphs[1:]):
            ap=np.argwhere(a);bp=np.argwhere(b);gap=float(np.linalg.norm(np.maximum(np.abs(ap[:,None,:]-bp[None,:,:])-1,0),axis=2).min())
            adjacent.append({'pair':ac+bc,'gap_px':round(gap,4),'overlap_ink_pixels':int((a&b).sum())})
        from PIL import Image
        Image.fromarray((label_mask*255).astype('uint8')).save(out_dir/'label-ink.png')
        visible=np.any(context!=background,axis=2)
        matches=np.abs(full.astype(int)-context.astype(int)).max(2)<8
        report={'artifact':str(self.path),'artifact_sha256':inv['artifact_sha256'],'text':''.join(e['text']for e in selected),'render_scale':scale,'pixel_units':'pixels in actual final PDF2x render; divide by2 for PDF points'if scale==2 else f'pixels in actual final PDF{scale}x render','font_source':'Original native PDF font resources; no substitution/reconstruction','selected_native_events':selected,'glyph_count':len(glyphs),'glyph_ink_pixels':int(label_mask.sum()),'same_label_glyph_overlap_pixels':overlap,'isolated_character_union_matches_label_ink':bool(np.array_equal(union,label_mask)),'isolated_glyph_union_difference_pixels':int(np.sum(union!=label_mask)),'visible_final_ink_match_fraction':float(np.mean((visible&matches)[label_mask])),'visible_match_method':'Selected native text with original vector background retained, compared with actual final; each ink pixel must also change the same native background with all text suppressed. This includes white route-shield glyphs and rejects fully occluded stale text. Road and other-label collisions are separate mandatory checks.','white_background_rgb_match_fraction_diagnostic':float(np.mean(np.abs(full.astype(int)-label_rgb.astype(int))[label_mask].max(axis=1)<8)),'adjacent_glyph_clearances_px':adjacent,'ink_threshold_alpha_above':255-threshold,'ink_mask_method':'Native glyph alpha coverage >35/255, consistently for dark and white text; equivalent to black-coverage-on-white minRGB<220. Original font color and resources remain unchanged.','render_size':[label_rgb.shape[1],label_rgb.shape[0]]}
        (out_dir/'report.json').write_text(json.dumps(report,indent=2));return report

def find_exact_group(events,text):
    matches=[]
    for start in range(len(events)):
        assembled='';group=[]
        for e in events[start:]:
            assembled+=e['text'];group.append(e['event_id'])
            if assembled==text:matches.append(group);break
            if not text.startswith(assembled):break
    return matches

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('pdf');parser.add_argument('output_dir');args=parser.parse_args();out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    native=NativePDF(Path(args.pdf));inventory=native.inventory();(out/'native-text-inventory.json').write_text(json.dumps(inventory,indent=2))
    for label in ['Lake Village Blvd','Baldwin Rd','75','East Entrance']:
        matches=find_exact_group(inventory['events'],label)
        if len(matches)!=1:raise ValueError((label,'Expected exactly one native label group',matches))
        result=native.label_evidence(matches[0],out/label.replace(' ','-'));print(label,{k:result[k]for k in ['glyph_count','same_label_glyph_overlap_pixels','isolated_character_union_matches_label_ink','isolated_glyph_union_difference_pixels','visible_final_ink_match_fraction']})
