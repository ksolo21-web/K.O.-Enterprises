# Territory Automatic Execution & Reviewer Parity Contract — R46 — 2026-09-12

## Standing authority

This contract is a **mandatory execution gate** for Kaleb's congregation territory-card work. It applies in regular Chat, ChatGPT Work, Projects, GitHub-backed execution, and any other available workflow that creates, revises, repairs, converts, styles, audits for release, or exports a territory-card artifact.

The user has explicitly authorized this behavior as a standing rule. **Do not ask for permission to use the territory skills or internal reviewer on each card.** Only a later explicit user instruction changing this standing rule may supersede it.

A territory task must never silently fall back to a generic map/PDF workflow because the territory skills were not manually named.

## 1. Automatic trigger — Chat and Work use the same rule

At the first sign that a request concerns the user's congregation territory-card system, automatically load the active territory package before substantive artifact work. Trigger examples include, but are not limited to:

- build/make/create a territory card or map;
- rebuild/redraw/convert an old card;
- fix a territory number, boundary, street, label, arrow, legend, sidebar, directions, color, crop, map layout, map style, or card style;
- update a territory card from a new drawing or live-map verification;
- continue a numbered territory or batch from another chat;
- export/re-export/optimize a territory PDF;
- review/release/repair a territory card;
- compare an old card to a new card;
- inspect whether an artifact matches the New Designed Territory Cards family;
- create apartment/telephone/business/residential territory cards;
- any request referring to the user's territory numbering, `Work Inside Only`, `Work Both Sides`, `Do Not Work`, assigned housing, territory boundaries, or the New Designed card format.

Audit-only territory questions also load the active skills when the answer depends on card identities, active numbering, coverage, or prior territory standards. The mandatory artifact review lane below applies whenever a card/map/PDF artifact is created or changed.

**Surface parity:** regular Chat and Work must use the same active revision, same references, same gates, same reviewer contract, and same score rule. Work is not a looser path.

## 2. Active-package loading — fail closed

Before building or changing a territory artifact:

1. Read `/Skills/Territory Cards/ACTIVE-SKILLS.json` when Library access is available.
2. Load the exact builder, critic, quality-loop, canonical family contract, visual regression standard, and validator paths named by the active record.
3. Use the active package revision, never a same-named stale copy recovered elsewhere.
4. Record the active revision and package hash in the task checkpoint/release evidence.

If the active package cannot be accessed in the current environment, attempt the available authorized Project/repository/package recovery route. If it still cannot be loaded, **block artifact creation/release rather than silently proceeding with generic instructions**. State the access limitation truthfully.

This contract encodes automatic behavior inside the territory workflow. It does not claim that a saved Markdown file can override a product-level router when the skill package is unavailable to that environment.

## 3. Mandatory execution chain for every artifact-changing task

No card may skip this chain:

`AUTO TRIGGER -> LOAD ACTIVE PACKAGE -> RECOVER REQUIREMENTS/SOURCES -> BUILDER -> DETERMINISTIC GATES -> FREEZE CANDIDATE -> INTERNAL CRITIC-ONLY REVIEW -> REPAIR LOOP -> [SEPARATE CRITIC WHEN AVAILABLE/REQUIRED] -> FINAL SAVE/OPTIMIZE -> EXACT-SAVED-PDF RECAPTURE -> INTERNAL FINAL REVIEW -> [SEPARATE FINAL REVIEW WHEN REQUIRED] -> RELEASE`

Rules:

- Loading the skills is automatic; no manual “use the skills” prompt is required.
- The internal reviewer is **mandatory on every created or changed territory artifact**, even when a separate critic is also available.
- A separate critic agent/runtime is **additional**, not a replacement for the internal reviewer, whenever such a runtime is available or independent review is required by the active task.
- If no separate agent runtime exists, record that honestly; the mandatory internal reviewer still runs and must never be labeled independent.
- Deterministic validators are evidence tools only and never replace visual review.

## 4. Internal reviewer = critic contract parity

The authorized internal reviewer must behave as a critic-only reviewer, not as a casual self-check. Reviewer provenance changes; the standard does not.

The internal reviewer MUST use the **same**:

- builder/critic source and coverage contracts;
- exact New Designed family contract;
- exact label decision tree and measurements;
- full geography/current-inventory/duplicate-coverage requirements;
- two-major-crossroad rule;
- branch/status-paint checks;
- housing/access/navigation rules;
- PDF/export/delivery-identity checks;
- hard vetoes and score caps;
- score categories and applicable visual-part scores;
- strictly `>9.0` unrounded minimum for every category/part, target 10;
- final release score = lowest applicable category/part score;
- actual-size and 2x/4x screenshot review requirements;
- exact-final-PDF hash binding;
- repair/retest loop and hash invalidation rules.

