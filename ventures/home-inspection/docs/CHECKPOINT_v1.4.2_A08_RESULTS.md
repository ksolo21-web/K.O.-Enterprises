# v1.4.2 — A08 completed generation, rejected output and local repairs

## Actual remote result: BLOCKED

[Run41195128626](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41195128626), job124519651687, commit `de60a65e90cb526a8b797891eeebf5504eaaee0d`.

- **229/229 remote tests passed**,31.692seconds, before installation/inference. Pinned Ollama v0.40.13 archive and Qwen writer digest matched the reviewed identities.
- Exactly **one** generation request used the pinned A07 synthetic input, prompt and scoped schema. Input JPEG1400x747,53922bytes; prompt3544characters. No geometry rerun, second generation, Granite download, tool execution or Q02 call.
- The request returned **HTTP200, complete body, done:true, done_reason:stop** in **217.022seconds**. The scoped generation schema was accepted for this call; the resulting proposal/tool contract did **not** pass.
- Actual model metrics: load3.567seconds, prompt evaluation111.424seconds for2458input tokens, generation101.980seconds for738output tokens. Available CPU affinity4; the server log reports its model thread pool as2threads. Do not infer a speedup without a benchmark.
- This completed request took longer than the application's180second limit. It supports CPU latency as an explanation for this new attempt; it does not retroactively prove the missing underlying exception in A07.
- The model produced12candidates: one roof description under cladding_type and11copies of the same door/trim description (10extra duplicates). Inspection of the actual synthetic drawing shows a visibly pitched roof with no shingle detail; the flat/shingle description is unsupported. No observation was accepted as an inspection finding.
- It again proposed `{"kind":"zoom","bbox":[0,0,1,1]}`. The unchanged-region gate correctly rejected it. **Zero tools, zero selected video stills, zero live Q02 calls.**
- Artifact13041160770:40460bytes,12members, ZIP SHA256 `acc5bb207196f81946c13571db84c4a3ecb52cff0c7ad3798411df0e04f30fc6`. All11manifest file hashes and5nested request-status hashes were verified, along with exact input/prompt/schema/payload identities.
- `docs/evidence/A08_REJECTED_WRITER_EVIDENCE.json` durably preserves the actual payload (including synthetic JPEG), response, HTTP audit, manifest, server log and snapshots. The process snapshot covers the parent Ollama process only; it does not measure the full model runner's CPU/memory. Model timing metrics above are the direct performance evidence.

## Local postflight changes; not remotely inferred

1. Reject indistinguishable normalized duplicate candidates before any tool execution. Preserve distinct components/locations/boxes. No silent deduplication, invented observation or feature relabeling.
2. Tell writers to avoid repeated claims and to describe the named feature itself. This prompt adjustment has not yet been exercised through a live model.
3. Carry feature_code, location and source bbox from proposals into the dossier, bind all three to the staged observation before Q02, and include them in Q02's claim data and review record. Q02 explicitly challenges description-to-feature fit; a syntactically permitted code is not semantic proof.
4. Bind those same fields in tool-to-proposal-to-review lineage. Tampered feature codes/locations/boxes cannot silently alter the reviewed claim.
5. Retain fail-closed handling for old feature dossiers missing a feature code: regenerate their dossier from trusted source rather than guessing a code.
6. Keep the application's180second deadline unchanged. The isolated600second diagnostic was not a general timeout expansion or an additional live attempt.

**236/236 local postflight tests passed.** A genuinely separate critic independently reran **236/236**,33.569seconds, verified actual A08 evidence and latest repairs, and returned **9.7/10 PASS with no mandatory code/evidence blocker**. Tests replay the exact rejected A08 output and exercise controlled Q02 calls, classification/location/bbox tampering, distinct-location preservation and review lineage. This proves record/control behavior; it does not prove a live reviewer will recognize the semantic error.

The consumed A08 temporary workflow is retired by this results commit. Root pause marker, main and ordinary paused workflow remain unchanged. No next model run is launched or authorized by this checkpoint.

## Remaining acceptance and next task

The runtime can complete this scoped request, but its content/tool behavior is inadequate. Repeated text consumed much of its output; simply increasing every timeout would not solve that quality problem.

Next bounded work should improve and test evidence-selection behavior and concise, distinct feature descriptions, using this exact failure as a regression case. Consider a tool representation that makes unchanged full-frame requests structurally unavailable while preserving model-selected targets and native-pixel limits. Any new representation must preserve source-coordinate provenance, reject unsupported requests, and be tested before a separate live attempt. No crop, timestamp, observation or successful answer should be scripted to force acceptance.

Mandatory open gates: model-selected native zoom followed by a result-based observation and live Q02 review; a genuinely different-time, changed-pixel selected video still followed by observation and live Q02 review; qualified real-property accuracy benchmarking and human release. All remain **BLOCKED/UNVERIFIED**. Earlier Granite errors and A05–A07 failures remain in the evidence record. Full Milestone2 and customer release are not approved.
