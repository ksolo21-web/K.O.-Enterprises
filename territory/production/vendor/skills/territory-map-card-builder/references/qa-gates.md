# Release QA Gates

All critical counters must be zero:

- missing_source_roads;
- extra_generated_roads;
- disconnected_intersections;
- unnamed_required_roads;
- unclassified_roads;
- perimeter_without_inside_side;
- hidden_internal_roads;
- mixed_status_overlaps;
- colored_endpoint_artifacts;
- branch_endpoint_overshoots;
- label_collisions;
- avoidable_label_clusters;
- clipped_elements;
- unresolved_rules;
- unresolved_source_conflicts;
- rasterized_street_geometry;
- unattributed_sources in the separate audit evidence;
- on_card_source_or_audit_lines;
- unresolved_current_inventory_discrepancies.
- altered_supplied_linework;
- wrong_road_labels;
- label_street_overlaps;
- label_gap_violations;
- partially_lifted_labels;
- unnecessary_callouts;
- malformed_arrowheads;
- arrow_label_overlaps;
- arrow_arrow_overlaps;
- arrow_wrong_targets;
- arrow_unrelated_road_crossings;
- bold_street_labels;
- inconsistent_label_fonts;
- back_page_present;
- do_not_work_list_present;
- missing_verified_site_names;
- unverified_site_names;
- site_label_obstructions;
- missing_verified_entrances;
- extra_unverified_entrances;
- entrance_wrong_targets;
- entrance_arrow_label_overlaps;
- entrance_arrow_arrow_overlaps;
- entrance_arrow_unrelated_road_crossings;
- entrance_arrow_route_overlap_outside_target_radius;
- disconnected_navigation_context;
- isolated_major_road_labels;
- nonuniform_source_scaling;
- supplied_geometry_clipped;
- directions_entrance_mismatches.
- unauthorized_map_mode_change;
- pixels_changed_outside_declared_correction_masks.
- repaired_stroke_style_mismatches.

An explicit user-directed change inside a declared correction mask does not increment `altered_supplied_linework`; any supplied-linework change outside all masks does. The in-mask repair still increments `repaired_stroke_style_mismatches` when it does not match the accepted source drawing style.

Boolean gates that must be true:

- boundary_closed for the closed-polygon representation;
- boundary_no_self_intersections for the closed-polygon representation;
- vector_geometry;
- source_ids_preserved;
- corrections_persisted;
- overlay_review_completed;
- final_render_inspected;
- label_by_label_review_completed;
- label_cluster_review_completed;
- street_names_live_verified;
- current_inventory_review_completed for every territory, including all locked new drawings;
- full_boundary_and_edges_checked;
- source_retrieval_complete;
- relevant_property_eligibility_resolved;
- source_map_preservation_verified when `map_mode` is `preserve_supplied_map`.
- site_name_inventory_verified;
- entrance_inventory_verified;
- entrance_target_review_completed;
- navigation_context_verified;
- directions_access_verified;
- source_transform_verified when `map_mode` is `preserve_supplied_map`.
- approved_map_base_preserved when `map_mode` is `preserve_supplied_map`;
- correction_masks_verified when revising an approved supplied map or card.
- repaired_stroke_style_verified in `preserve_supplied_map` mode; this means every stroke-repair mask passed the analyzer and paired 4x visual review, or no stroke repair was present.
- `sidebar_qa.visual_review_completed`;
- `sidebar_qa.legend_content_and_order_verified`;
- `sidebar_qa.legend_rows_left_aligned` and `sidebar_qa.legend_labels_left_aligned`;
- `sidebar_qa.lower_divider_present`;
- `sidebar_qa.calendar_icon_present`;
- `sidebar_qa.updated_date_present`.

Numeric placement gates:

- every direct or curved label guide has a 2-15 px gap from its assigned street;
- the gap spread along a curved label is no more than 8 px, preventing one end from lifting away;
- every callout leader is 12-80 px long and starts no more than 20 px from its label;
- arrow tips terminate on the assigned street stem, not merely the cul-de-sac bulb;
- the final PDF is one page and smaller than 300,000 bytes.
- every entrance leader stays within its declared, map-scale range; the Territory 252 regression fixture uses 25-140 px on a 1725 x 1220 map;
- every entrance arrow tip falls inside its verified target box and within the declared tolerance of the access stem;
- entrance-arrow overlap with route geometry is allowed only inside the declared target radius;
- horizontal and vertical supplied-map scale values are equal within 0.001, positive, and explicitly recorded;
- every supplied colored segment remains visible after scale and translation.
- regular legend labels are at least 9.5 pt;
- legend swatches are 18-24 pt wide and 18-24 pt high;
- legend row centers are spaced consistently within 36-50 pt;
- swatch and label left-edge alignment varies by no more than 2 px;
- excessive legend/update dead space is false after output-size visual comparison with the approved sidebar reference;
- every correction mask has finite positive dimensions and a unique ID;
- an approved-card revision uses an identically sized base/candidate render and changes zero pixels outside the declared correction masks, including renderer interpolation.
- every stroke-repair mask passes the hard limits in [stroke-style-gate.md](stroke-style-gate.md) at the final 2x render and has a stored report plus SHA-256 hash;
- paired 4x crops show no visible change in stroke width, status color, edge softness/antialiasing, curvature/centerline character, texture, boundary seam, or endpoint character. Human-visible mismatch vetoes an automated pass.

