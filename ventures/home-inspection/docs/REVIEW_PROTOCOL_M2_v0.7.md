# M2 second-pass evidence critique — v0.7

**Status: implemented and tested as a second-call provider interface, not verified against any live vision model.**

## Design contract

1. M00 dispatches an inspector-assigned image to the correct T01–T08 specialist using bounded work orders.
2. Specialist proposes observations or concerns with the media hash and optional exact native-pixel crop reference. No findings are definitive.
3. Q01 reevaluates custody, source hashes, source-relative crops and scope rules using deterministic checks.
4. Q02 is a separate *technical-review invocation* that receives the original context image and native crop together, plus a clearly marked untrusted claim. Responses are limited to `visually_plausible`, `not_supported`, and `insufficient_evidence` with reasons and requested evidence. It cannot invoke tools or modify findings.
5. A different `provider_id` is required. **Provider IDs alone do not verify the existence of a separate model, independent agent/runtime, or impartial opinion.** For stronger separation in a live installation, configure a genuinely different reviewer model/runtime. This is not yet demonstrated.
6. The dossier must match the project. Every proposed claim must be present in the original staged findings, with correct original-photo hashes and verified zoom lineage. Review fails before model access if custody/authority is compromised.
7. No Q02 disposition, including `visually_plausible`, can promote a finding to `human_verified`, sign off on safety, mark a system inspected, or release a report.

## Local optional reviewer invocation

Requires TWO *already installed* vision-capable Ollama models and an Ollama server at `127.0.0.1:11434`. Models are not downloaded automatically. The writer and critic model IDs must differ.

```bash
python -m inspection_engine agents-run private_case/intake.json \
  --media-ids P0001 --model WRITER_MODEL \
  --out-project private_case/staged.json --dossier private_case/writer_dossier.json
python -m inspection_engine agents-critic private_case/staged.json \
  --dossier private_case/writer_dossier.json \
  --review-model REVIEWER_MODEL --out private_case/second_pass.json
```

The second command will **fail clearly** without the local model, when the first model ID is reused, or when evidence has been altered. User content is not sent to a remote endpoint by this implementation. Runtime/model inference may take significant memory and time; particular models are NOT validated by the synthetic test suite.

## Acceptance and next blockers

- [x] Strict separate provider call and explicit role boundary
- [x] Original context plus native crop imagery; no digital detail enhancement
- [x] Dossier/project evidence hash, claim linkage, integrity and authority checks
- [x] Technical assessment has bounded response schema and no tool commands
- [x] Pending, rejected and plausible cases remain human-review-pending
- [x] Negative tests for fabricated, altered, duplicate or unsafe results
- [x] GitHub Actions workflow prepared (not remotely executed yet)
- [ ] Live independent model or truly separate agent runtime exercised and recorded
- [ ] Human-adjudicated reference set and real-property accuracy measured
- [ ] Human reviewer authentication and signature, security and privacy review
- [ ] Repository created, pushed, and CI run remotely

**Human inspection and final approval are essential.** No benchmark score or release approval is claimed.