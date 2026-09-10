"""Regression for within-word collisions missed by road/cross-label checks.

Run: python3 scripts/test_label_glyph_contract.py
Fixtures render real, separately rotated glyph ink and measure its intersection.
"""
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from label_glyph_contract import validate_label_glyph_review


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(directory, crowded=False):
    width, height = 192, 96
    font = ImageFont.truetype("DejaVuSans.ttf", 24)
    glyphs = []
    for angle in (-14, 14):
        glyph = Image.new("L", (48, 48))
        ImageDraw.Draw(glyph).text((9, 7), "W", font=font, fill=255)
        glyph = glyph.rotate(angle, resample=Image.Resampling.BICUBIC)
        glyph = glyph.crop(glyph.getbbox())
        glyphs.append(glyph)

    def placed(glyph, x):
        canvas = Image.new("L", (width, height))
        canvas.paste(glyph, (x, 10))
        return np.asarray(canvas) >= 128

    first = placed(glyphs[0], 8)
    candidates = [(x, placed(glyphs[1], x)) for x in range(9, 64)]
    last_overlap = max(x for x, mask in candidates if np.any(first & mask))
    second = placed(glyphs[1], last_overlap if crowded else last_overlap + 1)
    shared = int(np.count_nonzero(first & second))
    union = first | second
    road = np.zeros_like(union)
    road_y = int(np.where(union)[0].max()) + 7
    road[road_y, 2:92] = True
    unrelated = placed(glyphs[0], 130)
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    canvas[union | road | unrelated] = 0
    png = io.BytesIO()
    Image.fromarray(canvas).save(png, format="PNG")
    pdf = directory / "fixture.pdf"
    with fitz.open() as document:
        page = document.new_page(width=width / 2, height=height / 2)
        page.insert_image(page.rect, stream=png.getvalue())
        document.save(pdf)
    with fitz.open(pdf) as document:
        pixmap = document[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        rendered = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(height, width, 3)
    # The reported isolated glyph ink is actually present in the final artifact.
    assert np.all(rendered[union] == 0)
    row = {
        "id": "curve-1", "name": "WW", "kind": "curve",
        "glyph_ink_pixels": int(union.sum()),
        "same_label_glyph_overlap_pixels": shared,
        "isolated_character_union_matches_label_ink": bool(np.array_equal(first | second, union)),
        "visible_final_ink_match_fraction": 1.0,
        "adjacent_glyph_clearances_px": [{"pair": "WW", "gap_px": 0.0,
                                          "overlap_ink_pixels": shared}],
        "overlap_other_label_ink_pixels": int(np.count_nonzero(union & unrelated)),
        "overlap_all_road_ink_pixels": int(np.count_nonzero(union & road)),
        "glyph_gap_min_px": 6.0, "glyph_gap_max_px": 6.0,
        "glyph_gap_2_15_pass": True, "glyph_gap_spread_8_pass": True,
    }
    report = {
        "artifact_sha256": fingerprint(pdf), "render_scale": 2,
        "pixel_units": "actual final PDF 2x pixels; divide by 2 for points",
        "render_size": [width, height],
        "isolated_text_ink_not_in_original_label_layer_pixels": 0,
        "labels": [row],
    }
    report_path = directory / "measurements.json"
    report_path.write_text(json.dumps(report))
    review = {
        "schema_version": "curved-label-glyph-review-1",
        "report_path": str(report_path), "report_sha256": fingerprint(report_path),
        "curved_label_ids": ["curve-1"],
        "independent_visual_review": {
            "independent": True, "artifact_sha256": fingerprint(pdf),
            "curved_label_ids": ["curve-1"], "all_curved_labels_included": True,
            "actual_size_review_completed": True, "closeup_review_completed": True,
            "all_curved_labels_readable": True, "guide_induced_crowding_count": 0,
            "evidence": "Synthetic fixture review only; curve-1 actual-size and closeup checks.",
        },
    }
    return pdf, report, review


class GlyphContractRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.pdf, self.report, self.review = fixture(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def errors(self, labels=None):
        return validate_label_glyph_review(self.review, fingerprint(self.pdf),
            labels=labels, artifact_path=self.pdf)

    def rewrite_report(self):
        path = Path(self.review["report_path"])
        path.write_text(json.dumps(self.report))
        self.review["report_sha256"] = fingerprint(path)

    def test_actual_shared_ink_fails_while_other_labels_and_road_gaps_pass(self):
        self.pdf, self.report, self.review = fixture(self.directory, crowded=True)
        row = self.report["labels"][0]
        self.assertGreater(row["same_label_glyph_overlap_pixels"], 0)
        self.assertEqual(row["overlap_other_label_ink_pixels"], 0)
        self.assertEqual(row["overlap_all_road_ink_pixels"], 0)
        self.assertTrue(row["glyph_gap_2_15_pass"] and row["glyph_gap_spread_8_pass"])
        self.assertTrue(any("same_label_glyph_overlap_pixels" in error for error in self.errors()))

    def test_zero_cell_edge_gap_without_shared_ink_is_allowed(self):
        self.assertEqual(self.report["labels"][0]["same_label_glyph_overlap_pixels"], 0)
        self.assertEqual(self.report["labels"][0]["adjacent_glyph_clearances_px"][0]["gap_px"], 0)
        self.assertEqual(self.errors(), [])

    def test_missing_review_and_stale_report_fail_closed(self):
        self.assertTrue(validate_label_glyph_review(None, fingerprint(self.pdf)))
        Path(self.review["report_path"]).write_text("{}")
        self.assertTrue(any("file/hash mismatch" in error for error in self.errors()))

    def test_stale_artifact_and_false_union_fail_closed(self):
        self.report["artifact_sha256"] = "0" * 64
        self.report["labels"][0]["isolated_character_union_matches_label_ink"] = False
        self.rewrite_report()
        errors = self.errors()
        self.assertTrue(any("exact current final PDF" in error for error in errors))
        self.assertTrue(any("union" in error for error in errors))

    def test_scope_must_include_every_builder_curved_label(self):
        labels = [{"id": "curve-1", "text": "WW", "method": "curved"},
                  {"id": "curve-2", "text": "Other", "method": "curved"}]
        self.assertTrue(any("every and only builder curved label" in error for error in self.errors(labels)))

    def test_guide_induced_crowding_cannot_be_waived_by_zero_overlap(self):
        self.review["independent_visual_review"]["guide_induced_crowding_count"] = 1
        self.assertTrue(any("guide-induced crowding" in error for error in self.errors()))

    def test_visual_scope_and_actual_size_review_are_required(self):
        self.review["independent_visual_review"]["curved_label_ids"] = []
        self.review["independent_visual_review"]["actual_size_review_completed"] = False
        errors = self.errors()
        self.assertTrue(any("every curved label ID" in error for error in errors))
        self.assertTrue(any("actual_size_review_completed" in error for error in errors))

    def test_missing_nonfinite_boolean_and_pair_overlap_evidence_fail(self):
        original = copy.deepcopy(self.report)
        for field, value in (("same_label_glyph_overlap_pixels", False),
                             ("glyph_ink_pixels", 0),
                             ("visible_final_ink_match_fraction", None)):
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                self.report["labels"][0][field] = value
                self.rewrite_report()
                self.assertTrue(self.errors())
        self.report = copy.deepcopy(original)
        self.report["labels"][0]["adjacent_glyph_clearances_px"][0].update(
            gap_px=float("nan"), overlap_ink_pixels=1)
        self.rewrite_report()
        errors = self.errors()
        self.assertTrue(any("finite" in error for error in errors))
        self.assertTrue(any("shared glyph ink" in error for error in errors))

    def test_render_scale_and_dimensions_must_agree_with_pdf(self):
        self.report["render_scale"] = 3
        self.rewrite_report()
        self.assertTrue(any("render_size/scale" in error for error in self.errors()))

    def test_empty_curved_scope_requires_explicit_complete_review(self):
        self.report["labels"] = []
        self.review["curved_label_ids"] = []
        self.review["independent_visual_review"]["curved_label_ids"] = []
        self.rewrite_report()
        self.assertEqual(self.errors(labels=[]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
