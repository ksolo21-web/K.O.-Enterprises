"""Only authenticated, confined ephemeral sessions may process private data in CI."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib,json,os
from pathlib import Path
import sealed

_SESSION=ContextVar('territory_private_session',default=None)

def active():return _SESSION.get() is not None

@contextmanager
def authenticated_session(root:Path,payload):
    if not isinstance(payload,sealed.AuthenticatedPayload):raise ValueError('authenticated decryption proof required')
    root=root.resolve();code=Path(__file__).resolve().parent
    if root.is_relative_to(code) or code.is_relative_to(root):raise ValueError('private jobs must be outside the source tree')
    if not root.is_dir():raise ValueError('a verified extracted job is required')
    if os.environ.get('GITHUB_ACTIONS')=='true':
        temp=Path(os.environ['RUNNER_TEMP']).resolve()
        event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        if not root.is_relative_to(temp):raise ValueError('job must be in ephemeral runner storage')
        if event['repository']['full_name']!='ksolo21-web/K.O.-Enterprises' or event['repository']['private'] is not False:raise ValueError('repository identity or zero-spend public-runner condition changed')
        if os.environ.get('GITHUB_REF')!='refs/heads/territory-card-production' or event['sender']['login']!='ksolo21-web':raise ValueError('untrusted branch or event actor')
    token=_SESSION.set({'root':str(root),'payload_sha256':hashlib.sha256(payload).hexdigest()})
    try:yield
    finally:_SESSION.reset(token)
