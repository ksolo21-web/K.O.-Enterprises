#!/usr/bin/env python3
"""R52 evidence gate. Validates records/hashes/locked targets; not a visual agent.

Paths in a review are relative to that review; source_path in a target lock is
relative to the lock. Standalone bounded component success is NOT a card release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def point(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(finite(x) for x in value)


def in_polygon(pt: list[float], polygon: list[list[float]]) -> bool:
    """Point in a predeclared corridor; boundary counts as inside."""
    x, y = pt
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        ax, ay = a; bx, by = b
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) < 1e-8 and min(ax,bx)-1e-8 <= x <= max(ax,bx)+1e-8 and min(ay,by)-1e-8 <= y <= max(ay,by)+1e-8:
            return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def validate(data: dict, base: Path, pdf_path: str | Path | None = None) -> dict:
    errors: list[str] = []
    def require(test: bool, message: str) -> None:
        if not test: errors.append(message)
    r = data.get('label_navigation_review')
    c = data.get('critic_label_navigation_review')
    if not isinstance(r,dict) or not isinstance(c,dict):
        return {'passed':False,'errors':['R52 requires label_navigation_review and critic_label_navigation_review']}
    require(r.get('contract_revision') == 'R52', 'navigation contract_revision must be R52')
    require(r.get('scope') in ('whole_card','bounded_label_regression'), 'explicit navigation review scope required')
    artifact = r.get('artifact_sha256')
    require(isinstance(artifact,str) and len(artifact)==64 and all(ch in '0123456789abcdef' for ch in artifact), 'artifact_sha256 must be lowercase SHA-256')
    require(data.get('artifact_sha256') == artifact == c.get('artifact_sha256'), 'all artifact hashes must match')
    candidate = Path(pdf_path) if pdf_path else base / str(r.get('artifact_path',''))
    require(candidate.is_file() and candidate.suffix.lower()=='.pdf', 'exact PDF must be available')
    if candidate.is_file():
        require(sha256(candidate)==artifact, 'exact PDF hash mismatch')
        require(candidate.read_bytes().startswith(b'%PDF-'), 'artifact is not a PDF')
    lock_path = base / str(r.get('target_lock_path',''))
    if not lock_path.is_file(): return {'passed':False,'errors':errors+['separate target lock file is unavailable']}
    require(sha256(lock_path)==r.get('target_lock_sha256'), 'target lock hash mismatch')
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    require(lock.get('created_before_placement') is True, 'target lock must predate placement')
    source = lock_path.parent / str(lock.get('source_path',''))
    require(source.is_file(), 'target lock source unavailable')
    if source.is_file(): require(sha256(source)==lock.get('source_sha256'), 'target lock source hash mismatch')
    require(bool(lock.get('source_evidence')), 'target lock source evidence required')
    targets = lock.get('labels',[]); records = r.get('labels',[])
    require(isinstance(targets,list) and bool(targets), 'target lock labels required')
    require(isinstance(records,list) and bool(records), 'label records required')
    if not isinstance(targets,list) or not isinstance(records,list):
        return {'passed':False,'errors':errors}
    require(all(isinstance(x,dict) for x in targets+records),'label records must be objects')
    if not all(isinstance(x,dict) for x in targets+records): return {'passed':False,'errors':errors}
    ids=[x.get('label_id') for x in records]; locked_ids=[x.get('label_id') for x in targets]
    require(all(isinstance(x,str) and x for x in ids+locked_ids),'nonempty string label IDs required')
    if not all(isinstance(x,str) and x for x in ids+locked_ids): return {'passed':False,'errors':errors}
    require(len(ids)==len(set(ids)) and len(locked_ids)==len(set(locked_ids)), 'label IDs must be unique')
    require(set(ids)==set(locked_ids)==set(r.get('rendered_label_ids',[])), 'all rendered/in-scope/locked labels must reconcile')
    require(r.get('all_in_scope_labels_reviewed') is True, 'all in-scope labels must be reviewed')
    if r.get('scope')=='whole_card':
        legacy = data.get('label_metric_review',{}).get('label_metrics',[])
        require(set(ids)=={x.get('label_id') for x in legacy if isinstance(x,dict)}, 'whole-card R51 and R52 label inventories must reconcile')
    by_id={x['label_id']:x for x in targets}
    for rec in records:
        lid=rec['label_id']; target=by_id.get(lid)
        if not target: continue
        p=lid+': '
        for field in ['street','navigation_role','segment_id']:
            require(bool(target.get(field)) and rec.get(field)==target.get(field), p+field+' must match independently locked target')
        require(rec.get('observed_segment_id')==target.get('segment_id'), p+'observed target is the wrong physical segment')
        for field in ['source_segment_trace_verified','target_from_saved_pdf','actual_size_clear','closeup_clear']:
            require(rec.get(field) is True,p+field+' must be true')
        require(bool(rec.get('source_evidence')),p+'source evidence required')
        mode=rec.get('mode')
        require(mode in ('direct','curved','callout'),p+'invalid placement mode')
        if mode=='callout':
            callout=rec.get('callout',{})
            require(isinstance(callout,dict),p+'callout must be object')
            if not isinstance(callout,dict): continue
            poly=target.get('target_corridor_pt'); tip=callout.get('tip_pt')
            valid_poly=isinstance(poly,list) and len(poly)>=3 and all(point(x) for x in poly)
            require(valid_poly and point(tip),p+'locked corridor and actual saved-PDF tip required')
            if valid_poly and point(tip): require(in_polygon(tip,poly),p+'arrow misses intended segment corridor')
            gap=callout.get('tail_gap_pt')
            require(finite(gap) and 0<=gap<=2,p+'tail must attach outside glyph ink within existing 0–2pt gap')
            for field in ['target_paint_contact','single_filled_head','tail_outside_glyph_ink']:
                require(callout.get(field) is True,p+field+' must be true')
            require(callout.get('unrelated_crossings')==0,p+'callout crosses unrelated feature')
        if target.get('whole_contour_required') is True:
            require(mode=='curved',p+'the locked bending run requires full curved placement')
            curve=rec.get('curve',{})
            require(isinstance(curve,dict),p+'curve must be object')
            if not isinstance(curve,dict): continue
            for field in ['start_middle_end_inspected','terminal_suffix_inspected','all_glyphs_bound_to_assigned_run','continuous_local_tangent_verified','ends_on_assigned_run','native_metrics_verified']:
                require(curve.get(field) is True,p+field+' must be true')
            require(curve.get('font_metrics_source') in ('exact_pdf_font_widths','verified_shaping_engine_with_declared_kerning'),p+'actual font metrics required')
            require(curve.get('visual_crowding') is False,p+'visible crowding veto')
            require(curve.get('glyph_overlap_pixels')==0,p+'glyph overlap veto')
            gaps=curve.get('road_gaps_pt',[])
            require(isinstance(gaps,list) and len(gaps)==len(target['street'].replace(' ','')) and all(finite(g) and 2<=g<=15 for g in gaps),p+'per-visible-glyph road gaps must satisfy existing 2–15pt band')
            ev=curve.get('font_advance_evidence')
            require(isinstance(ev,str) and bool(ev),p+'font-advance evidence required')
            # A fixture-specified tolerance is immutable; no new universal tracking rule.
            limit=target.get('native_advance_error_limit')
            if limit is not None:
                value=curve.get('native_advance_relative_error_max')
                require(finite(limit) and limit>=0 and finite(value) and 0<=value<=limit,p+'actual font advance error exceeds locked tolerance')
    for field in ['raw_target_lock_reopened','each_repeat_role_rechecked','start_middle_end_and_suffix_rechecked','native_font_spacing_visual_review']:
        require(c.get(field) is True,'critic '+field+' must be true')
    require(c.get('builder_target_ids_used_as_proof') is False, 'critic cannot use builder target IDs as proof')
    require(c.get('reviewer_type') in ('authorized_internal','independent_agent'),'reviewer provenance required')
    if c.get('reviewer_type')=='authorized_internal': require(c.get('critic_independent') is False,'internal review cannot claim independence')
    else: require(c.get('critic_independent') is True and bool(c.get('agent_run_reference')),'independent reviewer requires actual run reference')
    screenshots=c.get('screenshots_inspected',[])
    require(isinstance(screenshots,list) and len(screenshots)>=2, 'inspected actual-size/closeup evidence required')
    if isinstance(screenshots,list):
        require(any('1x' in str(s) for s in screenshots) and any('4x' in str(s) for s in screenshots),'actual 1x and 4x evidence required')
        for path in screenshots: require((base/str(path)).is_file(),'screenshot unavailable: '+str(path))
    return {'passed':not errors,'errors':errors,'scope':r.get('scope'),'label_count':len(records),'authority':'evidence gate only; not visual or whole-card release certification'}


def main(review_path: str | Path, pdf_path: str | Path | None = None) -> dict:
    path=Path(review_path)
    try: return validate(json.loads(path.read_text(encoding='utf-8')),path.parent,pdf_path)
    except (OSError,ValueError,TypeError,KeyError) as exc: return {'passed':False,'errors':[f'invalid or unavailable evidence: {exc}']}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('review_json');ap.add_argument('--pdf');args=ap.parse_args()
    result=main(args.review_json,args.pdf);print(json.dumps(result,indent=2));sys.exit(0 if result['passed'] else 1)