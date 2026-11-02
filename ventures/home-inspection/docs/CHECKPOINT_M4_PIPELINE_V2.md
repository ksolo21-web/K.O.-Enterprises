# M4 checkpoint V2 — integrated private case pipeline (2026-11-02)

**Repository**: `ksolo21-web/K.O.-Enterprises` on the existing `home-inspection-development` branch. This file updates `CHECKPOINT_M4_PRIVATE_ASSEMBLY_V1.md` without superseding Milestone 1–3 restrictions. No real customer files or installed models were processed in this milestone increment.

## Scope and implemented code

1. `inspection_engine/m4_pipeline.py` adds opt-in preparation and four sequential stages: specialist source-photo proposals, Q02 original-image technical challenge, Q03 complete-ledger reconciliation, private Option 2 draft. Each stage persists hash-bound records under a separate restricted workspace. Input source and original bytes are revalidated, all stages are explicit and unmoved completed stages are not re-run. If inference or filesystem operations fail after the stage marker is created, that stage is held for **manual audit**, not automatically retried.
2. `inspection_engine/m4_assembly.py` takes an optional source-evidence root when rendering separately staged records; the original source project is never replaced. M4 draft receipts contain complete source media and crop metadata, unverified evidence classes, all original findings/observations/equipment/limitations, exact Q02/Q03 records and hashes, holds, and strictly false release claims.
3. `inspection_engine/report.py` retains the approved Option 2 cover/overview while adding, **only when requested by private M4 assembly**, a paginated, unabridged original-media and native-crop register to the full-record appendix. Raw videos without reviewed frames are listed as unreviewed; listing an asset does **not** mean its contents were visually assessed.
4. `scripts/m4_case_pipeline.py` provides separate operator-invoked commands. Inference subcommands require `--authorize-local-inference` and an **already-installed** loopback Ollama model. The CLI has no download, schedule, public cloud, approval, signing or delivery function. It was not used for real model execution in this work.
5. `tests/test_m4_pipeline.py` and `tests/test_m4_private_assembly.py` cover synthetic source custody, stage sequencing, checkpoint reuse, distinct role-provider IDs, Q03 holds, interrupted inference, output hashes, private workspace access, complete evidence register, and release denial.

## Operator commands (documentation only — no models were executed)

From `ventures/home-inspection`, use only a private, non-Git workspace:

```bash
python -m scripts.m4_case_pipeline prepare /private/case/case.json --workspace /private/m4-run --media-ids P0001
python -m scripts.m4_case_pipeline status --workspace /private/m4-run
# Explicit manual local-model use, only after qualified operator authorization:
python -m scripts.m4_case_pipeline specialists --workspace /private/m4-run --model ALREADY_INSTALLED_WRITER --authorize-local-inference
python -m scripts.m4_case_pipeline q02 --workspace /private/m4-run --model SEPARATE_INSTALLED_Q02 --authorize-local-inference
python -m scripts.m4_case_pipeline q03 --workspace /private/m4-run --model SEPARATE_INSTALLED_Q03 --authorize-local-inference
python -m scripts.m4_case_pipeline render --workspace /private/m4-run
```

Unrouted media and missing views remain recorded as gaps; photos extracted from video must pass existing provenance checks first. Separate provider IDs are not proof of independent runtimes or a real successful AI inspector.

## Acceptance checklist

- [x] Code committed to the dedicated development branch with original M3 and `PAUSE_AUTONOMY` preserved.
- [x] All source photos, unselected video IDs, source hashes, timestamps and crops retained in internal ledger, and full media register added to private PDF.
- [x] Distinct Q02/Q03 stages and explicit saved review states; unresolved Q03 findings remain held, not released.
- [x] No customer dispatch or qualification / safety / code-compliance claim from visual evidence.
- [x] Interrupted stages fail closed and never silently re-invoke an inference provider.
- [ ] **Final latest-commit CI result**: inspect the matching GitHub Actions run and fix failures; an earlier run found a stage-order assertion and was corrected before this checkpoint.
- [ ] Actual rendered PDF image review across every page, desktop and mobile reading sizes; text extraction tests alone do not certify visual layout.
- [ ] Genuine separate-runtime model evaluation on authorized real evidence; held-out qualified-inspector measurements remain outstanding.
- [ ] Authenticated qualified-human signoff, secure report distribution and verified access-control policies remain unimplemented.
- [ ] Full future stage-recovery operator interface for interrupted model calls remains blocked by design until side effects can be audited safely.

## Release disposition

**INTERNAL ENGINEERING / SYNTHETIC TESTS ONLY. NOT PRODUCTION APPROVED.**

Do not call Milestone 4 complete merely because synthetic unit tests pass. The next critical path is CI diagnosis, cross-page PDF layout evidence, secure qualified-human review and controlled inspector-labeled validation. The original professional validation and licensing boundaries remain in force.
