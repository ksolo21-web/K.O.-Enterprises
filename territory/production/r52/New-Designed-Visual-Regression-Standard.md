# New Designed Territory Card Visual Regression Standard — 2026-09-11

## Purpose

This is a fail-closed visual standard for Kaleb's current New Designed Territory Cards. It was added after the Territory 255a–260 R19→R28 review showed that a card can be collision-free and technically readable yet still look materially worse than the approved collection. Apply it to every new card, old-card conversion, relayout, label repair, and final critic review that is intended to match the current New Designed format.

The visual authority is the user's actual approved **New Designed Territory Cards** collection, not a generic map-design preference. Retrieve the current saved reference cards when working in a new chat. Territory 254 is a strong enlarged-detail reference and Territory 330 is a strong split/full-detail hierarchy reference. They are regression examples, not universal geometry templates.

## Required placement hierarchy

Use this order and prove it was considered:

1. **Direct label along the assigned street** when the full name fits cleanly.
2. **Curved label following the assigned road** when the road bends. Keep the full word close and visually parallel to the road.
3. **Move the label to clearer same-road whitespace** before adding a leader. Check farther along the same road and the opposite side of the road.
4. **Use one clean bent/gently routed leader only when direct/curved placement genuinely cannot fit.** The bent route is preferred over a long straight leader when it avoids clutter or unrelated roads.
5. **Use a professional enlarged detail in dedicated whitespace when local density cannot be solved cleanly.** The enlarged-detail system is preferred over inventing a numbered street-key workaround.

A collision-free layout does **not** satisfy this hierarchy by itself.

## Short streets and cul-de-sacs — callout-first rule

The approved card family does **not** treat a short stem or cul-de-sac like a normal long street merely because a small label can be squeezed beside it. This was a missed defect in R28 and is now a hard regression gate.

- For every short street, stub, cul-de-sac, or tiny loop, measure the usable stem/arc available for labeling after excluding the bulb, junction, and crowded endpoints.
- A direct/curved label is allowed only when the usable run is at least the rendered full-label ink length plus **30 px total breathing room** (15 px at each end), the label can remain 2–15 px from the road, and the full word remains visually associated with that one road without crowding a junction, bulb, boundary, or unrelated label.
- Otherwise use the approved **attached bent leader/arrow system**. Do not float the street name near the cul-de-sac without a leader.
- Cul-de-sac callouts must target the **street stem** when a stem exists; do not aim only at the circular bulb.
- Moving a short-road label into open whitespace without adding the required leader is still a failure.
- The same rule applies inside enlarged details. Enlargement does not turn a short road into a long-road direct-label exception unless the measured enlarged usable run actually satisfies the rule.

Record every short-road decision in the review evidence. Any unreviewed short road or unsupported direct-label exception blocks a passing (>9.0) visual score.


## Required short-street and leader inventory

A reviewer may not satisfy the short-street gate with a count-only assertion. The exact-final-PDF review must enumerate every visually short street/stub/cul-de-sac considered under this rule. Record `short_street_count` and a matching `short_street_decisions` array. Each record must name the street, state `treatment` as `callout` or `direct_measured`, identify the screenshot/crop evidence, and record the relevant measurements.

- For `direct_measured`, record `usable_run_px`, `label_ink_px`, and `end_breathing_room_px`; require `usable_run_px >= label_ink_px + 30` and `end_breathing_room_px >= 15`.
- For `callout`, record `target_stem_verified: true` and the leader/target evidence.
- The reviewer must also record `leader_count` and `leaders_reviewed_count`; they must be equal. `callout_geometry_review_completed` and `unrelated_road_crossing_review_completed` must both be true.
- A missing street decision, count mismatch, unsupported direct exception, or unreviewed leader is a hard failure and caps labels/overall visual quality at 8.

## Numbered-key density workaround — prohibited

