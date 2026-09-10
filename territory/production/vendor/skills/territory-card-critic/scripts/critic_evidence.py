"""Capture actual PDF evidence and validate a critic-authored report."""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from validate_major_crossroads import validate_major_crossroads
from validate_coverage import validate_coverage
from duplicate_coverage_contract import validate_duplicate_coverage
from validate_housing_instructions import validate_housing_instructions
from topology_contract import validate_topology_review
from neutral_knockout_contract import validate_neutral_knockout
from label_glyph_contract import validate_label_glyph_review
from validate_navigation_presentation import validate_navigation_presentation
from branch_color_contract import validate_branch_color_review
from native_unchanged_width_contract import validate_native_unchanged_width
from saved_native_unchanged_width import validate_saved
from raster_topology_contract import validate_raster_topology

WEIGHTS = {'preservation': .25, 'geography': .25, 'labels': .25, 'template': .15, 'export': .10}


def fingerprint(path):
    import fitz
    with fitz.open(path) as doc:
        return {'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'bytes': path.stat().st_size, 'pages': len(doc)}


def capture(pdf, output):
    import fitz
    output.mkdir(parents=True, exist_ok=True)
    manifest = fingerprint(pdf)
    manifest.update(pdf=str(pdf.resolve()), screenshots=[])
    with fitz.open(pdf) as doc:
        for n, page in enumerate(doc, 1):
            for scale in (1, 2):
                name = f'page-{n}-{scale}x.png'
                page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(output/name)
                manifest['screenshots'].append(name)
            w, h = page.rect.width, page.rect.height
            for i, (x0, y0, x1, y1) in enumerate([
                (0, 0, .36, .56), (.32, 0, .70, .56), (.66, 0, 1, .56),
                (0, .44, .36, 1), (.32, .44, .70, 1), (.66, .44, 1, 1)], 1):
                name = f'page-{n}-region-{i}.png'
                clip = fitz.Rect(x0*w, y0*h, x1*w, y1*h)
                page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False).save(output/name)
                manifest['screenshots'].append(name)
    (output/'capture.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def gate(pdf, report_path):
    report = json.loads(report_path.read_text())
    manifest = json.loads((report_path.parent/'capture.json').read_text())
    actual = fingerprint(pdf)
    errors = validate_major_crossroads(report.get("major_crossroad_review"))
    errors.extend(validate_label_glyph_review(report.get("label_glyph_review"),
        actual['artifact_sha256'], artifact_path=pdf))
    errors.extend(validate_coverage(report.get("coverage_review"), report.get("current_inventory_review")))
    errors.extend(validate_duplicate_coverage(report.get("duplicate_coverage_review"),
        artifact_sha256=actual["artifact_sha256"],
        source_sha256=report.get("coverage_review", {}).get("source_sha256")))
    import fitz
    with fitz.open(pdf) as document:
        housing_artifact_text = "\n".join(page.get_text() for page in document)
    errors.extend(validate_housing_instructions(report.get("housing_instruction_review"),
        report.get("current_inventory_review"), report.get("coverage_review", {}).get("source_sha256"), housing_artifact_text))
    errors.extend(validate_navigation_presentation(report.get("navigation_presentation_review"),
        actual["artifact_sha256"], manifest.get("screenshots", [])))
    errors.extend(validate_branch_color_review(report.get("branch_color_review"), actual["artifact_sha256"]))
    topology_masks = report.get("topology_mask_kinds")
    if not isinstance(topology_masks, dict):
        errors.append("topology_mask_kinds must explicitly list typed topology masks or be an empty object after source comparison")
    else:
        errors.extend(validate_topology_review(report.get("topology_patch_review"), actual['artifact_sha256'], topology_masks,
            original_assignment_sha256=report.get("coverage_review", {}).get("source_sha256")))
    raster_masks = report.get("preservation_audit", {}).get("correction_masks", [])
    if report.get("raster_topology_review") is not None or any(m.get("edit_kind") == "raster_topology_addition" for m in raster_masks):
        errors.extend(validate_raster_topology(report.get("raster_topology_review"), pdf,
            raster_masks, report.get("coverage_review", {}).get("source_sha256")))
    errors.extend(validate_neutral_knockout(report.get("neutral_knockout_review"), pdf,
        report.get("preservation_audit", {}).get("correction_masks", []),
        report.get("coverage_review", {}).get("source_sha256")))
    saved_identity = report.get("saved_native_unchanged_width_review")
    if saved_identity is not None:
        if report.get("native_unchanged_width_review") is not None:
            errors.append("Direct working and saved identity declarations are mutually exclusive")
        identity_errors, _, _ = validate_saved(saved_identity, pdf,
            preservation=report.get("preservation_audit"), critic_manifest=manifest)
    else:
        identity_errors, _ = validate_native_unchanged_width(
            report.get("native_unchanged_width_review"), pdf,
            preservation=report.get("preservation_audit"), critic_manifest=manifest)
    errors.extend(identity_errors)
    if any(actual[k] != manifest.get(k) for k in actual):
        errors.append('Captured artifact does not match current PDF')
    if report.get('artifact_sha256') != actual['artifact_sha256']:
        errors.append('Report hash does not match current PDF')
    if report.get('critic_independent') is not True:
        errors.append('Independent critic review not confirmed')
    clutter = report.get('label_clutter_review')
    if not isinstance(clutter, dict):
        errors.append('Missing visual label clutter review')
    else:
        for key in ('actual_size_review_completed', 'closeup_review_completed'):
            if clutter.get(key) is not True:
                errors.append(f'Label clutter review requires {key}')
        if type(clutter.get('remaining_avoidable_clusters')) is not int or clutter['remaining_avoidable_clusters'] != 0:
            errors.append('Avoidable label clusters must equal 0')
        if not isinstance(clutter.get('evidence'), str) or not clutter['evidence'].strip():
            errors.append('Label clutter review requires screenshot and placement evidence')
    inventory = report.get('current_inventory_review')
    if not isinstance(inventory, dict):
        errors.append('Missing current street/property inventory review')
    else:
        try:
            date.fromisoformat(inventory.get('check_date', ''))
        except (TypeError, ValueError):
            errors.append('Current inventory review requires an ISO check date')
        for key in ('full_boundary_and_edges_checked', 'source_retrieval_complete',
                    'relevant_property_eligibility_resolved'):
            if inventory.get(key) is not True:
                errors.append(f'Current inventory review requires {key}')
        if inventory.get('unresolved_discrepancies') != []:
            errors.append('Current inventory discrepancies must be an empty list')
        if not isinstance(inventory.get('evidence'), str) or not inventory['evidence'].strip():
            errors.append('Current inventory review requires source and feature evidence')
    content = report.get('card_content_review')
    if not isinstance(content, dict):
        errors.append('Missing card content review')
    else:
        if content.get('source_or_audit_lines_absent') is not True:
            errors.append('On-card source-credit or audit lines must be absent')
        if not isinstance(content.get('evidence'), str) or not content['evidence'].strip():
            errors.append('Card content review requires screenshot and extracted-text evidence')
    if actual['pages'] != 1 or actual['bytes'] >= 300000:
        errors.append('Export must be one page below 300000 bytes')
    inspected = report.get('screenshots_inspected', [])
    for name in manifest.get('screenshots', []):
        if name not in inspected or not (report_path.parent/name).is_file():
            errors.append(f'Missing inspected screenshot: {name}')
    scores = {}
    for key in WEIGHTS:
        entry = report.get('categories', {}).get(key, {})
        value = entry.get('score')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10 or not entry.get('reason'):
            errors.append(f'Invalid score or missing rationale: {key}')
        else:
            scores[key] = value
    weighted_score = sum(scores.get(k, 0)*w for k, w in WEIGHTS.items())
    score = round(weighted_score, 2)
    for key in ('blockers', 'unverified'):
        if not isinstance(report.get(key), list):
            errors.append(f'Missing {key} list')
        elif report[key]:
            errors.append(f'Unresolved {key}')
    if errors:
        score = min(score, 8)
    ready = not errors and weighted_score == 10 and all(scores.get(k) == 10 for k in WEIGHTS)
    if report.get('overall_score') != score:
        errors.append(f'Reported score must equal computed score {score}')
    if report.get('release_ready') is not ready:
        errors.append('Reported release state inconsistent with gates')
    return {'overall_score': score, 'release_ready': ready and not errors, 'errors': errors, **actual}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['capture', 'gate'])
    parser.add_argument('pdf', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    result = capture(args.pdf, args.target) if args.operation == 'capture' else gate(args.pdf, args.target)
    print(json.dumps(result, indent=2))
    if args.operation == 'gate' and not result['release_ready']:
        raise SystemExit(1)
