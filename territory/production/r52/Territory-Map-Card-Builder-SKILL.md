---
name: territory-map-card-builder
description: Automatically load and use the active territory-card skill system in regular Chat and Work whenever a congregation territory card/map is created, revised, repaired, converted, reviewed, audited for release, or exported. Create, label, revise, audit, or export congregation territory cards and coverage maps. Automatically use this skill when the user asks to make, rebuild, update, correct, convert, resize, style, or inspect a territory card, territory map, territory boundary, work-inside-only map, work-both-sides map, missing territory coverage, old territory-card conversion, or numbered territory such as 255A or 252A. Also trigger for an updated hand-drawn map, territory PDF, map screenshot, Canva territory design, street-boundary instructions, apartment-complex name, named entrance, or major cross-road request. Do not trigger for geopolitical territories, fantasy maps, ordinary navigation, or real-estate and business sales-territory charts. Preserve approved supplied linework, verify street and site names, and block release until labels, entrances, connected navigation context, arrows, work rules, map preservation, page fit, and file size pass strict gates.
---

# Territory Map Card Builder

Build territory cards as verified field-service maps, not approximated illustrations.

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
**R46 standing authorization:** a mandatory authorized-internal critic-only review runs
on every created or changed territory artifact without asking again. Record
`reviewer_type: authorized_internal` and `critic_independent: false`; never call it
independent. The internal reviewer uses the exact same critic contract, evidence,
hard vetoes and score floor. A genuinely separate critic is additional whenever a
callable runtime exists or independence is required; it never replaces the mandatory
internal review. Read `references/Territory-Automatic-Execution-Contract.md`.

A real permission boundary is not permission to guess or bypass access. Attempt
available authorized recovery routes, continue other unblocked cards, and preserve
the exact state. Platform/session interruption means interrupted work, not PASS
and not a promise of unattended continuation. A new turn resumes the saved round
rather than resetting a two-round counter. Do not interrupt the user merely
because a round failed or there is more routine work to do.

Use `scripts/continuous_review.py` to validate the round decision and preserve
`loop-state.json`; it does not generate a critic judgment or a passing score.

## R46 Automatic execution — Chat + Work — HARD OVERRIDE

For any territory-card intent, **regular Chat and Work automatically load the active
territory package before substantive work**. No user phrase such as “use the skills”
or “run the critic” is required. Read `/Skills/Territory Cards/ACTIVE-SKILLS.json`,
then `references/Territory-Automatic-Execution-Contract.md`.

For every territory artifact that is created or changed, the mandatory chain is:

`load active skills -> build -> deterministic gates -> freeze candidate -> mandatory internal critic-only review -> repair/retest loop -> separate critic too when available/required -> exact saved-PDF recapture -> mandatory final internal review -> release`.

The internal reviewer is mandatory even if a separate critic exists. If the active
skill package cannot be loaded in the current surface, recover it through an allowed
Project/repository/package route or block artifact release; never silently use a
generic map workflow.

## Automatic trigger contract

Use this skill as the primary workflow whenever any part of a territory-card artifact is being created or revised, including:

- a new territory card or territory map;
- a redraw of an old, blurry, cropped, or inaccurate card;
- a correction to a territory boundary, street, label, color, work rule, or page crop;
- conversion of an old territory PDF or image into the current card style;
- identification or filling of gaps in total territory coverage;
- a territory overview, route-coverage map, or card index;
- a Canva or PDF territory-card deliverable;
- requests mentioning territory numbers, `Work Inside Only`, `Work Both Sides`, `Do Not Work`, perimeter streets, internal streets, green/yellow/red street rules, or missing streets.

This skill owns map preservation, name verification, label placement, and territory-rule interpretation. Delegate only final-format operations after the map and label audit pass:

- use the PDF skill for PDF rendering, inspection, optimization, and export verification;
- use Canva only for approved card styling or layout, never to redraw or distort accepted street linework;
- never use image generation to invent, redraw, or approximate street geometry.

## Non-negotiable map modes

Choose and record exactly one mode before editing:

For Kaleb's territory collection, apply the September 6, 2026 source distinction before locking a map:

- The 91 newly drawn maps supplied in `Maps.zip` are accepted as current and accurate. Lock their supplied street geometry and work colors; audit labels, presentation and completeness without changing that drawing. Report a source conflict instead of silently correcting it. Match the actual archive member/source identity, not a territory-number range or a filename containing “new,” “final,” or “verified.”
- Other older maps may need evidence-backed street, topology and label corrections as part of the authorized update batch. A modern card layout or earlier provisional export does not turn legacy linework into one of the 91 locked drawings. Preserve the original for comparison, record verified corrections and their scope, and retain assigned coverage/work rules unless the user changes them. Do not ask again for routine legacy corrections already authorized; do not infer unverified roads or territory expansion.
- Record `source_class` as `locked_new_drawing`, `legacy_update_candidate`, or `unresolved`, with the source filename/hash. A specific later approval can lock any individual map. Localized legacy stroke repairs still require declared masks, zero change outside them, matching original stroke style and independent review.

- `preserve_supplied_map`: default when the user supplies a new hand-drawn map and says its street linework and colors are correct. That supplied map is the visual authority. Do not redraw, recolor, straighten, trace over, or replace its streets. Add verified street names and crop/scale the complete map uniformly. Removing obsolete neutral text is allowed only when the colored route pixels remain unchanged.
- `vector_rebuild`: use only when no accepted supplied map exists, the source is unusable, or the user explicitly requests a geometry rebuild. Use published legal vector data and retain source feature IDs.

Never switch modes merely because a live map looks cleaner. Current map sources verify names and topology; they do not override accepted supplied work colors or linework without an explicit correction.

Once a user accepts a supplied map or card, lock `preserve_supplied_map` and record the approved-base hash. A request to fix labels, junctions, colors, or other marked defects does not authorize a full redraw. Switch to `vector_rebuild` only after the user explicitly authorizes rebuilding the entire geometry.

## Source hierarchy

For street names and topology checks, use the most authoritative current source available, in this order:

