# Curved-word glyph review

Read this when placing or reviewing curved street names. Road clearance and collisions between separate labels do not detect cramping between letters inside one word.

## Evidence and interpretation

Measure actual glyph ink from the final label layer at the declared final render scale. Isolate each rendered glyph while preserving its font, advance, transform and position; do not substitute glyph bounding boxes, a guide line, or a whole-label mask. Confirm that the isolated glyph union exactly matches the complete label ink and that this label ink matches the visible final PDF. Bind the measurement report to the exact final PDF hash. Retained-file rebinding requires documented exact raster identity to the measured artifact.

For every curved label, record actual same-label glyph overlap, ordered adjacent-pair ink overlap and edge-distance diagnostics. Keep the renderer, ink threshold and pixel units consistent across comparisons. Shared glyph-ink pixels must be zero. Inspect the full word at actual output size and in close-up: guide-induced overlapping or visibly touching letters, collapsed counters or a cramped turn block release even when road gaps pass.

A zero distance between occupied raster pixel-cell edges can result from normal kerning, rotation or antialiasing without shared ink or visible crowding. It is not an automatic failure and does not create a universal positive letter-gap threshold. When interpretation is unclear, compare the same text and regular font at the same size with its normal shaping, and inspect the glyph shapes. Preserve ordinary kerning and ligatures; do not impose blanket tracking. Smooth or reposition the label guide first; use a small local spacing adjustment only when the actual word benefits, then remeasure road gaps, the full word and nearby labels. Never shrink the font, alter map strokes or relax existing thresholds to clear the finding.

Territory 006 Woodlake Ln is the regression example: its road gaps passed while the tight turn produced one shared ink pixel between `l` and `a`. A smoother guide and a measured local spacing adjustment removed that collision without changing the road or font size. Those exact guide coordinates and spacing are not universal requirements.

## Required contract

Both the builder project and independent critic report require top-level `label_glyph_review`:

```json
{
  "schema_version": "curved-label-glyph-review-1",
  "report_path": "path to the actual glyph measurement JSON",
  "report_sha256": "SHA-256 of that measurement file",
  "curved_label_ids": ["each curved label ID exactly once"],
  "independent_visual_review": {
    "independent": true,
    "artifact_sha256": "SHA-256 of the actual final PDF",
    "curved_label_ids": ["each independently inspected curved label ID"],
    "all_curved_labels_included": true,
    "actual_size_review_completed": true,
    "closeup_review_completed": true,
    "all_curved_labels_readable": true,
    "guide_induced_crowding_count": 0,
    "evidence": "Exact final screenshot locations and the critic's observations"
  }
}
```

Use the existing measurement report fields: `artifact_sha256`, `render_scale`, `pixel_units`, `render_size`, `isolated_text_ink_not_in_original_label_layer_pixels`, and `labels`. Each curved row identifies `id`, `name`, `kind: "curve"`, positive `glyph_ink_pixels`, `same_label_glyph_overlap_pixels: 0`, `isolated_character_union_matches_label_ink: true`, `visible_final_ink_match_fraction: 1`, and `adjacent_glyph_clearances_px` entries with `pair`, finite nonnegative `gap_px` and `overlap_ink_pixels: 0`. Represent actual shaping faithfully; do not assume every Unicode character renders as one glyph.

Require exact agreement between the wrapper scope, measured curved-label scope and independent visual scope. The builder also checks against every project label with method `curved`. Include an explicit empty curved-label scope when there are none; never omit a curved word because its whole-label bounds or road gap already passed. A report hash, asserted zero or score alone does not establish visual readability: the critic must inspect the word independently.

Run the existing builder and critic deterministic gates after populating this contract. Missing, stale, incomplete or failing evidence blocks release; all existing road-gap, spread, arrow, font, preservation and score thresholds remain unchanged.
