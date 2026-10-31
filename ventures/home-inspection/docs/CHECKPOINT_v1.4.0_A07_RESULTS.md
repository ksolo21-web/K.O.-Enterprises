# v1.4.0 — A07 actual result and local transport diagnostics

## Actual remote outcome: BLOCKED

[Run41168200329](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41168200329), job124440240360, source commit `d92d31a68ad1e386c1e5f66368f9771040c3e561`.

- **211/211 remote tests passed**,28.380seconds. This validates the reviewed preflight code, not the later local diagnostic repair below.
- The pinned Ollama binary and both A05/A06 model digests passed verification.
- **4/4 actual structured image checks passed**: Qwen and Granite each returned red square and blue circle, with completed responses, hashes and timings. These four calls took81.891,82.143,91.928,91.820seconds respectively.
- The first specialist writer call returned **no completed envelope and no structured answer**. It failed after **180.101seconds** with the historical generic message `Local Ollama unavailable; start Ollama with installed vision-capable models`.
- **Zero completed specialist writer calls, zero executed zooms, zero selected stills, zero Q02 calls.** A07 did not test whether a completed writer answer follows the new schema. No specialist-tool, separate technical-review or Milestone2 acceptance.
- The180.101second duration is consistent with the180second request deadline. The old transport error wrapper discarded the underlying exception category, and the server log was not uploaded. This archive alone cannot prove timeout versus connection/runtime failure, grammar compatibility, or slow model generation. Do not report a confirmed root cause.
- Artifact13029758825:144817bytes,23members, SHA-256 `bb174914ce89649b8eafcb64bf43e78ebc06f009433e629796be5a310485a998`. The archive digest,12 recorded JSON hashes and writer image/prompt/schema hashes were recalculated locally.
- `docs/evidence/A07_FIRST_WRITER_FAILURE.json` preserves the actual first request, failure response, exact input JPEG as base64 and archive provenance. This is **synthetic evidence only**, retained durably because the full Actions artifact expires2026-11-03.

## Local postflight repair; not remotely exercised

The loopback transport now distinguishes timeout, connection refusal and other transport failures while retaining the original exception as cause. The synthetic recorder saves a bounded chain of cause type names. No automatic retry, inference deadline increase, endpoint expansion or model change was added.

Local full regression after this repair: **213/213 passed**,26.420seconds. A separate critic independently reran **213/213**,25.156seconds, verified the actual archive and exact durable request/response/JPEG, and scored the postflight implementation and evidence **9.5/10 PASS with no mandatory code blocker**. That review required trigger retirement and this actual-results checkpoint before handoff; it did not grant a new live trial or Milestone2 acceptance. The original A07 failure record remains unchanged; improved error categories cannot retroactively identify its cause.

The consumed temporary A07 push trigger is retired by this results commit. Root `PAUSE_AUTONOMY`, normal paused workflow and `main` remain unchanged. No further model run is started by this checkpoint.

## Next bounded technical task

Isolate a single scoped writer request on the same synthetic input, with server diagnostics and an explicit per-call resource budget, before repeating the entire suite. Diagnose grammar/request compatibility and CPU latency from actual evidence, then decide the smallest change. The current grouped live-stage summary is too coarse for meaningful live progress; any future trial should expose stage timing and preserve bounded server diagnostics.

Keep all feature-code, area, custody, completion, changed-time/changed-pixel, tool-to-proposal-to-Q02 and human-release gates. Do not convert rejected outputs into findings or force a particular tool request. The earlier unconstrained Granite error remains part of the reliability record.

Real-property defect accuracy, equipment operation, concealed conditions, professional benchmarking, authenticated reviewer hosts and customer release remain unverified.
