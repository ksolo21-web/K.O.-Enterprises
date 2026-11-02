"""Milestone 4 integration preflight: no inference, approvals, or file writes.

This is a readiness contract, not a completed inspection. It deliberately refuses
to turn a report preview or a specialist plan into a customer-release approval.
"""
from __future__ import annotations

from pathlib import Path
import json
from .core import load_project, validate_project, blockers, coverage
from .agents import plan_specialists
from .capture import verify_custody


def preflight_case(project_path: str | Path, media_ids: list[str] | None = None,
                   *, evidence_root: Path | None = None) -> dict:
    path = Path(project_path).resolve()
    root = Path(evidence_root).resolve() if evidence_root is not None else path.parent
    document = (validate_project(json.loads(path.read_text(encoding='utf-8')), root)
                if evidence_root is not None else load_project(path))
    custody_errors = verify_custody(document, root)
    plan = plan_specialists(document, media_ids)
    unresolved = list(plan['unassigned_media']) + list(plan['unreviewed_videos'])
    quality_blockers = blockers(document)
    return {
        'schema_version': 1,
        'milestone': 'M4',
        'stage': 'PREFLIGHT_ONLY',
        'source_project': str(path),
        'specialist_plan': plan,
        'coverage': coverage(document),
        'custody_errors': custody_errors,
        'unrouted_evidence': unresolved,
        'report_blockers': quality_blockers,
        'ready_for_specialist_execution': not custody_errors and bool(plan['jobs']) and not unresolved,
        'inspector_approved': False,
        'customer_release_allowed': False,
        'real_model_accuracy_verified': False,
    }
