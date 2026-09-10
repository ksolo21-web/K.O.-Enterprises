"""Internal transport regression tests; mocked networking is not a live E2E run."""
import base64, hashlib, json, subprocess, unittest
from unittest.mock import patch
import transport as t

class TransportTests(unittest.TestCase):
    def test_repository_identity_endpoint_is_allowed(self):
        done=subprocess.CompletedProcess([],0,json.dumps({'full_name':t.REPO,'private':False}),'')
        with patch.object(t.subprocess,'run',return_value=done) as run:
            self.assertEqual(t.api('repos/'+t.REPO)['full_name'],t.REPO)
            self.assertEqual(run.call_args.args[0][2],'repos/'+t.REPO)
    def test_other_repository_is_blocked(self):
        for endpoint in ('repos/another/repo','repos/'+t.REPO+'-other','repos/'+t.REPO+'-other/git/ref/heads/main'):
            with self.subTest(endpoint=endpoint),self.assertRaises(t.TransportError):t.api(endpoint)
    def test_path_traversal_is_blocked(self):
        for endpoint in ('repos/'+t.REPO+'/../other','repos/'+t.REPO+'/%2e%2e/other','repos/'+t.REPO+'/git\\other'):
            with self.subTest(endpoint=endpoint),self.assertRaises(t.TransportError):t.api(endpoint)
    def test_transport_path_is_confined(self):
        for path in ('main','territory/production/a.py','territory/transport/requests/../x','territory/transport/inputs/'+'a'*32+'/../../x'):
            with self.subTest(path=path),self.assertRaises(t.TransportError):t.safe_path(path)
    def test_network_error_does_not_expose_private_body(self):
        done=subprocess.CompletedProcess([],1,'','SECRET PRIVATE INPUT')
        with patch.object(t.subprocess,'run',return_value=done):
            with self.assertRaises(t.TransportError) as error:t.api('repos/'+t.REPO,{'private':'SECRET PRIVATE INPUT'})
            self.assertNotIn('SECRET',str(error.exception))
    def test_commit_preserves_base_and_never_forces_main(self):
        calls=[]
        def fake(endpoint,data=None,method=None):
            calls.append((endpoint,data,method))
            if endpoint=='repos/'+t.REPO:return {'full_name':t.REPO,'private':False}
            if endpoint.endswith('/git/blobs'):
                b=base64.b64decode(data['content']);return {'sha':hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()}
            if '/git/ref/heads/' in endpoint:return {'object':{'sha':'a'*40}}
            if endpoint.endswith('/git/commits/'+'a'*40):return {'tree':{'sha':'b'*40}}
            if endpoint.endswith('/git/trees'):
                self.assertEqual(data['base_tree'],'b'*40);return {'sha':'c'*40}
            if endpoint.endswith('/git/commits'):
                self.assertEqual(data['parents'],['a'*40]);return {'sha':'d'*40}
            if '/git/refs/heads/' in endpoint:
                self.assertTrue(endpoint.endswith('/'+t.BRANCH));self.assertEqual(data,{'sha':'d'*40,'force':False});return {}
            raise AssertionError(endpoint)
        with patch.object(t,'api',side_effect=fake):
            self.assertEqual(t.commit({'territory/transport/requests/'+'a'*32:{'public':'synthetic'}},'test'),'d'*40)
        self.assertFalse(any('/heads/main' in c[0] for c in calls))
    def test_private_repository_blocks_upload(self):
        with patch.object(t,'api',return_value={'full_name':t.REPO,'private':True}),self.assertRaises(t.TransportError):
            t.commit({'territory/transport/requests/'+'a'*32:{}},'test')
    def test_wrong_repository_identity_blocks_upload(self):
        with patch.object(t,'api',return_value={'full_name':'not/the-owner','private':False}),self.assertRaises(t.TransportError):
            t.commit({'territory/transport/requests/'+'a'*32:{}},'test')
    def test_ciphertext_chunk_roundtrip(self):
        import sealed
        key=sealed.new_key();session=sealed.new_session();envelope=sealed.seal(b'complete synthetic exchange',sealed.public(key),session,'job');store={}
        with patch.object(t,'commit',side_effect=lambda files,message:store.update(files)):
            t.send_envelope(envelope,'inputs')
        with patch.object(t,'read',side_effect=lambda name:store[name]):
            got=t.receive_envelope(session,'inputs')
        self.assertEqual(sealed.unseal(got,key,session,'job'),b'complete synthetic exchange')
    def test_corrupt_chunk_is_rejected(self):
        import sealed
        key=sealed.new_key();session=sealed.new_session();envelope=sealed.seal(b'synthetic',sealed.public(key),session,'job');store={}
        with patch.object(t,'commit',side_effect=lambda files,message:store.update(files)):t.send_envelope(envelope,'inputs')
        part=next(k for k in store if 'part-' in k);store[part]['data']=('B' if store[part]['data'][0]=='A' else 'A')+store[part]['data'][1:]
        with patch.object(t,'read',side_effect=lambda name:store[name]),self.assertRaises(t.TransportError):t.receive_envelope(session,'inputs')

if __name__=='__main__':unittest.main()
