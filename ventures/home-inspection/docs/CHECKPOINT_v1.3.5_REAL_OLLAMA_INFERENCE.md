# Home inspection v1.3.5 — first genuine Ollama image inference (A05)

Observed date: 2026-10-30 Detroit (GitHub run began 2026-10-31 UTC).
Repository: `ksolo21-web/K.O.-Enterprises`, product branch `home-inspection-development`.

## Real remotely executed model evidence

- **A05 run ID:** `41164389582`
- **Run URL:** https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41164389582
- **Immutable run SHA:** `ffb4b566416fd29b662095022b00548528d3e1d3`
- The live job passed: runner setup, source checkout, narrow authorization guard, Python setup, FFmpeg+zstd provisioning, Python requirements+synthetic fixtures, verified Ollama v0.40.13 binary, starting loopback Ollama and downloading both public vision-model weights.
- **The step `Prove both models generate actual image-conditioned responses` completed SUCCESS.** Its executed Python code called `local_json('POST','/api/generate',...)` against `127.0.0.1:11434`, submitted one synthetic PNG to Qwen2.5-VL 3B and a distinct synthetic PNG to Granite 3.2 Vision 2B, required `done=True` for each real response, and saved `first_real_vision_proofs.json` for artifact upload. This was not a mocked provider or hard-coded simulation.
- The actual response text and per-model durations remain **awaiting run logs and artifact extraction**. The successful GitHub step establishes execution completion, not visual correctness; no claim should be made about what colors/shapes each model perceived until those outputs are read.
- At this checkpoint, the complete specialist zoom/video/Q02 acceptance step was still `in_progress`. Its pass status is **not established**, nor is real-property accuracy or professional inspector signoff.

## Independent regression and reliability repairs

The earlier A04 remote regression (https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41164253727) completed **174 tests, 1 failed and 12 errors**. The issues were FFmpeg video timestamp/seek differences and two tests incorrectly seeking the manual workflow inside the product rather than at repository root.

The development branch now includes commit `037b19273e9b5065f035a01bfe261e3dc36fa7f0` to:
- Select exactly one source-normalized video frame based on PTS and prevent codec prefetch from polluting timestamp attestation.
- Use the same reproducible decoder for video stills, selected-photo audits, video-derived native zoom and convenience samples; retain source SHA and pixel-custody requirements.
- Locate the manual workflow in both standalone project archives and monorepo checkouts.
- Add two timestamp-reproducibility tests.

A local working copy of the original v1.3.4 source plus these changes ran **181/181 tests successfully with FFmpeg 7.1.5**. This is not a fresh GitHub remote regression pass; GitHub runner-specific test verification remains outstanding.

## Governance and release

- A05 single-use workflow was removed in commit `4ebb25ae506df7ed7f1704c1971b86a9dd5c9b05`.
- Root `PAUSE_AUTONOMY` remains intact. Public repository uses synthetic evidence only; no client media, secrets, deployment, payments, outreach or `main` changes.
- No autonomous human verification; qualified inspector review is not demonstrated; reports may not be issued to customers.
- **Milestone 2 remains NOT APPROVED.** Distinguish verified live Ollama image inference from unfinished separate-agent zoom/video/Q02 gates.
