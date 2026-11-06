# CE-4C — Repository Execution-Surface Inventory and No-Go Report

**Checkpoint:** 2026-11-06 · **Implementation:** `src/company_os/release_surface_audit.py` and `tests/test_release_surface_audit.py`.  
**Status:** Static repository inventory. **Not a certified no-bypass proof, production readiness, or a real external-system audit.**

## Purpose

The company-wide release prerequisite cannot be accepted merely because a Python policy checks launch actions. An email client, payment provider, GitHub deployment workflow, shell script, API, hosted service or future plugin could execute outside the protected controller. This scan inventories current **repository-local executable surfaces** to make that remaining gap reviewable.

The scanner reads bounded UTF-8 source/workflow files under `src/`, `products/`, `scripts/` and `.github/workflows/`. It looks for candidate outbound HTTP clients, raw sockets, messaging/email and payment libraries, process execution, remote-deployment commands and GitHub Actions steps. It emits a SHA-256 manifest, file counts and line-number indicators. It does not print file bodies or secrets. These are *heuristics*, not proof of execution or complete discovery. Files outside the repository and dynamically loaded connectors are necessarily outside the scan.

For each candidate, the report records whether a policy-call string appears. **A string match is NOT proof of atomic authorization**; all candidates remain `MANUAL_EXECUTOR_BOUNDARY_REVIEW_REQUIRED` until an actual independent reviewer tests each protected path. Unknown actions and future scripts require review.

## CI safety contract

The GitHub CI step executes:

```bash
python -m company_os.release_surface_audit --repo-root . --expect-not-ready
```

This only returns test success when the source tree still contains `PAUSE_AUTONOMY`, the literal `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`, and the report explicitly says `BLOCK_REQUIRED_INDEPENDENT_EXECUTION_REVIEW`. It fails when either source-tree safety requirement is absent or changed. Normal CLI invocation returns nonzero (not production-ready). No CI result can grant release permission.

### Security limits

The inventory can miss obfuscated code, runtime imports, code generated after CI, network side effects inside external dependencies, manual browser actions, GitHub administrative paths, connected apps, payment dashboards or credentials on hosts outside this repository. Branch protections can be changed by authorized administrators; a malicious PR that modifies both code and CI could evade these source checks without an independently enforced GitHub ruleset. The scan is **evidence for a future independent no-bypass review**, not a substitute for one.

Unit tests challenge unguarded HTTP/email signals, false textual policy references, workflow deploy commands, symlink escapes, oversized source code, missing pause and flipped lock, hidden secret files, deterministic hashes, and the difference between a completed scan and a release permit.

## Remaining production acceptance gates

- **CE-1:** Genuine lawful original-source retrieval, authenticated competitor/issuer identity, complete addenda and contradiction investigation, original buyer payment/demand evidence, independently verified original snapshots.
- **CE-2:** Approved protected always-running host, separate identities and secret custody, bounded operator cost, automatic boot/restart/failover, nonlocal external monitor, private durable ledger and rollback/incident evidence.
- **CE-3:** An actually separate authenticated reviewer must inspect **original** evidence and all PDF renderings, test all twelve gates, score strictly above 9.0, preserve counterevidence and audit.
- **CE-4:** Inventory and enforce **every real connector/executor**. Integrate protected atomic release controller, real source/critic evidence, exact CEO scope, privacy/consent/client eligibility, branch ruleset and external immutable audit. Prove there is no bypass.
- **CE-5:** CEO approval and observed production deployment/recovery in the approved environment; independently validated health/operating evidence. No commercial activation while root pause and hard lock remain.

**Next action after CI:** Inspect actual candidate files and untrusted external paths with a genuinely separate reviewer; progressively bind real executors to an authenticated controller. A fully green offline CI suite still does not satisfy CE-1–CE-5.
