# Canonical New Designed Territory Card Family Contract — R45 — 2026-09-12

## Authority and purpose

This contract is a **hard release gate** for every territory card intended to be part of Kaleb's current **New Designed Territory Cards** collection. It governs the card shell, page structure, map presentation grammar, label grammar, directions layout, and family resemblance. Geography/source authority remains governed by the builder/critic source and coverage contracts; this document controls **how verified geography is presented**.

A card may not pass merely because it is readable, collision-free, under 300 KB, or geographically correct. If it does not visibly belong to the same New Designed card family at actual output size, release fails.

## Canonical positive references

Use the exact saved artifacts below as the primary shell/style authority:

1. **Territory - 033A.pdf** — current released A33 shell reference. SHA-256 `6abf8c1ac0412c7c2c96523f4200213744d0e9466fea7a38c42b13e28133e529`.
2. **Territory - 060Ab.pdf** — current released complex/site-layout reference. SHA-256 `9a86e3d70f6ec05d1755703ead2864b018128d365ebcbc7f75d386952661164c`.
3. **Territory-330-Final.pdf** — approved split/detail-layout reference inside the same shell. SHA-256 `84ae5c991404aaad01aad2647b795d46d82b1fff5a3f2c4f9b22630c134b1193`.

**Territory 254 is NOT a shell authority.** It may be used only as a historical/dense-label placement example where explicitly cited. Its older outer framing/sidebar geometry must never be copied to a new card when doing so conflicts with this contract.

Negative fixtures remain R19, R28, and annotated R42 for 255a–260.

## 1. Fixed page and shell geometry

All New Designed cards use one landscape front page only.

At PDF coordinates / 1x 72 dpi:

- Page size: **768.0 × 480.5 pt**. Tolerance: ±0.5 pt.
- Outer visual margin: approximately **9 pt**.
- Left sidebar: bounding box **x=9, y=9, x2=155, y2=472 pt**, tolerance ±2 pt.
- Sidebar nominal width: **146 pt**.
- Main map-panel shell: **x=164, y=9, x2=759, y2=375 pt**, tolerance ±2 pt.
- Directions-panel shell: **x=164, y=385, x2=759, y2=472 pt**, tolerance ±2 pt.
- Map-to-directions vertical gutter: approximately **10 pt**, tolerance 8–12 pt.
- Main content left edge remains **x≈164 pt**; do not widen/narrow the sidebar to solve map density.

The shell may not be replaced by a screenshot frame, a full-page border, an arbitrary dashboard, a portrait layout, or a differently proportioned card.

### Shell colors and borders

- Sidebar: dark blue-black family centered on **#10212B** (small antialias/render variation allowed).
- Map and directions panels: white.
- Panel border: subtle cool gray-blue, approximately **#D6E0E4**, thin stroke around 0.6–0.8 pt.
- Corners: softly rounded, matching A33/60AB/330; do not use sharp spreadsheet boxes or decorative cards.
- Sidebar legend swatches are exactly:
  - yellow **#FFDC18**
  - green **#51C72B**
  - red **#FF1435**
- Sidebar swatches: **20 × 20 pt** at approximately x=28–48, with rows centered around y=208, 252, and 296 pt.

## 2. Fixed sidebar hierarchy

The sidebar is not optional and may not be redesigned per territory.

Required order:

1. `TERRITORY`
2. large visible territory ID
3. locality/city/township
4. divider
5. `LEGEND`
6. yellow `Work Inside Only`
7. green `Work Both Sides`
8. red `Do Not Work`
9. lower divider
10. calendar icon
11. `UPDATED`
12. date

Canonical typography at 1x:

- `TERRITORY`: ~12 pt regular, white.
- Territory ID: ~40 pt bold, white. Longer IDs may reduce only as much as required to fit without changing hierarchy; target 36–40 pt.
- Locality: ~12–12.5 pt regular, white; two lines permitted when genuinely required.
- `LEGEND`: ~11 pt bold, white.
- Legend labels: ~9.5 pt regular, white.
- `UPDATED`: ~10 pt bold, white.
- Date: ~11 pt regular, white.

Street names never use the oversized/bold sidebar style.

## 3. Directions panel is a fixed structural component

