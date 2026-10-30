# Home Inspection Intelligence — resumable checkpoint v0.7 (2026-10-30)

Predecessor: v0.6 (85 passing tests). Preserves all M1 photo/video/natural zoom, video-still photo capture, editorial Option 2 PDF, 13-system property-description coverage, equipment research, and human comparison baseline. No feature regressions intentionally introduced.

## Verified in this pass
- Added read-only Q02 technical-review stage (`inspection_engine/critic.py`). Original + zoomed context sent to a *second* review provider invocation. Three supported dispositions; all remain pending inspector.
- Added `agents-critic` CLI for separately installed local Ollama reviewer model; distinct provider ID and checks prevent a reviewer call pretending to be the proposing call. Does not establish genuine independent runtime identity.
- Strict dossier/project/source/photo hash/zoom pixel and source claim cross-linking; fail closed on provenance discrepancies.
- Added local mock Ollama transport tests confirming expected fixed loopback endpoint, image base64, schema, JSON response handling, size limits and no silent cloud fallback.
- Added draft GitHub CI workflow and `.gitignore` excluding real customer media; no remote repository/CI was created or used.
- Scripted second-pass demonstration is **not a real vision model**; its `insufficient_evidence` responses are fixture results, not model reasoning.

## Acceptance block
- M2 coordination and reviewer contract are implemented; full M2 **NOT APPROVED** because no Ollama model/runtime is installed here, no actual image diagnosis was validated, no real professional reference benchmark exists, and no qualified human authentication/signoff exists.
- No legal/insurance/licensing validation, real-world production privacy review, or externally deployed infrastructure.

## Next action
1. Run live primary and independent reviewer models locally on the synthetic/consented fixture. Record model identities/versions, response accuracy, latency, rate of valid structured outputs and failure modes.
2. Collect appropriately consented and qualified-inspector-labeled inspection photo/video sets with both defect and negative controls. Adjudicate misses and false positives; hold out cases.
3. Build secure human sign-off workflow and benchmark-based release gates before any customer-facing use.
4. Establish a dedicated private GitHub repository and run CI. No existing unrelated repository should be used as a substitute.

Test evidence and limitations are in `ACCEPTANCE_M2_v0.7.md` and `output/m2_critic_demo/`. Source is runnable locally with Python >=3.12, dependencies in requirements.txt and FFmpeg.