1. county or municipal GIS road centerlines, parcels, addresses, rights-of-way, and boundaries;
2. state GIS open data;
3. OpenStreetMap for current or missing local streets and cross-checking;
4. Census TIGER/Line as fallback context;
5. an old card only for historic boundary intent and work instructions.

For rendered linework, an accepted updated supplied map outranks all sources in `preserve_supplied_map` mode. Live-map disagreements must be reported and resolved; do not silently redraw the supplied map.

Never extract or trace proprietary commercial map tiles as the permanent geometry dataset. Never claim a map is current without checking a current source.

Read [references/source-priority.md](references/source-priority.md) before gathering geometry.

## Required workflow

### 1. Intake and inspect

- Identify territory number, locality, desired format, current design, and reference files.
- For PDFs, render and inspect every map page using the PDF skill before interpretation.
- Record all visible boundary instructions, street names, color rules, notes, and corrections.
- Distinguish an old reference card from the accepted updated supplied map. Preserve the latter exactly.

### 2. Establish geographic location

- Resolve at least two unmistakable named intersections or one boundary plus multiple streets.
- Prefer four or more georeferencing control points when an old raster map guides the boundary.
- If the place cannot be uniquely resolved, do not invent it. Mark the location unresolved and stop release.

### 3. Verify the street inventory

- Before declaring **any** territory complete, perform a fresh, dated discovery check for new or missing streets and eligible properties across its full assigned boundary and immediate edges. Apply this to legacy cards, previously completed cards, and all 91 locked new drawings. Verifying only names already printed on the card is insufficient; source acceptance does not waive discovery.
- Include subdivision loops, cul-de-sacs, dead ends, service/private roads, alleys, divided carriageways, and unnamed access where relevant to the territory's actual work rules. Distinguish a navigable street from a driveway and a verified eligible property from an assumed one.
- Compare the complete current inventory with the supplied map and its assigned coverage. Use current county/municipal sources and a second current source for recent additions; inspect dated imagery or official development/property evidence where the road inventory may lag.
- Save a `current_inventory_review` audit with check date, source URLs and retrieval dates, source update/imagery dates or explicit unknown recency, geographic bounds, feature IDs/counts, complete pagination/transfer-limit evidence, matched and unmatched features, additions, eligibility decisions, and unresolved discrepancies. Read [references/source-priority.md](references/source-priority.md) for the evidence requirements.
- Preserve the 91 locked drawings when discovery reveals a conflict. Report it and obtain the needed correction authority; do not redraw silently. For older maps, make evidence-backed corrections already authorized in the update batch.
- Block completion when the boundary, street inventory, relevant property eligibility, or retrieval completeness remains unresolved. Report what was actually checked; do not promise that no real-world changes exist beyond the available dated evidence.

### 3A. Verify named sites and entrances

- Check whether the territory is a named apartment complex, condominium community, mobile-home park, campus, or similar property.
- Add a site name only when a current live map, official property source, or visible entrance sign verifies it. Never invent or infer a marketing name.
- Inventory every verified operational entrance relevant to field navigation. Record its entrance name or cardinal designation, the public street serving it, and the exact access stem or junction it uses.
- When the property name already appears once in the map, use concise entrance labels such as `North Entrance` and `West Entrance`; do not repeat the full property name in every callout.

### 4. Preserve or reconstruct the territory assignment

Read [references/coverage-model.md](references/coverage-model.md). Record `coverage_review` and a complete `current_inventory_review` for every card. Use the actual assignment representation: closed polygon, or verified explicit road segments/sides in preservation mode. The latter requires source/hash, resolved endpoints/rules/sides, complete bounded road/property dispositions and reviewed immediate edges; it never waives unresolved coverage or eligibility.

- In `preserve_supplied_map` mode, preserve the supplied colored boundary exactly except inside an explicit user-directed correction mask.
- In `vector_rebuild` mode, convert the territory edge into a closed vector polygon.
- Follow the original work instructions, not the visual distortion of the old card.
- Boundary segments may follow road centerlines, parcels, municipal lines, railways, waterways, or explicit user corrections.
- Save every user correction as a persistent geometry or rule patch, not merely as prose.

### 5. Classify every road segment

Assign each segment one class and one work rule:

- `interior` + `both_sides`;
- `perimeter` + `inside_only`, with the worked side explicitly identified;
- `excluded` + `do_not_work`;
- `context` + `context_only`.

Split a road into multiple segments when the rule changes along its length. Never apply one rule to an entire named road when only part of it borders the territory.

Read [references/territory-rules.md](references/territory-rules.md).

### 6. Determine worked side mathematically

For every `perimeter` segment:

- determine which side faces the territory polygon;
- store `left`, `right`, a cardinal direction, or `mixed` with segment-specific instructions;
- verify the side after reprojection and page rotation;
- visually encode the inside-only rule so a worker cannot mistake the worked side.

A yellow line by itself is insufficient when the worked side is ambiguous.

### 7. Render without altering the selected map authority

For `preserve_supplied_map`, use:

`immutable accepted base -> declared correction/label layers -> verified one-page PDF`

- Preserve all supplied colored route and boundary pixels outside explicit user-directed correction masks.
- Never draw replacement streets over the supplied map outside those masks.
- When the user marks a defect on an already accepted map, declare the smallest rectangular or polygonal correction mask that contains it. Keep the approved base as a separate immutable layer and apply only the requested repair above it. Do not move, reshape, relabel, recolor, or restyle anything outside those masks.
- For an already approved card revision, render the approved base and the candidate at the same size and compare them pixel by pixel. Release requires `pixels_changed_outside_declared_correction_masks == 0`, including renderer interpolation; use a small declared guard around each edit when necessary. If its original native map differs from the retained approved card, preserve both actual path/hash authorities and the separate retained-card comparison required by [references/native-topology-gate.md](references/native-topology-gate.md); `approved_base` continues to mean the approved card.
- Zero change outside the masks is necessary but not sufficient. If a correction changes a colored street or boundary stroke, compare it with nearby untouched approved strokes in the raster rendered from the actual final PDF at 2x. The repair must match the source's width, status color, edge softness and antialiasing, curvature and centerline character, texture, mask-boundary seam, and endpoint profile.
- Run `python scripts/validate_stroke_style.py` for every existing-path stroke-repair mask (typed authorized topology masks require the separate native topology gate), store its report and hash in `preservation_audit`, and inspect paired 4x crops. At multistatus junctions, compare width, color, softness, and texture only with the same status; evaluate the combined source path for curvature so a corrected status handoff does not manufacture a false bend. A numeric pass never overrules a visible mismatch, and thresholds must never be loosened to make a repair pass.
- Scale uniformly only when required for label clearance or verified navigation context. Record equal horizontal and vertical scale values plus translation. Preserve the aspect ratio, every supplied colored segment, and all source relationships.
- Crop only blank or explicitly unwanted context; never clip named or worked streets.
- When approach roads are missing, add only the minimum verified major-road context needed to reach the territory. The context must visibly connect through verified approach streets; isolated road labels do not count.

