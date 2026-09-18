# Territory Label Completeness, Contact & Clutter Contract — R50 — 2026-09-13

## Purpose
R50 closes the gap between having label rules on paper and actually proving that every rendered road was labeled correctly before critic review. A card may not pass because the recorded labels happen to look valid while a visible named street was omitted, a label sits on a road, two labels form an avoidable cluster, or a short-street callout is malformed.

This contract is mandatory for every new card, full rebuild, old-card conversion, material map redraw, label repair, or user-reported label defect. It supplements R49 source truth and all earlier family/label rules; when there is any conflict, this stricter R50 gate controls.

## 1. Road/name inventory must drive labels
Before final label placement, inventory **every visible road feature/branch in the map panel**, including all public streets, courts, cul-de-sacs, boundary roads, context roads, access roads, private drives, and visibly road-like unnamed branches.

Each visible feature must receive exactly one source-backed naming disposition:
- `named_public` — label required;
- `named_private` — label may be omitted only when current source evidence verifies it is private and omission is intentional;
- `unnamed` — label may be omitted only when current source evidence verifies no street name;
- `nonroad_feature` — may not be used to hide an uncertain road; source evidence must show it is not a street/drive that needs navigation treatment.

Every **named public street or named public cul-de-sac visible on the card requires a label**. A short street is not an exception; lack of room changes the placement method, not the labeling requirement.

No visible road may disappear from the label audit merely because the builder forgot to enter it in the label ledger. `visible_road_feature_count` must equal the number of road inventory records. `unaccounted_visible_road_count`, `unlabeled_required_road_count`, `unsupported_unlabeled_count`, and `wrong_or_duplicate_road_label_count` must all be zero.

## 2. Ordered placement rule — no on-road labels
For every required label apply the established order without skipping steps:
1. direct beside the street;
2. curved beside/following the street;
3. relocate to a clearer portion/opposite side of the same street;
4. for a genuinely short/cramped street, nearby attached-arrow callout;
5. dedicated enlarged detail when needed.

A direct or curved label must **rest beside its assigned road, never on top of it**. Zero glyph/road touch and zero glyph/road overlap are hard requirements. The existing 2–15 px assigned-road gap remains the hard geometric band, with 4–10 px preferred. The measured gap is supporting evidence; actual-size visual inspection still decides whether the word looks attached, clean, and family-consistent.

A long street that can carry a clean direct/curved label may not be converted to a callout just to avoid placement work.

## 3. Short-street / cul-de-sac rule
A short street or court may keep a direct/curved label only when the usable road run is at least `label_ink + 30 px` at 1x **and** the label retains at least 15 px end breathing room on both ends without touching a bulb, junction, panel edge, or another street.

When that fit is unavailable, move the label to the nearest practical uncluttered whitespace and use one clean callout:
- label block remains near its assigned street;
- leader tail visibly attaches to the label block, 0–2 px gap;
- one clean shaft/elbow/curve and one filled triangular arrowhead;
- arrowhead targets the exact street stem/centerline; if a cul-de-sac has a usable stem, do not target only the bulb;
- no word/glyph crossing;
- no unrelated-road crossing;
- no leader/leader knot;
- no wrong-street ambiguity;
- preferred leader <=80 px; >80 requires no-closer-clean-placement evidence; >110 requires explicit user approval.

## 4. Label-contact gate
On the exact frozen PDF candidate inspect every label against all road strokes, not just its assigned road.

Release requires:
- `label_road_touch_count = 0`;
- `label_road_overlap_count = 0`;
- `wrong_road_contact_count = 0`;
- `label_label_overlap_count = 0`;
- `clipped_label_count = 0`;
- `broken_word_count = 0`.

A label that appears to lie on top of a street at actual size fails even if a coarse bounding-box metric says it is clear.

## 5. Clutter-neighborhood gate
Collision-free labels can still fail. Review **label neighborhoods**, not just individual labels.

At actual size and close-up, identify every pair/group that shares a compact local area. Any label pair with an ink/bounding-box gap under 12 px at 1x is a mandatory `cluster_trigger` for explicit review; 12 px is a review trigger, not an automatic pass/fail threshold.

For every triggered pair/group record:
- labels involved and assigned roads;
- measured nearest-label gap;
- whether ownership is immediately unambiguous;
- same-road alternative positions inspected for each label;
- whether moving one label farther along/opposite its own road would improve clarity;
- whether a short-street callout would cleanly separate the cluster;
- actual-size and 4x crop evidence;
- final result.

If clearer same-road or nearby short-street-callout placement exists, the cluster is avoidable and blocks release. `avoidable_label_cluster_count` must be zero.

**Permanent regression:** the rejected Territory 269 candidate where `Winter Park Rd` sits on its green street and crowds `Winter Park Ct` is a mandatory negative example. A similar on-road label or Winter-Park-style crowding must fail before formal critic dispatch.

## 6. Pre-critic label gate
After rendering but before formal critic dispatch, freeze the candidate hash and perform:
- actual-size full-card inspection;
- 2x full-card inspection;
- overlapping 4x map crops;
- targeted 4x crop for every short-street callout;
- targeted 4x crop for every cluster trigger;
- direct side-by-side with exact saved Territory 273 for residential/neighborhood label grammar.

Populate both `label_completeness_review` and `label_contact_cluster_review`. Any missing required label, on-road/touching label, avoidable cluster, malformed callout, or unverified private/unnamed exception returns the artifact to builder mode **before** formal critic review.

## 7. AI/raster draft prohibition
An image-generation output, consumer-map screenshot, or raster-only concept may be used as a planning/reference draft only. It is **not critic-ready or field-release evidence** and may not satisfy R50 label measurement/review gates.

