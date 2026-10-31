"""Validated building-science differential prompts for 13 inspection domains.

These are hypotheses for evidence collection, not complete failure catalogs,
manufacturer specs, code clauses, real diagnoses or reasons to omit inspections.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
from .descriptors import REQUIRED_FEATURES
from .source_of_truth import KnowledgeError

PLAYBOOKS=Path(__file__).resolve().parents[1]/'knowledge'/'michigan_failure_mode_playbooks_v1.json'


def validate_playbooks(data):
    if not isinstance(data,dict) or data.get('schema_version')!=1 or data.get('status')!='engineering_hypothesis_training_aids_not_source_verified_code':
        raise KnowledgeError('Invalid failure-mode corpus status')
    rows=data.get('systems')
    if not isinstance(rows,list) or len(rows)!=len(REQUIRED_FEATURES):
        raise KnowledgeError('Expected 13 failure-mode domain guides')
    found=set()
    for p in rows:
        if not isinstance(p,dict) or p.get('system') not in REQUIRED_FEATURES or p['system'] in found:
            raise KnowledgeError('Invalid or duplicate failure-mode system')
        found.add(p['system'])
        if p.get('feature_codes')!=list(REQUIRED_FEATURES[p['system']]):
            raise KnowledgeError('Failure-mode codes diverge from audited engine vocabulary')
        for name in ('symptom_to_check','possible_mechanism','alternative_explanation','discriminating_verification',
                     'urgent_escalation_cue','expertise_boundary'):
            if not isinstance(p.get(name),str) or not 16<=len(p[name])<=400:
                raise KnowledgeError('Failure mode lacks bounded professional context')
        for flag,expected in [('requires_case_evidence',True),('may_declare_cause_proven',False),
                              ('may_declare_code_violation',False),('may_declare_no_defects',False)]:
            if p.get(flag) is not expected:raise KnowledgeError('Failure mode may not grant technical or legal authority')
    return copy.deepcopy(data)


@lru_cache(maxsize=1)
def _cached():return validate_playbooks(json.loads(PLAYBOOKS.read_text(encoding='utf-8')))


def load_playbooks():return copy.deepcopy(_cached())


def playbook_digest():return hashlib.sha256(PLAYBOOKS.read_bytes()).hexdigest()


def build_failure_mode_brief(systems):
    if not isinstance(systems,(list,tuple)) or not systems or any(s not in REQUIRED_FEATURES for s in systems):
        raise KnowledgeError('Invalid system selection for failure-mode guidance')
    available={r['system']:r for r in load_playbooks()['systems']}
    parts=['BUILDING_SCIENCE_DIFFERENTIAL: You are identifying possible visible cues, not diagnosing unseen causes. '
           'These are NON-EXHAUSTIVE examples; always document unknowns and escalate serious signs without hazardous testing.']
    for system in dict.fromkeys(systems):
        p=available[system]
        parts.append(f"SYSTEM {system} — inspect for: {p['symptom_to_check']}. "
          f"POSSIBLE (not confirmed): {p['possible_mechanism']}. "
          f"ALTERNATIVE: {p['alternative_explanation']}. "
          f"ADDITIONAL TEST/REVIEW: {p['discriminating_verification']}. "
          f"URGENT EVALUATION CUE: {p['urgent_escalation_cue']}.")
    parts.append('No single photograph, code index or model output establishes root cause or absence of problems. Qualified case review required.')
    return '\n'.join(parts)
