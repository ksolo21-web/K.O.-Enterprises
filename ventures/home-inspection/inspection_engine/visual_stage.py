"""Opt-in pixel-first request projection with auditable deferred technical context.

The original prompt, bound response format and full knowledge remain authoritative
for subsequent technical reasoning, evidence custody, Q02/Q03 and human review.
This component ONLY selects a smaller untrusted visual observation input; it
cannot approve, summarize legal requirements or infer a property's condition.
"""
from __future__ import annotations
import hashlib
import json
import re

MAX_VISUAL_PROMPT_BYTES = 4096
MAX_SOURCE_PROMPT_BYTES = 100_000
STRUCTURED = ('OBSERVATION_MEMORY_JSON', 'EVIDENCE_CONTEXT_JSON',
              'UNRECORDED_FEATURE_TASKS_JSON', 'ASSIGNED_COVERAGE_TASKS_JSON')


class VisualStageError(ValueError):
    """Refuse altered or non-projectable input rather than silently trim context."""


def _canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def _hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _digest(value):
    return _hash_bytes(_canon(value).encode('utf-8'))


def _only(lines, prefix):
    items = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if len(items) != 1:
        raise VisualStageError('Missing or duplicated required prompt receipt: ' + prefix)
    return items[0]


def _json_line(lines, name):
    try:
        return json.loads(_only(lines, name + ': '))
    except (ValueError, TypeError) as exc:
        raise VisualStageError('Invalid structured context: ' + name) from exc


