"""Generated envelope fixtures; no remote data or credentials used."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import delivery,sealed

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'returned'/ 'result.encrypted.json'
        self.sid=sealed.new_session();self.key=sealed.new_key()
        self.envelope=sealed.seal(b'only a generated integration fixture',sealed.public(self.key),self.sid,'result')
        self.request={'version':1,'session':self.sid,'reply_public_key':sealed.public(self.key)}
        self.reader=patch.object(delivery.transport,'read',return_value=self.request).start()
        self.receiver=patch.object(delivery.transport,'receive_envelope',return_value=self.envelope).start()
        self.addCleanup(patch.stopall)
    def test_exact_call_order_and_round_trip(self):
        result=delivery.mirror(self.sid,self.path)
        self.receiver.assert_called_once_with(self.sid,'outputs')
        self.reader.assert_called_once_with('territory/transport/requests/'+self.sid)
        self.assertFalse(result['content_decrypted']);self.assertFalse(result['card_release_authorized'])
        self.assertEqual(sealed.unseal(json.loads(self.path.read_text()),self.key,self.sid,'result'),b'only a generated integration fixture')
    def reject(self):
        with self.assertRaises((delivery.DeliveryError,sealed.EnvelopeError)):
            delivery.mirror(self.sid,self.path)
        self.assertFalse(self.path.exists())
    def test_wrong_envelope_session(self): self.envelope['session']=sealed.new_session();self.reject()
    def test_wrong_purpose(self): self.envelope['purpose']='job';self.reject()
    def test_wrong_receiver(self): self.envelope['receiver']=sealed.public(sealed.new_key());self.reject()
    def test_missing_field(self): del self.envelope['sender'];self.reject()
    def test_extra_field(self): self.envelope['plaintext']='not allowed';self.reject()
    def test_boolean_version(self): self.envelope['version']=True;self.reject()
    def test_wrong_request_session(self): self.request['session']=sealed.new_session();self.reject()
    def test_wrong_request_version(self): self.request['version']=True;self.reject()
    def test_short_nonce(self): self.envelope['nonce']=sealed.b64(b'abcd');self.reject()
    def test_short_sender(self): self.envelope['sender']=sealed.b64(b'abcd');self.reject()
    def test_invalid_cipher_encoding(self): self.envelope['ciphertext']='not valid$$';self.reject()
    def test_oversized_envelope(self): self.envelope['ciphertext']='A'*2_000_001;self.reject()
    def test_existing_file_is_preserved(self):
        self.path.parent.mkdir();self.path.write_bytes(b'owner data')
        with self.assertRaises(delivery.DeliveryError): delivery.mirror(self.sid,self.path)
        self.assertEqual(self.path.read_bytes(),b'owner data');self.receiver.assert_not_called()
    def test_symlink_is_preserved(self):
        self.path.parent.mkdir();self.path.symlink_to(Path(self.tmp.name)/'missing')
        with self.assertRaises(delivery.DeliveryError): delivery.mirror(self.sid,self.path)
        self.assertTrue(self.path.is_symlink());self.receiver.assert_not_called()
    def test_invalid_session_no_remote_read(self):
        with self.assertRaises(sealed.EnvelopeError): delivery.mirror('../main',self.path)
        self.reader.assert_not_called()

if __name__=='__main__':unittest.main()