- The directions panel always occupies the canonical lower panel shell.
- Use the approved vehicle/location icon treatment at the left.
- Preferred standard: directions text begins to the right of the icon at approximately x=227 pt. Released compact/detail cards may begin around x=185 pt when the icon/inner composition requires it, but the text must remain inside the canonical directions panel and preserve the same hierarchy.
- Preferred standard: `Directions:` uses ~9 pt bold dark text and the body ~9 pt regular. A released split/detail reference may use a compact 8–9 pt combined line; do not use that exception to shrink an ordinary card unnecessarily.
- Keep the panel concise enough to preserve the same hierarchy and whitespace as A33/60AB/330.
- Do not move directions into the sidebar, overlay them on the map, or replace them with a detached note box.
- Do not add audit/source-credit text to the directions panel.

## 4. Allowed map-layout modes inside the fixed shell

Choose exactly one and record it. The **outer shell never changes**.

### A. Full-map mode
Use for ordinary low/medium-density territories. One dominant map fills the main panel with balanced margins.

### B. Full-map + dedicated detail mode
Use only when density genuinely requires enlargement. Preserve a complete locator/full map and use dedicated whitespace for the detail. Do not overlay detail boxes on important map content.

### C. Deliberate split-detail mode
Use the 330 principle: a full-map locator plus one or more clean detail regions separated by intentional dividers inside the same main panel. Keep titles small and functional (`FULL MAP`, `NORTH DETAIL`, etc.).

### D. Site/building-assignment mode
For apartments/complexes/campuses where buildings rather than ordinary road sides are the assignment. Keep the same shell. Inside the map panel, use verified site geometry, muted unassigned context, clearly distinguished assigned buildings, and a small access/approach view only when needed. This is not permission to create a dashboard or unrelated infographics.

No fifth improvised mode is permitted without explicit user approval.

## 5. Map style and map-format grammar

The approved family is a **clean schematic field map**, not a screenshot of a consumer map.

- Render only verified roads, assignment geometry, required site/building shapes, and minimum navigation context.
- Do not use commercial basemap tiles, satellite imagery, photorealistic backgrounds, navigation UI, browser chrome, screenshot boxes, selection rectangles, crop frames, or arbitrary map-service styling in the final card.
- A screenshot rectangle or user-drawn box used to indicate the approximate workable area is **evidence only** unless the user explicitly states that the box itself is the legal/work boundary. Do not render that box as the territory boundary. Derive the work boundary from actual streets, work rules, supplied work-colored linework, parcels, or verified assignment evidence.
- Preserve accepted supplied work-colored geometry when in `preserve_supplied_map` mode, but compose it inside this shell.
- Keep the territory/workable geometry visually primary; irrelevant context must not dominate the panel.
- Required map-balance measurements from the visual standard still apply.
- Keep north-up when practical. If source orientation must differ, include clear orientation evidence; never rotate merely to make labels fit.

## 6. Work-color grammar

- Green = work both sides / assigned interior.
- Yellow = work territory-facing/inside side only.
- Red = do not work / excluded / access-only as explicitly authorized.
- Neutral/muted context must never look workable.
- Do not add a decorative black box boundary around the territory when actual cross streets/colored assignment geometry define the boundary.
- Do not recolor accepted source work-status linework just to make it aesthetically uniform.

## 7. Street-label family grammar

Street labels are part of the map, not floating annotations. **A street name should visually rest beside the street it names, follow that street's direction/curve, and use the street itself as its primary visual anchor.** A nearby word with no clear road attachment is not an acceptable street label.

### 7A. Mandatory label-placement decision tree — apply in this exact order

For **every navigational street label**, the builder and critic must apply and record this decision tree. Do not skip directly to a callout because it is easier to place.

1. **Direct road-following placement first.**
   - If the full name fits cleanly beside a usable straight road run, place it immediately beside that assigned road.
   - Keep the label visually close enough to "rest against" the road without touching it: use the visual-standard 2–15 pt/px hard road gap, preferably 4–10.
   - Align the text with the local road direction. The label must not look horizontal/vertical merely for convenience when the road clearly runs another direction.
   - The full word must fit inside the usable labeling run. Do not let the name visibly overhang the usable road segment into a junction, cul-de-sac bulb, adjacent street, panel edge, or empty area in a way that looks detached or tacky.
   - For ordinary direct labels, preserve visible end breathing room wherever the source geometry permits; target at least 10 pt/px at each end and do not accept less than 6 without a documented geometry constraint. Short-street direct exceptions retain the stricter 15-at-each-end / label+30 rule from the visual standard.