Do not create a `STREET KEY`, numbered legend, numbered bubbles, or number→name list merely to make dense street labels fit. This treatment is visually inconsistent with the approved New Designed cards and is a hard regression.

Exception: preserve an explicitly approved **source** numbered-key/connector convention when that convention is itself part of the accepted source card (for example, legacy A2-style reference connectors). That is source preservation, not permission to invent a numbered density key on another card. Record the approved source identity and connector review.

An unauthorized numbered density key blocks release and caps the visual/labels assessment at 8/10.

## Leader attachment and routing

Every callout must look intentionally connected from label to street.

- The leader tail must begin at the label block edge or within **0–2 px** of the label block. A visible tail-to-label gap greater than 2 px is a floating/disconnected leader and fails.
- The leader may touch the callout block edge but must not cut through glyph ink.
- Prefer a clean elbow/curved bend when it improves routing; avoid arbitrary zig-zags.
- Use one leader, one filled triangular head, and one unambiguous target.
- End on the named street's stem/centerline segment, not a nearby road, red/context feature, or only a cul-de-sac bulb when a stem is available.
- The full shaft must stay clear of unrelated labels, leaders, roads, and important map features except inside the target radius.
- **No leader segment may cross, touch, underline, or visually cut through any word/glyph**, including its own label after leaving the attachment edge. Zero geometric overlap is required, and actual-size visual inspection must confirm it does not merely graze the word.
- Do not route a leader across an unrelated street just because there is no text collision; move the label to the target side or choose a different bend.
- Review the **whole callout neighborhood**. A leader can be individually collision-free yet still be unprofessional when it creates a knot of arrows/labels in one pocket. Arrange neighboring callouts as a clean column, row, or fan-out pattern with obvious ownership.
- A wrong target, detached tail, malformed head, word-crossing leader, unrelated-road crossing, or leader that visually belongs to a different label is a hard failure.

## Clutter and whitespace veto

Review whole label neighborhoods, not only individual bounding boxes.

- Inspect at actual output size and 2×/4× close-up.
- Compare label density and whitespace with at least two approved New Designed reference cards, including one with similar map density when available.
- If a cluster feels packed because several labels/callouts occupy the same small pocket while usable same-road whitespace exists elsewhere, it fails even when collision metrics are zero.
- Do not solve clutter by shrinking type, compressing spacing, adding more leaders, or turning labels into a numbered key.
- Prefer fewer callouts, clearer whitespace, and road-following labels.

Any avoidable clutter cluster blocks release. A card with avoidable clutter cannot receive 9/10 or higher in labels or overall visual review.

## Enlarged-detail system

Use an enlarged detail when the full map cannot carry the necessary labels cleanly.

- The detail must occupy **dedicated whitespace or a deliberate split-panel region**. Do not float an inset over important full-map streets, labels, or work colors.
- If space is needed, uniformly reduce/reposition the complete main map; preserve aspect ratio and all source relationships.
- Keep the main map complete enough to understand the territory and locate the detail.
- Use a concise professional locator such as `A East grid - enlarged`, `A Southwest - enlarged`, etc. The locator is for the detail area, not a numbered street legend.
- Repeat only the subset of source geometry needed for the detail and preserve the same road geometry, work status, names, and orientation.
- Apply the same short-street/cul-de-sac callout rule inside the detail; enlarged scale does not waive leader requirements.
- Every detail label must be bound to the exact road segment it names and follow that segment's orientation/curvature when direct labeling is justified. Floating text in the middle of a detail is not acceptable.
- Keep label blocks and leader bends comfortably inside the detail panel; do not crowd the panel edge, divider, locator, or adjacent label.
- Leaders inside a detail must obey the same attachment, word-crossing, unrelated-road-crossing, and stem-target rules as the full map.
- The enlarged detail must reduce clutter rather than create a second crowded area. If the detail cannot be made cleaner than the full-map treatment, reject the detail and use another layout strategy.

An enlarged detail that overlays/covers important full-map content, changes source meaning, contains misbound/floating labels, violates the short-road rule, or is itself crowded fails.

