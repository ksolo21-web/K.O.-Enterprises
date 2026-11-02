# M3 v8 — automatic proposals and an executable signed lesson runtime

This revision implements the two software gaps left after v7: automatic source-backed report proposals, and actual local lesson-pack promotion/consumption/rollback. It does not establish real report accuracy, professional qualifications or customer release. No actual Ollama inference, production signer enrollment or production activation was performed in this session.

## Automatic report proposals

`inspection_engine.report_proposals` reads a source-validated prepared study. It sends each original page image and its complete bounded PDF spans/OCR word inventory to an explicit provider. IDs are namespaced by physical page. Adjacent-page calls may propose relationships between existing findings. Every output is reconstructed through the typed source validator; invented quotes, offsets, OCR IDs, unseen pages, unsupported links and self-approval fields reject. Page dispositions stay unresolved, and output kind/origin is **MODEL_PROPOSED**, never HUMAN_DECLARED.

The production adapter uses only fixed loopback Ollama endpoints, verifies the installed model digest before each call, rejects incomplete/non-stop generations, and never downloads models or falls back to the cloud. Both metadata and generation use absolute deadlines, bounded replies and no redirects/retries. A duplicate socket descriptor keeps the watchdog effective for HTTP/1.0 bodies after the connection object closes. The configured 1–600 second deadline covers preflight plus generation. Per-page/source/output/call budgets reject excessive work without silently dropping source content. Default maximum: 25 calls; hard maximum: 400. Global source-mapping bounds still apply.

```bash
python -m inspection_engine.report_study_pipeline propose \
  --reference /private/case/reference.json --registry /private/study/registry.json \
  --source-pdf /private/case/original.pdf --study-dir /private/case/prepared \
  --model ALREADY_INSTALLED_MODEL --model-digest PINNED_MODEL_SHA256 \
  --max-calls 25 --timeout 120 --out-dir /private/case/proposed
```

This is an explicit local model-execution command. It requires complete source renders and OCR for textless pages. The output includes the model-proposal receipt, typed pending mapping, original-scope readiness flags and a canonical offline source viewer. Source content is data, never a tool instruction. Schema/source validation does not prove that a description or interpretation is correct.

## Stage and evaluate the actual proposed lesson context

The existing v7 candidate and locked-holdout plan commands remain the source/case/media preparation path. The new benchmark freezes expected findings before a run. Expected rows contain `case_id` and `expected` lists of `{system, location, description, critical}`. All planned holdouts must appear exactly once. Labels are human-supplied and unauthenticated until external review; no labels enter the model prompt.

```bash
python -m inspection_engine.lesson_activation freeze-benchmark \
  --candidate /private/train/candidate.json --plan /private/study/frozen-plan.json \
  --labels /private/study/expected-findings.json --out /private/study/benchmark.json

python -m inspection_engine.report_study_pipeline propose \
  --reference /private/holdout/reference.json --registry /private/study/registry.json \
  --source-pdf /private/holdout/original.pdf --study-dir /private/holdout/prepared \
  --model ALREADY_INSTALLED_MODEL --model-digest PINNED_MODEL_SHA256 \
  --candidate /private/train/candidate.json --benchmark /private/study/benchmark.json \
  --out-dir /private/holdout/candidate-run

python -m inspection_engine.lesson_activation evaluate \
  --candidate /private/train/candidate.json --benchmark /private/study/benchmark.json \
  --runs /private/study/run-paths.json --out /private/study/evaluation.json
```

`run-paths.json` lists the private `model-proposals.json` paths for every holdout. Evaluation checks candidate/benchmark/model/source/corpus identity and requires each run to contain the exact candidate-context digest. The staged and active runtime use the same bounded supplemental DATA block. A perfect baseline run without candidate lessons cannot authorize those lessons.

Metrics are recomputed from normalized exact `(system, location, description)` matches, including false positives, false negatives and critical misses; supplied summary counts cannot replace predictions/labels. This conservative scorer does not accept paraphrases as semantic matches and does not measure table, diagram, handwriting or photo-inspection accuracy. Submitted run receipts are unsigned: coherent forged run records are not proof a model actually executed. The archive explicitly retains unauthenticated run/label provenance and unverified professional accuracy. Trusted reviewers must examine genuine original evidence and execution records before authorizing anything.

## Pinned local trust policy, default disabled

`inspection_engine.lesson_activation` uses Ed25519 via the declared `cryptography` dependency. An operator-controlled private policy contains exact fields `kind`, `namespace`, `task_scope`, `activation_enabled`, `keys`, `limits`. It must use kind `M3_LOCAL_LESSON_TRUST_POLICY_V8`; activation must be explicitly enabled after the owner is ready. No enabled policy or real trusted keys are shipped or enrolled by this work.

