# v1.6.2 — A09 actual live result and recovery

Run on 2026-10-31: https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41254138948

Reviewed source: `aef7abc8036e092463806182a9febfe64056ef3e`; authorization-only trigger: `cee3a96382fb793642842276f70374b2b0ca9be2`. One authorized attempt, no inference retry. **Full M2 remains unapproved.**

## What actually ran

Remote **629/629 regressions passed**,39.105seconds. The canonical pause/source authorization checks, verified Ollama archive and all three pinned weight digests passed. Qwen2.5VL3B and Granite3.2Vision2B were reused; Qwen2.5 7B was installed as an unpromoted Q03 candidate. Installation is not execution or quality validation.

The first real Qwen writer invocation ended with `TimeoutError` after **180.044seconds**, without a completed answer. Actual counts: one writer request, zero completed writer responses, zero Q02 calls, zero model-requested zoom/still actions, zero Q03 calls, no final inspection report. Synthetic video generation and initial frame extraction succeeded; those are deterministic preparation, not autonomous tool use. Q03 was installed and verified but never invoked.

## Evidence and bounded diagnosis

The exact original archive is retained under `evidence/A09/Home-Inspection-A09-Live-Evidence.zip` (157,415bytes; SHA256 `34e8ad8d11871d618cbc9eeb5c41a3d1bc74af76edd7489bb35245a7da19d9ba`). All **26 top-level and 12 nested manifest entries**, source JPEG, prompt and schema hashes were independently verified. Key unmodified JSON records and normal server log are alongside the ZIP; `A09_RESULT_SUMMARY.json` provides a compact index. No customer data, thinking/context arrays, model weights or credentials are included.

The request contained11,700prompt characters. Server logs report4,803input tokens (3,453text and1,350image), a16,384token context and two model threads. The runner loaded in4.02seconds; image encoding batches took21.965and7.887seconds. Logged prompt processing reached4,551/4,803tokens (95%) at169.69seconds, followed by sampler initialization and an HTTP500 at the client timeout.

This supports an **input-processing CPU-latency bottleneck for A09**. It does not prove every earlier failure had the same cause or assess current semantic accuracy. No completed answer exists to score observations or tool choices. No OOM evidence appeared. Sampled runner peakRSS was4,574,384KiB andCPU197%; available RAM before setup15,461,683,200bytes, free disk91,471,028,224bytes. These are actual samples, not guaranteed resource peaks.

Cleanup recorded all three tracked owned processes stopped, with successful child tracking; the final snapshot corroborates their absence. The one-shot workflow is retired from `.github/workflows`; its exact body is retained as `workflows/A09_RETIRED_WORKFLOW.yml`. The scope tests read that non-executable reference after retirement. Main, root pause and the ordinary paused workflow remain protected.

## Independent assessment and remaining gates

A genuinely separate critic independently verified the raw archive, all manifest/input hashes, actual timeout, logs/resources, zero downstream execution and cleanup. Verdict: **A09 BLOCKED; no live M2 acceptance**. The earlier9.7implementation/plan score is not an inspection-quality or runtime-acceptance score.

The earlier A05 geometry inference remains verified; A09 does not erase it. The corrected finding is that the runtime and weights exist and execute, while this CPU configuration did not complete the revised specialist request within the existing timeout. The missing capability is successful useful inspection/reconciliation under the bounded workflow.

Next critical work: profile and reduce duplicated prompt/schema/context overhead while preserving knowledge scope, source evidence, classifications and holds; benchmark latency and observation quality separately before another bounded live attempt. Repeating this unchanged configuration or merely extending deadlines would not establish competence. No second inference attempt is part of this recovery. Real-case qualified-inspector evaluation and authenticated physical/human signoff remain mandatory; M3 remains a quarantined report-study foundation.

The Library evidence save failed because storage was full. The complete verified ZIP and decisive records are therefore preserved in the authorized public GitHub development branch; no Library files were deleted or overwritten.

Post-retirement local verification: **629/629 passed**,39.379seconds. A genuinely separate critic independently passed **629/629**,39.228seconds, and awarded **9.7/10 for staged recovery/evidence preservation only**, with no mandatory blocker to the recovery commit. It verified the original ZIP/Git blob identity, ten decisive records byte-identical to the archive, exact retired workflow body and the sole two-line test lookup fallback. A09/liveM2 remain blocked. The commit protocol verifies every changed Git blob, the active-trigger deletion and baseline preservation before branch advancement, then reads back the final head and archive.
