import pathlib,json,urllib.request,urllib.parse,concurrent.futures,zipfile
P=pathlib.Path('public-supplement');P.mkdir(exist_ok=True)
def fetch(name,url):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public-map-reference/1.0'}),timeout=55) as r:b=r.read()
  (P/name).write_bytes(b);print(name,len(b))
 except Exception as e:(P/(name+'.error.txt')).write_text(str(e));print(name,e)
jobs=[('Rochester-Hills-StreetMapBook.pdf','https://www.rochesterhills.org/Maps/StreetMapBook.pdf'),('Rochester-Hills-StreetMap.pdf','https://www.rochesterhills.org/Maps/StreetMap.pdf'),('enterprise-services.json','https://gisservices.oakgov.com/arcgis/rest/services/Enterprise?f=pjson'),('application-services.json','https://gisservices.oakgov.com/arcgis2/rest/services/Applications?f=pjson'),('pivot-layers.json','https://gisservices.oakgov.com/arcgis2/rest/services/Applications/PivotPointAppMapService/FeatureServer/layers?f=pjson'),('enterprise-cadastral.json','https://gisservices.oakgov.com/arcgis/rest/services/Enterprise/EnterpriseCadastralMapService/MapServer?f=pjson'),('enterprise-property.json','https://gisservices.oakgov.com/arcgis/rest/services/Enterprise/EnterprisePropertyDataMapService/MapServer?f=pjson'),('rochester-development-app.json','https://rochesterhills.maps.arcgis.com/sharing/rest/content/items/d5f0e338a9544bcba7f256691591e204/data?f=json')]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:list(ex.map(lambda j:fetch(*j),jobs))
for p in list(P.glob('*services.json')):
 try:
  d=json.loads(p.read_text());host='https://gisservices.oakgov.com/arcgis2/rest/services/' if 'application' in p.name else 'https://gisservices.oakgov.com/arcgis/rest/services/'
  for s in d.get('services',[]):
   if any(q in s['name'].lower() for q in ['parcel','cadastral','property','landuse']):fetch(s['name'].replace('/','-')+'-layers.json',host+s['name']+'/'+s['type']+'/layers?f=pjson')
 except Exception as e:print(e)
with zipfile.ZipFile('public-supplement.zip','w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in P.rglob('*'):
  if p.is_file():z.write(p,str(p))
