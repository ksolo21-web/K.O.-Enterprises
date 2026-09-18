# Territory Segment-Role Binding & Whole-Label Continuity Contract — R52
2026-09-13 | Applies to builder, mandatory internal critic, and any additional independent critic.

## Why this revision exists
Territory 269 exposed a semantic failure that clean spacing and collision counts did not catch. The inner Foxboro Dr label had the correct name but the wrong navigation job: its arrow identified the eastern loop, while the missing label was for the entrance from Walton Blvd. Moving it to attractive whitespace without first fixing that target could not solve the problem. The accepted repeat sits below the loop, immediately west of the entrance, with a short attached arrow on the green entrance stem. The northern loop label stays unchanged.

The lower Steamboat Springs Dr name also had to follow the road over its entire length. A single rotated straight line did not follow the bend through its final “Dr.” The first curved repair still looked cramped because its placement used advance widths that differed from the font actually embedded in the PDF. Zero glyph overlap was not enough. The approved repair uses the actual PDF character widths and a continuous road-following baseline, including the suffix.

These are general lessons about navigation meaning and whole-label typography, not permission to copy Territory 269's coordinates, position every label below a loop, or add arrows to all streets.

## 1. Lock each label's navigation job BEFORE placement
Create a target lock from the source and the user's instructions before moving or scoring labels. Every label placement, including every repeat, needs a unique `label_id`, exact street name, `navigation_role`, physical `segment_id`, and source evidence. Identify that segment using its endpoints/junctions/entrance relation and a predeclared corridor or source feature span. Bind the lock to the exact source hash.

A label role can be entrance_run, loop_run, west_run, south_run, court_stem, or another source-defined role. Matching the street name alone does not prove correct attachment. Neither “arrow hits green paint” nor “arrow touches Foxboro Dr somewhere” is sufficient. Entrance labels must identify the verified entrance stem, not a loop, bulb, parallel branch, adjacent street, or general neighborhood area. Cross-check the selected entrance against the card's directions and source/user clarification. User clarification resolves a bounded labeling instruction; it does not certify new geography or work eligibility.

Repeated labels must each fulfill their intended navigation job. Two valid names on the same loop cannot satisfy a loop-plus-entrance requirement. Require role-to-segment coverage as well as count. Retain an already-correct repeat unless its change is explicitly necessary and authorized. A disagreement between directions, source and target remains unresolved; do not guess.

## 2. Keep placement order, constrained to the intended segment
Keep the existing order: direct beside road → curved beside road → clearer location on the same intended navigation run → nearby attached-arrow callout → dedicated detail. “Same road” does not authorize abandoning the required entrance/run for a roomier, same-named branch.

For a short entrance, a nearby callout is appropriate when direct/curved text cannot fit cleanly. Assess both sides and nearby whitespace; use the clearest placement that unambiguously serves that entrance. The label may sit outside the loop it serves. Its tail must be visibly attached with the existing 0–2 point/1x-pixel gap, must not begin inside a glyph, and its filled head must meet the exact locked target paint. Keep all existing length, crossing, clutter, fit and glyph-clearance requirements. Do not add unnecessary leaders.

## 3. Inspect the entire label, not its center
For each direct/curved name inspect the first word, middle, final word and suffix (Dr, Rd, Ct, Ln, Blvd, etc.). On a bending selected run, the complete baseline must follow the local street shape with consistent assigned-road clearance. Both ends must remain associated with that run. A suffix that straightens, twists, lifts away, crosses an adjoining road or overhangs the intended run fails even when the center is well placed.

Use saved-PDF glyph transforms and local street geometry, with actual-size and closeup review. Review local tangents and per-glyph road gaps, not only the average or minimum gap for the whole label. A straight label is still valid on a genuinely suitable straight segment; do not force cosmetic curvature. These requirements preserve all earlier spacing/alignment limits.