For `vector_rebuild`, use:

`authoritative GIS -> GeoJSON or GeoPackage -> styled SVG -> verified PDF`

- Keep streets as vector paths, retain topology, and document every manual correction.

Read [references/rendering-standard.md](references/rendering-standard.md). For existing-path repairs, apply [references/stroke-style-gate.md](references/stroke-style-gate.md). For source-backed authorized native additions/removals, apply [references/native-topology-gate.md](references/native-topology-gate.md); this separate typed gate proves the independently planned topology delta, original styling and actual final PDF without changing the old comparator or its cutoffs. Mixed edits require both gates.

### 8. Place street labels professionally

- Bind labels to their actual road objects.
- Use one regular-weight typeface for every street name; never bold a street name.
- Place direct labels beside their assigned street with a measured 2-15 px edge gap. They must not touch or cover street linework.
- For curved streets, bend the full label with the street and keep the entire guide consistently close. A label fails if one end is flush while the other end is visibly lifted away.
- Prefer direct or curved placement whenever the full name fits. Do not use an arrow merely because positioning requires care.
- Use a callout only when the street is genuinely too short for its full name. The leader must start just outside the label, remain separate from every label and other leader, use one clean stroke with a filled triangular arrowhead, avoid unrelated roads, and end on the named street's stem rather than only its cul-de-sac bulb.
- Preserve approved original numbered-key reference connectors according to [references/rendering-standard.md](references/rendering-standard.md). Short neutral, single-segment unheaded ticks, such as original A2 markers 10 and 15, retain that source style; explicitly record no arrowheads and verify number → connector → currently verified street → key. This source representation does not waive spacing or collision checks. New street and entrance callouts still require filled triangular arrowheads.
- Check letters within each curved word as well as collisions between separate labels. Require actual isolated glyph-ink evidence and independent actual-size/close-up legibility review using [references/label-glyph-review.md](references/label-glyph-review.md). Guide-induced overlapping or touching letters block release even when street gaps pass; ordinary kerning or a zero raster-cell edge distance alone does not justify adding letter spacing.
- Keep text upright and inside page bounds.
- Repeat names on long or disconnected segments when needed.
- Prioritize territory streets over context streets.
- Reject misplaced, clipped, overlapping, unreadable, or wrong-road labels.
- Review each label cluster at actual output size and in close-up even when collision and street-gap checks pass. Labels crowded around the same junction fail when clearer whitespace exists beside the same assigned road. Compare positions farther along that road, on its opposite side, and beside another suitable straight segment; choose the clearest unambiguous placement while preserving regular type, road association, and the required gap. Do not shrink text, add avoidable arrows, or alter map strokes to clear clutter. During a bounded revision, fix authorized labels and report unrelated blockers without expanding the edit scope.
- Use Territory 254's northern inset as a regression example: the user moved Quarter St below its road and West St to the segment above Renshaw St, separating labels previously crowded near Quarter/West. These are locations for that approved card, not universal positions for those names. Record `qa.avoidable_label_clusters = 0` and `qa.label_cluster_review_completed = true` only after whole-cluster visual review and same-road alternatives have been checked.

### 8A. Place site and entrance labels

- Place one verified property or complex name in clear interior whitespace, using the map's regular-weight font family. It must not cover a route, street, building/work shape, or another label.
- First assess whether named streets and directions already identify access; then apply the required navigation-presentation review. Use a feature callout only when that adds needed navigation information; arrows are expected when a necessary short access stem cannot carry its name.
- Bind every entrance callout to one verified entrance record and one verified access stem.
- Aim the arrow tip at the actual entrance/access stem or junction. Do not point at the property center, a building, parking area, nearby public road, unrelated route, or only a cul-de-sac bulb.
- Use one clean leader with a filled triangular head. Keep its shaft clear of text, other arrows, and unrelated roads except within the small allowed target radius at the entrance.
- State in the directions which public street serves each labeled entrance.

### 9. Apply territory styling

Default semantics unless the source card or user explicitly overrides them:

- green: work both sides / normal workable interior;
- yellow: perimeter street / work territory-facing side only;
- red: outside territory or do not work;
- muted context: orientation only and never implied to be workable.

Verified non-work navigation roads added outside the supplied map use red unless the territory rules assign another status. Never paint a new status color over accepted supplied linework.

Each rendered segment must have exactly one work-status color. At a multi-status junction, record one node owner and trim the other strokes to clean tangent endpoints. Side branches must stop before a differently colored boundary stroke; stacked caps, blended junction blobs, branch overshoots, and orphan colored dots fail release.

Treat the left-sidebar legend as a template-critical component, not a presence-only checklist. Match the approved reference's readable label scale, compact rounded swatches, row order, row spacing, left alignment, lower divider, calendar icon, and update block. A compressed legend, undersized labels, missing calendar block, or excessive unused space fails release even when all three colors and phrases are present.

For Kaleb's cards, use the shared sidebar palette `#FFDC18` / `#51C72B` / `#FF1435` independently of the source map's preserved colors. Read [references/visual-evidence-integrity.md](references/visual-evidence-integrity.md) for the standalone actual-PDF palette check, prior source-fixed entrance-radius evidence, independent complete-stroke cross-section checks, and whole-word/suffix legibility veto. Apply these supplemental checks without changing active validator thresholds.

