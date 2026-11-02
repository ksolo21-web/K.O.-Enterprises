"""Opt-in private audit journal for local report-model calls.

An audit event is a local transport receipt, not proof of inference accuracy,
professional review, source authenticity, or a trustworthy signing identity.
Raw requests include base64 page images and must remain in private storage.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .core import DataError

MAX_EVENT_BYTES = 25_000_000
MAX_TOTAL_BYTES = 512_000_000
MAX_EVENTS = 800


class PrivateProposalAudit:
    """Write each pre-call request and returned envelope before further work.

    The caller owns the output directory and must keep it out of public repos.
    A failed or interrupted call may have a request without a response; no
    synthetic response is ever inserted. No retries or network operations.
    """

    def __init__(self, directory):
        root = Path(directory).absolute()
        if (root.exists() or root.is_symlink() or not root.parent.is_dir()
                or any(parent.is_symlink() for parent in root.parents)):
            raise DataError('Audit directory must be new with no symlink ancestors')
        os.mkdir(root, 0o700)
        self.root = root
        self.events = []
        self.total = 0
        self.finished = False

    def _write(self, name, value, limit):
        data = (json.dumps(value, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
        if len(data) > limit or self.total + len(data) > MAX_TOTAL_BYTES:
            raise DataError('Private inference audit storage budget exceeded')
        path = self.root / name
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        self.total += len(data)
        return hashlib.sha256(data).hexdigest()

    def __call__(self, event):
        if self.finished:
            raise DataError('Audit journal already finalized')
        if (not isinstance(event, dict) or set(event) not in
                ({'kind', 'payload'}, {'kind', 'envelope'})):
            raise DataError('Unrecognized inference audit event')
        kind = event['kind']
        if kind not in ('generation_request', 'generation_response'):
            raise DataError('Unrecognized inference audit event kind')
        if ((kind == 'generation_request') != ('payload' in event)):
            raise DataError('Inference audit event type mismatch')
        if len(self.events) >= MAX_EVENTS:
            raise DataError('Private inference audit event count exceeded')
        number = len(self.events) + 1
        name = f'{number:04d}-{kind}.json'
        sha = self._write(name, event, MAX_EVENT_BYTES)
        self.events.append({'file': name, 'sha256': sha, 'kind': kind})

    def finish(self, status):
        if self.finished:
            return
        if status not in ('COMPLETED', 'FAILED'):
            raise DataError('Invalid inference audit outcome')
        manifest = {'kind': 'M3_PRIVATE_LOCAL_INFERENCE_AUDIT_V1',
                    'status': status, 'events': self.events,
                    'event_count': len(self.events),
                    'total_event_bytes': self.total,
                    'human_review_performed': False,
                    'field_accuracy_verified': False,
                    'training_approved': False,
                    'customer_release_allowed': False}
        self._write('manifest.json', manifest, MAX_EVENT_BYTES)
        self.finished = True

    def __enter__(self):
        return self

    def __exit__(self, typ, value, traceback):
        self.finish('FAILED' if typ is not None else 'COMPLETED')
        return False


def verify_private_audit(directory, proposal_path):
    """Verify receipt completeness and byte identities; not model authenticity."""
    import base64
    import stat

    from .report_review_queue import digest, _read_json

    root = Path(directory).absolute()
    if (not root.is_dir() or root.is_symlink()
            or any(p.is_symlink() for p in root.parents)):
        raise DataError('Invalid private inference audit directory')

    def read_event(name):
        path = root / name
        if (path.is_symlink() or not path.is_file()):
            raise DataError('Private audit event missing or redirected')
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode) or not 1 <= meta.st_size <= MAX_EVENT_BYTES:
                raise DataError('Invalid audit event file')
            content = stream.read(MAX_EVENT_BYTES + 1)
        if len(content) != meta.st_size:
            raise DataError('Incomplete audit event')
        try:
            value = json.loads(content)
        except (ValueError, UnicodeError) as exc:
            raise DataError('Unreadable audit event') from exc
        return value, hashlib.sha256(content).hexdigest(), len(content)

    manifest, _, _ = read_event('manifest.json')
    if (not isinstance(manifest, dict)
            or set(manifest) != {'kind','status','events','event_count','total_event_bytes',
                                 'human_review_performed','field_accuracy_verified',
                                 'training_approved','customer_release_allowed'}
            or manifest['kind'] != 'M3_PRIVATE_LOCAL_INFERENCE_AUDIT_V1'
            or manifest['status'] != 'COMPLETED'
            or any(manifest[k] is not False for k in ('human_review_performed',
                         'field_accuracy_verified','training_approved','customer_release_allowed'))):
        raise DataError('Incomplete or unsafe inference audit')
    rows = manifest['events']
    if (not isinstance(rows,list) or not 2<=len(rows)<=MAX_EVENTS
            or type(manifest['event_count']) is not int or manifest['event_count']!=len(rows)):
        raise DataError('Invalid inference audit event inventory')
    proposals = _read_json(Path(proposal_path))
    from .report_review_queue import digest
    clean = dict(proposals)
    recorded = clean.pop('proposal_sha256', None)
    if (recorded != digest(clean) or proposals.get('kind')!='M3_AUTOMATIC_REPORT_PROPOSALS_V8'
            or any(proposals.get(key) is not False for key in
                   ('human_review_performed','field_accuracy_verified','training_approved','customer_release_allowed'))
            or not isinstance(proposals.get('provider_id'),str)
            or not proposals['provider_id'].startswith('local-ollama:')):
        raise DataError('Invalid source model proposal receipt')
    calls = proposals.get('calls')
    if not isinstance(calls,list) or len(calls)*2 != len(rows):
        raise DataError('Proposal/audit call count mismatch')

    total = 0
    events = []
    file_names = {'manifest.json'}
    for n,row in enumerate(rows,1):
        expected_kind = 'generation_request' if n%2 else 'generation_response'
        expected_name = f'{n:04d}-{expected_kind}.json'
        if (not isinstance(row,dict) or set(row)!={'file','sha256','kind'}
                or row['file'] != expected_name or row['kind'] != expected_kind):
            raise DataError('Inference audit event sequence mismatch')
        event,sha,size = read_event(expected_name)
        if sha != row['sha256'] or not isinstance(event,dict) or event.get('kind')!=expected_kind:
            raise DataError('Inference audit event content changed')
        if set(event)!=( {'kind','payload'} if n%2 else {'kind','envelope'}):
            raise DataError('Inference audit event fields changed')
        total += size
        file_names.add(expected_name)
        events.append(event)
    if (type(manifest['total_event_bytes']) is not int
            or total != manifest['total_event_bytes']
            or set(p.name for p in root.iterdir()) != file_names):
        raise DataError('Inference audit inventory differs from observed files')
    expected_model = proposals['provider_id'][len('local-ollama:'):]
    for i,call in enumerate(calls):
        request,reply = events[2*i]['payload'],events[2*i+1]['envelope']
        if (not isinstance(call,dict) or not isinstance(request,dict)
                or not isinstance(reply,dict)
                or request.get('model')!=expected_model
                or not isinstance(request.get('prompt'),str)
                or hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest()!=call.get('prompt_sha256')):
            raise DataError('Original model prompt differs from proposal receipt')
        images = request.get('images')
        if not isinstance(images,list) or len(images)!=len(call.get('image_sha256',[])):
            raise DataError('Model source image inventory mismatch')
        try:
            hashes=[hashlib.sha256(base64.b64decode(encoded,validate=True)).hexdigest()
                    for encoded in images]
        except (ValueError,TypeError,base64.binascii.Error) as exc:
            raise DataError('Invalid recorded model image') from exc
        if hashes != call['image_sha256']:
            raise DataError('Model source image bytes differ from proposal receipt')
        if (reply.get('done') is not True or reply.get('done_reason')!='stop'
                or reply.get('model',expected_model)!=expected_model or 'error' in reply
                or not isinstance(reply.get('response'),str)):
            raise DataError('Recorded model response is not complete')
        try:
            decoded = json.loads(reply['response'])
        except (ValueError,TypeError) as exc:
            raise DataError('Recorded model result not valid JSON') from exc
        if digest(decoded)!=call.get('response_sha256'):
            raise DataError('Raw model result differs from proposal receipt')
    return {'kind':'M3_V8_PRIVATE_AUDIT_VERIFICATION','model_calls_verified':len(calls),
            'events_verified':len(rows),'request_response_integrity_verified':True,
            'model_execution_authenticated':False,'semantic_accuracy_verified':False,
            'professional_review_complete':False,'customer_release_allowed':False}
