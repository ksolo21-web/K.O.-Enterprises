"""Resumable owner-side encrypted jobs. Transport success never approves a card.

The key/checkpoint stays on the owner's machine. Request and ciphertext are saved
BEFORE publication, so a lost response cannot create a second logical submission.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time
import sealed
import transport
from atomic_delivery import install_directory

class RecoveryError(RuntimeError):
    pass

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read_json(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise RecoveryError('Duplicate checkpoint field')
            out[key] = value
        return out
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(RecoveryError('Nonfinite checkpoint value')))

def private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RecoveryError('Checkpoint must be a regular, unlinked private file')
    if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise RecoveryError('Checkpoint owner or private permissions are incorrect; key not opened')

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        private_file(path)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(sealed.canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == 'posix':
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)

@contextmanager
def exclusive(checkpoint):
    lock = checkpoint.with_name(checkpoint.name + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists() or lock.is_symlink():
        private_file(lock)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        if os.name == 'posix':
            import fcntl
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error: raise RecoveryError('Another client owns this checkpoint') from error
        elif os.name == 'nt':
            import msvcrt
            os.write(fd, b'0'); os.lseek(fd, 0, 0)
            try: msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as error: raise RecoveryError('Another client owns this checkpoint') from error
        else:
            raise RecoveryError('No supported process lock on this platform')
        yield
    finally:
        os.close(fd)

def inventory(root):
    if not root.is_dir() or root.is_symlink():
        raise RecoveryError('Expected an intact job/result directory')
    result = {}
    total = 0
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise RecoveryError('Symlinks cannot be input or result files')
        if path.is_dir(): continue
        if not path.is_file(): raise RecoveryError('Nonregular input or result file')
        name = path.relative_to(root).as_posix(); sealed.safe_name(name)
        raw = path.read_bytes(); total += len(raw)
        if len(raw) > sealed.MAX_FILE or total > sealed.MAX_RAW:
            raise RecoveryError('File inventory exceeds transport limits')
        result[name] = digest(raw)
    if not result or len(result) > sealed.MAX_FILES:
        raise RecoveryError('Empty or oversized file inventory')
    return result

def checkpoint_for(output):
    return output.with_name(output.name + '-client-key.json')

def prepare(job, output, checkpoint, kind):
    if kind not in ('candidates', 'visual'):
        raise RecoveryError('Unsupported job kind')
    if output.exists() or output.is_symlink() or checkpoint.exists() or checkpoint.is_symlink():
        raise RecoveryError('New job cannot overwrite a result or checkpoint')
    job = job.resolve(); output = output.absolute(); checkpoint = checkpoint.absolute()
    if output.resolve().is_relative_to(job) or checkpoint.resolve().is_relative_to(job):
        raise RecoveryError('Private client state/output must remain outside the uploaded job')
    inputs = inventory(job); key = sealed.new_key(); session = sealed.new_session()
    if kind == 'visual':
        request = {'version': 1, 'session': session, 'client_public': sealed.public(key)}
    else:
        request = {'version': 1, 'session': session, 'reply_public_key': sealed.public(key), 'created_at': time.time()}
    state = {'schema_version': 2, 'session': session, 'kind': kind, 'job': str(job),
             'output': str(output), 'private_key': sealed.b64(sealed.private_bytes(key)),
             'client_public': sealed.public(key), 'inputs': inputs,
             'input_identity': digest(sealed.canonical(inputs)), 'request': request,
             'phase': 'prepared', 'release_ready': False}
    atomic_json(checkpoint, state)
    return state

def load(checkpoint, output, job=None, kind=None):
    private_file(checkpoint); state = read_json(checkpoint)
    if set(state) == {'session', 'private_key'}:
        sealed.metadata(state['session'], 'job')
        public = sealed.public(sealed.load_private(sealed.unb64(state['private_key'], 100)))
        matches = []
        for family, mode, field in (('requests', 'candidates', 'reply_public_key'), ('visual-requests', 'visual', 'client_public')):
            request = optional('territory/transport/' + family + '/' + state['session'])
            if request is not None:
                if request.get(field) != public or request.get('session') != state['session']:
                    raise RecoveryError('Legacy key does not match the published request')
                matches.append((mode, request))
        if len(matches) != 1:
            raise RecoveryError('Legacy key has no unambiguous published request; it is preserved')
        mode, request = matches[0]
        state.update({'schema_version': 2, 'kind': mode, 'client_public': public,
                      'job': str(job.resolve()) if job is not None else '',
                      'output': str(output.absolute()), 'inputs': {},
                      'input_identity': digest(sealed.canonical({})), 'request': request,
                      'phase': 'legacy_result_only', 'legacy_result_only': True, 'release_ready': False})
        # Legacy keys can retrieve authenticated results, never resubmit unknown input.
    if state.get('schema_version') != 2:
        raise RecoveryError('Unknown checkpoint format; original key is preserved')
    sealed.metadata(state.get('session'), 'job')
    key = sealed.load_private(sealed.unb64(state.get('private_key'), 100))
    if sealed.public(key) != state.get('client_public'):
        raise RecoveryError('Saved private/public key identity differs')
    if state.get('output') != str(output.absolute()) or state.get('kind') not in ('candidates', 'visual'):
        raise RecoveryError('Output/job-kind binding differs from the saved session')
    if kind is not None and kind != state['kind']:
        raise RecoveryError('Cannot change a saved session job kind')
    if job is not None and str(job.resolve()) != state['job']:
        raise RecoveryError('Cannot replace the saved job with a different input directory')
    if digest(sealed.canonical(state.get('inputs'))) != state.get('input_identity'):
        raise RecoveryError('Saved input identity differs')
    public_field = 'client_public' if state['kind'] == 'visual' else 'reply_public_key'
    request = state.get('request', {})
    if request.get('session') != state['session'] or request.get(public_field) != state['client_public'] or type(request.get('version')) is not int or request['version'] != 1:
        raise RecoveryError('Saved request is not bound to the session and client key')
    return state

def optional(path):
    try: return transport.read(path)
    except transport.MissingObject: return None

def result_ready(state, checkpoint):
    output = Path(state['output']); expected = state.get('result_files')
    if output.exists() or output.is_symlink():
        if not expected or inventory(output) != expected:
            raise RecoveryError('Existing output does not match the saved authenticated result')
        state['phase'] = 'received'; atomic_json(checkpoint, state)
        return True
    root = 'territory/transport/outputs/' + state['session']
    if optional(root + '/manifest.json') is None:
        return False
    envelope = transport.receive_envelope(state['session'], 'outputs')
    key = sealed.load_private(sealed.unb64(state['private_key'], 100))
    raw = sealed.unseal(envelope, key, state['session'], 'result')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='territory-return-', dir=output.parent) as temporary:
        staged = Path(temporary) / 'result'; sealed.unpack(raw, staged)
        actual = inventory(staged)
        if expected is not None and actual != expected:
            raise RecoveryError('Returned result changed after an interrupted delivery')
        state['result_files'] = actual; state['result_sha256'] = digest(raw)
        state['phase'] = 'delivery_prepared'; atomic_json(checkpoint, state)
        if output.exists() or output.is_symlink():
            raise RecoveryError('Output appeared while receiving; refusing overwrite')
        install_directory(staged, output)
    state['phase'] = 'received'; atomic_json(checkpoint, state)
    return True

def advance(state, checkpoint):
    # Recover completed work before inspecting source files or making any write.
    if result_ready(state, checkpoint): return 'received'
    if state.get('legacy_result_only'):
        raise RecoveryError('Legacy result is not available; unbound input will not be resubmitted')
    session = state['session']; root = 'territory/transport/sessions/' + session
    status = optional(root + '/status.json')
    if status and (status.get('session') != session or status.get('status') == 'failed'):
        raise RecoveryError('Worker reports failure or a mismatched session; saved key remains intact')
    family = 'visual-requests' if state['kind'] == 'visual' else 'requests'
    request_path = 'territory/transport/' + family + '/' + session
    remote = optional(request_path)
    if remote is not None and remote != state['request']:
        raise RecoveryError('Published request differs from the saved session')
    if state.get('phase') == 'awaiting_result':
        if remote is None: raise RecoveryError('Published request disappeared')
        return 'awaiting_result'
    if inventory(Path(state['job'])) != state['inputs']:
        raise RecoveryError('Job files changed; the original session will not submit changed input')
    if remote is None:
        transport.commit({request_path: state['request']}, 'Start owner-authorized encrypted territory job')
        if optional(request_path) != state['request']:
            raise RecoveryError('Request publication was not verified; resume the same checkpoint')
    input_path = 'territory/transport/inputs/' + session + '/manifest.json'
    manifest = optional(input_path)
    if manifest is not None:
        uploaded = transport.receive_envelope(session, 'inputs')
        if uploaded != state.get('envelope'):
            raise RecoveryError('Published input is not the exact saved encrypted payload')
        state['phase'] = 'awaiting_result'; atomic_json(checkpoint, state)
        return 'awaiting_result'
    visual = state['kind'] == 'visual'
    server = optional(root + ('/ready.json' if visual else '/public.json'))
    if server is None: return 'awaiting_worker'
    public_field, expiry_field = ('server_public', 'expires') if visual else ('public_key', 'expires_at')
    expiry = server.get(expiry_field)
    if server.get('session') != session or type(server.get('version')) is not int or server['version'] != 1:
        raise RecoveryError('Worker identity differs from the saved request')
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or expiry <= time.time():
        raise RecoveryError('Worker expired before input was accepted; no automatic duplicate job was started')
    peer = server.get(public_field); sealed.derive(sealed.new_key(), peer, {'validate': True})
    if state.get('server_public') not in (None, peer):
        raise RecoveryError('Worker key changed; refusing to reuse or rewrite ciphertext')
    if 'envelope' not in state:
        raw = sealed.pack(Path(state['job']))
        if inventory(Path(state['job'])) != state['inputs']:
            raise RecoveryError('Input changed while packaging')
        state['server_public'] = peer; state['envelope'] = sealed.seal(raw, peer, session, 'job')
        state['phase'] = 'input_prepared'; atomic_json(checkpoint, state)
    transport.validate_envelope(state['envelope'], 'inputs')
    transport.send_envelope(state['envelope'], 'inputs')
    if transport.receive_envelope(session, 'inputs') != state['envelope']:
        raise RecoveryError('Input publication was not verified; resume the same checkpoint')
    state['phase'] = 'awaiting_result'; atomic_json(checkpoint, state)
    return 'awaiting_result'

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path, nargs='?')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kind', choices=('candidates', 'visual'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--timeout', type=int, default=3000)
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 3600: parser.error('timeout must be 1-3600 seconds')
    output = args.output.absolute(); checkpoint = checkpoint_for(output)
    with exclusive(checkpoint):
        if checkpoint.exists() or checkpoint.is_symlink():
            state = load(checkpoint, output, args.job, args.kind)
        else:
            if args.resume or args.job is None: parser.error('An existing checkpoint is required for resume')
            state = prepare(args.job, output, checkpoint, args.kind or 'candidates')
        deadline = time.monotonic() + args.timeout
        while True:
            phase = advance(state, checkpoint)
            if phase == 'received':
                print('Authenticated result files recovered. Read the unchanged card gates; transport is not approval.')
                return 0
            if args.once or time.monotonic() >= deadline:
                print('Session checkpoint saved; rerun the same command to resume. No card release is approved.')
                return 3
            time.sleep(min(5, max(0, deadline - time.monotonic())))

if __name__ == '__main__':
    try: raise SystemExit(main())
    except (RecoveryError, transport.TransportError, sealed.EnvelopeError, OSError, ValueError):
        print('Session stopped without approval. The private checkpoint was retained; inspect it locally and resume the same session.')
        raise SystemExit(2)
