"""Ephemeral, authenticated private-job envelopes; never stores a permanent cloud key."""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import zipfile
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAX_RAW=32_000_000
MAX_FILE=16_000_000
MAX_FILES=2000
VERSION=1
class EnvelopeError(ValueError): pass
_AUTHENTICATED=object()
class AuthenticatedPayload(bytes):
    def __new__(cls,value,proof=None):
        if proof is not _AUTHENTICATED:raise EnvelopeError('decryption proof required')
        return super().__new__(cls,value)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def b64(raw): return base64.b64encode(raw).decode('ascii')
def unb64(value, limit=MAX_RAW*2):
    if not isinstance(value,str) or len(value)>limit: raise EnvelopeError('invalid envelope field')
    try:return base64.b64decode(value,validate=True)
    except (ValueError,TypeError) as error:raise EnvelopeError('invalid base64') from error

def new_key(): return X25519PrivateKey.generate()
def public(key):
    return b64(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
def private_bytes(key):
    return key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
def load_private(raw):
    if len(raw)!=32:raise EnvelopeError('invalid private key')
    return X25519PrivateKey.from_private_bytes(raw)

def new_session(): return secrets.token_hex(16)
def metadata(session,purpose):
    if not isinstance(session,str) or not re.fullmatch(r'[0-9a-f]{32}',session):raise EnvelopeError('invalid session')
    if purpose not in ('job','result'):raise EnvelopeError('invalid purpose')
    return {'version':VERSION,'session':session,'purpose':purpose}

def derive(key, peer, header):
    try:
        raw=unb64(peer,100)
        if len(raw)!=32:raise EnvelopeError('invalid public key')
        shared=key.exchange(X25519PublicKey.from_public_bytes(raw))
        return HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b'territory-sealed-v1\0'+canonical(header)).derive(shared)
    except (ValueError,TypeError) as error:raise EnvelopeError('invalid peer key') from error

def seal(raw:bytes,receiver_public:str,session:str,purpose:str) -> dict:
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_RAW:raise EnvelopeError('payload outside bounds')
    sender=new_key();header=metadata(session,purpose)
    header['sender']=public(sender);header['receiver']=receiver_public
    nonce=os.urandom(12);cipher=AESGCM(derive(sender,receiver_public,header)).encrypt(nonce,raw,canonical(header))
    return {**header,'nonce':b64(nonce),'ciphertext':b64(cipher)}

def unseal(envelope:dict,receiver,session:str,purpose:str) -> bytes:
    expected={'version','session','purpose','sender','receiver','nonce','ciphertext'}
    if not isinstance(envelope,dict) or set(envelope)!=expected:raise EnvelopeError('unexpected envelope fields')
    required=metadata(session,purpose)
    if any(type(envelope[k]) is not type(v) or envelope[k]!=v for k,v in required.items()):raise EnvelopeError('envelope context mismatch')
    if envelope['receiver']!=public(receiver):raise EnvelopeError('wrong receiver')
    header={k:envelope[k] for k in ('version','session','purpose','sender','receiver')}
    nonce=unb64(envelope['nonce'],100);cipher=unb64(envelope['ciphertext'])
    if len(nonce)!=12 or not 16<len(cipher)<=MAX_RAW+16:raise EnvelopeError('invalid ciphertext size')
    try:raw=AESGCM(derive(receiver,envelope['sender'],header)).decrypt(nonce,cipher,canonical(header))
    except Exception as error:raise EnvelopeError('authentication failed') from error
    if len(raw)>MAX_RAW:raise EnvelopeError('payload too large')
    return AuthenticatedPayload(raw,_AUTHENTICATED)

def safe_name(name):
    if not isinstance(name,str) or '\\' in name or '\0' in name or ':' in name:raise EnvelopeError('unsafe archive path')
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(x in ('..','.') for x in p.parts) or p.as_posix()!=name:raise EnvelopeError('unsafe archive path')
    if any(x.startswith('.') for x in p.parts):raise EnvelopeError('hidden paths are not job data')
    return p

def pack(root:Path) -> bytes:
    root=root.resolve();members={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise EnvelopeError('symlink in job')
        if not p.is_file():continue
        name=p.relative_to(root).as_posix();safe_name(name)
        raw=p.read_bytes()
        if len(raw)>MAX_FILE:raise EnvelopeError('job member too large')
        members[name]=raw
    if not members or len(members)>MAX_FILES or sum(map(len,members.values()))>MAX_RAW:raise EnvelopeError('job size outside bounds')
    if 'TRANSPORT_MANIFEST.json' in members:raise EnvelopeError('reserved manifest name')
    manifest={n:hashlib.sha256(v).hexdigest() for n,v in members.items()}
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in members.items():z.writestr(name,raw)
        z.writestr('TRANSPORT_MANIFEST.json',canonical(manifest))
    data=out.getvalue()
    if len(data)>MAX_RAW:raise EnvelopeError('archive too large')
    return data

def unpack(raw:bytes,target:Path) -> dict:
    if not isinstance(raw,bytes) or len(raw)>MAX_RAW:raise EnvelopeError('archive too large')
    if target.exists():raise EnvelopeError('fresh extraction directory required')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos=z.infolist();names=[v.filename for v in infos]
            if len(names)!=len(set(names)) or not 1<len(names)<=MAX_FILES+1:raise EnvelopeError('duplicate or excessive members')
            if 'TRANSPORT_MANIFEST.json' not in names:raise EnvelopeError('missing transport manifest')
            if any(v.file_size>MAX_FILE or v.flag_bits&1 for v in infos) or sum(v.file_size for v in infos)>MAX_RAW:raise EnvelopeError('excessive or encrypted archive members')
            for info in infos:
                safe_name(info.filename)
                if info.is_dir() or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG):raise EnvelopeError('nonregular archive member')
            def unique(pairs):
                d={}
                for k,v in pairs:
                    if k in d:raise EnvelopeError('duplicate manifest key')
                    d[k]=v
                return d
            manifest=json.loads(z.read('TRANSPORT_MANIFEST.json'),object_pairs_hook=unique)
            if not isinstance(manifest,dict) or set(manifest)!=set(names)-{'TRANSPORT_MANIFEST.json'}:raise EnvelopeError('manifest membership mismatch')
            data={name:z.read(name) for name in manifest}
            for name,value in data.items():
                if hashlib.sha256(value).hexdigest()!=manifest[name]:raise EnvelopeError('member hash mismatch')
    except EnvelopeError:raise
    except Exception as error:raise EnvelopeError('invalid job archive') from error
    target.mkdir(parents=True,mode=0o700)
    try:
        for name,value in data.items():
            p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value);p.chmod(0o600)
    except Exception:
        import shutil
        shutil.rmtree(target,ignore_errors=True)
        raise
    return {'file_count':len(data),'transport_integrity':True,'quality_approval':False}
