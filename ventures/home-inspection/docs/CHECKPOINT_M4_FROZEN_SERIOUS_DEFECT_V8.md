# Home Inspection — M4 V8 frozen serious-defect evaluation checkpoint

**Date:** 2026-11-03  
**Development repository:** `ksolo21-web/K.O.-Enterprises`  
**Branch:** `home-inspection-development` (leave `main` and `PAUSE_AUTONOMY` untouched)  
**Scope:** Private offline serious-defect evaluation instrument; **no real-world model validation, inspector approval, or customer release**.

## Continuity and requirements preserved

V2 source-bound private intake / Q01 → specialists → Q02 → Q03 → Option 2 navy/white photo report, original evidence custody and PDF receipts; V3 signed human reviews; V4 visual and real-browser PDF tests; V5 jurisdiction-aware credentials and revocation; V6 corroborated issuer source receipts; V7 two-governor witnessed verifier-enrollment and revocation history. V7's 968-test baseline and checkpoint: [CHECKPOINT_M4_WITNESSED_GOVERNANCE_V7.md](CHECKPOINT_M4_WITNESSED_GOVERNANCE_V7.md).

Keep the previously user-supplied third-party DeepSeek/Qwen3.5-9B model **research-only**; see [CHECKPOINT_M4_MODEL_CANDIDATE_DEEPSEEK_QWEN35_9B_2026-11-03.md](CHECKPOINT_M4_MODEL_CANDIDATE_DEEPSEEK_QWEN35_9B_2026-11-03.md). No models were downloaded or evaluated live in V8. No customer photos, identities, access keys or case reports were published.

## Why V8 was implemented

The repository already contained `inspection_engine/serious_defect_benchmark.py` with conservative pilot thresholds: **≥100 actual consented held-out cases; ≥30 critical labels; all 13 inspection systems; residential and commercial coverage; zero missed critical defects; zero missed major defects; and at least 95% human-verified precision**. This is a preliminary metrics gate, never production release.

The missing layer was an auditable *pre-match freeze*. If predictions can be altered after humans see the ground truth, or if the same underlying property appears in training and holdout, a high benchmark score becomes untrustworthy. V8 adds a strict, read-only contract for these dependencies.

## Implemented source files and functionality

- `inspection_engine/m4_frozen_safety_audit.py`
  - `blinded_evidence_view(cases)` emits only six evidence/context fields: case ID, property collection/family ID, original evidence SHA256, partition, property scope and jurisdiction. It explicitly excludes human labels, labeler IDs, adjudicator IDs and consent statements from the **model-facing** view.
  - `score_frozen_safety_audit(...)` requires exact SHA256 externally supplied pins for full held-out cases, model freeze, adjudicated matching, and complete training/tuning exclusion registry. Those external pins must have been recorded before the evaluation by a truly independent custodian; locally computing them at review time does not independently authenticate anything.
  - Every model prediction is bound to its source case evidence SHA256 and system, with unique IDs and no unreviewed addition, deletion or substitution after freeze. The model snapshot identifies model artifact SHA256, prompt SHA256, frozen prediction digest, training registry digest and evidence-only manifest digest.
  - Every frozen prediction receives exactly one independent *post-freeze* human disposition: `matched`, `false_positive`, or `inconclusive`. Matches must identify an existing human-adjudicated label in the same case and inspection system. A real label cannot be claimed twice. A conservative inconclusive disposition is never counted as true-positive.
  - Exact training vs holdout leakage is rejected by **both source-file SHA256 and declared near-duplicate/property collection group**. Duplicate cases, duplicate original evidence SHA and repeated property groups in the held-out cohort are rejected.
  - Reuses the existing conservative serious-defect benchmark, adds per-system recall and miss counts, plus explicit critical and major misses, false alarms and inconclusive counts. Source metadata is indexed for bounded matching without repeatedly scanning all predictions.
  - **Always returns** `customer_release_allowed=false` and explicit `*_independently_verified=false` flags for professional credentials, real-case consent, blind model execution, snapshot custody, training exclusion completeness, and near-duplicate visual detection. Metric success is *not* production approval.
- `scripts/m4_safety_benchmark_cli.py`
  - Read-only local CLI accepts six private JSON inputs and four independently recorded snapshot SHA256 pins. Rejects files inside Git checkouts, symlink inputs, oversized/nonregular files, duplicate JSON keys and NaN/Infinity. All outputs stay in the operator's private environment and never update case state, training, model settings or customer release.
- `tests/test_m4_frozen_safety_audit.py` — **35 synthetic tests** exercising exact freeze, tampered snapshots, training holdout overlap, missing critical detections, duplicate labels/predictions/matches, proper blinded model manifest, wrong-system matches, wrong reviewer identity, missing post-freeze decisions, refusal of invented labels, unconsented cases, and 100-case threshold fixtures.
- `tests/test_m4_safety_benchmark_cli.py` — **5 additional synthetic tests** for private input JSON, duplicate keys, nonfinite numbers, symlinks and Git exclusion.

