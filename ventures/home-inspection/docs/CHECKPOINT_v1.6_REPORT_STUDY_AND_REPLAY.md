# v1.6 — M3 report-study foundation and M2 replay preparation

2026-10-31. Base commit `cb1a65084efe507c6cbe891996b58fd65059d8c0`, branch `home-inspection-development`.

The owner agreed to pursue the live M2 workflow while building M3's report-import/correction foundation. Current work delivers the executable local foundation and controlled full-chain replay harness. It does **not** close M2 or complete M3.

## Implemented requirements

- Local bounded PDF/TXT reference import: complete extracted text within limits, exact source/case/partition identity, page warnings and explicit declarations. Text/images/handwriting limitations stay visible; no OCR or arbitrary-report understanding is claimed.
- Explicit reference quote/page/offset annotations, lossless comparison ledgers, ambiguous-match preservation and every-row correction capture. Source snapshots and original media custody must still match. Human declarations are not authenticated qualifications or defect truth.
- Local immutable partition registry for declared case/source/normalized-text aliases, with holdout lesson exclusion; limited scope documented in `M3_REPORT_STUDY_FOUNDATION.md`.
- Quarantined correction candidates only: no prompt/model updates, training, operational facts or report release. Full ingestion/semantic matching, authenticated review, evaluation/promotion, rollback and durable corpus governance remain open.
- Synthetic M2 harness adds actual Q03-provider invocation, safe raw/structured response audit, source-bound reconciliation, held Option 2 PDF and hash manifest. Three installed digest-distinct models, explicit local opt-in, bounded call counts and a 30-minute CLI deadline. Existing two-role trial remains backward compatible; optional explicit scope enables the new hazard/specialty tasks.

## Verification

**617/617 final full-suite tests passed**, 42.109 seconds, including all 575 prior tests and 42 new tests (34 report-study, eight replay). The earlier 616-test check passed before the final source-custody repair. Parser review found and repaired unbounded stderr capture and race-prone whole-file reads. Project JSON and exported claim/output bounds were also enforced. A final source-custody race was repaired by feeding the PDF worker the exact bounded, hashed bytes via stdin instead of reopening a mutable path. An A-to-B-to-A replacement therefore cannot bind B text to A bytes. FIFO inputs are rejected without blocking. No truncation or relaxed safety gate was used to pass.

A separately retained controlled replay completed source-linked zoom/still/Q02/Q03/report integration with **17 Q03 decisions**, an `ADJUDICATION_HOLD`, and a 13-page explicitly unreleased PDF. PDF SHA256: `b4a9feb13fe9d9edff078859dc1be2bda749222a907511b7b2b52c020464adec`. All 13 pages were rasterized and visually inspected in a contact sheet; no clipping or overflow observed. This is fixture-provider evidence, not live AI performance. The Option 2 layout code is unchanged.

Genuinely separate critic `/root/ollama_gate_critic` independently passed **34/34 report-study tests** (0.845 seconds) and **617/617 final full-suite tests** (41.968 seconds). Its own A-to-B-to-A replacement probe retained both A's source hash and A's extracted text; FIFO rejection was immediate. It verified all 56 controlled-replay manifest hashes and inspected all 13 report pages plus evidence/ledger closeups. Final score: **9.7/10**, no remaining mandatory code blocker. This score covers the source foundation and controlled synthetic integration, not live M2, full M3 or field accuracy.

## Blockers, dependencies and next action

Local runtime preflight: Ollama absent on PATH and loopback connection refused. No live generation was made. No evaluated Q03 model is selected. Root `PAUSE_AUTONOMY` remains intact; no remote execution trigger was added. Prepare the exact evaluated models, hardware/context/call budget and authorized run envelope described in `M2_A09_RECONCILIATION_PREPARATION.md`, then collect actual model outputs and independent quality review.

M3 can now ingest authorized local text-bearing reports and capture comparisons/corrections. It cannot autonomously understand all report pages or learn from unreviewed material. Real-case consent/provenance and qualified field labels are not present. Customer release remains blocked.

Existing knowledge catalogs, prior source, approved Option 2 reporting, T07/T08 ownership and previous 575 regression checks are preserved. Main, root pause and workflows must remain unchanged. New source-only files and synthetic test metadata belong in GitHub; private report/registry/correction data do not.
