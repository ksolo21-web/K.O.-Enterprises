# Navigation and placement review

Apply this required contract to every final candidate in the builder project and independent critic report. Reinspect the exact final PDF at actual size and in close-ups after repairs; this supplements all existing geometry, preservation, stroke-style, glyph, gap and score gates without changing their cutoffs. The validator checks reporting and artifact identity, not visual truth.

## Three decisions

- Inventory access, then choose its necessary representation. When readable named streets plus street-based directions identify an entrance unambiguously, omit redundant entrance numbers, keys and feature callouts. A verified entrance need not have a separate drawn callout. Keep the access inventory and directions bindings. Preserve necessary approved original numbered-key conventions such as A2, including their neutral unheaded reference ticks, with the existing number-to-street/key evidence; this is not a blanket ban on numbers or authority to remove approved source marks. Current user instructions override older mandatory-callout wording. Territory 19's removed 1–4 entrance key is the regression case, not a rule to remove useful numbered street keys from other cards.
- Follow each road through its complete path in the actual full map and overlapping close-ups. Inspect sharp unexplained kinks, step-offs, gaps, seams, local jogs and discontinuous-looking joins, even when mathematical connectivity and style metrics pass. Compare source and final views at the same locations. Do not let a flattering crop hide a defect seen in the full map or another crop. Record genuine source bends as such with evidence; unexplained or visibly broken paths block release. An inherited defect grants no redraw authority: report it or repair only within already authorized scope/masks and rerun the applicable unchanged gates.
- Reassess label position after geometry repairs. Compare the center of the usable same-road run, positions farther along it and the opposite side, including clearer southern whitespace where available. A northern placement that avoids collisions can still fail if a clearer central/southern placement exists. Center means the usable road run, not the page center; do not require every label to move south or geometric midpoints when road binding, readability or the unchanged 2–15 px gap would suffer. Record the chosen position and why alternatives are worse. Territory 19's Concord Ln and Deerfield Ln illustrate the check, not universal positions for those names.

## Required JSON

Place `navigation_presentation_review` at the top level of PROJECT.json and review.json. Fill every field from actual evidence. Example structure (placeholders do not constitute evidence):

```json
{
  "artifact_sha256": "64 lowercase hex characters from the final PDF",
  "actual_size_screenshot": "page-1-1x.png",
  "closeup_screenshots": ["page-1-region-5.png", "page-1-region-6.png"],
  "entrances": {
    "inventory_complete": true,
    "inventory_source_evidence": "Source filename/hash and independently checked complete access inventory",
    "representations": [{
      "entrance_id": "verified-access-id",
      "representation": "named_street",
      "named_street_sufficient": true,
      "serving_street": "Verified public street",
      "directions_evidence": "Exact visible street-based directions and screenshot location",
      "decision_evidence": "Readable direct street binding makes a second numeric key unnecessary"
    }]
  },
  "street_paths": {
    "whole_map_review_completed": true,
    "views_consistent": true,
    "unresolved_discontinuities": [],
    "observations": [{"road": "Verified road", "location": "Inspected bend/join", "source_comparison": "Source location, whether inherited or repaired, and applicable repair evidence", "visual_evidence": "Full-page and crop filenames/locations showing a continuous path"}]
  },
  "label_placement": {
    "whole_map_review_completed": true,
    "post_repair_review_completed": true,
    "remaining_avoidable_placements": [],
    "observations": [{"label": "Verified label", "road": "Bound road", "usable_run_center_assessment": "Road segment and central placement compared", "southern_whitespace_assessment": "South alternative compared or specific reason it is unsuitable", "chosen_position_reason": "Why final position is clearest", "visual_evidence": "Full-page and crop filenames/locations after the final repair"}]
  }
}
```

Use `feature_callout` only with `named_street_sufficient:false` and a concrete need; existing arrow gates remain mandatory. Use `numbered_key` only with `named_street_sufficient:false`, concrete necessity and `approval_evidence`. Original numbered **street** keys remain governed by the rendering-standard connector convention; do not misclassify them as entrance markers. If no relevant entrances exist, use `representations:[]` and nonempty `no_entrances_evidence`; do not drop verified access records to avoid this check.

Builder projects using direct street access set the existing entrance record's `representation:"named_street"` and retain its ID/site/source/public/access-road fields. That entrance has no separate label, target box or arrow. Bind its named access road to a visible existing street label, and name both access and serving roads in directions. Other entrances use the necessary existing callout/arrow contract unless the independently checked descriptive-access contract below applies. Inventory and missing-entrance gates count verified access representations, not a mandatory number of separate drawn entrance labels. The review representations must cover the builder's complete entrance inventory exactly once.

Observations must identify every raised defect and repaired road/label, plus the whole-map inspection. At least one location-specific path and placement observation is required, including on unchanged cards. `post_repair_review_completed` also means review of the current final state when there was no repair. List actual source/capture locations rather than generic pass assertions. The critic must inspect independently; copying builder decisions is insufficient. Its screenshot names must belong to its exact final-artifact capture inventory: `page-1-1x.png` for actual size and `page-1-region-N.png` for close-ups. Every observation’s `visual_evidence` must name the actual-size capture and at least one declared crop. Missing sections, inconsistent views, stale artifact hash, redundant access notation, unexplained discontinuities or avoidable placement block release and cap the critic at 8. Preserve the target of 10 and minimum of 9 with every hard gate passed.


## Direct descriptors for verified unnamed access

Use `descriptive_access` only when an independent source review establishes that the exact access street has no established name and its descriptive label fits directly alongside its verified native segment. This is not `named_street`: set `named_street_sufficient:false`. Preserve the entrance ID, site, serving public road, access road, verified source and complete inventory. Require the same immutable `descriptive_access_contract` path/hash in PROJECT and navigation review. The shared contract binds source-name evidence, exact native segment, actual PDF, label and quantitative report, plus independent actual-size and close-up direct-fit evidence. Directions must explicitly name the descriptor and serving public road and match actual PDF text. All existing glyph gaps, collisions, entrance counts and direction gates remain mandatory. If a readable direct fit is unavailable, use the existing necessary callout contract; never claim a descriptor is an established name or omit an entrance to avoid an arrow gate.

V3 reconstructed enforcement requires independent original-map and authoritative-inventory corroboration, complete hash-bound site entrance inventory, and fresh actual-PDF native glyph/visibility/collision/gap recomputation. Rebinding claimed metrics cannot substitute for measurement. This proposal requires new independent review.

V4 regression: when one native path contains multiple named or descriptive segments, measure each label only against its verified contiguous source subsegment. Select actual native operators with their existing graphics state and transforms; a nearby return leg cannot provide substitute target ink. Preserve exact gap thresholds, and require both a wrong-subpath negative and truthful same-PDF positive control.


Visible colored obstacle coverage must preserve native occlusion. For descriptive access validation, compare actual all-vector versus neutral-vector-only native renders with text excluded and all original neutral paint/order/clip/transparency retained. Use exact RGB differences, not isolated hidden primitives or relaxed tolerances. All other source, inventory, glyph, subsegment, visibility and collision requirements remain unchanged.
