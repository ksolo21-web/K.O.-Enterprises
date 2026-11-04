# Home Inspections — Milestone 5 original engineering acceptance matrix (V8)

**2026-11-04 · `home-inspection-development` · software engineering only · customer release BLOCKED**

This tracks the *original approved Milestone 5*: GitHub-backed maintenance, regression automation, versioned public-safe synthetic examples, defect benchmark safeguards, deterministic Option 2 report production and recovery. It does **not** substitute proposed pilot paperwork for engineering work or pretend simulated cases are field validation.

## Dependency-aware mandatory engineering acceptance

| Requirement | Objective evidence / acceptance criterion | State before V8 CI |
|---|---|---|
| A. Reproducible offline regression | Full Python inspection test suite + legacy M3 regressions pass on exact commit; no trackable source drift | V7 baseline 1,132 tests verified; V8 pending |
| B. Versioned synthetic training/example sources | Exactly four pinned publicly safe example/generator sources; synthetic flags cannot turn into real consent; SHA violations block | Implemented, V8 retest pending |
| C. Defect benchmark safeguards | Nine matrix scenarios, 100 invented properties, 90 simulated defect labels (30 critical), all 13 systems, commercial/residential, 10 clean case/media controls; zero tolerated missed critical/major, precision threshold 95%, reject leakage | Implemented; not actual model accuracy |
| D. Report reproducibility | Independently regenerate 16-page editorial Option 2 PDF twice, compare every page's pixels/text to a previous golden fingerprint, reject dependency drift | Implemented, V8 retest pending |
| E. Source change control | Compare 10 protected inspection safety modules and root `PAUSE_AUTONOMY` to stored Git byte pins, reject unregistered drift | V7 live red/green GitHub PR passed |
| F. Synthetic recovery | Create bounded five-member synthetic ZIP, verify ZIP safety and exact source/content fingerprints, restore externally to new folder; no customer data | Implemented, V8 retest pending |
| G. Audit-friendly CI handoff | NEW V8 JSON receipt binds exact checked-out commit, CI event/run ID **as declarations**, source SHA256, 9-scenario matrix, pinned PDF fingerprint and actual archive bytes; verify independently before upload; refuse release flags and ZIP corruption | V8 CI pending |
| H. PR workflow trigger safety | M3 and M5 GitHub Actions run on all PRs targeting development; PRs must never publish recovery artifacts; code remains read-only; intentional failure/recovery demonstrated | V7 passed in PR #24; merged |
| I. Default safety | `main` unchanged, `PAUSE_AUTONOMY` matches approved root pin, no real evidence/secrets in public artifacts, no customer release | Enforced in code; owner review remains required |

## Separate mandatory governance and field-acceptance gates — NOT complete

- The development branch currently reports **unprotected**; an authorized GitHub admin must enable and independently test *required* check contexts `m3-v8-regression`, `synthetic-quality`, and at least one genuine separate reviewer with rejection of stale reviews/direct bypass. Read [V7 setup runbook](GITHUB_BRANCH_PROTECTION_RUNBOOK_V7.md).
- The receipt is **not signed by an independent external authority** and cannot authenticate a malicious commit owner or prove a run existed outside its GitHub Actions link.
- No real homeowner permission, original media chain of custody, authenticated inspector credentials, cross-property isolation, or independently adjudicated *real* holdout cases have been verified. The benchmark minimum remains **≥100 consented real cases, ≥30 critical findings, 13 systems, residential + commercial, ≥10 negative cases + ≥10 negative media, ≥10% clean cases, zero missed major/critical, and ≥95% human-verified precision**. Independent qualified human approval and legal/insurance coverage are separate.
- Therefore no field pilot or customer release may be enabled or described as validated. The company may prepare for professional trials only once lawful privacy, insurance and credentials are independently validated.

## V8 acceptance decision protocol

**PASS for original engineering implementation** only if V8 exact-commit `m3-v8-regression` and `synthetic-quality` GitHub jobs pass, including 18+ new adversarial receipt tests, receipt create + verify, report/golden baseline, archive restore and restricted upload. Independently inspect the published artifact to confirm both ZIP and receipt, matching ZIP SHA256. Ensure `main` and `PAUSE_AUTONOMY` remain unchanged.

**STOP / not accepted** for failing or untested mandatory checks. A 10/10 for implemented synthetic software checks can never override the unverified field/legal/governance blockers. Keep Milestone 5's actual *deployment readiness* unapproved until these distinct conditions are satisfied.

## Next executable step

Run CI on a V8 PR, evaluate failures, fix and retest. Only after successful run consider merging the reviewed *synthetic-only engineering* changes into `home-inspection-development`. Preserve exact job logs/IDs in the checkpoint; avoid inventing completed results.
