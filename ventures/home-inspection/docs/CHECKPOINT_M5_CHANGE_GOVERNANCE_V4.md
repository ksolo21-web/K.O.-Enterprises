# Home Inspection M5 V4 — safety-source change detection

**Date:** 2026-11-04. **Branch:** `home-inspection-development`. **Release status:** BLOCKED.

## Scope and preserved baseline

V10 original-byte private media checks and V9/V8 evidence-grounded serious-defect gates, V7 trust history, V6 issuer receipts, human signoff, M5 V3 versioned four synthetic inputs and pinned 16-page PDF rendering remain unchanged. Previous current-head validation: 1,085/1,085 inspection tests passed at commit `c7d199d7fc74dab0518ca7d02afc84f3606bc7f8`, [GitHub Actions 41820641712](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41820641712), with separate [M5 quality success 41820643013](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41820643013).

## Addition

- `examples/m5_safety_contract_registry_v1.json` stores the frozen exact Git blob SHA1 of 10 safety-critical source modules (benchmark V8/V9/V10, credentials, signed human review, governance, issuer receipts, pipeline/workflow) and the root `PAUSE_AUTONOMY` Git blob.
- `scripts/m5_safety_change_gate.py` is **offline, read-only**: validates exact file inventory and order, duplicate-key-safe bounded JSON, regular files and source fingerprints, source integrity, pause marker and release-blocked state.
- `tests/test_m5_safety_change_gate.py` includes 13 synthetic adversarial cases: changed technical/human gates, removed/reordered sources, missing/altered autonomy marker, symlink, malformed/duplicate registry, false release, wrong branch and a **deliberate repin** test documenting that self-updated registry entries are not independently authorized.
- `.github/workflows/home-inspection-m5-quality.yml` runs the safety-source gate before synthetic PDF acceptance and new tests with read-only credentials.

**Mandatory limitation:** this is a *source change detector*, not tamper-proof governance or independent review. A person with write permission may update a protected module and its registry in the same commit; branch rulesets, distinct mandatory reviewer and other external controls are NOT deployed or verified. Do not claim the 10 checked modules are vulnerability-free or that the signatures are independent. Updating a safety module requires documented impact, human code review by a genuinely independent qualified person and full CI; never silently re-pin on failing checks.

## Acceptance

V4 CI **VERIFIED** on commit `af9d6b83cc9b6a4da8a4915435dc4016fccb4c1b`: [full 1,098/1,098 offline tests](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41828210590) passed with compilation, M3 checks and source integrity; [dedicated M5 governance/visual quality run](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41828210561) also passed. This must not alter `main`, the root pause marker, inspection benchmark thresholds, heldout media requirements or disabled customer delivery.

M4 production acceptance remains BLOCKED for real professional identity and issuer authority, externally controlled media/custody pins, consented professionally labeled 100+ heldout cases/30+ critical defects across all 13 systems and both scopes, no missed major/critical labels, ≥95% human-verified precision, reviewed clean controls, and genuine authorized human release. No actual real-world accuracy has been demonstrated.

## Next engineering checkpoint

M5 V5: build a bounded, synthetic-only reproducible evidence package containing original synthetic PDF, pinned source/renderer receipts, and hash verified restore. Prohibit customer data or any media import in artifact publishing. Check retention and recovery via adversarial tests and CI. This is only test-evidence recovery, not a recovery guarantee for private field inspections.
