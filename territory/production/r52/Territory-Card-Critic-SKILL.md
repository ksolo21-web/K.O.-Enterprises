---
name: territory-card-critic
description: Automatically review every created or changed congregation territory-card artifact. The mandatory authorized-internal reviewer uses this exact critic contract in both regular Chat and Work; a genuinely separate critic is additional when available or required. Use fresh full-page and close-up screenshots, score 0–10, and repeat authorized repairs and reviews until the active strictly-greater-than-9 minimum and every mandatory gate pass. Companion to territory-map-card-builder, not for unrelated design or geopolitical maps.
---

# Territory Card Critic

Run this critic contract on every territory-card artifact change. **A mandatory authorized-internal critic-only review always runs**, in regular Chat and Work. When a genuinely separate critic agent/runtime is available or independence is required, run that critic as an additional review lane. This saved workflow does not preserve a running agent or assume previous chat files remain accessible.

## Continuous review–repair policy (2026-09-09)

There is no two-round stop and no fixed maximum number of review/repair rounds.
The latest explicit user acceptance contract controls the score threshold. The
territory default is **strictly greater than 9.0/10, without rounding**, target
10/10; a project can explicitly require a higher threshold. An exact 9.0 is not a pass;
the current 346–370 floor is also strictly >9.0 unless a higher project minimum applies. Every mandatory
check and every required item of evidence must still pass. No unresolved hard
failure, unverified required fact, or averaged-away deficient category can pass.

Run capture → inspect sources and every required image → report findings → make
bounded authorized repairs → retest → freshly capture and review again. Apply
this to the exact saved PDF, not merely the editable working copy. Preserve all
rounds and hashes. A changed PDF invalidates affected reviews. Stop the quality
loop only when the active score threshold and all mandatory gates pass.

Two consecutive unchanged findings trigger **diagnosis and a different repair
strategy inside the loop**, not a handoff or automatic stopping point. Recheck
road/name bindings, source data, measurements and the repair method; choose a
meaningfully different valid approach and continue. A failing test is an action
item. Do not blindly rerun the same failed edit, shrink scope, alter measurements,
enlarge correction masks after the fact, inflate a score, or waive a hard gate.

Use the saved critic and builder skills, not a new external app as a prerequisite.
The user has standing-authorized the internal reviewer for territory work. It is
mandatory on every created/changed artifact and must use this exact critic contract.
Record `reviewer_type: authorized_internal` and `critic_independent: false`. A real
separate critic, when available/required, is additive. Reviewer provenance never
weakens map, source, visual, export, evidence, identity, or score requirements.
Read `references/Territory-Automatic-Execution-Contract.md`.

A real permission boundary is not permission to guess or bypass access. Attempt
available authorized recovery routes, continue other unblocked cards, and preserve
the exact state. Platform/session interruption means interrupted work, not PASS
and not a promise of unattended continuation. A new turn resumes the saved round
rather than resetting a two-round counter. Do not interrupt the user merely
because a round failed or there is more routine work to do.

Use `scripts/continuous_review.py` to validate the round decision and preserve
`loop-state.json`; it does not generate a critic judgment or a passing score.

## Recover the actual task

Read the available `territory-map-card-builder` skill and its applicable rendering and QA references. Identify the current PDF, accepted source drawing, approved sidebar/design reference, user-authorized changes, and source/name evidence. Resolve inputs from current attachments or saved files, not remembered scratch paths. If a required source is unavailable, report that gate as unverified and retrieve or request it; never substitute a guessed drawing.

Apply the builder's source classification first. For Kaleb's collection, the 91 newly drawn `Maps.zip` sources are locked as current geometry/work-color authority; modern-looking legacy cards are not automatically members of that locked set. Older maps may receive evidence-backed corrections within the user's authorized update batch. Review declared legacy changes against source evidence and the stroke-style gate instead of demanding repeat permission solely because their old paths changed. This does not authorize altering the 91 new drawings or inventing coverage/work-rule changes. Record the actual source member/hash and honor later individual approvals.

Keep `preserve_supplied_map` locked for accepted linework. Review does not authorize redraws, tracing, recoloring, geometry repairs, new work rules, or a new inset. Preserve existing user approvals and limits. A request only to audit authorizes evidence creation, not changes to the card; a repair-and-review request authorizes in-scope layout/label fixes.

## Separate builder from critic

Use a fresh separate subagent with minimal context when a callable agent runtime exists. Give it raw inputs, current instructions, this skill, and the territory standards, not the builder's scores, claimed passes, expected diagnosis, or suggested answer. The separate critic renders and inspects its own screenshots and cannot edit the card.

**Mandatory internal lane:** regardless of separate-agent availability, freeze the candidate and run an authorized-internal critic-only review using the same inputs, report schema, screenshots, hard vetoes and score rule. The internal reviewer cannot truthfully be independent, but it cannot use a lighter checklist. It must not edit during scoring or use the builder's claimed score as evidence.

Use this task pattern:

> Use Territory Card Critic in critic-only mode to review [candidate PDF] against [source drawing], [approved design], [authorized changes] and [verification sources]. Generate fresh screenshots in [new round directory]. Inspect full card, every map region, crowded labels, junctions, inset if present, sidebar and directions. Return an evidence-backed score and report; do not alter the card. Do not read prior scores before completing your own assessment.

Do not recursively spawn another critic when already assigned critic-only mode.

## Screenshot evidence at every checkpoint