2. **Curved road-following placement when the street bends.**
   - If the street bends enough that a straight label would stop following it, curve/bend the entire label with the street.
   - Keep the label consistently close to the road for its whole word. One end may not hug the road while the other lifts away.
   - Never distort individual letters, twist suffixes, or create broken-looking words merely to follow a curve.

3. **Relocate along the same street before using any arrow.**
   - If the first direct/curved location is cramped, overhangs, sits in a junction, conflicts with another label, or creates a tacky cluster, inspect farther along **that same assigned street**, including the opposite side of the road where appropriate.
   - Choose the clearest same-road segment that preserves the direct/curved road relationship and normal type size.
   - Do not shrink the type, detach the name from its road, or add a leader while a clean same-road location exists.

4. **Nearby callout with arrow only when the street itself cannot carry the name cleanly.**
   - When no clean direct/curved same-road placement exists, move the label into the **nearest practical uncluttered whitespace** and use one clean attached leader/arrow to the exact assigned street.
   - The callout block should stay near its street; do not send a label across the map simply to find empty space. Target leader length is <=80 pt/px at 1x. Longer routing requires proof that no closer clean location exists; >110 is a hard failure unless the user explicitly approves that exact routing.
   - The leader tail visibly attaches to the label block (0–2 pt/px), never floats nearby.
   - The arrowhead lands on the exact named street stem/centerline. For cul-de-sacs, target the usable stem rather than only the bulb whenever a stem exists.
   - The leader may not cross/touch another word, leader, unrelated road, boundary, or important map feature except at the named target.
   - Neighboring callouts must form a clean row/column/fan-out with obvious ownership, not a knot.

5. **Use a dedicated enlarged detail when a clean nearby callout system still cannot be achieved.**
   - Do not create distant arrows, micro-text, a numbered street key, or an overpacked callout cluster to avoid using a detail.
   - Inside the detail, restart this same decision tree from step 1. Enlargement does not waive label-road attachment rules.

### 7B. Label-placement vetoes

Any of the following blocks release regardless of collision metrics:

- label floating in open space without a leader when it does not visibly belong to its street;
- straight label on a clearly curving street when a curved placement is feasible;
- label overhanging its usable road run into a junction/bulb/neighboring street or empty area in an avoidably tacky way;
- label sitting on, straddling, or touching its road stroke;
- label placed in a cluttered pocket when clearer same-road whitespace exists;
- arrow/callout used before same-road direct/curved alternatives were exhausted;
- distant callout when nearer clean whitespace exists;
- detached arrow tail, wrong road target, bulb-only target when a usable stem exists, or leader crossing text/unrelated roads;
- label type shrunk below the family floor merely to force it onto the map.

### 7C. Required label decision ledger

Every exact-final-PDF builder record and critic report must include `label_placement_decision_review` bound to the artifact SHA-256. It must enumerate **every navigational label** and record, at minimum:

- street/feature identity and verified road binding;
- treatment: `direct`, `curved`, `same_road_relocated_direct`, `same_road_relocated_curved`, `callout`, `detail_direct`, `detail_curved`, `detail_callout`, or approved source connector;
- label font size and regular/bold status;
- assigned-road gap and alignment/curve evidence;
- usable-run/end-breathing or `overhang_avoided` evidence;
- junction/bulb and neighboring-label clearance;
- whether same-road alternatives were assessed;
- for callouts: proof direct/curved same-road options were exhausted, nearest-practical whitespace was used, leader length, tail attachment, route clearances, target street/stem, and screenshot evidence;
- result and any documented geometry exception.

Count-only assertions are not enough. `label_count` must equal the number of decision records, `callout_count` must equal callout decisions, and every callout leader must be independently reviewed. Run `scripts/validate_label_placement_contract.py REVIEW.json` before release. Script PASS validates the evidence structure only; the critic must still visually judge the exact PDF.