## Actual verified evidence

- **V8 implementation source commit:** `17ecdbc2e942ce52250e07b00bb691fddfc5d9fb`.
- **GitHub Actions full CI:** [run 41684122890](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41684122890), SUCCESS, run head SHA identical to source branch SHA at the time of testing.
- Python compilation PASS, existing targeted M3 tests 7 + 5 + 28 PASS, full inspection suite **1,008 / 1,008 PASS**, tracked-source integrity PASS.
- Explicit 100-case synthetic fixture with 30 critical defects, 13 systems, both scopes and zero misses **can meet numerical thresholds** while all genuine authority/release flags remain FALSE.
- The paired 100-case fixture with one missed critical defect fails the metric threshold, with the missed label explicitly reported. Inconclusive/false positives do not count as successful detections.

## Internal review, exclusions and required real-world acceptance

**Internal review only; no independently callable critic agent was available.** The V8 software-only increment passed tests, but overall M4 is still **below 9/10 and not production approved**. Mandatory unresolved requirements:

1. **Real evidence authenticity:** the synthetic tests deliberately fabricate all case IDs and source digests and set `synthetic=false` solely to exercise validation. They do NOT demonstrate consent, real photos, inspector labels, issuer verification, field accuracy or legal applicability.
2. **Model-run sealing authority:** snapshot digests and timestamps are locally claimed. Need independently controlled freeze before label disclosure, signed tool/environment receipts, protected custody, and genuine human labeler/adjudicator credential authentication.
3. **No hidden training leakage:** source SHA and declared property groups detect known exact/group overlap, but no near-duplicate image search, semantic similarity scan, supplier or vendor training-set audit, or genuine withheld-corpus proof has been completed.
4. **No professional benchmark has been run:** obtain professionally labeled and consented real held-out cases, independent matches and multi-inspector disagreement resolution, pre-register performance thresholds and false-negative reviews; explicitly test severe electrical/roof/foundation/plumbing/HVAC safety hazards.
5. **Blind measurement, per-system uncertainty and scale:** confidence intervals, prevalence shifts, strata coverage, cross-jurisdiction representation, accessibility, long photo reports and repeated field deployments remain open. The pre-existing fixed 100-case/30-critical pilot gate cannot alone prove general deployment reliability.
6. **Credential, organization and witness identity:** V5–V7 can check signed records, but the real trustees, witness, model-reviewer legal scope and current ASHI/InterNACHI authority remain unauthenticated.
7. **No external customer delivery/payment or qualified inspector final signature**. `customer_release_allowed=false` remains a mandatory invariant throughout.

## Private CLI contract (paths/pins are only examples)

```bash
python -m scripts.m4_safety_benchmark_cli \
  --cases /private/evaluation/holdout_cases.json \
  --predictions /private/evaluation/frozen_model_predictions.json \
  --human-matches /private/evaluation/reviewer_matched_predictions.json \
  --model-snapshot /private/evaluation/model_snapshot.json \
  --adjudication-snapshot /private/evaluation/adjudication_snapshot.json \
  --training-index /private/evaluation/training_exclusion_registry.json \
  --externally-pinned-case-sha256 <independent-64-character-SHA256> \
  --externally-pinned-model-snapshot-sha256 <independent-64-character-SHA256> \
  --externally-pinned-adjudication-sha256 <independent-64-character-SHA256> \
  --externally-pinned-training-index-sha256 <independent-64-character-SHA256>
```

Never calculate the purported *independent* values from the six same-origin files merely to pass this CLI; a separately governed record is needed for real trust. Never store real source photos, customer addresses, private report bundles or signing keys in Git.

## Resume / critical next action

1. Verify that GitHub's final checkpoint/documentation-linked run passes on the latest branch head; the V8 code was already green at 1,008/1,008 as evidenced above.
2. Develop a **preregistered independent benchmark protocol and professional labeling workflow** with consent, separation of model builders from blinded label adjudicators, independent trust custody, clear severe-defect taxonomy, handling of "not visible"/"not inspected" states, and negative controls. Do not claim it has been run on actual professional cases.
3. In parallel, harden model-evidence mapping to individual original image/media IDs rather than only the entire case digest, and expand real-browser stress/accessibility checks for larger Option 2 reports.
4. Only consider the DeepSeek/Qwen candidate after verifying multimodal runtime/licensing and comparing it against identical blinded professionally labeled cases. Do not install or activate solely because the model was recommended.
5. Maintain `main`, `PAUSE_AUTONOMY`, and zero customer release, and record every commit/test result and remaining blocker for future chats.
