# Territory card production

This branch preserves the territory skills and runs candidate-build tooling without Work, Codex or paid model APIs. It is not yet approved for unattended real-card release.

## Verified September 10, 2026

- All 39 original source-transfer segments committed; the original ZIP reconstructed byte-for-byte; all 138 original skills, scripts and policy files verified by SHA-256 on GitHub.
- Candidate tooling installed and tested. Live run 34519312729, job 103012547203, passed 137 unique software tests with no failures, errors or skips. The 16 delivery tests were repeated separately and are not counted twice.
- A real encrypted synthetic trial processed two candidates with zero processing failures, generated 16 original evidence screenshots, published an encrypted result and returned an authenticated downloadable artifact. Local decryption verified all 24 returned files. Both saved PDFs matched local reference renders at 1x, 2x and 4x. The repair rejected the first authorized position and accepted the second, without changing colored road pixels or pixels outside approved masks.
- Real territory cards released: zero. Synthetic test success is not independent visual approval.

Read `production/CHECKPOINT.json` and `production/evidence/ENCRYPTED-INTEGRATION-RECEIPT.json` for exact identities, evidence and remaining work. The source-transfer blocker is resolved; do not repeat that migration or reinstall an older extension payload over changed files.

## Non-negotiable controls

No paid AI APIs, Work, Codex, larger runners or model-provider credentials are enabled in the tested candidate workflow. Standard public Ubuntu runners are used; no account billing balance is asserted. No OANDA or Stripe secrets are used. Nothing writes to main; main was reverified at 61ca9202fbfe45aae4a0ed29326df44cf7b25c9e.

Do not commit plaintext private maps, cards, address records, decrypted private evidence or private keys. The encrypted-job workflow commits ciphertext only. Its owner-triggered GitHub runner necessarily decrypts input in temporary storage to process it; this requires trusting that execution environment. Encryption does not hide running-job plaintext from the host. Encrypted return artifacts are bounded to two megabytes and retained for one day; encrypted transport also remains on the branch. The completed live trials used only synthetic data.

Preserve `territory-map-card-builder`, `territory-card-critic` and `kaleb-quality-loop` verbatim. The recovered strict policy requires every scoring category to equal 10 and every mandatory gate to pass. Deterministic checks and screenshot generation do not constitute an independent visual reviewer. Never replace missing evidence with a pass or overwrite approved sources.

## Running the installed code

Use Python 3.12 in a virtual environment and install `production/requirements.txt`. From the repository root:

```sh
python territory/production/engine.py doctor
python territory/production/audit_kit.py
python territory/production/batch.py /private/approved-job /private/fresh-candidates
python territory/production/client.py /private/approved-job --output /private/fresh-return
```

The client uses the owner's existing GitHub CLI authorization, saves an owner-only recovery key, and submits an encrypted job to this branch. The exact owner-client interruption/restart path is not yet certified. Never delete the recovery key until the returned result is safely recovered. Do not put the key in the public repository.

A job requires a schema-version-1 job.json with unique card IDs, build/repair actions and SHA-256-pinned recipes. Build mode needs an approved blank template and complete approved source-map page; it does not invent maps or infer coverage. Repair mode needs explicit old-label bounds, approved masks, font resources, assigned road geometry and authorized candidate placements. Output is candidate-only, accompanied by exact-file capture evidence and a checkpoint.

## Still blocked or unverified

Qualify the independent local visual critic on actual accepted and rejected territory cards; earlier synthetic model calibration is insufficient. Integrate the complete independent review, authorized repair, fresh review, original release gates and exact-final-file inspection. Recover and reconcile the real batch queue, approved maps, templates, coverage ledger and authorizations. Prove interrupted-batch resume, concurrent submission behavior, complete automatic owner-client execution and applicable real-card geography/template/legacy release checks.

Model-only release remains disabled. The signed-human-review path still requires all original release gates and an owner-pinned reviewer key; it has not approved a real card in this migration. Overall internal migration review: 7/10, not approved for unattended real-card production.