Run `python scripts/critic_evidence.py capture CANDIDATE.pdf ROUND_DIR` to record the exact PDF hash/bytes/page count and render every page at 1x and 2x plus overlapping 4x regional crops. Inspect images using the image viewer; generating them is not inspection. Add tightly framed screenshots of any unresolved junction, arrow, source comparison or stroke repair. Render without changing map geometry or using generative image tools.

Capture and review at the initial candidate, after each meaningful repair, and again from the exact final optimized/exported file. Inspect normal-size readability as well as close-ups; enlargement cannot excuse unreadable output. For a static map, different points means page regions, zoom levels, and revision checkpoints, not artificial perspective angles.

Apply [references/visual-evidence-integrity.md](references/visual-evidence-integrity.md) for every release: independently check the common sidebar palette `#FFDC18` / `#51C72B` / `#FF1435` separately from preserved map colors, verify entrance radius/region provenance, resolve disputed wide-stroke samples with complete independent cross-sections, and reject broken-looking whole words or twisted suffixes despite passing glyph gaps. Keep existing thresholds unchanged and identify the actual screenshot reviewer.

## Inspect visual clutter independently

Inspect whole junctions and surrounding label groups at actual output size and in close-up, not only individual bounding boxes. Collision-free labels can still form an avoidably crowded cluster. Compare usable whitespace farther along the same assigned road, on its opposite side, and on another suitable straight segment. Require the clearest unambiguous placement while retaining the required street gap, regular font, and source linework. Do not solve clutter by shrinking names, adding unnecessary arrows, or redrawing streets. For a bounded revision, send unrelated defects back as blockers rather than expanding the authorized edits.

Use Territory 254's northern inset as a regression example: Quarter St below its road and West St on the segment above Renshaw St separate the formerly crowded Quarter/West labels. Apply this principle to other clusters; do not impose those positions universally. Record actual-size and crop evidence plus the alternatives assessed in `label_clutter_review`. Any remaining avoidable cluster or unperformed cluster review blocks release and caps the score at 8, even when numerical overlap/gap checks pass. The builder makes authorized placement repairs, then the critic reviews fresh screenshots again.

Inspect the letters inside each curved word independently using [references/label-glyph-review.md](references/label-glyph-review.md). A label can clear its road and every other label while adjacent letters overlap at a tight guide turn. Require actual isolated glyph-ink measurements plus your own actual-size/close-up legibility review for every curved label; guide-induced overlapping or touching letters block release and cap the score at 8. Distinguish visible crowding from ordinary kerning or raster-cell edge contact; do not require blanket tracking or an arbitrary positive inter-letter gap.

For an approved original numbered-key map, independently preserve and assess its source connector convention. Original A2 markers such as 10 and 15 use short neutral, single-segment reference ticks with no arrowheads; explicitly record that representation and absence of heads. Verify number → connector → currently verified street → key against the approved source and current street evidence. Inspect actual-size and close-up views for measured endpoint proximity and correct street association, close and unambiguous number-end association without touching glyph ink, and no collisions with labels, other connectors or unrelated streets. Record the endpoint gap and source/render scale honestly; preserve any small approved source gap without claiming literal contact. This source representation does not waive spacing, readability, collision or street-verification gates. Filled triangular arrowheads and specified target contact remain required for new street callouts and entrance callouts; do not demand them on an approved unheaded reference tick or infer a street from a number alone.

## Verify the actual coverage representation

Read [references/coverage-model.md](references/coverage-model.md). Require top-level `coverage_review` and the complete `current_inventory_review` contract for every card. A genuine explicit road-segment/side assignment in preservation mode does not require an invented closed polygon; verify its original source/hash, complete assigned segments, endpoint/work-rule/side bindings, bounded audit extent and resolved immediate edges. Closed polygon assignments retain every existing closure/self-intersection check, and vector rebuilds always require a closed polygon.

Independently inspect the raw source and full road/property dispositions. Reject missing sources, partial retrieval, count/ID mismatches, omitted features, unknown edges, unresolved property eligibility or pending candidates regardless of representation. `full_coverage_resolved=true` alone is not evidence. Source acceptance or an earlier score never waives discovery. Any failure caps score at 8 and sets release false. The critic gate validates the same coverage/inventory contract as the builder. Preserve all existing major-road, preservation, style and score cutoffs.

Coverage representation does not authorize geometry changes. Authorized native additions/removals require the separate typed topology gate below; never change an old reference or repair threshold to make a failure pass.

## Reject duplicate worked coverage

Apply [references/duplicate-worked-coverage.md](references/duplicate-worked-coverage.md) to every card, including closed-polygon assignments. Require `duplicate_coverage_review` covering the complete active assignment collection and independently verify physical segment identity, measured extent and worked sides against source and actual cards. Both-sides overlaps with either worked side fail; opposite sides remain distinct. Missing collection scope or unresolved physical identity blocks release and caps the score at 8. Do not alter source assignments to remove a conflict without authorization.

## Review authorized native topology changes

Read [references/native-topology-gate.md](references/native-topology-gate.md). For source-backed legacy additions/removals or explicitly authorized locked-source edits, run the builder skill's `scripts/validate_topology_patch.py` against the immutable original/text-free base, prior source-backed native plan, actual patched source, original-geometry final-layout baseline and exact final PDF. Do not run a nonexistent local copy of that analyzer; the critic's local `topology_contract.py` validates the resulting evidence contract. Existing-path repairs keep their original comparator and all cutoffs. If the approved retained card differs from the original native map, require both exact authorities and independently replay the separate approved-card pixel comparison from the linked contract; never replace the approved card with the raw map to satisfy a hash check.

