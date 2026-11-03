# Home Inspection — Milestone 4 V9 source-media grounding checkpoint

**Date:** 2026-11-03  
**Repository:** `ksolo21-web/K.O.-Enterprises`  
**Branch:** `home-inspection-development`  
**Customer delivery:** BLOCKED. **Real inspection competency / inspector qualification:** NOT VERIFIED.  
**Scope of validation:** synthetic, offline media-grounded evaluation logic only.

## Baseline and requirements retained

The full approved Home Inspections business plan, M4 Q01→specialists→Q02→Q03 independence, original source evidence custody, private source-bound signed human decisions, professional credential preflights, Michigan jurisdiction snapshot, independently witnessed synthetic trust history and the navy-and-white Option 2 photo-led PDF remain untouched. V8 benchmark instrumentation remains the primary source of serious-defect metric thresholds and reviewer declarations. Do not change `main` or the root `PAUSE_AUTONOMY`. All customer source data, genuine inspector records, private case PDFs and signing keys remain outside Git.

Previous checkpoints:
- [V7 witnessed trust governance](CHECKPOINT_M4_WITNESSED_GOVERNANCE_V7.md)
- [V8 frozen serious-defect benchmark, 1008/1008 tests](CHECKPOINT_M4_FROZEN_SERIOUS_DEFECT_V8.md)
- [Research-only DeepSeek/Qwen 9B candidate](CHECKPOINT_M4_MODEL_CANDIDATE_DEEPSEEK_QWEN35_9B_2026-11-03.md)

No AI model was downloaded, integrated, fine-tuned or live-benchmarked. No production report or customer case was released.

## Why V9 was necessary

V8 froze case-level predictions and required independent human matching, but a predicted roof/electrical defect could still be credited as correct merely because a human matched its defect ID and system for the right *case*. This was insufficient to test whether the AI correctly located the problem in the **actual source photo or video frame**. V9 introduces separately frozen source-media and normalized region crosswalks, plus independently reviewed clean-photo controls.

## New implementation

1. `inspection_engine/m4_media_grounding.py` — **read-only additive V9 gate** around V8:
   - Per-case ordered source-media manifest, exact `media_id`, source SHA256, source kind (original photo, original video, or derived video frame), inspection area, assessment status and parent-video timestamp for derived frames.
   - Derived video frames require an original video SHA256 registered in the **same case**; arbitrary frame timestamps or missing parents fail closed. Original videos cannot be scored as if they were still photographs.
   - Each V8 model prediction and each professionally adjudicated defect label must have **exactly one** independently pinned media-ID/source-hash crosswalk with normalized image/frame bounding box `[x0,y0,x1,y1]`, with finite numbers inside [0,1]. An accepted match must point to the **same original photo or exact frame** and have intersection-over-union **≥0.25** with the human-marked defect region. Wrong photo/frame, wrong source hash, non-overlapping bounds, invalid geometry, duplicated region and invented source ID all block scoring.
   - Case manifest explicitly binds every photo/video/source row by SHA256. Training-vs-holdout exclusion is checked at the **individual photo/video/frame hash**, in addition to V8's case evidence hashes and property source-group checks.
   - The model-facing blinded media view excludes human label, reviewer and review-status fields. A separate model-time grounding snapshot binds the source-photo manifest and prediction regions to the V8 model snapshot, with a post-freeze human adjudication timestamp. Exact hashes must be independently pinned outside the untrusted local bundle before label disclosure.
   - Incomplete / not-inspected media cannot silently count as evidence of complete defect detection; a photo with no defects must explicitly have the `reviewed_no_defect` state. A photo marked clean cannot carry an adjudicated defect label.
   - A stricter media-level pilot metric check requires at least **10 clean-case controls**, at least **10 clean source images**, and clean cases representing at least **10% of the cohort**. Any false-alarm prediction on **any** reviewed clean photo blocks the new media-grounded threshold, including when another photo at the same property contains a true defect.
   - The original V8 threshold (≥100 cases, ≥30 critical defects, all 13 systems, both residential/commercial scopes, no missed major/critical hazards, precision ≥95%) is **not lowered or replaced**.
