# M5 V2 — GitHub engineering, versioned synthetic examples and report reproducibility

**Date:** 2026-11-04. **Branch:** `home-inspection-development`. **Main and `PAUSE_AUTONOMY`:** unchanged. **Client release:** BLOCKED.

## Alignment with the approved original Milestone 5

Original Milestone 5 is **GitHub engineering and maintenance**: automated regressions, versioned training/synthetic examples, inspection benchmarks, quality gates and reproducible Option 2 report rendering. The separately committed `CHECKPOINT_M5_PILOT_READINESS_V1.md` cohort-planning code supports eventual field trials, **but it is not a substitute for this original scope**. A real professional pilot and legal signoff remain separate later gates.

## New additive repository engineering increment

1. `examples/versioned_fixture_manifest_v1.json` pins Git blob identities of four **public-safe** synthetic project/reference/generator sources and their classifications. Any change requires an intentional new manifest version/pin. The validator refuses missing/extra examples, symlinks, changed bytes, and a synthetic property represented as real even if re-pinned.
2. `scripts/m5_release_quality_gate.py` generates source diagrams in two separate clean temporary directories, renders the same Option 2 editorial report twice, rasterizes **every** PDF page, extracts every page's text and compares the complete pixel/text hashes. PDF metadata differences are excluded, not visual/text differences. Blank/bad pages fail. No customer media or trained model inference is used.
3. `tests/test_m5_release_quality_gate.py` covers the genuine repeated render and adversarial manifest tampering, missing examples, false release claims, and re-pinned false provenance.
4. `.github/workflows/home-inspection-m5-quality.yml` runs the manifest quality gate, two-build report replay, focused tests and tracked-source cleanliness on the development branch. The inherited offline suite continues as its own required job. Both workflows have read-only repository access, no customer data or model download.
5. V10 checkpoint now records the verified source-code regression: **1,058/1,058** offline tests on commit `f4a5ef1a32b3bfb31013696600f72d52a2a46d71`, [run 41817691316](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41817691316). M5 V1 1,075/1,075 tests on `e66e46b02b31fadfcf9675b39666c53059eed7d1`, [run 41818353256](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41818353256).

## Acceptance review

**V2 tests and dedicated GitHub workflow status: PENDING** until the exact new commit finishes. Do not replace this status with a guessed success. The synthetic fixture content, structural report completeness and deterministic raster checks are software QA and do not imply professional accuracy, actual inspection coverage or real-world photo authenticity. A changing dependency or different operating system may alter raster bytes; rerun on the pinned CI environment before changing baselines.

**Milestone 4 residual production blockers:** independent professional trust authority/credentials; externally authenticated evaluation pins and original-media custody; real consented source photos/video; independent severe-defect labels; held-out ≥100 real cases, ≥30 critical defects, all 13 systems and residential/commercial coverage; zero missed major/critical findings; ≥95% precision; ≥10 clean case/image controls and ≥10% clean cases; independent qualified signoff. No real photos, labels or clients appear in Git; real defect accuracy remains untested. The experimental DeepSeek/Qwen candidate stays research-only.

**Milestone 5 remaining operations:** maintain reproducible dependency/asset baselines and evidence artifact retention, review expanded 13-system regression coverage, enforce appropriate branch review/check requirements, demonstrate private real data isolation and recovery, and evaluate genuine model quality when professionally authorized. Never describe this checkpoint as a production inspection approval.
