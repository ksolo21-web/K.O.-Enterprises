---
name: territory-card-critic
description: Independently critique congregation territory cards using fresh full-page and close-up screenshots, score 0–10, and repeat authorized repairs and reviews until 10/10 with every mandatory gate passed. Use for territory-card creation, revisions, release QA, or requests for a separate territory critic. Companion to territory-map-card-builder, not for unrelated design or geopolitical maps.
---

# Territory Card Critic

Launch a separate critic agent for every territory-card release. This saved workflow recreates the critic in any chat; it does not preserve a running agent or assume previous chat files remain accessible.

## Recover the actual task

Read the available `territory-map-card-builder` skill and its applicable rendering and QA references. Identify the current PDF, accepted source drawing, approved sidebar/design reference, user-authorized changes, and source/name evidence. Resolve inputs from current attachments or saved files, not remembered scratch paths. If a required source is unavailable, report that gate as unverified and retrieve or request it; never substitute a guessed drawing.

Apply the builder's source classification first. For Kaleb's collection, the 91 newly drawn `Maps.zip` sources are locked as current geometry/work-color authority; modern-looking legacy cards are not automatically members of that locked set. Older maps may receive evidence-backed corrections within the user's authorized update batch. Review declared legacy changes against source evidence and the stroke-style gate instead of demanding repeat permission solely because their old paths changed. This does not authorize altering the 91 new drawings or inventing coverage/work-rule changes. Record the actual source member/hash and honor later individual approvals.

Keep `preserve_supplied_map` locked for accepted linework. Review does not authorize redraws, tracing, recoloring, geometry repairs, new work rules, or a new inset. Preserve existing user approvals and limits. A request only to audit authorizes evidence creation, not changes to the card; a repair-and-review request authorizes in-scope layout/label fixes.

## Separate builder from critic

Use a fresh subagent with minimal context. Give it raw inputs, current instructions, this skill, and the territory standards, not the builder's scores, claimed passes, expected diagnosis, or suggested answer. The critic renders and inspects its own screenshots and cannot edit the card. When subagents are unavailable, disclose that independent review is blocked; a self-review is not a substitute.

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

Give each category a 0–10 score with evidence and calculate the weighted mean:

| Category key | Weight | Required checks |
|---|---:|---|
| preservation | 25% | Complete supplied linework, uniform scale, source colors, no unauthorized changes; any permitted repairs match source stroke style |
| geography | 25% | At least two evidenced distinct major cross roads drawn/readably labeled with connected approaches and directions; correct road/name bindings, boundaries, work sides, entrances; fresh complete street/property discovery; sources resolve conflicts |
| labels | 25% | Every required name readable, aligned to road, no overlaps, partial lift or avoidable clusters; same-road whitespace assessed; necessary callouts only; correct clean arrow targets |
| template | 15% | Approved legend scale, colors/order, spacing, alignment, sidebar, calendar/update block, map balance |
| export | 10% | One front page, no exclusions list, no clipping, actual PDF below 300000 bytes, final screenshots, no on-card source/audit lines, extracted text matches visible territory/locality |

Interpret 0 as absent/not completed; 1–4 as major failures; 5–6 as substantial defects; 7 to below 10 as needs correction and not releasable; 10 as no observable defects under the stated checks, never proof of physical-world perfection. Aim for 10/10 on every card and pursue useful authorized improvements. Release requires every category to equal 10/10, the unrounded weighted score to equal 10, and all mandatory gates to pass. Never round up or inflate scores.

Any hard territory gate failure or unverified required evidence blocks release regardless of mean score. Cap the overall score at 8 when blockers exist. Never lower standards, discard findings, hide a source defect, or inflate scores to terminate a loop. Distinguish source-inherited defects from newly introduced ones; neither authorizes a source edit. If inherited geometry conflicts with hard gates, stop for user direction instead of silently repairing or waiving it.

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
4. Continue while useful authorized fixes remain, aiming for 10/10. Release requires a score of exactly 10/10 and every hard gate passed; scores below 10 do not pass. Do not create endless blind retries: when a permission/source ambiguity blocks progress or two rounds make no measurable progress, report the exact blocker and request the needed decision without claiming completion.
5. Recheck the exact delivery PDF after optimization or saving changes; invalidate a score if the artifact hash changes. Save final card and review evidence through the environment's persistent artifact workflow, keeping audit material separate if embedding would break the PDF size limit.
6. After a reported download/preview mismatch, require a distinctly named fresh export and a delivery audit binding the final download path to the newly saved file ID, version and retained-byte SHA-256. Inspect a freshly retrieved copy of that exact saved object with full-page/close-up screenshots and extracted text; verify source/audit lines are absent and inspect a fresh preview from the same bytes. A clean working copy is insufficient. Reject stale copied xattrs or old link registration as proof of delivery identity, and do not diagnose caching without evidence. If a ZIP is supplied for an unambiguous handoff, compare its PDF member hashes with the exact reviewed retained copies. Record these checks under `delivery_identity_review`; keep geographic blockers and score limits unchanged.
7. Report score, number of rounds, material corrections, and any remaining minor caveats. In old or new chats, users can request `Use Territory Card Critic`; do not promise the same live agent persists or that a stale chat automatically refreshes its skill catalog.

## Assigned housing and printed instructions

Apply the user-authorized precedence in [references/housing-instructions.md](references/housing-instructions.md) on every card. Marked assigned residences control obsolete housing-type restrictions, including apartments, condominiums, townhomes and mobile homes. Require the builder to revise conflicting printed directions or work notes without repeatedly requesting the already authorized decision. Independently verify scope in both directions: retain work colors, inside-only sides, explicit map exclusions and verified other-territory/access restrictions. A workable approach alone does not assign a separately assigned complex. Record user provenance, full property bindings and actual final text in required `housing_instruction_review`. Any missing evidence, unresolved conflict, housing-only exclusion of assigned residences or instruction expansion caps score at 8 and makes release false. The target remains 10 and threshold exactly 10 with all hard gates passed.

## Access notation, continuous streets and usable-road placement

Apply [references/navigation-presentation.md](references/navigation-presentation.md) on every final candidate and populate required `navigation_presentation_review`. Prefer clear named-street access/directions over redundant entrance keys; preserve necessary approved numbered-key conventions. Inspect full street paths for unexplained kinks, step-offs and discontinuous joins across actual full-page and close-up views. Reassess the center of each usable road run and available southern whitespace after repairs; no collision alone is not a placement pass. Missing or failed evidence blocks release without changing any preservation, geometry, style, gap or scoring cutoff. Detection grants no automatic redraw authority.

## Required branch and status-paint review

Apply [references/branch-color-filenames.md](references/branch-color-filenames.md) on each working and saved-artifact review. Independently enumerate navigationally distinct branches and mixed-status junctions; record required `branch_color_review`. Explicit source-paint slivers, missing necessary branch labels and avoidable clusters veto numerical passes. Confirm individual delivery filename `Territory - 000Letters.pdf`, with visible card identity unchanged. User standard is exactly 10/10 in every category with all mandatory checks/evidence.

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