## Mandatory New Designed comparison review

Before a ≥9 visual score, the reviewer must perform a side-by-side comparison of the **exact final PDF render** against at least two approved New Designed cards. Record the reference card identities and evidence. Compare:

- whitespace and overall map balance;
- direct/curved label use versus callouts;
- leader attachment and routing;
- label cluster density;
- enlarged-detail hierarchy and dedicated space;
- typography/regular weight;
- sidebar/directions consistency;
- whether the card looks like the same card family at actual size.

A card that is technically collision-free but visibly denser, more key-driven, or more callout-heavy than the reference family must not pass 9/10.

## Required report object

Every builder release record and every critic report must include `new_design_visual_review` bound to the exact final artifact:

```json
{
  "artifact_sha256": "exact final PDF SHA-256",
  "reference_style": "new_designed_territory_cards",
  "reference_cards": ["Territory 254", "Territory 330"],
  "actual_size_review_completed": true,
  "closeup_review_completed": true,
  "same_road_alternatives_assessed": true,
  "direct_label_first_verified": true,
  "short_street_review_completed": true,
  "short_street_direct_label_exceptions": 0,
  "short_street_callout_policy_passed": true,
  "short_street_count": 2,
  "short_street_decisions": [
    {"street":"Example Ct","treatment":"callout","target_stem_verified":true,"evidence":"exact-PDF 4x crop"},
    {"street":"Example St","treatment":"direct_measured","usable_run_px":95,"label_ink_px":55,"end_breathing_room_px":20,"evidence":"exact-PDF 4x crop"}
  ],
  "leader_count": 1,
  "leaders_reviewed_count": 1,
  "callout_geometry_review_completed": true,
  "unrelated_road_crossing_review_completed": true,
  "numbered_density_key_used": false,
  "approved_source_numbered_connector_preserved": false,
  "approved_source_numbered_connector_evidence": null,
  "floating_leaders": 0,
  "detached_leaders": 0,
  "wrong_target_leaders": 0,
  "leader_word_crossings": 0,
  "leader_unrelated_road_crossings": 0,
  "unnecessary_leaders": 0,
  "max_tail_to_label_gap_px": 2,
  "avoidable_clutter_clusters": 0,
  "callout_neighborhood_clutter": 0,
  "enlarged_detail_review": {
    "used": false,
    "dedicated_whitespace": true,
    "overlays_full_map_content": false,
    "main_map_complete": true,
    "main_map_uniform_scale_or_unchanged": true,
    "locator_titles_clean": true,
    "source_geometry_status_preserved": true,
    "detail_label_binding_errors": 0,
    "detail_short_street_direct_label_violations": 0,
    "callout_rules_reapplied_in_detail": true
  },
  "family_resemblance_passed": true,
  "evidence": "Exact screenshots and side-by-side references inspected."
}
```

When no enlarged detail is used, keep its non-regression fields truthful (`overlays_full_map_content=false`, main map complete, etc.). When an approved source numbered connector is preserved, `numbered_density_key_used` still remains false because the source connector is not a newly invented density workaround; record its source evidence separately.

## Score vetoes

The reviewer must cap the overall visual score at **8.0** and keep release false if any of these are present or unverified:

- unauthorized numbered density key;
- floating/detached leader;
- wrong-target leader;
- any leader crossing/touching word glyphs or an unrelated road;
- any short street/cul-de-sac directly or loosely labeled without satisfying the measured usable-run exception;
- avoidable callout, callout-neighborhood knot, or avoidable clutter cluster;
- enlarged detail covering important full-map content;
- enlarged detail with misbound/floating labels, short-road violations, or crowded edge placement;
- crowded enlarged detail that did not improve readability;
- no side-by-side New Designed reference review;
- family resemblance failure at actual size.

Do not average these away with strong geography/export scores.

## Regression fixture: 255a–260 R19 → R28 → R42