- Default street label: regular-weight sans-serif, dark gray/blue-black near **#27343C**.
- Preferred normal-map size: **9 pt** at 1x.
- Dense/detail maps may use **8 pt** only when the exact-final-PDF readability/spacing gates pass. Do not shrink below 8 pt to solve density.
- Property/site names may use ~10–11 pt regular when clear interior whitespace exists.
- Never bold ordinary street names.
- Direct labels run parallel to the road; curved labels follow the road.
- Use the exact placement hierarchy and measurements from `New-Designed-Visual-Regression-Standard.md`.
- Short streets/cul-de-sacs use the measured direct exception or an attached leader. No floating nearby names.
- Every navigationally distinct worked branch must have clear label ownership.
- No label may sit on a road stroke, straddle an unrelated road, crowd a junction/bulb, or be pushed against panel edges/dividers.

## 8. Leader/callout family grammar

- Callouts are exceptions, not the default map language.
- Tail visibly attaches to label block within 0–2 px.
- One clean leader, few bends, one filled triangular head, one exact target.
- Target the named road stem, not merely the bulb when a stem exists.
- No leader may cross/touch text or an unrelated road.
- Neighboring callouts must form an intentional clean column/row/fan, not a knot.
- A card that becomes callout-heavy compared with the approved family fails family resemblance even if individual callouts are collision-free.

## 9. Family resemblance is a hard binary gate plus scored part

Before release, compare the exact final PDF at actual size against **A33 and 60AB**. Add **330** when a detail/split layout is used. Add another released similar-density card when available.

The reviewer must answer all of these `true`:

- `canonical_page_geometry_passed`
- `canonical_sidebar_geometry_passed`
- `canonical_map_panel_geometry_passed`
- `canonical_directions_panel_geometry_passed`
- `canonical_sidebar_hierarchy_passed`
- `canonical_legend_palette_and_swatch_passed`
- `canonical_typographic_hierarchy_passed`
- `allowed_map_layout_mode_passed`
- `schematic_map_style_passed`
- `screenshot_box_not_used_as_boundary`
- `street_label_family_passed`
- `label_decision_tree_passed`
- `label_overhang_and_attachment_passed`
- `same_road_before_callout_passed`
- `nearby_callout_fallback_passed`
- `directions_family_passed`
- `family_resemblance_passed`

Any `false`, missing, or unverified value blocks release and caps `template`, `family_resemblance`, and overall release at **8.0** until repaired.

## 10. Deterministic shell validation

Run `scripts/validate_new_designed_family.py FINAL.pdf` on the **exact final PDF** and `scripts/validate_label_placement_contract.py REVIEW.json` on the artifact-bound review before critic scoring.

The script is allowed to prove measurable shell facts only: page size, core panel locations, sidebar palette/swatch rows, required sidebar text hierarchy, basic font-size bands, directions location, one-page/export basics. It cannot prove that a map looks professional or that labels belong to the right roads.

A deterministic shell failure blocks release. A shell-script PASS does not waive human/model actual-size comparison.

## 11. Grandfathering and revisions

Previously released cards are not retroactively invalidated solely because an older approved card used a slightly different internal map treatment. However:

- every **new card, rebuild, old-card conversion, or materially relaid-out card** must use this R45 shell;
- every card touched for a substantial visual rebuild should be brought into the canonical shell unless the user's request is a narrowly bounded correction to an already approved card;
- source geometry/work rules remain protected even when the shell is normalized;
- a special older reference may inform one component but cannot override the canonical shell.

## 12. No aesthetic improvisation

Do not create a new visual language because it seems cleaner, more modern, more spacious, more dashboard-like, or easier to code. The collection must look deliberately standardized. Variation is allowed **inside the map panel only where the territory itself requires it**, and only through the approved map-layout modes above.


## 13. Active score floor

For current territory-card releases, every required category and applicable visual part must score **strictly greater than 9.0**, unrounded, with 10/10 the target. An exact 9.0 fails. This R44 rule supersedes older inclusive-9.0 wording while preserving any explicitly higher project threshold.


## R46 Review enforcement parity

This family contract is automatically loaded for territory artifact work in regular
Chat and Work through `Territory-Automatic-Execution-Contract.md`. The mandatory
internal reviewer uses the same family checks and vetoes as the Territory Card Critic.
It may not approve family resemblance from builder assertions, component booleans, or
a shell-validator PASS alone. It must inspect the exact PDF and pinned positive
references. A changed PDF hash requires fresh review.

