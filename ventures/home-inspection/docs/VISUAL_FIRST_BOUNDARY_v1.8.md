# A10 follow-up — bounded visual-first request and deferred expert knowledge

Date: 2026-10-31 (America/Detroit). Owner requested continued engineering after A10.

## Why

A10 GitHub Actions run 41257474223 completed 649 Python contract tests, installed three pinned models, then the first Qwen2.5-VL 3B inference timed out at its unchanged 180-second application deadline. No Q02 or Q03 call executed. The archived A10 first request carries 9,590 UTF-8 bytes of specialist/technical material for an initial image observation.

## Change

The opt-in `visual_first` path (OFF by default) projects a prevalidated, schema-aware specialist request into a bounded, pixel-only task. It includes the exact trusted delegated feature codes, original image/evidence context, existing observation-memory JSON, current uncertainty questions, coverage-task IDs, states and physical-check holds. It excludes the lengthy building-law/reference text from the initial **vision** call, while retaining a hash-bound complete source prompt in the PRIVATE dossier for downstream expert interpretation, case-specific retrieval and Q02/Q03/human inspection. The authoritative schema is passed *unchanged* to the provider. The existing `validate_proposal`, duplicate checks, custody hashes, native zoom/video controls, Q01/Q02, and human release guard are not altered. Omission or unbounded memory fails closed instead of truncating content.

No developer-entered defect or zoom coordinates are preprogrammed; the model is still asked to select meaningful visual evidence and is free to return no candidates/tools. It is instructed to avoid root cause, code violation, safety certification, or defect-free claims from the image alone. The saved full prompt must not be published or uploaded to a public GitHub repo for actual private inspections.

## Reproducible offline replay

Fixture: exact `trial/invocations/0001-writer.request.json` saved in the A10 synthetic-only Actions evidence archive. The image bytes and generation schema are NOT modified by this code.

- Baseline compact writer prompt: 9,590 UTF-8 bytes.
- Projected visual-stage prompt: 2,651 UTF-8 bytes (a 72.4% reduction).
- Offline dedicated tests: 12/12 PASS, including input/schema SHA identity, prior memory and evidence context equality, incomplete holds, oversized memory, duplicate structured labels, tampering, and whole original context provenance.
- These bytes are not model-token counts. **No inference speedup, visual accuracy improvement, Q02/Q03 result or valid field report has been demonstrated.**

## Critical acceptance and recovery

1. Full current-branch tests and security review must pass before enabling `--visual-first` in a remote trial. The current default is OFF.
2. Record the live image hash, prompt hashes, schema hash, model digest, load/prompt/generation timings, and actual output; validate retained deferred expert packet before technical review.
3. Verify correct diverse observations, false alarms, duplicate handling and useful autonomous source-crop/video moment selection; do not accept forced scripted coordinates.
4. Invoke and evaluate separate Q02 visual critique and Q03 adjudication with source-bound technical knowledge and source-status receipts.
5. Keep benchmark on independent qualified-inspector-labeled real cases as a non-negotiable field-release gate. No guarantee of spotting every defect or eliminating liability.
6. Preserve `PAUSE_AUTONOMY`, keep `main` unchanged and do not activate an external compute workflow without new specific owner authorization.

Internal review, not a separate agent review. Local replay test success does not approve Milestone 2.

The committed replay fixture is synthetic-only and SHA-pinned (`tests/fixtures/a10_saved_writer_request.json`). Tests cannot skip due to a missing `/mnt/data` path.
