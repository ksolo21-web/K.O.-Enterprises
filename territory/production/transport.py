"""GitHub CLI transport restricted to opaque encrypted job paths on one branch."""
from __future__ import annotations
import base64,hashlib,json,os,re,subprocess,urllib.parse
from pathlib import Path
import sealed
REPO='ksolo21-web/K.O.-Enterprises'
BRANCH='territory-card-production'
CHUNK=250_000
class TransportError(RuntimeError):pass
class MissingObject(TransportError):pass
class ProtocolError(TransportError):pass

def validate_envelope(envelope,direction):
    """Validate the current wire format before upload or model work; no key needed."""
    if direction not in ('inputs','outputs'):raise ProtocolError('invalid envelope direction')
    expected={'version','session','purpose','sender','receiver','nonce','ciphertext'}
    if not isinstance(envelope,dict) or set(envelope)!=expected:raise ProtocolError('envelope_schema_invalid')
    try:
        required=sealed.metadata(envelope['session'],'job' if direction=='inputs' else 'result')
        if any(type(envelope[k]) is not type(v) or envelope[k]!=v for k,v in required.items()):raise ProtocolError('envelope_context_invalid')
        if any(len(sealed.unb64(envelope[k],100))!=32 for k in ('sender','receiver')):raise ProtocolError('envelope_key_invalid')
        if len(sealed.unb64(envelope['nonce'],100))!=12:raise ProtocolError('envelope_nonce_invalid')
        if not 16<len(sealed.unb64(envelope['ciphertext']))<=sealed.MAX_RAW+16:raise ProtocolError('envelope_size_invalid')
    except sealed.EnvelopeError as error:raise ProtocolError('envelope_encoding_invalid') from error
    return envelope


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
    if r.returncode:
        if re.search(r'\bHTTP 404\b',r.stderr or ''):raise MissingObject('GitHub object not available')
        raise TransportError('GitHub operation failed; no private request body is logged')
    if len(r.stdout)>70_000_000:raise TransportError('oversized GitHub response')
    return json.loads(r.stdout)

def safe_path(path):
    if not re.fullmatch(r'territory/transport/(requests|visual-requests|sessions|inputs|outputs)/[0-9a-f]{32}(/[A-Za-z0-9.-]+)?',path):raise TransportError('unsafe transport path')
    if any(part in ('.','..') for part in path.split('/')):raise TransportError('unsafe transport path')
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
    """Store ciphertext parts plus a compact hash-bound manifest in one commit.

    The compact manifest avoids a manifest-size explosion when an owner-side connector
    must use many small transport chunks. Integrity remains fail-closed: the receiver
    verifies the exact part count, ordering/schema and SHA-256 of the complete ciphertext,
    and AES-GCM authenticates the decrypted envelope before any private job is processed.
    """
    validate_envelope(envelope,direction)
    session=envelope['session'];sealed.metadata(session,envelope['purpose'])
    if direction not in ('inputs','outputs'):raise TransportError('bad direction')
    root=f'territory/transport/{direction}/{session}';cipher=envelope['ciphertext'];files={};count=0
    for i in range(0,len(cipher),CHUNK):
        name=f'part-{i//CHUNK:04}.json';text=cipher[i:i+CHUNK]
        files[root+'/'+name]={'data':text};count+=1
    header={k:v for k,v in envelope.items() if k!='ciphertext'}
    files[root+'/manifest.json']={'envelope':header,'part_count':count,'ciphertext_sha256':hashlib.sha256(cipher.encode()).hexdigest()}
    return commit(files,'Store opaque encrypted territory '+direction)

def _receive_legacy_manifest(root,manifest):
    header=manifest['envelope'];parts=manifest['parts']
    if not isinstance(parts,list) or not 1<=len(parts)<=200:raise ProtocolError('invalid part count')
    chunks=[]
    for i,part in enumerate(parts):
        if not isinstance(part,dict) or set(part)!={'name','sha256'} or part['name']!=f'part-{i:04}.json':raise ProtocolError('invalid part ordering')
        try:item=read(root+'/'+part['name'])
        except MissingObject as error:raise ProtocolError('complete manifest references a missing part') from error
        if not isinstance(item,dict) or set(item)!={'data'}:raise ProtocolError('invalid part schema')
        value=item['data']
        if not isinstance(value,str) or len(value)>CHUNK or hashlib.sha256(value.encode()).hexdigest()!=part['sha256']:raise ProtocolError('encrypted part identity mismatch')
        chunks.append(value)
    return header,''.join(chunks)

def _receive_compact_manifest(root,manifest):
    header=manifest['envelope'];count=manifest['part_count']
    if type(count) is not int or not 1<=count<=200:raise ProtocolError('invalid part count')
    chunks=[]
    for i in range(count):
        try:item=read(root+f'/part-{i:04}.json')
        except MissingObject as error:raise ProtocolError('complete manifest references a missing part') from error
        if not isinstance(item,dict) or set(item)!={'data'}:raise ProtocolError('invalid part schema')
        value=item['data']
        if not isinstance(value,str) or not value or len(value)>CHUNK:raise ProtocolError('invalid encrypted part')
        chunks.append(value)
    return header,''.join(chunks)

def receive_envelope(session,direction):
    if direction not in ('inputs','outputs'):raise ProtocolError('bad direction')
    purpose='job' if direction=='inputs' else 'result'
    sealed.metadata(session,purpose)
    root=f'territory/transport/{direction}/{session}';manifest=read(root+'/manifest.json')
    if not isinstance(manifest,dict):raise ProtocolError('invalid manifest schema')
    if set(manifest)=={'envelope','parts','ciphertext_sha256'}:
        header,cipher=_receive_legacy_manifest(root,manifest)
    elif set(manifest)=={'envelope','part_count','ciphertext_sha256'}:
        header,cipher=_receive_compact_manifest(root,manifest)
    else:raise ProtocolError('invalid manifest schema')
    fields={'version','session','purpose','sender','receiver','nonce'}
    if not isinstance(header,dict) or set(header)!=fields:raise ProtocolError('envelope_schema_invalid')
    if header.get('session')!=session or header.get('purpose')!=purpose:raise ProtocolError('envelope_context_invalid')
    if not isinstance(manifest['ciphertext_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',manifest['ciphertext_sha256']):raise ProtocolError('invalid encrypted bundle identity')
    if hashlib.sha256(cipher.encode()).hexdigest()!=manifest['ciphertext_sha256']:raise ProtocolError('encrypted bundle identity mismatch')
    return validate_envelope({**header,'ciphertext':cipher},direction)
