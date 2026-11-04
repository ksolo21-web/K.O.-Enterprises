# M5 V7 — actual GitHub PR red/green + required-check path filter repair

**2026-11-04 · PR #24** https://github.com/ksolo21-web/K.O.-Enterprises/pull/24  
**Source:** `home-inspection-m5-pr-validation-v7`  
**Base:** `home-inspection-development`  
**Draft, NOT MERGED, no independent review. Customer release BLOCKED.**

## Rehearsal against real GitHub Actions

### Initial positive control — VERIFIED
- PR head `0f417b7df5a36cad1f4fb05c39dea8ae33ef9669`: harmless documentary-only checkpoint.
- [PR full regression 41836211539](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836211539): **1,130 / 1,130 PASS**, plus M3 checks and integrity.
- [PR dedicated M5 41836212193](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836212193): **69 focused tests PASS**, nine synthetic serious-defect scoring contract scenarios, 16-page synthetic PDF and recovery preflight.
- [General repository CI 41836211806](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836211806): success.
- **PR artifact isolation verified:** M5 upload step `skipped`, **zero GitHub artifacts** on this PR run, despite synthetic local build/restore.

### Deliberate negative control — VERIFIED
- PR-only head `0dd2b3d5bd746a2d62a71afd90ffed5b36f64930`: changed exactly the `git_blob_sha1` for `inspection_engine/serious_defect_benchmark.py` to `0000000000000000000000000000000000000000` in the **synthetic change registry**. The source module and `PAUSE_AUTONOMY` were NOT modified.
- [PR dedicated M5 41836890445](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836890445): **EXPECTED FAILURE**, specifically `M5_CHANGE_GOVERNANCE_BLOCKED` due to protected source SHA disagreement. Subsequent report/golden checks were skipped; `customer_release_allowed=false`.
- [PR full regression 41836890496](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836890496): **EXPECTED FAILURE**, 1,116 completed tests with safety-check errors and dependent recovery setup rejected by the identical fingerprint mismatch. This deliberately invalid branch revision was **never merged**.
- [General CI 41836890513](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41836890513): success—**general CI alone cannot be the required home-inspection acceptance check**.

### Recovery and V7 code fix — CI PENDING
- Restore approved registry byte-for-byte (Git blob `65d8a0eac3fc9e3074274bf552584350176ed6e3`) in a new, forward-only PR commit.
- Remove `on.pull_request.paths` filters from **both required inspection workflows** so a required status check will run for *any PR targeting `home-inspection-development`*, including root-only changes. Keep the existing `on.push.paths` optimization and development branch targeting.
- Strengthen `tests/test_m5_workflow_pr_controls.py` to reject restored PR path filtering, wrong base and loss of read-only/source restrictions, while preserving identical job names.
- Include [GitHub branch-ruleset administrator runbook](GITHUB_BRANCH_PROTECTION_RUNBOOK_V7.md) with exact check jobs `m3-v8-regression` and `synthetic-quality`. These settings still require an actual administrator and independent reviewer.

The green recovery must pass both real PR workflows and upload no artifact. No merge without a genuine independently authorized review; if that is not available, keep the PR draft and blocked. Do not claim branch protection is installed.

## Technical limitation

All tests use public-safe synthetic inputs and declared reviewers only. This rehearsal verifies **software enforcement behavior**, not defect recognition accuracy, authentic customer consent, real professional reviewer identity or external custody. Real heldout 100+ case/30+ critical and both scopes/13 systems, zero missed major/critical, ≥95% precision and professional release remain untested. `main`, `PAUSE_AUTONOMY` and M4 V10 private custody checks must remain unchanged.

Official GitHub required-check filter guidance:
https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks
