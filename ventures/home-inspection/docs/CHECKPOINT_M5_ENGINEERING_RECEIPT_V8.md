# M5 V8 checkpoint — auditable synthetic engineering receipt and acceptance matrix

**2026-11-04 · development target `home-inspection-development` · PR implementation under test.**  
**Customer release:** BLOCKED. **Real inspection accuracy:** untested.

The previous PR #24 was successfully merged at `d528388f1c03bd39fc100117728e5fbebe0ddc0d`, and [post-merge M3 run 41840060056](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41840060056) passed **1,132/1,132** tests; [M5 synthetic quality run 41840060038](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41840060038) passed 69 focused tests. V7's older checkpoint describing the PR as unmerged is a historical pre-merge snapshot, not current branch status.

## V8 addition: one bounded receipt tied to the CI run

- `scripts/m5_engineering_receipt.py`: an intentionally **unsigned, synthetic-only** CI receipt. On create **and** verify it rechecks the exact Git checkout SHA, declared CI event/run ID, ten protected sources and root pause pin, four versioned example sources, five ZIP members, pinned 16-page PDF pixel/text fingerprint, nine benchmark scenarios and the actual ZIP SHA256. It records raw SHA256 of the three source manifests/baseline files. Entire receipt stays outside the Git checkout.
- `tests/test_m5_engineering_receipt.py`: 18 focused adversarial tests against archive tampering, fake real-world accuracy/customer release, source or case-coverage downgrades, incorrect commit/event/run ID, duplicate JSON fields, noncanonical JSON, symlinked receipt, overwrites and attempted Git-checkout output. Tests use *mocked* expensive render/recovery functions; GitHub CI executes real render/recovery and actual SHA checks.
- `.github/workflows/home-inspection-m5-quality.yml`: creates then verifies receipt from actual `GITHUB_SHA`, `GITHUB_EVENT_NAME` and `GITHUB_RUN_ID` after prior restore; uploads both ZIP and receipt in the seven-day synthetic artifact **on push only**. On PR, upload remains skipped.
- [M5 engineering acceptance matrix](MILESTONE_5_ACCEPTANCE_MATRIX_V8.md) now distinguishes original M5 engineering scope from external field/governance acceptance, and lists exact pass evidence required.

## Scope boundaries

The receipt is **not externally signed** or backed by protected repository rules, and CI-provided run identity is a declaration cross-checked locally, not a third-party attestation. In particular, source hashes and their registries are written by the same repo author; they detect accidental or unauthorized source drift but not a malicious authorized committer. No real model inference, professionally labeled field evaluation, genuine credential validation or client report issuance is performed.

**At this checkpoint the engineering implementation is staged, not yet accepted:** obtain PR CI evidence, fix any red test, merge only the approved synthetic engineering changes, then verify full CI and actual published artifact on the final development head. Maintain `PAUSE_AUTONOMY`, `main` and customer-release restrictions.

## External acceptance blockers unchanged

Owner-level branch rules and genuinely independent PR reviewer, professional inspector credentials/insurance, lawful private real source-media custody, and independent ≥100-real-case heldout serious-defect scoring and signoff. See V7 [branch ruleset setup](GITHUB_BRANCH_PROTECTION_RUNBOOK_V7.md). Never call these complete from synthetic CI.
