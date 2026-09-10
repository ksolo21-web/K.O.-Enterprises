from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_project.py"
EXAMPLE = ROOT / "examples" / "territory-project.example.json"
TERRITORY_252 = ROOT / "examples" / "territory-252-regression.json"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), str(path)], text=True, capture_output=True, timeout=20)


def add_passing_stroke_repair(data: dict) -> None:
    preservation = data["preservation_audit"]
    preservation["correction_masks"] = [
        {
            "id": "junction-repair",
            "x": 100,
            "y": 120,
            "width": 40,
            "height": 35,
            "reason": "Remove a marked junction artifact without redrawing the street",
            "contains_stroke_repair": True,
            "statuses": ["green"],
        }
    ]
    preservation["stroke_style_check_required"] = True
    preservation["stroke_style_report"] = "audit/stroke-style-report.json"
    preservation["stroke_style_report_sha256"] = "a" * 64
    preservation["stroke_style_visual_review_completed"] = True
    preservation["repaired_stroke_style_mismatches"] = 0
    preservation["stroke_style_checks"] = [
        {
            "mask_id": "junction-repair",
            "passed": True,
            "median_width_delta_px": 0.25,
            "maximum_color_delta_rgb": 3.0,
            "edge_softness_delta_px": 0.1,
            "centerline_p95_deviation_px": 0.5,
            "boundary_presence_mismatch_pixels": 0,
            "texture_delta": 0.25,
            "unexpected_status_pixel_count": 0,
        }
    ]
    data["qa"]["repaired_stroke_style_mismatches"] = 0
    data["qa"]["repaired_stroke_style_verified"] = True


def test_valid_example_passes() -> None:
    result = run(EXAMPLE)
    assert result.returncode == 0, result.stdout + result.stderr


