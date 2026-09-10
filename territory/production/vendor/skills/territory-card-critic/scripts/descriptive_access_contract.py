"""Proposed, uninstalled direct-descriptor contract for verified unnamed access.
No thresholds or existing representation semantics are changed.
"""
import hashlib,json,math,re,xml.etree.ElementTree as ET
from pathlib import Path
from actual_ink import measure
import fitz,numpy as np
from shapely.geometry import LineString,Point

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(v):
 if isinstance(v,float)and not math.isfinite(v):raise ValueError('nonfinite value')
 if isinstance(v,dict):
  for x in v.values():finite(x)
 elif isinstance(v,list):
  for x in v:finite(x)
def record(ref):
 if not isinstance(ref,dict)or not isinstance(ref.get('path'),str)or not re.fullmatch('[a-f0-9]{64}',str(ref.get('sha256',''))):raise ValueError('missing file/hash binding')
 if sha(ref['path'])!=ref['sha256']:raise ValueError('stale file/hash binding')
 x=json.loads(Path(ref['path']).read_text());finite(x);return x
def need(ok,msg):
 if not ok:raise ValueError(msg)
def normalize_text(s):return ' '.join(str(s).lower().split())
def line_points(d):
 need(bool(d['items'])and all(x[0]=='l'for x in d['items']),'unsupported nonline access source')
 need(all(tuple(d['items'][i][2])==tuple(d['items'][i+1][1]) for i in range(len(d['items'])-1)), 'disconnected native path')
 return [list(d['items'][0][1])]+[list(x[2])for x in d['items']]

BINDINGS={'entrance':('id','site_id','public_road_id','target_access_road_id','verified','visible','representation','source_ref'),'site':('id','name','verified','source_ref','verified_entrance_count'),'access_road':('id','name','name_status','visible','geometry_verified','role','source_feature_id'),'public_road':('id','name','visible','geometry_verified'),'label':('id','text','road_id','method','font_family','font_weight','direct_fit_available','covers_street','overlaps_label','clipped')}
def select(obj,kind):return {k:obj.get(k)for k in BINDINGS[kind]}

