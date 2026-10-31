"""Bounded synthetic-trial call records and tool-to-Q02 lineage checks.

This does not establish diagnostic accuracy, trusted identities or client release.
The caller generates synthetic media; no automatic upload or model installation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from inspection_engine.core import DataError, safe_path
from inspection_engine.vision import ollama_local, MAX_MODEL_REPLY
from inspection_engine.critic import CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT


def _write(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.write('\n')


class TrialRecorder:
    """Preserve inputs and untrusted replies before proposal validation can fail."""

    def __init__(self, root: Path, *, live: bool):
        self.root = root / 'invocations'
        self.root.mkdir()
        self.live = live
        self.responses: list[dict] = []
        self.call_count = 0
        self.event_count = 0

    def event(self, value: dict) -> None:
        self.event_count += 1
        _write(self.root / f'event-{self.event_count:04d}.json', value)

    def provider(self, role: str, model: str, controlled_provider=None):
        def call(image: bytes, prompt: str, *, schema=None) -> dict:
            if role=='writer' and not isinstance(schema,dict):
                raise DataError('Writer requires an explicit scoped generation schema')
            effective_schema=schema if role=='writer' else CRITIC_SCHEMA
            self.call_count += 1
            prefix = f'{self.call_count:04d}-{role}'
            image_name = prefix + '.jpg'
            with (self.root / image_name).open('xb') as stream:
                stream.write(image)
            request = {'role':role, 'model':model, 'call_id':prefix,
                       'execution_kind':'local_ollama' if self.live else 'controlled_test',
                       'started_utc':datetime.now(timezone.utc).isoformat(),
                       'image_path':image_name, 'image_sha256':hashlib.sha256(image).hexdigest(),
                       'prompt':prompt, 'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                       'generation_schema':effective_schema,
                       'generation_schema_sha256':hashlib.sha256(json.dumps(effective_schema,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
            _write(self.root / (prefix + '.request.json'), request)
            response = {'call_id':prefix, 'role':role, 'model':model,
                        'execution_kind':request['execution_kind'],
                        'status':'STARTED', 'model_output_is_untrusted':True}
            started = time.monotonic()

            def envelope(value):
                if not isinstance(value, dict):
                    raise DataError('Unexpected model envelope type')
                # Retain actual answer/completion/metrics, not internal thinking
                # or unbounded context arrays. This log is synthetic-trial only.
                fields = {'model','created_at','response','done','done_reason','error',
                          'total_duration','load_duration','prompt_eval_count',
                          'prompt_eval_duration','eval_count','eval_duration'}
                captured = {k:v for k,v in value.items() if k in fields}
                encoded = json.dumps(captured, allow_nan=False)
                if len(encoded.encode()) > MAX_MODEL_REPLY:
                    raise DataError('Model envelope exceeds trial audit limit')
                response['transport_response_untrusted'] = captured
                response['omitted_envelope_fields'] = sorted(set(value) - fields)

            try:
                if self.live:
                    answer = ollama_local(image, prompt, model, timeout=180,
                        schema=effective_schema,
                        system_prompt=None if role=='writer' else CRITIC_SYSTEM_PROMPT,
                        response_audit=envelope)
                else:
                    answer = controlled_provider(image, prompt)
                encoded = json.dumps(answer, allow_nan=False)
                if len(encoded.encode()) > MAX_MODEL_REPLY:
                    raise DataError('Provider response exceeds trial audit limit')
                response['structured_response_untrusted'] = answer
                response['status'] = 'RETURNED_UNVALIDATED_DATA'
                return answer
            except (DataError, OSError, RuntimeError, ValueError, TypeError, TimeoutError) as exc:
                response.update(status='PROVIDER_ERROR', error_type=type(exc).__name__, error=str(exc))
                raise
            finally:
                response['elapsed_seconds'] = round(time.monotonic()-started, 3)
                _write(self.root / (prefix + '.response.json'), response)
                self.responses.append(response)
        return call

    def summary(self) -> dict:
        counts = {role:sum(r['role']==role and r['status']=='RETURNED_UNVALIDATED_DATA'
                          for r in self.responses) for role in ('writer','reviewer')}
        completed = {role:sum(r['role']==role and r['status']=='RETURNED_UNVALIDATED_DATA'
                             and r.get('transport_response_untrusted',{}).get('done') is True
                             and 'error' not in r.get('transport_response_untrusted',{})
                             for r in self.responses) if self.live else 0
                     for role in ('writer','reviewer')}
        return {'provider_call_count':self.call_count, 'returned_provider_calls':counts,
                'completed_live_calls':completed, 'engine_event_count':self.event_count,
                'records_are_acceptance_or_accuracy_approval':False}


def tool_review_evidence(document: dict, dossier: dict, review: dict,
                         root: Path, materially_different) -> dict:
    """Join executed tools to subsequent proposals and actual Q02 evidence IDs."""
    media = {m['id']:m for m in document['media']}
    zooms = {z['id']:z for z in document.get('zoom_views',[])}
    proposals = dossier.get('proposals',[])
    items = review.get('items',[])
    events = dossier.get('events',[])
    result = {'reviewed_zoom_ids':[], 'reviewed_video_still_ids':[],
              'temporally_distinct_reviewed_video_still_ids':[],
              'visibly_changed_reviewed_video_still_ids':[],
              'basis':'engine_proposal_and_Q02_lineage_not_aggregate_counts'}

    def reviewed_proposal(ident, zoom_id=None):
        return any(p.get('invocation_id') and p.get('evidence_id')==ident
                   and (zoom_id is None or zoom_id in p.get('zoom_view_ids',[]))
                   and any(e.get('invocation_id')==p.get('invocation_id')
                           and e.get('media_id')==ident and e.get('candidate_count',0)>0
                           and (zoom_id is None or e.get('zoom_id')==zoom_id) for e in events)
                   and any(i.get('source_media_id')==ident
                           and i.get('source_sha256')==media.get(ident,{}).get('sha256')
                           and i.get('proposal_description')==p.get('description')
                           and i.get('work_order')==p.get('work_order')
                           and (zoom_id is None or i.get('zoom_id')==zoom_id) for i in items)
                   for p in proposals)

    for tool in dossier.get('tool_requests',[]):
        if tool.get('status')!='EXECUTED':
            continue
        if not tool.get('invocation_id') or not any(
                e.get('invocation_id')==tool['invocation_id']
                and e.get('media_id')==tool.get('requested_from_media_id')
                and e.get('request_count')==1 for e in events):
            continue
        if tool.get('kind')=='zoom':
            zid = tool.get('zoom_id')
            z = zooms.get(zid)
            if z and reviewed_proposal(z['media_id'], zid):
                result['reviewed_zoom_ids'].append(zid)
        elif tool.get('kind')=='video_still':
            ident = tool.get('photo_id')
            target = media.get(ident)
            previous = media.get(tool.get('requested_from_media_id'))
            if not target or target.get('capture_origin')!='selected_video_still' or not reviewed_proposal(ident):
                continue
            result['reviewed_video_still_ids'].append(ident)
            if not previous or target.get('derived_from_id')!=previous.get('derived_from_id'):
                continue
            times = [target.get('timestamp_seconds'), previous.get('timestamp_seconds')]
            if not all(type(t) in (int,float) and math.isfinite(t) for t in times) or abs(times[0]-times[1])<0.0005:
                continue
            result['temporally_distinct_reviewed_video_still_ids'].append(ident)
            if materially_different(safe_path(root,previous['path']),safe_path(root,target['path'])):
                result['visibly_changed_reviewed_video_still_ids'].append(ident)
    return {k:sorted(set(v)) if isinstance(v,list) else v for k,v in result.items()}