There is **no lighter internal rubric** and no internal-review exemption from a critic rule. The internal report must carry the same major critic report objects, including family, label-placement, geography/current-inventory, duplicate-coverage, branch/status, navigation, housing, content and applicable delivery-identity reviews.

## 5. Reviewer separation protocol

Before an internal or independent review round:

1. Freeze the candidate PDF and record SHA-256, byte size, page count, source authority, and active skill revision.
2. The reviewer enters **critic-only mode**: it does not edit the candidate while scoring it.
3. The reviewer must generate/inspect fresh evidence for that exact hash.
4. The reviewer must not use the builder's claimed score, “looks good,” prior PASS wording, or expected diagnosis as evidence.
5. The reviewer must re-evaluate the whole card, not merely the repaired region.
6. If repair is needed, finish the review as FAIL/FIX_REQUIRED first. Then return to builder mode for the bounded repair.
7. A repaired PDF receives a new hash and a new review round from fresh captures.

For an internal reviewer, same-chat awareness cannot be truthfully called independence. Record `reviewer_type: authorized_internal` and `critic_independent: false` while still applying the same critic contract.

## 6. Mandatory evidence parity

Every internal-review round must inspect at least:

- full page at actual/1x size;
- full page at 2x;
- overlapping 4x regional crops covering the entire map/card, not only known defects;
- targeted closeups for dense labels, leaders, junctions, details, entrances, repaired strokes, and any disputed feature;
- approved family references side-by-side at actual size;
- source drawing/current geography evidence required by the applicable contracts;
- extracted PDF text for visible identity/stale hidden text/source-credit checks.

The review report must list the screenshots actually inspected. Capture generation alone is not inspection.

## 7. Mandatory internal-review parity record

Every internal review report must include `reviewer_parity_review` with at least:

```json
{
  "contract_revision": "R48",
  "reviewer_type": "authorized_internal",
  "critic_independent": false,
  "candidate_frozen_before_review": true,
  "reviewer_edited_during_review": false,
  "builder_claimed_score_used_as_evidence": false,
  "fresh_capture_generated": true,
  "actual_size_inspected": true,
  "full_page_2x_inspected": true,
  "overlapping_4x_full_coverage_inspected": true,
  "targeted_closeups_inspected": true,
  "same_critic_contract_applied": true,
  "same_hard_vetoes_applied": true,
  "same_score_floor_applied": true,
  "same_report_schema_applied": true,
  "whole_card_rechecked_after_repairs": true,
  "artifact_sha256": "<exact reviewed PDF SHA-256>",
  "active_skill_revision": "<ACTIVE-SKILLS revision>",
  "screenshots_inspected": []
}
```

Any false/missing required parity field blocks release. Run `scripts/validate_internal_reviewer_parity.py REVIEW.json` on every authorized-internal report.

## 8. Hash invalidation and exact saved artifact

Any byte change to the candidate invalidates all earlier builder validation, internal review, independent review, screenshots, and release receipts that were bound to the old hash unless a specific unchanged-evidence contract explicitly proves continued validity.

After optimization/upload/save, retrieve or materialize the **exact saved/delivered PDF**, recalculate its hash, render fresh screenshots, and run the internal reviewer again. A clean working copy is not enough.

If a user later points out a defect, that finding reopens approval for the affected artifact and any positive fixture based on it until repaired and retested.

## 9. Reviewer disagreement

If the mandatory internal reviewer and a separate critic disagree:

- do not average scores;
- do not pick the higher score;
- preserve both findings;
- treat any unresolved hard defect from either reviewer as blocking;
- repair the defect or obtain evidence resolving a mistaken finding;
- rerun both applicable review lanes on the revised exact artifact.

## 10. Release rule

A territory artifact is release-ready only when:

- the active package was loaded automatically;
- all mandatory builder/deterministic gates pass;
- mandatory internal reviewer parity validation passes;
- mandatory internal review has every category/part strictly >9.0 and no hard gate failure;
- any required/available separate critic lane also passes its applicable contract;
- exact saved/delivered bytes have been recaptured and re-reviewed;
- no unresolved user finding remains.

Target 10/10. Never call unfinished, unreviewed, stale-hash, or blocked work complete.

## R48 new-output template prerequisite
On every Chat/Work territory intent that creates a new card, converts an old card, or performs a full rebuild, the automatic pipeline must load `Locked-Template-Style-Token-Contract.md` and `R48-Canonical-Style-Tokens.json` before building. The locked renderer and strict style-token validator are mandatory before candidate freeze. If these R48 assets are unavailable, fail closed and do not improvise a generic shell.