def validate_contract(ref,artifact_sha256=None):
 errors=[];c=None
 try:
  c=record(ref);need(c.get('schema')=='descriptive-access-1','wrong contract schema')
  pdf=c['artifact'];need(sha(pdf['path'])==pdf['sha256'],'stale artifact')
  if artifact_sha256 is not None:need(pdf['sha256']==artifact_sha256,'wrong final artifact')
  e,s,r,p,l=[c[k]for k in ('entrance','site','access_road','public_road','label')]
  need(e['representation']=='descriptive_access','wrong mode')
  for obj in [e,s,r,p,l]:need(isinstance(obj.get('id'),str)and bool(obj['id'].strip()),'missing bound identity')
  need(e['verified']is True and e['visible']is True and s['verified']is True,'unverified or hidden entrance/site')
  need(type(s['verified_entrance_count'])is int and s['verified_entrance_count']>0,'missing real entrance count')
  need(bool(e['source_ref'])and bool(s['source_ref']),'missing entrance/site source')
  need(e['site_id']==s['id']and e['public_road_id']==p['id']and e['target_access_road_id']==r['id'],'entrance/site/road identity mismatch')
  need(r['id']!=p['id']and all(x['visible']is True and x['geometry_verified']is True for x in [r,p]),'hidden/unverified access or public road')
  need(r['role']=='access_stem'and r['name_status']=='verified_unnamed','not a verified unnamed access segment')
  desc=c['descriptor'];need(isinstance(desc,str)and bool(desc.strip())and r['name']==desc and l['text']==desc and l['road_id']==r['id'],'descriptor label binding mismatch')
  need(l['method']in ['direct','curved']and l['direct_fit_available']is True,'direct readable fit required')
  need(l['font_weight']==400 and bool(l['font_family']),'regular bound label font required')
  need(all(l[k]is False for k in ['covers_street','overlaps_label','clipped']),'label obstruction/collision/clipping')
  nr=record(c['source_name_review']);need(nr.get('schema')=='descriptive-access-source-review-1'and nr.get('independent')is True and nr.get('no_established_name')is True and bool(nr.get('evidence')),'independent unnamed-source review required')
  for key,val in [('entrance_id',e['id']),('site_id',s['id']),('access_road_id',r['id']),('public_road_id',p['id']),('feature_id',r['source_feature_id'])]:need(nr.get(key)==val,'source review '+key+' mismatch')
  corroboration=nr.get('non_osm_corroboration');need(isinstance(corroboration,dict),'non-OSM corroboration required')
  need(corroboration.get('independent_review_completed')is True and corroboration.get('conclusion')=='verified_unnamed_access','independent non-OSM unnamed conclusion required')
  need(corroboration.get('basis')=='original_map_and_authoritative_road_inventory','positive source corroboration basis required')
  for k in ['entrance_id','site_id','access_road_id','public_road_id']:need(corroboration.get(k)==nr.get(k),'corroboration identity mismatch')
  original=corroboration['original_map'];need(original['path']==c['source_segment']['path']and original['sha256']==c['source_segment']['sha256']and sha(original['path'])==original['sha256'],'corroboration original-map binding mismatch')
  authoritative=record(corroboration['authoritative_road_inventory']);need(isinstance(authoritative.get('features'),list)and bool(authoritative['features'])and not authoritative.get('exceededTransferLimit',False),'complete authoritative inventory required')
  need(str(corroboration.get('authority_url','')).startswith('https://')and 'openstreetmap' not in corroboration['authority_url'].lower(),'non-OSM authoritative source URL required')
  feature_key=corroboration['feature_id_field'];rawids=[str(f.get('attributes',{}).get(feature_key))for f in authoritative['features']];reviewed=corroboration['reviewed_feature_ids'];need(len(rawids)==len(set(rawids))and set(rawids)==set(map(str,reviewed))and len(reviewed)==len(rawids),'complete unique authoritative inventory review required')
  need(corroboration.get('native_access_geometry_reviewed')is True and corroboration.get('no_established_name_after_source_comparison')is True and bool(corroboration.get('geometry_comparison_evidence')),'independent original-map/inventory geometry comparison required')
  inventory=record(c['site_entrance_inventory']);need(inventory.get('independent')is True and inventory.get('complete')is True and inventory.get('site_id')==s['id']and inventory.get('artifact_sha256')==pdf['sha256'],'complete current site entrance inventory required')
  records=inventory.get('entrances');need(isinstance(records,list)and len(records)==s['verified_entrance_count'],'site entrance count mismatch');ids=[x.get('id')for x in records];need(len(set(ids))==len(ids)and e['id']in ids,'missing/duplicate inventory entrance')
  need(next(x for x in records if x.get('id')==e['id'])==e,'stale complete entrance inventory');need(all(x.get('verified')is True and x.get('visible')is True and x.get('site_id')==s['id']and bool(x.get('source_ref'))and bool(x.get('public_road_id'))and bool(x.get('target_access_road_id')) for x in records),'unverified/hidden inventory entrance')
  raw=nr['raw_source'];need(sha(raw['path'])==raw['sha256'],'stale raw name source');xml=ET.parse(raw['path']).getroot();need(xml.tag=='osm'and not xml.findall('error'),'invalid OSM source')
  typ,id=r['source_feature_id'].split('/');found=[x for x in xml if x.tag==typ and x.attrib.get('id')==id];need(len(found)==1,'missing/duplicate source object');tags={x.attrib['k']:x.attrib['v']for x in found[0].findall('tag')}
  need(tags==nr['raw_tags'],'stale source tags');need(tags.get('highway')in ['service','residential','unclassified','living_street'],'source is not an access street')
  need(not any(v.strip() for k,v in tags.items()if k in ['name','official_name','alt_name','short_name','loc_name','old_name']or k.startswith('name:')),'named road misclassified as unnamed')
  bind=c['source_segment'];need(bind==nr['source_segment'],'source segment review mismatch');need(sha(bind['path'])==bind['sha256'],'stale native source')
  with fitz.open(bind['path'])as doc:
   pi=bind['page_index'];di=bind['drawing_index'];need(type(pi)is int and type(di)is int and 0<=pi<len(doc),'invalid source page/index');ds=doc[pi].get_drawings();need(0<=di<len(ds),'missing native access path');native=line_points(ds[di]);width=ds[di]['width'];source_style={k:ds[di].get(k) for k in ['color','fill','lineCap','lineJoin','dashes','stroke_opacity','fill_opacity','closePath','type']}
  i,j=bind['vertex_range'];need(type(i)is int and type(j)is int and 0<=i<j<=len(native)and j-i>=2,'invalid source segment range');pts=np.array(native[i:j],float);scale,tx,ty=bind['transform'];need(all(type(v)in [int,float]and math.isfinite(v)for v in [scale,tx,ty])and scale>0,'invalid source transform');final=pts*scale+[tx,ty]
  with fitz.open(pdf['path'])as doc:
   need(len(doc)==1,'one actual front page required');draws=doc[0].get_drawings();idx=bind['final_drawing_index'];need(type(idx)is int and 0<=idx<len(draws),'missing final access path');actual=np.array(line_points(draws[idx]),float);expected=np.array(native,float)*scale+[tx,ty];need(actual.shape==expected.shape and np.max(abs(actual-expected))<=.001,'final/source access geometry mismatch');need(abs(draws[idx]['width']-width*scale)<.0001,'access width mismatch');need({k:draws[idx].get(k) for k in source_style}==dict(source_style,lineJoin=float(np.float32(source_style['lineJoin']*scale))),'access native style mismatch');actual_text=normalize_text(doc[0].get_text())
  directions=c['directions_text'];need(normalize_text(desc)in normalize_text(directions)and normalize_text(p['name'])in normalize_text(directions),'directions must name descriptor and serving public road');need(normalize_text(directions)in actual_text,'directions do not match actual PDF')
  q=record(c['measurement_report']);need(q['artifact_sha256']==pdf['sha256']and q.get('render_scale')==2,'stale/wrong-scale measurement');need(q['quantitative_gate']['pass']is True and q['quantitative_gate']['failures']==[],'existing quantitative checks fail');need(q['thresholds'].get('glyph_gap_px')==[2,15]and q['thresholds'].get('glyph_gap_spread_px_max')==8,'existing gap thresholds changed')
  entries=[x for x in q['labels']if x.get('id')==l['id']];need(len(entries)==1,'missing/duplicate measured label');m=entries[0];need(m['text']==desc and m['road_id']==r['id']and m['artifact_sha256']==pdf['sha256'],'measured label/road/artifact mismatch')
  for key in ['same_label_glyph_overlap_pixels','isolated_glyph_union_difference_pixels','overlap_other_label_ink_pixels','overlap_all_road_ink_pixels','overlap_purple_feature_ink_pixels']:need(type(m.get(key))is int and m[key]==0,'actual label collision '+key)
  need(m.get('clipped')is False and m.get('isolated_character_union_matches_label_ink')is True and m.get('visible_final_ink_match_fraction')==1.0,'hidden/unmatched native label')
  gaps=[x['clearance_px']for x in m['per_glyph_ink_clearance_px']];need(bool(gaps)and all(type(x)in [int,float]and math.isfinite(x)and 2<=x<=15 for x in gaps)and max(gaps)-min(gaps)<=8,'actual glyph/road gap failure')
  fresh,actual_gaps=measure(pdf['path'],desc,m,bind['final_drawing_index'],bind['vertex_range'],final);m=dict(m);m['selected_native_events']=fresh['selected_native_events']
  # Source-bound placement check supplements, rather than replaces, measured ink gaps.
  line=LineString(final);trace=[g for ev in m['selected_native_events']for glyph in ev.get('glyphs',[])for g in glyph.get('actual_trace_characters',[])];need(bool(trace),'actual native glyph positions required')
  need(all(np.linalg.norm(final[k+1]-final[k])>0 for k in range(len(final)-1)),'zero-length source segment');first=(final[1]-final[0]);first/=np.linalg.norm(first);last=final[-1]-final[-2];last/=np.linalg.norm(last)
  for g in trace:
   x0,y0,x1,y1=g['bbox'];center=np.array([(x0+x1)/2,(y0+y1)/2]);need(float((center-final[0])@first)>=0 and float((center-final[-1])@last)<=0,'label outside its usable source segment');need(line.distance(Point(center))<=width*scale/2+15/2+float(g['font_size_final_pt']),'label not adjacent to bound source segment')
  vr=c['independent_visual_review'];need(vr.get('independent')is True and vr.get('artifact_sha256')==pdf['sha256']and vr.get('entrance_id')==e['id']and vr.get('label_id')==l['id'],'stale/missing independent direct-fit review')
  for key in ['actual_size_review_completed','closeup_review_completed','readable_direct_fit','label_binds_actual_access_segment','no_arrow_needed']:need(vr.get(key)is True,'direct-fit review '+key+' required')
  need(bool(vr.get('evidence')),'visual evidence required')
 except (OSError,ValueError,TypeError,KeyError,IndexError,ET.ParseError,OverflowError)as exc:errors.append('descriptive_access: '+str(exc))
 return errors,c

