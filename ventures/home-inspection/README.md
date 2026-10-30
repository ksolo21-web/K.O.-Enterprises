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
**Branch created; status README committed; full source transfer and live-model validation remain pending.**