Status-geometry gates:

- every physical segment has one status color only;
- every multi-status junction declares one node owner, with adjacent strokes trimmed to non-overlapping tangent endpoints;
- side branches terminate before differently colored boundary strokes and never project into or through them;
- the final 2x render contains no blended junction blobs, orphan colored dots, or cap fragments.

Arrow gates:

- arrows are prohibited whenever the full street name fits directly or along a curve;
- every arrow uses one clean leader and a visible filled triangular head;
- no leader intersects a label, another leader, or an unrelated road;
- each arrow's stored road ID must match the label's stored road ID.

Entrance and navigation gates:

- the rendered entrance count for each named site must equal its verified entrance count;
- every entrance label binds to the same entrance ID, site ID, public-road ID, and access-stem ID recorded by verification;
- each entrance arrow uses one unambiguous shaft and a bound, filled triangular marker;
- the arrow target must touch the verified access stem within its tolerance, not merely the adjacent public road, property interior, parking area, or cul-de-sac bulb;
- no entrance arrow may overlap a label, another arrow, or an unrelated road outside the small target radius;
- one centered property name is preferred when the site is named; entrance callouts then use concise labels rather than repeating that name;
- every required major road must be drawn and named, and at least one verified connected approach path must lead from it to the territory;
- directions must list every entrance and the public road that serves it.

A visually attractive card does not pass when a geographic or work-rule gate fails.

## Visual clutter gate

Collision-free is not clutter-free. Inspect each junction and its surrounding label cluster at actual output size and in close-up. Compare usable whitespace farther along the assigned street, on its opposite side, and on another suitable straight segment. Block release when an avoidable concentration of labels remains, even if each label meets the numerical gap limit. Keep road association obvious and map strokes unchanged. Record the alternatives reviewed and screenshot locations in the audit; software validates the report, not visual judgment. The separate critic must repeat this inspection independently.

Territory 254 is the regression example: Quarter St moves below its road; West St moves to the segment above Renshaw St. This separates the crowded Quarter/West labels without changing streets. Apply the placement principle elsewhere, not these exact positions. The minimum critic score is 10/10 in every category; no score can waive this gate.

## Discovery and publication evidence

Require a fresh dated `current_inventory_review` before release, with sources, dataset/imagery recency, retrieval completeness, full-boundary/edge coverage, and a feature-level comparison recording additions and every unresolved candidate. Reviewing only existing labels does not pass. An unresolved coverage boundary, relevant property eligibility, missing street, or incomplete source response blocks release regardless of visual score. Locked new drawings still require this check; report discrepancies without changing their accepted geometry unless authorized.

Inspect the full-page render and extracted text for on-card source-credit/audit lines. None may remain. Preserve supporting citations and attribution in separate audit evidence.

## Mandatory two-major-cross-road evidence

Apply [major-crossroads.md](major-crossroads.md) to every card. Require at least two distinct verified physical major roads and a complete `major_crossroad_review`. Repeated names, aliases, divided carriageways, floating labels, directions-only mentions and minor internal streets cannot count. A missing or unverified second major road hard-fails release; the critic caps at 8 with release false. Preserve accepted linework and add minimal separate-layer verified context with uniform scaling only when necessary.

## Assignment representation and complete inventory

Apply [coverage-model.md](coverage-model.md). Both polygon and explicit road-segment assignments require complete source-bound coverage and current road/property inventory evidence. Segment assignments do not invent a closed polygon, skip immediate edges or waive unresolved candidates. Require the deterministic coverage/inventory gate and independent source review before release.

## Typed native topology edits

For source-backed authorized native additions/removals only, apply [native-topology-gate.md](native-topology-gate.md). Keep `contains_stroke_repair=true`, distinguish typed topology masks from existing-path repairs, and run every applicable gate. The original repair comparator and numeric cutoffs are unchanged; do not falsely report an old centerline failure as passed or bypass it by omitting colored edits.

Require the bidirectional map-versus-housing-instructions gate in `housing-instructions.md`. The marked assignment controls obsolete housing restrictions; preserve all map-side, exclusion and other-territory/access limits. Review actual full-page text, including work notes, and record the user decision.

## Curved-word glyph gate

Require the final-artifact-bound `label_glyph_review` contract in [label-glyph-review.md](label-glyph-review.md). Cover every curved label with isolated glyph-ink union/overlap evidence and independent actual-size/close-up legibility review. Same-label shared ink and guide-induced visible overlapping/touching letters must be zero. A zero distance between occupied raster-cell edges is a diagnostic, not an automatic failure or a universal minimum letter gap. All existing road-gap, spread, arrow, font and critic-score thresholds remain unchanged.