def validate_project_entrance(project,entrance,artifact_sha256=None):
 errors,c=validate_contract(entrance.get('descriptive_access_contract'),artifact_sha256)
 try:
  need(c is not None,'missing contract');need(len([x for x in project.get('entrances',[]) if x.get('id')==entrance.get('id')])==1,'missing/duplicate project entrance');need(select(entrance,'entrance')==c['entrance'],'stale project entrance')
  for kind,array in [('site','sites'),('access_road','roads'),('public_road','roads'),('label','labels')]:
   matches=[x for x in project.get(array,[])if x.get('id')==c[kind]['id']];need(len(matches)==1,'missing/duplicate project '+kind);need(select(matches[0],kind)==c[kind],'stale project '+kind)
  need(project['directions']['text']==c['directions_text'],'project directions mismatch');inventory=record(c['site_entrance_inventory']);actual=[select(x,'entrance') for x in project.get('entrances',[])if x.get('site_id')==c['site']['id']];need(sorted(actual,key=lambda x:x['id'])==sorted(inventory['entrances'],key=lambda x:x['id']),'project complete site inventory mismatch')
  need(not any(entrance.get(k)for k in ['arrow','label_text','target_box']),'descriptive access must not add a redundant callout')
  nav=[x for x in project['navigation_presentation_review']['entrances']['representations']if x.get('entrance_id')==entrance['id']];need(len(nav)==1,'missing/duplicate descriptive review');errors.extend(validate_review_record(nav[0],artifact_sha256,entrance))
 except (ValueError,TypeError,KeyError,IndexError)as exc:errors.append('descriptive_access: '+str(exc))
 return errors

