# Writer input compaction and one A10 synthetic evaluation

2026-10-31, owner local date. Base `6bab8462c91fd9ba4361eec6d81fabe912214638`. The owner's current **“ok”** follows this reported next priority: **“reduce input-processing overhead and benchmark latency and observation quality.”** The current task therefore includes source preparation and one new bounded evaluation of the changed input. A09's consumed authorization is not reused. Earlier source-only optimization review did not itself authorize execution; the new A10 record explicitly scopes this current instruction before the trigger.

## Requirements and dependency-aware gates

1. Profile the actual saved A09 request without model calls. Preserve original descriptor/JPEG and explicit unexecuted provenance for derivatives.
2. Keep the provider's authoritative JSON schema and validators byte-for-byte equivalent, and pass the same image bytes. For schema-aware providers, replace the redundant textual schema copy with complete readable field/type/status/action/bound guidance plus its schema digest. Legacy two-argument providers retain the original full prompt.
3. Minify serialized JSON only. Keep decoded knowledge, memory, context and meaningful string whitespace unchanged. Keep every non-JSON knowledge statement/reference, including prohibitions and uncertainty. No knowledge summarization, cropping, truncation, altered output limits or deadline extension.
4. Reduce task-card operational metadata only: repeated catalog/policy hashes and evidence IDs/snapshots. Task ID/hash, case/date/scope, state, physical-check holds, complete instructions and unknown/new fields remain in the model view. Full canonical cards remain in the audit and downstream ledger/Q02/Q03. No task becomes completed through compaction.
5. Test all13systems, multisystem schemas, MI context, unchanged images/format, later native evidence iterations, legacy behavior, duplicate/invalid claims, source limits, provenance and the new nonce guard. An unsupported future schema shape fails closed. Independent review strictly above9 with all mandatory source/evidence checks before a source/trigger commit.
6. New A10 must use a NEW authorization file, absent in its reviewed parent; exact public/development/push/first-attempt event, exact subject, source-parent and checkoutSHA. A09 remains retired and its existing record cannot authorize A10. No unknown nonce is accepted. Main, root pause, ordinary paused workflow and all knowledge catalogs remain unchanged.

## Measured offline profile

Saved A09 input:11,700characters/11,702UTF-8bytes. Compacted input:9,588characters/9,590bytes. **2,112bytes removed.** Same JPEG SHA256 `8a0511cb888a97140a67d47d1eb8c411398dc4e3eda749cbf1af23c592050313` and response-schema SHA256 `ace90d28fdcdc3de119cc7cfb26021e91770b7584c0ead4e5f09f19c2eb24959`.

These are measured character/byte differences, not tokenizer counts, model latency or observation-quality evidence. Offline descriptors explicitly say `OFFLINE_NOT_EXECUTED` and preserve historical A09 call attribution only under `source_request_metadata`. `profile_writer_input` validates source/image/prompt/schema hashes, writes new local files and calls no model.

```bash
python -m scripts.profile_writer_input \
  --request extracted_a09/trial/invocations/0001-writer.request.json \
  --out-dir new_offline_profile
```

## A10 exact execution scope

One standard public Ubuntu24 CPU job≤45minutes. Reuse the same verified Ollama v0.40.13 and exact three model digests from `evidence/A09_MODEL_MANIFEST_PINS.json`. Qwen2.5 7B remains an unpromoted Q03 candidate. No new model/provider/account, spending, customer media, credentials, outreach or deployment.

Same resource floors18GiBdisk/10GiBavailable/14GiBtotalRAM, parallelism1/one loaded model/keepalive0/context requested16384. Same application HTTP timeout180seconds (socket/inactivity semantics), harness/outer wall ceiling1800seconds shortened to reserve180seconds for diagnostics, maximum6writer/48Q02/1Q03calls, zero inference retries/fallback. No extra geometry/warmup generation, prescribed crop/time or scripted substitution. All report holds persist. A10 may still fail; shorter input does not establish a usable inspection model.

Review the actual archive after this one attempt: verify all manifests and source/model identities, input profiles and canonical cards; compare actual image/schema identities and observed timings with A09. Hardware/run variability and different generated output prevent treating one comparison as a formal causal benchmark. Independently assess any actual observations, source-backed tool choices and Q02/Q03 results. If no answer completes, observation quality stays untested. Installation, counters and a green job cannot establish fullM2/field accuracy/customer release.

Stop owned processes, preserve bounded server/resource diagnostics and all returned model evidence even on failure, retire the one-time A10 trigger, and save a resumable result checkpoint. No automatic second A10 attempt is part of this scope. FullM2 and qualified-inspector gates remain separate and mandatory.

## Trigger record

`ONE_TIME_SYNTHETIC_TRIAL_APPROVAL_2026-10-31_A10.md` is added only after accepted source/readback. Fields:

- `Authorization-ID: OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A10`
- `Authorization-Scope: one synthetic-only GitHub-hosted CPU reconciliation trial, no customers, no secrets, no deployment`
- `Source-Commit: <exact reviewed preparation commit>`

Exact subject: `trial(home-inspection): OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A10`. Only this NEW record changes in that commit. The source guard accepts only the fixed A09/A10 nonce/path pairs and independently enforces record absence in the parent, preserving the consumed-record protection.
