# Authorized native-PDF topology patch gate

Use this bounded gate only for a source-backed native path addition/removal in an authorized legacy update, or an explicitly authorized scoped edit to locked linework. It is not permission to redraw a map or change work assignments. Keep the original existing-path stroke comparator and every numeric cutoff unchanged.

## Declare the independent expected change

Retain the original assignment, the text-free source, the original-geometry final-layout baseline, the source-backed plan and provenance before evaluating the candidate. The expected native operations must come from retained source evidence and a plan established before the candidate, never from tracing or extracting the candidate. An earlier independently authored repair script may be the retained plan origin; bind its exact hash and identify the source/endpoint review. A newly wrapped JSON plan may cite that prior origin honestly; do not claim the wrapper itself predates an existing candidate. Independent review must verify this provenance; file dates or a true flag alone do not prove it.

The original-geometry baseline must use the exact final layout/labels and unchanged original source-map geometry. If a layout revision changes that baseline, refresh its hash while retaining the original independently declared topology operations. Do not build a substitute geometry authority from the candidate. Keep original failed existing-path reports as history, not rewritten passes.

Independently verify the source-relative order of neighboring verified streets and junctions when registering a local legacy-road addition. Matching two endpoint anchors is insufficient: the proposed departure, bend or junction must remain on the correct side of every relevant neighboring connection. Compare the raw source and proposed geometry together before approving the plan. For example, a ramp departure verified between Green Hollow and Meadowbrook must remain between them even if a different placement fits its endpoints. Inspect these relationships again in the actual final map; a numeric native-identity pass does not establish correct geographic registration.

Use plan schema `native-topology-patch-1`:

- `source_class`: `legacy_update_candidate` or `locked_new_drawing`;
- `correction_authority`: `authorized=true`, specific `evidence`, and `explicit_locked_edit_authorized=true` for locked sources;
- `original_assignment`: `{path, sha256, page_index}` for the immutable supplied source;
- `base_source_sha256`, `source_page_index`, `baseline_final_sha256`, `final_page_index=0`;
- `plan_origin`: `{path, sha256, predates_candidate:true, evidence}` binding the retained prior native plan/script;
- `independent_plan_review`: `{independent:true, source_geometry_verified:true, not_candidate_derived:true, evidence}`;
- `source_evidence`: nonempty records `{path, sha256, url, feature_ids, evidence}` binding retained geography/official/imagery evidence and exact endpoint, deletion extent and work-status decisions;
- `source_to_final`: `{scale, translate_x, translate_y}` in PDF points, with positive uniform scale;
- `palette`: named original-source RGB status colors;
- `operations`: `{id, kind:"addition"|"removal", before, after, expected_occurrences, mask_source:[x0,y0,x1,y1], status, reference_box_source:[x0,y0,x1,y1]}`. `before`/`after` are exact ASCII native path operations from the prior source-backed plan. Preserve graphics transforms and prohibit color, width, cap, join, text or arbitrary operators. References must be nearby untouched original same-status strokes outside every mask.

For an operation whose tight bounding rectangle would include another independent patch, optionally predeclare `mask_source_parts: [[x0,y0,x1,y1], ...]` in the source-backed plan. Require a nonempty ordered list of finite positive rectangles, all within `mask_source`, with their combined tight envelope equal to `mask_source`. Overlapping parts within one operation are allowed and form one set union; the envelope is only its capture bound. Omit `mask_source_parts` to retain the original single-rectangle behavior. Do not split or re-stroke a continuous native path merely to fit rectangular masks. Independently review the exact parts and refresh the plan/report/review hashes before release.

The bounded implementation requires one content stream on the source page and one final front page. If necessary, normalize streams before locking the base hash and independently prove original drawing identity. Never change an accepted base just to make a failed comparison pass.

## Run against actual PDF bytes

```bash
python scripts/validate_topology_patch.py \
  --plan PLAN.json --base-source TEXT-FREE-ORIGINAL.pdf \
  --patched-source PATCHED-SOURCE.pdf \
  --baseline-final ORIGINAL-GEOMETRY-FINAL-LAYOUT.pdf \
  --final-pdf ACTUAL-FINAL.pdf --report topology/report.json
```