A release candidate must be an exact measurable PDF with deterministic/native text or equivalent measurable label geometry and reproducible road geometry. If labels cannot be measured/reviewed against the exact PDF, release is blocked.

## 8. Required builder schema
`label_completeness_review` must include:
- `artifact_sha256`;
- `measurable_pdf_candidate: true`;
- `generated_raster_only: false`;
- `residential_neighborhood_map`;
- `visible_road_feature_count`;
- `records[]` for every visible road feature with `road_id`, `name`, `name_status`, `road_role`, `source_evidence`, `label_required`, `label_disposition`, `label_ids`, and `result`;
- `named_public_visible_count`;
- `unaccounted_visible_road_count: 0`;
- `unaccounted_visible_road_count: 0`;
- `unlabeled_required_road_count: 0`;
- `unsupported_unlabeled_count: 0`;
- `wrong_or_duplicate_road_label_count: 0`;
- `unsupported_unlabeled_count: 0`;
- `wrong_or_duplicate_road_label_count: 0`;
- `all_visible_road_features_inventoried: true`;
- `all_named_public_roads_labeled: true`;
- `private_unnamed_exceptions_source_verified: true`.

Allowed `label_disposition` values are `direct`, `curved`, `same_road_relocated_direct`, `same_road_relocated_curved`, `callout`, `detail_direct`, `detail_curved`, `detail_callout`, `intentionally_unlabeled_private`, `intentionally_unlabeled_unnamed`, and `nonroad_feature`.

`label_contact_cluster_review` must include:
- same exact `artifact_sha256`;
- `actual_size_inspected`, `two_x_inspected`, `four_x_full_map_inspected` all true;
- `all_labels_contact_checked: true`;
- `all_callouts_closeup_inspected: true`;
- `all_cluster_triggers_inspected: true`;
- `all_label_pairs_screened_for_cluster_trigger: true`;
- `label_placement_count_screened` equal to the exact label-placement ledger count;
- `cluster_trigger_count` equal to `cluster_records[]` length;
- for residential/neighborhood maps, `territory_273_label_system_side_by_side: true`;
- `label_road_touch_count: 0`;
- `label_road_overlap_count: 0`;
- `wrong_road_contact_count: 0`;
- `label_label_overlap_count: 0`;
- `avoidable_label_cluster_count: 0`;
- `clipped_label_count: 0`;
- `broken_word_count: 0`;
- `detached_leader_count: 0`;
- `wrong_callout_target_count: 0`;
- `callout_crossing_count: 0`;
- `premature_callout_count: 0`;
- `cluster_trigger_gap_px: 12`;
- `cluster_records[]` for every triggered pair/group;
- screenshot/evidence list.

## 9. Formal critic / internal reviewer independence of judgment
The critic and mandatory internal reviewer must independently re-inventory the **rendered** roads/labels from the exact PDF plus raw naming/topology evidence. They may compare counts with builder evidence only after forming their own inventory.

Populate `critic_label_audit` with:
- `raw_name_topology_sources_reopened: true`;
- `builder_label_ledger_used_as_proof: false`;
- `prior_label_score_used_as_proof: false`;
- `independent_visible_road_reinventory_completed: true`;
- `independent_label_reinventory_completed: true`;
- independent visible/named/required-label counts;
- `unaccounted_visible_road_count: 0`;
- `unlabeled_required_road_count: 0`;
- `unsupported_unlabeled_count: 0`;
- `wrong_or_duplicate_road_label_count: 0`;
- `label_road_touch_count: 0`;
- `label_road_overlap_count: 0`;
- `label_label_overlap_count: 0`;
- `avoidable_label_cluster_count: 0`;
- `detached_leader_count: 0`;
- `wrong_callout_target_count: 0`;
- `premature_callout_count: 0`;
- `all_callouts_closeup_inspected: true`;
- `all_cluster_triggers_inspected: true`;
- `all_label_pairs_screened_for_cluster_trigger: true`;
- `label_placement_count_screened` equal to the exact label-placement ledger count;
- `cluster_trigger_count` equal to `cluster_records[]` length;
- `generated_raster_treated_as_final: false`;
- residential/neighborhood `territory_273_label_system_side_by_side: true`;
- evidence and result.

Any positive defect count, missing inventory, unsupported unlabeled road, or false required field caps labels/family/overall at 8.0 and blocks release.

## 10. Validator role
`validate_label_completeness_preflight.py` and the strengthened `validate_label_placement_contract.py` validate structure, counts, evidence declarations, and optional exact-PDF hash binding. They do **not** prove that the visual judgment is correct. The formal critic/internal reviewer must still inspect the exact PDF visually.


## R51 measured-gap / repeat-count / PDF-delivery extension — 2026-09-13
This R50 contract now incorporates `Territory-PDF-Label-Metric-Contract.md`. Each named-public road record must include `required_label_count` (minimum 1); records with `navigation_repeat_required:true` require at least two distinct label IDs and distinct navigation roles. Pre-critic review also requires `delivery_format_review` and `label_metric_review` bound to the exact PDF. Image-only output blocks release regardless of visual quality.

## R52 Role-complete repeat inventory and entrance binding
Completeness includes the required navigation roles, not merely the number of matching names. A loop label plus another loop label cannot cover a loop and its entrance. Lock per-placement roles and source segments before layout; bind actual final-PDF callout targets to that exact run. Keep existing fit/leader/contact/clutter rules. Inspect the entire curved phrase including its suffix using actual-font metrics and visible spacing. Require the added `Territory-Segment-Role-Whole-Label-Contract.md` and its validator alongside all R50/R51 checks.