"""Strict observed C2PA delivery envelope; no operation PDF replay exception.

Caller must separately replay the hash-bound operation PDF through its existing
contract. This proves only delivery custody, not C2PA authenticity or release.
"""
from pathlib import Path
import hashlib
import re
import fitz

def require(ok, message):
    if not ok:
        raise ValueError(message)

def verify_delivery(operation_path, delivery_path):
    original = Path(operation_path).read_bytes()
    saved = Path(delivery_path).read_bytes()
    digest = lambda data: hashlib.sha256(data).hexdigest()
    require(saved.startswith(original), 'operation PDF must be exact byte prefix')
    if saved == original:
        return {'kind': 'identical_bytes', 'operation_sha256': digest(original), 'delivery_sha256': digest(saved)}
    with fitz.open(stream=original, filetype='pdf') as a, fitz.open(stream=saved, filetype='pdf') as b:
        require(not a.is_repaired and not b.is_repaired and not a.is_encrypted and not b.is_encrypted, 'repaired/encrypted PDF unsupported')
        n, cat = a.xref_length(), a.pdf_catalog()
        require(b.xref_length() == n + 2 and b.pdf_catalog() == cat, 'exact two metadata objects required')
        require(a.xref_get_key(-1, 'Root') == ('xref', f'{cat} 0 R'), 'only generation-zero original catalog supported')
        require(not {'AF', 'Names'} & set(a.xref_get_keys(cat)), 'existing associated files unsupported')
        old_start = re.search(rb'startxref\s+(\d+)\s+%%EOF\s*\Z', original)
        require(old_start is not None, 'original startxref')
        tail = saved[len(original):]
        # Only these three physical objects in one update, with bounded stream.
        head = re.match(fr'{cat} 1 obj\n(<<[^\x00]*?>>)\nendobj\n{n} 0 obj\n<< /Length ([0-9]+) /F << /Subtype \(application/c2pa\) /Length ([0-9]+) >> >>\nstream\n'.encode(), tail)
        require(head is not None, 'unsupported incremental object layout')
        original_catalogs = list(re.finditer(fr'(?:^|\n){cat} 0 obj\n(<<[^\x00]*?>>)\nendobj'.encode(), original))
        require(len(original_catalogs) == 1, 'single original catalog serialization required')
        original_catalog = original_catalogs[0][1]
        expected_catalog = original_catalog[:-2] + (f' /AF [{n+1} 0 R] /Names << /EmbeddedFiles << /Names [(Content Credentials) {n+1} 0 R] >> >> >>').encode()
        require(head[1] == expected_catalog, 'exact catalog serialization plus only delivery keys')
        length = int(head[2]); require(length == int(head[3]) and 30 <= length <= 16_000_000, 'manifest length')
        payload = tail[head.end():head.end()+length]
        require(len(payload) == length and int.from_bytes(payload[:4], 'big') == length and payload[4:8] == b'jumb' and payload[12:20] == b'jumdc2pa', 'C2PA JUMBF envelope')
        stream_end = head.end()+length
        filespec = (f'\nendstream\nendobj\n{n+1} 0 obj\n<< /AFRelationship /C2PA_Manifest /Desc (Content Credentials) /F (Content Credentials) /EF << /F {n} 0 R >> /Subtype (application/c2pa) /Type /FileSpec /UF (Content Credentials) >>\nendobj\n').encode()
        require(tail[stream_end:stream_end+len(filespec)] == filespec, 'exact inert C2PA filespec')
        xref_offset = len(original)+stream_end+len(filespec)
        stream_offset = len(original)+head.start()+head[0].index(f'{n} 0 obj\n'.encode())
        file_offset = len(original)+stream_end+len(b'\nendstream\nendobj\n')
        expected_xref = (f'xref\n{cat} 1\n{len(original):010d} 00001 n \n{n} 2\n{stream_offset:010d} 00000 n \n{file_offset:010d} 00000 n \ntrailer\n').encode()
        remainder = saved[xref_offset:]
        require(remainder.startswith(expected_xref), 'exact incremental xref offsets/generations')
        trailer = remainder[len(expected_xref):]
        require(re.fullmatch(rb'<< /Size '+str(n+2).encode()+rb' /Root '+str(cat).encode()+rb' 1 R /Prev '+old_start[1]+rb' /ID \[<[0-9A-Fa-f]+><[0-9A-Fa-f]+>\] >>\nstartxref\n'+str(xref_offset).encode()+rb'\n%%EOF\n\n?', trailer) is not None, 'single exact trailer; no arbitrary appended updates')
        require(a.xref_get_key(-1,'ID') == b.xref_get_key(-1,'ID'), 'document ID custody')
        require(set(b.xref_get_keys(cat)) == set(a.xref_get_keys(cat)) | {'AF','Names'}, 'catalog key allowlist')
        require(b.xref_get_key(cat,'AF') == ('array', f'[{n+1} 0 R]'), 'AF binding')
        require(b.xref_get_key(cat,'Names') == ('dict', f'<</EmbeddedFiles<</Names[(Content Credentials){n+1} 0 R]>>>>'), 'embedded files binding')
        for i in range(1,n):
            if i == cat:
                require(all(a.xref_get_key(i,k) == b.xref_get_key(i,k) for k in a.xref_get_keys(i)), 'original catalog entries custody')
            else:
                require(a.xref_object(i) == b.xref_object(i), f'original object {i} custody')
            require(a.xref_stream_raw(i) == b.xref_stream_raw(i), f'raw stream {i} custody')
        require(len(a) == len(b), 'page count')
        renders=[]
        for pa,pb in zip(a,b):
            require(pa.get_text('rawdict') == pb.get_text('rawdict') and pa.get_drawings(extended=True) == pb.get_drawings(extended=True), 'text/native/layer custody')
            require(pa.get_image_info(hashes=True,xrefs=True) == pb.get_image_info(hashes=True,xrefs=True), 'image custody')
            require(pa.get_links() == pb.get_links() and list(pa.annot_xrefs()) == list(pb.annot_xrefs()), 'links/annotations custody')
            for scale in (1,2,4,8):
                x,y = [p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=True,annots=True) for p in (pa,pb)]
                require((x.width,x.height,x.n,x.samples) == (y.width,y.height,y.n,y.samples), f'render custody {scale}x')
                renders.append({'page':pa.number,'scale':scale,'sha256':digest(x.samples)})
        return {'kind':'strict_c2pa_incremental','operation_sha256':digest(original),'delivery_sha256':digest(saved),'original_object_count':n,'new_metadata_objects':[n,n+1],'renders':renders,'release_approval':False}