Independently verify plan provenance, source-backed endpoint/deletion/work-status decisions, original-to-base drawing identity, exact native operation counts, unchanged other paths/styles, final transformed geometry and expected raster, explicit deletion delta, zero outside masks and original same-status style references. Inspect actual-size and every paired4x capture generated by the gate. At topology-changing junctions, compare actual paint with independently planned paint rendered using unchanged source style; do not misclassify changed junction medial-axis width as brush width. A visible style defect still vetoes the numeric pass.

Record `topology_mask_kinds` on every critic report: `{}` when source comparison establishes no topology edits, otherwise each mask ID mapped to `native_topology_addition` or `native_topology_removal`. Require `topology_patch_review` from the linked contract for every typed mask, with actual plan/report/capture hashes and the critic's own final-artifact/plan-bound independent source/visual review. An omitted record, stale hash, unverified authority/provenance, unplanned delta or failed applicable gate caps score at8 and blocks release. Do not set an old failed generic comparator report to PASS; retain it as history and explain which typed gate evaluates the intentional topology change.

## Verify current inventory and card content

For **every** territory, including the 91 locked new drawings and previously completed cards, inspect a fresh dated discovery audit against current sources. Require full assigned-boundary and immediate-edge coverage, complete query pagination/transfer-limit evidence, dataset/imagery recency distinct from retrieval dates, and a feature-level comparison of existing and new/missing streets plus relevant eligible properties. Inspect private roads and unnamed access where relevant to the actual work rules. A review of only names already on the card is not a discovery check. Do not count the supplied drawing's acceptance or a prior visual score as this evidence.

Record `current_inventory_review` below and cite its separate audit file and source/feature evidence. Independently assess the inventory's scope, additions, exclusions and unresolved candidates. Missing evidence, an undefined coverage edge, unresolved relevant property eligibility, a possible missing street, or incomplete retrieval blocks release and caps the score at 8. Preserve locked drawings while reporting conflicts; only user-authorized correction permits changing them.

Inspect the full-page screenshots and extracted text for source-credit/audit lines such as `Names: Oakland County GIS / Auburn Gate` or `Names checked: ...`. Require their absence from the card and the continued presence of supporting attribution/citations in separate audit evidence. Record `card_content_review`; a removed footer does not waive geographic evidence.

## Require two major cross roads on EVERY card

Independently verify at least **two distinct verified MAJOR cross roads** on every card, including legacy, previously completed, all 91 locked new drawings and future cards. Read [references/major-crossroads.md](references/major-crossroads.md) for the required `major_crossroad_review` evidence contract. Count distinct physical roads, never repeated labels, aliases, divided carriageways of one road, or minor internal streets. Require source-supported major-road qualification and identity, visibly drawn geometry, readable bound labels, verified drawn connected approaches and visible directions naming both roads. Source evidence stays outside the card.

Inspect the actual final-size and close-up screenshots yourself and compare each road and connection with source feature evidence. Do not copy builder assertions as independent verification. Missing or unverified second major road, absent source evidence, a fake/duplicate identity, floating text, unreadability or disconnected context is a hard blocker: cap overall at 8 and set `release_ready=false` regardless of category mean. Preserve accepted linework; ask the builder for minimal verified context on a separate layer and uniform scaling only if needed, never a retrace. The target remains 10 and the minimum remains 9 with every hard gate passed.

## Score honestly

Give each category a 0–10 score with evidence. **Do not use an average to decide release.**

| Category key | Diagnostic weight only | Required checks |
|---|---:|---|
| preservation | 25% | Complete supplied linework, uniform scale, source colors, no unauthorized changes; any permitted repairs match source stroke style |
| geography | 25% | At least two evidenced distinct major cross roads drawn/readably labeled with connected approaches and directions; correct road/name bindings, boundaries, work sides, entrances; fresh complete street/property discovery; sources resolve conflicts |
| labels | 25% | Every required name readable, measured/aligned to road, branch-complete, no overlaps, partial lift or avoidable clusters; same-road whitespace assessed; necessary callouts only; correct clean arrow targets |
| template | 15% | Approved legend scale, colors/order, spacing, alignment, sidebar, calendar/update block, measured map balance |
| export | 10% | One front page, no exclusions list, no clipping, actual PDF below 300000 bytes, final screenshots, no on-card source/audit lines, extracted text matches visible territory/locality |

Also score every applicable `new_design_visual_review.part_scores` item: `direct_curved_label_placement`, `callout_leader_system`, `branch_completeness`, `clutter_whitespace_balance`, `map_balance_and_context`, `family_resemblance`, plus `enlarged_detail_quality` when a detail is used.

Interpret 0 as absent/not completed; 1–4 as major failures; 5–6 as substantial defects; 7 to below 9 as needs correction; 9 to below 10 as release quality only when every hard gate passes; 10 as no observable defects under the stated checks, never proof of physical-world perfection. Aim for **10/10 in every category and part**.

**Strictly greater than 9.0 is required for every category and every applicable part, unrounded; 9.0 exactly fails.** Release score is the **minimum** of all applicable category and part scores. A weighted mean may be retained only as a diagnostic statistic; it cannot make a deficient part pass. If one category or part is 8.99 and every other score is 10, the card still fails.

Any hard territory gate failure or unverified required evidence blocks release regardless of any mean. Hard visual defects cap the affected visual part(s) and overall release score at 8 until repaired. Never lower standards, discard findings, hide a source defect, or inflate scores to terminate a loop. Distinguish source-inherited defects from newly introduced ones; neither authorizes a source edit. If inherited geometry conflicts with hard gates, stop for user direction instead of silently repairing or waiving it.