def validate_review_record(r,artifact_sha256=None,entrance=None):
 errors,c=validate_contract(r.get('descriptive_access_contract'),artifact_sha256)
 try:
  need(c is not None,'missing navigation contract');need(r.get('representation')=='descriptive_access'and r.get('named_street_sufficient')is False,'descriptor is not a verified street name')
  for key,val in [('entrance_id',c['entrance']['id']),('site_id',c['site']['id']),('access_road_id',c['access_road']['id']),('public_road_id',c['public_road']['id']),('label_id',c['label']['id']),('descriptor',c['descriptor']),('serving_street',c['public_road']['name'])]:need(r.get(key)==val,'navigation '+key+' mismatch')
  if entrance is not None:need(entrance.get('descriptive_access_contract')==r.get('descriptive_access_contract'),'project/navigation contract mismatch')
 except (ValueError,TypeError,KeyError,IndexError)as exc:errors.append('descriptive_access: '+str(exc))
 return errors

def validate_review_inventory(representations):
 errors=[]
 try:
  ids=[x.get('entrance_id') for x in representations if isinstance(x,dict)]
  for r in representations:
   if not isinstance(r,dict) or r.get('representation')!='descriptive_access':continue
   c=record(r.get('descriptive_access_contract'));inv=record(c['site_entrance_inventory'])
   need(all(ids.count(x['id'])==1 for x in inv['entrances']),'standalone navigation omitted/duplicated a verified site entrance')
 except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:errors.append('descriptive_access: '+str(exc))
 return errors
