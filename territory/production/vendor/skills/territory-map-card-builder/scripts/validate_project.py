#!/usr/bin/env python3
"""Validate a Territory Map Card Builder project manifest.

Uses jsonschema when installed and always runs semantic release gates.
"""
from __future__ import annotations

from descriptive_access_contract import validate_project_entrance
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any
from validate_major_crossroads import validate_major_crossroads
from validate_coverage import validate_coverage
from duplicate_coverage_contract import validate_duplicate_coverage
from validate_housing_instructions import validate_housing_instructions
from topology_contract import validate_topology_review, KINDS as TOPOLOGY_KINDS
from neutral_knockout_contract import validate_neutral_knockout, KIND as KNOCKOUT_KIND
from label_glyph_contract import validate_label_glyph_review
from validate_navigation_presentation import validate_navigation_presentation
from branch_color_contract import validate_branch_color_review
from native_unchanged_width_contract import validate_native_unchanged_width
from saved_native_unchanged_width import validate_saved
from raster_topology_contract import validate_raster_topology

ZERO_GATES = (
    "missing_source_roads",
    "extra_generated_roads",
    "disconnected_intersections",
    "unnamed_required_roads",
    "unclassified_roads",
    "perimeter_without_inside_side",
    "hidden_internal_roads",
    "mixed_status_overlaps",
    "colored_endpoint_artifacts",
    "branch_endpoint_overshoots",
    "label_collisions",
    "avoidable_label_clusters",
    "clipped_elements",
    "unresolved_rules",
    "unresolved_source_conflicts",
    "unattributed_sources",
    "altered_supplied_linework",
    "wrong_road_labels",
    "label_street_overlaps",
    "label_gap_violations",
    "partially_lifted_labels",
    "unnecessary_callouts",
    "malformed_arrowheads",
    "arrow_label_overlaps",
    "arrow_arrow_overlaps",
    "arrow_wrong_targets",
    "arrow_unrelated_road_crossings",
    "bold_street_labels",
    "inconsistent_label_fonts",
    "back_page_present",
    "do_not_work_list_present",
    "missing_verified_site_names",
    "unverified_site_names",
    "site_label_obstructions",
    "missing_verified_entrances",
    "extra_unverified_entrances",
    "entrance_wrong_targets",
    "entrance_arrow_label_overlaps",
    "entrance_arrow_arrow_overlaps",
    "entrance_arrow_unrelated_road_crossings",
    "entrance_arrow_route_overlap_outside_target_radius",
    "disconnected_navigation_context",
    "isolated_major_road_labels",
    "nonuniform_source_scaling",
    "supplied_geometry_clipped",
    "directions_entrance_mismatches",
    "unauthorized_map_mode_change",
    "pixels_changed_outside_declared_correction_masks",
    "repaired_stroke_style_mismatches",
)

STROKE_STYLE_LIMITS = {
    "median_width_delta_px": 1.25,
    "maximum_color_delta_rgb": 18.0,
    "edge_softness_delta_px": 0.85,
    "centerline_p95_deviation_px": 2.0,
    "boundary_presence_mismatch_pixels": 0.0,
    "texture_delta": 2.5,
    "unexpected_status_pixel_count": 0.0,
}

