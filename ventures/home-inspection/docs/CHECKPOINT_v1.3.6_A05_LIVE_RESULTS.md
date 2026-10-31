# v1.3.6 — Actual A05 vision results and exact next gate (2026-10-30 Detroit)

## Real inference: VERIFIED, with evidence
- GitHub Actions run: https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41164389582
- Run commit: `ffb4b566416fd29b662095022b00548528d3e1d3`, event `push`, completed with **overall FAILURE**.
- Evidence artifact ID: `13028571288`, name `one-time-home-inspection-synthetic-vision-proof-a05`.
- Ollama v0.40.13 binary checksum verification, service start, and model pulls completed successfully.
- Two separate real Ollama API inference calls returned `done=true`:
  - Qwen2.5-VL 3B, synthetic red-square image: **“Red, square”**, 57.43 s.
  - Granite 3.2 Vision 2B, synthetic blue-circle image: **“The one large solid object is black and rectangular.”**, 59.07 s (**incorrect**).
- The subsequent controlled structured prompt made **four real image-conditioned calls** (both models on red-square and blue-circle). All four correct, `SYNTHETIC_VISION_PROBE_PASSED`. Actual model hashes and timings are retained in `acceptance/image_probe.json`. The two models were hosted in the same Ollama process, not independently deployed agents.
- **Real Ollama image inference is no longer unverified**. Reliability remains uncertain; the preliminary Granite error is material and must not be concealed.

## Why full Milestone 2 remains blocked
- `trial/trial_status.json`: `BLOCKED`, reason **`Feature code must belong to specialist system`**.
- The real writer generated an invalid candidate code not present in the authorized registry. The deterministic system correctly rejected it. No model-generated zoom or video-still request was executed; no claim reached a separate Q02 review.
- Acceptance JSON explicitly reports `live_model_inference_verified=true`, but `live_specialist_tool_use_verified=false`, `reviewer_visual_assessment_verified=false`, `technical_review_items=0`, `customer_release_allowed=false`.
- The remote independent regression step ran **174 tests: 1 failed, 12 errors**, mainly FFmpeg timestamp/seek differences and stale workflow test-path assumptions.
- A separate development commit `037b19273e9b5065f035a01bfe261e3dc36fa7f0` implements single-frame source-timeline selection, consistent video still/zoom audits, and monorepo workflow-path test fixes. These changes were verified locally, not by this A05 immutable run commit.

## Latest source correction
- This revision adds the exact `REQUIRED_FEATURES` allowed-code map to each bounded specialist prompt. The local model must select a code from its actual delegated system, or return no unsupported candidate. Potential concerns must omit feature codes.
- The strict validator is unchanged; invented feature codes remain **BLOCKED**, never rewritten, approved, or concealed.
- Local suite against source archive plus fixes: **183/183 tests passed using FFmpeg 7.1.5**. A fresh remote test of these new commits remains open.

## Governance / approval
- A05 one-time workflow was removed in `4ebb25ae506df7ed7f1704c1971b86a9dd5c9b05`.
- Company root `PAUSE_AUTONOMY` remains effective; `main` unchanged; synthetic files only.
- No live Q02 technical review, autonomous agent-chosen zoom and still, professional case scoring, qualified human signoff or customer release.
- **Internal review only, not a separate critic runtime.** Evidence includes raw A05 artifact/logs, per-model hashes and structured responses, observed failures, local regression suite and GitHub source checks.
- Milestone 2 score remains unawarded / blocked. Next external synthetic diagnostic requires the owner's limited authorization and an approved test plan, not a silent relaunch.