### 9A. Show at least two verified major cross roads on EVERY card

- Require at least **two distinct verified MAJOR cross roads** for location orientation on every card: legacy, previously completed, all 91 locked new drawings, and future cards. No source acceptance or earlier score waives this gate. Count physical roads, not repeated labels, aliases, divided carriageways of one road, or minor internal streets.
- Read [references/major-crossroads.md](references/major-crossroads.md) and populate `major_crossroad_review`; the deterministic validator enforces distinct identities, evidence, drawing/label bindings, connected approach and directions. Missing or unverified second major road is a hard failure; the independent critic caps the overall score at 8 and sets release false. Keep the target 10/10 and minimum specified by the active acceptance policy (default 9/10).
- Prefer the minimum connected approach: major road -> verified approach street(s) -> territory.
- Include the road geometry and label; a floating major-road name without a connected road line fails.
- Keep this context outside the accepted supplied-map layer and verify its names and connections against current sources.

Do not use decorative styling that obscures work instructions. Ensure all relevant internal streets remain visible.

### 10. Compare and verify label by label

Produce a verification overlay or equivalent machine-checkable comparison showing:

- source roads;
- rendered roads;
- territory boundary;
- old-card boundary when applicable;
- missing roads;
- extra roads;
- source conflicts;
- unresolved work rules;
- street-name mismatches;
- wrong-road label assignments;
- label-to-street gaps and partial-lift measurements;
- label collisions, street coverage, and clipping;
- avoidable label clustering, available same-road whitespace, and actual-size plus close-up visual evidence for the chosen placements;
- mixed-status overlaps, branch endpoint overshoots, and colored endpoint artifacts in both vector geometry and the final 2x render;
- unnecessary callouts, malformed arrowheads, wrong arrow targets, and arrow collisions;
- supplied-map pixel changes in `preserve_supplied_map` mode.
- legend label size, swatch dimensions, row spacing and alignment, lower divider, calendar/update block, and excessive sidebar dead space against the approved sidebar reference;
- any rendered pixel change outside declared correction masks when revising an approved card;
- every repaired-stroke mask's measured width, color, edge-softness, curvature/centerline, texture, seam, unexpected-status, and paired 4x visual-review result;
- the approved-base hash, original mode, redraw-authorization state, and every correction-mask bound;
- missing, extra, or unverified named sites and entrances;
- entrance-label and entrance-arrow target bindings;
- arrow-tip distance from the verified access stem and target box;
- entrance-arrow collisions outside the allowed target radius;
- isolated or disconnected major-road context;
- non-uniform source-map scaling, clipping, or hidden supplied colored pixels;
- missing directions associations between entrances and their serving public streets.

Run `python scripts/validate_project.py PROJECT.json` before release.

### 11. Export and audit

Before release, apply the installed `territory-card-critic` skill. Resolve it by frontmatter name in the available personal skills, not a remembered temporary path. Launch its separate critic with raw source and candidate files; require fresh full-page and close-up screenshots at initial review, after repairs, and from the final export. Aim for 10/10 on every card and pursue useful authorized improvements. Repeat authorized fixes and independent review until the score meets the active minimum (default 9/10) with no hard-gate failures or unverified required evidence. Do not round up or inflate any category score; every category must meet the active minimum (default 9/10). A score never waives this skill's preservation or geographic gates. If the critic is unavailable or a needed change lacks authority, report that blocker instead of claiming independent verification. In critic-only mode, do not spawn another critic recursively.

Deliver the approved digital format:

- one front-page PDF only; no card back;
- the `Do Not Work` legend remains, but do not add a do-not-work address list or bottom-panel do-not-work list;
- editable SVG and preview PNG as internal masters when available;
- validation report or audit JSON, kept separate from the card;
- no on-card source-credit or audit lines such as `Names: Oakland County GIS / Auburn Gate`, `Names checked: ...`, verification badges, or source URLs. Keep required attribution, citations and verification dates in the separate audit evidence; removing a footer does not remove the evidence requirement;
- GeoJSON or GeoPackage only for `vector_rebuild` projects.

The final PDF must be smaller than 300,000 bytes. Optimize after visual approval; never reduce it by making names unreadable.

### 11A. Resolve a delivered-file mismatch

When the user reports that a download or preview differs from the reviewed card, treat the delivered object as unverified. Do not assert a cache cause without evidence. Create a distinctly named fresh export and save it with a fresh receipt; do not reuse stale copied file metadata/xattrs or a previous link registration. Record the exact final download path, saved file ID, version and retained-byte SHA-256 in the delivery audit. Retrieve the newly saved object, rerun the full visual and extracted-text checks on that retained copy, and inspect a fresh source-credit-free preview made from those same bytes. Bind the final link and critic report to this exact object, not merely a clean working copy. If useful for an unambiguous handoff, also provide a ZIP containing the exact verified PDFs and verify each member's hash. Delivery repair never waives unresolved geographic gates or establishes an overall pass.

## Fail-closed release gates

Do not label a territory card complete when any of these remain:

