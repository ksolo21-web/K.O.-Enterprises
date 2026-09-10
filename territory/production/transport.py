"""GitHub CLI transport restricted to opaque encrypted job paths on one branch."""
from __future__ import annotations
import base64,hashlib,json,os,re,subprocess,urllib.parse
from pathlib import Path
import sealed
REPO='ksolo21-web/K.O.-Enterprises'
BRANCH='territory-card-production'
CHUNK=250_000
class TransportError(RuntimeError):pass

def api(endpoint,data=None,method=None):
    base='repos/'+REPO
    if endpoint!=base and not endpoint.startswith(base+'/'):raise TransportError('endpoint outside the approved repository')
    decoded=urllib.parse.unquote(endpoint.split('?',1)[0])
    if any(v in ('.','..') for v in decoded.split('/')) or '\\' in decoded:raise TransportError('noncanonical API path')
    args=['gh','api',endpoint,'--hostname','github.com']
    if method:args+=['--method',method]
    raw=None
    if data is not None:
        args+=['--input','-'];raw=json.dumps(data,allow_nan=False)
        if method is None:args+=['--method','POST']
    try:r=subprocess.run(args,input=raw,capture_output=True,text=True,timeout=60,env={**os.environ,'GH_HOST':'github.com','GH_PROMPT_DISABLED':'1'})
    except (OSError,subprocess.TimeoutExpired) as error:raise TransportError('GitHub transport unavailable') from error
    if r.returncode:raise TransportError('GitHub operation failed; no private request body is logged')
    if len(r.stdout)>70_000_000:raise TransportError('oversized GitHub response')
    return json.loads(r.stdout)

def safe_path(path):
    if not re.fullmatch(r'territory/transport/(requests|sessions|inputs|outputs)/[0-9a-f]{32}(/[A-Za-z0-9.-]+)?',path):raise TransportError('unsafe transport path')
    return path

def read(path):
    path=safe_path(path);entry=api(f'repos/{REPO}/contents/{path}?ref={BRANCH}')
    if entry.get('type')!='file' or entry.get('encoding')!='base64':raise TransportError('invalid transport object')
    return json.loads(base64.b64decode(entry['content'],validate=False))

def commit(files,message):
    for name in files:safe_path(name)
    repo=api(f'repos/{REPO}')
    if repo.get('full_name')!=REPO or repo.get('private') is not False:raise TransportError('repository identity or public standard-runner zero-spend condition changed')
    entries=[]
    for name,value in files.items():
        raw=sealed.canonical(value);blob=api(f'repos/{REPO}/git/blobs',{'content':base64.b64encode(raw).decode(),'encoding':'base64'})
        if blob['sha']!=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest():raise TransportError('uploaded blob identity mismatch')
        entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
    base=api(f'repos/{REPO}/git/ref/heads/{BRANCH}')['object']['sha']
    tree=api(f'repos/{REPO}/git/commits/{base}')['tree']['sha']
    new=api(f'repos/{REPO}/git/trees',{'base_tree':tree,'tree':entries})
    commit=api(f'repos/{REPO}/git/commits',{'message':message,'tree':new['sha'],'parents':[base]})
    api(f'repos/{REPO}/git/refs/heads/{BRANCH}',{'sha':commit['sha'],'force':False},'PATCH')
    return commit['sha']

def send_envelope(envelope,direction):
    session=envelope['session'];sealed.metadata(session,envelope['purpose'])
    if direction not in ('inputs','outputs'):raise TransportError('bad direction')
    root=f'territory/transport/{direction}/{session}';cipher=envelope['ciphertext'];files={};parts=[]
    for i in range(0,len(cipher),CHUNK):
        name=f'part-{i//CHUNK:04}.json';text=cipher[i:i+CHUNK]
        files[root+'/'+name]={'data':text};parts.append({'name':name,'sha256':hashlib.sha256(text.encode()).hexdigest()})
    header={k:v for k,v in envelope.items() if k!='ciphertext'}
    files[root+'/manifest.json']={'envelope':header,'parts':parts,'ciphertext_sha256':hashlib.sha256(cipher.encode()).hexdigest()}
    return commit(files,'Store opaque encrypted territory '+direction)

def receive_envelope(session,direction):
    sealed.metadata(session,'job' if direction=='inputs' else 'result')
    if direction not in ('inputs','outputs'):raise TransportError('bad direction')
    root=f'territory/transport/{direction}/{session}';manifest=read(root+'/manifest.json');parts=manifest['parts']
    if not isinstance(parts,list) or not 1<=len(parts)<=200:raise TransportError('invalid part count')
    chunks=[]
    for i,part in enumerate(parts):
        if part['name']!=f'part-{i:04}.json':raise TransportError('invalid part ordering')
        value=read(root+'/'+part['name'])['data']
        if not isinstance(value,str) or len(value)>CHUNK or hashlib.sha256(value.encode()).hexdigest()!=part['sha256']:raise TransportError('encrypted part identity mismatch')
        chunks.append(value)
    cipher=''.join(chunks)
    if hashlib.sha256(cipher.encode()).hexdigest()!=manifest['ciphertext_sha256']:raise TransportError('encrypted bundle identity mismatch')
    envelope={**manifest['envelope'],'ciphertext':cipher}
    if envelope['session']!=session:raise TransportError('session mismatch')
    return envelope