The validator:

1. Binds original/source/plan/evidence/baseline hashes and correction authority. Proves original-to-text-free visible vector drawing/style and image identity rather than accepting an arbitrary base.
2. Applies only the declared exact before/after operation counts to the immutable base. Prohibits changed graphics transforms/style operators and verifies all actual patched-source operations and unrelated source pages.
3. Measures every planned addition and removal independently. Rejects a nonexistent declared delta or an undeclared opposite delta. Requires every isolated source geometry delta inside that operation's rectangle or explicit parts union, then renders that isolated native operation in the unchanged final-layout baseline and requires zero changed pixels outside its own mapped union. A hole in the union or another operation's mask cannot hide a delta. Deletion correctness is checked explicitly; absence of new ridge pixels is not evidence of a correct removal.
4. Locates the exact original source Form in the final-layout baseline, patches that independently expected stream, and verifies the declared transform. Compares every final native drawing's geometry, style and order, plus the entire actual final raster, with the independently expected result. The fixed 0.01 PDF-point coordinate allowance handles PDF numeric serialization only; exact expected raster equality is still required.
5. Requires zero changed pixels outside transformed source correction masks, with a fixed one-2x-pixel renderer guard on each rectangle before forming its operation's union. Different operations' mapped guarded unions must remain disjoint; overlaps within a single operation are allowed. This does not enlarge any existing repair mask or relax zero tolerance.
6. Proves affected native stroke settings match adjacent original same-status reference strokes. For intended junction changes, compares actual junction paint against independently expected paint produced with those original settings. A T-branch deletion changes medial-axis shape; do not label that as a brush-width change. Keep the existing style maxima: width 1.25px, RGB 18, softness 0.85px, texture 2.5, unexpected-status pixels 0. Pure deletion additionally verifies absence and the removed source's native/reference style identity.
7. Saves the expected-source/expected-final PDFs, actual-size image and paired actual 4x mask captures under the report's `evidence/`, with hashes. These are review evidence, not new delivery cards.

Independent source/plan and actual-size/paired-4x inspection remains mandatory. Software checks consistency and native identity; it cannot establish geographic truth or authentic earlier plan authorship. Visible mismatch vetoes an automated pass. Re-run after any final-byte change.

## Integrate without bypassing old repair gates

Keep `contains_stroke_repair=true` on a colored topology mask. Add `edit_kind=native_topology_addition` or `native_topology_removal`. An omitted kind means `existing_path_repair` and retains the original stroke comparator. Mixed jobs run both gates; do not relabel an existing-path repair to avoid a failure.

`stroke_style_check_required` and `stroke_style_checks` cover existing-path repair masks only. A topology-only job has those false/empty and must pass the separate mandatory topology gate; this is not a claim that a historical generic comparator report passed. Continue requiring overall preservation/stroke visual review and zero mismatch counters, informed by both applicable gates.

Add top-level `topology_patch_review` in project and critic JSON:

```json
{
  "plan_path": "/absolute/path/plan.json",
  "plan_sha256": "actual plan SHA-256",
  "report_path": "/absolute/path/report.json",
  "report_sha256": "actual report SHA-256",
  "independent_visual_review": {
    "independent": true,
    "source_plan_review_completed": true,
    "actual_size_review_completed": true,
    "paired_4x_review_completed": true,
    "no_visible_style_mismatch": true,
    "artifact_sha256": "exact final PDF SHA-256",
    "plan_sha256": "same actual plan SHA-256",
    "evidence": "Independent reviewer, verified source/endpoint/deletion plan and each actual-size/paired-4x region inspected"
  }
}
```

The critic additionally records `topology_mask_kinds` as an object mapping every topology mask ID to its typed edit kind, or `{}` when none exists. Require this field on every critic report so missing topology review cannot silently default to no edits. The builder obtains these kinds directly from its correction masks. Both report gates validate the actual plan/report/capture/expected-PDF file hashes and exact final artifact, all native proofs, zero-outside count, operation IDs/kinds and unchanged style maxima. Missing or stale evidence fails release and caps critic score at 8. Target 10 and minimum 9 remain unchanged.

