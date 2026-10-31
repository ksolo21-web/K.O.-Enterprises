"""Offline checksum-gate tests; not a model installation or live inference."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from scripts import verify_pinned_ollama as pin

class PinnedOllamaTests(unittest.TestCase):
    def test_pin_contains_frozen_upstream_asset(self):
        self.assertEqual(pin.OLLAMA_RELEASE,'v0.40.13')
        self.assertTrue(pin.OLLAMA_ASSET_URL.endswith('/v0.40.13/ollama-linux-amd64.tar.zst'))
        self.assertEqual(len(pin.OLLAMA_SHA256),64)
        self.assertGreater(pin.OLLAMA_SIZE_BYTES,1_000_000_000)

    def test_verified_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'fixture.bin';f.write_bytes(b'controlled-test-fixture')
            with patch.object(pin,'OLLAMA_SIZE_BYTES',f.stat().st_size), patch.object(pin,'OLLAMA_SHA256',hashlib.sha256(f.read_bytes()).hexdigest()):
                self.assertEqual(pin.verify_archive(f)['status'],'VERIFIED')

    def test_tampered_archive_fails_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'fixture.bin';f.write_bytes(b'a')
            with patch.object(pin,'OLLAMA_SIZE_BYTES',1), patch.object(pin,'OLLAMA_SHA256',hashlib.sha256(b'b').hexdigest()):
                with self.assertRaisesRegex(pin.VerificationError,'SHA-256 mismatch'):
                    pin.verify_archive(f)

    def test_wrong_size_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'fixture.bin';f.write_bytes(b'wrong')
            with self.assertRaisesRegex(pin.VerificationError,'size mismatch'):
                pin.verify_archive(f)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);target=p/'target';target.write_bytes(b'x')
            link=p/'link';link.symlink_to(target)
            with self.assertRaisesRegex(pin.VerificationError,'not a symlink'):
                pin.verify_archive(link)

    def test_invalid_missing_archive(self):
        self.assertEqual(pin.main(['/nonexistent-ollama-archive-do-not-create']),2)

    def test_workflow_checks_hash_before_extract_and_removes_archive(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'.github/workflows/home-inspection-live-synthetic-manual.yml'
        if not path.is_file():
            path=root.parent.parent/'.github/workflows/home-inspection-live-synthetic-manual.yml'
        wf=path.read_text(encoding='utf-8')
        self.assertLess(wf.index('scripts.verify_pinned_ollama'),wf.index('tar --zstd -xf'))
        self.assertLess(wf.index('tar --zstd -xf'),wf.index('rm -- "$archive"'))
        self.assertIn('9 * 1024 * 1024',wf)
        self.assertIn('OLLAMA_MODELS:',wf)
        self.assertNotIn('sh "$RUNNER_TEMP/install-ollama.sh"',wf)

if __name__ == '__main__':unittest.main()
