# v1.7 — input compaction and A10 preparation

2026-10-31 owner-local date. Base `6bab8462c91fd9ba4361eec6d81fabe912214638`. The user said “ok” after the proposed next priority to reduce input-processing overhead and benchmark latency/observation quality. Requirements, exact bounded A10 scope and dependencies are in `INPUT_COMPACTION_AND_A10_PLAN.md`.

## Implemented and measured

The schema-aware writer path sends the exact same authoritative schema to the provider and retains all validators. Its prompt replaces the duplicate full-schema text with complete field/type/status/action/bound guidance and the schema hash. Legacy two-argument providers retain their original full prompt.

JSON-only serialization is compacted with decoded knowledge/memory/context values unchanged. All non-JSON knowledge text, references, rights/uncertainty limits and report holds remain. Task view projection removes only four redundant operational fields: catalog/policy hashes, evidence IDs and evidence snapshot. Complete task instructions, IDs/hash, case/date/scope/state, physical-check requirement and unknown/new fields stay in the model view. Full canonical task cards remain in pre-call audit data and all downstream case records. No image resizing, record truncation, source/knowledge edits, relaxed limit or deadline change.

The actual saved A09 request profiles from11,700to9,588characters and11,702to9,590bytes: **2,112bytes removed**. JPEG and API-schema identity are unchanged. The self-contained proof is `evidence/INPUT_COMPACTION/` (exact original JPEG, offline descriptor, full receipt); original A09 archive is retained separately. Original request bytes are untouched.

Offline derivatives are explicitly `OFFLINE_NOT_EXECUTED`, `model_invocations=0`. Original live call metadata is nested as historical source attribution, preventing an optimized descriptor from masquerading as an executed A09 request. Token counts, latency and observation-quality flags remain false; input size alone does not prove any of those improvements.

## Verification

All **649/649 local tests passed**,39.490seconds. A genuinely separate critic independently passed **649/649**,39.643seconds. Fifteen compaction cases and five A10 cases were added to the prior629suite. The existing schema-forwarding test was updated for the intentional representation change while retaining explicit authoritative format/field/system/feature/extra-key assertions.

Checks cover all13systems, complete MI knowledge/JSON values, multisystem feature-code coupling, legacy behavior, native zoom iterations, canonical downstream identity, semantic whitespace/unknown technical fields, exact image bytes/schema, source tamper/limits/invalid claims/duplicates, audit-before-call and offline attribution. A10 tests preserve canonical pause, exact nonce/path/source parent, first-attempt/public/development checks and new-record-only protection; unknown or reused authorizations fail. YAML and all9shell blocks parsed.

Final separate critic: **9.7/10 for implementation and the bounded A10 plan**, all mandatory reviewed checks passed. It recomputed the self-contained proof against the original A09 archive, including the exact JPEG/schema and unexecuted provenance. No token-count, latency, observation-quality or fullM2 approval was inferred. This is implementation/plan acceptance only, not liveM2/inspection accuracy.

## Next authorized bounded action

After exact source readback, add only the new A10 record with its reviewed parent and trigger the one evaluation. Reuse the same pinned binary/three model digests, single-model loading, resource floors,45minute publicCPU job,≤30minute harness and existing180second HTTP timeout, zero inference retries/fallback. No new model/account/provider, spending, customer input or model promotion. A09 remains consumed/retired.

Inspect actual A10 requests/responses/logs, source-backed tool/Q02/Q03 behavior and artifact hashes, then retire A10 and preserve a result checkpoint regardless of outcome. A failed or incomplete actual run cannot inherit the source/test score. FullM2, field accuracy, authenticated human completion and customer release remain open.
