"""Fail-closed review contract for actual ink within curved street labels.

Consume the renderer's hash-bound isolated-glyph measurements. Raster cell-edge
clearance of zero is diagnostic, not an ink overlap or a mandatory spacing rule.
Keep visual guide-induced crowding review separate from shared-ink measurements.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def _number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def _ids(value):
    return (isinstance(value, list)
            and all(isinstance(item, str) and item.strip() for item in value)
            and len(value) == len(set(value)))


def validate_label_glyph_review(review, artifact_sha256, labels=None, artifact_path=None):
    """Validate the same contract for builder and critic, without relaxing gates.

    ``labels`` is the builder's complete label inventory when available. The
    critic also attests complete curved-label coverage in its independent review.
    Measurement paths are absolute, matching the other evidence contracts.
    """
    errors = []

    def check(condition, message):
        if not condition:
            errors.append("label_glyph_review: " + message)

    if not isinstance(review, dict):
        return ["label_glyph_review is required, including explicit empty curved scope"]
    check(review.get("schema_version") == "curved-label-glyph-review-1",
          "schema_version must be curved-label-glyph-review-1")
    scope = review.get("curved_label_ids")
    check(_ids(scope), "curved_label_ids must be an explicit list of unique label IDs")
    scope = set(scope) if _ids(scope) else set()

    expected = None
    if labels is not None:
        check(isinstance(labels, list), "builder label inventory must be a list")
        curved = [item for item in labels if isinstance(item, dict)
                  and item.get("method") == "curved"] if isinstance(labels, list) else []
        ids = [item.get("id") for item in curved]
        check(_ids(ids), "builder curved label IDs must be unique and nonempty")
        expected = {item.get("id"): item.get("text") for item in curved
                    if isinstance(item.get("id"), str)}
        check(scope == set(expected), "curved_label_ids must cover every and only builder curved label")

    path_value = review.get("report_path")
    report_path = Path(path_value) if isinstance(path_value, str) else None
    report = {}
    try:
        if report_path is None or not report_path.is_absolute():
            raise ValueError("measurement report path must be absolute")
        raw = report_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != review.get("report_sha256"):
            raise ValueError("measurement report file/hash mismatch")
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError("measurement report must be a JSON object")
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"label_glyph_review: cannot read bound measurement report: {exc}")
        report = {}

    check(isinstance(artifact_sha256, str) and len(artifact_sha256) == 64
          and report.get("artifact_sha256") == artifact_sha256,
          "measurement report must bind the exact current final PDF")
    scale = report.get("render_scale")
    check(_number(scale) and scale > 0, "render_scale must be a finite positive number")
    units = report.get("pixel_units")
    check(isinstance(units, str) and bool(units.strip()), "measurement pixel_units are required")
    size = report.get("render_size")
    valid_size = (isinstance(size, list) and len(size) == 2
                  and all(type(value) is int and value > 0 for value in size))
    check(valid_size, "render_size must contain positive integer width and height")
    if artifact_path is not None and _number(scale) and scale > 0 and valid_size:
        try:
            import fitz
            with fitz.open(artifact_path) as document:
                bounds = (document[0].rect * fitz.Matrix(scale, scale)).irect
                check(size == [bounds.width, bounds.height],
                      "measurement render_size/scale must match the current PDF")
        except Exception as exc:
            errors.append(f"label_glyph_review: cannot verify PDF render scale: {exc}")
    count = report.get("isolated_text_ink_not_in_original_label_layer_pixels")
    check(type(count) is int and count == 0,
          "isolated glyph ink must match the original final label layer")

    rows = report.get("labels")
    check(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
          "measurement labels must be a list of label records")
    rows = rows if isinstance(rows, list) else []
    curved_rows = [row for row in rows if isinstance(row, dict)
                   and row.get("kind") in ("curve", "curved")]
    row_ids = [row.get("id") for row in curved_rows]
    check(_ids(row_ids) and set(row_ids) == scope,
          "measurement curved label IDs must exactly cover the declared scope")
    for row in curved_rows:
        label_id = row.get("id")
        prefix = str(label_id) + ": "
        name = row.get("name")
        check(isinstance(name, str) and bool(name.strip()), prefix + "label name is required")
        if expected is not None:
            check(isinstance(label_id, str) and name == expected.get(label_id),
                  prefix + "measurement name differs from builder text")
        ink = row.get("glyph_ink_pixels")
        check(type(ink) is int and ink > 0, prefix + "actual glyph ink must be nonempty")
        overlap = row.get("same_label_glyph_overlap_pixels")
        check(type(overlap) is int and overlap == 0,
              prefix + "same_label_glyph_overlap_pixels must equal 0")
        check(row.get("isolated_character_union_matches_label_ink") is True,
              prefix + "isolated glyph union must exactly match label ink")
        match = row.get("visible_final_ink_match_fraction")
        check(_number(match) and match == 1,
              prefix + "measured glyph ink must match the actual final label")
        pairs = row.get("adjacent_glyph_clearances_px")
        check(isinstance(pairs, list), prefix + "adjacent glyph diagnostics are required")
        for index, pair in enumerate(pairs if isinstance(pairs, list) else []):
            if not isinstance(pair, dict):
                check(False, prefix + f"adjacent pair {index} must be an object")
                continue
            check(isinstance(pair.get("pair"), str) and bool(pair["pair"].strip()),
                  prefix + f"adjacent pair {index} identity is required")
            # Do not infer glyph count from Unicode characters: shaping can vary.
            check(_number(pair.get("gap_px")), prefix + f"adjacent pair {index} gap must be finite and >= 0")
            overlap = pair.get("overlap_ink_pixels")
            check(type(overlap) is int and overlap == 0,
                  prefix + f"adjacent pair {index} shared glyph ink must equal 0")

    visual = review.get("independent_visual_review")
    check(isinstance(visual, dict), "independent visual review is required")
    visual = visual if isinstance(visual, dict) else {}
    check(visual.get("artifact_sha256") == artifact_sha256 and bool(artifact_sha256),
          "independent visual review must bind the exact current final PDF")
    visual_ids = visual.get("curved_label_ids")
    check(_ids(visual_ids) and set(visual_ids) == scope,
          "independent visual review must cover every curved label ID")
    for key in ("independent", "all_curved_labels_included", "actual_size_review_completed",
                "closeup_review_completed", "all_curved_labels_readable"):
        check(visual.get(key) is True, "independent visual review requires " + key)
    crowding = visual.get("guide_induced_crowding_count")
    check(type(crowding) is int and crowding == 0,
          "independently reviewed guide-induced crowding must equal 0")
    evidence = visual.get("evidence")
    check(isinstance(evidence, str) and bool(evidence.strip()),
          "independent visual review needs label-specific actual-size/closeup evidence")
    return errors
