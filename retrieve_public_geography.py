import pathlib,json,urllib.request,urllib.parse,datetime,hashlib,concurrent.futures,zipfile,re
ROOT=pathlib.Path('public-data');ROOT.mkdir(exist_ok=True);TMP=pathlib.Path('_public_raw');TMP.mkdir(exist_ok=True)
B=[-83.225,42.64,-83.075,42.77]
def save(n,d):
 p=TMP/n;p.parent.mkdir(parents=True,exist_ok=True);r=d if isinstance(d,bytes) else json.dumps(d,ensure_ascii=False).encode();p.write_bytes(r);return hashlib.sha256(r).hexdigest()
def get(url,params=None,data=None,timeout=60):
 if params:url+='?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,data=data,headers={'User-Agent':'Public-geography-reference/1.0'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(),url
def layer(name,url):
 rec={'name':name,'url':url,'bounds':B,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':False}
 try:
  raw,u=get(url,{'f':'pjson'});m=json.loads(raw);save(name+'/metadata.json',raw)
  oid=m.get('objectIdField') or next(f['name'] for f in m['fields'] if f['type']=='esriFieldTypeOID')
  q={'f':'json','where':'1=1','geometry':','.join(map(str,B)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects'}
  raw,u=get(url+'/query',{**q,'returnIdsOnly':'true'});d=json.loads(raw);save(name+'/ids.json',raw);ids=sorted(set(d['objectIds']))
  raw,u=get(url+'/query',{**q,'returnCountOnly':'true'});count=json.loads(raw);save(name+'/count.json',raw)
  if count['count']!=len(ids):raise RuntimeError('ID/count mismatch')
  fields=[f['name'] for f in m['fields'] if not any(t in f['name'].lower() for t in ['owner','taxpayer','mail','phone','email'])]
  features=[];seen=set();rec['requests']=[]
  for i in range(0,len(ids),400):
   part=ids[i:i+400];params={'f':'json','objectIds':','.join(map(str,part)),'outFields':','.join(fields),'returnGeometry':'true','outSR':4326}
   raw,u=get(url+'/query',params);d=json.loads(raw)
   if 'error' in d:raise RuntimeError(d['error'])
   got={f['attributes'][oid] for f in d.get('features',[])}
   if got!=set(part):raise RuntimeError('Incomplete page '+str(i))
   rec['requests'].append({'url':u,'count':len(got),'sha256':save(name+'/page-%03d.json'%(i//400),raw)})
   features+=d['features'];seen|=got
  rec.update(expected_count=len(ids),actual_count=len(features),complete=seen==set(ids));save(name+'/features.json',{'features':features,'fields':m['fields'],'spatialReference':{'wkid':4326}})
 except Exception as e:rec['error']=str(e)
 save(name+'/receipt.json',rec);return rec
jobs=[('county-roads','https://gisservices.oakgov.com/arcgis/rest/services/Enterprise/EnterpriseTransportationDataMapService/MapServer/0'),('county-parcels','https://gisservices.oakgov.com/arcgis2/rest/services/Applications/PivotPointAppMapService/FeatureServer/1')]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:receipts=list(ex.map(lambda j:layer(*j),jobs))
for name,url in [('rochester-street-map-2022.pdf','https://rochestermi.org/DocumentCenter/View/4254'),('rochester-precinct-map-2024.pdf','https://rochestermi.org/DocumentCenter/View/5482/Voter-Precinct-1'),('rochester-hills-map-index.html','https://atlas.rochesterhills.org/IndexMapsofInterest/')]:
 try:
  raw,u=get(url);save(name,raw);receipts.append({'name':name,'url':url,'success':True})
  if name.endswith('.html'):
   text=raw.decode(errors='replace');print('MAP_INDEX_HTML_START');print(text);print('MAP_INDEX_HTML_END')
 except Exception as e:receipts.append({'name':name,'error':str(e)})
q='[out:json][timeout:100];(way[highway](42.64,-83.225,42.77,-83.075);nwr[landuse](42.64,-83.225,42.77,-83.075);nwr[building](42.64,-83.225,42.77,-83.075););out body geom;'
try:
 raw,u=get('https://overpass-api.de/api/interpreter',data=urllib.parse.urlencode({'data':q}).encode(),timeout=120);d=json.loads(raw);save('osm-inventory.json',raw);receipts.append({'name':'osm','url':u,'query':q,'complete':not d.get('remark'),'count':len(d.get('elements',[])),'remark':d.get('remark')})
except Exception as e:receipts.append({'name':'osm','complete':False,'error':str(e)})
save('RETRIEVAL_RECEIPTS.json',receipts)
manifest={str(p.relative_to(TMP)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in TMP.rglob('*') if p.is_file()}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(ROOT/'rochester-public-geography.zip','w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in TMP.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(TMP))
(ROOT/'retrieval-summary.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='requests'} for r in receipts],indent=2))
print((ROOT/'retrieval-summary.json').read_text());print('ZIP_BYTES',(ROOT/'rochester-public-geography.zip').stat().st_size)
