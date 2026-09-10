"""Verify native assignment and retained approved-card authority independently."""
import hashlib
import json
import math
from pathlib import Path
from topology_masks import final_mask_parts


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _record(record):
    try:
        return (isinstance(record, dict) and isinstance(record.get('path'), str)
                and Path(record['path']).is_file() and _sha(record['path']) == record.get('sha256'))
    except OSError:
        return False


def _rect(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and value[0] < value[2] and value[1] < value[3])


def _same_rects(a, b):
    return (len(a) == len(b) and all(_rect(x) and _rect(y)
            and all(math.isclose(v, w, rel_tol=0, abs_tol=1e-9) for v, w in zip(x, y))
            for x, y in zip(a, b)))


def validate_preservation_authorities(review, plan, native_report, artifact_sha256,
                                      source_sha256=None, project_preservation=None):
    """Retain the old same-authority path; independently replay dual-card proof.

    A plan's approved_card_baseline makes the second chain mandatory for the
    critic too. The builder additionally compares it with its approved base.
    No free original-assignment hash can substitute for actual file identity.
    """
    errors = []
    def check(value, message):
        if not value:
            errors.append('preservation_authorities: ' + message)
    assignment = plan.get('original_assignment', {})
    check(_record(assignment), 'original assignment path/hash must identify actual source-map bytes')
    assignment_hash = assignment.get('sha256') if isinstance(assignment, dict) else None
    check(bool(assignment_hash) and native_report.get('original_assignment_sha256') == assignment_hash,
          'native topology report must prove this exact original assignment')
    if source_sha256 is not None:
        check(source_sha256 == assignment_hash, 'original assignment differs from project coverage source')
    declared_card = plan.get('approved_card_baseline')
    if declared_card is not None:
        check(_record(declared_card), 'plan approved_card_baseline must identify the actual retained card')
    plan_card_hash = declared_card.get('sha256') if isinstance(declared_card, dict) else None
    project = project_preservation if isinstance(project_preservation, dict) else None
    approved_hash = project.get('approved_base_sha256') if project is not None else plan_card_hash
    dual = bool(approved_hash and approved_hash != assignment_hash)
    if project is not None and dual:
        check(plan_card_hash == approved_hash, 'plan must bind the separately approved retained card')
    if declared_card is not None:
        check(bool(plan_card_hash) and plan_card_hash != assignment_hash,
              'approved_card_baseline is only for a distinct retained-card authority')
        dual = True
    authority = review.get('preservation_authorities')
    if not dual and authority is None:
        return errors
    if not isinstance(authority, dict):
        check(False, 'dual authority requires preservation_authorities and retained-card comparison')
        return errors
    if project is not None:
        for key in ('approved_base_path', 'approved_base_sha256', 'original_assignment_path',
                    'original_assignment_sha256', 'retained_card_baseline', 'correction_masks'):
            check(authority.get(key) == project.get(key), 'review/project disagreement in ' + key)
    retained = authority.get('retained_card_baseline')
    retained = retained if isinstance(retained, dict) else {}
    approved = {'path': authority.get('approved_base_path'), 'sha256': authority.get('approved_base_sha256')}
    original = {'path': authority.get('original_assignment_path'), 'sha256': authority.get('original_assignment_sha256')}
    check(_record(approved) and approved.get('sha256') == plan_card_hash,
          'approved base must remain the plan-bound retained card')
    check(_record(original) and original.get('sha256') == assignment_hash,
          'separate original assignment must match actual plan-bound source map')
    check(_record(retained) and retained.get('sha256') == approved.get('sha256')
          and retained.get('path') == approved.get('path'),
          'retained-card baseline must be the exact approved card')
    bound = {'path': retained.get('rendered_comparison_path'),
             'sha256': retained.get('rendered_comparison_sha256')}
    if not _record(bound):
        check(False, 'retained-card comparison file/hash is required')
        return errors
    try:
        comparison = json.loads(Path(bound['path']).read_text())
        if not isinstance(comparison, dict):
            raise ValueError('comparison is not an object')
    except (OSError, ValueError, TypeError) as exc:
        check(False, 'invalid retained comparison: ' + str(exc))
        return errors
    for path_key, hash_key, expected in (
        ('artifact_path', 'artifact_sha256', artifact_sha256),
        ('retained_card_path', 'retained_card_sha256', approved.get('sha256')),
        ('original_assignment_path', 'original_assignment_sha256', assignment_hash),
    ):
        check(_record({'path': comparison.get(path_key), 'sha256': comparison.get(hash_key)})
              and bool(expected) and comparison.get(hash_key) == expected,
              'retained comparison has missing or mismatched ' + path_key)
    declared = {'path': comparison.get('declared_masks_input'),
                'sha256': comparison.get('declared_masks_input_sha256')}
    check(_record(declared), 'declared mask input must be an actual hash-bound file')
    try:
        original_masks = json.loads(Path(declared['path']).read_text()).get('masks_final', []) if _record(declared) else []
    except (OSError, ValueError, TypeError, AttributeError):
        original_masks = []
    rects = comparison.get('masks_final')
    valid_rects = isinstance(rects, list) and bool(rects) and all(_rect(r) for r in rects)
    check(valid_rects and isinstance(original_masks, list) and _same_rects(rects, original_masks),
          'comparison masks must equal the independently declared mask input')
    mask_ids = retained.get('correction_mask_ids')
    valid_ids = (isinstance(mask_ids, list) and bool(mask_ids)
                 and all(isinstance(v, str) and v for v in mask_ids) and len(mask_ids) == len(set(mask_ids)))
    check(valid_ids, 'retained comparison must identify its exact correction_mask_ids')
    masks = authority.get('correction_masks')
    masks = masks if isinstance(masks, list) else []
    selected = []
    if valid_ids:
        for mask_id in mask_ids:
            found = [m for m in masks if isinstance(m, dict) and m.get('id') == mask_id]
            check(len(found) == 1, 'retained correction mask missing or duplicated: ' + mask_id)
            if len(found) == 1:
                m = found[0]
                try:
                    selected.extend(final_mask_parts(m))
                except (KeyError, TypeError, ValueError):
                    check(False, 'invalid retained mask geometry: ' + mask_id)
    check(valid_rects and _same_rects(selected, rects),
          'retained comparison mask coordinates differ from declared project corrections')
    checks = comparison.get('checks')
    checks = checks if isinstance(checks, list) else []
    scales = [r.get('scale') for r in checks if isinstance(r, dict)]
    valid_scales = (len(scales) == len(checks) and all(type(s) in (int, float) and s in (1, 2, 4) for s in scales)
                    and len(scales) == len(set(scales)) and {1, 2}.issubset(set(scales)))
    check(valid_scales and retained.get('actual_render_scales') == scales,
          'retained comparison must declare matching 1x/2x scales and every supplied 4x check')
    check(type(retained.get('pixels_changed_outside_masks')) is int and retained['pixels_changed_outside_masks'] == 0,
          'retained-card outside-mask count must equal 0')
    check(comparison.get('all_zero_outside') is True, 'retained comparison must report zero outside every mask')
    # A hash-bound zero is insufficient: compare actual approved/candidate pixels.
    if errors or not valid_rects or not valid_scales:
        return errors
    try:
        import fitz
        import numpy as np
        with fitz.open(retained['path']) as before, fitz.open(comparison['artifact_path']) as after:
            check(len(before) == len(after) == 1, 'approved-card comparison must contain one front page')
            check(before[0].rect == after[0].rect, 'retained/candidate page dimensions must match')
            for row in checks:
                scale = row['scale']
                a = before[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                b = after[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                if (a.width, a.height, a.n) != (b.width, b.height, b.n):
                    check(False, 'retained/candidate raster dimensions differ'); continue
                aa = np.frombuffer(a.samples, np.uint8).reshape(a.height, a.width, a.n)
                bb = np.frombuffer(b.samples, np.uint8).reshape(b.height, b.width, b.n)
                changed = np.any(aa != bb, axis=2); allowed = np.zeros(changed.shape, bool)
                for x0, y0, x1, y1 in rects:
                    allowed[max(0, math.floor(y0 * scale)):min(b.height, math.ceil(y1 * scale)),
                            max(0, math.floor(x0 * scale)):min(b.width, math.ceil(x1 * scale))] = True
                outside = int((changed & ~allowed).sum()); total = int(changed.sum())
                check(type(row.get('changed_pixels')) is int and row['changed_pixels'] == total,
                      f'{scale}x retained changed-pixel count differs from actual replay')
                check(type(row.get('changed_outside_masks')) is int and row['changed_outside_masks'] == outside == 0,
                      f'{scale}x actual retained-card pixels changed outside declared masks')
    except Exception as exc:
        check(False, 'cannot replay retained-card comparison: ' + str(exc))
    return errors