- unresolved location or source conflict affecting geometry;
- missing or invented roads;
- disconnected intersections;
- an open or self-crossing polygon boundary; an explicit road-segment assignment with missing source/endpoints/sides, incomplete bounded inventory, or any unresolved coverage edge or property eligibility;
- unclassified road segments;
- perimeter street without a verified worked side;
- hidden internal streets;
- any segment carrying more than one status color, any mixed-color junction blob, any branch projecting into a differently colored boundary, or any orphan colored endpoint artifact;
- wrong, missing, clipped, or colliding required labels;
- missing final-artifact-bound curved-word glyph evidence, actual same-label ink overlap, or independently observed guide-induced letter crowding;
- avoidably crowded label clusters, including labels that individually pass collision/gap checks but have clearer placement along their assigned roads;
- any street-name pixel touching or covering street linework;
- any direct or curved label outside the 2-15 px placement standard;
- a curved label that is only partially flush with its road;
- a callout used where direct placement fits;
- an unclear, malformed, overlapping, or wrong-target arrow;
- map content cut off by the page;
- altered supplied linework outside explicit correction masks in `preserve_supplied_map` mode;
- any switch away from a locked approved-map mode without explicit full-redraw authorization;
- any rendered pixel changed outside a declared correction mask during an approved-card revision;
- any repaired street or boundary stroke that is visibly distinguishable from nearby untouched source linework, even when it remains inside its mask or passes numeric tolerances;
- missing, invented, duplicated, or unverified property/complex names;
- missing verified access representations, or extra/unnecessary entrance callouts compared with the reviewed representation inventory;
- entrance arrow aimed at anything except its verified access stem or junction;
- entrance arrow crossing an unrelated road or another callout outside its target radius;
- property name or entrance label obscuring a road, route, building/work shape, or label;
- fewer than two distinct verified major cross roads on any card, missing major-road/source evidence or drawing/label bindings, isolated names, or navigation context that does not visibly connect to the territory;
- non-uniform scaling, undeclared map transforms, clipping, or hidden supplied colored pixels;
- directions that omit the public street serving a labeled entrance;
- rasterized primary street geometry in `vector_rebuild` mode;
- unrecorded user corrections;
- missing source attribution in the separate audit evidence;
- an on-card source-credit or audit line;
- missing fresh discovery evidence for new/missing streets and relevant eligible properties, incomplete source retrieval, or unresolved inventory/boundary/eligibility discrepancies;
- visual design that can be confused with a different work rule;
- a legend that merely contains the correct phrases and colors but does not match the approved sidebar hierarchy, readable scale, alignment, spacing, divider, calendar icon, and update block;
- a back page, do-not-work list, or PDF size of 300,000 bytes or more.

Read [references/qa-gates.md](references/qa-gates.md).

## Revision behavior

When the user says a map is wrong:

1. identify the exact geometry, rule, label, crop, or styling failure;
2. if an approved map exists, keep its mode locked and declare a tight correction mask for each requested visual change;
3. update the structured project data and preservation audit first;
4. repair only those masks on a separate layer over the immutable approved base;
5. render the approved base and candidate identically, then require zero changed pixels outside the declared masks;
6. for every mask that changes colored linework, run its applicable existing-path or typed native-topology gate and compare paired 4x crops against nearby untouched source strokes;
7. reject any width, color, softness, curvature/centerline, texture, seam, endpoint, or unexpected-status mismatch; never tune the limits to force a pass;
8. rerun the full verification gates.

An uncontrolled cosmetic patch is not a correction. A mask-locked overlay with a recorded approved-base hash, a zero-outside-mask rendered comparison, and repaired-stroke style evidence is the required method for localized repairs to an accepted raster or PDF. Never substitute a full reconstruction unless the user explicitly authorizes one.

## Required truthfulness

Say exactly what was verified. Distinguish:

- authoritative-source geometry;
- cross-source agreement;
- user-directed manual correction;
- unresolved conflict;
- visual approximation used only for context.

Never claim physical-world perfection. Claim identity to the selected source dataset only when the comparison proves it.

## Assigned housing takes precedence

Apply the user-authorized rule in `references/housing-instructions.md` to every card: revise old housing exclusions when the marked workable assignment includes those residences. Retain work colors, inside-only sides, explicit map exclusions and verified other-territory/access limits. Record user provenance and require `housing_instruction_review`; missing or conflicting evidence hard-fails the builder. Do not repeatedly ask for this already authorized correction.

## Access notation, continuous streets and usable-road placement

Apply [references/navigation-presentation.md](references/navigation-presentation.md) on every final candidate and populate required `navigation_presentation_review`. Prefer clear named-street access/directions over redundant entrance keys; preserve necessary approved numbered-key conventions. Inspect full street paths for unexplained kinks, step-offs and discontinuous joins across actual full-page and close-up views. Reassess the center of each usable road run and available southern whitespace after repairs; no collision alone is not a placement pass. Missing or failed evidence blocks release without changing any preservation, geometry, style, gap or scoring cutoff. Detection grants no automatic redraw authority.

## Branch completeness, status paint and filenames

Apply [references/branch-color-filenames.md](references/branch-color-filenames.md) to every new review/export. Require its artifact-bound `branch_color_review` in PROJECT and independent critic reports. User-identified missing branch labels or mixed-status defects reopen approval. Deliver filenames as `Territory - 000Letters.pdf` only; keep visible card identities unchanged. Current user threshold is at least the active minimum (default 9/10) in every category with every required gate passed.

## Learning from returned cards

Read [references/learning-regressions.md](references/learning-regressions.md) at batch intake and whenever the user reports a missed defect. Preserve failed and corrected artifacts, test the changed rule against both, and carry versioned evidence into the next chat. A rule is not proven merely because it was written.

For release run `scripts/validate_release.py PROJECT.json CARD.pdf REVIEW.json --critic-script <installed-territory-card-critic>/scripts/critic_evidence.py`. Project validation alone is not release approval. This invokes both complete gates and independently requires every category to meet the active policy minimum.

For a mixed native addition followed by a predeclared existing terminal repair with the proven disconnected-fragment width-estimator defect, apply [references/mixed-native-existing-chain.md](references/mixed-native-existing-chain.md). Require its explicit original-to-final chain, independently reviewed estimator and actual final2x/4x evidence; never infer a waiver from an earlier source-crop pass.

For a retained full OSM response, require [references/osm-property-scope.md](references/osm-property-scope.md): independently audit all building/property candidates, preserve truthful raw XML/JSON provenance, and run the actual-PDF scope guard alongside both release gates.

For an explicitly source-planned neutral paint knockout, use [the native neutral knockout contract](references/native-neutral-knockout.md); do not relabel it as a path trim or topology removal.

For a source-reviewed addition/removal pair sharing one junction, apply [the shared junction contract](references/shared-junction-pairs.md). All member operations remain independently bound to the immutable original.

For narrowly source-bound unchanged native width evidence, apply [the exact native width contract](references/native-unchanged-width.md). Retain original PNG failures and all other gates; require independently pinned actual PNG evidence.