Both **R19 and R28 are retained negative fixtures**. R19 failed because it was too dense, had visually detached leaders, and invented a numbered street-key workaround. R28 fixed some of that, but the user correctly rejected it again because the critic still passed major label-system defects: short streets/cul-de-sacs were directly/floating-labeled without the leader system, some arrow lines crossed words or created tangled neighborhoods, and the first enlarged-detail layouts had poorly bound/tacky label placement.

The post-feedback repair series R29–R42 changed strategy instead of simply moving the same labels. It converted short stems/cul-de-sacs to attached bent leaders, enforced leader-vs-word crossing checks, targeted stems rather than bulbs, rejected crowded callout neighborhoods, and rebuilt the 258/260 detail treatment. **Do not treat R28 as a positive example.** Future reviewers must be able to fail R28-class defects even when overlap metrics are zero.

Required regression assertions:

- R19: FAIL.
- R28: FAIL.
- A corrected candidate may pass only after the exact-PDF short-street inventory, leader attachment/crossing, callout-neighborhood, and enlarged-detail checks all pass.
- The user feedback that triggered this rule outranks any earlier model-generated score for R19 or R28.

The regression rule is the design principle, not a requirement that every future card literally resemble the geometry of 255a–260.

## R42 annotated rejection — 2026-09-11 — SUPERSEDES any earlier R42 visual pass

The user's five annotated R42 screenshots for territories 256–260 are now **negative regression fixtures**. R42 is not a positive visual successor and must not be used as evidence that the New Designed visual standard was satisfied. The user's annotations exposed defects that still passed the prior automated/internal review.

### What the annotations mean

- **Territory 256**
  - The large circled western area is excessive non-work/context geometry and dead whitespace that compresses the actual workable grid. This is a map-balance failure, not merely a cosmetic preference.
  - Roselawn Dr and Fairview Ave are cramped against the N Alice/yellow-edge area; their callout/label placement does not have a professional whitespace moat and the road association is visually weak.
  - The marked upper-right green branch/stub pieces do not have clear label/continuation ownership. Every navigationally distinct worked branch must be explicitly bound to a street label or documented same-name continuation.
- **Territory 257**
  - W 3rd St, Roselawn Dr, Fairview Ave, Flora Valley Ct, and Burgoyne Blvd form an overpacked callout/label cluster. Zero collisions is insufficient when the cluster has poor spacing and ambiguous visual ownership.
  - N Alice Ave, N Helen Ave, and N Castell Ave sit on or too close to their road strokes. Vertical labels must be parallel to, but visibly offset from, the road.
- **Territory 258**
  - In the enlarged panel, W 3rd St, Roselawn Dr, Fairview Ave, and N Alice Ave are not consistently bound/offset to their actual road geometry. Several labels sit on, straddle, or visually float across the red/green linework.
  - The large circled red/context area on the full map is wasted presentation space that compresses the useful Willow Grove/assigned portion.
  - The circled 1st St / S Alice Ave / S Helen Ave junction is too crowded; labels are placed too close to an intersection/other labels.
- **Territory 259**
  - The circled Carlo Ct, Brittany Ct, Hidden Ln, Springwood Ct, Deerfield Ct, Kingsview Ct, Fawn Ct, and Antler Ct callouts are a system-level failure: several labels are too close to adjacent roads/labels, some leaders visually float from the label block, and several arrow tips emphasize the bulb rather than the usable street stem. The upper callouts also form a crowded row rather than a clean column/fan-out.
- **Territory 260**
  - Black Maple Dr is crowded against the upper boundary/context line.
  - Sugar Pine Rd / Tanglewood Dr and Rochingham Dr are too close to or sitting on their road strokes; the text-to-road offset is not controlled.
  - Timberlea Dr is crowded into a red junction/context pocket.
  - In the enlarged detail, Cypress Ct and Tanglewood Ct have poor label/leader spacing and weak stem association.
  - The lower-right circled green cul-de-sac/branch has no clear label binding at all: this is a branch-completeness failure.
  - The enlarged detail itself lacks the clean measured label-to-road spacing expected from the approved New Designed family.

