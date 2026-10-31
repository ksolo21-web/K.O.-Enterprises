# A07 — specialist schema and actual tool evidence

## Observed baseline

A06 run41167245127 failed despite 206/206 remote regressions and four structured geometry checks. Its exact writer response omitted required feature_code and requested an unchanged full-image zoom. Zero tools and zero Q02 calls executed. See `CHECKPOINT_v1.3.8_A06_RESULTS.md`. Source parent after retirement: `8abc5a5ff2de6dfb39efee2dc9f29ad7bf04697d`. Preserve all earlier wrong answers and failed trials.

## Repair and local acceptance

- Generate a trusted schema per work order, never by parsing model output. A feature requires feature_code with a system-specific enum; a concern cannot contain it. System scope follows the work order, including roles that own multiple systems.
- Zoom requires only kind+bbox, video_still requires only kind+timestamp; standalone photographs offer no still action. Timestamp range uses freshly probed duration. Require a strictly smaller useful crop in the prompt; authoritative area and pixel validators remain.
- Explicit schema-aware provider opt-in preserves existing two-argument controlled providers. Live CLI and diagnostic use the scoped schema. Put the same schema in the prompt and save its canonical SHA-256 in the trial request.
- Tests replay the exact A06 missing-field response, retain full-image rejection, inspect the actual mocked Ollama request, ensure cross-system rejection and conditional tool fields, and verify saved schema hash. Full existing evidence-lineage/completion tests remain mandatory.

## One external attempt

Exactly one public standard ubuntu-24.04 GitHub CPU job, maximum100minutes, contents-read only. Same pinned actions, loopback-only Ollama v0.40.13 verified archive, one loaded/parallel model. Same qwen2.5vl:3b writer digest fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1 and granite3.2-vision:2b reviewer digest 3be41a661804ad72cd08269816c5a145f1df6479ad07e2b3a7e29dba575d2669. Require9GiB free space. No customer evidence, secrets, paid service, deployment or main/pause change.

Stages: check exact approval/ref/repository and pause; install media dependencies; generate synthetic fixtures; run all regressions before downloads; verify pinned binary and model digests; run all four real geometry probes; then bounded specialists with optional autonomous tool choices and a second-model Q02 review. Preserve synthetic evidence as a three-day artifact, retrieve and inspect it, recalculate its hashes, independently review results, and remove the one-time trigger.

Acceptance is unchanged: real completed calls, a model-selected native zoom linked to a subsequent proposal and Q02 review, plus a selected video still from a different source time with visibly changed pixels linked to its own subsequent proposal and Q02 review. Aggregate tool counts or review of unrelated original imagery do not pass. Valid Q02 dispositions may include insufficient evidence; they never approve a home.

Optional tool choice can still yield a truthful failure. Do not force a request or claim to pass. No automatic retry, no silent fallback or model upgrade. Any missing required proof remains blocked. No result proves field accuracy, separate authenticated reviewer hosts, full Milestone2 acceptance or customer release.
