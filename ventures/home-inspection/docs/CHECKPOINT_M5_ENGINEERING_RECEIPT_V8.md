# M5 V8 checkpoint — auditable synthetic engineering receipt and acceptance matrix

**2026-11-04 · development merge `ef777181dc0a0680b88050ea119a1cfa3b507c55` · original M5 engineering tests verified.**  
**Customer release:** BLOCKED. **Real inspection accuracy:** untested.

The previous PR #24 was successfully merged at `d528388f1c03bd39fc100117728e5fbebe0ddc0d`, and [post-merge M3 run 41840060056](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41840060056) passed **1,132/1,132** tests; [M5 synthetic quality run 41840060038](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41840060038) passed 69 focused tests. V7's older checkpoint describing the PR as unmerged is a historical pre-merge snapshot, not current branch status.

## V8 addition: one bounded receipt tied to the CI run

- `scripts/m5_engineering_receipt.py`: an intentionally **unsigned, synthetic-only** CI receipt. On create **and** verify it rechecks the exact Git checkout SHA, declared CI event/run ID, ten protected sources and root pause pin, four versioned example sources, five ZIP members, pinned 16-page PDF pixel/text fingerprint, nine benchmark scenarios and the actual ZIP SHA256. It records raw SHA256 of the three source manifests/baseline files. Entire receipt stays outside the Git checkout.
- `tests/test_m5_engineering_receipt.py`: 18 focused adversarial tests against archive tampering, fake real-world accuracy/customer release, source or case-coverage downgrades, incorrect commit/event/run ID, duplicate JSON fields, noncanonical JSON, symlinked receipt, overwrites and attempted Git-checkout output. Tests use *mocked* expensive render/recovery functions; GitHub CI executes real render/recovery and actual SHA checks.
- `.github/workflows/home-inspection-m5-quality.yml`: creates then verifies receipt from actual `GITHUB_SHA`, `GITHUB_EVENT_NAME` and `GITHUB_RUN_ID` after prior restore; uploads both ZIP and receipt in the seven-day synthetic artifact **on push only**. On PR, upload remains skipped.
- [M5 engineering acceptance matrix](MILESTONE_5_ACCEPTANCE_MATRIX_V8.md) now distinguishes original M5 engineering scope from external field/governance acceptance, and lists exact pass evidence required.

## Scope boundaries

The receipt is **not externally signed** or backed by protected repository rules, and CI-provided run identity is a declaration cross-checked locally, not a third-party attestation. In particular, source hashes and their registries are written by the same repo author; they detect accidental or unauthorized source drift but not a malicious authorized committer. No real model inference, professionally labeled field evaluation, genuine credential validation or client report issuance is performed.

**V8 synthetic engineering verification complete (not production):** [PR #25](https://github.com/ksolo21-web/K.O.-Enterprises/pull/25) was merged at `ef777181dc0a0680b88050ea119a1cfa3b507c55`. [Post-merge full regression 41843236700](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41843236700) passed **1,150/1,150**, and [post-merge M5 quality 41843236203](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41843236203) passed **87 focused tests** plus nine matrix scenarios. The workflow created and verified the synthetic evidence receipt before uploading the GitHub QA artifact `13329503386`, expiring 2026-11-11. The actual downloaded outer ZIP contained exactly the five-member recovery ZIP and JSON receipt; byte hashes/CRC/member manifests agreed and the embedded 16-page PDF could be extracted. The GitHub runner's pinned dependencies proved PDF pixel/text fingerprint equality; a separate local runtime using different pypdfium2/pypdf/Pillow/reportlab versions re-rendered a different fingerprint, so **no claim of a matching independent local pixel baseline is made**. A 16-page visual contact sheet was reviewed; no page appears blank, truncated or omitted.

**Engineering acceptance decision:** PASS for original M5 *synthetic GitHub engineering* only. Reviewer governance, real model accuracy, authentic custody, legal/insurance and customer release remain separate unfulfilled gates. `main`, `PAUSE_AUTONOMY` and customer-release restrictions remain unchanged.

## External acceptance blockers unchanged

Owner-level branch rules and genuinely independent PR reviewer, professional inspector credentials/insurance, lawful private real source-media custody, and independent ≥100-real-case heldout serious-defect scoring and signoff. See V7 [branch ruleset setup](GITHUB_BRANCH_PROTECTION_RUNBOOK_V7.md). Never call these complete from synthetic CI.
