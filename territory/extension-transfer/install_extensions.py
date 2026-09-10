#!/usr/bin/env python3
"""Install the pinned candidate extensions without replacing changed work.
Original vendor sources and release rules are never rewritten by this installer.
"""
from pathlib import Path
import base64,hashlib,json,lzma,os,tempfile
PACKED_SHA='7b6e08b6345a3263bdfb4debc5972a111ae95c99245a3f4101dbc16b7c9800d4'
NAMES={'batch.py','client.py','privacy.py','readiness.py','repair.py','sealed.py',
       'transport.py','worker.py','verify_originals.py','test_privacy.py',
       'test_readiness.py','test_repair.py','test_sealed.py','test_transport.py',
       'audit_kit.py','requirements.txt'}
class InstallError(RuntimeError):pass

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise InstallError('duplicate payload key')
        result[key]=value
    return result

def gitsha(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def sha(data):return hashlib.sha256(data).hexdigest()

def install(parts,root):
    parts=Path(parts);root=Path(root)
    expected={f'part-{i:02}.txt' for i in range(1,6)}
    if {p.name for p in parts.glob('part-*.txt')}!=expected:raise InstallError('five exact segments required')
    chunks=[]
    for i,name in enumerate(sorted(expected)):
        path=parts/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=(396 if i==4 else 6000):raise InstallError('segment identity differs')
        chunks.append(path.read_bytes())
    packed=base64.b64decode(b''.join(chunks),validate=True)
    if len(packed)!=18296 or sha(packed)!=PACKED_SHA:raise InstallError('pinned compressed payload differs')
    decoder=lzma.LZMADecompressor(memlimit=128*1024*1024)
    raw=decoder.decompress(packed,max_length=71071)
    if not decoder.eof or decoder.unused_data or len(raw)!=71070:raise InstallError('payload stream differs')
    data=json.loads(raw,object_pairs_hook=unique)
    if data['schema_version']!=1 or set(data['new_files'])!=NAMES or set(data['patches'])!={'engine.py'}:raise InstallError('unexpected install scope')
    staged={}
    for name,text in data['new_files'].items():
        if not isinstance(text,str):raise InstallError('invalid file encoding')
        if name=='test_repair.py':
            before='    def setUp(self):\n'
            after="    def setUp(self):\n        # These generated fixtures exercise local repairs; test_cloud_input_guard\n        # separately verifies that unauthenticated public CI remains blocked.\n        local=patch.dict('os.environ',{'GITHUB_ACTIONS':'false'})\n        local.start();self.addCleanup(local.stop)\n"
            if text.count(before)!=1:raise InstallError('synthetic fixture baseline changed')
            text=text.replace(before,after,1)
            if sha(text.encode())!='b407e76728f013009a0a68df4db5a91a91586c30970fc06bebd5ae708b44cd00':raise InstallError('fixture isolation patch differs')
        new=text.encode();target=root/name
        if target.is_symlink():raise InstallError('symlink target blocked')
        if target.exists():
            old=target.read_bytes()
            if old!=new and gitsha(old)!=data['existing_files'].get(name):raise InstallError('existing file changed: '+name)
        staged[name]=new
    for name,patch in data['patches'].items():
        target=root/name
        if target.is_symlink() or not target.is_file():raise InstallError('engine baseline missing')
        old=target.read_bytes()
        if sha(old)==patch['after_sha256']:staged[name]=old;continue
        if gitsha(old)!=patch['before_git_blob'] or old.count(patch['old'].encode())!=1:raise InstallError('engine changed; patch requires reconciliation')
        new=old.replace(patch['old'].encode(),patch['new'].encode(),1)
        if sha(new)!=patch['after_sha256']:raise InstallError('patched engine identity differs')
        staged[name]=new
    # Validate every target before writing any. A restart can safely finish identical files.
    root.mkdir(parents=True,exist_ok=True)
    for name,new in staged.items():
        if (root/name).exists() and (root/name).read_bytes()==new:continue
        with tempfile.NamedTemporaryFile(dir=root,delete=False) as f:
            temp=Path(f.name);f.write(new)
        try:os.chmod(temp,0o644);temp.replace(root/name)
        finally:temp.unlink(missing_ok=True)
    for name,new in staged.items():
        if (root/name).read_bytes()!=new:raise InstallError('installed bytes differ')
    return {'installed_files':len(staged),'sha256':{k:sha(v) for k,v in staged.items()},'card_release_authorized':False}

if __name__=='__main__':
    parts=Path(__file__).resolve().parent
    print(json.dumps(install(parts,parts.parent/'production'),indent=2))