These annotated screenshots outrank every earlier model-generated R42 score. Future reviewers must be able to fail these exact defect classes.

## Canonical measurement coordinate system

All numeric placement thresholds below are measured against the **exact final PDF rendered at 1× / 72 dpi** with no scaling after measurement. At that reference, 1 px = 1 PDF point. A 2× review doubles every pixel threshold; a 4× review quadruples it. Record the final PDF SHA-256 and the renderer used.

Measurements are from **visible ink/stroke edges**, not text-box or SVG-object bounds, unless a field explicitly says otherwise.

## Label-placement measurement standard

### Direct and curved street labels

For every direct or curved navigational street label:

- **Assigned-road edge gap:** hard range **2–15 px**; preferred release-quality target **4–10 px**.
- **Ink overlap with assigned road:** **0 px**.
- **Ink clearance from any unrelated label:** minimum **10 px**; target **14 px**.
- **Ink clearance from an unrelated road/boundary/context stroke:** minimum **8 px**, unless the text names that exact stroke.
- **Clearance from a junction, intersection center, or cul-de-sac bulb edge:** minimum **12 px** unless the label is a measured short-road exception and the geometry proves more room is impossible.
- **Panel-edge / divider / compass / detail-title clearance:** minimum **12 px**; target **18 px**.
- **Straight-label alignment:** baseline must be within **8 degrees** of the local assigned-road tangent.
- **Curved-label consistency:** every sampled letter-to-road gap must remain inside the 2–15 px hard range and the difference between the maximum and minimum sampled gap must be **<= 6 px**.
- **Short-street direct exception:** the usable road run, excluding the bulb, junction, and crowded endpoints, must be at least `label_ink_length + 30 px`, leaving **>=15 px** breathing room at both ends.

A label that technically avoids collision but violates these distances is not professionally placed and cannot score 9 or higher.

### Callout labels and leaders

For every callout:

- **Leader tail-to-label-block gap:** **0–2 px**.
- **Leader-to-unrelated glyph clearance:** minimum **8 px** everywhere after leaving the attachment edge.
- **Leader-to-unrelated road/boundary clearance:** minimum **6 px**; crossings are prohibited.
- **Leader-to-other-leader clearance:** minimum **6 px** except at deliberately separated common origins/targets that remain visually unambiguous.
- **Callout label-to-neighboring label clearance:** minimum **10 px**; target **14 px**.
- **Arrow-tip target distance:** tip must land on the named street stroke or be within **2 px** of its visible stroke edge.
- **Stem target:** when a cul-de-sac stem exists, the tip must target the stem, preferably **>=8 px** from the bulb edge and **>=8 px** from the junction when usable stem length permits. If the stem is shorter than 16 px, target its midpoint and document the exception.
- **Leader length:** target <= **80 px** at 1×; >80 px requires a recorded no-cleaner-placement justification. >110 px is a hard fail unless the user explicitly approves that exact routing.
- **Leader bends:** use the fewest bends needed; ordinary callouts should use 0–2 bends. Zig-zag routing is a failure.
- **Words crossed/touched by leader:** **0**.
- **Unrelated roads crossed/touched by leader:** **0**.
- **Wrong target / bulb-only target when a stem exists:** **0**.

### Navigational branch completeness

Every navigationally distinct green/yellow branch, stub, tiny loop, or cul-de-sac must be accounted for.

- `unlabeled_worked_branches = 0`.
- A branch may be satisfied by a direct label, curved label, callout, or a documented same-name continuation that is visually unambiguous.
- The review must inventory every worked branch and reconcile `navigational_branch_count` with `branch_label_bindings`.
- A visually distinct worked branch with no clear street ownership is a hard failure even if the road name appears elsewhere on the card.

