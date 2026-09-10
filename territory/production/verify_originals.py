"""Check the pinned source capsule and installed file bytes without adapter assumptions."""
from pathlib import Path
import hashlib
import json
import zipfile

ARCHIVE_SHA256='49809b315b7dd9939912eca9a716a196abc67a8e649e74c44e1613d5cbc5deb9'
MANIFEST_SHA256='00760b2cbcf8deaf1f2a1d288f470174eaa0840d350568d9287c1a58db242c83'

def verify_capsule(home: Path) -> dict:
    archive=home/'Territory-Skills-Source-Capsule.zip'
    digest=lambda b:hashlib.sha256(b).hexdigest()
    if digest(archive.read_bytes())!=ARCHIVE_SHA256:
        raise ValueError('Original source archive identity differs')
    with zipfile.ZipFile(archive) as z:
        raw=z.read('manifest.json')
        if digest(raw)!=MANIFEST_SHA256:raise ValueError('Original manifest identity differs')
        manifest=json.loads(raw)
        if len(manifest['files'])!=138:raise ValueError('Wrong original source count')
        if len(z.namelist())!=139 or set(z.namelist())!=set(manifest['files'])|{'manifest.json'}:
            raise ValueError('Source archive inventory differs')
        for name,checksum in manifest['files'].items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name:
                raise ValueError('Unconfined original source path')
            if digest(z.read(name))!=checksum:raise ValueError('Archived original differs: '+name)
    return {'passed':True,'verified_files':138,'archive_sha256':ARCHIVE_SHA256,
            'archive_manifest_sha256':MANIFEST_SHA256}

def verify_installed(home: Path) -> dict:
    result=verify_capsule(home)
    with zipfile.ZipFile(home/'Territory-Skills-Source-Capsule.zip') as z:
        manifest=json.loads(z.read('manifest.json'))
    for name,checksum in manifest['files'].items():
        installed=home/'vendor'/name
        if installed.is_symlink() or not installed.is_file():
            raise ValueError('Missing or unsafe installed original: '+name)
        if hashlib.sha256(installed.read_bytes()).hexdigest()!=checksum:
            raise ValueError('Installed original differs: '+name)
    index=json.loads((home/'skills-manifest.json').read_text())
    indexed=index.get('files',index)
    if indexed!=manifest['files']:
        raise ValueError('Installed source index does not match the original inventory')
    if 'file_count' in index and index['file_count']!=138:
        raise ValueError('Installed source count differs')
    return {**result,'installed_originals_verified':138}
