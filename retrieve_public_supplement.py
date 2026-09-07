import pathlib,json,urllib.request,urllib.parse,concurrent.futures,zipfile,datetime,time,hashlib
P=pathlib.Path('public-supplement');P.mkdir(exist_ok=True)
B=[-83.225,42.64,-83.075,42.77]
BASE='https://gisservices.oakgov.com/arcgis/rest/services/Enterprise/EnterpriseOpenParcelDataMapService/MapServer/'
def save(n,b):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);b=b if isinstance(b,bytes) else json.dumps(b,ensure_ascii=False).encode();p.write_bytes(b);return hashlib.sha256(b).hexdigest()
def get(u,q):
 u+='?'+urllib.parse.urlencode(q)
 for k in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Public-geographic-audit/1.0'}),timeout=60) as r:b=r.read()
   d=json.loads(b)
   if 'error' in d:raise RuntimeError(d['error'])
   return d,b,u
  except Exception:
   if k==2:raise
   time.sleep(1+k)
def layer(name,num,fields):
 u=BASE+str(num);rec={'name':name,'url':u,'bounds':B,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':False,'allowed_fields':fields}
 try:
  meta,b,v=get(u,{'f':'json'});save(name+'/metadata.json',b);oid=meta.get('objectIdField') or next(f['name'] for f in meta['fields'] if f['type']=='esriFieldTypeOID')
  available=[f['name'] for f in meta['fields']];fields=[f for f in fields if f in available]
  if oid not in fields:fields.insert(0,oid)
  q={'f':'json','where':'1=1','geometry':','.join(map(str,B)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects'}
  d,b,v=get(u+'/query',{**q,'returnIdsOnly':'true'});save(name+'/ids.json',b);ids=sorted(set(d['objectIds']))
  d,b,v=get(u+'/query',{**q,'returnCountOnly':'true'});save(name+'/count.json',b);assert d['count']==len(ids),(d['count'],len(ids))
  chunks=[ids[i:i+350] for i in range(0,len(ids),350)]
  def page(pair):
   i,part=pair;d,b,v=get(u+'/query',{'f':'json','objectIds':','.join(map(str,part)),'outFields':','.join(fields),'returnGeometry':'true','outSR':4326});fs=d['features'];got={f['attributes'][oid] for f in fs};assert got==set(part),(i,len(got),len(part));h=save(name+'/page-%04d.json'%i,b);return fs,{'url':v,'count':len(fs),'sha256':h}
  features=[];requests=[]
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
   for fs,r in ex.map(page,enumerate(chunks)):features+=fs;requests.append(r)
  save(name+'/features.json',{'features':features,'spatialReference':{'wkid':4326},'fields':[f for f in meta['fields'] if f['name'] in fields]});rec.update(complete=len(features)==len(ids),expected_count=len(ids),actual_count=len(features),requests=requests)
 except Exception as e:rec['error']=str(e)
 save(name+'/receipt.json',rec);print(name,rec.get('actual_count'),rec.get('complete'),rec.get('error'));return rec
jobs=[('parcel-classification',1,['OBJECTID_12','OBJECTID','KEYPIN','REVISIONDATE','CVTTAXCODE','CVTTAXDESCRIPTION','PIN','CLASSCODE','SITEADDRESS','SITECITY','SITESTATE','SITEZIP5','STRUCTURE_DESC']),('site-addresses',0,['OBJECTID','TYPE','PIN','SITEPREFIXONE','SITESTREETNUMBER','SITESTREETNAME','SITESTREETTYPE','SITESUFFIXONE','SITESTREETADDRESS','SITECITY','SITESTATE','SITEZIPCODE']),('recorded-subdivisions',4,['OBJECTID','CondoType','NAME','OCCP','TYPE','LIBERPAGE','ACRESRECORDED','ACRES','ExhibitBLink','NumberOfUnits','PlatLink'])]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:receipts=list(ex.map(lambda j:layer(*j),jobs))
save('RECEIPTS.json',receipts)
with zipfile.ZipFile('public-supplement.zip','w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,str(p))