For every card require [the duplicate worked physical coverage contract](references/duplicate-worked-coverage.md). Treat new drawings as authoritative. Replay complete source-bound physical road intervals and canonical worked sides within and across relevant active cards; fully worked streets must not be worked twice. Missing scope, stale artifacts, ambiguous identity/sides, or any full/full, full/side or same-side positive overlap blocks release. Distinct local road IDs do not establish distinct physical coverage. Require independent source-to-artifact and complete-scope verification; a manually labeled scope alone never establishes a pass. Existing gates and correction authority remain unchanged.

### Raster-source street additions

For authorized additions to a raster-only source, declare `raster_topology_addition` masks with `contains_stroke_repair: true` and final-page coordinates. Use `raster_topology_review` with `scripts/raster_topology_contract.py`; retain immutable source and prior-plan provenance, exact replayed embedded pixels, identical expected renders at 1×/2×/4×, zero changes outside the declared masks with the fixed renderer guard, and the unchanged same-status stroke-style limits. Require an independent review bound to the report, replay program, exact arguments, prior plan, source geometry, representative reference strokes and paired close-ups. The gate must recompute the evidence. Never fabricate native-vector evidence for raster-only originals or omit a colored edit mask. Existing native topology and existing-path repair gates remain mandatory for their respective edit types.

Apply the user’s standing boundary rule: newly verified residential streets inside the territory’s red/yellow enclosing boundaries are workable unless an explicit exclusion or separate territory assignment applies. Retain red exclusions and the territory-facing yellow side. Check physical street intervals, sides and actual property access against neighboring assignments before release. Retain Telephone designation even when the residences include apartments or condos.
## New Designed visual regression gate — 2026-09-11

Apply [references/new-designed-visual-standard.md](references/new-designed-visual-standard.md) to every current-format territory card. This gate was added after the 255a–260 R19→R28 regression proved that collision-free labels can still be visibly cluttered and unlike the approved card family.

Before release, compare the exact final PDF side-by-side with at least two approved New Designed cards. Use this placement hierarchy: direct label → curved road-following label → clearer same-road whitespace → attached bent/gently routed leader → dedicated enlarged detail. Do **not** invent a numbered street-key/number legend as a density workaround. Preserve only an explicitly approved source numbered-connector convention.

A leader must visually attach to its label: its tail begins at the label block edge or within 0–2 px, without cutting glyph ink. A floating/detached leader, wrong-target leader, avoidable cluster, unauthorized numbered density key, or enlarged detail that overlays important full-map content is a hard release failure and cannot be averaged away by geography/export scores.

When density genuinely requires enlargement, use a professional 254/330-style detail in dedicated whitespace or a deliberate split panel. Keep the main map complete, uniformly scaled/repositioned when necessary, and source-faithful. Label the detail directly/curved whenever possible; the detail must reduce clutter rather than create a second crowded map.

Populate required `new_design_visual_review` on the builder project. The deterministic validator checks that this visual review is present and fail-closed; the human/model reviewer must still inspect actual-size and 2x/4x screenshots and make the visual judgment.

## Short-road / callout regression override — 2026-09-11 R28 rejection

The user's R28 rejection supersedes any earlier model-generated visual pass for territories 256–260. Apply `references/new-designed-visual-standard.md` as a hard override whenever a street is short, a cul-de-sac/stub/tiny loop is present, a callout is used, or an enlarged detail is introduced.

A short street or cul-de-sac must **not** receive a loose/direct floating label merely because the text technically fits nearby. Direct/curved placement is allowed only when the usable stem/arc (excluding bulb/junction/crowded endpoints) can carry the complete rendered name plus 15 px breathing room at both ends while maintaining the normal 2–15 px street gap. Otherwise use the attached bent leader/arrow system and target the street stem rather than the bulb.

Before release, machine-check and visually inspect every leader for tail attachment, glyph/word crossings, unrelated-road crossings, target correctness, and neighborhood clutter. Zero bounding-box collisions alone is not a pass. Enlarged details reapply the same short-road/callout rules; every detail label must bind to the exact road, sit professionally within the panel, and improve—not duplicate—clutter. R19 and R28 are both negative regression fixtures.
The exact-final-PDF report must enumerate every short street/cul-de-sac in `short_street_decisions`, reconcile `short_street_count`, and reconcile `leader_count` with `leaders_reviewed_count`. A direct exception requires measured usable run >= label ink + 30 px and >=15 px end breathing room. A callout requires verified stem targeting. Missing inventory/count reconciliation is a hard visual failure.


## R42 annotated measurement and per-part score override — 2026-09-11

R42 territories 256–260 are now user-rejected negative regression fixtures. Before building or releasing another current-format card, apply `references/new-designed-visual-standard.md` including the canonical exact-final-PDF 1×/72-dpi measurement standard.

The builder must produce a complete label/branch/map-balance measurement record, not just collision counts. Every navigational label must have treatment and spacing evidence; every worked branch/stub/cul-de-sac must have explicit label ownership; large irrelevant context/dead space must be cropped/rebalanced unless required and justified. Enlarged details reapply the same label measurements.

Release requires every category **and every applicable visual part** to score strictly greater than 9.0 unrounded; an exact 9.0 fails. The release score is the lowest applicable score; weighted averages are diagnostic only and never authorize PASS. Target 10/10 in every part.

## R44 Canonical New Designed Card Family Contract — 2026-09-12 — HARD OVERRIDE

Before building, relaying out, or releasing any current-format territory card, read and apply `references/New-Designed-Card-Family-Contract.md` **before** choosing a page composition. This contract is the canonical shell/style authority and supersedes any older instruction that could be read as allowing a visually different outer card structure.

### Required builder behavior