PROHIBITED_GEOMETRY_SOURCES = (
    "google maps",
    "google street view",
    "bing maps screenshot",
    "apple maps screenshot",
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {exc}") from exc


def schema_validate(project: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(project), key=lambda e: list(e.path)):
        location = ".".join(str(p) for p in err.path) or "$"
        errors.append(f"schema:{location}: {err.message}")
    return errors


def semantic_validate(project: dict[str, Any]) -> list[str]:
    errors: list[str] = validate_major_crossroads(project.get("major_crossroad_review"))

    errors.extend(validate_duplicate_coverage(project.get("duplicate_coverage_review"), project))

    map_mode = project.get("map_mode")
    if map_mode not in {"preserve_supplied_map", "vector_rebuild"}:
        errors.append("map_mode must be preserve_supplied_map or vector_rebuild")

    boundary = project.get("boundary", {})
    errors.extend(validate_coverage(project.get("coverage_review"), project.get("current_inventory_review"),
                                    boundary, map_mode, project.get("roads", [])))

    artifact_text = None
    housing_pdf = Path(project.get("output", {}).get("pdf", ""))
    if housing_pdf.is_file():
        try:
            import fitz
            with fitz.open(housing_pdf) as document:
                artifact_text = "\n".join(page.get_text() for page in document)
        except Exception as exc:
            errors.append(f"Cannot verify actual PDF housing instructions: {exc}")
    errors.extend(validate_housing_instructions(project.get("housing_instruction_review"),
        project.get("current_inventory_review"), project.get("coverage_review", {}).get("source_sha256"), artifact_text))

    nav_pdf = Path(project.get("output", {}).get("pdf", ""))
    nav_hash = hashlib.sha256(nav_pdf.read_bytes()).hexdigest() if nav_pdf.is_file() else None
    errors.extend(validate_branch_color_review(project.get("branch_color_review"), nav_hash))
    errors.extend(validate_navigation_presentation(project.get("navigation_presentation_review"), nav_hash,
        entrances=project.get("entrances", []), roads=project.get("roads", [])))

    sources = project.get("sources", [])
    if not sources:
        errors.append("at least one source is required")
    for i, source in enumerate(sources):
        if source.get("license_checked") is not True:
            errors.append(f"sources[{i}].license_checked must be true")

    seen_ids: set[str] = set()
    roads_by_id: dict[str, dict[str, Any]] = {}
    for i, road in enumerate(project.get("roads", [])):
        prefix = f"roads[{i}]"
        road_id = str(road.get("id", ""))
        if not road_id:
            errors.append(f"{prefix}.id is required")
        elif road_id in seen_ids:
            errors.append(f"duplicate road id: {road_id}")
        seen_ids.add(road_id)
        roads_by_id[road_id] = road

        geometry_source = str(road.get("geometry_source", "")).lower()
        if any(term in geometry_source for term in PROHIBITED_GEOMETRY_SOURCES):
            errors.append(f"{prefix}.geometry_source uses prohibited traced commercial map geometry")
        if road.get("geometry_verified") is not True:
            errors.append(f"{prefix}.geometry_verified must be true")
        if road.get("visible") is not True and road.get("classification") in {"interior", "perimeter"}:
            errors.append(f"{prefix} is a required territory road but is not visible")
        if road.get("label_status") == "unresolved":
            errors.append(f"{prefix}.label_status is unresolved")

        classification = road.get("classification")
        work_rule = road.get("work_rule")
        inside_side = road.get("inside_side")
        expected = {
            "interior": "both_sides",
            "perimeter": "inside_only",
            "excluded": "do_not_work",
            "context": "context_only",
        }.get(classification)
        if expected and work_rule != expected and not road.get("exception_reason"):
            errors.append(f"{prefix}: {classification} normally requires {expected}; add a documented exception")
        if classification == "perimeter" and inside_side == "not_applicable":
            errors.append(f"{prefix}: perimeter road must identify the worked side")
        if classification != "perimeter" and inside_side != "not_applicable" and not road.get("exception_reason"):
            errors.append(f"{prefix}: inside_side is only expected for perimeter roads")

    labels = project.get("labels", [])
    glyph_pdf = None
    glyph_artifact_hash = None
    try:
        glyph_pdf = Path(project.get("output", {}).get("pdf", ""))
        glyph_artifact_hash = hashlib.sha256(glyph_pdf.read_bytes()).hexdigest()
    except (OSError, TypeError, ValueError):
        glyph_pdf = None
    errors.extend(validate_label_glyph_review(project.get("label_glyph_review"),
        glyph_artifact_hash, labels, glyph_pdf))
    if not labels:
        errors.append("at least one audited street label is required")
    seen_label_ids: set[str] = set()
    labeled_road_ids: set[str] = set()
    font_families: set[str] = set()
    for i, label in enumerate(labels):
        prefix = f"labels[{i}]"
        label_id = str(label.get("id", ""))
        if not label_id:
            errors.append(f"{prefix}.id is required")
        elif label_id in seen_label_ids:
            errors.append(f"duplicate label id: {label_id}")
        seen_label_ids.add(label_id)

        road_id = str(label.get("road_id", ""))
        road = roads_by_id.get(road_id)
        if road is None:
            errors.append(f"{prefix}.road_id does not match a project road")
        else:
            labeled_road_ids.add(road_id)
            if label.get("text") != road.get("name"):
                errors.append(f"{prefix}.text does not match its assigned road name")

        family = str(label.get("font_family", "")).strip().lower()
        if not family:
            errors.append(f"{prefix}.font_family is required")
        else:
            font_families.add(family)
        if label.get("font_weight") != 400:
            errors.append(f"{prefix}.font_weight must be 400 (regular)")
        for flag in ("covers_street", "overlaps_label", "clipped"):
            if label.get(flag) is not False:
                errors.append(f"{prefix}.{flag} must be false")

        method = label.get("method")
        arrow = label.get("arrow")
        if method == "callout":
            if label.get("direct_fit_available") is not False:
                errors.append(f"{prefix}: callout is prohibited when direct placement fits")
            if not isinstance(arrow, dict):
                errors.append(f"{prefix}.arrow is required for a callout")
            else:
                if arrow.get("target_road_id") != road_id:
                    errors.append(f"{prefix}.arrow targets the wrong street")
                if arrow.get("target_kind") != "street_stem":
                    errors.append(f"{prefix}.arrow must target the street stem")
                if arrow.get("filled_triangular_head") is not True:
                    errors.append(f"{prefix}.arrow must use a filled triangular head")
                length = arrow.get("leader_length_px")
                if not isinstance(length, (int, float)) or not 12 <= length <= 80:
                    errors.append(f"{prefix}.arrow leader length must be 12-80 px")
                start_gap = arrow.get("start_gap_px")
                if not isinstance(start_gap, (int, float)) or not 0 < start_gap <= 20:
                    errors.append(f"{prefix}.arrow start gap must be greater than 0 and at most 20 px")
                for flag in ("overlaps_label", "overlaps_arrow", "crosses_unrelated_road"):
                    if arrow.get(flag) is not False:
                        errors.append(f"{prefix}.arrow.{flag} must be false")
        else:
            if arrow not in (None, {}):
                errors.append(f"{prefix}.arrow is prohibited for a non-callout label")
            minimum = label.get("guide_gap_min_px")
            maximum = label.get("guide_gap_max_px")
            spread = label.get("guide_gap_spread_px")
            if not isinstance(minimum, (int, float)) or not 2 <= minimum <= 15:
                errors.append(f"{prefix}.guide_gap_min_px must be 2-15")
            if not isinstance(maximum, (int, float)) or not 2 <= maximum <= 15:
                errors.append(f"{prefix}.guide_gap_max_px must be 2-15")
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
                if minimum > maximum:
                    errors.append(f"{prefix}: minimum label gap exceeds maximum")
                if maximum - minimum > 8:
                    errors.append(f"{prefix}: label is partially lifted; gap spread exceeds 8 px")
            if not isinstance(spread, (int, float)) or spread > 8:
                errors.append(f"{prefix}.guide_gap_spread_px must be at most 8")
            if method == "curved" and label.get("follows_street_shape") is not True:
                errors.append(f"{prefix}: curved label must follow its street shape")

    if len(font_families) > 1:
        errors.append("all street labels must use one font family")
    for road_id, road in roads_by_id.items():
        if (
            road.get("visible") is True
            and road.get("name")
            and road.get("label_status") != "not_required"
            and road_id not in labeled_road_ids
        ):
            errors.append(f"road {road_id} is visible and named but has no audited label")

    sites_by_id: dict[str, dict[str, Any]] = {}
    site_label_families: set[str] = set()
    for i, site in enumerate(project.get("sites", [])):
        prefix = f"sites[{i}]"
        site_id = str(site.get("id", ""))
        if not site_id:
            errors.append(f"{prefix}.id is required")
        elif site_id in sites_by_id:
            errors.append(f"duplicate site id: {site_id}")
        sites_by_id[site_id] = site
        if site.get("verified") is not True:
            errors.append(f"{prefix}.verified must be true; never invent a site name")
        if not str(site.get("source_ref", "")).strip():
            errors.append(f"{prefix}.source_ref is required")
        verified_count = site.get("verified_entrance_count")
        if not isinstance(verified_count, int) or verified_count < 0:
            errors.append(f"{prefix}.verified_entrance_count must be a non-negative integer")

        label = site.get("label")
        if not isinstance(label, dict):
            errors.append(f"{prefix}.label is required")
            continue
        if label.get("text") != site.get("name"):
            errors.append(f"{prefix}.label.text must match the verified site name")
        family = str(label.get("font_family", "")).strip().lower()
        if not family:
            errors.append(f"{prefix}.label.font_family is required")
        else:
            site_label_families.add(family)
        if label.get("font_weight") != 400:
            errors.append(f"{prefix}.label.font_weight must be 400 (regular)")
        if label.get("centered_in_site_zone") is not True:
            errors.append(f"{prefix}.label must be centered in the verified site zone")
        for flag in ("covers_route", "covers_building_or_work_shape", "overlaps_label", "clipped"):
            if label.get(flag) is not False:
                errors.append(f"{prefix}.label.{flag} must be false")

    entrances_by_id: dict[str, dict[str, Any]] = {}
    entrances_by_site: dict[str, list[dict[str, Any]]] = {}
    entrance_label_families: set[str] = set()
    for i, entrance in enumerate(project.get("entrances", [])):
        prefix = f"entrances[{i}]"
        entrance_id = str(entrance.get("id", ""))
        if not entrance_id:
            errors.append(f"{prefix}.id is required")
        elif entrance_id in entrances_by_id:
            errors.append(f"duplicate entrance id: {entrance_id}")
        entrances_by_id[entrance_id] = entrance

        site_id = str(entrance.get("site_id", ""))
        if site_id not in sites_by_id:
            errors.append(f"{prefix}.site_id does not match a verified site")
        entrances_by_site.setdefault(site_id, []).append(entrance)
        if entrance.get("verified") is not True:
            errors.append(f"{prefix}.verified must be true; extra or unverified entrances are prohibited")
        if not str(entrance.get("source_ref", "")).strip():
            errors.append(f"{prefix}.source_ref is required")

        public_road_id = str(entrance.get("public_road_id", ""))
        if public_road_id not in roads_by_id:
            errors.append(f"{prefix}.public_road_id does not match a project road")
        access_road_id = str(entrance.get("target_access_road_id", ""))
        access_road = roads_by_id.get(access_road_id)
        if access_road is None:
            errors.append(f"{prefix}.target_access_road_id does not match a project road")
        elif entrance.get("representation") != "named_street" and access_road.get("role") != "access_stem":
            errors.append(f"{prefix}.target_access_road_id must identify an access_stem road")

        if entrance.get("representation") == "descriptive_access":
            errors.extend(validate_project_entrance(project, entrance, nav_hash))
            continue

        if entrance.get("representation") == "named_street":
            access_name = str((access_road or {}).get("name", "")).strip()
            if not access_name or not any(label.get("road_id") == access_road_id and label.get("text") == access_name and label.get("method") in {"direct", "curved"} for label in project.get("labels", [])):
                errors.append(f"{prefix}: named access requires its bound direct street label")
            if not access_name or access_name.lower() not in str(project.get("directions", {}).get("text", "")).lower():
                errors.append(f"{prefix}: directions must name the access street")
            if any(entrance.get(k) for k in ("arrow", "label_text", "target_box")):
                errors.append(f"{prefix}: named street access must not add a redundant entrance callout")
            review_entries = project.get("navigation_presentation_review", {}).get("entrances", {}).get("representations", [])
            if not any(r.get("entrance_id") == entrance_id and r.get("representation") == "named_street" for r in review_entries if isinstance(r, dict)):
                errors.append(f"{prefix}: named-street representation requires matching review evidence")
            continue

        family = str(entrance.get("label_font_family", "")).strip().lower()
        if not family:
            errors.append(f"{prefix}.label_font_family is required")
        else:
            entrance_label_families.add(family)
        if entrance.get("label_font_weight") != 400:
            errors.append(f"{prefix}.label_font_weight must be 400 (regular)")
        if entrance.get("label_overlaps_feature") is not False:
            errors.append(f"{prefix}.label_overlaps_feature must be false")
        if entrance.get("clipped") is not False:
            errors.append(f"{prefix}.clipped must be false")

        target_box = entrance.get("target_box")
        if not isinstance(target_box, dict):
            errors.append(f"{prefix}.target_box is required")
            target_box = {}
        bounds = [target_box.get(k) for k in ("x_min", "y_min", "x_max", "y_max")]
        if not all(isinstance(value, (int, float)) for value in bounds):
            errors.append(f"{prefix}.target_box must contain numeric bounds")
        elif bounds[0] > bounds[2] or bounds[1] > bounds[3]:
            errors.append(f"{prefix}.target_box minimums must not exceed maximums")

        arrow = entrance.get("arrow")
        if not isinstance(arrow, dict):
            errors.append(f"{prefix}.arrow is required")
            continue
        if arrow.get("target_access_road_id") != access_road_id:
            errors.append(f"{prefix}.arrow targets the wrong access stem")
        target_x = arrow.get("target_x")
        target_y = arrow.get("target_y")
        if all(isinstance(value, (int, float)) for value in bounds) and isinstance(target_x, (int, float)) and isinstance(target_y, (int, float)):
            inside_box = bounds[0] <= target_x <= bounds[2] and bounds[1] <= target_y <= bounds[3]
            if not inside_box:
                errors.append(f"{prefix}.arrow target is outside the verified entrance box")
        else:
            errors.append(f"{prefix}.arrow target coordinates must be numeric")
        if arrow.get("target_in_verified_box") is not True:
            errors.append(f"{prefix}.arrow.target_in_verified_box must be true")
        distance = arrow.get("distance_to_access_px")
        tolerance = arrow.get("target_tolerance_px")
        if not isinstance(distance, (int, float)) or not isinstance(tolerance, (int, float)) or tolerance <= 0:
            errors.append(f"{prefix}.arrow access distance and tolerance must be valid numbers")
        elif distance > tolerance:
            errors.append(f"{prefix}.arrow misses the verified access stem")

        length = arrow.get("leader_length_px")
        minimum = arrow.get("leader_min_px")
        maximum = arrow.get("leader_max_px")
        if not all(isinstance(value, (int, float)) for value in (length, minimum, maximum)):
            errors.append(f"{prefix}.arrow leader length range must be numeric")
        elif minimum <= 0 or minimum > maximum or not minimum <= length <= maximum:
            errors.append(f"{prefix}.arrow leader length must stay inside its declared map-scale range")
        if arrow.get("shaft_segment_count") != 1:
            errors.append(f"{prefix}.arrow must use one clean shaft segment")
        if arrow.get("filled_triangular_head") is not True:
            errors.append(f"{prefix}.arrow must use a filled triangular head")
        if arrow.get("marker_bound") is not True:
            errors.append(f"{prefix}.arrow must bind its triangular marker")
        for flag in ("overlaps_label", "overlaps_arrow", "crosses_unrelated_road", "route_overlap_outside_target_radius"):
            if arrow.get(flag) is not False:
                errors.append(f"{prefix}.arrow.{flag} must be false")

    for site_id, site in sites_by_id.items():
        expected_count = site.get("verified_entrance_count")
        actual_count = len(entrances_by_site.get(site_id, []))
        if isinstance(expected_count, int) and expected_count != actual_count:
            errors.append(
                f"site {site_id} entrance inventory mismatch: expected {expected_count}, rendered {actual_count}"
            )

    all_map_font_families = font_families | site_label_families | entrance_label_families
    if len(all_map_font_families) > 1:
        errors.append("street, site, and entrance labels must use one font family")

    navigation = project.get("navigation_context", {})
    major_road_ids = navigation.get("major_road_ids", [])
    approach_paths = navigation.get("approach_paths", [])
    if navigation.get("verified") is not True:
        errors.append("navigation_context.verified must be true")
    if navigation.get("minimum_context_only") is not True:
        errors.append("navigation_context.minimum_context_only must be true")
    if navigation.get("required") is not True:
        errors.append("navigation context is required on EVERY card")
    if len(set(major_road_ids)) < 2:
        errors.append("navigation_context requires at least two distinct major road IDs")
    if navigation.get("required") is True:
        if not major_road_ids:
            errors.append("navigation context is required but no major roads are recorded")
        if not approach_paths:
            errors.append("navigation context is required but no connected approach paths are recorded")
    elif major_road_ids or approach_paths:
        errors.append("navigation context is marked unnecessary but major roads or approach paths were added")

    major_ids_seen = set()
    for road_id in major_road_ids:
        road = roads_by_id.get(str(road_id))
        if road is None:
            errors.append(f"navigation major road {road_id} does not match a project road")
        elif road.get("visible") is not True:
            errors.append(f"navigation major road {road_id} must be visibly drawn")
        elif str(road_id) not in labeled_road_ids:
            errors.append(f"navigation major road {road_id} has an isolated or missing label")

    for i, path in enumerate(approach_paths):
        prefix = f"navigation_context.approach_paths[{i}]"
        major_id = str(path.get("major_road_id", ""))
        territory_road_id = str(path.get("territory_road_id", ""))
        major_ids_seen.add(major_id)
        if major_id not in major_road_ids:
            errors.append(f"{prefix}.major_road_id is not in major_road_ids")
        if territory_road_id not in roads_by_id:
            errors.append(f"{prefix}.territory_road_id does not match a project road")
        for via_id in path.get("via_road_ids", []):
            if str(via_id) not in roads_by_id:
                errors.append(f"{prefix}.via_road_ids contains an unknown road: {via_id}")
        if path.get("connected") is not True:
            errors.append(f"{prefix}.connected must be true")
        if path.get("geometry_verified") is not True:
            errors.append(f"{prefix}.geometry_verified must be true")
    for major_id in major_road_ids:
        if str(major_id) not in major_ids_seen:
            errors.append(f"major road {major_id} has no verified connected approach path")

    review = project.get("major_crossroad_review", {})
    if isinstance(review, dict):
        if review.get("directions_text") != project.get("directions", {}).get("text"):
            errors.append("major_crossroad_review.directions_text must equal the actual directions text")
        reviewed_ids = set()
        labels_by_id = {label.get("id"): label for label in labels}
        for record in review.get("roads", []):
            if not isinstance(record, dict):
                continue
            bindings = record.get("road_ids", [])
            reviewed_ids.update(bindings)
            for road_id in bindings:
                road = roads_by_id.get(road_id, {})
                if road_id not in major_road_ids or road.get("name") != record.get("name") or road.get("visible") is not True:
                    errors.append(f"major cross-road binding {road_id} must match a visible named navigation road")
            for label_id in record.get("label_ids", []):
                label = labels_by_id.get(label_id, {})
                if label.get("road_id") not in bindings or label.get("text") != record.get("name"):
                    errors.append(f"major cross-road label binding {label_id} is missing or assigned to another road")
            chain = record.get("approach", {}).get("road_ids", [])
            if any(road_id not in roads_by_id or roads_by_id[road_id].get("visible") is not True for road_id in chain):
                errors.append("major cross-road approach must use known visible drawn roads")
            if not chain or (roads_by_id.get(chain[-1], {}).get("classification") not in {"interior", "perimeter"} and not any(e.get("target_access_road_id") == chain[-1] for e in project.get("entrances", []))):
                errors.append("major cross-road approach must reach a territory road")
            matching_paths = [path for path in approach_paths if [path.get("major_road_id"), *path.get("via_road_ids", []), path.get("territory_road_id")] == chain]
            if not matching_paths:
                errors.append("major cross-road approach does not match a navigation approach path")
        if reviewed_ids != set(major_road_ids):
            errors.append("major_crossroad_review must cover exactly all navigation major road IDs")

    source_transform = project.get("source_transform")
    if map_mode == "preserve_supplied_map":
        if not isinstance(source_transform, dict):
            errors.append("source_transform is required in preserve_supplied_map mode")
        else:
            scale_x = source_transform.get("scale_x")
            scale_y = source_transform.get("scale_y")
            if not isinstance(scale_x, (int, float)) or not isinstance(scale_y, (int, float)):
                errors.append("source_transform scale values must be numeric")
            elif scale_x <= 0 or scale_y <= 0 or abs(scale_x - scale_y) > 0.001:
                errors.append("source_transform must use positive uniform scaling within 0.001")
            for field in (
                "aspect_ratio_preserved",
                "all_supplied_geometry_visible",
                "colored_pixels_preserved",
                "crop_contains_only_blank_context",
            ):
                if source_transform.get(field) is not True:
                    errors.append(f"source_transform.{field} must be true")
    elif source_transform is not None:
        errors.append("source_transform must be null in vector_rebuild mode")

    topology_mask_kinds = {}
    preservation = project.get("preservation_audit")
    if map_mode == "preserve_supplied_map":
        if not isinstance(preservation, dict):
            errors.append("preservation_audit is required in preserve_supplied_map mode")
        else:
            if preservation.get("approved_base_present") is not True:
                errors.append("preservation_audit.approved_base_present must be true")
            base_hash = preservation.get("approved_base_sha256")
            if not isinstance(base_hash, str) or len(base_hash) != 64 or any(
                character not in "0123456789abcdefABCDEF" for character in base_hash
            ):
                errors.append("preservation_audit.approved_base_sha256 must be a 64-character hex digest")
            if preservation.get("original_map_mode") != "preserve_supplied_map":
                errors.append("preservation_audit.original_map_mode must remain preserve_supplied_map")
            if preservation.get("full_redraw_authorized") is not False:
                errors.append("full_redraw_authorized must be false while preserving an approved map")
            if preservation.get("rendered_comparison_completed") is not True:
                errors.append("preservation_audit.rendered_comparison_completed must be true")
            if preservation.get("pixels_changed_outside_masks") != 0:
                errors.append("preservation_audit.pixels_changed_outside_masks must equal 0")

            masks = preservation.get("correction_masks", [])
            if not isinstance(masks, list):
                errors.append("preservation_audit.correction_masks must be an array")
                masks = []
            mask_ids: set[str] = set()
            stroke_mask_ids: set[str] = set()
            for i, mask in enumerate(masks):
                prefix = f"preservation_audit.correction_masks[{i}]"
                if not isinstance(mask, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                mask_id = str(mask.get("id", ""))
                if not mask_id:
                    errors.append(f"{prefix}.id is required")
                elif mask_id in mask_ids:
                    errors.append(f"duplicate correction mask id: {mask_id}")
                mask_ids.add(mask_id)
                for dimension in ("width", "height"):
                    value = mask.get(dimension)
                    if not isinstance(value, (int, float)) or value <= 0:
                        errors.append(f"{prefix}.{dimension} must be positive")
                contains_stroke_repair = mask.get("contains_stroke_repair")
                if not isinstance(contains_stroke_repair, bool):
                    errors.append(f"{prefix}.contains_stroke_repair must be boolean")
                elif contains_stroke_repair:
                    edit_kind = mask.get("edit_kind", "existing_path_repair")
                    if edit_kind in TOPOLOGY_KINDS:
                        topology_mask_kinds[mask_id] = edit_kind
                    elif edit_kind == "raster_topology_addition":
                        pass  # Source-raster additions use mandatory replay below.
                    elif edit_kind == KNOCKOUT_KIND:
                        pass  # Mandatory data-bound replay below; never an existing-path edit.
                    elif edit_kind == "existing_path_repair":
                        stroke_mask_ids.add(mask_id)
                    else:
                        errors.append(f"{prefix}.edit_kind is unsupported")
                    statuses = mask.get("statuses")
                    if (
                        not isinstance(statuses, list)
                        or not statuses
                        or any(not isinstance(status, str) or not status.strip() for status in statuses)
                        or len(set(statuses)) != len(statuses)
                    ):
                        errors.append(
                            f"{prefix}.statuses must list unique expected work-status colors"
                        )

                if not contains_stroke_repair and (mask.get("edit_kind") in TOPOLOGY_KINDS or mask.get("edit_kind") in (KNOCKOUT_KIND, "raster_topology_addition")):
                    errors.append(f"{prefix}: native topology edits must retain contains_stroke_repair=true")

            style_required = bool(stroke_mask_ids)
            if preservation.get("stroke_style_check_required") is not style_required:
                errors.append(
                    "preservation_audit.stroke_style_check_required must match whether "
                    "a correction mask contains an existing-path stroke repair (typed topology has its own mandatory gate)"
                )
            style_checks = preservation.get("stroke_style_checks")
            if not isinstance(style_checks, list):
                errors.append("preservation_audit.stroke_style_checks must be an array")
                style_checks = []
            mismatch_count = preservation.get("repaired_stroke_style_mismatches")
            if mismatch_count != 0:
                errors.append(
                    "preservation_audit.repaired_stroke_style_mismatches must equal 0"
                )

            if style_required:
                report_path = preservation.get("stroke_style_report")
                if not isinstance(report_path, str) or not report_path.strip():
                    errors.append(
                        "preservation_audit.stroke_style_report is required for stroke repairs"
                    )
                report_hash = preservation.get("stroke_style_report_sha256")
                if not isinstance(report_hash, str) or len(report_hash) != 64 or any(
                    character not in "0123456789abcdefABCDEF" for character in report_hash
                ):
                    errors.append(
                        "preservation_audit.stroke_style_report_sha256 must be a 64-character "
                        "hex digest for stroke repairs"
                    )
                if preservation.get("stroke_style_visual_review_completed") is not True:
                    errors.append(
                        "preservation_audit.stroke_style_visual_review_completed must be true "
                        "for stroke repairs"
                    )

                check_ids: set[str] = set()
                for i, check in enumerate(style_checks):
                    prefix = f"preservation_audit.stroke_style_checks[{i}]"
                    if not isinstance(check, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    check_id = str(check.get("mask_id", ""))
                    if not check_id:
                        errors.append(f"{prefix}.mask_id is required")
                    elif check_id in check_ids:
                        errors.append(f"duplicate stroke-style check mask id: {check_id}")
                    check_ids.add(check_id)
                    if check.get("passed") is not True:
                        errors.append(f"{prefix}.passed must be true")
                    for metric, maximum in STROKE_STYLE_LIMITS.items():
                        value = check.get(metric)
                        if (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(float(value))
                            or value < 0
                        ):
                            errors.append(f"{prefix}.{metric} must be a finite nonnegative number")
                        elif value > maximum:
                            errors.append(
                                f"{prefix}.{metric} exceeds the maximum {maximum:g}"
                            )
                if check_ids != stroke_mask_ids:
                    errors.append(
                        "preservation_audit.stroke_style_checks must cover every and only "
                        "stroke-repair mask"
                    )
            elif style_checks:
                errors.append(
                    "preservation_audit.stroke_style_checks must be empty when no mask "
                    "contains a stroke repair"
                )
    elif isinstance(preservation, dict):
        locked_preserve_base = (
            preservation.get("approved_base_present") is True
            and preservation.get("original_map_mode") == "preserve_supplied_map"
        )
        if locked_preserve_base and preservation.get("full_redraw_authorized") is not True:
            errors.append("vector_rebuild of an approved supplied map requires explicit full-redraw authorization")

    saved_identity = project.get("saved_native_unchanged_width_review")
    if saved_identity is not None:
        if project.get("native_unchanged_width_review") is not None:
            errors.append("Direct working and saved identity declarations are mutually exclusive")
        identity_errors, _, _ = validate_saved(saved_identity, Path(project.get("output", {}).get("pdf", "")),
            preservation=preservation)
    else:
        identity_errors, _ = validate_native_unchanged_width(
            project.get("native_unchanged_width_review"), Path(project.get("output", {}).get("pdf", "")),
            preservation=preservation)
    errors.extend(identity_errors)

    if topology_mask_kinds or project.get("topology_patch_review") is not None:
        pdf_path = Path(project.get("output", {}).get("pdf", ""))
        artifact_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest() if pdf_path.is_file() else None
        errors.extend(validate_topology_review(project.get("topology_patch_review"), artifact_hash,
                                               topology_mask_kinds, project.get("coverage_review", {}).get("source_sha256"), project.get("source_class"),
                                               project_preservation=preservation))

    raster_masks = preservation.get("correction_masks", []) if isinstance(preservation, dict) else []
    if project.get("raster_topology_review") is not None or any(m.get("edit_kind") == "raster_topology_addition" for m in raster_masks):
        errors.extend(validate_raster_topology(project.get("raster_topology_review"),
            Path(project.get("output", {}).get("pdf", "")), raster_masks,
            project.get("coverage_review", {}).get("source_sha256")))

    errors.extend(validate_neutral_knockout(project.get("neutral_knockout_review"),
        Path(project.get("output", {}).get("pdf", "")),
        preservation.get("correction_masks", []) if isinstance(preservation, dict) else [],
        project.get("coverage_review", {}).get("source_sha256")))

    directions = project.get("directions", {})
    directions_text = str(directions.get("text", ""))
    direction_major_ids = set(str(value) for value in directions.get("major_road_ids", []))
    if direction_major_ids != set(str(value) for value in major_road_ids):
        errors.append("directions.major_road_ids must exactly match navigation_context.major_road_ids")
    for road_id in major_road_ids:
        road_name = str(roads_by_id.get(str(road_id), {}).get("name", ""))
        if road_name and road_name.lower() not in directions_text.lower():
            errors.append(f"directions.text must name major road {road_name}")

    direction_access = directions.get("entrance_access", [])
    direction_pairs: dict[str, str] = {}
    for i, item in enumerate(direction_access):
        entrance_id = str(item.get("entrance_id", ""))
        public_road_id = str(item.get("public_road_id", ""))
        if entrance_id in direction_pairs:
            errors.append(f"directions.entrance_access has duplicate entrance {entrance_id}")
        direction_pairs[entrance_id] = public_road_id
        if entrance_id not in entrances_by_id:
            errors.append(f"directions.entrance_access[{i}] references an unknown entrance")
    if set(direction_pairs) != set(entrances_by_id):
        errors.append("directions.entrance_access must contain every verified entrance exactly once")
    for entrance_id, entrance in entrances_by_id.items():
        public_road_id = str(entrance.get("public_road_id", ""))
        if direction_pairs.get(entrance_id) != public_road_id:
            errors.append(f"directions entry for {entrance_id} uses the wrong public road")
        label_text = str(entrance.get("label_text", ""))
        road_name = str(roads_by_id.get(public_road_id, {}).get("name", ""))
        if label_text and label_text.lower() not in directions_text.lower():
            errors.append(f"directions.text must name entrance {label_text}")
        if road_name and road_name.lower() not in directions_text.lower():
            errors.append(f"directions.text must associate {label_text} with {road_name}")

    unresolved = project.get("unresolved_items", [])
    if unresolved:
        errors.append(f"unresolved_items must be empty for release; found {len(unresolved)}")

    qa = project.get("qa", {})
    for gate in ZERO_GATES:
        if qa.get(gate) != 0:
            errors.append(f"qa.{gate} must equal 0")
    for gate in (
        "overlay_review_completed",
        "final_render_inspected",
        "label_by_label_review_completed",
        "label_cluster_review_completed",
        "street_names_live_verified",
        "site_name_inventory_verified",
        "entrance_inventory_verified",
        "entrance_target_review_completed",
        "navigation_context_verified",
        "directions_access_verified",
    ):
        if qa.get(gate) is not True:
            errors.append(f"qa.{gate} must be true")
    if map_mode == "vector_rebuild" and qa.get("rasterized_street_geometry") != 0:
        errors.append("qa.rasterized_street_geometry must equal 0 in vector_rebuild mode")
    if map_mode == "preserve_supplied_map" and qa.get("source_map_preservation_verified") is not True:
        errors.append("qa.source_map_preservation_verified must be true in preserve_supplied_map mode")
    if map_mode == "preserve_supplied_map" and qa.get("source_transform_verified") is not True:
        errors.append("qa.source_transform_verified must be true in preserve_supplied_map mode")
    if map_mode == "preserve_supplied_map" and qa.get("approved_map_base_preserved") is not True:
        errors.append("qa.approved_map_base_preserved must be true in preserve_supplied_map mode")
    if map_mode == "preserve_supplied_map" and qa.get("correction_masks_verified") is not True:
        errors.append("qa.correction_masks_verified must be true in preserve_supplied_map mode")
    if map_mode == "preserve_supplied_map" and qa.get("repaired_stroke_style_verified") is not True:
        errors.append("qa.repaired_stroke_style_verified must be true in preserve_supplied_map mode")
    if map_mode == "preserve_supplied_map" and isinstance(preservation, dict):
        if qa.get("pixels_changed_outside_declared_correction_masks") != preservation.get(
            "pixels_changed_outside_masks"
        ):
            errors.append(
                "qa.pixels_changed_outside_declared_correction_masks must match "
                "preservation_audit.pixels_changed_outside_masks"
            )
        if qa.get("repaired_stroke_style_mismatches") != preservation.get(
            "repaired_stroke_style_mismatches"
        ):
            errors.append(
                "qa.repaired_stroke_style_mismatches must match "
                "preservation_audit.repaired_stroke_style_mismatches"
            )

    sidebar = project.get("sidebar_qa")
    if not isinstance(sidebar, dict):
        errors.append("sidebar_qa is required")
    else:
        reference = sidebar.get("legend_reference")
        if not isinstance(reference, str) or not reference.strip():
            errors.append("sidebar_qa.legend_reference is required")
        for field in (
            "legend_heading_present",
            "legend_content_and_order_verified",
            "legend_rows_left_aligned",
            "legend_labels_left_aligned",
            "lower_divider_present",
            "calendar_icon_present",
            "updated_date_present",
            "visual_review_completed",
        ):
            if sidebar.get(field) is not True:
                errors.append(f"sidebar_qa.{field} must be true")
        if sidebar.get("excessive_dead_space") is not False:
            errors.append("sidebar_qa.excessive_dead_space must be false")

        font_size = sidebar.get("legend_label_minimum_font_pt")
        if not isinstance(font_size, (int, float)) or isinstance(font_size, bool) or font_size < 9.5:
            errors.append("sidebar_qa.legend_label_minimum_font_pt must be at least 9.5")
        for dimension in ("legend_swatch_width_pt", "legend_swatch_height_pt"):
            value = sidebar.get(dimension)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 18 <= value <= 24
            ):
                errors.append(f"sidebar_qa.{dimension} must be 18-24")
        spacing = sidebar.get("legend_row_center_spacing_pt")
        if (
            not isinstance(spacing, (int, float))
            or isinstance(spacing, bool)
            or not 36 <= spacing <= 50
        ):
            errors.append("sidebar_qa.legend_row_center_spacing_pt must be 36-50")
        for alignment in ("legend_swatch_alignment_delta_px", "legend_label_alignment_delta_px"):
            value = sidebar.get(alignment)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
                or value > 2
            ):
                errors.append(f"sidebar_qa.{alignment} must be 0-2")

    output = project.get("output", {})
    if output.get("page_fit_verified") is not True:
        errors.append("output.page_fit_verified must be true")
    for key in ("svg", "pdf", "preview_png", "audit_report"):
        if not output.get(key):
            errors.append(f"output.{key} is required")
    if map_mode == "vector_rebuild":
        if output.get("vector_geometry") is not True:
            errors.append("output.vector_geometry must be true in vector_rebuild mode")
        if not output.get("geodata"):
            errors.append("output.geodata is required in vector_rebuild mode")
    if map_mode == "preserve_supplied_map" and output.get("source_map_linework_preserved") is not True:
        errors.append("output.source_map_linework_preserved must be true")
    if output.get("page_count") != 1:
        errors.append("output.page_count must equal 1")
    if output.get("back_included") is not False:
        errors.append("output.back_included must be false")
    if output.get("do_not_work_list_included") is not False:
        errors.append("output.do_not_work_list_included must be false")
    size = output.get("pdf_size_bytes")
    if not isinstance(size, int) or not 0 <= size < 300_000:
        errors.append("output.pdf_size_bytes must be below 300000")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "schemas" / "territory-project.schema.json",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        project = load_json(args.project)
        if not isinstance(project, dict):
            raise ValueError("Project root must be a JSON object")
        errors = schema_validate(project, args.schema) + semantic_validate(project)
    except ValueError as exc:
        errors = [str(exc)]

    report = {
        "status": "PASS" if not errors else "FAIL",
        "project": str(args.project),
        "error_count": len(errors),
        "errors": errors,
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