Each enrolled key record contains `public_key_hex` (32 raw public-key bytes in hex), `roles` (`owner` or `reviewer`), `revoked` and integer UTC `expires_at`. Limits contain `minimum_cases`, `maximum_false_positives`, `maximum_false_negatives`, `maximum_critical_false_negatives`; critical misses must be zero. The current computed benchmark supports task scope `report_interpretation`. Its finding-only metrics are not evidence of broad semantic competence. Report-scoped approvals cannot authorize a `photo_specialist` consumer; that path stays blocked without its own evaluated task.

A signature proves that a key enrolled in this local policy authorized exact bytes. It does **not** prove inspector licensing, competence, label truth, model execution or real field accuracy. Professional and customer-release gates remain false. Pinning/trusting the policy and verifying signer qualifications are external operator responsibilities; anyone able to replace the trusted policy has crossed that local trust boundary.

## Actual promotion, loading and rollback

```bash
python -m inspection_engine.lesson_activation init \
  --store /private/study/lesson-store --policy /private/study/trust-policy.json

python -m inspection_engine.lesson_activation request \
  --store /private/study/lesson-store --policy /private/study/trust-policy.json \
  --candidate /private/train/candidate.json --evaluation /private/study/evaluation.json \
  --action promote --nonce UNIQUE_32_OR_MORE_HEX_CHARACTERS --expires-at UTC_EPOCH_SECONDS \
  --out /private/study/unsigned-request.json

python -m inspection_engine.lesson_activation apply \
  --store /private/study/lesson-store --policy /private/study/trust-policy.json \
  --candidate /private/train/candidate.json --evaluation /private/study/evaluation.json \
  --request /private/study/unsigned-request.json --approvals /private/study/signed-approvals.json

python -m inspection_engine.lesson_activation load \
  --store /private/study/lesson-store --policy /private/study/trust-policy.json \
  --model-digest PINNED_MODEL_SHA256 --task-scope report_interpretation
```

Two approvals are required, exact `{key_id, role, signature_hex}` records from distinct public-key fingerprints, one owner and one reviewer. Alias IDs cannot fake independence. Sign **`KO-HOME-INSPECTION-LESSON-ACTIVATION-V8` + newline + canonical request JSON**, encoded UTF-8; canonical JSON uses sorted keys, ASCII escaping and separators `(',', ':')`. Private signing keys never enter these commands.

The request binds domain/action, task, namespace, policy hash, candidate/evaluation/model/corpus hashes, expected current state, target pack, nonce and validity interval. Requests are valid for at most one hour. New stores have a random public store identity included in the state hash, so an approval for one fresh store cannot be replayed into another fresh store with the same namespace/policy.

Promotion executes under an exclusive lock and compare-and-swap state check. Immutable signed journal records and nonce history are retained; the active pointer changes by atomic replacement. Every load revalidates the signed chain, thresholds, policy, model and task. Supplemental lesson data is limited to 2,000 encoded bytes. The original source of truth, SOP/knowledge briefs, evidence obligations and release holds retain priority. No weights or base knowledge are rewritten.

To consume an authorized report pack, use `report_study_pipeline propose` with `--lesson-store` and `--lesson-policy` in place of `--candidate`. The model-pinned factory verifies the actual local model inventory. Active context is rechecked before and after each provider call. The optional photo-specialist integration likewise refuses a report-only pack. Existing callers remain unchanged when the optional parameters are absent.

Rollback is a real pointer change to the intact immediately previous approved pack. Create a fresh `request --action rollback --target-pack PREDECESSOR_PACK_HASH`, supplying that predecessor's candidate/evaluation; obtain two fresh signatures; then `apply`. Old approval nonces cannot be reused. The temporary-store tests execute promotion → load/consume → second-version promotion → rollback → reload, rather than merely preparing a rollback plan.

## Stops, recovery and local-owner boundary

The real root `PAUSE_AUTONOMY` blocks activation, rollback and learned-context consumption. `COMPANY_OS_PAUSED` follows company policy, including stopping on unknown values. The stop is checked immediately before state replacement and at consumption boundaries; it is cooperative, not a way to cancel arbitrary already-running external code. This work never removes the pause. Tests simulate an unpaused state only in temporary stores with ephemeral test keys.

Directories/files are private. Caught initialization failure removes the new partial store. Failed state replacement preserves the old state; a byte-identical inert orphan event can be retried. Existing locks are not stolen. A hard crash may leave a lock or orphan; inspect/recover offline before retrying. The journal is bounded to 64 operations, after which controlled migration is required.

Policy replacement, key revocation or expiry invalidates historical verification and fails closed; seamless rotation/migration is not implemented. There is no external trusted monotonic head. A local store owner who coherently restores an entire old state/journal cannot be detected by local hashes alone. Do not describe this as resistance to a malicious filesystem/policy owner or as authenticated corpus governance. These limitations do not permit skipping professional evaluation.

## Evidence

The current controlled tests exercise actual cryptographic signing/verification, private filesystem state changes and runtime consumption, with original synthetic PDF/Tesseract source validation. Model replies are controlled fixtures and local HTTP test servers; no real model accuracy or production activation is claimed. Independent full regression, actual model-origin browser screenshots and final GitHub parity are recorded in the v8 checkpoint/evidence package when complete.