def project_visual_stage(prompt: str, schema: dict) -> tuple[str, dict]:
    """Preserve essential evidence context; defer complete knowledge without editing it.

    Full original prompt is retained by the caller's trusted private provenance
    snapshot. This returns a SHA-256 reference to bind later full-text retrieval.
    No evidence image, schema, memory record or tool action is generated here.
    """
    if not isinstance(prompt, str) or len(prompt.encode('utf-8')) > MAX_SOURCE_PROMPT_BYTES:
        raise VisualStageError('Missing or oversized original specialist prompt')
    if not isinstance(schema, dict):
        raise VisualStageError('Missing provider response-format schema')
    lines = prompt.splitlines()
    provider_digest = _only(lines, 'PROVIDER_SCHEMA_SHA256: ')
    if provider_digest != _digest(schema):
        raise VisualStageError('Provider schema digest does not match the unmodified response format')
    guide = _only(lines, 'OUTPUT_GUIDE: ')
    if len(guide) > 1200 or 'candidates' not in guide or 'requests' not in guide:
        raise VisualStageError('Missing bounded candidate/action guidance')
    memory = _json_line(lines, 'OBSERVATION_MEMORY_JSON')
    context = _json_line(lines, 'EVIDENCE_CONTEXT_JSON')
    feature_tasks = _json_line(lines, 'UNRECORDED_FEATURE_TASKS_JSON')
    coverage_tasks = _json_line(lines, 'ASSIGNED_COVERAGE_TASKS_JSON')
    if not isinstance(memory, dict) or not isinstance(context, dict) or not isinstance(feature_tasks, list) or not isinstance(coverage_tasks, list):
        raise VisualStageError('Unexpected visual evidence or task context')
    if not isinstance(context.get('evidence_id'), str) or not context['evidence_id']:
        raise VisualStageError('Missing selected media identity')
    if not isinstance(context.get('invocation_id'), str) or not context['invocation_id']:
        raise VisualStageError('Missing invocation identity')
    if not isinstance(memory.get('records', []), list) or len(memory.get('records', [])) > 128:
        raise VisualStageError('Unbounded memory list')
    if len(coverage_tasks) > 24 or len(feature_tasks) > 80:
        raise VisualStageError('Oversized unresolved task set: split the work order')
    # Derive allowed feature-code and system pairs exclusively from trusted response
    # schema, NOT the image, previous model output or a memory description.
    candidates = schema.get('properties', {}).get('candidates', {}).get('items', {}).get('anyOf', [])
    allowed = {}
    seen_pairs = set()
    if not isinstance(candidates, list) or not candidates:
        raise VisualStageError('Invalid candidate variants')
    for variant in candidates:
        p = variant.get('properties', {})
        system = p.get('system', {}).get('enum', [])
        kind = p.get('type', {}).get('enum', [])
        if len(system) != 1 or len(kind) != 1 or kind[0] not in ('feature', 'potential_concern'):
            raise VisualStageError('Unsupported schema variant; refuse unsafe projection')
        pair = (system[0], kind[0])
        if pair in seen_pairs:
            raise VisualStageError('Duplicate schema variant')
        seen_pairs.add(pair)
        if kind[0] == 'feature':
            codes = p.get('feature_code', {}).get('enum', [])
            if not isinstance(codes, list) or not codes or not all(isinstance(x, str) for x in codes):
                raise VisualStageError('Missing exact permitted feature codes')
            if system[0] in allowed:
                raise VisualStageError('Duplicate feature system')
            allowed[system[0]] = codes
    if not allowed or seen_pairs != {(s, k) for s in allowed for k in ('feature', 'potential_concern')}:
        raise VisualStageError('No complete delegated system schema')
    for t in coverage_tasks:
        if not isinstance(t, dict) or not isinstance(t.get('id'), str) or 'state' not in t or 'physical_check_required' not in t:
            raise VisualStageError('Incomplete coverage task; manual triage required')
    # Hold IDs and states are included even if the task's complete technical
    # instructions are deferred. No physical test can be marked complete here.
    holds = [{'id': t['id'], 'state': t['state'],
              'physical_check_required': t['physical_check_required']} for t in coverage_tasks]
    if not isinstance(context.get('current_zoom_id'), (str, type(None))):
        raise VisualStageError('Invalid zoom lineage')
    output = '\n'.join([
        'PIXEL_OBSERVATION_STAGE_V1: Describe ONLY visible image facts. Never diagnose root cause, assess code compliance, certify safety, assert absence of defects, or approve a report. The full technical knowledge and SOP packet is deferred to independent reasoning, Q02/Q03 and qualified inspector review.',
        'OUTPUT_GUIDE: ' + guide,
        'PROVIDER_SCHEMA_SHA256: ' + provider_digest,
        'DELEGATED_FEATURE_CODES_JSON: ' + _canon(allowed),
        'EVIDENCE_CONTEXT_JSON: ' + _canon(context),
        'OBSERVATION_MEMORY_JSON: ' + _canon(memory),
        'UNRECORDED_FEATURE_TASKS_JSON: ' + _canon(feature_tasks),
        'UNCLEARED_COVERAGE_HOLDS_JSON: ' + _canon(holds),
        'VISUAL_ACTIONS: Prefer requests:[] unless a different small native crop or genuinely different video moment could resolve a named visible uncertainty. Never select full image [0,0,1,1], repeat an existing crop, or invent a test result. At most 3 distinct visible candidates, not an output quota. All concerns remain review_pending.',
        'DEFERRED_FULL_CONTEXT_SHA256: ' + _hash_bytes(prompt.encode('utf-8')),
        'NO_CUSTOMER_RELEASE',
        '',
    ])
    visual_bytes = len(output.encode('utf-8'))
    if visual_bytes > MAX_VISUAL_PROMPT_BYTES:
        raise VisualStageError('Visual stage exceeds fixed budget; split work order, never truncate memory or holds')
    record = {
        'version': 1, 'stage': 'UNVERIFIED_PIXEL_OBSERVATION',
        'full_original_prompt_sha256': _hash_bytes(prompt.encode('utf-8')),
        'visual_prompt_sha256': _hash_bytes(output.encode('utf-8')),
        'provider_schema_sha256': provider_digest,
        'full_context_bytes': len(prompt.encode('utf-8')),
        'visual_context_bytes': visual_bytes,
        'memory_sha256': _digest(memory),
        'evidence_context_sha256': _digest(context),
        'coverage_tasks_sha256': _digest(coverage_tasks),
        'coverage_task_count': len(coverage_tasks),
        'deferred_context_retained_by_caller': False,
        'image_changed': False, 'schema_changed': False,
        'no_knowledge_derived_finding': True, 'no_field_approval': True,
        'customer_release_allowed': False, 'latency_improvement_verified': False,
    }
    return output, record


def preserve_deferred_packet(original: str, projection: dict, *, invocation_id: str, evidence_id: str) -> dict:
    """Bind full input to the visual stage for PRIVATE Q02/Q03/human retrieval.

    Consumers MUST keep this inside the case's private evidence store; these
    may contain inspector notes and must never enter public reference indexes.
    """
    if not isinstance(projection, dict) or not isinstance(original, str):
        raise VisualStageError('Incomplete original input provenance')
    source_digest = _hash_bytes(original.encode('utf-8'))
    if source_digest != projection.get('full_original_prompt_sha256'):
        raise VisualStageError('Deferred original knowledge packet hash mismatch')
    if not all(isinstance(x, str) and x for x in (invocation_id, evidence_id)):
        raise VisualStageError('Missing immutable work-order identity')
    if projection.get('customer_release_allowed') is not False:
        raise VisualStageError('Unsafe visual-stage receipt')
    return {'stage':'DEFERRED_PRIVATE_TECHNICAL_CONTEXT', 'invocation_id': invocation_id,
            'evidence_id': evidence_id, 'full_prompt':original,
            'full_prompt_sha256':source_digest, 'visual_prompt_sha256':projection['visual_prompt_sha256'],
            'technical_reasoning_completed':False, 'qualified_review_completed':False,
            'customer_release_allowed':False}
