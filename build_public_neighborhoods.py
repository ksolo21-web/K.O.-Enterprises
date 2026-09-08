import pathlib,json,zipfile,hashlib,re,collections,math
from shapely.geometry import LineString,MultiLineString,Polygon,box,shape
from shapely.ops import unary_union
Z=zipfile.ZipFile('public-data/rochester-public-geography.zip');OUT=pathlib.Path('public-neighborhoods');OUT.mkdir(exist_ok=True)
raw=Z.read('county-roads/features.json');D=json.loads(raw);fs=D['features'];meta=json.loads(Z.read('county-roads/metadata.json'))
(OUT/'road-fields-and-examples.json').write_text(json.dumps({'fields':meta['fields'],'examples':[f['attributes'] for f in fs[:3]]},indent=2))
print('ROAD_FIELDS',list(fs[0]['attributes']))
def name(f):
 a=f['attributes'];return str(a.get('CartographicName') or a.get('FULLNAME') or a.get('StreetName') or a.get('STREETNAME') or '')
def key(n):return re.sub(r'[^a-z0-9]','',n.lower())
features=[]
for f in fs:
 paths=f.get('geometry',{}).get('paths',[])
 if not paths:continue
 g=unary_union([LineString(p) for p in paths if len(p)>1])
 features.append((f,g,name(f)))
(OUT/'all-road-names.json').write_text(json.dumps(sorted(set(n for f,g,n in features)),indent=2))
seeds={
 'glenmoor':['glenmoor','lysander','sycamore','courtland','redoak'],
 'oaklandvalley':['oaklandvalley','cedarwald','kennebunk','broadleaf','thornyash','reddingwood','beechview','birchhill'],
 'bedlington':['bedlington','windsong','blushing','arcadian','bliss','enchantment','windrift'],
 'claremont':['claremont','antrim','birnam','brecon','castlemartin'],
 'cloisters':['cloisters','stoneykirk','monarch'],
 'addison':['addison','croftshire','ambleside','ashburton','carlisle'],
 'murfield':['murfield','wellwood','lancewood','ledgewood','shorebrook','carrollton','baytree','westchester','lochmoor'],
 'wyngate':['millecoquins','rockvalley','ringneck','beavercreek','wyngate','hollowcorners','loggers','snowyowl','caribou'],
 'dunham':['maplecreek','catlin','watson','copper','minersrun','dunham','tulberry','christenbury','garnet','boulder'],
 'stonypointe':['creekview','pebblecreek','stonycreek','roundview','kentfield','stonypointe','putnam','pebblepointe','pointeplace'],
 'ansal':['tanglewood','sugarpine','sumac','blackmaple','ansal','nesbit','wimpole'],
 'campus':['fairoak','campus','rutgers','spartan','baylor','croydon','kingstree','bucknell','yale'],
 'avoncircle':['rochesterhills','seville','avoncir'],
 'wildwood':['pedal','alpine','wildwood','ulster','munster','lynndale','winwood','leinster','castlebar','hampstead','redwood','briar'],
 'bellevernon':['avoncrest','bellevernon','clairhill','chalet','wayward'],
 'maryknolle':['kingsleyfair','sussexfair','hillendale','maryknolle','canterbury','stratford','knollcrest','moonway','longford'],
 'quarry':['panorama','majestic','quarry','galena','tranquility','millrace','trickey','petoskey','placid','passive','serene','triumph'],
 'willowtree':['orionct','elmhill','maplehill','willowtree','cherryblossom','applehill','appleorchard','cherrytree'],
 'honeycrisp':['crispin','lobo','hawkeye','honeycrisp','winesap','jonimac','goldrush']
}
index=[]
for area,words in seeds.items():
 seed=[(f,g,n) for f,g,n in features if any(key(n).startswith(w) for w in words)]
 if not seed:index.append({'area':area,'error':'No matched seed roads'});continue
 g=unary_union([g for f,g,n in seed]);b=list(g.bounds);pad=.00045;b=[b[0]-pad,b[1]-pad,b[2]+pad,b[3]+pad];region=box(*b)
 rows=[]
 for f,g,n in features:
  if not g.intersects(region):continue
  c=g.intersection(region).simplify(.000005,preserve_topology=True)
  paths=[list(c.coords)] if c.geom_type=='LineString' else [list(v.coords) for v in getattr(c,'geoms',[]) if v.geom_type=='LineString']
  a=f['attributes'];oid=a.get('OBJECTID',a.get('ObjectID',a.get('FID')))
  ps=[[[round((x+83)*1000000),round((y-42)*1000000)] for x,y,*z in p] for p in paths]
  rows.append([oid,n,ps])
 payload={'area':area,'bounds':b,'coordinate_decode':{'lon':'x/1000000-83','lat':'y/1000000+42'},'seed_names':sorted(set(n for f,g,n in seed)),'rows':rows,'source_sha256':hashlib.sha256(raw).hexdigest(),'note':'Public-source diagnostic geometry only; not a territory assignment or replacement drawing.'}
 p=OUT/(area+'.json');p.write_text(json.dumps(payload,separators=(',',':')))
 index.append({'area':area,'bounds':b,'roads':len(rows),'seed_names':payload['seed_names'],'bytes':p.stat().st_size})
(OUT/'INDEX.json').write_text(json.dumps(index,indent=2));print(json.dumps(index,indent=2))