def test_clutter_blocks_collision_free_card(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert data["qa"]["label_collisions"] == 0
    data["qa"]["avoidable_label_clusters"] = 1
    path = tmp_path / "crowded-junction.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "qa.avoidable_label_clusters must equal 0" in result.stdout


def test_missing_cluster_review_blocks_release(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    del data["qa"]["label_cluster_review_completed"]
    path = tmp_path / "missing-cluster-review.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "label_cluster_review_completed" in result.stdout


def test_undersized_legend_labels_fail(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["sidebar_qa"]["legend_label_minimum_font_pt"] = 8.5
    path = tmp_path / "undersized-legend.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "legend_label_minimum_font_pt must be at least 9.5" in result.stdout


def test_missing_calendar_icon_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["sidebar_qa"]["calendar_icon_present"] = False
    path = tmp_path / "missing-calendar.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "calendar_icon_present must be true" in result.stdout


def test_excessive_legend_dead_space_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["sidebar_qa"]["excessive_dead_space"] = True
    path = tmp_path / "legend-dead-space.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "excessive_dead_space must be false" in result.stdout


def test_territory_252_site_entrance_and_navigation_fixture_passes() -> None:
    result = run(TERRITORY_252)
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_road_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["qa"]["missing_source_roads"] = 1
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "missing_source_roads" in result.stdout


def test_status_geometry_artifacts_fail(tmp_path: Path) -> None:
    for counter in (
        "mixed_status_overlaps",
        "colored_endpoint_artifacts",
        "branch_endpoint_overshoots",
    ):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        data["qa"][counter] = 1
        path = tmp_path / f"bad-{counter}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = run(path)
        assert result.returncode == 1
        assert counter in result.stdout


def test_perimeter_without_side_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["roads"][1]["inside_side"] = "not_applicable"
    path = tmp_path / "bad-side.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "worked side" in result.stdout


def test_traced_google_geometry_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["roads"][0]["geometry_source"] = "Google Maps screenshot trace"
    path = tmp_path / "bad-source.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "prohibited" in result.stdout


def test_partially_lifted_curved_label_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["labels"][1]["guide_gap_min_px"] = 3
    data["labels"][1]["guide_gap_max_px"] = 14
    data["labels"][1]["guide_gap_spread_px"] = 11
    path = tmp_path / "bad-lift.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "partially lifted" in result.stdout


def test_unnecessary_callout_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    label = data["labels"][0]
    label["method"] = "callout"
    label["direct_fit_available"] = True
    label["arrow"] = {
        "target_road_id": "road-001",
        "target_kind": "street_stem",
        "filled_triangular_head": True,
        "leader_length_px": 40,
        "start_gap_px": 8,
        "overlaps_label": False,
        "overlaps_arrow": False,
        "crosses_unrelated_road": False,
    }
    path = tmp_path / "bad-callout.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "callout is prohibited" in result.stdout


def test_arrow_label_overlap_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    label = data["labels"][0]
    label["method"] = "callout"
    label["direct_fit_available"] = False
    label["arrow"] = {
        "target_road_id": "road-001",
        "target_kind": "street_stem",
        "filled_triangular_head": True,
        "leader_length_px": 40,
        "start_gap_px": 8,
        "overlaps_label": True,
        "overlaps_arrow": False,
        "crosses_unrelated_road": False,
    }
    path = tmp_path / "bad-arrow-overlap.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "arrow.overlaps_label" in result.stdout


def test_bold_street_label_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["labels"][0]["font_weight"] = 700
    path = tmp_path / "bad-bold.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "font_weight must be 400" in result.stdout


def test_pdf_at_300000_bytes_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["output"]["pdf_size_bytes"] = 300000
    path = tmp_path / "bad-size.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "pdf_size_bytes" in result.stdout


def test_entrance_arrow_that_misses_access_stem_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["entrances"][0]["arrow"]["distance_to_access_px"] = 20
    path = tmp_path / "bad-entrance-target.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "misses the verified access stem" in result.stdout


def test_entrance_arrow_crossing_unrelated_road_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["entrances"][1]["arrow"]["crosses_unrelated_road"] = True
    path = tmp_path / "bad-entrance-crossing.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "crosses_unrelated_road" in result.stdout


def test_missing_verified_entrance_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["entrances"].pop()
    path = tmp_path / "missing-entrance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "entrance inventory mismatch" in result.stdout


def test_disconnected_major_road_context_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["navigation_context"]["approach_paths"][0]["connected"] = False
    path = tmp_path / "disconnected-context.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert ".connected must be true" in result.stdout


def test_isolated_major_road_label_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["labels"] = [label for label in data["labels"] if label["road_id"] != "road-s-main"]
    path = tmp_path / "isolated-major-road-label.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "isolated or missing label" in result.stdout


def test_nonuniform_source_scaling_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["source_transform"]["scale_y"] = 0.74
    path = tmp_path / "nonuniform-scale.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "positive uniform scaling" in result.stdout


def test_clipped_supplied_geometry_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["source_transform"]["all_supplied_geometry_visible"] = False
    path = tmp_path / "clipped-supplied-map.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "all_supplied_geometry_visible" in result.stdout


def test_approved_map_cannot_switch_to_vector_without_authorization(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["map_mode"] = "vector_rebuild"
    data["source_transform"] = None
    data["preservation_audit"]["full_redraw_authorized"] = False
    path = tmp_path / "unauthorized-redraw.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "explicit full-redraw authorization" in result.stdout


def test_rendered_change_outside_correction_masks_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["preservation_audit"]["pixels_changed_outside_masks"] = 1
    data["qa"]["pixels_changed_outside_declared_correction_masks"] = 1
    path = tmp_path / "outside-correction-mask.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "pixels_changed_outside_masks must equal 0" in result.stdout


def test_unpreserved_approved_base_fails(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["qa"]["approved_map_base_preserved"] = False
    path = tmp_path / "approved-base-not-preserved.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "approved_map_base_preserved" in result.stdout


def test_stroke_repair_requires_style_evidence(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["preservation_audit"]["correction_masks"] = [
        {
            "id": "junction-repair",
            "x": 100,
            "y": 120,
            "width": 40,
            "height": 35,
            "contains_stroke_repair": True,
            "statuses": ["green"],
        }
    ]
    path = tmp_path / "missing-stroke-style-evidence.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "stroke_style_check_required" in result.stdout
    assert "stroke_style_checks must cover" in result.stdout


def test_stroke_width_mismatch_fails_even_when_report_says_pass(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    add_passing_stroke_repair(data)
    data["preservation_audit"]["stroke_style_checks"][0]["median_width_delta_px"] = 1.26
    path = tmp_path / "stroke-too-wide.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "median_width_delta_px exceeds the maximum 1.25" in result.stdout


def test_visible_stroke_style_review_is_mandatory(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    add_passing_stroke_repair(data)
    data["preservation_audit"]["stroke_style_visual_review_completed"] = False
    path = tmp_path / "missing-stroke-visual-review.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "stroke_style_visual_review_completed must be true" in result.stdout


def test_stroke_style_mismatch_counter_must_match_qa(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    add_passing_stroke_repair(data)
    data["preservation_audit"]["repaired_stroke_style_mismatches"] = 1
    path = tmp_path / "stroke-style-mismatch.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "repaired_stroke_style_mismatches must equal 0" in result.stdout
    assert "must match preservation_audit.repaired_stroke_style_mismatches" in result.stdout


def test_entrance_target_outside_verified_box_fails(tmp_path: Path) -> None:
    data = json.loads(TERRITORY_252.read_text(encoding="utf-8"))
    data["entrances"][0]["arrow"]["target_x"] = 610
    path = tmp_path / "outside-entrance-box.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert "outside the verified entrance box" in result.stdout