Inspect inset edges for clipped pieces of neighboring streets masquerading as orphan dots. Narrow an authorized inset's framing only when all intended inset streets remain complete enough to interpret and the full main source map stays untouched. Check PDF extracted text for stale territory numbers/localities hidden beneath opaque overlays; a correct screenshot alone does not validate search/copy/accessibility content.

## Report contract

Write `review.json` in each round directory using:

```json
{
  "artifact_sha256": "hash from capture manifest",
  "critic_independent": true,
  "categories": {
    "preservation": {"score": 0, "reason": "evidence"},
    "geography": {"score": 0, "reason": "evidence"},
    "labels": {"score": 0, "reason": "evidence"},
    "template": {"score": 0, "reason": "evidence"},
    "export": {"score": 0, "reason": "evidence"}
  },
  "screenshots_inspected": ["page-1-1x.png", "page-1-2x.png", "page-1-region-1.png"],
  "label_clutter_review": {
    "actual_size_review_completed": true,
    "closeup_review_completed": true,
    "remaining_avoidable_clusters": 0,
    "evidence": "Name actual-size and crop screenshots, locations, and same-road alternative placements assessed."
  },
  "new_design_visual_review": {
    "artifact_sha256": "exact final PDF SHA-256",
    "reference_style": "new_designed_territory_cards",
    "reference_cards": ["Territory 254", "Territory 330"],
    "actual_size_review_completed": true,
    "closeup_review_completed": true,
    "same_road_alternatives_assessed": true,
    "direct_label_first_verified": true,
    "numbered_density_key_used": false,
    "approved_source_numbered_connector_preserved": false,
    "approved_source_numbered_connector_evidence": null,
    "floating_leaders": 0,
    "detached_leaders": 0,
    "wrong_target_leaders": 0,
    "unnecessary_leaders": 0,
    "max_tail_to_label_gap_px": 2,
    "avoidable_clutter_clusters": 0,
    "enlarged_detail_review": {
      "used": false,
      "dedicated_whitespace": true,
      "overlays_full_map_content": false,
      "main_map_complete": true,
      "main_map_uniform_scale_or_unchanged": true,
      "locator_titles_clean": true,
      "source_geometry_status_preserved": true,
      "direct_labels_used_in_detail": true
    },
    "family_resemblance_passed": true,
    "evidence": "Actual-size and close-up comparison against approved New Designed cards."
  },
  "label_glyph_review": {},
  "housing_instruction_review": {},
  "topology_mask_kinds": {},
  "topology_patch_review": null,
  "coverage_review": {
    "representation": "closed_polygon",
    "map_mode": "preserve_supplied_map",
    "source_ref": "Original assignment source and retained audit",
    "source_sha256": "64-character original source SHA-256",
    "geometry_verified": false,
    "full_coverage_resolved": false,
    "audit_extent": {"crs": "Actual CRS", "bounds": [], "evidence": "Verified full extent and immediate edges"},
    "edges_reviewed": false,
    "edge_evidence": "Source and feature evidence resolving all edges",
    "unresolved_edges": [],
    "polygon_boundary": {"closed": false, "no_self_intersections": false, "geometry_verified": false}
  },
  "current_inventory_review": {
    "check_date": "YYYY-MM-DD",
    "full_boundary_and_edges_checked": false,
    "source_retrieval_complete": false,
    "relevant_property_eligibility_resolved": false,
    "unresolved_discrepancies": [],
    "unresolved_candidates": [],
    "audit_extent": {"crs": "Actual CRS", "bounds": [], "evidence": "Whole assignment and immediate edges"},
    "sources": [],
    "feature_dispositions": [],
    "evidence": "Separate audit file plus dated sources, source recency, retrieval completeness and feature comparison references."
  },
  "major_crossroad_review": {
    "actual_size_review_completed": false,
    "closeup_review_completed": false,
    "distinct_physical_roads_verified": false,
    "directions_reference_both": false,
    "directions_text": "Exact visible directions naming both major roads",
    "roads": []
  },
  "card_content_review": {
    "source_or_audit_lines_absent": false,
    "evidence": "Full-page screenshot and extracted-text inspection."
  },
  "blockers": [{"id": "B1", "detail": "specific failure", "evidence": "screenshot and location"}],
  "minor_findings": [],
  "unverified": [],
  "overall_score": 0,
  "release_ready": false
}
```

Complete `label_glyph_review` using [references/label-glyph-review.md](references/label-glyph-review.md), with the hash-bound measurement report, complete curved-label scope and your own final-artifact visual assessment. An empty object deliberately does not pass.

Complete `housing_instruction_review` using [references/housing-instructions.md](references/housing-instructions.md), independently checking all assigned housing types, current printed full-page text and every explicit property/side/other-territory exclusion against source evidence and the recorded user decision.

Complete the linked coverage contract: the skeleton above deliberately does not pass; explicit segment assignments replace `polygon_boundary` with complete `segment_assignments`. Populate all source/count/ID/disposition inventory records. Populate `major_crossroad_review.roads` with at least two complete records using the linked major-crossroads contract; an empty list or a count-only assertion fails the deterministic gate. List all inspected screenshots, not only the example entries. Every finding needs a location and evidence. Mark unverified requirements explicitly. The builder may check facts and provide evidence against a mistaken finding, but cannot alter the critic's score or mark its own review independent.

Run `python scripts/critic_evidence.py gate CANDIDATE.pdf ROUND_DIR/review.json` to independently recalculate the numeric gate, check hash, screenshot inventory, export limits and report consistency. This script validates reporting; it cannot judge visuals or prove that a source/label is correct.