For each multipart operation, both report gates additionally require result fields `mask_source` and `mask_source_parts` to match the exact ordered plan coordinates, `mask_renderer_guard_2x_px: 1`, `isolated_delta_contained: true`, `isolated_pixels_changed_outside_mask: 0`, `added_length_outside_mask_source_pt: 0`, and `removed_length_outside_mask_source_pt: 0`. The analyzer records these measured proofs; a historical report that only checked the bounding rectangle is insufficient. Style sampling uses the actual union and paired captures use its declared tight envelope.

On the matching project `correction_masks` row, retain the operation ID and add `parts_final: [[x0,y0,x1,y1], ...]` with the exact ordered source parts transformed by the plan's `source_to_final` into final PDF points. Keep `x`, `y`, `width`, and `height` as the tight envelope for identification/captures. When project/preservation-authority records are supplied, both topology report gates verify that source-to-final mapping using the existing 1e-9 coordinate comparison allowance. Do not add a hidden renderer guard to these final rectangles. Optional project `mask_source_parts` metadata must also match the source plan if present.

## Retained approved card and original map are separate authorities

When a revision's approved card differs from the original native assignment map, keep `preservation_audit.approved_base_path/approved_base_sha256` bound to the immutable approved **card**. Record `original_assignment_path/original_assignment_sha256` separately and require those actual source-map bytes to match both `coverage_review.source_sha256` and the native plan/report's original assignment. Do not relabel the map as the approved card or replace either file to satisfy a hash check. Same-authority jobs keep their existing contract.

For a distinct approved card, add `approved_card_baseline: {path, sha256}` to the source-backed native plan. This records the retained authority without changing the independently planned operations or falsely dating a new wrapper. Refresh the plan hash, native report and independent review after adding this metadata. Its presence makes the second proof mandatory in the critic even if the review omits its authority wrapper.

Both project and critic `topology_patch_review` must contain `preservation_authorities`, with these exact project-preservation fields:

- `approved_base_path`, `approved_base_sha256` for the plan-bound retained card;
- `original_assignment_path`, `original_assignment_sha256` for the plan-bound original map;
- `correction_masks`, unchanged from the project;
- `retained_card_baseline: {path, sha256, rendered_comparison_path, rendered_comparison_sha256, actual_render_scales, pixels_changed_outside_masks: 0, correction_mask_ids}`. The baseline must identify the same approved card. The selected unique mask IDs identify the exact ordered project rectangles used in the comparison.

The hash-bound retained comparison JSON records `artifact_path/artifact_sha256`, `retained_card_path/retained_card_sha256`, `original_assignment_path/original_assignment_sha256`, `declared_masks_input/declared_masks_input_sha256`, `masks_final` as ordered PDF-point rectangles, `checks` with `{scale, changed_pixels, changed_outside_masks: 0}`, and `all_zero_outside: true`. The separately retained declared-mask input contains the same ordered `masks_final`. For a selected correction row with `parts_final`, flatten its actual ordered rectangles into `masks_final`; its envelope authorizes no pixels. Require nonempty finite ordered parts inside the row's tight envelope. Parts may overlap within one row and replay as a union. A row without `parts_final` retains its single-rectangle behavior. Preserve the selected row IDs/order while flattening, and never replace a union with its bounding rectangle. Declare at least 1x and 2x; when supplying 4x, include it in both `checks` and `actual_render_scales`.

`preservation_authority_contract.py`, invoked by both topology report gates, verifies the actual bytes for all three authorities, the coverage/native source binding, the plan's retained-card binding, and exact selected mask coordinates. It independently renders the actual approved card and candidate at every declared scale and compares full RGB pixels. Mask rasterization uses floor at each lower bound and ceil at each upper bound; it adds no guard or tolerance. Every actual changed-pixel count must equal its recorded count and every outside-mask count must equal zero. Missing proof, stale identities, renamed authorities, altered mask coordinates, or a false zero fails release. This separate approved-card proof does not replace the original-geometry native expected-render proof, existing-path repair comparison, visual review, or any existing threshold.
