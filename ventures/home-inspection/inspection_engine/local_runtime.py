"""Opt-in, loopback-only Ollama transport and vision-capability preflight.

Only exact loopback HTTP endpoints are ever contacted. No redirects, proxies,
remote endpoints, model downloads, inference on preflight, or customer releases.
"""
from __future__ import annotations

import http.client
import json
import re
import socket
from typing import Any

from .core import DataError

PORT = 11434
ALLOWED_ENDPOINTS = {('GET', '/api/tags'), ('POST', '/api/show'), ('POST', '/api/generate')}
MODEL_PATTERN = re.compile(r'(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,49}/)?[A-Za-z0-9][A-Za-z0-9_.-]{0,49}(?::[A-Za-z0-9][A-Za-z0-9_.-]{0,39})?\Z')
MAX_REQUEST_BYTES = 24_000_000
MAX_METADATA_BYTES = 500_000


def validate_model_name(model: str) -> str:
    """Model identifiers are names, not URLs or hostnames to contact."""
    if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model) or '..' in model:
        raise DataError('Invalid local model identifier')
    return model


def local_json(method: str, endpoint: str, body: dict[str, Any] | None = None,
               *, timeout: int = 5, max_bytes: int = MAX_METADATA_BYTES) -> dict:
    """Fixed-address HTTP, deliberately without urllib redirects or proxy support."""
    if (method, endpoint) not in ALLOWED_ENDPOINTS:
        raise DataError('Unapproved local model endpoint')
    if type(timeout) is not int or not 1 <= timeout <= 180:
        raise DataError('Local model timeout must be 1-180 seconds')
    if type(max_bytes) is not int or not 128 <= max_bytes <= 1_000_000:
        raise DataError('Invalid local model reply limit')
    if method == 'GET' and body is not None:
        raise DataError('GET may not include model data')
    if method == 'POST' and not isinstance(body, dict):
        raise DataError('POST requires model data')
    encoded = (json.dumps(body, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
               if body is not None else None)
    if encoded is not None and len(encoded) > MAX_REQUEST_BYTES:
        raise DataError('Local model request exceeds media limit')
    conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    try:
        conn.request(method, endpoint, body=encoded, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        response = conn.getresponse()
        if 300 <= response.status < 400:
            raise DataError('Local model redirect refused to prevent evidence disclosure')
        if response.status != 200:
            raise DataError('Local model request failed (HTTP %d)' % response.status)
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise DataError('Local model response exceeds limit')
    except (TimeoutError, socket.timeout) as exc:
        raise DataError('Local Ollama request timed out before a completed response; generation may still be running') from exc
    except ConnectionRefusedError as exc:
        raise DataError('Local Ollama connection refused; verify the local runtime is listening') from exc
    except (OSError, http.client.HTTPException) as exc:
        raise DataError('Local Ollama transport failed before a completed response') from exc
    finally:
        conn.close()
    try:
        parsed = json.loads(raw.decode('utf-8'))
        if not isinstance(parsed, dict):
            raise ValueError('Non-object response')
        return parsed
    except (UnicodeError, ValueError) as exc:
        raise DataError('Local model returned invalid JSON') from exc


def preflight_models(writer_model: str, reviewer_model: str) -> dict:
    """Read-only Ollama capability check; NOT real vision inference or independence proof."""
    writer = validate_model_name(writer_model)
    reviewer = validate_model_name(reviewer_model)
    if writer == reviewer:
        raise DataError('Writer and reviewer require distinct model identifiers')
    available = local_json('GET', '/api/tags')
    tags = available.get('models')
    if not isinstance(tags, list):
        raise DataError('Ollama model inventory unavailable')
    installed = {m['name']:m for m in tags if isinstance(m,dict) and isinstance(m.get('name'),str)}
    checks=[]
    for role, model in [('writer', writer), ('reviewer', reviewer)]:
        if model not in installed:
            raise DataError('%s model not installed locally: %s' % (role.capitalize(), model))
        info = local_json('POST', '/api/show', {'model':model})
        capabilities = info.get('capabilities')
        if not isinstance(capabilities, list) or 'vision' not in capabilities:
            raise DataError('%s model does not advertise vision capability: %s' % (role.capitalize(), model))
        metadata = installed[model]
        digest = metadata.get('digest')
        if digest is not None and (not isinstance(digest,str) or not re.fullmatch('[0-9a-fA-F]{64}',digest)):
            raise DataError('Invalid model digest from local inventory')
        checks.append({'role':role,'model':model,'installed':True,
                       'model_digest_sha256':digest,'vision_capability_advertised':True})
    if all(x['model_digest_sha256'] for x in checks) and checks[0]['model_digest_sha256']==checks[1]['model_digest_sha256']:
        raise DataError('Writer and reviewer resolve to identical model digests')
    return {'preflight':'LOCAL_MODELS_ADVERTISED_VISION', 'endpoint':'127.0.0.1:11434',
            'models':checks,'real_inference_completed':False,
            'separate_runtime_identity_verified':False,'field_accuracy_verified':False,
            'qualified_human_signoff':False,'customer_release_allowed':False,
            'next_action':'Run opt-in writer and Q02 reviewer against consented local evidence; score independently labeled real cases.'}
