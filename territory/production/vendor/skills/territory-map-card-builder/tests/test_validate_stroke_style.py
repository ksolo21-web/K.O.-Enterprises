from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_stroke_style.py"
SPEC = importlib.util.spec_from_file_location("validate_stroke_style", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


GREEN = (96, 198, 74)
YELLOW = (214, 211, 24)
RED = (216, 73, 62)


def approved_line() -> np.ndarray:
    scale = 4
    high = Image.new("RGB", (160 * scale, 100 * scale), "white")
    draw = ImageDraw.Draw(high)
    draw.line((10 * scale, 50 * scale, 150 * scale, 50 * scale), fill=GREEN, width=8 * scale)
    return np.asarray(high.resize((160, 100), Image.Resampling.LANCZOS), dtype=np.int16)


def approved_multistatus_junction() -> np.ndarray:
    scale = 4
    high = Image.new("RGB", (160 * scale, 100 * scale), "white")
    draw = ImageDraw.Draw(high)
    draw.line((10 * scale, 50 * scale, 76 * scale, 50 * scale), fill=GREEN, width=8 * scale)
    draw.line((80 * scale, 8 * scale, 80 * scale, 92 * scale), fill=YELLOW, width=6 * scale)
    draw.line((84 * scale, 50 * scale, 150 * scale, 50 * scale), fill=RED, width=4 * scale)
    return np.asarray(high.resize((160, 100), Image.Resampling.LANCZOS), dtype=np.int16)


def config() -> dict:
    return {
        "palette": {"green": list(GREEN), "yellow": list(YELLOW), "red": list(RED)},
        "reference_ring_px": 24,
        "masks": [
            {
                "id": "repair",
                "x": 60,
                "y": 34,
                "width": 40,
                "height": 32,
                "contains_stroke_repair": True,
                "statuses": ["green"],
            }
        ],
    }


def test_unchanged_source_style_passes() -> None:
    base = approved_line()
    report = MODULE.analyze(base, base.copy(), config())
    assert report["status"] == "PASS", report
    assert report["repaired_stroke_style_mismatches"] == 0


def test_thicker_repaired_stroke_fails() -> None:
    base = approved_line()
    candidate_image = Image.fromarray(base.astype(np.uint8), mode="RGB")
    ImageDraw.Draw(candidate_image).line((65, 50, 95, 50), fill=GREEN, width=15)
    report = MODULE.analyze(base, np.asarray(candidate_image, dtype=np.int16), config())
    assert report["status"] == "FAIL"
    assert any("stroke_width" in failure for failure in report["results"][0]["failures"])


def test_shifted_repaired_stroke_fails_curvature_or_seam() -> None:
    base = approved_line()
    candidate_image = Image.fromarray(base.astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(candidate_image)
    draw.rectangle((64, 42, 96, 58), fill="white")
    draw.line((64, 55, 96, 55), fill=GREEN, width=8)
    report = MODULE.analyze(base, np.asarray(candidate_image, dtype=np.int16), config())
    assert report["status"] == "FAIL"
    failures = report["results"][0]["failures"]
    assert any("centerline_curvature" in failure or "boundary_seam" in failure for failure in failures)


def test_wrong_work_status_color_fails() -> None:
    base = approved_line()
    candidate_image = Image.fromarray(base.astype(np.uint8), mode="RGB")
    ImageDraw.Draw(candidate_image).line((64, 50, 96, 50), fill=RED, width=8)
    report = MODULE.analyze(base, np.asarray(candidate_image, dtype=np.int16), config())
    assert report["status"] == "FAIL"
    assert any("unexpected_status_pixels" in failure for failure in report["results"][0]["failures"])


def test_change_outside_declared_mask_fails() -> None:
    base = approved_line()
    candidate = base.copy()
    candidate[5, 5] = (0, 0, 0)
    report = MODULE.analyze(base, candidate, config())
    assert report["status"] == "FAIL"
    assert report["pixels_changed_outside_declared_masks"] == 1


def test_thresholds_cannot_be_loosened() -> None:
    base = approved_line()
    unsafe = config()
    unsafe["thresholds"] = {"max_median_width_delta_px": 20}
    try:
        MODULE.analyze(base, base.copy(), unsafe)
    except ValueError as exc:
        assert "Invalid threshold" in str(exc)
    else:
        raise AssertionError("A looser stroke-style threshold was accepted")


def test_changed_pixel_tolerance_cannot_hide_outside_changes() -> None:
    base = approved_line()
    unsafe = config()
    unsafe["changed_pixel_tolerance"] = 1
    try:
        MODULE.analyze(base, base.copy(), unsafe)
    except ValueError as exc:
        assert "changed_pixel_tolerance must remain 0" in str(exc)
    else:
        raise AssertionError("A nonzero changed-pixel tolerance was accepted")


def test_multistatus_junction_compares_each_status_separately() -> None:
    base = approved_multistatus_junction()
    multi = config()
    multi["masks"][0]["statuses"] = ["green", "yellow", "red"]
    multi["masks"][0]["reference_boxes"] = {
        "green": {"x": 10, "y": 40, "width": 35, "height": 20},
        "yellow": {"x": 72, "y": 8, "width": 18, "height": 22},
        "red": {"x": 115, "y": 40, "width": 35, "height": 20},
    }
    report = MODULE.analyze(base, base.copy(), multi)
    assert report["status"] == "PASS", report
    metrics = report["results"][0]["status_metrics"]
    widths = {name: round(value["repaired_median_width_px"], 2) for name, value in metrics.items()}
    assert len(set(widths.values())) > 1, widths
    assert all(value["median_width_delta_px"] == 0 for value in metrics.values())


def test_low_level_resampling_noise_does_not_create_centerline_failure() -> None:
    base = approved_line()
    candidate = base.copy()
    # Simulate final-PDF resampling noise on existing ridge pixels.  It is a
    # real pixel delta for the exact outside-mask audit, but not a material
    # geometry change for the curvature calculation.
    candidate[49:52, 65:96] = np.clip(candidate[49:52, 65:96] + 3, 0, 255)
    report = MODULE.analyze(base, candidate, config())
    assert report["status"] == "PASS", report
    result = report["results"][0]
    assert result["metrics"]["centerline_p95_deviation_px"] == 0