## 4. Use the actual font metrics and judge visual spacing
Compute curved-text advance positions from the actual PDF font widths or the verified shaping engine for the actual font, with any intended kerning/tracking explicitly represented. A reconstructed/extracted font with different advance widths cannot silently replace the PDF's metrics. Do not “repair” width errors with blanket tracking, smaller type or a different font.

Retain quantitative glyph-ink overlap/contact checks AND visual whole-word spacing review. Zero overlap does not imply readable rhythm. Inspect suspicious kerning, squeezed pairs, expanded gaps and the ending suffix at actual size and 4x. Metrics are supporting evidence, never substitutes for that review. In the pinned Territory 269 fixture, the native-width check uses the previously declared 5% maximum relative error; that fixture tolerance is not a universal typographic redesign rule.

## 5. Critic duties and hard vetoes
Freeze the exact candidate. The mandatory authorized-internal critic reopens the raw target lock and source, independently traces each disputed/repeated label to its actual intended segment, and inspects every word's ending. Record `critic_independent:false`; a genuinely separate runtime is additional when available or required. Never use the builder's target ID, prior PASS, counts or claimed score as proof.

The reviewer must explain what the label tells someone navigating the card. Ask: which entrance/run does this placement identify, and can the reader tell immediately? Then inspect start → middle → suffix, including font spacing. Record both actual-size and closeup screenshots actually inspected. A correct name on the wrong part of that street, a missing entrance-role label, a suffix that departs from its street, or visible crowding is a hard failure. Cap affected visual part(s) and overall release score at 8 until repaired. Unknown/missing evidence cannot pass. Preserve strictly >9.0, target 10, and every prior mandatory gate; no averaging.

## 6. Preserve approvals and make the lessons executable
The user-approved exact PDF is SHA-256 `ddd76a4c1ac44854c988ae8c10f1e238574a83245813dc60ba4a839cd92443cd`, 60,648 bytes. It is a positive component reference for these two label treatments and bounded preservation. It does NOT replace A33/60AB shell authority, Territory 273's broader residential comparator, current-source checks, inventory or duplicate-coverage audits. Do not reopen or modify it merely to update skills.

The earlier 9.7/10 input is negative, not positive evidence. Preserve the wrong-target/straight-label version and cramped-font first repair as negative fixtures. Run actual-PDF regression checks that accept the approved component behavior, reject both known failures for the relevant reasons, and leave the approved PDF unchanged. A skills-only update never manufactures a new full-card certification.

For a later bounded repair, predeclare permitted edit areas; compare complete page renders and native paths, other labels, repeated roles, sidebar, directions, date and work colors. Do not expand masks after detecting unexpected differences. Recapture the exact saved bytes after any edit. This contract adds checks; it does not waive inherited full-card gates or authorize geographic changes.

## 7. Evidence contract and execution
Require `label_navigation_review` and `critic_label_navigation_review`, bound to the exact final PDF hash. The first contains a separate target-lock path/hash, all in-scope rendered label IDs, role/segment bindings, source evidence, final-PDF target coordinates, and whole-label/font-spacing measurements where applicable. The critic record contains fresh source/role/whole-label checks and inspected screenshot paths. Examples are in `tests/R52-component-review.json` and `tests/R52-target-lock.json`.

Run `scripts/validate_label_navigation_contract.py REVIEW.json --pdf FINAL.pdf`. It validates evidence structure, target-lock/artifact hashes, declared coordinates against locked corridors, role coverage, whole-label records and inherited numeric limits. It does not discover real streets or act as a visual critic. `scripts/validate_internal_reviewer_parity.py` must invoke this additional gate for a full-card R52 review. A bounded component report may pass its focused regression but must NOT pass the full-card release gate.

Run `scripts/check_t269_label_regression.py fixtures/R52-T269/approved.pdf` for fixture-specific measurements derived from actual PDF paths/text/font widths. Run `python tests/test_r52.py` for positive/negative and integration regression tests. Coordinate/text selectors in the fixture checker are deliberately restricted to Territory 269; general production work requires its own source-bound target lock.