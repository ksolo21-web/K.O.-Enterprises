# Milestone 4 — integrated inspection workflow

Status: authorized for engineering, not accepted for production. Branch: home-inspection-development. Preserve M3 V8 and deferred real-world validation.

Objective: private photo/video intake -> provenance and coverage -> specialist findings -> independent Q01/Q02/Q03 review -> qualified human inspector approval -> Option 2 PDF. Never claim photo evidence establishes concealed conditions, functionality, code compliance, or equipment manufacture dates without adequate corroboration.

Work packages:
- Inventory and reuse M1 photo/video intake, M2 agents, M3 report-learning interfaces and Option 2 renderer.
- Implement one resumable, fail-closed private case runner with source-bound stage receipts.
- Preserve original hashes, frame timestamps, crop lineage, missing views and inconclusive evidence.
- Distinguish directly visible, probable, inaccessible, physical-test-required and unresolved findings.
- Carry normal observations, structure/foundation/framing/subfloor, equipment data, photos, recommendations and limitations into Option 2 PDF without inventing unknowns.
- Add synthetic end-to-end fixture, provenance/quality/approval regression tests and GitHub CI.
- Prepare later professionally reviewed photo/video benchmark; defer real model accuracy, qualified review, signed learning activation and field/customer release until explicitly authorized.

Acceptance: no fabricated claims; no dropped evidence; Q01/Q02/Q03 and human review states retained; unverified reports cannot be customer released; reproducible private workflow; passing offline CI. Public repo must contain no customer media or secrets. Preserve main and PAUSE_AUTONOMY.

Next: inspect existing integration APIs, implement private case orchestration, test, review and fix. This plan is a Milestone 4 scope checkpoint, not a completed milestone or a complete business plan.