## Repair loop and handoff

1. Receive the independent findings. Address specific failures with smallest authorized edits and declared correction masks. Never rebuild the entire map to fix labels.
2. Rerun the territory's deterministic gates and original-source comparison. For any explicitly permitted stroke repairs, run the builder's stroke-style analyzer and inspect paired 4x crops; numerical pass never overrides visible mismatch.
3. Send the revised artifact for another screenshot review. Preserve previous round reports as history. Recheck the entire card for regressions, not only edited regions.
4. Continue while useful authorized fixes remain, aiming for 10/10. Release requires a score of at least the active minimum (default 9/10) and every hard gate passed; lower scores do not pass. There is no fixed round limit. After two rounds with no measurable progress, diagnose the cause, change the repair strategy, and continue the review–repair loop. A failed round is not an acceptable stopping point. Honor genuine permission boundaries and never invent missing evidence.
5. Recheck the exact delivery PDF after optimization or saving changes; invalidate a score if the artifact hash changes. Save final card and review evidence through the environment's persistent artifact workflow, keeping audit material separate if embedding would break the PDF size limit.
6. After a reported download/preview mismatch, require a distinctly named fresh export and a delivery audit binding the final download path to the newly saved file ID, version and retained-byte SHA-256. Inspect a freshly retrieved copy of that exact saved object with full-page/close-up screenshots and extracted text; verify source/audit lines are absent and inspect a fresh preview from the same bytes. A clean working copy is insufficient. Reject stale copied xattrs or old link registration as proof of delivery identity, and do not diagnose caching without evidence. If a ZIP is supplied for an unambiguous handoff, compare its PDF member hashes with the exact reviewed retained copies. Record these checks under `delivery_identity_review`; keep geographic blockers and score limits unchanged.
7. Report score, number of rounds, material corrections, and any remaining minor caveats. In old or new chats, users can request `Use Territory Card Critic`; do not promise the same live agent persists or that a stale chat automatically refreshes its skill catalog.

## Assigned housing and printed instructions

Apply the user-authorized precedence in [references/housing-instructions.md](references/housing-instructions.md) on every card. Marked assigned residences control obsolete housing-type restrictions, including apartments, condominiums, townhomes and mobile homes. Require the builder to revise conflicting printed directions or work notes without repeatedly requesting the already authorized decision. Independently verify scope in both directions: retain work colors, inside-only sides, explicit map exclusions and verified other-territory/access restrictions. A workable approach alone does not assign a separately assigned complex. Record user provenance, full property bindings and actual final text in required `housing_instruction_review`. Any missing evidence, unresolved conflict, housing-only exclusion of assigned residences or instruction expansion caps score at 8 and makes release false. The target remains 10 and the active default pass rule is strictly >9.0 with all hard gates passed.

## Access notation, continuous streets and usable-road placement

Apply [references/navigation-presentation.md](references/navigation-presentation.md) on every final candidate and populate required `navigation_presentation_review`. Prefer clear named-street access/directions over redundant entrance keys; preserve necessary approved numbered-key conventions. Inspect full street paths for unexplained kinks, step-offs and discontinuous joins across actual full-page and close-up views. Reassess the center of each usable road run and available southern whitespace after repairs; no collision alone is not a placement pass. Missing or failed evidence blocks release without changing any preservation, geometry, style, gap or scoring cutoff. Detection grants no automatic redraw authority.

## Required branch and status-paint review

Apply [references/branch-color-filenames.md](references/branch-color-filenames.md) on each working and saved-artifact review. Independently enumerate navigationally distinct branches and mixed-status junctions; record required `branch_color_review`. Explicit source-paint slivers, missing necessary branch labels and avoidable clusters veto numerical passes. Confirm individual delivery filename `Territory - 000Letters.pdf`, with visible card identity unchanged. Use the active user acceptance contract: every category and applicable part must score strictly >9.0 with all mandatory checks/evidence, target 10. Never change a separately requested higher project minimum.

## Learning from returned cards

Read [references/learning-regressions.md](references/learning-regressions.md) at batch intake and whenever the user reports a missed defect. Preserve failed and corrected artifacts, test the changed rule against both, and carry versioned evidence into the next chat. A rule is not proven merely because it was written.

For a mixed native addition followed by a predeclared existing terminal repair with the proven disconnected-fragment width-estimator defect, apply [references/mixed-native-existing-chain.md](references/mixed-native-existing-chain.md). Require its explicit original-to-final chain, independently reviewed estimator and actual final2x/4x evidence; never infer a waiver from an earlier source-crop pass.

For a retained full OSM response, require [references/osm-property-scope.md](references/osm-property-scope.md): inspect all property candidates independently and require the actual-PDF scope guard as well as the complete release gates. A road-only inventory does not establish full property review.

For an explicitly source-planned neutral paint knockout, use [the native neutral knockout contract](references/native-neutral-knockout.md); do not relabel it as a path trim or topology removal.

For a source-reviewed addition/removal pair sharing one junction, apply [the shared junction contract](references/shared-junction-pairs.md). All member operations remain independently bound to the immutable original.

For narrowly source-bound unchanged native width evidence, apply [the exact native width contract](references/native-unchanged-width.md). Retain original PNG failures and all other gates; require independently pinned actual PNG evidence.

### Raster-source street additions

