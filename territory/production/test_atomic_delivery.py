"""Real crypto/filesystem and SIGKILL regressions; GitHub is simulated on disk.

No model inference, real card approval, external network or paid infrastructure.
The child harness is test-only. Production has no kill switches or test bypasses.
"""
from __future__ import annotations
from contextlib import ExitStack
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import atomic_delivery
import client
import sealed
import transport


class DiskRemote:
    """Durable fake GitHub objects around the real envelope/chunking functions."""
    def __init__(self, root: Path, kill_stage: str = ''):
        self.root = root
        self.remote = root / 'remote'
        self.remote.mkdir(exist_ok=True)
        self.kill_stage = kill_stage

    def kill(self, stage: str) -> None:
        if self.kill_stage == stage:
            # Parent verifies this was a real SIGKILL, never a caught exception.
            os.kill(os.getpid(), signal.SIGKILL)

    def record(self, event: dict) -> None:
        with (self.root / 'operations.jsonl').open('a') as stream:
            stream.write(json.dumps(event, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def read(self, path: str):
        transport.safe_path(path)
        path = self.remote / path
        if not path.is_file():
            raise transport.MissingObject('Simulated absent remote object')
        return json.loads(path.read_text())

    def commit(self, files, message):
        for name, value in files.items():
            transport.safe_path(name)
            client.atomic_json(self.remote / name, value)
        names = sorted(files)
        self.record({'files': names, 'sha256': {
            name: hashlib.sha256(sealed.canonical(value)).hexdigest()
            for name, value in files.items()}})
        request = next((name for name in files if '/requests/' in name or '/visual-requests/' in name), None)
        if request:
            self.kill('request_published_before_ack')
        if any('/inputs/' in name and name.endswith('/manifest.json') for name in files):
            self.kill('input_published_before_ack')
        return hashlib.sha1(sealed.canonical(files)).hexdigest()

    def pump(self):
        """One deterministic synthetic worker step; never another client job."""
        for family in ('requests', 'visual-requests'):
            folder = self.remote / 'territory/transport' / family
            if not folder.exists():
                continue
            for request_file in folder.iterdir():
                request = json.loads(request_file.read_text())
                session = request['session']
                server_file = self.root / ('worker-' + session + '.json')
                if not server_file.exists():
                    key = sealed.new_key()
                    client.atomic_json(server_file, {'private_key': sealed.b64(sealed.private_bytes(key))})
                else:
                    key = sealed.load_private(sealed.unb64(json.loads(server_file.read_text())['private_key'], 100))
                visual = family == 'visual-requests'
                public_path = 'territory/transport/sessions/' + session + ('/ready.json' if visual else '/public.json')
                if not (self.remote / public_path).exists():
                    value = {'version': 1, 'session': session,
                             'server_public' if visual else 'public_key': sealed.public(key),
                             'expires' if visual else 'expires_at': time.time() + 3600}
                    client.atomic_json(self.remote / public_path, value)
                input_file = self.remote / 'territory/transport/inputs' / session / 'manifest.json'
                output_file = self.remote / 'territory/transport/outputs' / session / 'manifest.json'
                if input_file.exists() and not output_file.exists():
                    envelope = transport.receive_envelope(session, 'inputs')
                    raw = sealed.unseal(envelope, key, session, 'job')
                    with tempfile.TemporaryDirectory(dir=self.root) as temporary:
                        unpacked = Path(temporary) / 'job'
                        sealed.unpack(raw, unpacked)
                        if client.inventory(unpacked) != client.inventory(self.root / 'job'):
                            raise AssertionError('Actual uploaded plaintext hashes differ')
                    receiver = request['client_public' if visual else 'reply_public_key']
                    result = sealed.seal(sealed.pack(self.root / 'expected'), receiver, session, 'result')
                    transport.send_envelope(result, 'outputs')

    def context(self):
        context = ExitStack()
        context.enter_context(patch.object(transport, 'read', side_effect=self.read))
        context.enter_context(patch.object(transport, 'commit', side_effect=self.commit))
        context.enter_context(patch.object(transport, 'api', side_effect=AssertionError('Network must not be called')))
        return context


def make_fixture(root: Path, kind: str):
    job = root / 'job'; job.mkdir()
    (job / 'input.txt').write_bytes(b'SYNTHETIC ONLY\n')
    expected = root / 'expected'; expected.mkdir()
    (expected / 'report.json').write_text('{"release_ready":false,"synthetic_only":true}\n')
    (expected / 'nested').mkdir()
    (expected / 'nested/result.txt').write_bytes(b'Authenticated synthetic return\n')
    output = root / 'output'
    checkpoint = client.checkpoint_for(output)
    state = client.prepare(job, output, checkpoint, kind)
    return state, checkpoint, output


def child(root: Path, kind: str, stage: str) -> int:
    remote = DiskRemote(root, stage)
    original_save = client.atomic_json
    original_install = client.install_directory
    output = root / 'output'
    checkpoint = client.checkpoint_for(output)

    def save(path, value):
        if path == checkpoint and value.get('phase') == 'delivery_prepared':
            remote.kill('before_delivery_checkpoint')
        original_save(path, value)
        if path == checkpoint:
            remote.kill('after_checkpoint_' + value.get('phase', ''))

    def install(source, destination):
        remote.kill('before_install')
        original_install(source, destination)
        remote.kill('after_install')

    with remote.context(), patch.object(client, 'atomic_json', side_effect=save), patch.object(client, 'install_directory', side_effect=install):
        for _ in range(12):
            remote.pump()
            rc = client.main(['--output', str(output), '--kind', kind, '--resume', '--once'])
            if rc == 0:
                return 0
            if rc != 3:
                return rc
    raise AssertionError('Synthetic worker/client did not settle')


class AtomicPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'staged'; self.source.mkdir()
        (self.source / 'receipt').write_text('verified')
        self.output = self.root / 'output'

    def test_new_destination_preserves_contents_and_directory_identity(self):
        identity = self.source.stat().st_ino
        atomic_delivery.install_directory(self.source, self.output)
        self.assertFalse(self.source.exists())
        self.assertEqual(self.output.stat().st_ino, identity)
        self.assertEqual((self.output / 'receipt').read_text(), 'verified')

    def test_unicode_and_spaces_in_path(self):
        target = self.root / 'verified résultat 01'
        atomic_delivery.install_directory(self.source, target)
        self.assertEqual((target / 'receipt').read_text(), 'verified')

    def reject_existing(self, mode):
        if mode == 'empty_directory':
            self.output.mkdir()
        elif mode == 'nonempty_directory':
            self.output.mkdir(); (self.output / 'owner').write_text('unrelated')
        elif mode == 'file':
            self.output.write_text('unrelated')
        elif mode == 'directory_symlink':
            other = self.root / 'owner'; other.mkdir(); self.output.symlink_to(other, target_is_directory=True)
        elif mode == 'dangling_symlink':
            self.output.symlink_to(self.root / 'absent')
        else:
            raise AssertionError(mode)
        before = self.output.lstat()
        with self.assertRaises(FileExistsError):
            atomic_delivery.install_directory(self.source, self.output)
        self.assertEqual(self.output.lstat().st_ino, before.st_ino)
        self.assertEqual(self.output.lstat().st_mode, before.st_mode)
        self.assertEqual((self.source / 'receipt').read_text(), 'verified')
        if mode == 'file': self.assertEqual(self.output.read_text(), 'unrelated')
        if mode == 'nonempty_directory': self.assertEqual((self.output / 'owner').read_text(), 'unrelated')

    def test_source_symlink_is_not_installed(self):
        link = self.root / 'link'; link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(OSError): atomic_delivery.install_directory(link, self.output)
        self.assertFalse(self.output.exists())
        self.assertTrue(link.is_symlink())

    def test_non_directory_source_is_not_installed(self):
        with self.assertRaises(OSError): atomic_delivery.install_directory(self.source / 'receipt', self.output)
        self.assertFalse(self.output.exists())

    def test_nul_path_is_rejected_before_native_call(self):
        with patch.object(atomic_delivery, '_linux_rename') as native:
            with self.assertRaises(ValueError): atomic_delivery.install_directory(self.source, Path(str(self.output) + '\0tail'))
            native.assert_not_called()

    def test_missing_source_is_not_created(self):
        with self.assertRaises(FileNotFoundError): atomic_delivery.install_directory(self.root / 'absent', self.output)
        self.assertFalse(self.output.exists())

    def test_unsupported_platform_does_not_fallback_to_replace(self):
        with patch.object(atomic_delivery.sys, 'platform', 'unsupported'), patch.object(atomic_delivery.os, 'rename') as rename:
            with self.assertRaises(OSError) as error: atomic_delivery.install_directory(self.source, self.output)
            self.assertEqual(error.exception.errno, errno.ENOTSUP)
            rename.assert_not_called()
        self.assertTrue(self.source.exists())

    def test_missing_linux_primitive_does_not_fallback(self):
        with patch.object(atomic_delivery.ctypes, 'CDLL', return_value=object()), patch.object(atomic_delivery.os, 'rename') as rename:
            with self.assertRaises(OSError) as error: atomic_delivery.install_directory(self.source, self.output)
            self.assertEqual(error.exception.errno, errno.ENOTSUP)
            rename.assert_not_called()
        self.assertTrue(self.source.exists())

    def test_filesystem_refusal_preserves_source_and_no_fallback(self):
        class Native:
            def __call__(self, *args):
                ctypes.set_errno(errno.EOPNOTSUPP)
                return -1
        class Library:
            renameat2 = Native()
        with patch.object(atomic_delivery.ctypes, 'CDLL', return_value=Library()), patch.object(atomic_delivery.os, 'rename') as rename:
            with self.assertRaises(OSError) as error: atomic_delivery.install_directory(self.source, self.output)
            self.assertEqual(error.exception.errno, errno.EOPNOTSUPP)
            rename.assert_not_called()
        self.assertTrue(self.source.exists())
        self.assertFalse(self.output.exists())


class DeliveryRaceTests(unittest.TestCase):
    def race(self, kind):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, checkpoint, output = make_fixture(root, kind)
            remote = DiskRemote(root)
            with remote.context():
                envelope = sealed.seal(sealed.pack(root / 'expected'), state['client_public'], state['session'], 'result')
                transport.send_envelope(envelope, 'outputs')
                original_install = client.install_directory
                identities = []
                def competing_directory(source, destination):
                    destination.mkdir()
                    identities.append(destination.stat().st_ino)
                    original_install(source, destination)
                with patch.object(client, 'install_directory', side_effect=competing_directory):
                    with self.assertRaises(FileExistsError): client.advance(state, checkpoint)
                self.assertEqual(output.stat().st_ino, identities[0])
                self.assertEqual(list(output.iterdir()), [])
                retained = client.load(checkpoint, output)
                self.assertEqual(retained['private_key'], state['private_key'])
                self.assertEqual(retained['session'], state['session'])
                self.assertEqual(retained['phase'], 'delivery_prepared')
                self.assertFalse(retained['release_ready'])
                # Owner removes their competing empty directory, then same-session retry.
                output.rmdir()
                self.assertEqual(client.advance(retained, checkpoint), 'received')
                self.assertEqual(client.inventory(output), client.inventory(root / 'expected'))

    def test_candidate_late_directory_is_preserved_then_same_session_recovers(self): self.race('candidates')
    def test_visual_late_directory_is_preserved_then_same_session_recovers(self): self.race('visual')


STAGES = ('request_published_before_ack', 'after_checkpoint_input_prepared',
          'input_published_before_ack', 'after_checkpoint_awaiting_result',
          'before_delivery_checkpoint', 'after_checkpoint_delivery_prepared',
          'before_install', 'after_install', 'after_checkpoint_received')


class ProcessDeathTests(unittest.TestCase):
    def check_restart(self, kind, stage):
        # These are explicitly Linux-runner process-death tests; do not silently skip.
        self.assertTrue(sys.platform.startswith('linux'), 'SIGKILL tests require the approved Linux runtime')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initial, checkpoint, output = make_fixture(root, kind)
            command = [sys.executable, str(Path(__file__).resolve()), '--child', str(root), kind]
            killed = subprocess.run(command + [stage], capture_output=True, text=True, timeout=30)
            self.assertEqual(killed.returncode, -signal.SIGKILL, killed.stderr)
            after_death = client.load(checkpoint, output)
            self.assertEqual(after_death['private_key'], initial['private_key'])
            self.assertEqual(after_death['session'], initial['session'])
            self.assertEqual(after_death['input_identity'], initial['input_identity'])
            resumed = subprocess.run(command + [''], capture_output=True, text=True, timeout=30)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            final = client.load(checkpoint, output)
            self.assertEqual(final['session'], initial['session'])
            self.assertEqual(final['private_key'], initial['private_key'])
            self.assertEqual(final['phase'], 'received')
            self.assertFalse(final['release_ready'])
            self.assertEqual(client.inventory(output), client.inventory(root / 'expected'))
            log = (root / 'operations.jsonl').read_bytes()
            events = [json.loads(line) for line in log.decode().splitlines()]
            for fragment in ('/inputs/', '/outputs/'):
                self.assertEqual(sum(any(fragment in p for p in event['files']) for event in events), 1)
            self.assertEqual(sum(any('/requests/' in p or '/visual-requests/' in p for p in event['files']) for event in events), 1)
            if 'envelope' in after_death:
                self.assertEqual(final['envelope'], after_death['envelope'])
            repeated = subprocess.run(command + [''], capture_output=True, text=True, timeout=30)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual((root / 'operations.jsonl').read_bytes(), log)
            # Delivered bytes remain a gate on every resumed invocation.
            (output / 'report.json').write_text('changed bytes')
            bad = subprocess.run(command + [''], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(bad.returncode, 0)
            self.assertEqual((root / 'operations.jsonl').read_bytes(), log)


for _mode in ('empty_directory', 'nonempty_directory', 'file', 'directory_symlink', 'dangling_symlink'):
    def _existing(self, mode=_mode): self.reject_existing(mode)
    setattr(AtomicPrimitiveTests, 'test_reject_existing_' + _mode, _existing)
for _kind in ('candidates', 'visual'):
    for _stage in STAGES:
        def _restart(self, kind=_kind, stage=_stage): self.check_restart(kind, stage)
        setattr(ProcessDeathTests, 'test_sigkill_' + _kind + '_' + _stage, _restart)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        raise SystemExit(child(Path(sys.argv[2]), sys.argv[3], sys.argv[4]))
    unittest.main()
