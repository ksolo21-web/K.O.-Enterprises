# Home Inspection — development branch

This is the home-inspection product track of **K.O. Enterprises**, kept on the separate Git branch `home-inspection-development` and isolated from the main company operating system.

## Decision and scope
- Parent organization: K.O. Enterprises.
- GitHub repository: `ksolo21-web/K.O.-Enterprises`.
- Development branch: `home-inspection-development`, branched from `main` on 2026-10-30.
- Source location **when integrated**: `ventures/home-inspection/`.
- Report design: approved Option 2, spacious navy-and-white editorial PDF.
- Inspection evidence: original photos, video footage, extracted full-resolution stills, native zooms, and source/timestamp/hash traceability.
- Specialist structure: inspection director, bounded technical work orders, separate Q01/Q02 reviews, and required authenticated professional/human approval.
- No AI finding can be labeled verified or customer-ready solely because a model proposes or a reviewer echoes it.

## Prototype baseline to integrate
The latest **local** v0.7 package is `Home_Inspection_M2_Technical_Critic_v0.7_Source.zip`, SHA-256:
`ba9dedcf000e4f77a746e614e0a55cc279e23343a3a436483e8ede75435cd025`.

The local suite was rerun on 2026-10-30: **104 tests passed**. Synthetic model replies only; no real live vision-model/qualified-inspector benchmark yet.

**Important:** This README establishes the GitHub branch and records the handoff. It does not claim the full v0.7 source ZIP is already uploaded to GitHub.

## Milestone gates
1. Retain Milestone 1 intake, photo-from-video, frame provenance, zoom, crop audit and professional PDF rendering.
2. Preserve Milestone 2 bounded specialist coordination and independent technical review interfaces.
3. Integrate the versioned source and tests into this branch (no customer photos, secrets, runtime artifacts, or generated report contents).
4. Run CI and confirm source parity with local acceptance evidence.
5. Run live vision model(s), real-world annotated cases and separate review; measure false positives, misses and limitations.
6. Require authenticated inspector sign-off before client release. Do not market the software as production-ready without this evidence.

## Public-repository safeguards
This repository is currently **public**; all branches, including this one, are public. Never commit real inspection photos, videos, addresses, reports, credentials, customer data or unlicensed stock photographs. Synthetic code fixtures should be minimal, labeled, and rights-cleared. No paid API, deployment or customer-facing action is authorized by branch creation.

The repository's `PAUSE_AUTONOMY` governance marker remains in effect for external/scheduled operations; this branch does not remove or change it.

## Status (2026-10-30)
**Source and safe synthetic test fixtures transferred; 118 local tests pass including long-report pagination. No remote CI run, no live vision-model validation, and no qualified-inspector field approval.**


## Current source and report status

The working engine is in [`inspection_engine/`](inspection_engine/). Run and test it using [`docs/GITHUB_DEVELOPMENT.md`](docs/GITHUB_DEVELOPMENT.md). See [`docs/PAGINATION_ACCEPTANCE.md`](docs/PAGINATION_ACCEPTANCE.md) and [`docs/SOURCE_TRANSFER_COMPLETION.md`](docs/SOURCE_TRANSFER_COMPLETION.md) for fresh verified status. The earlier `SOURCE_TRANSFER_HANDOFF.md` reflects the pre-recovery point, not the current state.

## Local vision runtime v1.0 (integration update)

A real, optional **local Ollama** setup and two-model synthetic smoke probe are now implemented. See [runtime setup and safety gates](docs/LOCAL_VISION_RUNTIME_v1.0.md) and [current acceptance blockers](docs/RUNTIME_ACCEPTANCE_v1.0.json).

The project has a Windows PowerShell and Linux/macOS shell setup helper (`scripts/setup_vision_models.ps1` / `scripts/setup_vision_models.sh`) that only downloads model weights when an authorized operator explicitly executes it. Default candidate models: `qwen2.5vl:3b` (specialist writer) and `granite3.2-vision:2b` (Q02 technical challenger).

Commands `python -m inspection_engine model-smoke` and `python -m scripts.run_local_live_trial` are opt-in, loopback-only; the latter exercises original synthetic photo/video evidence and records any model-selected zooms/stills. **Live vision inference has NOT been executed in the development container** because it has no Ollama runtime/models or outbound model-download access. Current tests cover software behavior with controlled providers, not real inspection accuracy. No real customer media or credentials are stored in the public repository. `main` and `PAUSE_AUTONOMY` remain unchanged.