### Map balance and useful-space standard

The map panel must prioritize the assigned/workable geometry and required navigation context.

- Preferred: the bounding box of assigned/workable geometry plus required connected approach context should occupy **65–90%** of the available map-panel width and **65–90%** of its height after normal margins.
- Hard review trigger: if either dimension is below **55%**, or a single contiguous irrelevant blank/non-work context region visually consumes more than **25%** of the panel, the reviewer must reject the layout or record a specific navigation/source-preservation reason that makes the space necessary.
- Do not preserve large irrelevant context merely because it existed in an old/source image when that context can be uniformly cropped/repositioned without changing the assignment.
- Enlarged details do not excuse a poorly balanced full map.

### Enlarged-detail placement measurements

An enlarged detail must use the same label measurements as the main map, plus:

- **Detail label to panel edge/divider/title:** minimum **12 px**, target **18 px**.
- **Detail label-to-label clearance:** minimum **10 px**, target **14 px**.
- **Detail geometry fill:** the useful enlarged geometry should normally occupy **60–90%** of the detail panel's usable width and height; large empty crop areas are a visual failure unless required for label whitespace.
- **Label binding errors:** 0.
- **Unlabeled worked branches in detail:** 0.
- **Leader word/unrelated-road crossings in detail:** 0.
- The detail must be visibly cleaner than the same labels on the full map. If not, reject the detail strategy.

## Exact-final-PDF measurement inventory

Every visual review must include:

- `measurement_reference: "exact_final_pdf_1x_72dpi"`
- `measurement_standards_applied: true`
- `label_count`
- `label_placement_measurements` with one record for every navigational label
- `navigational_branch_count`
- `branch_label_bindings`
- `unlabeled_worked_branches`
- `map_balance_review`
- the existing `short_street_decisions` and leader inventory

A direct/curved-label record must include the measured assigned-road gap, unrelated-label clearance, unrelated-road clearance, junction/bulb clearance, panel-edge clearance, and tangent/alignment evidence. A callout record must include tail gap, label clearance, leader clearances/crossing counts, target distance, and stem-target evidence.

Count-only assertions are not enough: list lengths must reconcile with their declared counts.

## Per-part >9.0 minimum — NO averaging escape hatch

For territory cards, **every scored category and every applicable mandatory visual part must be strictly greater than 9.0/10**; an exact 9.0 fails. It is not a maximum; the target is **10/10 everywhere**.

Required category scores remain:
- preservation
- geography
- labels
- template
- export

Required visual part scores are:
- `direct_curved_label_placement`
- `callout_leader_system`
- `branch_completeness`
- `clutter_whitespace_balance`
- `map_balance_and_context`
- `family_resemblance`
- `enlarged_detail_quality` when an enlarged detail is used

Rules:
- every applicable category score must be **>9.0**, unrounded;
- every applicable part score must be **>9.0**, unrounded;
- any hard gate or unverified mandatory evidence still fails release;
- **release score = the lowest applicable category/part score**, not a weighted average;
- a weighted mean may be reported only as a diagnostic statistic and can never determine PASS;
- if any applicable score is 8.99, the card fails even if every other score is 10;
- always continue useful repair/review work toward 10/10.

Hard visual defects from this standard continue to cap the applicable visual part(s) and overall release score at **8.0 or below** until repaired.

## Regression fixture status after annotated R42 rejection

- R19: FAIL.
- R28: FAIL.
- R42: FAIL — user-annotated negative fixture.
- No later candidate becomes a positive fixture merely because a model assigns a score above 9. It becomes a positive fixture only after the exact-final-PDF measurement inventory, per-part score floor, visual comparison, and all mandatory gates pass, with no subsequent user rejection.

## R45 canonical card-family shell and label-decision authority — 2026-09-12 — SUPERSEDING STRUCTURAL AUTHORITY