- Use the fixed 768.0 × 480.5 pt one-page shell and canonical sidebar/map/directions panel geometry from the R45 family contract.
- Treat **A33 and 60AB** as the primary released shell references. Use 330 for approved split/detail behavior. Territory 254 may inform a dense-label/detail decision only; **never copy 254's older outer shell** into a new card.
- Choose one allowed internal map-layout mode: `full_map`, `full_plus_detail`, `split_detail`, or `site_building_assignment`. No improvised fifth layout without explicit user approval.
- Keep the final map a clean schematic field map. Consumer-map screenshots, map tiles, browser/navigation UI, screenshot crop boxes and user selection rectangles never become the rendered map style.
- A source screenshot/box showing "workable area is between the box" is boundary evidence, **not a drawable box boundary**. Use actual cross streets/source work linework/verified assignment edges.
- Preserve accepted source geography and work colors while normalizing only the card shell/presentation.
- Use the canonical sidebar palette, hierarchy, swatch positions, directions panel and label grammar.
- Run `scripts/validate_new_designed_family.py` on the exact final PDF before the critic. A failure is a hard release blocker.

Add required `card_family_review` to PROJECT/release evidence with all boolean fields from section 9 of the family contract plus `layout_mode`, `shell_validator_report`, `shell_validator_sha256`, `reference_card_hashes`, and actual-size side-by-side evidence.

A card that does not look like the same New Designed family at actual size must be repaired even if all geography, collision, PDF-size and text-extraction tests pass. `family_resemblance_passed` may not be inferred from component booleans alone.



## R45 Label placement decision tree — 2026-09-12 — HARD OVERRIDE

For every current-format card, apply the canonical family's `7A Mandatory label-placement decision tree` to **every navigational label** before release. The shorthand is:

**rest beside/follow the assigned road -> bend with the road -> move along the same road to cleaner space -> nearby attached-arrow callout -> dedicated detail.**

Do not treat this as optional style advice. Build and save `label_placement_decision_review` for the exact final PDF, enumerating every label and proving the selected treatment. Specifically:

- Direct labels must visibly rest beside and align with their road, without touching it or avoidably overhanging the usable run.
- Curved labels must bend with the road and remain consistently close along the whole word.
- If a location is cluttered, move the label along the same assigned street or to its opposite side before using an arrow.
- If no same-road placement fits cleanly, place the label in the nearest practical uncluttered whitespace and attach one clean arrow to the exact street stem.
- Do not use a distant arrow when closer clean space exists. Do not shrink type or create a numbered key instead.
- If a nearby callout system would still be crowded/tacky, use an approved dedicated detail and restart the same decision hierarchy inside it.

Before critic dispatch, run `scripts/validate_label_placement_contract.py REVIEW.json`. Any evidence failure is a builder release blocker. A validator PASS does not override the visual critic.


## R46 Internal reviewer parity and candidate freeze — HARD OVERRIDE

Before every review round, freeze the candidate PDF/hash. The mandatory internal
reviewer switches to critic-only mode, does not edit while scoring, generates and
inspects fresh actual-size, 2x, overlapping 4x and targeted evidence, does not use
the builder's claimed score as evidence, and applies the complete Territory Card
Critic rubric without omissions. A repair ends that review as FIX_REQUIRED first;
then builder mode performs the repair and a new hash gets a fresh full review.

Require `reviewer_parity_review` and run
`scripts/validate_internal_reviewer_parity.py REVIEW.json`. Any changed PDF invalidates
prior reviews. Re-review the exact saved/delivered PDF after optimization/upload.

## R47 Locked template/style-token layer - 2026-09-12 - HARD OVERRIDE
For every **new card, old-card conversion, or full current-format rebuild**, read `references/Locked-Template-Style-Token-Contract.md` and `references/R48-Canonical-Style-Tokens.json` before rendering.

The builder must not reconstruct the New Designed shell by eye or copy a convenient previous card. Create the new-output shell with `scripts/render_locked_template.py`, then add the verified map/label layers without changing the locked shell. Preserve the exact active R48 token provenance through the final saved PDF.

Mandatory pre-critic gates for new/rebuilt output:
1. `scripts/validate_style_token_layer.py FINAL.pdf` PASS;
2. existing `scripts/validate_new_designed_family.py FINAL.pdf` PASS;
3. exact final PDF uses only an allowed layout mode and locality/ID variant;
4. `style_token_review` records token SHA-256, renderer SHA-256, template asset SHA-256, layout mode, locality variant, final artifact SHA-256, and both validator reports/hashes.

The only automatic shell variants are the locked one-line/two-line locality variants and the tokenized territory-ID fit rule. Long IDs use DejaVu Sans Condensed Bold and may decrease only enough to fit the locked ID box, never below 28 pt. Do not widen the sidebar, wrap the ID, or alter map/directions panel geometry.

For a bounded edit to an already approved exact card, preserve the approved base and correction-mask rules rather than forcing a cosmetic R48 rebase. This grandfathering applies only to bounded revisions; it may not be used to build a new card or avoid R48 on a full rebuild.

Before a missing-card production batch resumes, run `scripts/validate_r48_test_scope.py`; the R48 corrected regression fixtures are layout-only and never establish geography/work-rule approval.


## R48 Canonical territory identity / filename normalization — 2026-09-12 — HARD OVERRIDE
Read `references/Territory-Identity-Naming-Contract.md` before intake identity is placed on a card. Master-map labels (`R-263-A`, `T-247-N`, etc.) are source aliases only and must be stored as `source_master_label`; never render them as the card ID or copy them into a release filename.

Every production project must have a verified `card_identity` with `base_number`, `card_class` (``, `A`, `T`, `TA`), optional lowercase `suffix`, derived `display_id`, and derived `canonical_filename`. Residential/default uses **no R**. Visible grammar is `class + number + suffix`; filename grammar is `Territory - NNN + class + suffix + .pdf`. Examples: `A263a` -> `Territory - 263Aa.pdf`; `TA263b` -> `Territory - 263TAb.pdf`; `263a` -> `Territory - 263a.pdf`.

Do not infer a production identity solely from a BIG Map prefix/suffix. Resolve conversions/reclassifications and duplicate-number conflicts first. Run `scripts/validate_territory_identity.py IDENTITY.json --actual-filename \"FINAL.pdf\"` before release. The R48 renderer independently enforces the same grammar and rejects noncanonical production filenames.


