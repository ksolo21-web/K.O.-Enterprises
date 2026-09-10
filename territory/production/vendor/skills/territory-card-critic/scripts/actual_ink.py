"""Fresh final-PDF measurement using retained NativePDF isolation, never claimed metrics."""
import tempfile
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from native_subsegment import isolate_subsegment
from descriptive_access_native_pdf import NativePDF,render_alpha,render_pdf

def require(ok,msg):
 if not ok:raise ValueError(msg)
def exact_gap_map(mask,target):
 rp=np.argwhere(target);require(len(rp)>0,'Assigned native road mask is empty');tree=cKDTree(rp);ip=np.argwhere(mask);near,_=tree.query(ip);result=np.full(mask.shape,np.inf)
 for pix,d in zip(ip,near):
  cs=rp[tree.query_ball_point(pix,float(d)+2**.5)];result[tuple(pix)]=float(np.linalg.norm(np.maximum(np.abs(cs-pix)-1,0),axis=1).min())
 return result

def measure(pdf,descriptor,claimed,final_drawing_index,vertex_range,expected_vertices):
 import fitz
 native=NativePDF(Path(pdf));inv=native.inventory();events=inv['events'];ids=claimed.get('native_event_ids')
 require(isinstance(ids,list) and ids and len(ids)==len(set(ids)),'complete unique native event IDs required')
 indexed={e['event_id']:e for e in events};require(all(i in indexed for i in ids),'missing actual native event')
 selected=[indexed[i] for i in ids];require(''.join(e['text'] for e in selected)==descriptor,'actual complete native characters differ from descriptor')
 if 'selected_native_events' in claimed:require(claimed['selected_native_events']==selected,'claimed native trace is not actual PDF trace')
 with tempfile.TemporaryDirectory(prefix='descriptive-access-') as td:
  out=Path(td);fresh=native.label_evidence(ids,out,scale=2)
  for k in ['same_label_glyph_overlap_pixels','isolated_glyph_union_difference_pixels']:require(fresh[k]==0,'actual glyph isolation/overlap failure')
  require(fresh['visible_final_ink_match_fraction']==1.0,'actual descriptor hidden, overpainted or changed')
  mask=render_alpha(out/'label.pdf')>35
  otherids=[e['event_id'] for e in events if e['event_id'] not in ids]
  other=render_alpha(native.isolate(event_ids=otherids))>35
  require(not np.any(mask&other),'actual other-text collision')
  require(not (mask[0].any()or mask[-1].any()or mask[:,0].any()or mask[:,-1].any()),'actual clipped label')
  mapping=native.paint_mapping();draws=fitz.open(pdf)[0].get_drawings()
  def vector_mask(indices):
   paints=[m['event_id'] for m in mapping if m['final_drawing_index'] in indices]
   require(paints,'missing actual assigned native paint')
   return render_alpha(native.isolate(event_ids=[],keep_vector_event_ids=paints))>35
  assigned_paints=[m['event_id']for m in mapping if m['final_drawing_index']==final_drawing_index]
  require(len(assigned_paints)==1,'one native access stroke required')
  actual_road_pdf=native.isolate(event_ids=[],keep_vector_event_ids=assigned_paints)
  selected_pdf=isolate_subsegment(actual_road_pdf,vertex_range,expected_vertices)
  road=(render_alpha(selected_pdf)>35)&(render_alpha(actual_road_pdf)>35)
  require(road.any(),'empty actual source-bound subsegment ink')
  colored={i for i,d in enumerate(draws) if any(c and max(c)-min(c)>.2 for c in [d.get('color'),d.get('fill')])}
  if colored:
   # Preserve every neutral paint, graphics state, clip and compositing order.
   all_ids=[m['event_id']for m in mapping]
   neutral_ids=[m['event_id']for m in mapping if m['final_drawing_index']not in colored]
   full_vectors=render_pdf(native.isolate(event_ids=[],keep_vector_event_ids=all_ids))
   neutral_vectors=render_pdf(native.isolate(event_ids=[],keep_vector_event_ids=neutral_ids))
   require(full_vectors.shape==neutral_vectors.shape,'inconsistent native vector render dimensions')
   visible_colored_contribution=np.any(full_vectors!=neutral_vectors,axis=2)
   require(not np.any(mask&visible_colored_contribution),'actual colored road/site collision')
  gapmap=exact_gap_map(mask,road);per=[]
  for i,g in enumerate([g for e in selected for g in e['glyphs'] if not g['unicode'].isspace()]):
   gm=render_alpha(out/f'glyph-{i:03}.pdf')>35;per.append({'char':g['unicode'],'clearance_px':round(float(gapmap[gm].min()),4)})
  vals=[x['clearance_px'] for x in per];require(vals and min(vals)>=2 and max(vals)<=15 and max(vals)-min(vals)<=8,'actual glyph/road gap failure')
  require(per==claimed['per_glyph_ink_clearance_px'],'claimed glyph gaps differ from fresh actual measurement')
  return fresh,per