## R48 canonical identity/naming integration — 2026-09-12
R48 adds `Territory-Identity-Naming-Contract.md` as a hard prerequisite. Source/master labels remain source aliases only. New/rebuilt cards must use a verified `card_identity`, the derived congregation-facing display ID, and the exact derived canonical filename. The locked renderer and internal/critic release path fail closed on identity mismatch.


## R49 source-truth / pre-critic automatic stage — 2026-09-12
Insert a mandatory stage **before candidate freeze/formal critic** for every new card, full rebuild, old-card conversion, material geography redraw, or geography/family-rejection repair:

`raw source lock -> endpoint/topology trace -> render -> quick family preflight -> formal critic -> repair -> final exact-byte critic`

The automatic chain must load `Territory-Source-Truth-Preflight-Contract.md`. Formal critic dispatch is forbidden until `source_truth_preflight` has zero invented connections, unresolved omissions and topology conflicts and the quick family preflight has zero obvious mismatch. For residential/neighborhood redraws, exact Territory 273 side-by-side comparison is mandatory.

The critic must then independently re-open raw sources; it may not merely validate or echo the builder's preflight. If no separate critic runtime exists, the mandatory internal reviewer still performs this re-grounding in critic-only mode and records `critic_independent:false`. Deterministic validators remain supporting gates only.

## R50 automatic label preflight + reviewer reinventory stage — 2026-09-13
Supersede the earlier automatic chain with:
`AUTO TRIGGER -> LOAD ACTIVE R50 -> RAW SOURCE/NAME LOCK -> VISIBLE ROAD INVENTORY -> TOPOLOGY TRACE -> BUILD MEASURABLE PDF -> FREEZE PREFLIGHT HASH -> LABEL COMPLETENESS/CONTACT/CLUTTER PREFLIGHT -> FAMILY PREFLIGHT -> INTERNAL CRITIC-ONLY REVIEW -> REPAIR LOOP -> OPTIONAL/REQUIRED SEPARATE CRITIC -> FINAL SAVE -> EXACT-BYTE RECAPTURE -> INTERNAL FINAL REVIEW -> RELEASE`.

Formal critic dispatch is forbidden until `label_completeness_review` and `label_contact_cluster_review` pass structurally **and** the builder's actual-size/2x/4x visual preflight finds zero missing required labels, zero road-contact/overlap labels, zero avoidable clusters, and zero callout defects. Residential/neighborhood maps must include a Territory 273 label-system side-by-side.

The mandatory internal reviewer must independently recount the rendered roads and labels from the exact PDF plus raw naming/topology sources. Its report must include `critic_label_audit`, may not use the builder ledger or prior label score as proof, and must inspect every callout plus every cluster trigger. `validate_internal_reviewer_parity.py` now requires R50 and these objects.

Do not route image-generation/raster-only drafts into formal review or release. They may be used only as concept references until rebuilt as a measurable PDF candidate.



## R51 automatic PDF + metric stage — 2026-09-13
Insert `PDF DELIVERY/METRIC PREFLIGHT` before critic dispatch and repeat it on the exact saved bytes. Territory completion cannot end on a generated image. The canonical PDF is the sole release artifact; rendered images are evidence only.

The builder must measure a same-card gap baseline using at least three approved ordinary labels and screen every label placement against contact, broad 2–15 px limits, and the R51 median-consistency band. Roads flagged for navigation repetition must meet `required_label_count`. The internal reviewer independently remeasures all disputed/outlier labels and at least three reference labels and verifies the final response/download artifact is the reviewed PDF. Run `validate_pdf_label_metrics.py` plus the existing R50 validators in both candidate and final-saved review lanes.

## R52 automatic role-target / whole-label stage — 2026-09-13
The active R52 chain adds `LOCK LABEL ROLE + EXACT SOURCE SEGMENT` before label placement and `ROLE/TARGET + START/MIDDLE/SUFFIX + NATIVE FONT SPACING PREFLIGHT` before critic dispatch and after final save. Load `Territory-Segment-Role-Whole-Label-Contract.md`; require `label_navigation_review` and `critic_label_navigation_review`, and invoke `validate_label_navigation_contract.py` through mandatory reviewer parity. The critic must reopen raw evidence rather than accept the builder's same-street target assertion. No inherited source, inventory, coverage, shell, label, identity, PDF or reviewer-parity requirement is removed. Bounded regression tests do not certify a full card. For skill revisions, preserve positive/negative exact-byte fixtures and verify persisted activation before reporting the saved system updated.