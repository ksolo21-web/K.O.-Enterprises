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