For authorized additions to a raster-only source, declare `raster_topology_addition` masks with `contains_stroke_repair: true` and final-page coordinates. Use `raster_topology_review` with `scripts/raster_topology_contract.py`; retain immutable source and prior-plan provenance, exact replayed embedded pixels, identical expected renders at 1×/2×/4×, zero changes outside the declared masks with the fixed renderer guard, and the unchanged same-status stroke-style limits. Require an independent review bound to the report, replay program, exact arguments, prior plan, source geometry, representative reference strokes and paired close-ups. The gate must recompute the evidence. Never fabricate native-vector evidence for raster-only originals or omit a colored edit mask. Existing native topology and existing-path repair gates remain mandatory for their respective edit types.

Apply the user’s standing boundary rule: newly verified residential streets inside the territory’s red/yellow enclosing boundaries are workable unless an explicit exclusion or separate territory assignment applies. Retain red exclusions and the territory-facing yellow side. Check physical street intervals, sides and actual property access against neighboring assignments before release. Retain Telephone designation even when the residences include apartments or condos.
## New Designed family-regression veto — 2026-09-11

Apply [references/new-designed-visual-standard.md](references/new-designed-visual-standard.md) on **every** current-format card before awarding 9/10 or higher. The R19 review of territories 255a–260 is a retained negative lesson: it scored too highly because the reviewer treated zero collisions as sufficient while missing avoidable clutter, leaders that visually floated away from their labels, and an invented numbered street-key system that did not match the approved New Designed collection.

The critic must independently compare the exact final PDF with at least two approved New Designed cards, using a similar-density example when available. Inspect actual size plus 2x/4x crops. Require this hierarchy: direct label → curved road-following label → clearer same-road whitespace → attached bent/gently routed leader → dedicated enlarged detail.

Hard visual vetoes that cap the overall score at 8.0 and set `release_ready=false`:

- any invented numbered density key / `STREET KEY` workaround not preserved from an explicitly approved source convention;
- any leader tail more than 2 px from its label block, any visually detached/floating leader, or any leader attached to the wrong label;
- any wrong-target leader, including a callout aimed at a nearby red/context feature rather than its assigned road;
- any avoidable clutter cluster even when collision metrics are zero;
- any unnecessary callout where direct/curved placement or clearer same-road whitespace works;
- any enlarged detail that overlays important full-map content, obscures work colors, is itself crowded, or fails to improve hierarchy;
- failure to resemble the approved New Designed card family at actual output size.

An enlarged detail is preferred over an invented numbered key when a dense area genuinely cannot be labeled cleanly. Use 254/330 as regression references for clean dedicated-detail hierarchy, not as fixed geometry templates.

Every critic report, including an explicitly authorized internal critic, must include a hash-bound `new_design_visual_review` object meeting the linked contract. Missing or failed review evidence is a hard gate failure. Internal review uses the exact same visual vetoes; reviewer provenance never weakens them.

## R28 rejection: short-road, leader-crossing, and detail-placement veto — 2026-09-11

Treat the user's rejection of territories 256–260 R28 as authoritative regression evidence. **R28 is not a positive fixture and cannot be used to justify a pass.** The critic previously missed major defects even after the numbered-key issue was removed.

For every short street, cul-de-sac, stub, or tiny loop, independently determine whether the usable stem/arc can truly carry the full name plus 15 px breathing room at both ends while preserving the 2–15 px street gap. If not, require an attached bent leader/arrow. A floating/direct label near a short road without meeting that measured exception is a hard failure.

Inspect every leader as actual geometry and visually: the tail must attach to the label edge, the shaft must not cross/touch/underline any word or glyph, it must not cross an unrelated road merely to reach the target, and its head must land on the named street stem when available rather than the cul-de-sac bulb. Review neighboring callouts as one composition; a knot of individually collision-free arrows still fails.

For enlarged details, independently re-run the label-binding and short-road rules inside the detail. Reject floating/misbound labels, labels jammed against panel edges/dividers, callout violations, or a detail that is not visibly cleaner than the full-map alternative. These defects cap the labels/overall visual score at 8.0 and keep release false until repaired.
The exact-final-PDF report must enumerate every short street/cul-de-sac in `short_street_decisions`, reconcile `short_street_count`, and reconcile `leader_count` with `leaders_reviewed_count`. A direct exception requires measured usable run >= label ink + 30 px and >=15 px end breathing room. A callout requires verified stem targeting. Missing inventory/count reconciliation is a hard visual failure.


## R42 annotated label-placement measurement override — 2026-09-11

The user's annotated R42 screenshots for territories 256–260 reopen and reject R42. Treat R42 as a negative regression fixture alongside R19 and R28. Read `references/new-designed-visual-standard.md` and apply its canonical 1×/72-dpi measurement system to the exact final PDF.

A passing (>9.0) review now requires a reconciled `label_placement_measurements` inventory for every navigational label, a complete `branch_label_bindings` inventory, `unlabeled_worked_branches == 0`, the measured map-balance review, and the per-part score floor. The reviewer must specifically detect:
- excessive irrelevant/blank map space that compresses the assigned area;
- labels on or too close to their road strokes;
- labels too close to intersections, bulbs, panel edges, unrelated roads or other labels;
- visually distinct worked branches with no clear label ownership;
- callouts whose label blocks/leaders do not maintain the measured clearances;
- bulb-targeting when a usable stem exists;
- enlarged-detail labels that float, straddle road ink, or ignore the same measurement rules.

No category average can offset a visual part at or below 9.0. `overall_score` for release is the lowest applicable category/part score.

## R44 Canonical family-shell veto — 2026-09-12 — HARD OVERRIDE

Read `references/New-Designed-Card-Family-Contract.md` before scoring any current-format card. Review the exact final PDF against the canonical released shell, not merely against a generic map-design rubric.

