import copy,hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import sealed

class SealedTests(unittest.TestCase):
    def setUp(self):
        self.key=sealed.new_key();self.session=sealed.new_session();self.raw=b'private Territory - 123.pdf data'
        self.envelope=sealed.seal(self.raw,sealed.public(self.key),self.session,'job')
    def test_roundtrip(self):self.assertEqual(sealed.unseal(self.envelope,self.key,self.session,'job'),self.raw)
    def test_result_roundtrip(self):
        value=sealed.seal(self.raw,sealed.public(self.key),self.session,'result');self.assertEqual(sealed.unseal(value,self.key,self.session,'result'),self.raw)
    def test_no_plaintext_metadata(self):self.assertNotIn('Territory - 123',json.dumps(self.envelope))
    def test_unique_keys(self):self.assertNotEqual(sealed.public(sealed.new_key()),sealed.public(self.key))
    def test_unique_nonces(self):self.assertNotEqual(self.envelope['nonce'],sealed.seal(self.raw,sealed.public(self.key),self.session,'job')['nonce'])
    def test_key_save_reload(self):self.assertEqual(sealed.public(sealed.load_private(sealed.private_bytes(self.key))),sealed.public(self.key))
    def test_bad_private_key(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.load_private(b'bad')
    def test_different_recipient(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(self.envelope,sealed.new_key(),self.session,'job')
    def test_different_session(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(self.envelope,self.key,sealed.new_session(),'job')
    def test_different_purpose(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(self.envelope,self.key,self.session,'result')
    def test_unknown_field(self):
        e={**self.envelope,'approval':True}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_missing_field(self):
        e=self.envelope.copy();del e['nonce']
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_wrong_version(self):
        e={**self.envelope,'version':2}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_bool_version(self):
        e={**self.envelope,'version':True}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_tampered_ciphertext(self):
        raw=bytearray(sealed.unb64(self.envelope['ciphertext']));raw[-1]^=1;e={**self.envelope,'ciphertext':sealed.b64(bytes(raw))}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_tampered_sender(self):
        e={**self.envelope,'sender':sealed.public(sealed.new_key())}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_tampered_nonce(self):
        e={**self.envelope,'nonce':sealed.b64(b'0'*12)}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_bad_base64(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.unb64('!not base64!')
    def test_bad_nonce_length(self):
        e={**self.envelope,'nonce':sealed.b64(b'12')}
        with self.assertRaises(sealed.EnvelopeError):sealed.unseal(e,self.key,self.session,'job')
    def test_invalid_session(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.seal(self.raw,sealed.public(self.key),'../../x','job')
    def test_invalid_purpose(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.seal(self.raw,sealed.public(self.key),self.session,'execute')
    def test_empty_payload(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.seal(b'',sealed.public(self.key),self.session,'job')
    def test_oversized_payload(self):
        with patch.object(sealed,'MAX_RAW',4),self.assertRaises(sealed.EnvelopeError):sealed.seal(self.raw,sealed.public(self.key),self.session,'job')
    def test_invalid_peer_key(self):
        with self.assertRaises(sealed.EnvelopeError):sealed.seal(self.raw,sealed.b64(b'0'),self.session,'job')
    def test_paths(self):
        for value in ['../secret','/etc/passwd','a/../../x','C:/secret','a\\b','a//b','./a','.git/config','a/']:
            with self.subTest(value=value),self.assertRaises(sealed.EnvelopeError):sealed.safe_name(value)
    def test_valid_path(self):self.assertEqual(str(sealed.safe_name('sources/map.pdf')),'sources/map.pdf')
    def test_archive_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'input';root.mkdir();(root/'card.pdf').write_bytes(self.raw)
            out=Path(t)/'output';report=sealed.unpack(sealed.pack(root),out)
            self.assertEqual(report['file_count'],1);self.assertFalse(report['quality_approval']);self.assertEqual((out/'card.pdf').read_bytes(),self.raw)
    def test_fresh_extraction_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'data').write_text('secret')
            with self.assertRaises(sealed.EnvelopeError):sealed.unpack(sealed.pack(root),root)
    def test_symlink_input(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'real').write_text('secret');(root/'link').symlink_to(root/'real')
            with self.assertRaises(sealed.EnvelopeError):sealed.pack(root)
    def test_manifest_reserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'TRANSPORT_MANIFEST.json').write_text('{}')
            with self.assertRaises(sealed.EnvelopeError):sealed.pack(root)
    def test_manifest_tamper(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('a.txt','payload');z.writestr('TRANSPORT_MANIFEST.json',json.dumps({'a.txt':'0'*64}))
        with tempfile.TemporaryDirectory() as t,self.assertRaises(sealed.EnvelopeError):sealed.unpack(out.getvalue(),Path(t)/'out')
    def test_archive_traversal(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('../x',b'data');z.writestr('TRANSPORT_MANIFEST.json',json.dumps({'../x':hashlib.sha256(b'data').hexdigest()}))
        with tempfile.TemporaryDirectory() as t,self.assertRaises(sealed.EnvelopeError):sealed.unpack(out.getvalue(),Path(t)/'out')
    def test_bad_archive(self):
        with tempfile.TemporaryDirectory() as t,self.assertRaises(sealed.EnvelopeError):sealed.unpack(b'not a zip',Path(t)/'out')
    def test_missing_manifest(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('a','b')
        with tempfile.TemporaryDirectory() as t,self.assertRaises(sealed.EnvelopeError):sealed.unpack(out.getvalue(),Path(t)/'out')
    def test_duplicate_manifest_keys(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('a','b');z.writestr('TRANSPORT_MANIFEST.json','{"a":"0","a":"1"}')
        with tempfile.TemporaryDirectory() as t,self.assertRaises(sealed.EnvelopeError):sealed.unpack(out.getvalue(),Path(t)/'out')

if __name__=='__main__':unittest.main()
