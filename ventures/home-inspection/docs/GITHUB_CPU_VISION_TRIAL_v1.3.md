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
3. The runner downloads Ollama's official installer only after an operator supplies a 64-character SHA-256 digest from a separately reviewed copy. The script **fails closed** on a missing or incorrect digest. The installer URL still serves mutable content, so the approved digest must be reverified before each run. This installation supply-chain review and authorization remain open; do not guess the digest.
4. Running two multi-billion-parameter models on CPU may be slow, memory-constrained, or fail to satisfy the required autonomous tool-selection gate; the run is only evidence, not a guarantee.

## Acceptance

The mandatory acceptance CLI is `python -m scripts.run_vision_acceptance --out-dir local-results/github-actions-synthetic-live`, using real installed Ollama models. Four image-conditioned responses, actual tool selection for zoom and video-derived still, and a distinct Q02 review must all pass. The script writes SHA-256 references and hard-blocks on failure. Even success is `LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN`, **not** a licensed home inspection or customer release.

## Next owner decision, not presumed

To authorize a public GitHub Actions compute trial, the CEO must explicitly approve (a) a scoped exception/change to `PAUSE_AUTONOMY`, (b) any main-branch registration or alternate runner activation, and (c) the pinned installer. Until then, continue offline code review and controlled simulation; do not claim the live-model blocker has cleared.