## R47 locked template/style-token authority - 2026-09-12 - SUPERSEDING NEW-OUTPUT AUTHORITY
The canonical family shell is now implemented as a reusable locked token layer. Read `Locked-Template-Style-Token-Contract.md` and the active `R48-Canonical-Style-Tokens.json`.

New cards, old-card conversions and full rebuilds must originate from `render_locked_template.py` and retain the exact token provenance through the final artifact. R48 preserves the R47-validated one-line and two-line locality variants and a territory-ID fit variant (DejaVu Sans Condensed Bold, 40 pt when possible, >=28 pt, fixed ID box). These are controlled variants, not permission for arbitrary sidebar edits.

A33/60AB remain shell authority; 330 remains split-detail authority; dense residential 345 is a compatibility stress reference. Current 288 and current 262A are retained scaled-shell negatives: their 576 x 360.375 page geometry does not define the family.


## R48 canonical identity/naming integration — 2026-09-12
R48 adds `Territory-Identity-Naming-Contract.md` as a hard prerequisite. Source/master labels remain source aliases only. New/rebuilt cards must use a verified `card_identity`, the derived congregation-facing display ID, and the exact derived canonical filename. The locked renderer and internal/critic release path fail closed on identity mismatch.


## R49 residential map-drawing comparator + pre-critic veto — 2026-09-12
For newly redrawn residential/neighborhood maps, exact saved Territory 273 is now a mandatory **map-drawing comparator** (not a replacement for A33/60AB/330 shell authority). Before formal critic dispatch and again during critic review, inspect side-by-side map crops for stroke character, natural road geometry, cul-de-sac/junction grammar, road-following labels, label scale/weight, occupancy/whitespace and perimeter/context treatment.

A candidate that shares the locked shell but visibly uses a different map-drawing language fails family resemblance. Sparse node diagrams, simplified topology, oversized/free-floating labels, generic schematic curves, or unnatural empty-space balance are hard family failures even if all token, collision and PDF validators pass. Territory 269 R48 is a negative regression example and may not be used as a positive family fixture.

## R50 Label completeness and neighborhood composition — 2026-09-13 — HARD FAMILY GATE
The family label grammar is now completeness-driven, not ledger-driven. Every visible named public street and named public cul-de-sac must be labeled. Private/unnamed omissions require source evidence. Missing a road from the builder ledger does not waive its label.

No label may sit on or touch road linework. Long/normal streets use direct/curved road-following labels offset beside the road. Short streets/courts use direct placement only when the short-street fit/breathing rule passes; otherwise use the nearest clean attached-arrow callout targeting the street stem. Labels may never be forced onto a short road merely to avoid a callout.

Composition is judged by neighborhoods. Labels that individually clear their roads still fail when they form an avoidable cluster. Every <12 px local label-gap trigger requires explicit comparison of clearer same-road/opposite-side/nearby-callout alternatives. Territory 273 is the mandatory residential/neighborhood label-system comparator.

Any missing required label, label-road touch/overlap, avoidable label cluster, unsupported unlabeled road, malformed callout, or raster-only/generated final map blocks family resemblance and caps the applicable label/family/overall score at 8.0 until repaired.



## R51 Measured placement consistency and navigation repeats — 2026-09-13
R50 contact/clutter rules remain mandatory. In addition, ordinary labels on the same card should exhibit a coherent visual road offset. Establish a median assigned-road gap from at least three clearly successful labels on the exact 1x PDF; labels designated `match_reference_gap:true` must remain within ±3 px of that median absent an independently accepted geometry exception. This is a consistency gate, not permission to violate the 2–15 px hard range or 4–10 px preferred band.

Repeat a street name on a second materially separate run when needed for field navigation; each placement must be useful, non-cluttering, and independently road-bound. A long/turning road with a remote entrance may legitimately carry two labels. The final released artifact is the PDF; raster previews are never the card itself.

## R52 Meaningful road association through the final suffix
In addition to family appearance and R51 gaps/repeats, require exact navigation-role/segment binding and complete local contour through the ending suffix under `Territory-Segment-Role-Whole-Label-Contract.md`. A wrong same-street target or visually cramped curved word is not family-compliant simply because it is collision-free. Territory 269's approved two-label correction is a component-only example, not a new outer-shell or whole-geography authority.