For outer card structure and collection-wide visual identity, `New-Designed-Card-Family-Contract.md` is now the canonical authority. This visual-regression standard continues to govern measured labels, leaders, branch completeness, clutter, map balance and detail quality.

The reference hierarchy is now explicit:

- **A33 + 60AB**: primary released shell/sidebar/directions authority.
- **330**: approved split/detail behavior while retaining the canonical shell.
- **254**: dense-label/detail placement example only; its older shell is not a template for new cards.

Before any passing (>9.0) `family_resemblance` score, require the exact-final-PDF `card_family_review` and a PASS from `scripts/validate_new_designed_family.py`, plus actual-size visual confirmation. A script PASS cannot prove family resemblance; a script FAIL blocks it.

The fixed shell, schematic-map requirement, screenshot-box boundary prohibition, allowed map-layout modes and canonical label typography bands in the family contract are hard visual gates. They cannot be averaged away by label/geography/export strength.



## R45 ordered label-placement decision gate — 2026-09-12 — HARD OVERRIDE

The canonical family contract's label decision tree is mandatory for **every navigational label**. This section makes the user's long-standing placement rule explicit and testable.

Required order: **direct beside road -> curved with road -> clearer same-road placement -> nearby attached-arrow callout -> dedicated detail**. A builder/reviewer may move forward only after the earlier option has been shown unsuitable.

### Direct/curved attachment expectations

- Street names visually rest beside the exact assigned street; they are not free-floating annotations.
- Keep the existing 2–15 px assigned-road gap, preferred 4–10 px.
- Straight labels align with the road tangent; curved labels bend with the road and remain consistently close along the whole word.
- Do not permit avoidable label overhang beyond the usable road run. Target >=10 px end breathing on ordinary labels; <6 px requires a documented unavoidable source-geometry reason. Short-road direct exceptions keep the stricter >=15 px per end and usable-run >= label-ink+30 rule.
- A road-following label that technically has no pixel collision but looks detached, overhung, tacky, misaligned, or poorly associated with the road fails the visual standard.

### Same-road relocation before arrow

If the first placement is cluttered, near a junction/bulb, overhangs, or has poor road association, inspect other clear portions of the **same street** and the opposite side before introducing a callout. The review must record `same_road_alternatives_assessed=true` for any callout.

### Nearby-arrow fallback

When no clean same-road placement exists, move the label to the nearest practical uncluttered area and attach one clean leader to the exact street. Callouts are not permission to move a label far away merely because a distant blank area exists. Prefer <=80 px leader length; >80 needs a no-closer-placement justification; >110 fails absent explicit user approval.

### Required additional evidence

`new_design_visual_review` and `label_placement_decision_review` must record:

- `label_decision_tree_completed: true`
- `label_overhang_violations: 0`
- `floating_unled_labels: 0`
- `same_road_before_callout_verified: true`
- `distant_avoidable_callouts: 0`
- `callouts_without_exhausted_direct_options: 0`
- `callouts_not_in_nearest_practical_whitespace: 0`
- one decision record per navigational label.

Any missing/false value or count above zero is a hard visual failure and caps labels/family resemblance/overall at 8 until repaired. Run `validate_label_placement_contract.py` on the artifact-bound review JSON; structural PASS never replaces visual inspection.


## R46 Mandatory reviewer parity

The visual standard is identical for authorized-internal and separate critic reviews.
On every created/changed territory artifact, the internal reviewer automatically
rechecks the exact PDF at actual size, 2x and full-coverage overlapping 4x regions,
plus targeted dense/leader/detail crops. No internal shortcut, memory-based approval,
or builder score may substitute for the measurements and visual judgment required
above. A separate critic is additional when available/required.

## R47 locked style-token regression gate - 2026-09-12
For new/rebuilt output, family resemblance begins with deterministic R47 token provenance. The shell may no longer be manually recreated. Require strict-token validator PASS plus canonical-family validator PASS on the exact PDF before a >9 template/family score.

