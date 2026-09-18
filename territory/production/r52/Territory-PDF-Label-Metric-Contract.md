# Territory PDF Label Metrics & Delivery Contract — R51 — 2026-09-13

## Purpose
R51 closes two failure classes that survived earlier visual review: inconsistent label-to-road offsets that still looked "close enough," and image-only territory outputs being shown as if they were deliverables. This contract supplements R50 and is a hard release gate.

## 1. PDF is the only release artifact
For territory-card creation, rebuild, redraw, conversion, or update, the user-facing release artifact is the canonical **PDF** (`Territory - NNN...pdf`). PNG/JPG/WebP renders are evidence/previews only.

Release requires `delivery_format_review` bound to the exact artifact SHA-256:
- `artifact_filename` ends in `.pdf` and matches the canonical territory filename;
- `artifact_mime_type: application/pdf`;
- `final_user_deliverable_pdf: true`;
- `image_preview_only: true`;
- `vector_or_native_map_geometry: true` for rebuilt/new maps;
- `pdf_openable: true`, `single_page: true`, `encrypted: false`;
- `bytes < 300000` per standing territory-card limit.

An image-generation output may guide a rebuild but can never be the final answer artifact or satisfy release review.

## 2. Measured road-gap baseline
The exact final PDF is rendered at 1x/72 dpi. For each ordinary direct/curved label, measure the nearest visible glyph-ink edge to its assigned road stroke. Existing R50 hard range 2–15 px remains; preferred 4–10 px remains.

In addition, each card establishes a **same-card reference gap baseline** from at least three clearly successful ordinary labels selected before evaluating disputed/outlier labels. Record `reference_label_ids[]`, their measured gaps, the median, and a default consistency tolerance of 3 px.

Labels explicitly marked `match_reference_gap: true` must stay within `median ± tolerance` unless a documented geometry exception is independently accepted. This catches labels that float noticeably higher/lower than otherwise good labels even while remaining within the broad 2–15 px hard band.

The reviewer must not choose the disputed label itself as a reference label.

## 3. Navigation repeats on long/complex roads
A road inventory record may require more than one label where one name placement is insufficient for field navigation, including long roads with distinct runs, entrances, or turns.

Each named-public road record must carry `required_label_count >= 1`. When `navigation_repeat_required: true`, `required_label_count >= 2`, and the rendered/decision ledgers must contain at least that many distinct label IDs on materially separated runs.

Duplicate labels are not decorative repetition. Each must have a declared `navigation_role` such as `west_run`, `entrance_run`, `east_run`, `north_run`, or `detail_run` and must independently pass gap/contact/clutter checks.

## 4. Curved labels must follow the whole local run
For labels on visibly bending streets, straight placement is acceptable only where the selected local run is genuinely straight enough. Otherwise use a curved label whose sampled baseline/tangent follows the road. Curved labels retain R50/R45 glyph integrity and 2–15 px road-gap rules.

A label that merely rotates beside a curve but visibly departs from it at one end fails. Roanoke-style curved/diagonal streets must be judged over the whole word, not only its center.

## 5. Cluster-aware repeated-label placement
Adding a second label may not create a new cluster. Repeated labels and adjacent short-road callouts must still satisfy the R50 cluster trigger and same-road alternative review. A repeated label must improve navigation without reducing local legibility.

## 6. Reviewer duties
The builder records measurements; the critic/internal reviewer independently remeasures all disputed/outlier labels and a sample of at least three reference labels from fresh exact-PDF renders.

`label_metric_review` must include:
- exact artifact SHA-256;
- `measurement_reference: exact_final_pdf_1x_72dpi`;
- at least three `reference_label_ids` and `reference_gap_values_px`;
- `reference_gap_median_px`;
- `consistency_tolerance_px` (default 3);
- `reference_gap_consistency_passed: true`;
- `outlier_label_count: 0`;
- `label_metrics[]` for every label placement;
- `repeat_label_groups[]` for roads requiring repeated labels;
- reviewer remeasurement fields in critic/internal review.

A validator PASS proves report consistency only; actual visual placement remains a mandatory reviewer judgment.

## R52 Semantic attachment and terminal-word measurements
R51 count and gap metrics are necessary, not sufficient. Add the source-bound role/segment lock and `label_navigation_review`/`critic_label_navigation_review` from `Territory-Segment-Role-Whole-Label-Contract.md`. Check actual PDF arrow endpoints against the intended entrance/run, not any same-colored/same-named road. Inspect local contour and clearance for the full name and suffix and verify actual PDF font advances; zero ink overlap does not excuse visible crowding. Keep the same-card gap band and every earlier numeric limit. Run `validate_label_navigation_contract.py` in addition to this metric validator. Fixture-specific 269 coordinates/native-width tolerances are not universal label-placement values.