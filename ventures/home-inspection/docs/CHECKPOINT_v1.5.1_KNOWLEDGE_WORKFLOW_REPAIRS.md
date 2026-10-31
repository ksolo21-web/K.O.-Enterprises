# v1.5.1 — Knowledge-to-workflow repairs

Date: 2026-10-31. Base: `594630f0131a156c460c79b9b64d2eddff81380f`, branch `home-inspection-development`.

## Authorized requirements

The owner requested fixes for three defects identified during the knowledge-base review: prediction-level false-positive accounting, the v7 benchmark's obsolete pass-status check, and hazard/specialty tasks that were indexed but not assigned through the inspection workflow. Preserve the current v2–v7 knowledge work, approved Option 2 reporting, source custody, T07/T08 ownership, independent review and human release gates. This is source remediation; no runtime installation, model invocation, customer upload, paid operation or pause removal is authorized or performed here.

## Resulting behavior

1. **Every prediction is scored.** Only an independently verified, correct-system, one-to-one label match earns credit. An extra unverified or wrong-system prediction counts as a false positive even when it names an already detected label. Exact boolean matching decisions are required. Duplicate valid matches still fail validation; critical misses still block. Outputs expose accepted-prediction and total-prediction counts.
2. **Metric pass reaches external audit.** Scorer and wrapper share `METRIC_THRESHOLDS_MET_EXTERNAL_REVIEW_PENDING`. Meeting the numeric gates advances to `ADJUDICATION_EVIDENCE_AUDIT_REQUIRED`; it never authenticates credentials, establishes field accuracy or authorizes release.
3. **Knowledge creates assigned, evidence-bound work.** A scoped case receives 13 hazard tasks plus two residential specialties (fireplace/hearth and garage door), or the separate commercial fire/life-safety specialty. Existing specialist owners receive the tasks; specialty work routes to T05. Relevant task instructions and IDs enter actual specialist image prompts. Missing views remain assigned open work, rather than fabricated findings.

Task identities bind project, explicit residential/commercial scope, inspection date, policy/catalog digests and source-media provenance. Canonical plans are rebuilt, so cached completion, deletion, changed scope, stale sources or altered catalogs cannot silently satisfy a task. Source observations and tasks share the bounded Q03 ledger, with deterministic links in both directions. Writer memory keeps prior claims; coverage tasks have their own prompt cards.

Q02 makes an actual image-provider call for each applicable task/photo pair, including when the writer proposed no findings. Every saved assessment must match task and source hashes. Tasks without a photo receive a deterministic missing-evidence disposition, explicitly **not** a model review. Q03 reconciles every ledger entry; even `distinct` preserves missing-view and physical-check holds. A visually useful photo is neither proof of hazard absence nor completion of a physical test. Existing report status/blocker logic receives these holds; the Option 2 layout is unchanged.

## Scope and use

Set `property.building_type` to `residential`, `residential_one_two_family`, `commercial`, `commercial_general` or `commercial_pca`; alternatively explicitly declare `property.inspection_scope` as residential/commercial with an unknown building type. Conflicting declarations and unsupported building types are rejected. Unknown scope is never treated as residential and remains held for model workflows.

Photo area labels `fireplace`, `hearth`, `chimney`, `garage`, `garage_door`, `commercial_fire`, `commercial_egress` and `life_safety` route specialty evidence. Generic interior photos do not establish fireplace or garage coverage. Labels dispatch work; they do not prove an item is present or inspected.

Existing specialist-plan/run, Q02 review and Q03 adjudication interfaces carry the new work. The local live-trial script can request coverage review even with no proposed claim; this change has only controlled-provider tests, not a new live trial.

## Validation

Baseline: 552 tests, two pre-existing Q02 prompt parsing errors. Policy text had been appended after the final `CLAIM DATA` JSON; moving policy before that final JSON restores the contract without weakening tests.

First combined implementation check: **575/575 tests passed**, 34.269 seconds. This includes 23 new algorithm/controlled-provider regressions covering the two scoring failures, a passing metric cohort reaching external audit without release, false-positive precision failures, specialty routing, all hazard assignments, scope separation/conflicts, actual image calls, zero-call missing evidence, review budgets, stale/duplicate/unknown review records, bidirectional ledger links, retained Q03 physical holds, cache deletion, source/scope changes and unchanged input documents.

Benchmark test metadata is fabricated solely to exercise algorithm branches; it is not a collected, consented or professionally adjudicated field cohort. Controlled image providers and Q03 replies are not live model performance evidence.

Independent critic `/root/ollama_gate_critic` separately passed **23/23 targeted tests** and **575/575 full-suite tests**, with the full run completing in **33.934 seconds**. Final verdict: **9.7/10; all three implementation fixes pass; no remaining mandatory blocker found**. The critic performed no edits or live model calls. This score covers implementation and controlled tests only.

Prepublication integrity readback found all 175 baseline product files present, with all knowledge catalogs/modules/tests preserved byte-for-byte. Only the intended eight existing files and three new source/test/checkpoint files are included; generated local media fixtures are excluded. Development head remained at the stated base before commit preparation. Main remains `61ca9202fbfe45aae4a0ed29326df44cf7b25c9e`; the root pause blob remains `37455fd13813683bb0169d36cb24b86a07094aa7`.

## Remaining limits

Physical task checks intentionally stay open: there is no authenticated qualified-inspector task-completion or not-applicable signoff flow in this prototype. This repair exposes that outstanding work and cannot produce a fully released customer inspection by itself. Explicit evidence-backed completion and scoped exclusions need a separate implementation and professional review.

Bounds remain: 24 specialist jobs per batch, 20,000-byte complete specialist prompts, 128 combined ledger entries and 60,000 serialized Q03 context characters. Q02 allows at most 48 combined claim/task-photo image assessments per batch and fails before provider access if that budget is exceeded. Larger-case batched reconciliation is outstanding; nothing is silently dropped.

No stronger model has been promoted. Live observation quality, autonomous useful zoom selection and actual model Q02/Q03 performance remain unproven. Qualified-inspector evaluation on consented locked holdouts remains mandatory. Root `main`, `PAUSE_AUTONOMY`, workflows and knowledge catalogs are unchanged by this repair.