Review long territory IDs and two-line localities specifically: they must use the locked responsive variants, preserve the fixed sidebar, and never clip or force a sidebar-width change. Current 288 and current 262A are negative scaled-shell regression fixtures; R47 reflow fixtures demonstrate layout fit only and are NOT FIELD USE geography evidence.


## R48 visible identity regression veto — 2026-09-12
The territory identifier is part of family resemblance. Master-map notation is not card typography. Reject visible IDs containing source hyphens or a residential `R` prefix. Require congregation-card display grammar (`263a`, `A263a`, `T263a`, `TA263a`) and the separately validated canonical filename. Identity errors cap family resemblance/template/overall at 8.


## R49 pre-critic residential visual regression — 2026-09-12
Before a new/redrawn residential candidate reaches formal critic review, require actual-size + 2x + 4x map inspection beside exact saved Territory 273 and one additional density-similar approved New Designed card when available. Record `precritic_family_review`. Zero collisions are insufficient: the candidate must visibly share the same road/label drawing grammar and neighborhood-scale composition.

Territory 269 R48 is a negative regression fixture. Its former passing scores do not establish a positive baseline. Any future candidate reproducing its sparse schematic character, topology simplification, family mismatch, or reviewer self-confirmation must fail before critic dispatch.

## R50 label-system negative regression and pre-critic veto — 2026-09-13
Add the user-rejected Territory 269 label candidate to permanent negative regression evidence. It must fail for at least these independently visible reasons: **Winter Park Rd is laid on/touching its green road**, and the **Winter Park Rd + Winter Park Ct neighborhood is avoidably crowded**. Similar defects may not be excused by zero bounding-box collisions elsewhere or by a high shell/family score.

Before formal critic dispatch require a complete rendered-road/name inventory, zero missing required public street/cul-de-sac labels, zero label-road touch/overlap, zero label-label overlap, zero avoidable clusters, and zero callout attachment/target/crossing defects. Every label-neighbor gap under 12 px at 1x is a mandatory cluster-review trigger; visually clean ownership and no clearer alternative must be demonstrated.

For residential/neighborhood maps, exact Territory 273 is the label-placement positive reference: labels rest beside/follow roads; short streets that cannot carry their names cleanly use nearby attached callouts; the card preserves readable separation between adjacent labels. Raster/image-generation concepts are not release candidates and cannot become positive fixtures.



## R51 road-gap consistency / PDF-output regression — 2026-09-13
Add two permanent failure classes: (1) a label visibly floating farther from its street than neighboring approved labels despite technically remaining within 2–15 px, and (2) an image-only territory result presented as completed output. Use a same-card median from at least three good direct/curved labels and a default ±3 px review band for labels expected to match that spacing. Preserve visual judgment: a numerical pass never overrides obvious detachment.

For long/complex roads, review whether repeated labels are needed for navigation. Each repeated placement must occupy a genuinely distinct readable run and pass contact/clutter checks. Curved/diagonal labels must follow the local street shape over the whole word.

## R52 Territory 269 entrance-target / suffix / spacing regression
Pin the user-approved two-label PDF hash `ddd76a4c1ac44854c988ae8c10f1e238574a83245813dc60ba4a839cd92443cd` as a component-only reference. Foxboro's lower repeat identifies the Walton entrance stem, while the upper loop repeat stays; southern Steamboat follows the road through “Dr” with native-width spacing, while the west repeat stays. Negative hashes: wrong-target/straight-label `391522520a6011c797cdba4186e0e0748113749725dffda18ea3154fe8d0a253`; cramped-width first repair `c6c16c2b6b86129044958800c064f2b175dbb9d5b43506d5473f68ca73c85996`. Withdraw the old 9.7 approval; never use it as positive evidence. See `fixtures/R52-T269/fixture.json`, the new contract and regression tests. Reject both known failure classes from actual PDF measurements and fresh visual comparison; count-only/overlap-only passes are insufficient. Preserve all historical negative fixtures and canonical shell/273 authorities.