# A10 CPU live trial — evidence review and retired trigger

Date: 2026-10-31 America/Detroit; GitHub run UTC 2026-11-01.
Project: K.O. Enterprises Home Inspection; development branch `home-inspection-development`.

## Grounded run and artifact
- GitHub Actions run: https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41257474223
- Run ID `41257474223`; job `124703594863`; trigger commit `181f38c9bf9f54ba427c9119bbe84ee15d33225e`.
- Result: `failure`. Successful: checkout, owner pause/authorization checks, Python/runtime prerequisites, remote regression, verified Ollama binary, model weight setup, exact three model identities.
- Remote regression: **649/649 tests PASS**, measured 45.672 seconds. This is software-contract evidence, not field detection accuracy.
- Artifact: `one-time-home-inspection-reconciliation-a10`, GitHub artifact ID `13063173799`, 28 ZIP members, SHA256 `20d44feb4821eb1f2f5010f9281e872dd55a8edc5758c5b067f4445ca6926780`.
- Artifact ZIP CRC test passed; 27 listed payload hashes match their bytes. Do not treat the archived media as real property evidence; all input media were synthetic.

## Actual inference outcome
- The first visual writer call used `qwen2.5vl:3b`, image SHA256 `8a0511cb888a97140a67d47d1eb8c411398dc4e3eda749cbf1af23c592050313`, and schema-aware compact prompt 9,588 characters / 9,590 bytes (pre-compaction: 11,700 characters). Schema hash `ace90d28fdcdc3de119cc7cfb26021e91770b7584c0ead4e5f09f19c2eb24959`.
- The request exceeded the application 180-second deadline. Archived `trial/invocations/0001-writer.response.json` records `PROVIDER_ERROR`, `TimeoutError`, elapsed **180.095s**. Writer: 1 request, 0 completed responses. Q02: 0 completed calls. Q03: not invoked. No accepted inspection candidate, tool action, or held report.
- Ollama was actively running: model loaded on CPU with two threads; multimodal image chunks took ~32.4s and ~11.3s; the server logged an initial 3,753-token prompt and had processed 2,503 tokens by ~141 seconds. No observed out-of-memory, though this does not establish other machine configurations.
- A prior model test (A05) demonstrated completed live image-conditioned inference; A10 does **not** demonstrate completed end-to-end three-role inspection, autonomous zoom/still, or technical review.
- Full `Milestone 2` and all professional/field release gates remain **BLOCKED**.

## Safe cleanup performed
- Consumed A10 single-use workflow `.github/workflows/home-inspection-one-time-20261031-a10.yml` removed in commit `5b4c76b1f84ab72e9c4ed1b65b1b9bf12ca619c2`.
- Root `PAUSE_AUTONOMY` and `main` remain intact. No further external compute or automatic retries were authorized.

## Technical next milestone (not yet implemented)
1. Benchmark the actual prompt and image workload under bounded CPU budgets. Treat model performance as an empirical requirement, not infer speed from model size.
2. Retain the full source-of-truth, but do not force the entire legal/technical/administrative packet through the 3B **vision** forward pass. Use a small pixel-grounded observation request plus typed, citeable retrieval and evidence memory, then pass only matched facts and observations into the separate reasoning/review stages. Preserve no-loss source identifiers, provenance hashes, and refusal on missing context.
3. Evaluate alternate small vision encoders/models and smaller image resolutions for latency **and** serious-defect recall; don't silently downscale original native evidence or hide important defects. Full-resolution source crops must remain available.
4. Require genuinely completed Qwen/Granite/Q03 results, useful native zoom/video selection, synthetic temporal checks, independent criticism, and qualified real-inspector cases before promotion.
5. Validate complete latest-branch regression after any source change; do not reactivate one-shot trial without new owner authorization.

Internal evidence review only. No separate critic agent was called; source verification cannot earn approval for field operation.