### Canonical critic references

- Primary shell/style: released **A33** and **60AB**.
- Split/detail layout: **330** when applicable.
- 254 is a component/density-placement example only and may not justify a different outer shell.

### Mandatory critic checks

Independently verify:

1. exact page size and one-page structure;
2. canonical sidebar/map-panel/directions-panel geometry;
3. canonical sidebar hierarchy, swatches, palette, typography bands and update block;
4. allowed internal map-layout mode;
5. clean schematic map style rather than consumer-map/screenshot styling;
6. no screenshot crop/selection box rendered as a territory boundary unless explicitly authorized as the real boundary;
7. street-label family grammar, not merely collision freedom;
8. directions-panel family resemblance;
9. actual-size side-by-side resemblance to A33/60AB (+330 for detail layouts).

Run `scripts/validate_new_designed_family.py` independently on the exact PDF and bind its report/hash into `card_family_review`. The script cannot substitute for visual judgment.

If the shell geometry differs materially, the sidebar/directions are redesigned, an unapproved map layout is invented, screenshot-map styling is used, or family resemblance fails, cap `template`, `family_resemblance`, and overall release at **8.0**, set `release_ready=false`, and return the card for repair. Do not award a passing >9.0 score because the map itself is geographically correct.

Require a complete `card_family_review` object in every critic report. Missing/unverified fields are a hard failure.



## R45 Independent label decision-tree veto — 2026-09-12 — HARD OVERRIDE

Independently re-evaluate **every navigational label** using the canonical label decision order; do not accept the builder's treatment choice merely because its measurements are present.

For each label ask, in order:

1. Can the full name sit beside the exact street with clean road gap, end breathing, no overhang, and professional association?
2. If the street bends, does the label bend with it rather than float away or stay artificially straight?
3. If this spot is cluttered, is there clearer whitespace farther along that same road or on the opposite side?
4. Only if not: is the callout placed in the nearest practical uncluttered area, with a visibly attached arrow to the exact street/stem and no text/unrelated-road crossings?
5. If even that creates long/tangled callouts: should the card use a dedicated detail instead?

Hard critic failures include: avoidable overhang, floating unled label, straight label on a bend where curvature is feasible, callout before same-road alternatives were exhausted, avoidably distant callout, detached leader, wrong target, bulb-only target when a stem exists, arrow knot, or micro-text used to avoid the proper hierarchy.

Require and independently populate `label_placement_decision_review` for the exact artifact. Run `validate_label_placement_contract.py` against the critic's report. Any failed/unverified decision blocks release and caps `labels`, `family_resemblance`, and overall at 8 until repaired.


## R46 Mandatory internal-review parity — Chat + Work — HARD OVERRIDE

Read `references/Territory-Automatic-Execution-Contract.md`. Every created or changed
territory artifact requires an authorized-internal critic-only review using this
**entire** critic contract. This is automatic in regular Chat and Work and does not
require the user to ask for a critic.

The internal reviewer must freeze the candidate, inspect fresh 1x/actual, 2x, full-
coverage overlapping 4x crops plus targeted closeups, inspect the same source/family
references, complete the same report objects, apply every hard veto, and use the same
strictly >9.0 per-category/per-part floor. **The internal reviewer uses the same critic contract without omissions.** It may not edit during the review or rely
on the builder's score/pass claim.

Require `reviewer_parity_review`; run
`scripts/validate_internal_reviewer_parity.py REVIEW.json`. Any failure keeps
`release_ready=false`. Any changed hash invalidates the review. Re-run the internal
review on the exact saved/delivered PDF. A separate critic is additive when available
or required; disagreement is resolved by repair/evidence, never averaging or choosing
the higher score.

## R47 Locked-template provenance veto - 2026-09-12 - HARD OVERRIDE
For any new card, old-card conversion, or full current-format rebuild, independently apply `references/Locked-Template-Style-Token-Contract.md`.

Before scoring the artifact, run both `scripts/validate_style_token_layer.py` and `scripts/validate_new_designed_family.py` on the **exact frozen PDF**. Verify the embedded token provenance, fixed panel geometry, locked palette, DejaVu shell typography, allowed locality/ID variant, A33 directions badge, allowed map-layout mode, and the final artifact hash. A missing or failed strict-token report caps template/family/overall at 8 and blocks release.

Do not treat A33/60AB/330/345 historical font/icon differences as permission to improvise new output. Existing released cards may be compatibility references; new R48 output must use the R48 token layer. Current 288 and current 262A are retained negative shell-drift regressions until rebuilt through R48; their existence is not a pass.

The internal reviewer uses this same locked-template provenance veto under the R48 parity contract. A builder claim or renderer metadata alone is not visual approval; inspect actual-size and close-up screenshots as usual.


## R48 Identity / filename critic veto — 2026-09-12 — HARD OVERRIDE
Independently verify the source/master alias, visible card ID, extracted PDF identity, and actual delivered filename against `references/Territory-Identity-Naming-Contract.md`. The BIG Map label is evidence, not the rendered identity. Residential/default cards never show `R`; classifications appear before the number on-card (`A263a`, `T263a`, `TA263a`) and after the zero-padded number in the filename (`263Aa`, `263Ta`, `263TAa`).

A visible master-style ID (`R-263-A`, `T-247-N`), wrong class order, wrong suffix case, unresolved production identity, filename/display mismatch, hidden stale ID, or actual filename differing from the derived canonical filename is a hard blocker. Set `release_ready=false` and cap identity/template/export/overall at 8 until repaired. Internal review under R46 applies this exact same veto.


