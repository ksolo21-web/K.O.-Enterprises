#!/usr/bin/env python3
"""Reassemble the exact, immutable 138-file skill archive. No model or network.
The compressed transfer, manifest, every file and rebuilt ZIP must all match.
This is source preservation, never approval of a territory card.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

PACKED_SHA = 'ca279cf593c915a32889fc25d428d9fccb00cee8de64a53b7183ac4594ee4e80'
MANIFEST_SHA = '00760b2cbcf8deaf1f2a1d288f470174eaa0840d350568d9287c1a58db242c83'
ARCHIVE_SHA = '49809b315b7dd9939912eca9a716a196abc67a8e649e74c44e1613d5cbc5deb9'

class SourceError(RuntimeError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise SourceError('Duplicate source key')
        out[key] = value
    return out

def assemble(parts: Path, output: Path) -> dict:
    names = [f'part-{i:02}.txt' for i in range(1, 40)]
    if {p.name for p in parts.glob('part-*.txt')} != set(names):
        raise SourceError('All and only 39 source segments are required')
    chunks = []
    for i, name in enumerate(names):
        path = parts / name
        if path.is_symlink() or not path.is_file():
            raise SourceError('Source segment is missing or a symlink')
        if path.stat().st_size != (2368 if i == 38 else 6000):
            raise SourceError('Source segment size differs')
        chunks.append(path.read_bytes())
    packed = base64.b64decode(b''.join(chunks), validate=True)
    if len(packed) != 172776 or digest(packed) != PACKED_SHA:
        raise SourceError('Compressed source identity differs')
    decoder = lzma.LZMADecompressor(memlimit=128*1024*1024)
    raw = decoder.decompress(packed, max_length=2_000_001)
    if not decoder.eof or decoder.unused_data or len(raw) != 1259575:
        raise SourceError('Decoded source size or stream differs')
    files = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(files, dict) or len(files) != 139:
        raise SourceError('Source member count differs')
    manifest_raw = files['manifest.json'].encode('utf-8')
    if digest(manifest_raw) != MANIFEST_SHA:
        raise SourceError('Original manifest differs')
    manifest = json.loads(manifest_raw, object_pairs_hook=unique)
    expected = manifest['files']
    if len(expected) != 138 or list(files) != ['manifest.json', *sorted(expected)]:
        raise SourceError('Original source member set or order differs')
    for name, text in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name
                or ':' in name or not isinstance(text, str)):
            raise SourceError('Invalid original source path or encoding')
        if name != 'manifest.json' and digest(text.encode('utf-8')) != expected[name]:
            raise SourceError('An original source file differs')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 8, 17, 41, 20))
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(info, text.encode('utf-8'),
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = buffer.getvalue()
    if len(data) != 419980 or digest(data) != ARCHIVE_SHA:
        raise SourceError('Rebuilt original ZIP differs; no output is permitted')
    if output.is_symlink():
        raise SourceError('Output is a symlink')
    if output.exists():
        if output.read_bytes() != data:
            raise SourceError('Existing archive differs; refusing to overwrite')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        try:
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    return {'verified_source_files': 138, 'verified_segments': 39,
            'archive_sha256': digest(output.read_bytes()), 'archive_bytes': len(data),
            'source_integrity': True, 'card_release_authorized': False}

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    print(json.dumps(assemble(root, root.parent/'production'/'Territory-Skills-Source-Capsule.zip')))