2. `scripts/m4_media_grounding_cli.py` — local read-only CLI. Expects ten **private** JSON inputs: V8 cases, predictions, human matches, model snapshot, adjudication snapshot, training index, source media manifest, prediction regions, label regions and the grounding snapshot. It also requires eight separately pinned SHA256 values. It delegates to the V8 safe JSON loader, which refuses symlinks, nonregular/oversize files, untrusted duplicate-key/nonfinite JSON and inputs inside Git.
3. `tests/test_m4_media_grounding.py` — 36 synthetic adversarial tests, including correct photo localization; wrong photo; wrong frame from the same original video; missing parent video; bad timestamp/bounds; NaN; mismatched source hash; training/media collision; missing or duplicated label/prediction regions; uninspected/inconclusive evidence; no-defect photograph with a label; silent missing labeling; a canonical 100-case metric fixture with 10 negative control cases; fewer than 10 controls; and false alarms on a clean photo at an otherwise defective property.

## Verified test evidence and repair history

- **V9 source-code commit:** `acd5f9a7c16439f7c70533be0968a0640f52dcf3`.
- **Source-code CI:** [GitHub Actions run 41740718729](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41740718729) — SUCCESS, exact branch head matched the tested commit at that time.
- Python compilation: PASS; targeted M3 regressions: 7+5+28 PASS; **full offline inspection suite: 1,044/1,044 PASS**; source integrity: PASS.
- First V9 full run [41739966235](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41739966235): 1,044 executed, one test fixture error. Invalid NaN deliberately cannot be hashed into canonical JSON; the test tried to seal it before expecting rejection from the media checker. Corrected `test_bad_coordinates_and_nan_rejected` to assert rejection at the earliest canonical freeze stage. Validation and safety requirements unchanged.
- Internal review further caught clean-photo false alarms within a defective property; fixed in `m4_media_grounding.py` and added an explicit 100-case regression. CI passed on the corrected code.

## Mandatory limitations — NEVER claim production approval

- `actual_source_bytes_independently_rehashed=false`: V9 cross-checks **declared media SHA256**, but has not yet loaded, decoded and independently hashed actual original customer photos/videos, or verified that extracted frames correspond to source-video frames. A false media manifest can still be signed by untrusted operators. Develop a private original-byte reader, frame-extraction provenance and independently retained custody receipts.
- `real_photo_or_video_contents_professionally_validated=false`: all assertions about defects and their regions remain synthetic for test purposes; photo-based hazards and component recognition have **not** been measured against a real professionally labeled held-out dataset.
- `independent_evaluation_pins_authenticated=false`: hash equality is not proof that the external pin originated with an independent qualified custodian. The code cannot detect a dishonest custodian or retroactively forged model-time freeze without a genuine external authority.
- `qualified_inspector_authorized=false`: professional identity, legal qualifications, consent, issuer authority, independent Q02/Q03 governance and approved human signoff remain real-world blockers.
- IoU ≥0.25, 10% clean-case requirement and zero clean-photo false alarms are **pilot evaluation heuristics**, not scientifically validated operating thresholds. Pre-register and calibrate with independent professional review before use with customers. Do not optimize the model on held-out examples.
- Real corpus requirements persist: at least 100 permissioned professionally labeled cases, 30 critical hazards, all 13 systems, false alarm/false negative adjudication, known property family exclusion, and independent holdout custody.
- All returned results preserve `customer_release_allowed=false` even if synthetic V8/V9 numerical thresholds pass.

## Internal critic / acceptance status

Internal review only; no separately callable independent critic agent was available. **V9's synthetic software contract passed 1,044/1,044 offline checks**, but full Milestone 4 production readiness remains **below the user's strict >9.0/10 threshold** because real photo evidence authenticity, independent professional labels, held-out model accuracy and verified signoff have not passed. Do not call the business operational or publishable.

## Resume action — next critical path

1. Verify final CI associated with this documentation checkpoint (documentation commits trigger full reruns), without confusing source-code success with the later documentation-only run.
2. Add a **private original-byte source evidence verifier** that rehashes/decode-checks actual photos and checks video/frame extraction provenance, with permission/consent guardrails and synthetic fixtures; never commit originals.
3. Establish professional blinded labeling protocol and held-out pilot authorization, including a distinct source/evidence custodian and independent inspector reviewers, visibility and uninspected-state adjudication, double labeling of severe hazards and minimum cohort design.
4. Exercise all 13 systems on consented professionally adjudicated real photos/video, once properly authorized. Report serious-defect miss rates, confidence intervals and safety/coverage stratification, not simply a single aggregate accuracy number.
5. Protect V2–V9 architecture, no new accounts/paid tools, `main`, `PAUSE_AUTONOMY`, offline/privacy restrictions and disabled customer delivery. Keep DeepSeek/Qwen candidate research-only until measured with the same frozen evaluation.
