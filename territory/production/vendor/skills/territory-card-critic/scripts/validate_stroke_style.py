#!/usr/bin/env python3
"""Compare repaired street strokes with nearby untouched approved strokes.

The gate is deliberately local.  It checks only masks declared as containing a
stroke repair, learns the approved drawing characteristics from the surrounding
untouched source, and fails when a repair changes the visible drawing language.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


DEFAULT_THRESHOLDS = {
    "max_median_width_delta_px": 1.25,
    "max_color_delta_rgb": 18.0,
    "max_edge_softness_delta_px": 0.85,
    "max_centerline_p95_deviation_px": 2.0,
    "max_boundary_presence_mismatch_pixels": 0,
    "max_texture_delta": 2.5,
    "max_unexpected_status_pixels": 0,
}
FAIL_SENTINEL = 1_000_000.0
DEFAULT_CORE_COLOR_TOLERANCE = 55.0
DEFAULT_FRINGE_COLOR_TOLERANCE = 120.0
DEFAULT_REFERENCE_RING_PX = 24
MINIMUM_STATUS_PIXELS = 6
# Final PDF compositing can perturb otherwise unchanged antialiased pixels by a
# few RGB levels.  Curvature is therefore measured only on ridge pixels whose
# Euclidean RGB change is larger than this fixed, non-configurable noise floor.
# Width, color, softness, texture, seams, and all outside-mask changes remain
# independently fail-closed.
MATERIAL_CHANGE_RGB_DISTANCE = 6.0


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be an object")
    return value


def load_rgb(path: Path) -> np.ndarray:
    try:
        return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    except OSError as exc:
        raise ValueError(f"Cannot read image {path}: {exc}") from exc


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ValueError(f"Cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def parse_palette(config: dict[str, Any]) -> tuple[list[str], np.ndarray]:
    palette = config.get("palette")
    if not isinstance(palette, dict) or not palette:
        raise ValueError("config.palette must be a non-empty object of RGB colors")
    names: list[str] = []
    values: list[list[int]] = []
    for name, rgb in palette.items():
        if (
            not isinstance(name, str)
            or not isinstance(rgb, list)
            or len(rgb) != 3
            or any(not isinstance(channel, int) or not 0 <= channel <= 255 for channel in rgb)
        ):
            raise ValueError(f"Invalid palette entry for {name!r}")
        names.append(name)
        values.append(rgb)
    return names, np.asarray(values, dtype=np.int16)


def palette_assignment(image: np.ndarray, colors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    delta = image[:, :, None, :] - colors[None, None, :, :]
    distance = np.sqrt(np.sum(delta.astype(np.float64) ** 2, axis=3))
    return np.argmin(distance, axis=2), np.min(distance, axis=2)


def box_mask(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    height, width = shape
    x, y, box_width, box_height = box
    if x < 0 or y < 0 or box_width <= 0 or box_height <= 0 or x + box_width > width or y + box_height > height:
        raise ValueError(f"Correction mask {box} falls outside image bounds {width}x{height}")
    result = np.zeros(shape, dtype=bool)
    result[y : y + box_height, x : x + box_width] = True
    return result


def expanded_ring(mask: np.ndarray, pixels: int, exclusions: np.ndarray) -> np.ndarray:
    outer = ndi.binary_dilation(mask, iterations=pixels)
    return outer & ~mask & ~exclusions


def ridge_mask(binary: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    distance = ndi.distance_transform_edt(binary)
    local_maximum = distance >= ndi.maximum_filter(distance, size=3, mode="constant") - 1e-9
    ridge = binary & local_maximum & (distance >= 1.0)
    return ridge, distance


def median_stroke_width(binary: np.ndarray, region: np.ndarray) -> float:
    ridge, distance = ridge_mask(binary)
    samples = 2.0 * distance[ridge & region]
    if samples.size < 3:
        return math.nan
    return float(np.median(samples))


def edge_softness(core: np.ndarray, fringe: np.ndarray, region: np.ndarray) -> float:
    selected_core = core & region
    selected_fringe = fringe & region
    perimeter = selected_core & ~ndi.binary_erosion(core)
    perimeter_count = int(perimeter.sum())
    if perimeter_count < 3:
        return math.nan
    transition_area = max(0, int(selected_fringe.sum()) - int(selected_core.sum()))
    return float(transition_area / perimeter_count)


def texture_measure(image: np.ndarray, core: np.ndarray, region: np.ndarray) -> float:
    interior = ndi.binary_erosion(core) & region
    if int(interior.sum()) < 8:
        interior = core & region
    if int(interior.sum()) < 8:
        return math.nan
    luminance = image.astype(np.float64).mean(axis=2)
    local_average = ndi.gaussian_filter(luminance, sigma=0.8)
    residual = np.abs(luminance - local_average)
    return float(np.mean(residual[interior]))


def finite_delta(left: float, right: float) -> float:
    if not math.isfinite(left) or not math.isfinite(right):
        return FAIL_SENTINEL
    return abs(left - right)


def analyze(base: np.ndarray, candidate: np.ndarray, config: dict[str, Any]) -> dict[str, Any]:
    if base.shape != candidate.shape:
        return {
            "status": "FAIL",
            "error": f"Image dimensions differ: {base.shape} vs {candidate.shape}",
            "results": [],
        }

    height, width, _ = base.shape
    names, colors = parse_palette(config)
    name_to_index = {name: index for index, name in enumerate(names)}
    masks = config.get("masks")
    if not isinstance(masks, list):
        raise ValueError("config.masks must be an array")

    thresholds = dict(DEFAULT_THRESHOLDS)
    supplied_thresholds = config.get("thresholds", {})
    if not isinstance(supplied_thresholds, dict):
        raise ValueError("config.thresholds must be an object")
    for key, value in supplied_thresholds.items():
        if (
            key not in thresholds
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
            or float(value) > DEFAULT_THRESHOLDS[key]
        ):
            raise ValueError(f"Invalid threshold {key}")
        thresholds[key] = float(value)

    core_value = config.get("core_color_tolerance", DEFAULT_CORE_COLOR_TOLERANCE)
    fringe_value = config.get("fringe_color_tolerance", DEFAULT_FRINGE_COLOR_TOLERANCE)
    ring_value = config.get("reference_ring_px", DEFAULT_REFERENCE_RING_PX)
    minimum_value = config.get("minimum_status_pixels", MINIMUM_STATUS_PIXELS)
    changed_tolerance = config.get("changed_pixel_tolerance", 0)
    if (
        isinstance(core_value, bool)
        or not isinstance(core_value, (int, float))
        or not math.isfinite(float(core_value))
        or not 0 < float(core_value) <= DEFAULT_CORE_COLOR_TOLERANCE
    ):
        raise ValueError("core_color_tolerance must be positive and no greater than 55")
    if (
        isinstance(fringe_value, bool)
        or not isinstance(fringe_value, (int, float))
        or not math.isfinite(float(fringe_value))
        or not float(core_value) < float(fringe_value) <= DEFAULT_FRINGE_COLOR_TOLERANCE
    ):
        raise ValueError("fringe_color_tolerance must exceed core and be no greater than 120")
    if isinstance(ring_value, bool) or not isinstance(ring_value, int) or not 8 <= ring_value <= 48:
        raise ValueError("reference_ring_px must be an integer from 8 through 48")
    if (
        isinstance(minimum_value, bool)
        or not isinstance(minimum_value, int)
        or minimum_value < MINIMUM_STATUS_PIXELS
    ):
        raise ValueError("minimum_status_pixels must be an integer of at least 6")
    if isinstance(changed_tolerance, bool) or changed_tolerance != 0:
        raise ValueError("changed_pixel_tolerance must remain 0")
    core_tolerance = float(core_value)
    fringe_tolerance = float(fringe_value)
    reference_ring_px = ring_value
    minimum_status_pixels = minimum_value

    base_class, base_distance = palette_assignment(base, colors)
    candidate_class, candidate_distance = palette_assignment(candidate, colors)
    base_core = base_distance <= core_tolerance
    candidate_core = candidate_distance <= core_tolerance
    base_fringe = base_distance <= fringe_tolerance
    candidate_fringe = candidate_distance <= fringe_tolerance

    all_declared = np.zeros((height, width), dtype=bool)
    parsed_masks: list[tuple[dict[str, Any], np.ndarray]] = []
    ids: set[str] = set()
    for index, item in enumerate(masks):
        if not isinstance(item, dict):
            raise ValueError(f"masks[{index}] must be an object")
        mask_id = str(item.get("id", ""))
        if not mask_id or mask_id in ids:
            raise ValueError(f"Mask IDs must be non-empty and unique: {mask_id!r}")
        ids.add(mask_id)
        values = tuple(item.get(key) for key in ("x", "y", "width", "height"))
        if any(not isinstance(value, int) for value in values):
            raise ValueError(f"Mask {mask_id} coordinates must be integers")
        region = box_mask((height, width), values)  # type: ignore[arg-type]
        all_declared |= region
        parsed_masks.append((item, region))

    raw_delta = np.max(np.abs(base - candidate), axis=2)
    rgb_delta = np.linalg.norm((candidate - base).astype(np.float64), axis=2)
    materially_changed = rgb_delta > MATERIAL_CHANGE_RGB_DISTANCE
    changed = raw_delta > 0
    outside_count = int((changed & ~all_declared).sum())

    results: list[dict[str, Any]] = []
    style_failure_count = 0
    for item, region in parsed_masks:
        if item.get("contains_stroke_repair") is not True:
            continue
        mask_id = str(item["id"])
        requested_statuses = item.get("statuses")
        if not isinstance(requested_statuses, list) or not requested_statuses:
            raise ValueError(f"Stroke-repair mask {mask_id} must list statuses")
        unknown = [status for status in requested_statuses if status not in name_to_index]
        if unknown:
            raise ValueError(f"Mask {mask_id} uses unknown statuses: {unknown}")

        ring = expanded_ring(region, reference_ring_px, all_declared)
        reference_boxes = item.get("reference_boxes", {})
        if not isinstance(reference_boxes, dict):
            raise ValueError(f"Mask {mask_id} reference_boxes must be an object")
        status_metrics: dict[str, Any] = {}
        maximum_color_delta = 0.0
        maximum_width_delta = 0.0
        maximum_softness_delta = 0.0
        maximum_texture_delta = 0.0
        failures: list[str] = []
        for status in requested_statuses:
            status_index = name_to_index[status]
            reference_region = ring
            if status in reference_boxes:
                reference_box = reference_boxes[status]
                if not isinstance(reference_box, dict):
                    raise ValueError(f"Mask {mask_id} reference box for {status} must be an object")
                values = tuple(reference_box.get(key) for key in ("x", "y", "width", "height"))
                if any(not isinstance(value, int) for value in values):
                    raise ValueError(f"Mask {mask_id} reference box for {status} must use integers")
                reference_region = box_mask((height, width), values) & ~all_declared  # type: ignore[arg-type]

            candidate_status_core = candidate_core & (candidate_class == status_index)
            candidate_status_fringe = candidate_fringe & (candidate_class == status_index)
            approved_status_core = base_core & (base_class == status_index)
            approved_status_fringe = base_fringe & (base_class == status_index)
            candidate_pixels = candidate[
                region & candidate_status_core
            ]
            reference_pixels = base[
                reference_region & approved_status_core
            ]
            if len(candidate_pixels) < minimum_status_pixels:
                failures.append(f"{status}:insufficient_repaired_pixels")
                color_delta = FAIL_SENTINEL
            elif len(reference_pixels) < minimum_status_pixels:
                failures.append(f"{status}:insufficient_untouched_reference_pixels")
                color_delta = FAIL_SENTINEL
            else:
                repaired_median = np.median(candidate_pixels, axis=0)
                reference_median = np.median(reference_pixels, axis=0)
                color_delta = float(np.linalg.norm(repaired_median - reference_median))

            candidate_width = median_stroke_width(candidate_status_fringe, region)
            approved_local_width = median_stroke_width(approved_status_fringe, region)
            width_delta = finite_delta(candidate_width, approved_local_width)
            candidate_softness = edge_softness(
                candidate_status_core, candidate_status_fringe, region
            )
            approved_local_softness = edge_softness(
                approved_status_core, approved_status_fringe, region
            )
            softness_delta = finite_delta(candidate_softness, approved_local_softness)
            candidate_texture = texture_measure(candidate, candidate_status_core, region)
            approved_local_texture = texture_measure(base, approved_status_core, region)
            texture_delta = finite_delta(candidate_texture, approved_local_texture)

            maximum_color_delta = max(maximum_color_delta, color_delta)
            maximum_width_delta = max(maximum_width_delta, width_delta)
            maximum_softness_delta = max(maximum_softness_delta, softness_delta)
            maximum_texture_delta = max(maximum_texture_delta, texture_delta)
            status_metrics[status] = {
                "repaired_core_pixels": int(len(candidate_pixels)),
                "reference_core_pixels": int(len(reference_pixels)),
                "median_color_delta_rgb": color_delta,
                "repaired_median_width_px": candidate_width,
                "approved_local_median_width_px": approved_local_width,
                "median_width_delta_px": width_delta,
                "repaired_edge_softness_px": candidate_softness,
                "approved_local_edge_softness_px": approved_local_softness,
                "edge_softness_delta_px": softness_delta,
                "repaired_texture": candidate_texture,
                "approved_local_texture": approved_local_texture,
                "texture_delta": texture_delta,
            }

        expected_indices = {name_to_index[status] for status in requested_statuses}
        unexpected_status_pixels: dict[str, int] = {}
        unexpected_added_total = 0
        for status, status_index in name_to_index.items():
            if status_index in expected_indices:
                continue
            repaired_count = int((region & candidate_core & (candidate_class == status_index)).sum())
            approved_count = int((region & base_core & (base_class == status_index)).sum())
            added = max(0, repaired_count - approved_count)
            if added:
                unexpected_status_pixels[status] = added
                unexpected_added_total += added

        # Centerline is a geometry check across the complete colored route.  It
        # deliberately does not split at status handoffs: cleaning an overlapped
        # green/yellow/red ownership transition must not look like a geometric
        # bend merely because the color boundary moved along the same source
        # path.  Only materially changed ridge samples are evaluated, so minor
        # final-PDF resampling on otherwise unchanged pixels is ignored here.
        candidate_ridge, _ = ridge_mask(candidate_fringe)
        approved_ridge, _ = ridge_mask(base_fringe)
        candidate_changed_ridge = candidate_ridge & region & materially_changed
        approved_search = approved_ridge & ndi.binary_dilation(
            region, iterations=reference_ring_px
        )
        if int(candidate_changed_ridge.sum()) == 0:
            centerline_delta = 0.0
        elif int(approved_search.sum()) < 3:
            centerline_delta = FAIL_SENTINEL
        else:
            distance_to_approved = ndi.distance_transform_edt(~approved_search)
            centerline_delta = float(
                np.percentile(distance_to_approved[candidate_changed_ridge], 95)
            )

        inner_boundary = region & ~ndi.binary_erosion(region, iterations=1)
        boundary_mismatch = int(((candidate_fringe ^ base_fringe) & inner_boundary).sum())

        checks = (
            ("stroke_width", maximum_width_delta, thresholds["max_median_width_delta_px"]),
            ("stroke_color", maximum_color_delta, thresholds["max_color_delta_rgb"]),
            ("edge_softness", maximum_softness_delta, thresholds["max_edge_softness_delta_px"]),
            ("centerline_curvature", centerline_delta, thresholds["max_centerline_p95_deviation_px"]),
            ("boundary_seam", float(boundary_mismatch), thresholds["max_boundary_presence_mismatch_pixels"]),
            ("stroke_texture", maximum_texture_delta, thresholds["max_texture_delta"]),
            ("unexpected_status_pixels", float(unexpected_added_total), thresholds["max_unexpected_status_pixels"]),
        )
        for check_name, value, maximum in checks:
            if not math.isfinite(value) or value > maximum:
                failures.append(f"{check_name}:{value:.3f}>{maximum:.3f}")

        passed = not failures
        if not passed:
            style_failure_count += 1
        results.append(
            {
                "mask_id": mask_id,
                "mask_bounds": {
                    key: item[key] for key in ("x", "y", "width", "height")
                },
                "expected_statuses": requested_statuses,
                "passed": passed,
                "failures": failures,
                "status_metrics": status_metrics,
                "metrics": {
                    "median_width_delta_px": maximum_width_delta,
                    "maximum_color_delta_rgb": maximum_color_delta,
                    "edge_softness_delta_px": maximum_softness_delta,
                    "materially_changed_ridge_pixels": int(candidate_changed_ridge.sum()),
                    "centerline_p95_deviation_px": centerline_delta,
                    "boundary_presence_mismatch_pixels": boundary_mismatch,
                    "texture_delta": maximum_texture_delta,
                    "unexpected_status_pixels": unexpected_status_pixels,
                    "unexpected_status_pixel_count": unexpected_added_total,
                },
                "thresholds": thresholds,
            }
        )

    if not results:
        style_failure_count += 1
    status = "PASS" if outside_count == 0 and style_failure_count == 0 else "FAIL"
    return {
        "status": status,
        "image_size": [width, height],
        "analysis_parameters": {
            "palette": {name: colors[index].tolist() for index, name in enumerate(names)},
            "core_color_tolerance": core_tolerance,
            "fringe_color_tolerance": fringe_tolerance,
            "reference_ring_px": reference_ring_px,
            "minimum_status_pixels": minimum_status_pixels,
            "changed_pixel_tolerance": 0,
            "material_change_rgb_distance": MATERIAL_CHANGE_RGB_DISTANCE,
            "thresholds": thresholds,
        },
        "changed_pixel_count": int(changed.sum()),
        "pixels_changed_outside_declared_masks": outside_count,
        "stroke_repair_masks_checked": len(results),
        "repaired_stroke_style_mismatches": style_failure_count,
        "results": results,
    }


def serializable_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    """Keep unavailable measurements as explicit failures, never a JSON crash."""
    unavailable: list[str] = []

    def visit(value: Any, path: str) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            unavailable.append(path)
            return None
        if isinstance(value, dict):
            return {key: visit(item, f"{path}.{key}") for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item, f"{path}[{index}]") for index, item in enumerate(value)]
        return value

    result = visit(report, "report")
    if unavailable:
        result["status"] = "FAIL"
        result["unavailable_numeric_measurements"] = unavailable
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True, help="Approved render")
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate render at identical dimensions")
    parser.add_argument("--config", type=Path, required=True, help="Palette, masks, and optional thresholds")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        report = analyze(load_rgb(args.base), load_rgb(args.candidate), load_json(args.config))
        report["evidence_sha256"] = {
            "approved_render": file_sha256(args.base),
            "candidate_render": file_sha256(args.candidate),
            "configuration": file_sha256(args.config),
        }
    except ValueError as exc:
        report = {"status": "FAIL", "error": str(exc), "results": []}

    report = serializable_diagnostics(report)
    text = json.dumps(report, indent=2, allow_nan=False)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
