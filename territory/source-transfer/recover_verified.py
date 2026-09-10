#!/usr/bin/env python3
"""Recover verified public skill-source blobs; never handle private card jobs.

Every remote byte is checked against its Git object identity. This program only
adds missing source segments, never replaces a different existing segment. A
partial transfer is a checkpoint, not a completed installation or card approval.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

REPO = 'ksolo21-web/K.O.-Enterprises'
BRANCH = 'territory-card-production'
ROOT = Path(__file__).resolve().parent
PREFIX = 'territory/source-transfer/'
API = 'https://api.github.com/repos/' + REPO

class RecoveryError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RecoveryError('Redirects are not permitted')

def git_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()

def api(path: str, body=None, method=None):
    if not path.startswith('/git/') and path != '':
        raise RecoveryError('Unapproved API route')
    token = os.environ.get('GH_RECOVERY_TOKEN', '')
    if not token:
        raise RecoveryError('Missing scoped GitHub workflow credential')
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'}
    data = None if body is None else json.dumps(body, allow_nan=False).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers,
                                 method=method or ('GET' if body is None else 'POST'))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=30) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RecoveryError('Oversized GitHub response')
    return json.loads(raw)

def guard() -> None:
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RecoveryError('Recovery writes are permitted only in the owner branch workflow')
    if (os.environ.get('GITHUB_REPOSITORY') != REPO
            or os.environ.get('GITHUB_REF') != 'refs/heads/' + BRANCH
            or os.environ.get('GITHUB_ACTOR') != 'ksolo21-web'
            or os.environ.get('GITHUB_EVENT_NAME') != 'push'):
        raise RecoveryError('Wrong repository, branch, actor, or event')
    record = api('')
    if record.get('full_name') != REPO or record.get('private') is not False:
        raise RecoveryError('Repository identity or public visibility changed')

def atomic_json(path: Path, value) -> None:
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)

def main() -> None:
    guard()
    index = json.loads((ROOT / 'recovery-index-20260910.json').read_text())
    blobs = index['blobs']
    if index.get('required_segments') != 39 or len(blobs) != 26:
        raise RecoveryError('Pinned recovery index shape changed')
    expected_names = {f'part-{i:02}.txt' for i in range(1, 27)}
    if set(blobs) != expected_names:
        raise RecoveryError('Unexpected segment path')
    head = api('/git/ref/heads/' + BRANCH)['object']['sha']
    commit = api('/git/commits/' + head)
    additions = []
    verified = []
    for name in sorted(blobs):
        digest = blobs[name]
        if not re.fullmatch(r'[0-9a-f]{40}', digest):
            raise RecoveryError('Invalid expected object identity')
        record = api('/git/blobs/' + digest)
        if record.get('sha') != digest or record.get('encoding') != 'base64':
            raise RecoveryError('Unexpected blob response')
        data = base64.b64decode(''.join(record['content'].split()), validate=True)
        if len(data) != 6000 or record.get('size') != len(data) or git_sha(data) != digest:
            raise RecoveryError('Source blob identity mismatch: ' + name)
        if not re.fullmatch(rb'[A-Za-z0-9+/=]+', data):
            raise RecoveryError('Unexpected transfer alphabet')
        local = ROOT / name
        if local.is_symlink():
            raise RecoveryError('Segment is a symlink')
        if local.exists() and local.read_bytes() != data:
            raise RecoveryError('Existing source segment differs; no overwrite: ' + name)
        if not local.exists():
            local.write_bytes(data)
            additions.append({'path': PREFIX + name, 'mode': '100644', 'type': 'blob', 'sha': digest})
        verified.append({'segment': name, 'git_sha': digest})
    receipt = {'kind': 'actual_github_source_recovery', 'source_branch_head': head,
               'verified_segments': len(verified), 'required_segments': 39,
               'original_source_file_count': 138, 'source_installation_complete': False,
               'card_release_authorized': False, 'verified': verified,
               'run_id': os.environ.get('GITHUB_RUN_ID'),
               'missing_segments': [f'part-{i:02}.txt' for i in range(1, 40)
                                    if not (ROOT / f'part-{i:02}.txt').is_file()]}
    receipt_text = json.dumps(receipt, indent=2) + '\n'
    additions.append({'path': PREFIX + 'SOURCE-RECOVERY-RECEIPT.json',
                      'mode': '100644', 'type': 'blob', 'content': receipt_text})
    tree = api('/git/trees', {'base_tree': commit['tree']['sha'], 'tree': additions})
    new = api('/git/commits', {'message': 'Retain verified original source recovery checkpoint [skip ci]',
                             'tree': tree['sha'], 'parents': [head]})
    result = api('/git/refs/heads/' + BRANCH, {'sha': new['sha'], 'force': False}, method='PATCH')
    if result.get('object', {}).get('sha') != new['sha']:
        raise RecoveryError('Branch update readback differs')
    if api('/git/ref/heads/' + BRANCH)['object']['sha'] != new['sha']:
        raise RecoveryError('Concurrent branch change; refresh checkpoint before retrying')
    atomic_json(ROOT / 'SOURCE-RECOVERY-RECEIPT.json', receipt)
    print(json.dumps({'verified_segments': len(verified), 'required_segments': 39,
                      'commit': new['sha'], 'source_installation_complete': False,
                      'card_release_authorized': False}))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f'## Original source recovery\nVerified {len(verified)}/39 source segments.\n\n')
            stream.write('The complete 138-file installation and territory-card release remain unapproved.\n')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not print credential-bearing requests or arbitrary API response bodies.
        raise SystemExit('Source recovery stopped without release approval: ' + type(error).__name__)