### R48 required identity review record
Before critic dispatch, populate the exact-artifact `territory_identity_review` from `Territory-Identity-Naming-Contract.md`. Bind it to the candidate PDF SHA-256 and include the complete `card_identity` object, derived-ID/filename matches, visible/extracted/metadata identity checks, source-alias non-rendering, actual filename match, zero stale hidden identities, and both validator results. Rebuild/rename first when any field fails; do not ask the critic to waive identity.



## R49 Source-truth + pre-critic gate — 2026-09-12 — HARD OVERRIDE
Before drawing or materially redrawing geography, read `Territory-Source-Truth-Preflight-Contract.md`. Do not allow a reconstructed card, prior critic report, or validator output to become its own geography evidence. Lock assignment/boundary truth from the current master/approved source and independently verify current street topology from raw current mapping evidence. Trace every named/colored road endpoint-to-endpoint; verify intersections, terminations, cul-de-sac/dead-end/through status, and every branch that can affect coverage. Invented connections, unresolved omissions, screenshot-box boundaries, or unresolved source conflicts block rendering/critic dispatch.

After rendering and **before formal critic dispatch**, run the quick visual preflight on the exact candidate at actual size plus 2x/4x map crops. For a newly redrawn residential/neighborhood map, place it side-by-side with the exact saved Territory 273 as the mandatory map-drawing comparator while retaining A33/60AB/330 as shell authorities. Compare stroke grammar, road curvature/cul-de-sacs, road-following labels, label scale/weight, map occupancy/whitespace, junctions and perimeter/context treatment. If it visibly looks like a sparse node diagram, generic schematic, or different drawing system, repair it before the critic sees it.

Populate `source_truth_preflight`; run `validate_source_truth_preflight.py REVIEW.json --pdf CANDIDATE.pdf` after the candidate is frozen. Validator PASS proves only evidence structure/artifact binding, never geography or visual family resemblance. A false/unsupported preflight is a build failure.

## R50 Label completeness/contact/clutter preflight — 2026-09-13 — HARD OVERRIDE
Read `Territory-Label-Completeness-Preflight-Contract.md` before label placement on every new card, full rebuild, material map redraw, or label repair. R50 supersedes any weaker interpretation that a valid per-label ledger is enough.

Before rendering final labels, derive a complete visible-road/name inventory from raw topology/naming sources. Every visible **named public street and named public cul-de-sac must be labeled**. A road may remain unlabeled only when current source evidence explicitly classifies it as a private drive or genuinely unnamed, and that disposition must be recorded. The builder may not omit a visible road from the ledger and thereby avoid a label requirement.

No street-name glyph may sit on, touch, straddle, or overlap any road stroke. Direct/curved labels must rest beside their road inside the existing 2–15 px band (4–10 preferred) and remain visually clean at actual size. For short streets/courts, keep direct placement only when the measured usable-run and 15-px-per-end breathing rules pass; otherwise move the label to the nearest clean whitespace and use an attached callout to the exact street stem. Do not target only a cul-de-sac bulb when a usable stem exists.

Before formal critic dispatch, freeze the candidate and populate `label_completeness_review` plus `label_contact_cluster_review`. Inspect actual size, 2x, overlapping 4x map coverage, every callout closeup, and every cluster trigger. Any label pair/group closer than 12 px at 1x triggers explicit neighborhood review; 12 px is a review trigger, not an automatic clearance. If clearer same-road/nearby placement exists, repair before critic dispatch. `unlabeled_required_road_count`, all label-road contact/overlap counts, label-label overlap count, avoidable cluster count, detached/wrong callout counts, and premature-callout count must all be zero.

Run both `validate_label_completeness_preflight.py REVIEW.json --pdf CANDIDATE.pdf` and the strengthened `validate_label_placement_contract.py REVIEW.json`. Script PASS proves evidence structure only; it never overrides visible contact/clutter.

For residential/neighborhood maps, exact saved Territory 273 is the mandatory **label-system comparator** as well as the R49 map-drawing comparator. Match its off-road road-following labels, short-street callout discipline, whitespace, and cluster separation.

Image-generation/raster concepts are planning drafts only. Never send an image-generation output or raster-only concept to the critic as a field/release candidate. Rebuild the accepted concept as a measurable exact PDF with deterministic/native text or equivalent measurable label geometry first.



## R51 Measured label baseline + PDF-only release — 2026-09-13 — HARD OVERRIDE
Read `Territory-PDF-Label-Metric-Contract.md` for every territory-card creation/rebuild/update. The final user deliverable is the canonical PDF; image-generation/raster outputs are preview/reference evidence only and must never be delivered as the completed territory card.

Before critic dispatch, establish a same-card label-gap baseline from at least three clearly successful ordinary direct/curved labels measured on the exact PDF at 1x/72 dpi. Use the median gap and a default ±3 px consistency tolerance to catch visibly floating outliers that still fall inside the broad 2–15 px hard band. Do not include the disputed/outlier label in its own reference set. Record `label_metric_review` and run `validate_pdf_label_metrics.py`.

Every named-public road inventory record now carries `required_label_count`. Use more than one label when navigation genuinely requires separate readable runs/entrances. Each repeated label must have a distinct `navigation_role` and independently pass contact, gap, clutter and road-following checks. Preserve labels the user has explicitly approved unless a required fix makes local movement unavoidable.

## R52 Segment-role binding and whole-label continuity — 2026-09-13 — HARD OVERRIDE
Read `Territory-Segment-Role-Whole-Label-Contract.md` before any label/repeat/callout work. Lock each label's navigation role and exact physical segment before positioning it. A same-named loop is not an acceptable substitute for an entrance stem; preserve correct repeats. Apply the existing placement order within the intended run. Inspect and measure first word, middle, final word and suffix against the local street. Use actual PDF font widths/verified shaping; zero collision is not enough to establish readable spacing. Require `label_navigation_review`, `critic_label_navigation_review` and `validate_label_navigation_contract.py` in addition to all inherited gates. The approved Territory 269 two-label PDF is a component-only reference; do not recertify geography or change its approved bytes.