# v1.3 — Proposed GitHub CPU vision proof (not activated)

**Status: PREPARED, NOT EXECUTED. No live model inference has been verified.**

## Why this matters

The chat environment has ~5.8 GiB RAM and no Ollama installation/weights/GPU. GitHub's standard `ubuntu-24.04` runner currently advertises 4 CPUs and **16 GiB RAM for public repositories**. The two Ollama model downloads total roughly 5.6 GB of weights, so a disposable CPU runner is a plausible alternative **for a synthetic trial**, not a continuous inspection server. Performance and success are unknown until an actual run. Review provider quotas/terms before activation.

Sources (checked October 30, 2026):
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://ollama.com/library/qwen2.5vl
- https://ollama.com/library/granite3.2-vision
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

## What is staged

The repository root workflow `.github/workflows/home-inspection-live-synthetic-manual.yml` is a **manual-only proposal on the development branch**. It never responds to push, pull request, a schedule, or another automation. It uses read-only repository permissions, restricts itself to the exact development branch/repository, refuses the current `PAUSE_AUTONOMY`, and runs the existing fully synthetic acceptance harness. It does not load customer media or launch a product. It keeps model work loopback-only and uses a single loaded model at a time to reduce peak RAM. Synthetic evidence is saved as a short-retention GitHub Actions artifact only if executed.

## Current gates preventing execution

1. Root `PAUSE_AUTONOMY` is still active. **Do not bypass or remove it** without the owner's governance decision. The workflow checks it before any downloads.
2. A GitHub `workflow_dispatch` workflow must ordinarily exist on the **default branch** to be discoverable from the GitHub Actions UI. This workflow is on the development branch only, keeping `main` untouched. **Do not merge it to main without a separate owner decision.** GitHub's API/CLI behavior for branch-only dispatch may differ; no dispatch is represented as tested.
3. **Installer integrity addressed in v1.3.1, execution still unverified.** The proposed runner downloads the fixed Ollama **v0.40.13 Linux x64 release archive**, not a mutable installer script. It checks the published asset size and hard-pinned SHA-256 before extraction, then deletes the downloaded archive to save disk. The official release metadata was read October 30, 2026: https://api.github.com/repos/ollama/ollama/releases/tags/v0.40.13 . Published asset digest: `c9490e0f520be21271d969e6703f012268b1d39f8b70dd58854e5bfef7a75bb6` (1,525,346,571 bytes). Any upstream release or asset change requires a new review and code change. This is code-level supply-chain review, **not** evidence the 1.5 GB archive was downloaded and verified in a runner.
4. Public Ubuntu GitHub runners are listed as 4 vCPU / 16 GB RAM / **14 GB SSD** (https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job). The runner checks for 9 GiB free disk, installs the verified archive only into ephemeral runner storage, and removes the compressed package before downloading models. Even so, memory, free storage and CPU inference speed may cause a blocked or timed-out run; passing is not guaranteed.

## Acceptance

The mandatory acceptance CLI is `python -m scripts.run_vision_acceptance --out-dir local-results/github-actions-synthetic-live`, using real installed Ollama models. Four image-conditioned responses, actual tool selection for zoom and video-derived still, and a distinct Q02 review must all pass. The script writes SHA-256 references and hard-blocks on failure. Even success is `LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN`, **not** a licensed home inspection or customer release.

## Next owner decision, not presumed

To authorize a public GitHub Actions compute trial, the CEO must explicitly approve (a) a scoped exception/change to `PAUSE_AUTONOMY`, (b) any main-branch registration or alternate runner activation, and (c) the proposed pinned binary release and its limited external compute use. Until then, continue offline code review and controlled simulation; do not claim the live-model blocker has cleared.

## v1.3.1 addendum — verified archive pin, no activation

- Added `scripts/verify_pinned_ollama.py`, a no-network verifier with immutable release, size and SHA-256 constants, and negative unit tests.
- Replaced `curl https://ollama.com/install.sh` followed by shell execution with the direct immutable-version GitHub archive, checksum before extraction, and temporary-path installation. This **removes the mutable installer blocker** but does not bypass the governance or workflow-registration gates.
- The model weights still download during any eventual authorized trial; they are checked by the existing model-identity/readiness protocol, not treated as pre-reviewed/field-validated.
- The root `PAUSE_AUTONOMY` remains active and the workflow remains branch-only. Nothing has been dispatched, installed, or approved for customers.