### R48 mandatory identity-review schema
The critic/internal reviewer must independently populate and validate the complete `territory_identity_review` defined by `Territory-Identity-Naming-Contract.md`. Recompute the canonical card ID/filename rather than trusting builder-derived strings. On `final_saved` review, inspect the exact delivered basename, extracted text, PDF metadata and artifact SHA-256. Any missing/false field, stale source/master identity, hidden old ID, unresolved production identity or validator failure blocks release and caps identity/template/export/overall at 8.



## R49 Source-truth re-grounding + anti-anchoring veto — 2026-09-12 — HARD OVERRIDE
Read `Territory-Source-Truth-Preflight-Contract.md` before reviewing any new/rebuilt/materially redrawn card. The builder's `source_truth_preflight`, prior passing score, prior critic prose, and deterministic validator results are **not proof** of geography or family resemblance. Re-open the raw assignment/boundary source and current topology source yourself and independently reconstruct enough of the road graph to challenge every worked/boundary road plus each junction/termination that determines coverage. Populate `critic_source_truth_review`; `builder_topology_ledger_used_as_proof` and `prior_score_used_as_proof` must both be false.

For residential/neighborhood redraws, independently inspect a direct side-by-side map crop against exact saved Territory 273 in addition to the canonical shell references. Shell/token similarity cannot justify a >9 family score when street drawing, label grammar, occupancy, curvature, cul-de-sacs, junctions or overall map character visibly differ. Any obvious family mismatch blocks critic PASS before numerical averaging.

Territory 269 R48 is a permanent negative regression: its old 9.4/9.7 internal reports were user-rejected for wrong geography and family mismatch. Never cite those scores/artifacts as positive evidence. A user-reported defect reopens approval immediately. Run `validate_source_truth_preflight.py` for evidence consistency, but remember that its PASS cannot prove source truth or visual quality.

## R50 Independent rendered-road/label audit — 2026-09-13 — HARD OVERRIDE
Read `Territory-Label-Completeness-Preflight-Contract.md` on every new/rebuilt/materially redrawn card and every label-defect repair. A builder label ledger, validator PASS, prior label score, or generated preview is not proof that labels are complete or correctly placed.

Independently re-inventory every visible road/branch from the exact PDF and raw name/topology evidence. Verify that every visible named public street and cul-de-sac has a correct label, and that every intentionally unlabeled feature is independently proven private or unnamed. Populate `critic_label_audit`; `builder_label_ledger_used_as_proof` and `prior_label_score_used_as_proof` must be false.

Inspect every label at actual size and close-up. Hard vetoes include: any glyph sitting on/touching/overlapping any road; any missing required street/cul-de-sac label; any wrong-road label; any avoidable label cluster; any label pair/group whose ownership is unclear; any short-street direct label that fails fit/breathing; any callout used before direct/curved same-road options were exhausted; any detached leader; wrong target; bulb-only target when a usable stem exists; word/road/leader crossing; or arrow knot.

Every <12 px label-neighbor trigger recorded by R50 must receive explicit actual-size + 4x cluster review. The critic must also look for clusters the builder failed to record. Zero geometric overlap is necessary but not sufficient: if `Winter Park Rd`/`Winter Park Ct`-style crowding remains while a cleaner position exists, FAIL/FIX_REQUIRED and cap labels/family/overall at 8.0.

For residential/neighborhood maps, compare the label system side-by-side with exact saved Territory 273. The permanent Territory 269 R50 negative fixture demonstrates two independent failures that must never pass: a long street label laying on its road, and an avoidably crowded long-street/short-court label neighborhood.

A generated raster/map image may be reviewed as a draft only. It cannot receive a release score. Formal critic scoring begins only on the exact measurable PDF candidate.



## R51 Independent label-metric + PDF-delivery review — 2026-09-13 — HARD OVERRIDE
Read `Territory-PDF-Label-Metric-Contract.md`. Reject any territory completion whose primary user deliverable is an image rather than the canonical PDF. Fresh PNG renders are review evidence only.

Independently remeasure all disputed/outlier labels plus at least three builder-selected reference labels from the exact PDF at 1x/72 dpi. Confirm the reference labels are genuinely good before using them as the baseline. Check the median reference gap, ±3 px default consistency band, actual road contact, and whole-word road following. A visually floating label fails even if it remains within the broad 2–15 px hard band.

Independently verify every road with `navigation_repeat_required:true` has the required number of distinct, useful, non-cluttering label placements. Do not count duplicate text that occupies essentially the same navigational run. Require `delivery_format_review`, `label_metric_review`, and `critic_label_metric_review`; run `validate_pdf_label_metrics.py` and retain the existing R50 vetoes.

## R52 Navigation-role and whole-label critic veto — 2026-09-13 — HARD OVERRIDE
Apply `Territory-Segment-Role-Whole-Label-Contract.md` in mandatory authorized-internal and any separate critic lanes. Reopen the raw source/target lock; independently trace every entrance/repeated placement to its exact required physical run. Correct street spelling and contact with another same-named segment do not pass. Inspect start, middle, final word and complete suffix; reject partial road-following or visible crowding even with zero collisions. Verify actual-font advances and final-PDF transforms, not builder assertions. Require both R52 report objects, fresh inspected actual-size/closeup evidence and `validate_label_navigation_contract.py`. Wrong role/target, wandering suffix or cramped spacing is a hard veto, caps affected visual parts/overall at 8, and reopens the repair loop. Preserve the user-approved T269 component reference; old 9.7/10 and cramped first repair remain negative. Do not turn a bounded label review into whole-card geography certification.